"""Command-line interface for making structured OpenAI API calls."""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum, IntEnum
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
    TypeVar,
    Union,
    cast,
    get_origin,
    overload,
)

if sys.version_info >= (3, 11):
    from enum import StrEnum

from datetime import date, datetime, time
from pathlib import Path

import click
import jinja2
import yaml
from openai import AsyncOpenAI
from openai_structured.client import (
    async_openai_structured_stream,
    supports_structured_output,
)
from openai_structured.errors import (
    APIResponseError,
    EmptyResponseError,
    InvalidResponseFormatError,
    ModelNotSupportedError,
    ModelVersionError,
    OpenAIClientError,
    SchemaFileError,
    SchemaValidationError,
    StreamBufferError,
    StreamInterruptedError,
    StreamParseError,
)
from openai_structured.model_registry import ModelRegistry
from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationError,
    create_model,
)
from pydantic.fields import FieldInfo as FieldInfoType
from pydantic.functional_validators import BeforeValidator
from pydantic.types import constr
from typing_extensions import TypeAlias

from ostruct.cli.click_options import create_click_command
from ostruct.cli.exit_codes import ExitCode

from .. import __version__  # noqa: F401 - Used in package metadata
from . import errors
from .errors import (
    CLIError,
    DirectoryNotFoundError,
    FieldDefinitionError,
    FileNotFoundError,
    InvalidJSONError,
    ModelCreationError,
    ModelValidationError,
    NestedModelError,
    PathSecurityError,
    TaskTemplateSyntaxError,
    TaskTemplateVariableError,
    VariableError,
    VariableNameError,
    VariableValueError,
)
from .file_utils import FileInfoList, TemplateValue, collect_files
from .path_utils import validate_path_mapping
from .security import SecurityManager
from .serialization import LogSerializer
from .template_env import create_jinja_env
from .template_utils import SystemPromptError, render_template
from .token_utils import estimate_tokens_with_encoding

# Constants
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


@dataclass
class Namespace:
    """Compatibility class to mimic argparse.Namespace for existing code."""

    # Required fields without defaults
    task: Optional[str]
    task_file: Optional[str]
    file: List[str]
    files: List[str]
    dir: List[str]
    allowed_dir: List[str]
    base_dir: str
    allowed_dir_file: Optional[str]
    dir_recursive: bool
    dir_ext: Optional[str]
    var: List[str]
    json_var: List[str]
    system_prompt: Optional[str]
    system_prompt_file: Optional[str]
    ignore_task_sysprompt: bool
    schema_file: str
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
    # Model parameters - all optional since support varies by model
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    reasoning_effort: Optional[str] = None
    # Other fields with defaults
    progress_level: str = "basic"


# Set up logging
logger = logging.getLogger(__name__)

# Configure openai_structured logging based on debug flag
openai_logger = logging.getLogger("openai_structured")
openai_logger.setLevel(logging.DEBUG)  # Allow all messages through to handlers
openai_logger.propagate = False  # Prevent propagation to root logger

# Remove any existing handlers
for handler in openai_logger.handlers:
    openai_logger.removeHandler(handler)

# Create a file handler for openai_structured logger that captures all levels
log_dir = os.path.expanduser("~/.ostruct/logs")
os.makedirs(log_dir, exist_ok=True)
openai_file_handler = logging.FileHandler(
    os.path.join(log_dir, "openai_stream.log")
)
openai_file_handler.setLevel(logging.DEBUG)  # Always capture debug in file
openai_file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
openai_logger.addHandler(openai_file_handler)

# Create a file handler for the main logger that captures all levels
ostruct_file_handler = logging.FileHandler(
    os.path.join(log_dir, "ostruct.log")
)
ostruct_file_handler.setLevel(logging.DEBUG)  # Always capture debug in file
ostruct_file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(ostruct_file_handler)


# Type aliases
FieldType = (
    Any  # Changed from Type[Any] to allow both concrete types and generics
)
FieldDefinition = Tuple[FieldType, FieldInfoType]
ModelType = TypeVar("ModelType", bound=BaseModel)
ItemType: TypeAlias = Type[BaseModel]
ValueType: TypeAlias = Type[Any]


def is_container_type(tp: Type[Any]) -> bool:
    """Check if a type is a container type (list, dict, etc.)."""
    origin = get_origin(tp)
    return origin in (list, dict)


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
        if (
            isinstance(items_schema, dict)
            and items_schema.get("type") == "object"
        ):
            array_item_model = create_dynamic_model(
                items_schema,
                base_name=f"{base_name}_{field_name}_Item",
                show_schema=False,
                debug_validation=False,
            )
            array_type: Type[List[Any]] = List[array_item_model]  # type: ignore[valid-type]
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
    registry = ModelRegistry()
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
            f"Total tokens ({total_tokens:,}) exceed model's context window limit "
            f"of {context_limit:,} tokens"
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
) -> str:
    """Process system prompt from various sources.

    Args:
        task_template: The task template string
        system_prompt: Optional system prompt string
        system_prompt_file: Optional path to system prompt file
        template_context: Template context for rendering
        env: Jinja2 environment
        ignore_task_sysprompt: Whether to ignore system prompt in task template

    Returns:
        The final system prompt string

    Raises:
        SystemPromptError: If the system prompt cannot be loaded or rendered
        FileNotFoundError: If a prompt file does not exist
        PathSecurityError: If a prompt file path violates security constraints
    """
    # Default system prompt
    default_prompt = "You are a helpful assistant."

    # Check for conflicting arguments
    if system_prompt is not None and system_prompt_file is not None:
        raise SystemPromptError(
            "Cannot specify both --system-prompt and --system-prompt-file"
        )

    # Try to get system prompt from CLI argument first
    if system_prompt_file is not None:
        try:
            name, path = validate_path_mapping(
                f"system_prompt={system_prompt_file}"
            )
            with open(path, "r", encoding="utf-8") as f:
                system_prompt = f.read().strip()
        except (FileNotFoundError, PathSecurityError) as e:
            raise SystemPromptError(f"Invalid system prompt file: {e}")

    if system_prompt is not None:
        # Render system prompt with template context
        try:
            template = env.from_string(system_prompt)
            return cast(str, template.render(**template_context).strip())
        except jinja2.TemplateError as e:
            raise SystemPromptError(f"Error rendering system prompt: {e}")

    # If not ignoring task template system prompt, try to extract it
    if not ignore_task_sysprompt:
        try:
            # Extract YAML frontmatter
            if task_template.startswith("---\n"):
                end = task_template.find("\n---\n", 4)
                if end != -1:
                    frontmatter = task_template[4:end]
                    try:
                        metadata = yaml.safe_load(frontmatter)
                        if (
                            isinstance(metadata, dict)
                            and "system_prompt" in metadata
                        ):
                            system_prompt = str(metadata["system_prompt"])
                            # Render system prompt with template context
                            try:
                                template = env.from_string(system_prompt)
                                return cast(
                                    str,
                                    template.render(
                                        **template_context
                                    ).strip(),
                                )
                            except jinja2.TemplateError as e:
                                raise SystemPromptError(
                                    f"Error rendering system prompt: {e}"
                                )
                    except yaml.YAMLError as e:
                        raise SystemPromptError(
                            f"Invalid YAML frontmatter: {e}"
                        )

        except Exception as e:
            raise SystemPromptError(
                f"Error extracting system prompt from template: {e}"
            )

    # Fall back to default
    return default_prompt


def validate_variable_mapping(
    mapping: str, is_json: bool = False
) -> tuple[str, Any]:
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
                    f"Invalid JSON value for variable {name!r}: {value!r}"
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
            raise ValueError(
                "Invalid path mapping format. Expected format: name=path"
            )

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
            base_path = (
                Path.cwd() if base_dir is None else Path(base_dir).resolve()
            )
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
                    allowed_dirs=[
                        str(d) for d in security_manager.allowed_dirs
                    ],
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


def validate_task_template(
    task: Optional[str], task_file: Optional[str]
) -> str:
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
        raise TaskTemplateVariableError(
            "Cannot specify both --task and --task-file"
        )

    if task is None and task_file is None:
        raise TaskTemplateVariableError(
            "Must specify either --task or --task-file"
        )

    template_content: str
    if task_file is not None:
        try:
            name, path = validate_path_mapping(f"task={task_file}")
            with open(path, "r", encoding="utf-8") as f:
                template_content = f.read()
        except (FileNotFoundError, PathSecurityError) as e:
            raise TaskTemplateVariableError(str(e))
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
        with open(path) as f:
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
                    f"Invalid JSON in schema file {path}: {e}", source=path
                )
    except FileNotFoundError:
        msg = f"Schema file not found: {path}"
        logger.error(msg)
        raise SchemaFileError(msg)
    except Exception as e:
        if isinstance(e, InvalidJSONError):
            raise
        msg = f"Failed to read schema file {path}: {e}"
        logger.error(msg)
        logger.debug("Unexpected error details: %s", str(e))
        raise SchemaFileError(msg)

    # Pre-validation structure checks
    if verbose:
        logger.info("Performing pre-validation structure checks")
        logger.debug("Loaded schema: %s", json.dumps(schema, indent=2))

    if not isinstance(schema, dict):
        msg = f"Schema in {path} must be a JSON object"
        logger.error(msg)
        raise SchemaValidationError(msg)

    # Validate schema structure
    if "schema" in schema:
        if verbose:
            logger.debug("Found schema wrapper, validating inner schema")
        inner_schema = schema["schema"]
        if not isinstance(inner_schema, dict):
            msg = f"Inner schema in {path} must be a JSON object"
            logger.error(msg)
            raise SchemaValidationError(msg)
        if verbose:
            logger.debug("Inner schema validated successfully")
            logger.debug(
                "Inner schema: %s", json.dumps(inner_schema, indent=2)
            )
    else:
        if verbose:
            logger.debug("No schema wrapper found, using schema as-is")
            logger.debug("Schema: %s", json.dumps(schema, indent=2))

    # Additional schema validation
    if "type" not in schema.get("schema", schema):
        msg = f"Schema in {path} must specify a type"
        logger.error(msg)
        raise SchemaValidationError(msg)

    # Return the full schema including wrapper
    return schema


def collect_template_files(
    args: Namespace,
    security_manager: SecurityManager,
) -> Dict[str, TemplateValue]:
    """Collect files from command line arguments.

    Args:
        args: Parsed command line arguments
        security_manager: Security manager for path validation

    Returns:
        Dictionary mapping variable names to file info objects

    Raises:
        PathSecurityError: If any file paths violate security constraints
        ValueError: If file mappings are invalid or files cannot be accessed
    """
    try:
        result = collect_files(
            file_mappings=args.file,
            pattern_mappings=args.files,
            dir_mappings=args.dir,
            dir_recursive=args.dir_recursive,
            dir_extensions=args.dir_ext.split(",") if args.dir_ext else None,
            security_manager=security_manager,
        )
        return cast(Dict[str, TemplateValue], result)
    except PathSecurityError:
        # Let PathSecurityError propagate without wrapping
        raise
    except (FileNotFoundError, DirectoryNotFoundError) as e:
        # Wrap file-related errors
        raise ValueError(f"File access error: {e}")
    except Exception as e:
        # Don't wrap InvalidJSONError
        if isinstance(e, InvalidJSONError):
            raise
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            raise e.__cause__
        # Wrap other errors
        raise ValueError(f"Error collecting files: {e}")


def collect_simple_variables(args: Namespace) -> Dict[str, str]:
    """Collect simple string variables from --var arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary mapping variable names to string values

    Raises:
        VariableNameError: If a variable name is invalid or duplicate
    """
    variables: Dict[str, str] = {}
    all_names: Set[str] = set()

    if args.var:
        for mapping in args.var:
            try:
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


def collect_json_variables(args: Namespace) -> Dict[str, Any]:
    """Collect JSON variables from --json-var arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary mapping variable names to parsed JSON values

    Raises:
        VariableNameError: If a variable name is invalid or duplicate
        InvalidJSONError: If a JSON value is invalid
    """
    variables: Dict[str, Any] = {}
    all_names: Set[str] = set()

    if args.json_var:
        for mapping in args.json_var:
            try:
                name, json_str = mapping.split("=", 1)
                if not name.isidentifier():
                    raise VariableNameError(f"Invalid variable name: {name}")
                if name in all_names:
                    raise VariableNameError(f"Duplicate variable name: {name}")
                try:
                    value = json.loads(json_str)
                    variables[name] = value
                    all_names.add(name)
                except json.JSONDecodeError as e:
                    raise InvalidJSONError(
                        f"Error parsing JSON for variable '{name}': {str(e)}. Input was: {json_str}"
                    )
            except ValueError:
                raise VariableNameError(
                    f"Invalid JSON variable mapping format: {mapping}. Expected name=json"
                )

    return variables


def create_template_context(
    files: Optional[Dict[str, FileInfoList]] = None,
    variables: Optional[Dict[str, str]] = None,
    json_variables: Optional[Dict[str, Any]] = None,
    security_manager: Optional[SecurityManager] = None,
    stdin_content: Optional[str] = None,
) -> Dict[str, Any]:
    """Create template context from direct inputs.

    Args:
        files: Optional dictionary mapping names to FileInfoList objects
        variables: Optional dictionary of simple string variables
        json_variables: Optional dictionary of JSON variables
        security_manager: Optional security manager for path validation
        stdin_content: Optional content to use for stdin

    Returns:
        Template context dictionary

    Raises:
        PathSecurityError: If any file paths violate security constraints
        VariableError: If variable mappings are invalid
    """
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


def create_template_context_from_args(
    args: "Namespace",
    security_manager: SecurityManager,
) -> Dict[str, Any]:
    """Create template context from command line arguments.

    Args:
        args: Parsed command line arguments
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
        files = None
        if any([args.file, args.files, args.dir]):
            files = collect_files(
                file_mappings=args.file,
                pattern_mappings=args.files,
                dir_mappings=args.dir,
                dir_recursive=args.dir_recursive,
                dir_extensions=(
                    args.dir_ext.split(",") if args.dir_ext else None
                ),
                security_manager=security_manager,
            )

        # Collect simple variables
        try:
            variables = collect_simple_variables(args)
        except VariableNameError as e:
            raise VariableError(str(e))

        # Collect JSON variables
        json_variables = {}
        if args.json_var:
            for mapping in args.json_var:
                try:
                    name, value = mapping.split("=", 1)
                    if not name.isidentifier():
                        raise VariableNameError(
                            f"Invalid variable name: {name}"
                        )
                    try:
                        json_value = json.loads(value)
                    except json.JSONDecodeError as e:
                        raise InvalidJSONError(
                            f"Error parsing JSON for variable '{name}': {str(e)}. Input was: {value}"
                        )
                    if name in json_variables:
                        raise VariableNameError(
                            f"Duplicate variable name: {name}"
                        )
                    json_variables[name] = json_value
                except ValueError:
                    raise VariableNameError(
                        f"Invalid JSON variable mapping format: {mapping}. Expected name=json"
                    )

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
        context["current_model"] = args.model

        return context

    except PathSecurityError:
        # Let PathSecurityError propagate without wrapping
        raise
    except (FileNotFoundError, DirectoryNotFoundError) as e:
        # Wrap file-related errors
        raise ValueError(f"File access error: {e}")
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
                f"Error parsing JSON for variable '{name}': {str(e)}. Input was: {json_str}"
            )

        return name, value

    except ValueError as e:
        if "not enough values to unpack" in str(e):
            raise VariableValueError(
                f"Invalid JSON variable mapping (expected name=json format): {var_str!r}"
            )
        raise


def _create_enum_type(values: List[Any], field_name: str) -> Type[Enum]:
    """Create an enum type from a list of values.

    Args:
        values: List of enum values
        field_name: Name of the field for enum type name

    Returns:
        Created enum type
    """
    # Determine the value type
    value_types = {type(v) for v in values}

    if len(value_types) > 1:
        # Mixed types, use string representation
        enum_dict = {f"VALUE_{i}": str(v) for i, v in enumerate(values)}
        return type(f"{field_name.title()}Enum", (str, Enum), enum_dict)
    elif value_types == {int}:
        # All integer values
        enum_dict = {f"VALUE_{v}": v for v in values}
        return type(f"{field_name.title()}Enum", (IntEnum,), enum_dict)
    elif value_types == {str}:
        # All string values
        enum_dict = {v.upper().replace(" ", "_"): v for v in values}
        if sys.version_info >= (3, 11):
            return type(f"{field_name.title()}Enum", (StrEnum,), enum_dict)
        else:
            # Other types, use string representation
            return type(f"{field_name.title()}Enum", (str, Enum), enum_dict)

    # Default case: treat as string enum
    enum_dict = {f"VALUE_{i}": str(v) for i, v in enumerate(values)}
    return type(f"{field_name.title()}Enum", (str, Enum), enum_dict)


def handle_error(e: Exception) -> None:
    """Handle CLI errors and display appropriate messages."""
    if isinstance(e, (SchemaFileError, errors.SchemaFileError)):
        msg = f"Schema error: {str(e)}"
        logger.error(msg)
        click.secho(msg, fg="red", err=True)
        sys.exit(ExitCode.SCHEMA_ERROR)
    elif isinstance(e, click.UsageError):
        msg = f"Usage error: {str(e)}"
        logger.error(msg)
        click.secho(msg, fg="red", err=True)
        sys.exit(ExitCode.USAGE_ERROR)
    elif isinstance(e, (errors.InvalidJSONError, json.JSONDecodeError)):
        msg = f"Schema validation error: {str(e)}"
        logger.error(msg)
        click.secho(msg, fg="red", err=True)
        sys.exit(ExitCode.DATA_ERROR)
    elif isinstance(e, (SchemaValidationError, errors.SchemaValidationError)):
        msg = f"Schema validation error: {str(e)}"
        logger.error(msg)
        click.secho(msg, fg="red", err=True)
        sys.exit(ExitCode.VALIDATION_ERROR)
    elif isinstance(e, errors.CLIError):
        msg = str(e)
        logger.error(msg)
        click.secho(msg, fg="red", err=True)
        sys.exit(e.exit_code)
    else:
        msg = f"Unexpected error: {str(e)}"
        logger.error(msg, exc_info=True)
        click.secho(msg, fg="red", err=True)
        sys.exit(ExitCode.INTERNAL_ERROR)


def validate_model_parameters(model: str, params: Dict[str, Any]) -> None:
    """Validate model parameters against model capabilities.

    Args:
        model: The model name to validate parameters for
        params: Dictionary of parameter names and values to validate

    Raises:
        CLIError: If any parameters are not supported by the model
    """
    try:
        capabilities = ModelRegistry().get_capabilities(model)
        for param_name, value in params.items():
            try:
                capabilities.validate_parameter(param_name, value)
            except OpenAIClientError as e:
                logger.error(
                    "Validation failed for model %s: %s", model, str(e)
                )
                raise CLIError(
                    str(e),
                    exit_code=ExitCode.VALIDATION_ERROR,
                    context={
                        "model": model,
                        "param": param_name,
                        "value": value,
                    },
                )
    except (ModelNotSupportedError, ModelVersionError) as e:
        logger.error("Model validation failed: %s", str(e))
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
    **kwargs: Any,
) -> AsyncGenerator[BaseModel, None]:
    """Stream structured output from OpenAI API.

    This function follows the guide's recommendation for a focused async streaming function.
    It handles the core streaming logic and resource cleanup.

    Args:
        client: The OpenAI client to use
        model: The model to use
        system_prompt: The system prompt to use
        user_prompt: The user prompt to use
        output_schema: The Pydantic model to validate responses against
        output_file: Optional file to write output to
        **kwargs: Additional parameters to pass to the API

    Returns:
        An async generator yielding validated model instances

    Raises:
        ValueError: If the model does not support structured output or parameters are invalid
        StreamInterruptedError: If the stream is interrupted
        APIResponseError: If there is an API error
    """
    try:
        # Check if model supports structured output using openai_structured's function
        if not supports_structured_output(model):
            raise ValueError(
                f"Model {model} does not support structured output with json_schema response format. "
                "Please use a model that supports structured output."
            )

        # Extract non-model parameters
        on_log = kwargs.pop("on_log", None)

        # Handle model-specific parameters
        stream_kwargs = {}
        registry = ModelRegistry()
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

        # Log the API request details
        logger.debug("Making OpenAI API request with:")
        logger.debug("Model: %s", model)
        logger.debug("System prompt: %s", system_prompt)
        logger.debug("User prompt: %s", user_prompt)
        logger.debug("Parameters: %s", json.dumps(stream_kwargs, indent=2))
        logger.debug("Schema: %s", output_schema.model_json_schema())

        # Use the async generator from openai_structured directly
        async for chunk in async_openai_structured_stream(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            on_log=on_log,  # Pass non-model parameters directly to the function
            **stream_kwargs,  # Pass only validated model parameters
        ):
            yield chunk

    except (
        StreamInterruptedError,
        StreamBufferError,
        StreamParseError,
        APIResponseError,
        EmptyResponseError,
        InvalidResponseFormatError,
    ) as e:
        logger.error(f"Stream error: {e}")
        raise
    finally:
        # Always ensure client is properly closed
        await client.close()


@create_click_command()
def cli(**kwargs: Any) -> None:
    """Command-line interface for making structured OpenAI API calls."""
    try:
        args = Namespace(**kwargs)

        # Validate required arguments first
        if not args.task and not args.task_file:
            raise click.UsageError("Must specify either --task or --task-file")
        if not args.schema_file:
            raise click.UsageError("Missing option '--schema-file'")
        if args.task and args.task_file:
            raise click.UsageError(
                "Cannot specify both --task and --task-file"
            )
        if args.system_prompt and args.system_prompt_file:
            raise click.UsageError(
                "Cannot specify both --system-prompt and --system-prompt-file"
            )

        # Early validation of model parameters
        registry = ModelRegistry()
        capabilities = registry.get_capabilities(args.model)

        # Check which parameters were explicitly provided
        ctx = click.get_current_context()
        for param_name in [
            "temperature",
            "max_output_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "reasoning_effort",
        ]:
            if param_name in ctx.params and ctx.params[param_name] is not None:
                if param_name not in capabilities.supported_parameters:
                    msg = f"Model {args.model} does not support parameter: {param_name}"
                    logger.error(
                        "Validation failed for model %s: %s", args.model, msg
                    )
                    raise CLIError(
                        msg,
                        exit_code=ExitCode.VALIDATION_ERROR,
                        context={"model": args.model, "param": param_name},
                    )
                try:
                    capabilities.validate_parameter(
                        param_name, ctx.params[param_name]
                    )
                except ValueError as e:
                    msg = f"Invalid value for parameter {param_name}: {str(e)}"
                    logger.error(
                        "Validation failed for model %s: %s", args.model, msg
                    )
                    raise CLIError(
                        msg,
                        exit_code=ExitCode.VALIDATION_ERROR,
                        context={
                            "model": args.model,
                            "param": param_name,
                            "value": ctx.params[param_name],
                        },
                    )

        # Validate JSON variables
        if args.json_var:
            try:
                for mapping in args.json_var:
                    name, value = mapping.split("=", 1)
                    if not name:
                        raise VariableNameError(
                            "Empty name in JSON variable mapping"
                        )
                    try:
                        json.loads(value)
                    except json.JSONDecodeError as e:
                        logger.error("Invalid JSON: %s", str(e))
                        raise InvalidJSONError(
                            f"Error parsing JSON for variable '{name}': {str(e)}. Input was: {value}"
                        )
            except ValueError:
                raise VariableNameError(
                    f"Invalid JSON variable mapping format: {mapping}. Expected name=json"
                )

        # Run the async function synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            exit_code = loop.run_until_complete(run_cli_async(args))
        finally:
            loop.close()
        sys.exit(exit_code)

    except (CLIError, InvalidJSONError, VariableError) as e:
        logger.error("%s: %s", type(e).__name__, str(e))
        if isinstance(e, CLIError):
            sys.exit(e.exit_code)
        elif isinstance(e, InvalidJSONError):
            sys.exit(ExitCode.DATA_ERROR)
        elif isinstance(e, VariableError):
            sys.exit(ExitCode.VALIDATION_ERROR)
    except click.UsageError:
        raise  # Let Click handle usage errors
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(ExitCode.INTERNAL_ERROR)


async def run_cli_async(args: Namespace) -> int:
    """Async wrapper for CLI operations.

    Returns:
        Exit code to return from the CLI

    Raises:
        CLIError: For various error conditions
        KeyboardInterrupt: When operation is cancelled by user
    """
    try:
        # 0. Model Parameter Validation
        logger.debug("=== Model Parameter Validation ===")
        params = {
            "temperature": args.temperature,
            "max_output_tokens": args.max_output_tokens,
            "top_p": args.top_p,
            "frequency_penalty": args.frequency_penalty,
            "presence_penalty": args.presence_penalty,
            "reasoning_effort": args.reasoning_effort,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        validate_model_parameters(args.model, params)

        # 1. Input Validation Phase
        logger.debug("=== Input Validation Phase ===")
        security_manager = validate_security_manager(
            base_dir=args.base_dir,
            allowed_dirs=args.allowed_dir,
            allowed_dir_file=args.allowed_dir_file,
        )

        task_template = validate_task_template(args.task, args.task_file)
        logger.debug("Validating schema from %s", args.schema_file)
        schema = validate_schema_file(args.schema_file, args.verbose)
        template_context = create_template_context_from_args(
            args, security_manager
        )
        env = create_jinja_env()

        # 2. Template Processing Phase
        logger.debug("=== Template Processing Phase ===")
        system_prompt = process_system_prompt(
            task_template,
            args.system_prompt,
            args.system_prompt_file,
            template_context,
            env,
            args.ignore_task_sysprompt,
        )
        user_prompt = render_template(task_template, template_context, env)

        # 3. Model & Schema Validation Phase
        logger.debug("=== Model & Schema Validation Phase ===")
        try:
            output_model = create_dynamic_model(
                schema,
                show_schema=args.show_model_schema,
                debug_validation=args.debug_validation,
            )
            logger.debug("Successfully created output model")
        except (
            SchemaFileError,
            InvalidJSONError,
            SchemaValidationError,
            ModelCreationError,
        ) as e:
            logger.error("Schema error: %s", str(e))
            raise  # Let the error propagate with its context

        if not supports_structured_output(args.model):
            msg = f"Model {args.model} does not support structured output"
            logger.error(msg)
            raise ModelNotSupportedError(msg)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        total_tokens = estimate_tokens_with_encoding(messages, args.model)
        registry = ModelRegistry()
        capabilities = registry.get_capabilities(args.model)
        context_limit = capabilities.context_window

        if total_tokens > context_limit:
            msg = f"Total tokens ({total_tokens}) exceeds model context limit ({context_limit})"
            logger.error(msg)
            raise CLIError(
                msg,
                context={
                    "total_tokens": total_tokens,
                    "context_limit": context_limit,
                },
            )

        # 4. Dry Run Output Phase
        if args.dry_run:
            logger.info("\n=== Dry Run Summary ===")
            logger.info("✓ Template rendered successfully")
            logger.info("✓ Schema validation passed")
            logger.info("✓ Model compatibility validated")
            logger.info(f"✓ Token count: {total_tokens}/{context_limit}")

            if args.verbose:
                logger.info("\nSystem Prompt:")
                logger.info("-" * 40)
                logger.info(system_prompt)
                logger.info("\nRendered Template:")
                logger.info("-" * 40)
                logger.info(user_prompt)

            return ExitCode.SUCCESS

        # 5. Execution Phase
        logger.debug("=== Execution Phase ===")
        api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            msg = "No API key provided. Set OPENAI_API_KEY environment variable or use --api-key"
            logger.error(msg)
            raise CLIError(msg, exit_code=ExitCode.API_ERROR)

        client = AsyncOpenAI(api_key=api_key, timeout=args.timeout)

        # Create detailed log callback
        def log_callback(
            level: int, message: str, extra: dict[str, Any]
        ) -> None:
            if args.debug_openai_stream:
                if extra:
                    extra_str = LogSerializer.serialize_log_extra(extra)
                    if extra_str:
                        logger.debug("%s\nExtra:\n%s", message, extra_str)
                    else:
                        logger.debug("%s\nExtra: Failed to serialize", message)
                else:
                    logger.debug(message)

        try:
            # Create output buffer
            output_buffer = []

            # Stream the response
            async for response in stream_structured_output(
                client=client,
                model=args.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_model,
                output_file=args.output_file,
                **params,  # Only pass validated model parameters
                on_log=log_callback,  # Pass logging callback separately
            ):
                output_buffer.append(response)

            # Handle final output
            if args.output_file:
                with open(args.output_file, "w") as f:
                    json.dump(output_buffer, f)

            return ExitCode.SUCCESS

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

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        raise
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
        cli = create_cli()
        cli(standalone_mode=False)
    except Exception as e:
        handle_error(e)
        sys.exit(1)


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


def create_dynamic_model(
    schema: Dict[str, Any],
    base_name: str = "DynamicModel",
    show_schema: bool = False,
    debug_validation: bool = False,
) -> Type[BaseModel]:
    """Create a Pydantic model from a JSON schema.

    Args:
        schema: JSON schema dict, can be wrapped in {"schema": ...} format
        base_name: Base name for the model
        show_schema: Whether to show the generated schema
        debug_validation: Whether to enable validation debugging

    Returns:
        Generated Pydantic model class

    Raises:
        ModelCreationError: When model creation fails
        SchemaValidationError: When schema is invalid
    """
    if debug_validation:
        logger.info("Creating dynamic model from schema:")
        logger.info(json.dumps(schema, indent=2))

    try:
        # Extract required fields
        required: Set[str] = set(schema.get("required", []))

        # Handle our wrapper format if present
        if "schema" in schema:
            if debug_validation:
                logger.info("Found schema wrapper, extracting inner schema")
                logger.info(
                    "Original schema: %s", json.dumps(schema, indent=2)
                )
            inner_schema = schema["schema"]
            if not isinstance(inner_schema, dict):
                if debug_validation:
                    logger.info(
                        "Inner schema must be a dictionary, got %s",
                        type(inner_schema),
                    )
                raise SchemaValidationError(
                    "Inner schema must be a dictionary"
                )
            if debug_validation:
                logger.info("Using inner schema:")
                logger.info(json.dumps(inner_schema, indent=2))
            schema = inner_schema

        # Ensure schema has type field
        if "type" not in schema:
            if debug_validation:
                logger.info("Schema missing type field, assuming object type")
            schema["type"] = "object"

        # For non-object root schemas, create a wrapper model
        if schema["type"] != "object":
            if debug_validation:
                logger.info(
                    "Converting non-object root schema to object wrapper"
                )
            schema = {
                "type": "object",
                "properties": {"value": schema},
                "required": ["value"],
            }

        # Create model configuration
        config = ConfigDict(
            title=schema.get("title", base_name),
            extra=(
                "forbid"
                if schema.get("additionalProperties") is False
                else "allow"
            ),
            validate_default=True,
            use_enum_values=True,
            arbitrary_types_allowed=True,
            json_schema_extra={
                k: v
                for k, v in schema.items()
                if k
                not in {
                    "type",
                    "properties",
                    "required",
                    "title",
                    "description",
                    "additionalProperties",
                    "readOnly",
                }
            },
        )

        if debug_validation:
            logger.info("Created model configuration:")
            logger.info("  Title: %s", config.get("title"))
            logger.info("  Extra: %s", config.get("extra"))
            logger.info(
                "  Validate Default: %s", config.get("validate_default")
            )
            logger.info("  Use Enum Values: %s", config.get("use_enum_values"))
            logger.info(
                "  Arbitrary Types: %s", config.get("arbitrary_types_allowed")
            )
            logger.info(
                "  JSON Schema Extra: %s", config.get("json_schema_extra")
            )

        # Create field definitions
        field_definitions: Dict[str, FieldDefinition] = {}
        properties = schema.get("properties", {})

        for field_name, field_schema in properties.items():
            try:
                if debug_validation:
                    logger.info("Processing field %s:", field_name)
                    logger.info(
                        "  Schema: %s", json.dumps(field_schema, indent=2)
                    )

                python_type, field = _get_type_with_constraints(
                    field_schema, field_name, base_name
                )

                # Handle optional fields
                if field_name not in required:
                    if debug_validation:
                        logger.info(
                            "Field %s is optional, wrapping in Optional",
                            field_name,
                        )
                    field_type = cast(Type[Any], Optional[python_type])
                else:
                    field_type = python_type
                    if debug_validation:
                        logger.info("Field %s is required", field_name)

                # Create field definition
                field_definitions[field_name] = (field_type, field)

                if debug_validation:
                    logger.info("Successfully created field definition:")
                    logger.info("  Name: %s", field_name)
                    logger.info("  Type: %s", str(field_type))
                    logger.info("  Required: %s", field_name in required)

            except (FieldDefinitionError, NestedModelError) as e:
                if debug_validation:
                    logger.error("Error creating field %s:", field_name)
                    logger.error("  Error type: %s", type(e).__name__)
                    logger.error("  Error message: %s", str(e))
                raise ModelValidationError(base_name, [str(e)])

        # Create the model with the fields
        field_defs: dict[str, tuple[type[Any], FieldInfoType]] = {
            name: (field_type, field)
            for name, (field_type, field) in field_definitions.items()
        }

        # Create model with explicit type casting
        model: Type[BaseModel] = cast(
            Type[BaseModel],
            create_model(  # type: ignore[call-overload]
                base_name,
                __base__=BaseModel,
                model_config=config,
                __module__=__name__,
                **field_defs,
            ),
        )

        if debug_validation:
            logger.info("Successfully created model: %s", model.__name__)
            logger.info("Model config: %s", dict(model.model_config))
            logger.info(
                "Model schema: %s",
                json.dumps(model.model_json_schema(), indent=2),
            )

        # Validate the model's JSON schema
        try:
            model.model_json_schema()
        except ValidationError as e:
            if debug_validation:
                logger.error("Schema validation failed:")
                logger.error("  Error type: %s", type(e).__name__)
                logger.error("  Error message: %s", str(e))
            validation_errors = (
                [str(err) for err in e.errors()]
                if hasattr(e, "errors")
                else [str(e)]
            )
            raise ModelValidationError(base_name, validation_errors)

        return model

    except Exception as e:
        if debug_validation:
            logger.error("Failed to create model:")
            logger.error("  Error type: %s", type(e).__name__)
            logger.error("  Error message: %s", str(e))
            if hasattr(e, "__cause__"):
                logger.error("  Caused by: %s", str(e.__cause__))
            if hasattr(e, "__context__"):
                logger.error("  Context: %s", str(e.__context__))
            if hasattr(e, "__traceback__"):
                import traceback

                logger.error(
                    "  Traceback:\n%s",
                    "".join(traceback.format_tb(e.__traceback__)),
                )
        raise ModelCreationError(
            f"Failed to create model '{base_name}': {str(e)}"
        )


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


if __name__ == "__main__":
    main()
