"""Command-line interface for making structured OpenAI API calls."""

import asyncio
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
    StreamBufferError,
)
from openai_structured.model_registry import ModelRegistry
from pydantic import AnyUrl, BaseModel, EmailStr, Field
from pydantic.fields import FieldInfo as FieldInfoType
from pydantic.functional_validators import BeforeValidator
from pydantic.types import constr
from typing_extensions import TypeAlias

from ostruct.cli.click_options import all_options
from ostruct.cli.exit_codes import ExitCode

from .. import __version__  # noqa: F401 - Used in package metadata
from .errors import (
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
from .file_utils import FileInfoList, collect_files
from .model_creation import _create_enum_type, create_dynamic_model
from .path_utils import validate_path_mapping
from .security import SecurityManager
from .serialization import LogSerializer
from .template_env import create_jinja_env
from .template_utils import (
    SystemPromptError,
    render_template,
    validate_json_schema,
)
from .token_utils import estimate_tokens_with_encoding

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

    files: List[
        Tuple[str, str]
    ]  # List of (name, path) tuples from Click's nargs=2
    dir: List[
        Tuple[str, str]
    ]  # List of (name, dir) tuples from Click's nargs=2
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
        except OstructFileNotFoundError as e:
            raise SystemPromptError(
                f"Failed to load system prompt file: {e}"
            ) from e
        except PathSecurityError as e:
            raise SystemPromptError(f"Invalid system prompt file: {e}") from e

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
            raise TaskTemplateVariableError(
                f"Error reading task template file: {e}"
            )
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
        files = list(
            args.get("files", [])
        )  # List of (name, path) tuples from Click
        dirs = args.get("dir", [])  # List of (name, dir) tuples from Click
        patterns = args.get(
            "patterns", []
        )  # List of (name, pattern) tuples from Click

        # Collect files from directories and patterns
        dir_files = collect_files(
            file_mappings=cast(List[Tuple[str, Union[str, Path]]], files),
            dir_mappings=cast(List[Tuple[str, Union[str, Path]]], dirs),
            pattern_mappings=cast(
                List[Tuple[str, Union[str, Path]]], patterns
            ),
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
                    name, value = (
                        mapping  # Value is already parsed by Click validator
                    )
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
                "Error details:\n"
                f"Type: {type(e).__name__}\n"
                f"{context_str.rstrip()}"
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

    except APIResponseError as e:
        if "Invalid schema for response_format" in str(
            e
        ) and 'type: "array"' in str(e):
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
        logger.error(f"API error: {e}")
        raise
    except (
        StreamInterruptedError,
        StreamBufferError,
        StreamParseError,
        EmptyResponseError,
        InvalidResponseFormatError,
    ) as e:
        logger.error("Stream error: %s", str(e))
        raise
    finally:
        # Always ensure client is properly closed
        await client.close()


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """ostruct CLI - Make structured OpenAI API calls.

    ostruct allows you to invoke OpenAI Structured Output to produce structured JSON
    output using templates and JSON schemas. It provides support for file handling, variable
    substitution, and output validation.

    For detailed documentation, visit: https://ostruct.readthedocs.io

    Examples:

        # Basic usage with a template and schema

        ostruct run task.j2 schema.json -V name=value

        # Process files with recursive directory scanning

        ostruct run template.j2 schema.json -f code main.py -d src ./src -R

        # Use JSON variables and custom model parameters

        ostruct run task.j2 schema.json -J config='{"env":"prod"}' -m o3-mini
    """
    pass


@cli.command()
@click.argument("task_template", type=click.Path(exists=True))
@click.argument("schema_file", type=click.Path(exists=True))
@all_options
@click.pass_context
def run(
    ctx: click.Context,
    task_template: str,
    schema_file: str,
    **kwargs: Any,
) -> None:
    """Run a structured task with template and schema.

    Args:
        ctx: Click context
        task_template: Path to task template file
        schema_file: Path to schema file
        **kwargs: Additional CLI options
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
                logger.debug(
                    "Error context: %s", json.dumps(e.context, indent=2)
                )
            # Re-raise to preserve error chain and exit code
            raise
        except (CLIError, InvalidJSONError, SchemaFileError) as e:
            handle_error(e)
            sys.exit(
                e.exit_code
                if hasattr(e, "exit_code")
                else ExitCode.INTERNAL_ERROR
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


# Remove the old @create_click_command() decorator and cli function definition
# Keep all the other functions and code below this point


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
    SecurityManager, str, Dict[str, Any], Dict[str, Any], jinja2.Environment
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

    task_template = validate_task_template(
        args.get("task"), args.get("task_file")
    )

    # Load and validate schema
    logger.debug("Validating schema from %s", args["schema_file"])
    try:
        schema = validate_schema_file(
            args["schema_file"], args.get("verbose", False)
        )

        # Validate schema structure before any model creation
        validate_json_schema(
            schema
        )  # This will raise SchemaValidationError if invalid
    except SchemaValidationError as e:
        logger.error("Schema validation error: %s", str(e))
        raise  # Re-raise the SchemaValidationError to preserve the error chain

    template_context = await create_template_context_from_args(
        args, security_manager
    )
    env = create_jinja_env()

    return security_manager, task_template, schema, template_context, env


async def process_templates(
    args: CLIParams,
    task_template: str,
    template_context: Dict[str, Any],
    env: jinja2.Environment,
) -> Tuple[str, str]:
    """Process system prompt and user prompt templates.

    Args:
        args: Command line arguments
        task_template: Validated task template
        template_context: Template context dictionary
        env: Jinja2 environment

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
    )
    user_prompt = render_template(task_template, template_context, env)
    return system_prompt, user_prompt


async def validate_model_and_schema(
    args: CLIParams,
    schema: Dict[str, Any],
    system_prompt: str,
    user_prompt: str,
) -> Tuple[Type[BaseModel], List[Dict[str, str]], int, ModelRegistry]:
    """Validate model compatibility and schema, and check token limits.

    Args:
        args: Command line arguments
        schema: Schema dictionary
        system_prompt: Processed system prompt
        user_prompt: Processed user prompt

    Returns:
        Tuple of (output_model, messages, total_tokens, registry)

    Raises:
        CLIError: For validation errors
        ModelCreationError: When model creation fails
        SchemaValidationError: When schema is invalid
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
    registry = ModelRegistry()
    capabilities = registry.get_capabilities(args["model"])
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

    return output_model, messages, total_tokens, registry


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
    """
    logger.debug("=== Execution Phase ===")
    api_key = args.get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "No API key provided. Set OPENAI_API_KEY environment variable or use --api-key"
        logger.error(msg)
        raise CLIError(msg, exit_code=ExitCode.API_ERROR)

    client = AsyncOpenAI(api_key=api_key, timeout=args.get("timeout", 60.0))

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

    try:
        # Create output buffer
        output_buffer = []

        # Stream the response
        async for response in stream_structured_output(
            client=client,
            model=args["model"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_model,
            output_file=args.get("output_file"),
            on_log=log_callback,
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
                    json_output += "  " + response.model_dump_json(
                        indent=2
                    ).replace("\n", "\n  ")
                json_output += "\n]"
                print(json_output)

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
    finally:
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
        # 0. Model Parameter Validation
        logger.debug("=== Model Parameter Validation ===")
        params = await validate_model_params(args)

        # 1. Input Validation Phase (includes schema validation)
        security_manager, task_template, schema, template_context, env = (
            await validate_inputs(args)
        )

        # 2. Template Processing Phase
        system_prompt, user_prompt = await process_templates(
            args, task_template, template_context, env
        )

        # 3. Model & Schema Validation Phase
        output_model, messages, total_tokens, registry = (
            await validate_model_and_schema(
                args, schema, system_prompt, user_prompt
            )
        )

        # 4. Dry Run Output Phase - Moved after all validations
        if args.get("dry_run", False):
            logger.info("\n=== Dry Run Summary ===")
            # Only log success if we got this far (no validation errors)
            logger.info("✓ Template rendered successfully")
            logger.info("✓ Schema validation passed")

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
        sys.exit(
            e.exit_code if hasattr(e, "exit_code") else ExitCode.INTERNAL_ERROR
        )
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
