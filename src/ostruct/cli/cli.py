"""Command-line interface for making structured OpenAI API calls."""

import asyncio
import copy
import json
import logging
import os
import sys
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
)

if sys.version_info >= (3, 11):
    pass

from datetime import date, datetime, time
from pathlib import Path

import click
import jinja2
import yaml
from openai import AsyncOpenAI
from openai_model_registry import (
    ModelNotSupportedError,
    ModelRegistry,
    ModelRegistryError,
    ModelVersionError,
    ParameterNotSupportedError,
    ParameterValidationError,
)
from pydantic import AnyUrl, BaseModel, EmailStr, Field
from pydantic.fields import FieldInfo as FieldInfoType
from pydantic.functional_validators import BeforeValidator
from pydantic.types import constr
from typing_extensions import TypeAlias

from ostruct.cli.click_options import all_options
from ostruct.cli.exit_codes import ExitCode

from .. import __version__  # noqa: F401 - Used in package metadata
from .code_interpreter import CodeInterpreterManager
from .config import OstructConfig
from .cost_estimation import calculate_cost_estimate, format_cost_breakdown
from .errors import (
    APIErrorMapper,
    CLIError,
    DirectoryNotFoundError,
    InvalidJSONError,
    ModelCreationError,
    OstructFileNotFoundError,
    PathSecurityError,
    SchemaFileError,
    SchemaValidationError,
    StreamInterruptedError,
    StreamParseError,
    TaskTemplateSyntaxError,
    TaskTemplateVariableError,
    VariableNameError,
    VariableValueError,
)
from .explicit_file_processor import ExplicitFileProcessor
from .file_search import FileSearchManager
from .file_utils import FileInfoList, collect_files
from .mcp_integration import MCPConfiguration, MCPServerManager
from .model_creation import _create_enum_type, create_dynamic_model
from .path_utils import validate_path_mapping
from .progress_reporting import (
    configure_progress_reporter,
    get_progress_reporter,
    report_success,
)
from .registry_updates import get_update_notification
from .security import SecurityManager
from .serialization import LogSerializer
from .template_env import create_jinja_env
from .template_utils import (
    SystemPromptError,
    render_template,
    validate_json_schema,
)
from .token_utils import estimate_tokens_with_encoding
from .token_validation import TokenLimitValidator
from .unattended_operation import (
    UnattendedCompatibilityValidator,
    UnattendedOperationManager,
)


def make_strict(obj: Any) -> None:
    """Transform Pydantic schema for Responses API strict mode.

    This function recursively adds 'additionalProperties: false' to all object types
    in a JSON schema to make it compatible with OpenAI's strict mode requirement.

    Args:
        obj: The schema object to transform (modified in-place)
    """
    if isinstance(obj, dict):
        if obj.get("type") == "object" and "additionalProperties" not in obj:
            obj["additionalProperties"] = False
        for value in obj.values():
            make_strict(value)
    elif isinstance(obj, list):
        for item in obj:
            make_strict(item)


# Model Registry Integration - Using external openai-model-registry library


# For compatibility with existing code
def supports_structured_output(model: str) -> bool:
    """Check if model supports structured output."""
    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)
        return getattr(capabilities, "supports_structured_output", True)
    except Exception:
        # Default to True for backward compatibility
        return True


class RegistryUpdateStatus:
    """Status constants for registry updates."""

    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    ALREADY_CURRENT = "ALREADY_CURRENT"


# Code Interpreter Integration (T2.2) - File upload and code execution
# Error Mapping (T3.1) - OpenAI SDK error mapping
# Explicit File Routing (T2.4) - Tool-specific file routing system
# File Search Integration (T2.3) - Vector store and retrieval
# MCP Integration (T2.1) - Model Context Protocol server support


# Temporary error classes (to be replaced in T1.2)
class APIResponseError(Exception):
    pass


class EmptyResponseError(Exception):
    pass


class InvalidResponseFormatError(Exception):
    pass


class OpenAIClientError(Exception):
    pass


class StreamBufferError(Exception):
    pass


# Constants
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


# Validation functions
def pattern(regex: str) -> Any:
    return constr(pattern=regex)


def min_length(length: int) -> Any:
    return BeforeValidator(lambda v: v if len(str(v)) >= length else None)


def max_length(length: int) -> Any:
    return BeforeValidator(lambda v: v if len(str(v)) <= length else None)


def ge(value: Union[int, float]) -> Any:
    return BeforeValidator(lambda v: v if float(v) >= value else None)


def le(value: Union[int, float]) -> Any:
    return BeforeValidator(lambda v: v if float(v) <= value else None)


def gt(value: Union[int, float]) -> Any:
    return BeforeValidator(lambda v: v if float(v) > value else None)


def lt(value: Union[int, float]) -> Any:
    return BeforeValidator(lambda v: v if float(v) < value else None)


def multiple_of(value: Union[int, float]) -> Any:
    return BeforeValidator(lambda v: v if float(v) % value == 0 else None)


def create_template_context(
    files: Optional[
        Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]]
    ] = None,
    variables: Optional[Dict[str, str]] = None,
    json_variables: Optional[Dict[str, Any]] = None,
    security_manager: Optional[SecurityManager] = None,
    stdin_content: Optional[str] = None,
) -> Dict[str, Any]:
    """Create template context from files and variables."""
    context: Dict[str, Any] = {}

    # Add file variables
    if files:
        for name, file_list in files.items():
            context[name] = file_list  # Always keep FileInfoList wrapper

    # Add simple variables
    if variables:
        context.update(variables)

    # Add JSON variables
    if json_variables:
        context.update(json_variables)

    # Add stdin if provided
    if stdin_content is not None:
        context["stdin"] = stdin_content

    return context


class CLIParams(TypedDict, total=False):
    """Type-safe CLI parameters."""

    files: List[Tuple[str, str]]  # List of (name, path) tuples from Click's nargs=2
    dir: List[Tuple[str, str]]  # List of (name, dir) tuples from Click's nargs=2
    patterns: List[
        Tuple[str, str]
    ]  # List of (name, pattern) tuples from Click's nargs=2
    allowed_dirs: List[str]
    base_dir: str
    allowed_dir_file: Optional[str]
    recursive: bool
    var: List[str]
    json_var: List[str]
    system_prompt: Optional[str]
    system_prompt_file: Optional[str]
    ignore_task_sysprompt: bool
    model: str
    timeout: float
    output_file: Optional[str]
    dry_run: bool
    no_progress: bool
    api_key: Optional[str]
    verbose: bool
    debug_openai_stream: bool
    show_model_schema: bool
    debug_validation: bool
    temperature: Optional[float]
    max_output_tokens: Optional[int]
    top_p: Optional[float]
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    reasoning_effort: Optional[str]
    progress_level: str
    task_file: Optional[str]
    task: Optional[str]
    schema_file: str
    mcp_servers: List[str]
    mcp_allowed_tools: List[str]
    mcp_require_approval: str
    mcp_headers: Optional[str]
    code_interpreter_files: List[str]
    code_interpreter_dirs: List[str]
    code_interpreter_download_dir: str
    code_interpreter_cleanup: bool
    file_search_files: List[str]
    file_search_dirs: List[str]
    file_search_vector_store_name: str
    file_search_cleanup: bool
    file_search_retry_count: int
    file_search_timeout: float
    template_files: List[str]
    template_dirs: List[str]
    template_file_aliases: List[
        Tuple[str, str]
    ]  # List of (name, path) tuples from --fta
    code_interpreter_file_aliases: List[
        Tuple[str, str]
    ]  # List of (name, path) tuples from --fca
    file_search_file_aliases: List[
        Tuple[str, str]
    ]  # List of (name, path) tuples from --fsa
    tool_files: List[Tuple[str, str]]  # List of (tool, path) tuples from --file-for


# Set up logging
logger = logging.getLogger(__name__)


def _generate_template_variable_name(file_path: str) -> str:
    """Generate a template variable name from a file path.

    Converts filename to a valid template variable name by:
    1. Taking the full filename (with extension)
    2. Replacing dots and other special characters with underscores
    3. Ensuring it starts with a letter or underscore

    Examples:
        data.csv -> data_csv
        data.json -> data_json
        my-file.txt -> my_file_txt
        123data.xml -> _123data_xml

    Args:
        file_path: Path to the file

    Returns:
        Valid template variable name
    """
    import re

    filename = Path(file_path).name
    # Replace special characters with underscores
    var_name = re.sub(r"[^a-zA-Z0-9_]", "_", filename)
    # Ensure it starts with letter or underscore
    if var_name and var_name[0].isdigit():
        var_name = "_" + var_name
    return var_name


# Configure OpenAI SDK logging
openai_logger = logging.getLogger("openai")
openai_logger.setLevel(logging.DEBUG)  # Allow all messages through to handlers
openai_logger.propagate = False  # Prevent propagation to root logger

# Remove any existing handlers
for handler in openai_logger.handlers:
    openai_logger.removeHandler(handler)

# Create a file handler for OpenAI SDK logger that captures all levels
log_dir = os.path.expanduser("~/.ostruct/logs")
os.makedirs(log_dir, exist_ok=True)
openai_file_handler = logging.FileHandler(os.path.join(log_dir, "openai_stream.log"))
openai_file_handler.setLevel(logging.DEBUG)  # Always capture debug in file
openai_file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
openai_logger.addHandler(openai_file_handler)

# Create a file handler for the main logger that captures all levels
ostruct_file_handler = logging.FileHandler(os.path.join(log_dir, "ostruct.log"))
ostruct_file_handler.setLevel(logging.DEBUG)  # Always capture debug in file
ostruct_file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(ostruct_file_handler)


# Type aliases
FieldType = Any  # Changed from Type[Any] to allow both concrete types and generics
FieldDefinition = Tuple[FieldType, FieldInfoType]
ModelType = TypeVar("ModelType", bound=BaseModel)
ItemType: TypeAlias = Type[BaseModel]
ValueType: TypeAlias = Type[Any]


def _create_field(**kwargs: Any) -> FieldInfoType:
    """Create a Pydantic Field with the given kwargs."""
    field: FieldInfoType = Field(**kwargs)
    return field


def _get_type_with_constraints(
    field_schema: Dict[str, Any], field_name: str, base_name: str
) -> FieldDefinition:
    """Get type with constraints from field schema.

    Args:
        field_schema: Field schema dict
        field_name: Name of the field
        base_name: Base name for nested models

    Returns:
        Tuple of (type, field)
    """
    field_kwargs: Dict[str, Any] = {}

    # Add common field metadata
    if "title" in field_schema:
        field_kwargs["title"] = field_schema["title"]
    if "description" in field_schema:
        field_kwargs["description"] = field_schema["description"]
    if "default" in field_schema:
        field_kwargs["default"] = field_schema["default"]
    if "readOnly" in field_schema:
        field_kwargs["frozen"] = field_schema["readOnly"]

    field_type = field_schema.get("type")

    # Handle array type
    if field_type == "array":
        items_schema = field_schema.get("items", {})
        if not items_schema:
            return (List[Any], Field(**field_kwargs))

        # Create nested model for object items
        if isinstance(items_schema, dict) and items_schema.get("type") == "object":
            array_item_model = create_dynamic_model(
                items_schema,
                base_name=f"{base_name}_{field_name}_Item",
                show_schema=False,
                debug_validation=False,
            )
            array_type: Type[List[Any]] = List[array_item_model]  # type: ignore
            return (array_type, Field(**field_kwargs))

        # For non-object items, use the type directly
        item_type = items_schema.get("type", "string")
        if item_type == "string":
            return (List[str], Field(**field_kwargs))
        elif item_type == "integer":
            return (List[int], Field(**field_kwargs))
        elif item_type == "number":
            return (List[float], Field(**field_kwargs))
        elif item_type == "boolean":
            return (List[bool], Field(**field_kwargs))
        else:
            return (List[Any], Field(**field_kwargs))

    # Handle object type
    if field_type == "object":
        # Create nested model with explicit type annotation
        object_model = create_dynamic_model(
            field_schema,
            base_name=f"{base_name}_{field_name}",
            show_schema=False,
            debug_validation=False,
        )
        return (object_model, Field(**field_kwargs))

    # Handle additionalProperties
    if "additionalProperties" in field_schema and isinstance(
        field_schema["additionalProperties"], dict
    ):
        # Create nested model with explicit type annotation
        dict_value_model = create_dynamic_model(
            field_schema["additionalProperties"],
            base_name=f"{base_name}_{field_name}_Value",
            show_schema=False,
            debug_validation=False,
        )
        dict_type: Type[Dict[str, Any]] = Dict[str, dict_value_model]  # type: ignore[valid-type]
        return (dict_type, Field(**field_kwargs))

    # Handle other types
    if field_type == "string":
        field_type_cls: Type[Any] = str

        # Add string-specific constraints to field_kwargs
        if "pattern" in field_schema:
            field_kwargs["pattern"] = field_schema["pattern"]
        if "minLength" in field_schema:
            field_kwargs["min_length"] = field_schema["minLength"]
        if "maxLength" in field_schema:
            field_kwargs["max_length"] = field_schema["maxLength"]

        # Handle special string formats
        if "format" in field_schema:
            if field_schema["format"] == "date-time":
                field_type_cls = datetime
            elif field_schema["format"] == "date":
                field_type_cls = date
            elif field_schema["format"] == "time":
                field_type_cls = time
            elif field_schema["format"] == "email":
                field_type_cls = EmailStr
            elif field_schema["format"] == "uri":
                field_type_cls = AnyUrl

        return (field_type_cls, Field(**field_kwargs))

    if field_type == "number":
        field_type_cls = float

        # Add number-specific constraints to field_kwargs
        if "minimum" in field_schema:
            field_kwargs["ge"] = field_schema["minimum"]
        if "maximum" in field_schema:
            field_kwargs["le"] = field_schema["maximum"]
        if "exclusiveMinimum" in field_schema:
            field_kwargs["gt"] = field_schema["exclusiveMinimum"]
        if "exclusiveMaximum" in field_schema:
            field_kwargs["lt"] = field_schema["exclusiveMaximum"]
        if "multipleOf" in field_schema:
            field_kwargs["multiple_of"] = field_schema["multipleOf"]

        return (field_type_cls, Field(**field_kwargs))

    if field_type == "integer":
        field_type_cls = int

        # Add integer-specific constraints to field_kwargs
        if "minimum" in field_schema:
            field_kwargs["ge"] = field_schema["minimum"]
        if "maximum" in field_schema:
            field_kwargs["le"] = field_schema["maximum"]
        if "exclusiveMinimum" in field_schema:
            field_kwargs["gt"] = field_schema["exclusiveMinimum"]
        if "exclusiveMaximum" in field_schema:
            field_kwargs["lt"] = field_schema["exclusiveMaximum"]
        if "multipleOf" in field_schema:
            field_kwargs["multiple_of"] = field_schema["multipleOf"]

        return (field_type_cls, Field(**field_kwargs))

    if field_type == "boolean":
        return (bool, Field(**field_kwargs))

    if field_type == "null":
        return (type(None), Field(**field_kwargs))

    # Handle enum
    if "enum" in field_schema:
        enum_type = _create_enum_type(field_schema["enum"], field_name)
        return (cast(Type[Any], enum_type), Field(**field_kwargs))

    # Default to Any for unknown types
    return (Any, Field(**field_kwargs))


T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def validate_token_limits(
    model: str, total_tokens: int, max_token_limit: Optional[int] = None
) -> None:
    """Validate token counts against model limits."""
    registry = ModelRegistry.get_instance()
    capabilities = registry.get_capabilities(model)
    context_limit = capabilities.context_window
    output_limit = (
        max_token_limit
        if max_token_limit is not None
        else capabilities.max_output_tokens
    )

    # Check if total tokens exceed context window
    if total_tokens >= context_limit:
        raise ValueError(
            f"Total tokens ({total_tokens:,}) exceed {model}'s context window "
            f"of {context_limit:,} tokens. Consider using a model with a larger "
            f"context window or reducing input size."
        )

    # Check if there's enough room for output tokens
    remaining_tokens = context_limit - total_tokens
    if remaining_tokens < output_limit:
        raise ValueError(
            f"Only {remaining_tokens:,} tokens remaining in context window, but "
            f"output may require up to {output_limit:,} tokens"
        )


def process_system_prompt(
    task_template: str,
    system_prompt: Optional[str],
    system_prompt_file: Optional[str],
    template_context: Dict[str, Any],
    env: jinja2.Environment,
    ignore_task_sysprompt: bool = False,
    template_path: Optional[str] = None,
) -> str:
    """Process system prompt from various sources.

    Args:
        task_template: The task template string
        system_prompt: Optional system prompt string
        system_prompt_file: Optional path to system prompt file
        template_context: Template context for rendering
        env: Jinja2 environment
        ignore_task_sysprompt: Whether to ignore system prompt in task template
        template_path: Optional path to template file for include_system resolution

    Returns:
        The final system prompt string

    Raises:
        SystemPromptError: If the system prompt cannot be loaded or rendered
        FileNotFoundError: If a prompt file does not exist
        PathSecurityError: If a prompt file path violates security constraints
    """
    # Check for conflicting arguments
    if system_prompt is not None and system_prompt_file is not None:
        raise SystemPromptError(
            "Cannot specify both --system-prompt and --system-prompt-file"
        )

    # CLI system prompt takes precedence and stops further processing
    if system_prompt_file is not None:
        try:
            name, path = validate_path_mapping(f"system_prompt={system_prompt_file}")
            with open(path, "r", encoding="utf-8") as f:
                cli_system_prompt = f.read().strip()
        except OstructFileNotFoundError as e:
            raise SystemPromptError(f"Failed to load system prompt file: {e}") from e
        except PathSecurityError as e:
            raise SystemPromptError(f"Invalid system prompt file: {e}") from e

        try:
            template = env.from_string(cli_system_prompt)
            return template.render(**template_context).strip()
        except jinja2.TemplateError as e:
            raise SystemPromptError(f"Error rendering system prompt: {e}")

    elif system_prompt is not None:
        try:
            template = env.from_string(system_prompt)
            return template.render(**template_context).strip()
        except jinja2.TemplateError as e:
            raise SystemPromptError(f"Error rendering system prompt: {e}")

    # Build message parts from template in order: auto-stub, include_system, system_prompt
    message_parts = []

    # 1. Auto-stub (default system prompt)
    message_parts.append("You are a helpful assistant.")

    # 2. Template-based system prompts (include_system and system_prompt)
    if not ignore_task_sysprompt:
        try:
            # Extract YAML frontmatter
            if task_template.startswith("---\n"):
                end = task_template.find("\n---\n", 4)
                if end != -1:
                    frontmatter = task_template[4:end]
                    try:
                        metadata = yaml.safe_load(frontmatter)
                        if isinstance(metadata, dict):
                            # 2a. include_system: from template
                            inc = metadata.get("include_system")
                            if inc and template_path:
                                inc_path = (Path(template_path).parent / inc).resolve()
                                if not inc_path.is_file():
                                    raise click.ClickException(
                                        f"include_system file not found: {inc}"
                                    )
                                include_txt = inc_path.read_text(encoding="utf-8")
                                message_parts.append(include_txt)

                            # 2b. system_prompt: from template
                            if "system_prompt" in metadata:
                                template_system_prompt = str(metadata["system_prompt"])
                                try:
                                    template = env.from_string(template_system_prompt)
                                    message_parts.append(
                                        template.render(**template_context).strip()
                                    )
                                except jinja2.TemplateError as e:
                                    raise SystemPromptError(
                                        f"Error rendering system prompt: {e}"
                                    )
                    except yaml.YAMLError as e:
                        raise SystemPromptError(f"Invalid YAML frontmatter: {e}")

        except Exception as e:
            raise SystemPromptError(
                f"Error extracting system prompt from template: {e}"
            )

    # Return the combined message (remove default if we have other content)
    if len(message_parts) > 1:
        # Remove the default auto-stub if we have other content
        return "\n\n".join(message_parts[1:]).strip()
    else:
        # Return just the default
        return message_parts[0]


def validate_variable_mapping(mapping: str, is_json: bool = False) -> tuple[str, Any]:
    """Validate a variable mapping in name=value format."""
    try:
        name, value = mapping.split("=", 1)
        if not name:
            raise VariableNameError(
                f"Empty name in {'JSON ' if is_json else ''}variable mapping"
            )

        if is_json:
            try:
                value = json.loads(value)
            except json.JSONDecodeError as e:
                raise InvalidJSONError(
                    f"Invalid JSON value for variable {name!r}: {value!r}",
                    context={"variable_name": name},
                ) from e

        return name, value

    except ValueError as e:
        if "not enough values to unpack" in str(e):
            raise VariableValueError(
                f"Invalid {'JSON ' if is_json else ''}variable mapping "
                f"(expected name=value format): {mapping!r}"
            )
        raise


@overload
def _validate_path_mapping_internal(
    mapping: str,
    is_dir: Literal[True],
    base_dir: Optional[str] = None,
    security_manager: Optional[SecurityManager] = None,
) -> Tuple[str, str]: ...


@overload
def _validate_path_mapping_internal(
    mapping: str,
    is_dir: Literal[False] = False,
    base_dir: Optional[str] = None,
    security_manager: Optional[SecurityManager] = None,
) -> Tuple[str, str]: ...


def _validate_path_mapping_internal(
    mapping: str,
    is_dir: bool = False,
    base_dir: Optional[str] = None,
    security_manager: Optional[SecurityManager] = None,
) -> Tuple[str, str]:
    """Validate a path mapping in the format "name=path".

    Args:
        mapping: The path mapping string (e.g., "myvar=/path/to/file").
        is_dir: Whether the path is expected to be a directory (True) or file (False).
        base_dir: Optional base directory to resolve relative paths against.
        security_manager: Optional security manager to validate paths.

    Returns:
        A (name, path) tuple.

    Raises:
        VariableNameError: If the variable name portion is empty or invalid.
        DirectoryNotFoundError: If is_dir=True and the path is not a directory or doesn't exist.
        FileNotFoundError: If is_dir=False and the path is not a file or doesn't exist.
        PathSecurityError: If the path is inaccessible or outside the allowed directory.
        ValueError: If the format is invalid (missing "=").
        OSError: If there is an underlying OS error (permissions, etc.).
    """
    logger = logging.getLogger(__name__)
    logger.debug("Starting path validation for mapping: %r", mapping)
    logger.debug("Parameters - is_dir: %r, base_dir: %r", is_dir, base_dir)

    try:
        if not mapping or "=" not in mapping:
            logger.debug("Invalid mapping format: %r", mapping)
            raise ValueError("Invalid path mapping format. Expected format: name=path")

        name, path = mapping.split("=", 1)
        logger.debug("Split mapping - name: %r, path: %r", name, path)

        if not name:
            logger.debug("Empty name in mapping")
            raise VariableNameError(
                f"Empty name in {'directory' if is_dir else 'file'} mapping"
            )

        if not path:
            logger.debug("Empty path in mapping")
            raise VariableValueError("Path cannot be empty")

        # Convert to Path object and resolve against base_dir if provided
        logger.debug("Creating Path object for: %r", path)
        path_obj = Path(path)
        if base_dir:
            logger.debug("Resolving against base_dir: %r", base_dir)
            path_obj = Path(base_dir) / path_obj
        logger.debug("Path object created: %r", path_obj)

        # Resolve the path to catch directory traversal attempts
        try:
            logger.debug("Attempting to resolve path: %r", path_obj)
            resolved_path = path_obj.resolve()
            logger.debug("Resolved path: %r", resolved_path)
        except OSError as e:
            logger.error("Failed to resolve path: %s", e)
            raise OSError(f"Failed to resolve path: {e}")

        # Check for directory traversal
        try:
            base_path = Path.cwd() if base_dir is None else Path(base_dir).resolve()
            if not str(resolved_path).startswith(str(base_path)):
                raise PathSecurityError(
                    f"Path {str(path)!r} resolves to {str(resolved_path)!r} which is outside "
                    f"base directory {str(base_path)!r}"
                )
        except OSError as e:
            raise OSError(f"Failed to resolve base path: {e}")

        # Check if path exists
        if not resolved_path.exists():
            if is_dir:
                raise DirectoryNotFoundError(f"Directory not found: {path!r}")
            else:
                raise FileNotFoundError(f"File not found: {path!r}")

        # Check if path is correct type
        if is_dir and not resolved_path.is_dir():
            raise DirectoryNotFoundError(f"Path is not a directory: {path!r}")
        elif not is_dir and not resolved_path.is_file():
            raise FileNotFoundError(f"Path is not a file: {path!r}")

        # Check if path is accessible
        try:
            if is_dir:
                os.listdir(str(resolved_path))
            else:
                with open(str(resolved_path), "r", encoding="utf-8") as f:
                    f.read(1)
        except OSError as e:
            if e.errno == 13:  # Permission denied
                raise PathSecurityError(
                    f"Permission denied accessing path: {path!r}",
                    error_logged=True,
                )
            raise

        if security_manager:
            try:
                security_manager.validate_path(str(resolved_path))
            except PathSecurityError:
                raise PathSecurityError.from_expanded_paths(
                    original_path=str(path),
                    expanded_path=str(resolved_path),
                    base_dir=str(security_manager.base_dir),
                    allowed_dirs=[str(d) for d in security_manager.allowed_dirs],
                    error_logged=True,
                )

        # Return the original path to maintain relative paths in the output
        return name, path

    except ValueError as e:
        if "not enough values to unpack" in str(e):
            raise VariableValueError(
                f"Invalid {'directory' if is_dir else 'file'} mapping "
                f"(expected name=path format): {mapping!r}"
            )
        raise


def validate_task_template(task: Optional[str], task_file: Optional[str]) -> str:
    """Validate and load a task template.

    Args:
        task: The task template string
        task_file: Path to task template file

    Returns:
        The task template string

    Raises:
        TaskTemplateVariableError: If neither task nor task_file is provided, or if both are provided
        TaskTemplateSyntaxError: If the template has invalid syntax
        FileNotFoundError: If the template file does not exist
        PathSecurityError: If the template file path violates security constraints
    """
    if task is not None and task_file is not None:
        raise TaskTemplateVariableError("Cannot specify both --task and --task-file")

    if task is None and task_file is None:
        raise TaskTemplateVariableError("Must specify either --task or --task-file")

    template_content: str
    if task_file is not None:
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                template_content = f.read()
        except FileNotFoundError:
            raise TaskTemplateVariableError(
                f"Task template file not found: {task_file}"
            )
        except PermissionError:
            raise TaskTemplateVariableError(
                f"Permission denied reading task template file: {task_file}"
            )
        except Exception as e:
            raise TaskTemplateVariableError(f"Error reading task template file: {e}")
    else:
        template_content = task  # type: ignore  # We know task is str here due to the checks above

    try:
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.parse(template_content)
        return template_content
    except jinja2.TemplateSyntaxError as e:
        raise TaskTemplateSyntaxError(
            f"Invalid task template syntax at line {e.lineno}: {e.message}"
        )


def validate_schema_file(
    path: str,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Validate and load a JSON schema file.

    Args:
        path: Path to schema file
        verbose: Whether to enable verbose logging

    Returns:
        The validated schema

    Raises:
        SchemaFileError: When file cannot be read
        InvalidJSONError: When file contains invalid JSON
        SchemaValidationError: When schema is invalid
    """
    if verbose:
        logger.info("Validating schema file: %s", path)

    try:
        logger.debug("Opening schema file: %s", path)
        with open(path, "r", encoding="utf-8") as f:
            logger.debug("Loading JSON from schema file")
            try:
                schema = json.load(f)
                logger.debug(
                    "Successfully loaded JSON: %s",
                    json.dumps(schema, indent=2),
                )
            except json.JSONDecodeError as e:
                logger.error("JSON decode error in %s: %s", path, str(e))
                logger.debug(
                    "Error details - line: %d, col: %d, msg: %s",
                    e.lineno,
                    e.colno,
                    e.msg,
                )
                raise InvalidJSONError(
                    f"Invalid JSON in schema file {path}: {e}",
                    context={"schema_path": path},
                ) from e
    except FileNotFoundError:
        msg = f"Schema file not found: {path}"
        logger.error(msg)
        raise SchemaFileError(msg, schema_path=path)
    except PermissionError:
        msg = f"Permission denied reading schema file: {path}"
        logger.error(msg)
        raise SchemaFileError(msg, schema_path=path)
    except Exception as e:
        if isinstance(e, (InvalidJSONError, SchemaValidationError)):
            raise
        msg = f"Failed to read schema file {path}: {e}"
        logger.error(msg)
        logger.debug("Unexpected error details: %s", str(e))
        raise SchemaFileError(msg, schema_path=path) from e

    # Pre-validation structure checks
    if verbose:
        logger.info("Performing pre-validation structure checks")
        logger.debug("Loaded schema: %s", json.dumps(schema, indent=2))

    if not isinstance(schema, dict):
        msg = f"Schema in {path} must be a JSON object"
        logger.error(msg)
        raise SchemaValidationError(
            msg,
            context={
                "validation_type": "schema",
                "schema_path": path,
            },
        )

    # Validate schema structure
    if "schema" in schema:
        if verbose:
            logger.debug("Found schema wrapper, validating inner schema")
        inner_schema = schema["schema"]
        if not isinstance(inner_schema, dict):
            msg = f"Inner schema in {path} must be a JSON object"
            logger.error(msg)
            raise SchemaValidationError(
                msg,
                context={
                    "validation_type": "schema",
                    "schema_path": path,
                },
            )
        if verbose:
            logger.debug("Inner schema validated successfully")
            logger.debug("Inner schema: %s", json.dumps(inner_schema, indent=2))
    else:
        if verbose:
            logger.debug("No schema wrapper found, using schema as-is")
            logger.debug("Schema: %s", json.dumps(schema, indent=2))

    # Additional schema validation
    if "type" not in schema.get("schema", schema):
        msg = f"Schema in {path} must specify a type"
        logger.error(msg)
        raise SchemaValidationError(
            msg,
            context={
                "validation_type": "schema",
                "schema_path": path,
            },
        )

    # Validate schema against JSON Schema spec
    try:
        validate_json_schema(schema)
    except SchemaValidationError as e:
        logger.error("Schema validation error: %s", str(e))
        raise  # Re-raise to preserve error chain

    # Return the full schema including wrapper
    return schema


def collect_template_files(
    args: CLIParams,
    security_manager: SecurityManager,
) -> Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]]:
    """Collect files from command line arguments.

    Args:
        args: Command line arguments
        security_manager: Security manager for path validation

    Returns:
        Dictionary mapping variable names to file info objects

    Raises:
        PathSecurityError: If any file paths violate security constraints
        ValueError: If file mappings are invalid or files cannot be accessed
    """
    try:
        # Get files, directories, and patterns from args - they are already tuples from Click's nargs=2
        files = list(args.get("files", []))  # List of (name, path) tuples from Click
        dirs = args.get("dir", [])  # List of (name, dir) tuples from Click
        patterns = args.get("patterns", [])  # List of (name, pattern) tuples from Click

        # Collect files from directories and patterns
        dir_files = collect_files(
            file_mappings=cast(List[Tuple[str, Union[str, Path]]], files),
            dir_mappings=cast(List[Tuple[str, Union[str, Path]]], dirs),
            pattern_mappings=cast(List[Tuple[str, Union[str, Path]]], patterns),
            dir_recursive=args.get("recursive", False),
            security_manager=security_manager,
        )

        # Combine results
        return cast(
            Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]],
            dir_files,
        )
    except PathSecurityError:
        # Let PathSecurityError propagate without wrapping
        raise
    except (FileNotFoundError, DirectoryNotFoundError) as e:
        # Convert FileNotFoundError to OstructFileNotFoundError
        if isinstance(e, FileNotFoundError):
            raise OstructFileNotFoundError(str(e))
        # Let DirectoryNotFoundError propagate
        raise
    except Exception as e:
        # Don't wrap InvalidJSONError
        if isinstance(e, InvalidJSONError):
            raise
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            raise e.__cause__
        # Wrap other errors
        raise ValueError(f"Error collecting files: {e}")


def collect_simple_variables(args: CLIParams) -> Dict[str, str]:
    """Collect simple string variables from --var arguments.

    Args:
        args: Command line arguments

    Returns:
        Dictionary mapping variable names to string values

    Raises:
        VariableNameError: If a variable name is invalid or duplicate
    """
    variables: Dict[str, str] = {}
    all_names: Set[str] = set()

    if args.get("var"):
        for mapping in args["var"]:
            try:
                # Handle both tuple format and string format
                if isinstance(mapping, tuple):
                    name, value = mapping
                else:
                    name, value = mapping.split("=", 1)

                if not name.isidentifier():
                    raise VariableNameError(f"Invalid variable name: {name}")
                if name in all_names:
                    raise VariableNameError(f"Duplicate variable name: {name}")
                variables[name] = value
                all_names.add(name)
            except ValueError:
                raise VariableNameError(
                    f"Invalid variable mapping (expected name=value format): {mapping!r}"
                )

    return variables


def collect_json_variables(args: CLIParams) -> Dict[str, Any]:
    """Collect JSON variables from --json-var arguments.

    Args:
        args: Command line arguments

    Returns:
        Dictionary mapping variable names to parsed JSON values

    Raises:
        VariableNameError: If a variable name is invalid or duplicate
        InvalidJSONError: If a JSON value is invalid
    """
    variables: Dict[str, Any] = {}
    all_names: Set[str] = set()

    if args.get("json_var"):
        for mapping in args["json_var"]:
            try:
                # Handle both tuple format and string format
                if isinstance(mapping, tuple):
                    name, value = mapping  # Value is already parsed by Click validator
                else:
                    try:
                        name, json_str = mapping.split("=", 1)
                    except ValueError:
                        raise VariableNameError(
                            f"Invalid JSON variable mapping format: {mapping}. Expected name=json"
                        )
                    try:
                        value = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        raise InvalidJSONError(
                            f"Invalid JSON value for variable '{name}': {json_str}",
                            context={"variable_name": name},
                        ) from e

                if not name.isidentifier():
                    raise VariableNameError(f"Invalid variable name: {name}")
                if name in all_names:
                    raise VariableNameError(f"Duplicate variable name: {name}")

                variables[name] = value
                all_names.add(name)
            except (VariableNameError, InvalidJSONError):
                raise

    return variables


async def create_template_context_from_args(
    args: CLIParams,
    security_manager: SecurityManager,
) -> Dict[str, Any]:
    """Create template context from command line arguments.

    Args:
        args: Command line arguments
        security_manager: Security manager for path validation

    Returns:
        Template context dictionary

    Raises:
        PathSecurityError: If any file paths violate security constraints
        VariableError: If variable mappings are invalid
        ValueError: If file mappings are invalid or files cannot be accessed
    """
    try:
        # Collect files from arguments
        files = collect_template_files(args, security_manager)

        # Collect simple variables
        variables = collect_simple_variables(args)

        # Collect JSON variables
        json_variables = collect_json_variables(args)

        # Get stdin content if available
        stdin_content = None
        try:
            if not sys.stdin.isatty():
                stdin_content = sys.stdin.read()
        except (OSError, IOError):
            # Skip stdin if it can't be read
            pass

        context = create_template_context(
            files=files,
            variables=variables,
            json_variables=json_variables,
            security_manager=security_manager,
            stdin_content=stdin_content,
        )

        # Add current model to context
        context["current_model"] = args["model"]

        return context

    except PathSecurityError:
        # Let PathSecurityError propagate without wrapping
        raise
    except (FileNotFoundError, DirectoryNotFoundError) as e:
        # Convert FileNotFoundError to OstructFileNotFoundError
        if isinstance(e, FileNotFoundError):
            raise OstructFileNotFoundError(str(e))
        # Let DirectoryNotFoundError propagate
        raise
    except Exception as e:
        # Don't wrap InvalidJSONError
        if isinstance(e, InvalidJSONError):
            raise
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            raise e.__cause__
        # Wrap other errors
        raise ValueError(f"Error collecting files: {e}")


async def create_template_context_from_routing(
    args: CLIParams,
    security_manager: SecurityManager,
    routing_result: Any,  # ProcessingResult from explicit_file_processor
) -> Dict[str, Any]:
    """Create template context from explicit file routing result.

    Args:
        args: Command line arguments
        security_manager: Security manager for path validation
        routing_result: Result from explicit file processor

    Returns:
        Template context dictionary

    Raises:
        PathSecurityError: If any file paths violate security constraints
        VariableError: If variable mappings are invalid
        ValueError: If file mappings are invalid or files cannot be accessed
    """
    try:
        # Get files from routing result - include ALL routed files in template context
        template_files = routing_result.validated_files.get("template", [])
        code_interpreter_files = routing_result.validated_files.get(
            "code-interpreter", []
        )
        file_search_files = routing_result.validated_files.get("file-search", [])

        # Convert to the format expected by create_template_context
        # For legacy compatibility, we need (name, path) tuples
        files_tuples = []
        seen_files = set()  # Track files to avoid duplicates

        # Add template files - handle both auto-naming and custom naming
        template_file_tuples = args.get("template_files", [])
        for name_path_tuple in template_file_tuples:
            if isinstance(name_path_tuple, tuple):
                custom_name, file_path = name_path_tuple
                file_path = str(file_path)

                if custom_name is None:
                    # Auto-generate name for single-arg form: -ft config.yaml
                    file_name = _generate_template_variable_name(file_path)
                else:
                    # Use custom name for two-arg form: -ft code_file src/main.py
                    file_name = custom_name

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Add template file aliases (from --fta)
        template_file_aliases = args.get("template_file_aliases", [])
        for name_path_tuple in template_file_aliases:
            if isinstance(name_path_tuple, tuple):
                custom_name, file_path = name_path_tuple
                file_path = str(file_path)
                file_name = custom_name  # Always use custom name for aliases

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Also process template_files from routing result (for compatibility)
        for file_path in template_files:
            file_name = _generate_template_variable_name(file_path)
            if file_path not in seen_files:
                files_tuples.append((file_name, file_path))
                seen_files.add(file_path)

        # Add code interpreter files - handle both auto-naming and custom naming
        code_interpreter_file_tuples = args.get("code_interpreter_files", [])
        for name_path_tuple in code_interpreter_file_tuples:
            if isinstance(name_path_tuple, tuple):
                custom_name, file_path = name_path_tuple
                file_path = str(file_path)

                if custom_name is None:
                    # Auto-generate name: -fc data.csv
                    file_name = _generate_template_variable_name(file_path)
                else:
                    # Use custom name: -fc dataset data.csv
                    file_name = custom_name

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Add code interpreter file aliases (from --fca)
        code_interpreter_file_aliases = args.get("code_interpreter_file_aliases", [])
        for name_path_tuple in code_interpreter_file_aliases:
            if isinstance(name_path_tuple, tuple):
                custom_name, file_path = name_path_tuple
                file_path = str(file_path)
                file_name = custom_name  # Always use custom name for aliases

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Also process code_interpreter_files from routing result (for compatibility)
        for file_path in code_interpreter_files:
            file_name = _generate_template_variable_name(file_path)
            if file_path not in seen_files:
                files_tuples.append((file_name, file_path))
                seen_files.add(file_path)

        # Add file search files - handle both auto-naming and custom naming
        file_search_file_tuples = args.get("file_search_files", [])
        for name_path_tuple in file_search_file_tuples:
            if isinstance(name_path_tuple, tuple):
                custom_name, file_path = name_path_tuple
                file_path = str(file_path)

                if custom_name is None:
                    # Auto-generate name: -fs docs.pdf
                    file_name = _generate_template_variable_name(file_path)
                else:
                    # Use custom name: -fs manual docs.pdf
                    file_name = custom_name

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Add file search file aliases (from --fsa)
        file_search_file_aliases = args.get("file_search_file_aliases", [])
        for name_path_tuple in file_search_file_aliases:
            if isinstance(name_path_tuple, tuple):
                custom_name, file_path = name_path_tuple
                file_path = str(file_path)
                file_name = custom_name  # Always use custom name for aliases

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Also process file_search_files from routing result (for compatibility)
        for file_path in file_search_files:
            file_name = _generate_template_variable_name(file_path)
            if file_path not in seen_files:
                files_tuples.append((file_name, file_path))
                seen_files.add(file_path)

        # Process files from explicit routing
        files_dict = collect_files(
            file_mappings=files_tuples,
            security_manager=security_manager,
        )

        # Handle legacy files and directories separately to preserve variable names
        legacy_files = args.get("files", [])
        legacy_dirs = args.get("dir", [])
        legacy_patterns = args.get("patterns", [])

        if legacy_files or legacy_dirs or legacy_patterns:
            legacy_files_dict = collect_files(
                file_mappings=legacy_files,
                dir_mappings=legacy_dirs,
                pattern_mappings=legacy_patterns,
                dir_recursive=args.get("recursive", False),
                security_manager=security_manager,
            )
            # Merge legacy results into the main template context
            files_dict.update(legacy_files_dict)

        # Collect simple variables
        variables = collect_simple_variables(args)

        # Collect JSON variables
        json_variables = collect_json_variables(args)

        # Get stdin content if available
        stdin_content = None
        try:
            if not sys.stdin.isatty():
                stdin_content = sys.stdin.read()
        except (OSError, IOError):
            # Skip stdin if it can't be read
            pass

        context = create_template_context(
            files=files_dict,
            variables=variables,
            json_variables=json_variables,
            security_manager=security_manager,
            stdin_content=stdin_content,
        )

        # Add current model to context
        context["current_model"] = args["model"]

        return context

    except PathSecurityError:
        # Let PathSecurityError propagate without wrapping
        raise
    except (FileNotFoundError, DirectoryNotFoundError) as e:
        # Convert FileNotFoundError to OstructFileNotFoundError
        if isinstance(e, FileNotFoundError):
            raise OstructFileNotFoundError(str(e))
        # Let DirectoryNotFoundError propagate
        raise
    except Exception as e:
        # Don't wrap InvalidJSONError
        if isinstance(e, InvalidJSONError):
            raise
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            raise e.__cause__
        # Wrap other errors
        raise ValueError(f"Error collecting files: {e}")


def validate_security_manager(
    base_dir: Optional[str] = None,
    allowed_dirs: Optional[List[str]] = None,
    allowed_dir_file: Optional[str] = None,
) -> SecurityManager:
    """Validate and create security manager.

    Args:
        base_dir: Base directory for file access. Defaults to current working directory.
        allowed_dirs: Optional list of additional allowed directories
        allowed_dir_file: Optional file containing allowed directories

    Returns:
        Configured SecurityManager instance

    Raises:
        PathSecurityError: If any paths violate security constraints
        DirectoryNotFoundError: If any directories do not exist
    """
    # Use current working directory if base_dir is None
    if base_dir is None:
        base_dir = os.getcwd()

    # Create security manager with base directory
    security_manager = SecurityManager(base_dir)

    # Add explicitly allowed directories
    if allowed_dirs:
        for dir_path in allowed_dirs:
            security_manager.add_allowed_directory(dir_path)

    # Add directories from file if specified
    if allowed_dir_file:
        try:
            with open(allowed_dir_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        security_manager.add_allowed_directory(line)
        except OSError as e:
            raise DirectoryNotFoundError(
                f"Failed to read allowed directories file: {e}"
            )

    return security_manager


def parse_var(var_str: str) -> Tuple[str, str]:
    """Parse a simple variable string in the format 'name=value'.

    Args:
        var_str: Variable string in format 'name=value'

    Returns:
        Tuple of (name, value)

    Raises:
        VariableNameError: If variable name is empty or invalid
        VariableValueError: If variable format is invalid
    """
    try:
        name, value = var_str.split("=", 1)
        if not name:
            raise VariableNameError("Empty name in variable mapping")
        if not name.isidentifier():
            raise VariableNameError(
                f"Invalid variable name: {name}. Must be a valid Python identifier"
            )
        return name, value
    except ValueError as e:
        if "not enough values to unpack" in str(e):
            raise VariableValueError(
                f"Invalid variable mapping (expected name=value format): {var_str!r}"
            )
        raise


def parse_json_var(var_str: str) -> Tuple[str, Any]:
    """Parse a JSON variable string in the format 'name=json_value'.

    Args:
        var_str: Variable string in format 'name=json_value'

    Returns:
        Tuple of (name, parsed_value)

    Raises:
        VariableNameError: If variable name is empty or invalid
        VariableValueError: If variable format is invalid
        InvalidJSONError: If JSON value is invalid
    """
    try:
        name, json_str = var_str.split("=", 1)
        if not name:
            raise VariableNameError("Empty name in JSON variable mapping")
        if not name.isidentifier():
            raise VariableNameError(
                f"Invalid variable name: {name}. Must be a valid Python identifier"
            )

        try:
            value = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise InvalidJSONError(
                f"Error parsing JSON for variable '{name}': {str(e)}. Input was: {json_str}",
                context={"variable_name": name},
            )

        return name, value

    except ValueError as e:
        if "not enough values to unpack" in str(e):
            raise VariableValueError(
                f"Invalid JSON variable mapping (expected name=json format): {var_str!r}"
            )
        raise


def handle_error(e: Exception) -> None:
    """Handle CLI errors and display appropriate messages.

    Maintains specific error type handling while reducing duplication.
    Provides enhanced debug logging for CLI errors.
    """
    # 1. Determine error type and message
    if isinstance(e, SchemaValidationError):
        msg = str(e)  # Already formatted in SchemaValidationError
        exit_code = e.exit_code
    elif isinstance(e, ModelCreationError):
        # Unwrap ModelCreationError that might wrap SchemaValidationError
        if isinstance(e.__cause__, SchemaValidationError):
            return handle_error(e.__cause__)
        msg = f"Model creation error: {str(e)}"
        exit_code = ExitCode.SCHEMA_ERROR
    elif isinstance(e, click.UsageError):
        msg = f"Usage error: {str(e)}"
        exit_code = ExitCode.USAGE_ERROR
    elif isinstance(e, SchemaFileError):
        msg = str(e)  # Use existing __str__ formatting
        exit_code = ExitCode.SCHEMA_ERROR
    elif isinstance(e, (InvalidJSONError, json.JSONDecodeError)):
        msg = f"Invalid JSON error: {str(e)}"
        exit_code = ExitCode.DATA_ERROR
    elif isinstance(e, CLIError):
        msg = str(e)  # Use existing __str__ formatting
        exit_code = ExitCode(e.exit_code)  # Convert int to ExitCode
    else:
        msg = f"Unexpected error: {str(e)}"
        exit_code = ExitCode.INTERNAL_ERROR

    # 2. Debug logging
    if isinstance(e, CLIError) and logger.isEnabledFor(logging.DEBUG):
        # Format context fields with lowercase keys and simple values
        context_str = ""
        if hasattr(e, "context") and e.context:
            for key, value in sorted(e.context.items()):
                if key not in {
                    "timestamp",
                    "host",
                    "version",
                    "python_version",
                }:
                    if isinstance(value, dict):
                        context_str += (
                            f"{key.lower()}:\n{json.dumps(value, indent=2)}\n"
                        )
                    else:
                        context_str += f"{key.lower()}: {value}\n"

            logger.debug(
                f"Error details:\nType: {type(e).__name__}\n{context_str.rstrip()}"
            )
    elif not isinstance(e, click.UsageError):
        logger.error(msg, exc_info=True)
    else:
        logger.error(msg)

    # 3. User output
    click.secho(msg, fg="red", err=True)
    sys.exit(exit_code)


def validate_model_parameters(model: str, params: Dict[str, Any]) -> None:
    """Validate model parameters against model capabilities.

    Args:
        model: The model name to validate parameters for
        params: Dictionary of parameter names and values to validate

    Raises:
        CLIError: If any parameters are not supported by the model
    """
    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)
        # This will now raise ModelNotSupportedError for invalid models
        for param_name, value in params.items():
            capabilities.validate_parameter(param_name, value)
    except (ModelNotSupportedError, ModelVersionError) as e:
        # Convert to internal CLIError with helpful message
        logger.error("Model validation failed: %s", str(e))
        raise CLIError(
            f"Model validation failed: {str(e)}",
            exit_code=ExitCode.VALIDATION_ERROR,
            context={"model": model},
        )
    except (
        ParameterNotSupportedError,
        ParameterValidationError,
        ModelRegistryError,
        ValueError,
    ) as e:
        # Handle parameter-specific errors
        raise CLIError(
            str(e),
            exit_code=ExitCode.VALIDATION_ERROR,
            context={"model": model},
        )


async def stream_structured_output(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    output_schema: Type[BaseModel],
    output_file: Optional[str] = None,
    tools: Optional[List[dict]] = None,
    **kwargs: Any,
) -> AsyncGenerator[BaseModel, None]:
    """Stream structured output from OpenAI API using Responses API.

    This function uses the OpenAI Responses API with strict mode schema validation
    to generate structured output that matches the provided Pydantic model.

    Args:
        client: The OpenAI client to use
        model: The model to use
        system_prompt: The system prompt to use
        user_prompt: The user prompt to use
        output_schema: The Pydantic model to validate responses against
        output_file: Optional file to write output to
        tools: Optional list of tools (e.g., MCP, Code Interpreter) to include
        **kwargs: Additional parameters to pass to the API

    Returns:
        An async generator yielding validated model instances

    Raises:
        ValueError: If the model does not support structured output or parameters are invalid
        StreamInterruptedError: If the stream is interrupted
        APIResponseError: If there is an API error
    """
    try:
        # Check if model supports structured output using our stub function
        if not supports_structured_output(model):
            raise ValueError(
                f"Model {model} does not support structured output with json_schema response format. "
                "Please use a model that supports structured output."
            )

        # Extract non-model parameters
        on_log = kwargs.pop("on_log", None)

        # Handle model-specific parameters
        stream_kwargs = {}
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)

        # Validate and include supported parameters
        for param_name, value in kwargs.items():
            if param_name in capabilities.supported_parameters:
                # Validate the parameter value
                capabilities.validate_parameter(param_name, value)
                stream_kwargs[param_name] = value
            else:
                logger.warning(
                    f"Parameter {param_name} is not supported by model {model} and will be ignored"
                )

        # Prepare schema for strict mode
        schema = output_schema.model_json_schema()
        strict_schema = copy.deepcopy(schema)
        make_strict(strict_schema)

        # Generate schema name from model class name
        schema_name = output_schema.__name__.lower()

        # Combine system and user prompts into a single input string
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Prepare API call parameters
        api_params = {
            "model": model,
            "input": combined_prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": strict_schema,
                    "strict": True,
                }
            },
            "stream": True,
            **stream_kwargs,
        }

        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            logger.debug("Tools: %s", json.dumps(tools, indent=2))

        # Log the API request details
        logger.debug("Making OpenAI Responses API request with:")
        logger.debug("Model: %s", model)
        logger.debug("Combined prompt: %s", combined_prompt)
        logger.debug("Parameters: %s", json.dumps(stream_kwargs, indent=2))
        logger.debug("Schema: %s", json.dumps(strict_schema, indent=2))

        # Use the Responses API with streaming
        response = await client.responses.create(**api_params)

        # Process streaming response
        accumulated_content = ""
        async for chunk in response:
            if on_log:
                on_log(logging.DEBUG, f"Received chunk: {chunk}", {})

            # Handle different response formats based on the chunk structure
            content_added = False

            # Try different possible response formats
            if hasattr(chunk, "choices") and chunk.choices:
                # Standard chat completion format
                choice = chunk.choices[0]
                if (
                    hasattr(choice, "delta")
                    and hasattr(choice.delta, "content")
                    and choice.delta.content
                ):
                    accumulated_content += choice.delta.content
                    content_added = True
                elif (
                    hasattr(choice, "message")
                    and hasattr(choice.message, "content")
                    and choice.message.content
                ):
                    accumulated_content += choice.message.content
                    content_added = True
            elif hasattr(chunk, "response") and hasattr(chunk.response, "body"):
                # Responses API format
                accumulated_content += chunk.response.body
                content_added = True
            elif hasattr(chunk, "content"):
                # Direct content
                accumulated_content += chunk.content
                content_added = True
            elif hasattr(chunk, "text"):
                # Text content
                accumulated_content += chunk.text
                content_added = True

            if on_log and content_added:
                on_log(
                    logging.DEBUG,
                    f"Added content, total length: {len(accumulated_content)}",
                    {},
                )

            # Try to parse and validate accumulated content as complete JSON
            try:
                if accumulated_content.strip():
                    # Attempt to parse as complete JSON
                    data = json.loads(accumulated_content.strip())
                    validated = output_schema.model_validate(data)
                    yield validated
                    # Reset for next complete response (if any)
                    accumulated_content = ""
            except (json.JSONDecodeError, ValueError):
                # Not yet complete JSON, continue accumulating
                continue

        # Handle any remaining content
        if accumulated_content.strip():
            try:
                data = json.loads(accumulated_content.strip())
                validated = output_schema.model_validate(data)
                yield validated
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse final accumulated content: {e}")
                raise StreamParseError(f"Failed to parse response as valid JSON: {e}")

    except Exception as e:
        # Map OpenAI errors using the error mapper (T3.1)
        from openai import OpenAIError

        if isinstance(e, OpenAIError):
            mapped_error = APIErrorMapper.map_openai_error(e)
            logger.error(f"OpenAI API error mapped: {mapped_error}")
            raise mapped_error

        # Handle special schema array error with detailed guidance
        if "Invalid schema for response_format" in str(e) and 'type: "array"' in str(e):
            error_msg = (
                "OpenAI API Schema Error: The schema must have a root type of 'object', not 'array'. "
                "To fix this:\n"
                "1. Wrap your array in an object property, e.g.:\n"
                "   {\n"
                '     "type": "object",\n'
                '     "properties": {\n'
                '       "items": {\n'
                '         "type": "array",\n'
                '         "items": { ... your array items schema ... }\n'
                "       }\n"
                "     }\n"
                "   }\n"
                "2. Make sure to update your template to handle the wrapper object."
            )
            logger.error(error_msg)
            raise InvalidResponseFormatError(error_msg)

        # For non-OpenAI errors, try to map them as well
        error_msg = str(e).lower()
        if (
            "context_length_exceeded" in error_msg
            or "maximum context length" in error_msg
        ):
            mapped_error = APIErrorMapper.map_openai_error(e)
            logger.error(f"Context length error mapped: {mapped_error}")
            raise mapped_error
        elif "rate_limit" in error_msg or "429" in str(e):
            mapped_error = APIErrorMapper.map_openai_error(e)
            logger.error(f"Rate limit error mapped: {mapped_error}")
            raise mapped_error
        elif "invalid_api_key" in error_msg:
            mapped_error = APIErrorMapper.map_openai_error(e)
            logger.error(f"Authentication error mapped: {mapped_error}")
            raise mapped_error
        else:
            logger.error(f"Unmapped API error: {e}")
            raise APIResponseError(str(e))
    finally:
        # Note: We don't close the client here as it may be reused
        # The caller is responsible for client lifecycle management
        pass


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Configuration file path (default: ostruct.yaml)",
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[str] = None) -> None:
    """ostruct - AI-powered structured output with multi-tool integration.

    ostruct transforms unstructured inputs into structured JSON using OpenAI APIs,
    Jinja2 templates, and powerful tool integrations including Code Interpreter,
    File Search, and MCP servers.

    🚀 QUICK START:
        ostruct run template.j2 schema.json -V name=value

    📁 FILE ROUTING (explicit tool assignment):
        -ft/--file-for-template          Template access only
        -fc/--file-for-code-interpreter  Code execution & analysis
        -fs/--file-for-file-search       Document search & retrieval

    ⚡ EXAMPLES:
        # Basic usage (unchanged)
        ostruct run template.j2 schema.json -f config.yaml

        # Multi-tool explicit routing
        ostruct run analysis.j2 schema.json -fc data.csv -fs docs.pdf -ft config.yaml

        # Advanced routing with --file-for
        ostruct run task.j2 schema.json --file-for code-interpreter shared.json --file-for file-search shared.json

        # MCP server integration
        ostruct run template.j2 schema.json --mcp-server deepwiki@https://mcp.deepwiki.com/sse

    📖 For detailed documentation: https://ostruct.readthedocs.io
    """
    # Load configuration
    try:
        app_config = OstructConfig.load(config)
        ctx.ensure_object(dict)
        ctx.obj["config"] = app_config
    except Exception as e:
        click.secho(
            f"Warning: Failed to load configuration: {e}",
            fg="yellow",
            err=True,
        )
        # Use default configuration
        ctx.ensure_object(dict)
        ctx.obj["config"] = OstructConfig()

    # Check for registry updates in a non-intrusive way
    try:
        update_message = get_update_notification()
        if update_message:
            click.secho(f"Note: {update_message}", fg="blue", err=True)
    except Exception:
        # Ensure any errors don't affect normal operation
        pass


@cli.command()
@click.argument("task_template", type=click.Path(exists=True))
@click.argument("schema_file", type=click.Path(exists=True))
@all_options  # type: ignore[misc]
@click.pass_context
def run(
    ctx: click.Context,
    task_template: str,
    schema_file: str,
    **kwargs: Any,
) -> None:
    """Run structured output generation with multi-tool integration.

    \b
    📁 FILE ROUTING OPTIONS:

    Template Access Only:
      -ft, --file-for-template FILE     Files available in template only
      -dt, --dir-for-template DIR       Directories for template access

    Code Interpreter (execution & analysis):
      -fc, --file-for-code-interpreter FILE    Upload files for code execution
      -dc, --dir-for-code-interpreter DIR      Upload directories for analysis

    File Search (document retrieval):
      -fs, --file-for-file-search FILE         Upload files for vector search
      -ds, --dir-for-search DIR                Upload directories for search

    Advanced Routing:
      --file-for TOOL PATH              Route files to specific tools
                                        Example: --file-for code-interpreter data.json

    \b
    🔧 TOOL INTEGRATION:

    MCP Servers:
      --mcp-server [LABEL@]URL          Connect to MCP server
                                        Example: --mcp-server deepwiki@https://mcp.deepwiki.com/sse

    \b
    ⚡ EXAMPLES:

    Basic usage:
      ostruct run template.j2 schema.json -V name=value

    Multi-tool explicit routing:
      ostruct run analysis.j2 schema.json -fc data.csv -fs docs.pdf -ft config.yaml

    Legacy compatibility (still works):
      ostruct run template.j2 schema.json -f config main.py -d src ./src

    \b
    Arguments:
      TASK_TEMPLATE  Path to Jinja2 template file
      SCHEMA_FILE    Path to JSON schema file defining output structure
    """
    try:
        # Convert Click parameters to typed dict
        params: CLIParams = {
            "task_file": task_template,
            "task": None,
            "schema_file": schema_file,
        }
        # Add only valid keys from kwargs
        valid_keys = set(CLIParams.__annotations__.keys())
        for k, v in kwargs.items():
            if k in valid_keys:
                params[k] = v  # type: ignore[literal-required]

        # Apply configuration defaults if values not explicitly provided
        # Check for command-level config option first, then group-level
        command_config = kwargs.get("config")
        if command_config:
            config = OstructConfig.load(command_config)
        else:
            config = ctx.obj.get("config") if ctx.obj else OstructConfig()

        if params.get("model") is None:
            params["model"] = config.get_model_default()  # type: ignore[literal-required]

        # Run the async function synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            exit_code = loop.run_until_complete(run_cli_async(params))
            sys.exit(int(exit_code))
        except SchemaValidationError as e:
            # Log the error with full context
            logger.error("Schema validation error: %s", str(e))
            if e.context:
                logger.debug("Error context: %s", json.dumps(e.context, indent=2))
            # Re-raise to preserve error chain and exit code
            raise
        except (CLIError, InvalidJSONError, SchemaFileError) as e:
            handle_error(e)
            sys.exit(
                e.exit_code if hasattr(e, "exit_code") else ExitCode.INTERNAL_ERROR
            )
        except click.UsageError as e:
            handle_error(e)
            sys.exit(ExitCode.USAGE_ERROR)
        except Exception as e:
            handle_error(e)
            sys.exit(ExitCode.INTERNAL_ERROR)
        finally:
            loop.close()
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        raise


@cli.command("quick-ref")
def quick_reference() -> None:
    """Show quick reference for file routing and common usage patterns."""
    quick_ref = """
🚀 OSTRUCT QUICK REFERENCE

📁 FILE ROUTING:
  -ft FILE    📄 Template access only       (config files, small data)
  -fc FILE    💻 Code Interpreter upload    (data files, scripts)
  -fs FILE    🔍 File Search vector store   (documents, manuals)

  -dt DIR     📁 Template directory         (config dirs, reference data)
  -dc DIR     📂 Code execution directory   (datasets, code repos)
  -ds DIR     📁 Search directory           (documentation, knowledge)

🔄 ADVANCED ROUTING:
  --file-for code-interpreter data.csv      Single tool, single file
  --file-for file-search docs.pdf           Single tool, single file
  --file-for code-interpreter shared.json --file-for file-search shared.json   Multi-tool routing

🏷️  VARIABLES:
  -V name=value                             Simple string variables
  -J config='{"key":"value"}'               JSON structured data

🔌 TOOLS:
  --mcp-server label@https://server.com/sse MCP server integration
  --timeout 7200                           2-hour timeout for long operations

⚡ COMMON PATTERNS:
  # Basic template rendering
  ostruct run template.j2 schema.json -V env=prod

  # Data analysis with Code Interpreter
  ostruct run analysis.j2 schema.json -fc data.csv -V task=analyze

  # Document search + processing
  ostruct run search.j2 schema.json -fs docs/ -ft config.yaml

  # Multi-tool workflow
  ostruct run workflow.j2 schema.json -fc raw_data.csv -fs knowledge/ -ft config.json

📖 Full help: ostruct run --help
📖 Documentation: https://ostruct.readthedocs.io
"""
    click.echo(quick_ref)


@cli.command("update-registry")
@click.option(
    "--url",
    help="URL to fetch the registry from. Defaults to official repository.",
    default=None,
)
@click.option(
    "--force",
    is_flag=True,
    help="Force update even if the registry is already up to date.",
    default=False,
)
def update_registry(url: Optional[str] = None, force: bool = False) -> None:
    """Update the model registry with the latest model definitions.

    This command fetches the latest model registry from the official repository
    or a custom URL if provided, and updates the local registry file.

    Example:
        ostruct update-registry
        ostruct update-registry --url https://example.com/models.yml
    """
    try:
        registry = ModelRegistry.get_instance()

        # Show current registry config path
        config_path = registry.config.registry_path
        click.echo(f"Current registry file: {config_path}")

        if force:
            click.echo("🔄 Forcing registry update...")
            refresh_result = registry.refresh_from_remote(url)
            if refresh_result.success:
                click.echo("✅ Registry successfully updated!")
            else:
                click.echo(f"❌ Failed to update registry: {refresh_result.message}")
            return

        click.echo("🔍 Checking for registry updates...")
        update_result = registry.check_for_updates()

        if update_result.status.value == "update_available":
            click.echo(f"📦 Update available: {update_result.message}")
            click.echo("🔄 Updating registry...")
            refresh_result = registry.refresh_from_remote(url)
            if refresh_result.success:
                click.echo("✅ Registry successfully updated!")
            else:
                click.echo(f"❌ Failed to update registry: {refresh_result.message}")
        elif update_result.status.value == "already_current":
            click.echo("✅ Registry is already up to date")
        else:
            click.echo(f"⚠️ Registry check failed: {update_result.message}")
    except Exception as e:
        click.echo(f"❌ Error updating registry: {str(e)}")
        sys.exit(ExitCode.API_ERROR.value)


@cli.command("list-models")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "simple"]),
    default="table",
    help="Output format for model list",
)
@click.option(
    "--show-deprecated",
    is_flag=True,
    help="Include deprecated models in output",
)
def list_models(format: str = "table", show_deprecated: bool = False) -> None:
    """List available models from the registry."""
    try:
        registry = ModelRegistry.get_instance()
        models = registry.models

        # Filter models if not showing deprecated
        if not show_deprecated:
            # Filter out deprecated models (this depends on registry implementation)
            filtered_models = []
            for model_id in models:
                try:
                    capabilities = registry.get_capabilities(model_id)
                    # If we can get capabilities, it's likely not deprecated
                    filtered_models.append(
                        {
                            "id": model_id,
                            "context_window": capabilities.context_window,
                            "max_output": capabilities.max_output_tokens,
                        }
                    )
                except Exception:
                    # Skip models that can't be accessed (likely deprecated)
                    continue
            models_data = filtered_models
        else:
            # Include all models
            models_data = []
            for model_id in models:
                try:
                    capabilities = registry.get_capabilities(model_id)
                    models_data.append(
                        {
                            "id": model_id,
                            "context_window": capabilities.context_window,
                            "max_output": capabilities.max_output_tokens,
                            "status": "active",
                        }
                    )
                except Exception:
                    models_data.append(
                        {
                            "id": model_id,
                            "context_window": "N/A",
                            "max_output": "N/A",
                            "status": "deprecated",
                        }
                    )

        if format == "table":
            # Calculate dynamic column widths based on actual data
            max_id_width = (
                max(len(model["id"]) for model in models_data) if models_data else 8
            )
            max_id_width = max(max_id_width, len("Model ID"))

            max_context_width = 15  # Keep reasonable default for context window
            max_output_width = 12  # Keep reasonable default for max output
            status_width = 10  # Keep fixed for status

            # Ensure minimum widths for readability
            id_width = max(max_id_width, 8)

            total_width = (
                id_width + max_context_width + max_output_width + status_width + 6
            )  # 6 for spacing

            click.echo("Available Models:")
            click.echo("-" * total_width)
            click.echo(
                f"{'Model ID':<{id_width}} {'Context Window':<{max_context_width}} {'Max Output':<{max_output_width}} {'Status':<{status_width}}"
            )
            click.echo("-" * total_width)
            for model in models_data:
                status = model.get("status", "active")
                context = (
                    f"{model['context_window']:,}"
                    if isinstance(model["context_window"], int)
                    else model["context_window"]
                )
                output = (
                    f"{model['max_output']:,}"
                    if isinstance(model["max_output"], int)
                    else model["max_output"]
                )
                click.echo(
                    f"{model['id']:<{id_width}} {context:<{max_context_width}} {output:<{max_output_width}} {status:<{status_width}}"
                )
        elif format == "json":
            import json

            click.echo(json.dumps(models_data, indent=2))
        else:  # simple
            for model in models_data:
                click.echo(model["id"])

    except Exception as e:
        click.echo(f"❌ Error listing models: {str(e)}")
        sys.exit(ExitCode.API_ERROR.value)


async def validate_model_params(args: CLIParams) -> Dict[str, Any]:
    """Validate model parameters and return a dictionary of valid parameters.

    Args:
        args: Command line arguments

    Returns:
        Dictionary of validated model parameters

    Raises:
        CLIError: If model parameters are invalid
    """
    params = {
        "temperature": args.get("temperature"),
        "max_output_tokens": args.get("max_output_tokens"),
        "top_p": args.get("top_p"),
        "frequency_penalty": args.get("frequency_penalty"),
        "presence_penalty": args.get("presence_penalty"),
        "reasoning_effort": args.get("reasoning_effort"),
    }
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    validate_model_parameters(args["model"], params)
    return params


async def validate_inputs(
    args: CLIParams,
) -> Tuple[
    SecurityManager,
    str,
    Dict[str, Any],
    Dict[str, Any],
    jinja2.Environment,
    Optional[str],
]:
    """Validate all input parameters and return validated components.

    Args:
        args: Command line arguments

    Returns:
        Tuple containing:
        - SecurityManager instance
        - Task template string
        - Schema dictionary
        - Template context dictionary
        - Jinja2 environment
        - Template file path (if from file)

    Raises:
        CLIError: For various validation errors
        SchemaValidationError: When schema is invalid
    """
    logger.debug("=== Input Validation Phase ===")
    security_manager = validate_security_manager(
        base_dir=args.get("base_dir"),
        allowed_dirs=args.get("allowed_dirs"),
        allowed_dir_file=args.get("allowed_dir_file"),
    )

    # Process explicit file routing (T2.4)
    logger.debug("Processing explicit file routing")
    file_processor = ExplicitFileProcessor(security_manager)
    routing_result = await file_processor.process_file_routing(args)

    # Display auto-enablement feedback to user
    if routing_result.auto_enabled_feedback:
        print(routing_result.auto_enabled_feedback)

    # Store routing result in args for use by tool processors
    args["_routing_result"] = routing_result  # type: ignore[typeddict-item]

    task_template = validate_task_template(args.get("task"), args.get("task_file"))

    # Load and validate schema
    logger.debug("Validating schema from %s", args["schema_file"])
    try:
        schema = validate_schema_file(args["schema_file"], args.get("verbose", False))

        # Validate schema structure before any model creation
        validate_json_schema(schema)  # This will raise SchemaValidationError if invalid
    except SchemaValidationError as e:
        logger.error("Schema validation error: %s", str(e))
        raise  # Re-raise the SchemaValidationError to preserve the error chain

    template_context = await create_template_context_from_routing(
        args, security_manager, routing_result
    )
    env = create_jinja_env()

    return (
        security_manager,
        task_template,
        schema,
        template_context,
        env,
        args.get("task_file"),
    )


async def process_templates(
    args: CLIParams,
    task_template: str,
    template_context: Dict[str, Any],
    env: jinja2.Environment,
    template_path: Optional[str] = None,
) -> Tuple[str, str]:
    """Process system prompt and user prompt templates.

    Args:
        args: Command line arguments
        task_template: Validated task template
        template_context: Template context dictionary
        env: Jinja2 environment
        template_path: Optional path to template file for include_system resolution

    Returns:
        Tuple of (system_prompt, user_prompt)

    Raises:
        CLIError: For template processing errors
    """
    logger.debug("=== Template Processing Phase ===")
    system_prompt = process_system_prompt(
        task_template,
        args.get("system_prompt"),
        args.get("system_prompt_file"),
        template_context,
        env,
        args.get("ignore_task_sysprompt", False),
        template_path,
    )
    user_prompt = render_template(task_template, template_context, env)
    return system_prompt, user_prompt


def extract_template_file_paths(template_context: Dict[str, Any]) -> List[str]:
    """Extract actual file paths from template context for token validation.

    Args:
        template_context: Template context dictionary containing FileInfoList objects

    Returns:
        List of file paths that were included in template rendering
    """
    file_paths = []

    for key, value in template_context.items():
        if isinstance(value, FileInfoList):
            # Extract paths from FileInfoList
            for file_info in value:
                if hasattr(file_info, "path"):
                    file_paths.append(file_info.path)
        elif key == "stdin":
            # Skip stdin content - it's already counted in template
            continue
        elif key == "current_model":
            # Skip model name
            continue

    return file_paths


async def validate_model_and_schema(
    args: CLIParams,
    schema: Dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    template_context: Dict[str, Any],
) -> Tuple[Type[BaseModel], List[Dict[str, str]], int, ModelRegistry]:
    """Validate model compatibility and schema, and check token limits.

    Args:
        args: Command line arguments
        schema: Schema dictionary
        system_prompt: Processed system prompt
        user_prompt: Processed user prompt
        template_context: Template context with file information

    Returns:
        Tuple of (output_model, messages, total_tokens, registry)

    Raises:
        CLIError: For validation errors
        ModelCreationError: When model creation fails
        SchemaValidationError: When schema is invalid
        PromptTooLargeError: When prompt exceeds context window with actionable guidance
    """
    logger.debug("=== Model & Schema Validation Phase ===")
    try:
        output_model = create_dynamic_model(
            schema,
            show_schema=args.get("show_model_schema", False),
            debug_validation=args.get("debug_validation", False),
        )
        logger.debug("Successfully created output model")
    except (
        SchemaFileError,
        InvalidJSONError,
        SchemaValidationError,
        ModelCreationError,
    ) as e:
        logger.error("Schema error: %s", str(e))
        # Pass through the error without additional wrapping
        raise

    if not supports_structured_output(args["model"]):
        msg = f"Model {args['model']} does not support structured output"
        logger.error(msg)
        raise ModelNotSupportedError(msg)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    total_tokens = estimate_tokens_with_encoding(messages, args["model"])
    registry = ModelRegistry.get_instance()
    capabilities = registry.get_capabilities(args["model"])
    context_limit = capabilities.context_window

    # Enhanced token validation with actionable guidance for file routing
    template_files = extract_template_file_paths(template_context)
    validator = TokenLimitValidator(args["model"])

    # Combine both prompts for total template content validation
    combined_template_content = f"{system_prompt}\n\n{user_prompt}"
    validator.validate_prompt_size(
        combined_template_content, template_files, context_limit
    )

    return output_model, messages, total_tokens, registry


async def process_mcp_configuration(args: CLIParams) -> MCPServerManager:
    """Process MCP configuration from CLI arguments.

    Args:
        args: CLI parameters containing MCP settings

    Returns:
        MCPServerManager: Configured manager ready for tool integration

    Raises:
        CLIError: If MCP configuration is invalid
    """
    logger.debug("=== MCP Configuration Processing ===")

    # Parse MCP servers from CLI arguments
    servers = []
    for server_spec in args.get("mcp_servers", []):
        try:
            # Parse format: [label@]url
            if "@" in server_spec:
                label, url = server_spec.rsplit("@", 1)
            else:
                url = server_spec
                label = None

            server_config = {"url": url}
            if label:
                server_config["label"] = label

            # Add require_approval setting from CLI
            server_config["require_approval"] = args.get(
                "mcp_require_approval", "never"
            )

            # Parse headers if provided
            if args.get("mcp_headers"):
                try:
                    headers = json.loads(args["mcp_headers"])
                    server_config["headers"] = headers
                except json.JSONDecodeError as e:
                    raise CLIError(
                        f"Invalid JSON in --mcp-headers: {e}",
                        exit_code=ExitCode.USAGE_ERROR,
                    )

            servers.append(server_config)

        except Exception as e:
            raise CLIError(
                f"Failed to parse MCP server spec '{server_spec}': {e}",
                exit_code=ExitCode.USAGE_ERROR,
            )

    # Process allowed tools if specified
    allowed_tools_map = {}
    for tools_spec in args.get("mcp_allowed_tools", []):
        try:
            if ":" not in tools_spec:
                raise ValueError("Format should be server_label:tool1,tool2")
            label, tools_str = tools_spec.split(":", 1)
            tools_list = [tool.strip() for tool in tools_str.split(",")]
            allowed_tools_map[label] = tools_list
        except Exception as e:
            raise CLIError(
                f"Failed to parse MCP allowed tools '{tools_spec}': {e}",
                exit_code=ExitCode.USAGE_ERROR,
            )

    # Apply allowed tools to server configurations
    for server in servers:
        server_label = server.get("label")
        if server_label and server_label in allowed_tools_map:
            server["allowed_tools"] = allowed_tools_map[server_label]  # type: ignore[assignment]

    # Create configuration and manager
    config = MCPConfiguration(servers)
    manager = MCPServerManager(config)

    # Pre-validate servers for CLI compatibility
    validation_errors = await manager.pre_validate_all_servers()
    if validation_errors:
        error_msg = "MCP server validation failed:\n" + "\n".join(
            f"- {error}" for error in validation_errors
        )
        # Map as MCP error
        mapped_error = APIErrorMapper.map_tool_error("mcp", Exception(error_msg))
        raise mapped_error

    logger.debug(
        "MCP configuration validated successfully with %d servers",
        len(servers),
    )
    return manager


async def process_code_interpreter_configuration(
    args: CLIParams, client: AsyncOpenAI
) -> Optional[Dict[str, Any]]:
    """Process Code Interpreter configuration from CLI arguments.

    Args:
        args: CLI parameters containing Code Interpreter settings
        client: AsyncOpenAI client for file uploads

    Returns:
        Dictionary with Code Interpreter tool config and manager, or None if no files specified

    Raises:
        CLIError: If Code Interpreter configuration is invalid
    """
    logger.debug("=== Code Interpreter Configuration Processing ===")

    # Collect all files to upload
    files_to_upload = []

    # Add individual files
    files_to_upload.extend(args.get("code_interpreter_files", []))

    # Add files from directories
    for directory in args.get("code_interpreter_dirs", []):
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                raise CLIError(
                    f"Directory not found: {directory}",
                    exit_code=ExitCode.USAGE_ERROR,
                )

            # Get all files from directory (non-recursive for safety)
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    files_to_upload.append(str(file_path))

        except Exception as e:
            raise CLIError(
                f"Failed to process directory {directory}: {e}",
                exit_code=ExitCode.USAGE_ERROR,
            )

    # If no files specified, return None
    if not files_to_upload:
        return None

    # Create Code Interpreter manager
    manager = CodeInterpreterManager(client)

    # Validate files before upload
    validation_errors = manager.validate_files_for_upload(files_to_upload)
    if validation_errors:
        error_msg = "Code Interpreter file validation failed:\n" + "\n".join(
            f"- {error}" for error in validation_errors
        )
        raise CLIError(error_msg, exit_code=ExitCode.USAGE_ERROR)

    try:
        # Upload files
        logger.debug(f"Uploading {len(files_to_upload)} files for Code Interpreter")
        file_ids = await manager.upload_files_for_code_interpreter(files_to_upload)

        # Build tool configuration
        tool_config = manager.build_tool_config(file_ids)

        # Get container limits info for user awareness
        limits_info = manager.get_container_limits_info()
        logger.debug(f"Code Interpreter container limits: {limits_info}")

        return {
            "tool_config": tool_config,
            "manager": manager,
            "file_ids": file_ids,
            "limits_info": limits_info,
        }

    except Exception as e:
        logger.error(f"Failed to configure Code Interpreter: {e}")
        # Clean up any uploaded files on error
        await manager.cleanup_uploaded_files()
        # Map tool-specific errors
        mapped_error = APIErrorMapper.map_tool_error("code-interpreter", e)
        raise mapped_error


async def process_file_search_configuration(
    args: CLIParams, client: AsyncOpenAI
) -> Optional[Dict[str, Any]]:
    """Process File Search configuration from CLI arguments.

    Args:
        args: CLI parameters containing File Search settings
        client: AsyncOpenAI client for vector store operations

    Returns:
        Dictionary with File Search tool config and manager, or None if no files specified

    Raises:
        CLIError: If File Search configuration is invalid
    """
    logger.debug("=== File Search Configuration Processing ===")

    # Collect all files to upload
    files_to_upload = []

    # Add individual files
    files_to_upload.extend(args.get("file_search_files", []))

    # Add files from directories
    for directory in args.get("file_search_dirs", []):
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                raise CLIError(
                    f"Directory not found: {directory}",
                    exit_code=ExitCode.USAGE_ERROR,
                )

            # Get all files from directory (non-recursive for safety)
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    files_to_upload.append(str(file_path))

        except Exception as e:
            raise CLIError(
                f"Failed to process directory {directory}: {e}",
                exit_code=ExitCode.USAGE_ERROR,
            )

    # If no files specified, return None
    if not files_to_upload:
        return None

    # Create File Search manager
    manager = FileSearchManager(client)

    # Validate files before upload
    validation_errors = manager.validate_files_for_file_search(files_to_upload)
    if validation_errors:
        error_msg = "File Search file validation failed:\n" + "\n".join(
            f"- {error}" for error in validation_errors
        )
        raise CLIError(error_msg, exit_code=ExitCode.USAGE_ERROR)

    try:
        # Get configuration parameters
        vector_store_name = args.get("file_search_vector_store_name", "ostruct_search")
        retry_count = args.get("file_search_retry_count", 3)
        timeout = args.get("file_search_timeout", 60.0)

        # Create vector store with retry logic
        logger.debug(
            f"Creating vector store '{vector_store_name}' for {len(files_to_upload)} files"
        )
        vector_store_id = await manager.create_vector_store_with_retry(
            name=vector_store_name, max_retries=retry_count
        )

        # Upload files to vector store
        logger.debug(
            f"Uploading {len(files_to_upload)} files to vector store with {retry_count} max retries"
        )
        file_ids = await manager.upload_files_to_vector_store(
            vector_store_id=vector_store_id,
            files=files_to_upload,
            max_retries=retry_count,
        )

        # Wait for vector store to be ready
        logger.debug(f"Waiting for vector store indexing (timeout: {timeout}s)")
        is_ready = await manager.wait_for_vector_store_ready(
            vector_store_id=vector_store_id, timeout=timeout
        )

        if not is_ready:
            logger.warning(
                f"Vector store may not be fully indexed within {timeout}s timeout"
            )
            # Continue anyway as indexing is typically instant

        # Build tool configuration
        tool_config = manager.build_tool_config(vector_store_id)

        # Get performance info for user awareness
        perf_info = manager.get_performance_info()
        logger.debug(f"File Search performance info: {perf_info}")

        return {
            "tool_config": tool_config,
            "manager": manager,
            "vector_store_id": vector_store_id,
            "file_ids": file_ids,
            "perf_info": perf_info,
        }

    except Exception as e:
        logger.error(f"Failed to configure File Search: {e}")
        # Clean up any created resources on error
        await manager.cleanup_resources()
        # Map tool-specific errors
        mapped_error = APIErrorMapper.map_tool_error("file-search", e)
        raise mapped_error


async def execute_model(
    args: CLIParams,
    params: Dict[str, Any],
    output_model: Type[BaseModel],
    system_prompt: str,
    user_prompt: str,
) -> ExitCode:
    """Execute the model and handle the response.

    Args:
        args: Command line arguments
        params: Validated model parameters
        output_model: Generated Pydantic model
        system_prompt: Processed system prompt
        user_prompt: Processed user prompt

    Returns:
        Exit code indicating success or failure

    Raises:
        CLIError: For execution errors
        UnattendedOperationTimeoutError: For operation timeouts
    """
    logger.debug("=== Execution Phase ===")

    # Initialize unattended operation manager
    timeout_seconds = args.get("timeout", 3600)
    operation_manager = UnattendedOperationManager(timeout_seconds)

    # Pre-validate unattended compatibility
    mcp_servers = args.get("mcp_servers", [])
    if mcp_servers:
        validator = UnattendedCompatibilityValidator()
        validation_errors = validator.validate_mcp_servers(mcp_servers)
        if validation_errors:
            error_msg = "Unattended operation compatibility errors:\n" + "\n".join(
                f"  • {err}" for err in validation_errors
            )
            logger.error(error_msg)
            raise CLIError(error_msg, exit_code=ExitCode.VALIDATION_ERROR)

    api_key = args.get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "No API key provided. Set OPENAI_API_KEY environment variable or use --api-key"
        logger.error(msg)
        raise CLIError(msg, exit_code=ExitCode.API_ERROR)

    client = AsyncOpenAI(
        api_key=api_key, timeout=min(args.get("timeout", 60.0), 300.0)
    )  # Cap at 5 min for client timeout

    # Create detailed log callback
    def log_callback(level: int, message: str, extra: dict[str, Any]) -> None:
        if args.get("debug_openai_stream", False):
            if extra:
                extra_str = LogSerializer.serialize_log_extra(extra)
                if extra_str:
                    logger.debug("%s\nExtra:\n%s", message, extra_str)
                else:
                    logger.debug("%s\nExtra: Failed to serialize", message)
            else:
                logger.debug(message)

    async def execute_main_operation() -> ExitCode:
        """Main execution operation wrapped for timeout handling."""
        # Create output buffer
        output_buffer = []

        # Process tool configurations
        tools = []
        nonlocal code_interpreter_info, file_search_info

        # Process MCP configuration if provided
        if args.get("mcp_servers"):
            mcp_config = await process_mcp_configuration(args)
            tools.extend(mcp_config.get_tools_for_responses_api())

        # Get routing result from explicit file processor
        routing_result = args.get("_routing_result")

        # Process Code Interpreter configuration if enabled
        if routing_result and "code-interpreter" in routing_result.enabled_tools:
            code_interpreter_files = routing_result.validated_files.get(
                "code-interpreter", []
            )
            if code_interpreter_files:
                # Override args with routed files for Code Interpreter processing
                ci_args = dict(args)
                ci_args["code_interpreter_files"] = code_interpreter_files
                ci_args[
                    "code_interpreter_dirs"
                ] = []  # Files already expanded from dirs
                code_interpreter_info = await process_code_interpreter_configuration(
                    ci_args, client
                )
                if code_interpreter_info:
                    tools.append(code_interpreter_info["tool_config"])

        # Process File Search configuration if enabled
        if routing_result and "file-search" in routing_result.enabled_tools:
            file_search_files = routing_result.validated_files.get("file-search", [])
            if file_search_files:
                # Override args with routed files for File Search processing
                fs_args = dict(args)
                fs_args["file_search_files"] = file_search_files
                fs_args["file_search_dirs"] = []  # Files already expanded from dirs
                file_search_info = await process_file_search_configuration(
                    fs_args, client
                )
                if file_search_info:
                    tools.append(file_search_info["tool_config"])

        # Stream the response
        async for response in stream_structured_output(
            client=client,
            model=args["model"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_model,
            output_file=args.get("output_file"),
            on_log=log_callback,
            tools=tools,
        ):
            output_buffer.append(response)

        # Handle final output
        output_file = args.get("output_file")
        if output_file:
            with open(output_file, "w") as f:
                if len(output_buffer) == 1:
                    f.write(output_buffer[0].model_dump_json(indent=2))
                else:
                    # Build complete JSON array as a single string
                    json_output = "[\n"
                    for i, response in enumerate(output_buffer):
                        if i > 0:
                            json_output += ",\n"
                        json_output += "  " + response.model_dump_json(
                            indent=2
                        ).replace("\n", "\n  ")
                    json_output += "\n]"
                    f.write(json_output)
        else:
            # Write to stdout when no output file is specified
            if len(output_buffer) == 1:
                print(output_buffer[0].model_dump_json(indent=2))
            else:
                # Build complete JSON array as a single string
                json_output = "[\n"
                for i, response in enumerate(output_buffer):
                    if i > 0:
                        json_output += ",\n"
                    json_output += "  " + response.model_dump_json(indent=2).replace(
                        "\n", "\n  "
                    )
                json_output += "\n]"
                print(json_output)

        # Handle file downloads from Code Interpreter if any were generated
        if (
            code_interpreter_info
            and hasattr(response, "file_ids")
            and response.file_ids
        ):
            try:
                download_dir = args.get("code_interpreter_download_dir", "./downloads")
                manager = code_interpreter_info["manager"]
                downloaded_files = await manager.download_generated_files(
                    response.file_ids, download_dir
                )
                if downloaded_files:
                    logger.info(
                        f"Downloaded {len(downloaded_files)} generated files to {download_dir}"
                    )
                    for file_path in downloaded_files:
                        logger.info(f"  - {file_path}")
            except Exception as e:
                logger.warning(f"Failed to download generated files: {e}")

        return ExitCode.SUCCESS

    # Execute main operation with timeout safeguards
    code_interpreter_info = None
    file_search_info = None

    try:
        result = await operation_manager.execute_with_safeguards(
            execute_main_operation, "model execution"
        )
        return result
    except (
        StreamInterruptedError,
        StreamBufferError,
        StreamParseError,
        APIResponseError,
        EmptyResponseError,
        InvalidResponseFormatError,
    ) as e:
        logger.error("Stream error: %s", str(e))
        raise CLIError(str(e), exit_code=ExitCode.API_ERROR)
    except Exception as e:
        logger.exception("Unexpected error during streaming")
        raise CLIError(str(e), exit_code=ExitCode.UNKNOWN_ERROR)
    finally:
        # Clean up Code Interpreter files if requested
        if code_interpreter_info and args.get("code_interpreter_cleanup", True):
            try:
                manager = code_interpreter_info["manager"]
                await manager.cleanup_uploaded_files()
                logger.debug("Cleaned up Code Interpreter uploaded files")
            except Exception as e:
                logger.warning(f"Failed to clean up Code Interpreter files: {e}")

        # Clean up File Search resources if requested
        if file_search_info and args.get("file_search_cleanup", True):
            try:
                manager = file_search_info["manager"]
                await manager.cleanup_resources()
                logger.debug("Cleaned up File Search vector stores and files")
            except Exception as e:
                logger.warning(f"Failed to clean up File Search resources: {e}")

        await client.close()


async def run_cli_async(args: CLIParams) -> ExitCode:
    """Async wrapper for CLI operations.

    Args:
        args: CLI parameters.

    Returns:
        Exit code.

    Raises:
        CLIError: For errors during CLI operations.
    """
    try:
        # 0. Configure Progress Reporting
        configure_progress_reporter(
            verbose=args.get("verbose", False),
            progress_level=args.get("progress_level", "basic"),
        )
        progress_reporter = get_progress_reporter()

        # 0. Model Parameter Validation
        progress_reporter.report_phase("Validating configuration", "🔧")
        logger.debug("=== Model Parameter Validation ===")
        params = await validate_model_params(args)

        # 1. Input Validation Phase (includes schema validation)
        progress_reporter.report_phase("Processing input files", "📂")
        (
            security_manager,
            task_template,
            schema,
            template_context,
            env,
            template_path,
        ) = await validate_inputs(args)

        # Report file routing decisions
        routing_result = args.get("_routing_result")
        if routing_result:
            template_files = routing_result.validated_files.get("template", [])
            container_files = routing_result.validated_files.get("code-interpreter", [])
            vector_files = routing_result.validated_files.get("file-search", [])
            progress_reporter.report_file_routing(
                template_files, container_files, vector_files
            )

        # 2. Template Processing Phase
        progress_reporter.report_phase("Rendering template", "📝")
        system_prompt, user_prompt = await process_templates(
            args, task_template, template_context, env, template_path
        )

        # 3. Model & Schema Validation Phase
        progress_reporter.report_phase("Validating model and schema", "✅")
        (
            output_model,
            messages,
            total_tokens,
            registry,
        ) = await validate_model_and_schema(
            args, schema, system_prompt, user_prompt, template_context
        )

        # Report validation results
        capabilities = registry.get_capabilities(args["model"])
        progress_reporter.report_validation_results(
            schema_valid=True,  # If we got here, schema is valid
            template_valid=True,  # If we got here, template is valid
            token_count=total_tokens,
            token_limit=capabilities.context_window,
        )

        # 4. Dry Run Output Phase - Moved after all validations
        if args.get("dry_run", False):
            report_success("Dry run completed successfully - all validations passed")

            # Calculate cost estimate
            estimated_cost = calculate_cost_estimate(
                model=args["model"],
                input_tokens=total_tokens,
                output_tokens=capabilities.max_output_tokens,
                registry=registry,
            )

            # Enhanced dry-run output with cost estimation
            cost_breakdown = format_cost_breakdown(
                model=args["model"],
                input_tokens=total_tokens,
                output_tokens=capabilities.max_output_tokens,
                total_cost=estimated_cost,
                context_window=capabilities.context_window,
            )
            print(cost_breakdown)

            if args.get("verbose", False):
                logger.info("\nSystem Prompt:")
                logger.info("-" * 40)
                logger.info(system_prompt)
                logger.info("\nRendered Template:")
                logger.info("-" * 40)
                logger.info(user_prompt)

            # Return success only if we got here (no validation errors)
            return ExitCode.SUCCESS

        # 5. Execution Phase
        progress_reporter.report_phase("Generating response", "🤖")
        return await execute_model(
            args, params, output_model, system_prompt, user_prompt
        )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        raise
    except SchemaValidationError as e:
        # Ensure schema validation errors are properly propagated with the correct exit code
        logger.error("Schema validation error: %s", str(e))
        raise  # Re-raise the SchemaValidationError to preserve the error chain
    except Exception as e:
        if isinstance(e, CLIError):
            raise  # Let our custom errors propagate
        logger.exception("Unexpected error")
        raise CLIError(str(e), context={"error_type": type(e).__name__})


def create_cli() -> click.Command:
    """Create the CLI command.

    Returns:
        click.Command: The CLI command object
    """
    return cli  # The decorator already returns a Command


def main() -> None:
    """Main entry point for the CLI."""
    try:
        cli(standalone_mode=False)
    except (
        CLIError,
        InvalidJSONError,
        SchemaFileError,
        SchemaValidationError,
    ) as e:
        handle_error(e)
        sys.exit(e.exit_code if hasattr(e, "exit_code") else ExitCode.INTERNAL_ERROR)
    except click.UsageError as e:
        handle_error(e)
        sys.exit(ExitCode.USAGE_ERROR)
    except Exception as e:
        handle_error(e)
        sys.exit(ExitCode.INTERNAL_ERROR)


# Export public API
__all__ = [
    "ExitCode",
    "estimate_tokens_with_encoding",
    "parse_json_var",
    "create_dynamic_model",
    "validate_path_mapping",
    "create_cli",
    "main",
]


if __name__ == "__main__":
    main()
