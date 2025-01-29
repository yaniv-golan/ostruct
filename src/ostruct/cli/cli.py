"""Command-line interface for making structured OpenAI API calls."""

import argparse
import asyncio
import json
import logging
import os
import sys
from enum import Enum, IntEnum

if sys.version_info >= (3, 11):
    from enum import StrEnum

from datetime import date, datetime, time
from pathlib import Path
from typing import (
    Any,
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

import jinja2
import tiktoken
import yaml
from openai import (
    APIConnectionError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
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

from .. import __version__
from .errors import (
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
from .progress import ProgressContext
from .security import SecurityManager
from .template_env import create_jinja_env
from .template_utils import SystemPromptError, render_template

# Constants
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."

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


class ExitCode(IntEnum):
    """Exit codes for the CLI following standard Unix conventions.

    Categories:
    - Success (0-1)
    - User Interruption (2-3)
    - Input/Validation (64-69)
    - I/O and File Access (70-79)
    - API and External Services (80-89)
    - Internal Errors (90-99)
    """

    # Success codes
    SUCCESS = 0

    # User interruption
    INTERRUPTED = 2

    # Input/Validation errors (64-69)
    USAGE_ERROR = 64
    DATA_ERROR = 65
    SCHEMA_ERROR = 66
    VALIDATION_ERROR = 67

    # I/O and File Access errors (70-79)
    IO_ERROR = 70
    FILE_NOT_FOUND = 71
    PERMISSION_ERROR = 72
    SECURITY_ERROR = 73

    # API and External Service errors (80-89)
    API_ERROR = 80
    API_TIMEOUT = 81

    # Internal errors (90-99)
    INTERNAL_ERROR = 90
    UNKNOWN_ERROR = 91


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
    field_type = field_schema.get("type")
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

    # Handle array type
    if field_type == "array":
        items_schema = field_schema.get("items", {})
        if not items_schema:
            return (List[Any], Field(**field_kwargs))

        # Create nested model with explicit type annotation
        array_item_model = create_dynamic_model(
            items_schema,
            base_name=f"{base_name}_{field_name}_Item",
            show_schema=False,
            debug_validation=False,
        )
        array_type: Type[List[Any]] = List[array_item_model]  # type: ignore[valid-type]
        return (array_type, Field(**field_kwargs))

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


def estimate_tokens_for_chat(
    messages: List[Dict[str, str]], model: str
) -> int:
    """Estimate the number of tokens in a chat completion."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to cl100k_base for unknown models
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0
    for message in messages:
        # Add message overhead
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(encoding.encode(str(value)))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


def get_default_token_limit(model: str) -> int:
    """Get the default token limit for a given model.

    Note: These limits are based on current OpenAI model specifications as of 2024 and may
    need to be updated if OpenAI changes the models' capabilities.

    Args:
        model: The model name (e.g., 'gpt-4o', 'gpt-4o-mini', 'o1')

    Returns:
        The default token limit for the model
    """
    if "o1" in model:
        return 100_000  # o1 supports up to 100K output tokens
    elif "gpt-4o" in model:
        return 16_384  # gpt-4o and gpt-4o-mini support up to 16K output tokens
    else:
        return 4_096  # default fallback


def get_context_window_limit(model: str) -> int:
    """Get the total context window limit for a given model.

    Note: These limits are based on current OpenAI model specifications as of 2024 and may
    need to be updated if OpenAI changes the models' capabilities.

    Args:
        model: The model name (e.g., 'gpt-4o', 'gpt-4o-mini', 'o1')

    Returns:
        The context window limit for the model
    """
    if "o1" in model:
        return 200_000  # o1 supports 200K total context window
    elif "gpt-4o" in model:
        return 128_000  # gpt-4o and gpt-4o-mini support 128K context window
    else:
        return 8_192  # default fallback


def validate_token_limits(
    model: str, total_tokens: int, max_token_limit: Optional[int] = None
) -> None:
    """Validate token counts against model limits.

    Args:
        model: The model name
        total_tokens: Total number of tokens in the prompt
        max_token_limit: Optional user-specified token limit

    Raises:
        ValueError: If token limits are exceeded
    """
    context_limit = get_context_window_limit(model)
    output_limit = (
        max_token_limit
        if max_token_limit is not None
        else get_default_token_limit(model)
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
    template_context: Dict[str, Any],
    env: jinja2.Environment,
    ignore_task_sysprompt: bool = False,
) -> str:
    """Process system prompt from various sources.

    Args:
        task_template: The task template string
        system_prompt: Optional system prompt string or file path (with @ prefix)
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

    # Try to get system prompt from CLI argument first
    if system_prompt:
        if system_prompt.startswith("@"):
            # Load from file
            path = system_prompt[1:]
            try:
                name, path = validate_path_mapping(f"system_prompt={path}")
                with open(path, "r", encoding="utf-8") as f:
                    system_prompt = f.read().strip()
            except (FileNotFoundError, PathSecurityError) as e:
                raise SystemPromptError(f"Invalid system prompt file: {e}")

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
    try:
        if not mapping or "=" not in mapping:
            raise ValueError(
                "Invalid path mapping format. Expected format: name=path"
            )

        name, path = mapping.split("=", 1)
        if not name:
            raise VariableNameError(
                f"Empty name in {'directory' if is_dir else 'file'} mapping"
            )

        if not path:
            raise VariableValueError("Path cannot be empty")

        # Convert to Path object and resolve against base_dir if provided
        path_obj = Path(path)
        if base_dir:
            path_obj = Path(base_dir) / path_obj

        # Resolve the path to catch directory traversal attempts
        try:
            resolved_path = path_obj.resolve()
        except OSError as e:
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
            if not security_manager.is_allowed_file(str(resolved_path)):
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


def validate_task_template(task: str) -> str:
    """Validate and load a task template.

    Args:
        task: The task template string or path to task template file (with @ prefix)

    Returns:
        The task template string

    Raises:
        TaskTemplateVariableError: If the template file cannot be read or is invalid
        TaskTemplateSyntaxError: If the template has invalid syntax
        FileNotFoundError: If the template file does not exist
        PathSecurityError: If the template file path violates security constraints
    """
    template_content = task

    # Check if task is a file path
    if task.startswith("@"):
        path = task[1:]
        try:
            name, path = validate_path_mapping(f"task={path}")
            with open(path, "r", encoding="utf-8") as f:
                template_content = f.read()
        except (FileNotFoundError, PathSecurityError) as e:
            raise TaskTemplateVariableError(f"Invalid task template file: {e}")

    # Validate template syntax
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
    """Validate a JSON schema file.

    Args:
        path: Path to the schema file
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
        with open(path) as f:
            schema = json.load(f)
    except FileNotFoundError:
        raise SchemaFileError(f"Schema file not found: {path}")
    except json.JSONDecodeError as e:
        raise InvalidJSONError(f"Invalid JSON in schema file: {e}")
    except Exception as e:
        raise SchemaFileError(f"Failed to read schema file: {e}")

    # Pre-validation structure checks
    if verbose:
        logger.info("Performing pre-validation structure checks")
        logger.debug("Loaded schema: %s", json.dumps(schema, indent=2))

    if not isinstance(schema, dict):
        if verbose:
            logger.error(
                "Schema is not a dictionary: %s", type(schema).__name__
            )
        raise SchemaValidationError("Schema must be a JSON object")

    # Validate schema structure
    if "schema" in schema:
        if verbose:
            logger.debug("Found schema wrapper, validating inner schema")
        inner_schema = schema["schema"]
        if not isinstance(inner_schema, dict):
            if verbose:
                logger.error(
                    "Inner schema is not a dictionary: %s",
                    type(inner_schema).__name__,
                )
            raise SchemaValidationError("Inner schema must be a JSON object")
        if verbose:
            logger.debug("Inner schema validated successfully")
    else:
        if verbose:
            logger.debug("No schema wrapper found, using schema as-is")

    # Return the full schema including wrapper
    return schema


def collect_template_files(
    args: argparse.Namespace,
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
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            raise e.__cause__
        # Wrap unexpected errors
        raise ValueError(f"Error collecting files: {e}")


def collect_simple_variables(args: argparse.Namespace) -> Dict[str, str]:
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


def collect_json_variables(args: argparse.Namespace) -> Dict[str, Any]:
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
                        f"Invalid JSON value for {name}: {str(e)}"
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
            # For single files, extract the first FileInfo object
            if len(file_list) == 1:
                context[name] = file_list[0]
            else:
                context[name] = file_list

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
    args: argparse.Namespace,
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
                            f"Invalid JSON value for {name} ({value!r}): {str(e)}"
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

        return create_template_context(
            files=files,
            variables=variables,
            json_variables=json_variables,
            security_manager=security_manager,
            stdin_content=stdin_content,
        )

    except PathSecurityError:
        # Let PathSecurityError propagate without wrapping
        raise
    except (FileNotFoundError, DirectoryNotFoundError) as e:
        # Wrap file-related errors
        raise ValueError(f"File access error: {e}")
    except Exception as e:
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            raise e.__cause__
        # Wrap unexpected errors
        raise ValueError(f"Error collecting files: {e}")


def validate_security_manager(
    base_dir: Optional[str] = None,
    allowed_dirs: Optional[List[str]] = None,
    allowed_dirs_file: Optional[str] = None,
) -> SecurityManager:
    """Create and validate a security manager.

    Args:
        base_dir: Optional base directory to resolve paths against
        allowed_dirs: Optional list of allowed directory paths
        allowed_dirs_file: Optional path to file containing allowed directories

    Returns:
        Configured SecurityManager instance

    Raises:
        FileNotFoundError: If allowed_dirs_file does not exist
        PathSecurityError: If any paths are outside base directory
    """
    # Convert base_dir to string if it's a Path
    base_dir_str = str(base_dir) if base_dir else None
    security_manager = SecurityManager(base_dir_str)

    if allowed_dirs_file:
        security_manager.add_allowed_dirs_from_file(str(allowed_dirs_file))

    if allowed_dirs:
        for allowed_dir in allowed_dirs:
            security_manager.add_allowed_dir(str(allowed_dir))

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
                f"Invalid JSON value for variable {name!r}: {json_str!r}"
            ) from e

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


def create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="Make structured OpenAI API calls.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Debug output options
    debug_group = parser.add_argument_group("Debug Output Options")
    debug_group.add_argument(
        "--show-model-schema",
        action="store_true",
        help="Display the generated Pydantic model schema",
    )
    debug_group.add_argument(
        "--debug-validation",
        action="store_true",
        help="Show detailed schema validation debugging information",
    )
    debug_group.add_argument(
        "--verbose-schema",
        action="store_true",
        help="Enable verbose schema debugging output",
    )
    debug_group.add_argument(
        "--progress-level",
        choices=["none", "basic", "detailed"],
        default="basic",
        help="Set the level of progress reporting (default: basic)",
    )

    # Required arguments
    parser.add_argument(
        "--task",
        required=True,
        help="Task template string or @file",
    )

    # File access arguments
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Map file to variable (name=path)",
        metavar="NAME=PATH",
    )
    parser.add_argument(
        "--files",
        action="append",
        default=[],
        help="Map file pattern to variable (name=pattern)",
        metavar="NAME=PATTERN",
    )
    parser.add_argument(
        "--dir",
        action="append",
        default=[],
        help="Map directory to variable (name=path)",
        metavar="NAME=PATH",
    )
    parser.add_argument(
        "--allowed-dir",
        action="append",
        default=[],
        help="Additional allowed directory or @file",
        metavar="PATH",
    )
    parser.add_argument(
        "--base-dir",
        help="Base directory for file access (defaults to current directory)",
        default=os.getcwd(),
    )
    parser.add_argument(
        "--allowed-dirs-file",
        help="File containing list of allowed directories",
    )
    parser.add_argument(
        "--dir-recursive",
        action="store_true",
        help="Process directories recursively",
    )
    parser.add_argument(
        "--dir-ext",
        help="Comma-separated list of file extensions to include in directory processing",
    )

    # Variable arguments
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        help="Pass simple variables (name=value)",
        metavar="NAME=VALUE",
    )
    parser.add_argument(
        "--json-var",
        action="append",
        default=[],
        help="Pass JSON variables (name=json)",
        metavar="NAME=JSON",
    )

    # System prompt options
    parser.add_argument(
        "--system-prompt",
        help=(
            "System prompt for the model (use @file to load from file, "
            "can also be specified in task template YAML frontmatter)"
        ),
        default=DEFAULT_SYSTEM_PROMPT,
    )
    parser.add_argument(
        "--ignore-task-sysprompt",
        action="store_true",
        help="Ignore system prompt from task template YAML frontmatter",
    )

    # Schema validation
    parser.add_argument(
        "--schema",
        dest="schema_file",
        required=True,
        help="JSON schema file for response validation",
    )
    parser.add_argument(
        "--validate-schema",
        action="store_true",
        help="Validate schema and response",
    )

    # Model configuration
    parser.add_argument(
        "--model",
        default="gpt-4o-2024-08-06",
        help="Model to use",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature (0.0-2.0)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Maximum tokens to generate",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Top-p sampling (0.0-1.0)",
    )
    parser.add_argument(
        "--frequency-penalty",
        type=float,
        default=0.0,
        help="Frequency penalty (-2.0-2.0)",
    )
    parser.add_argument(
        "--presence-penalty",
        type=float,
        default=0.0,
        help="Presence penalty (-2.0-2.0)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="API timeout in seconds",
    )

    # Output options
    parser.add_argument(
        "--output-file",
        help="Write JSON output to file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate API call without making request",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress indicators",
    )

    # Other options
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (overrides env var)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--debug-openai-stream",
        action="store_true",
        help="Enable low-level debug output for OpenAI streaming (very verbose)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


async def _main() -> ExitCode:
    """Main CLI function.

    Returns:
        ExitCode: Exit code indicating success or failure
    """
    try:
        parser = create_argument_parser()
        args = parser.parse_args()

        # Configure logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logger.setLevel(log_level)

        # Create security manager
        security_manager = validate_security_manager(
            base_dir=args.base_dir,
            allowed_dirs=args.allowed_dir,
            allowed_dirs_file=args.allowed_dirs_file,
        )

        # Validate task template
        task_template = validate_task_template(args.task)

        # Validate schema file
        schema = validate_schema_file(args.schema_file, args.verbose)

        # Create template context
        template_context = create_template_context_from_args(
            args, security_manager
        )

        # Create Jinja environment
        env = create_jinja_env()

        # Process system prompt
        args.system_prompt = process_system_prompt(
            task_template,
            args.system_prompt,
            template_context,
            env,
            args.ignore_task_sysprompt,
        )

        # Render task template
        rendered_task = render_template(task_template, template_context, env)
        logger.info(rendered_task)  # Log the rendered template

        # If dry run, exit here
        if args.dry_run:
            logger.info("DRY RUN MODE")
            return ExitCode.SUCCESS

        # Load and validate schema
        try:
            logger.debug("[_main] Loading schema from %s", args.schema_file)
            schema = validate_schema_file(
                args.schema_file, verbose=args.verbose_schema
            )
            logger.debug("[_main] Creating output model")
            output_model = create_dynamic_model(
                schema,
                base_name="OutputModel",
                show_schema=args.show_model_schema,
                debug_validation=args.debug_validation,
            )
            logger.debug("[_main] Successfully created output model")
        except (SchemaFileError, InvalidJSONError, SchemaValidationError) as e:
            logger.error(str(e))
            return ExitCode.SCHEMA_ERROR
        except ModelCreationError as e:
            logger.error(f"Model creation error: {e}")
            return ExitCode.SCHEMA_ERROR
        except Exception as e:
            logger.error(f"Unexpected error creating model: {e}")
            return ExitCode.SCHEMA_ERROR

        # Validate model support
        try:
            supports_structured_output(args.model)
        except ModelNotSupportedError as e:
            logger.error(str(e))
            return ExitCode.DATA_ERROR
        except ModelVersionError as e:
            logger.error(str(e))
            return ExitCode.DATA_ERROR

        # Estimate token usage
        messages = [
            {"role": "system", "content": args.system_prompt},
            {"role": "user", "content": rendered_task},
        ]
        total_tokens = estimate_tokens_for_chat(messages, args.model)
        context_limit = get_context_window_limit(args.model)

        if total_tokens > context_limit:
            logger.error(
                f"Total tokens ({total_tokens}) exceeds model context limit ({context_limit})"
            )
            return ExitCode.DATA_ERROR

        # Get API key
        api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error(
                "No OpenAI API key provided (--api-key or OPENAI_API_KEY env var)"
            )
            return ExitCode.USAGE_ERROR

        # Create OpenAI client
        client = AsyncOpenAI(api_key=api_key, timeout=args.timeout)

        # Create log callback that matches expected signature
        def log_callback(
            level: int, message: str, extra: dict[str, Any]
        ) -> None:
            # Only log if debug_openai_stream is enabled
            if args.debug_openai_stream:
                # Include extra dictionary in the message for both DEBUG and ERROR
                if extra:  # Only add if there's actually extra data
                    extra_str = json.dumps(extra, indent=2)
                    message = f"{message}\nDetails:\n{extra_str}"
                openai_logger.log(level, message, extra=extra)

        # Make API request
        try:
            logger.debug("Creating ProgressContext for API response handling")
            with ProgressContext(
                description="Processing API response",
                level=args.progress_level,
            ) as progress:
                logger.debug("Starting API response stream processing")
                logger.debug("Debug flag status: %s", args.debug_openai_stream)
                logger.debug("OpenAI logger level: %s", openai_logger.level)
                for handler in openai_logger.handlers:
                    logger.debug("Handler level: %s", handler.level)
                async for chunk in async_openai_structured_stream(
                    client=client,
                    model=args.model,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    top_p=args.top_p,
                    frequency_penalty=args.frequency_penalty,
                    presence_penalty=args.presence_penalty,
                    system_prompt=args.system_prompt,
                    user_prompt=rendered_task,
                    output_schema=output_model,
                    timeout=args.timeout,
                    on_log=log_callback,
                ):
                    logger.debug("Received API response chunk")
                    if not chunk:
                        logger.debug("Empty chunk received, skipping")
                        continue

                    # Write output
                    try:
                        logger.debug("Starting to process output chunk")
                        dumped = chunk.model_dump(mode="json")
                        logger.debug("Successfully dumped chunk to JSON")
                        logger.debug("Dumped chunk: %s", dumped)
                        logger.debug(
                            "Chunk type: %s, length: %d",
                            type(dumped),
                            len(json.dumps(dumped)),
                        )

                        if args.output_file:
                            logger.debug(
                                "Writing to output file: %s", args.output_file
                            )
                            try:
                                with open(
                                    args.output_file, "a", encoding="utf-8"
                                ) as f:
                                    json_str = json.dumps(dumped, indent=2)
                                    logger.debug(
                                        "Writing JSON string of length %d",
                                        len(json_str),
                                    )
                                    f.write(json_str)
                                    f.write("\n")
                                    logger.debug("Successfully wrote to file")
                            except Exception as e:
                                logger.error(
                                    "Failed to write to output file: %s", e
                                )
                        else:
                            logger.debug(
                                "About to call progress.print_output with JSON string"
                            )
                            json_str = json.dumps(dumped, indent=2)
                            logger.debug(
                                "JSON string length before print_output: %d",
                                len(json_str),
                            )
                            logger.debug(
                                "First 100 chars of JSON string: %s",
                                json_str[:100] if json_str else "",
                            )
                            progress.print_output(json_str)
                            logger.debug(
                                "Completed print_output call for JSON string"
                            )

                        logger.debug("Starting progress update")
                        progress.update()
                        logger.debug("Completed progress update")
                    except Exception as e:
                        logger.error("Failed to process chunk: %s", e)
                        logger.error("Chunk: %s", chunk)
                        continue

                logger.debug("Finished processing API response stream")

        except StreamInterruptedError as e:
            logger.error(f"Stream interrupted: {e}")
            return ExitCode.API_ERROR
        except StreamBufferError as e:
            logger.error(f"Stream buffer error: {e}")
            return ExitCode.API_ERROR
        except StreamParseError as e:
            logger.error(f"Stream parse error: {e}")
            return ExitCode.API_ERROR
        except APIResponseError as e:
            logger.error(f"API response error: {e}")
            return ExitCode.API_ERROR
        except EmptyResponseError as e:
            logger.error(f"Empty response error: {e}")
            return ExitCode.API_ERROR
        except InvalidResponseFormatError as e:
            logger.error(f"Invalid response format: {e}")
            return ExitCode.API_ERROR
        except (APIConnectionError, InternalServerError) as e:
            logger.error(f"API connection error: {e}")
            return ExitCode.API_ERROR
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return ExitCode.API_ERROR
        except BadRequestError as e:
            logger.error(f"Bad request: {e}")
            return ExitCode.API_ERROR
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return ExitCode.API_ERROR
        except OpenAIClientError as e:
            logger.error(f"OpenAI client error: {e}")
            return ExitCode.API_ERROR
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return ExitCode.INTERNAL_ERROR

        return ExitCode.SUCCESS

    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        return ExitCode.INTERRUPTED
    except PathSecurityError as e:
        # Only log security errors if they haven't been logged already
        logger.debug(
            "[_main] Caught PathSecurityError: %s (logged=%s)",
            str(e),
            getattr(e, "has_been_logged", False),
        )
        if not getattr(e, "has_been_logged", False):
            logger.error(str(e))
        return ExitCode.SECURITY_ERROR
    except ValueError as e:
        # Get the original cause of the error
        cause = e.__cause__ or e.__context__
        if isinstance(cause, PathSecurityError):
            logger.debug(
                "[_main] Caught wrapped PathSecurityError in ValueError: %s (logged=%s)",
                str(cause),
                getattr(cause, "has_been_logged", False),
            )
            # Only log security errors if they haven't been logged already
            if not getattr(cause, "has_been_logged", False):
                logger.error(str(cause))
            return ExitCode.SECURITY_ERROR
        else:
            logger.debug("[_main] Caught ValueError: %s", str(e))
            logger.error(f"Invalid input: {e}")
            return ExitCode.DATA_ERROR
    except Exception as e:
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            logger.debug(
                "[_main] Caught wrapped PathSecurityError in Exception: %s (logged=%s)",
                str(e.__cause__),
                getattr(e.__cause__, "has_been_logged", False),
            )
            # Only log security errors if they haven't been logged already
            if not getattr(e.__cause__, "has_been_logged", False):
                logger.error(str(e.__cause__))
            return ExitCode.SECURITY_ERROR
        logger.debug("[_main] Caught unexpected error: %s", str(e))
        logger.error(f"Unexpected error: {e}")
        return ExitCode.INTERNAL_ERROR


def main() -> None:
    """CLI entry point that handles all errors."""
    try:
        logger.debug("[main] Starting main execution")
        exit_code = asyncio.run(_main())
        sys.exit(exit_code.value)
    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        sys.exit(ExitCode.INTERRUPTED.value)
    except PathSecurityError as e:
        # Only log security errors if they haven't been logged already
        logger.debug(
            "[main] Caught PathSecurityError: %s (logged=%s)",
            str(e),
            getattr(e, "has_been_logged", False),
        )
        if not getattr(e, "has_been_logged", False):
            logger.error(str(e))
        sys.exit(ExitCode.SECURITY_ERROR.value)
    except ValueError as e:
        # Get the original cause of the error
        cause = e.__cause__ or e.__context__
        if isinstance(cause, PathSecurityError):
            logger.debug(
                "[main] Caught wrapped PathSecurityError in ValueError: %s (logged=%s)",
                str(cause),
                getattr(cause, "has_been_logged", False),
            )
            # Only log security errors if they haven't been logged already
            if not getattr(cause, "has_been_logged", False):
                logger.error(str(cause))
            sys.exit(ExitCode.SECURITY_ERROR.value)
        else:
            logger.debug("[main] Caught ValueError: %s", str(e))
            logger.error(f"Invalid input: {e}")
            sys.exit(ExitCode.DATA_ERROR.value)
    except Exception as e:
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            logger.debug(
                "[main] Caught wrapped PathSecurityError in Exception: %s (logged=%s)",
                str(e.__cause__),
                getattr(e.__cause__, "has_been_logged", False),
            )
            # Only log security errors if they haven't been logged already
            if not getattr(e.__cause__, "has_been_logged", False):
                logger.error(str(e.__cause__))
            sys.exit(ExitCode.SECURITY_ERROR.value)
        logger.debug("[main] Caught unexpected error: %s", str(e))
        logger.error(f"Unexpected error: {e}")
        sys.exit(ExitCode.INTERNAL_ERROR.value)


# Export public API
__all__ = [
    "ExitCode",
    "estimate_tokens_for_chat",
    "get_context_window_limit",
    "get_default_token_limit",
    "parse_json_var",
    "create_dynamic_model",
    "validate_path_mapping",
    "create_argument_parser",
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

        # Validate root schema is object type
        if schema["type"] != "object":
            if debug_validation:
                logger.error(
                    "Schema type must be 'object', got %s", schema["type"]
                )
            raise SchemaValidationError("Root schema must be of type 'object'")

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
        model = create_model(
            base_name,
            __config__=config,
            **{
                name: (
                    (
                        cast(Type[Any], field_type)
                        if is_container_type(field_type)
                        else field_type
                    ),
                    field,
                )
                for name, (field_type, field) in field_definitions.items()
            },
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
                if hasattr(e, "errors"):
                    logger.error("  Validation errors:")
                    for error in e.errors():
                        logger.error("    - %s", error)
            validation_errors = (
                [str(err) for err in e.errors()]
                if hasattr(e, "errors")
                else [str(e)]
            )
            raise ModelValidationError(base_name, validation_errors)

        return cast(Type[BaseModel], model)

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
