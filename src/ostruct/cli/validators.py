"""Validators for CLI options and arguments."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import click
import jinja2

from .errors import (
    DirectoryNotFoundError,
    InvalidJSONError,
    SchemaFileError,
    SchemaValidationError,
    VariableNameError,
    VariableValueError,
)
from .explicit_file_processor import ExplicitFileProcessor
from .security import SecurityManager
from .template_env import create_jinja_env
from .template_processor import (
    create_template_context_from_routing,
    validate_task_template,
)
from .template_utils import validate_json_schema
from .types import CLIParams

logger = logging.getLogger(__name__)

# Type alias for file routing results
FileRoutingResult = List[Tuple[Optional[str], Union[str, Path]]]


def validate_name_path_pair(
    ctx: click.Context,
    param: click.Parameter,
    value: List[Tuple[str, Union[str, Path]]],
) -> List[Tuple[str, Union[str, Path]]]:
    """Validate name/path pairs for files and directories.

    Args:
        ctx: Click context
        param: Click parameter
        value: List of (name, path) tuples

    Returns:
        List of validated (name, Path) tuples

    Raises:
        click.BadParameter: If validation fails
    """
    if not value:
        return value

    result: List[Tuple[str, Union[str, Path]]] = []
    for name, path in value:
        if not name.isidentifier():
            raise click.BadParameter(f"Invalid variable name: {name}")
        result.append((name, Path(path)))
    return result


def validate_file_routing_spec(
    ctx: click.Context,
    param: click.Parameter,
    value: List[str],
) -> FileRoutingResult:
    """Validate file routing specifications supporting multiple syntaxes.

    Supports two syntaxes currently:
    - Simple path: -ft config.yaml (auto-generates variable name)
    - Equals syntax: -ft code_file=src/main.py (custom variable name)

    Note: Two-argument syntax (-ft name path) requires special handling at the CLI level
    and is not supported in this validator due to Click's argument processing.

    Args:
        ctx: Click context
        param: Click parameter
        value: List of file specifications from multiple options

    Returns:
        List of (variable_name, path) tuples where variable_name=None means auto-generate

    Raises:
        click.BadParameter: If validation fails
    """
    if not value:
        return []

    result: FileRoutingResult = []

    for spec in value:
        if "=" in spec:
            # Equals syntax: -ft code_file=src/main.py
            if spec.count("=") != 1:
                raise click.BadParameter(
                    f"Invalid format '{spec}'. Use name=path or just path."
                )
            name, path = spec.split("=", 1)
            if not name.strip():
                raise click.BadParameter(f"Empty variable name in '{spec}'")
            if not path.strip():
                raise click.BadParameter(f"Empty path in '{spec}'")
            name = name.strip()
            path = path.strip()
            if not name.isidentifier():
                raise click.BadParameter(f"Invalid variable name: {name}")
            if not Path(path).exists():
                raise click.BadParameter(f"File not found: {path}")
            result.append((name, Path(path)))
        else:
            # Simple path: -ft config.yaml
            path = spec.strip()
            if not path:
                raise click.BadParameter("Empty file path")
            if not Path(path).exists():
                raise click.BadParameter(f"File not found: {path}")
            # Mark as auto-name with None, will be processed later
            result.append((None, Path(path)))

    return result


def validate_variable(
    ctx: click.Context, param: click.Parameter, value: Optional[List[str]]
) -> Optional[List[Tuple[str, str]]]:
    """Validate name=value format for simple variables.

    Args:
        ctx: Click context
        param: Click parameter
        value: List of "name=value" strings

    Returns:
        List of validated (name, value) tuples with whitespace stripped from both parts

    Raises:
        click.BadParameter: If validation fails
    """
    if not value:
        return None

    result = []
    for var in value:
        if "=" not in var:
            raise click.BadParameter(
                f"Variable must be in format name=value: {var}"
            )
        name, val = var.split("=", 1)
        name = name.strip()
        val = val.strip()
        if not name.isidentifier():
            raise click.BadParameter(f"Invalid variable name: {name}")
        result.append((name, val))
    return result


def validate_json_variable(
    ctx: click.Context, param: click.Parameter, value: Optional[List[str]]
) -> Optional[List[Tuple[str, Any]]]:
    """Validate JSON variable format.

    Args:
        ctx: Click context
        param: Click parameter
        value: List of "name=json_string" values

    Returns:
        List of validated (name, parsed_json) tuples with whitespace stripped from name

    Raises:
        click.BadParameter: If validation fails
    """
    if not value:
        return None

    result = []
    for var in value:
        if "=" not in var:
            raise InvalidJSONError(
                f"JSON variable must be in format name='{'json':\"value\"}': {var}"
            )
        name, json_str = var.split("=", 1)
        name = name.strip()
        json_str = json_str.strip()
        if not name.isidentifier():
            raise VariableNameError(f"Invalid variable name: {name}")
        try:
            json_value = json.loads(json_str)
            result.append((name, json_value))
        except json.JSONDecodeError as e:
            raise InvalidJSONError(
                f"Invalid JSON value for variable {name!r}: {json_str!r}",
                context={"variable_name": name},
            ) from e
    return result


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


def validate_schema_file(
    path: str,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Validate and load a JSON schema file.

    Args:
        path: Path to the schema file
        verbose: Whether to log additional information

    Returns:
        Dictionary containing the schema data

    Raises:
        SchemaFileError: If the schema file is invalid
    """
    try:
        with Path(path).open("r") as f:
            schema_data = json.load(f)

        # Validate basic schema structure
        if not isinstance(schema_data, dict):
            raise SchemaFileError(
                f"Schema file must contain a JSON object, got {type(schema_data).__name__}",
                schema_path=path,
            )

        # Must have either "schema" key or be a direct schema
        if "schema" in schema_data:
            # Wrapped schema format
            actual_schema = schema_data["schema"]
        else:
            # Direct schema format
            actual_schema = schema_data

        if not isinstance(actual_schema, dict):
            raise SchemaFileError(
                f"Schema must be a JSON object, got {type(actual_schema).__name__}",
                schema_path=path,
            )

        # Validate that root type is object for structured output
        if actual_schema.get("type") != "object":
            raise SchemaFileError(
                f"Schema root type must be 'object', got '{actual_schema.get('type')}'",
                schema_path=path,
            )

        return schema_data

    except json.JSONDecodeError as e:
        raise InvalidJSONError(
            f"Invalid JSON in schema file: {e}",
            source=path,
        ) from e
    except FileNotFoundError as e:
        raise SchemaFileError(
            f"Schema file not found: {path}",
            schema_path=path,
        ) from e
    except Exception as e:
        raise SchemaFileError(
            f"Error reading schema file: {e}",
            schema_path=path,
        ) from e


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
    routing_result = await file_processor.process_file_routing(args)  # type: ignore[arg-type]

    # Display auto-enablement feedback to user
    if routing_result.auto_enabled_feedback:
        print(routing_result.auto_enabled_feedback)

    # Store routing result in args for use by tool processors
    args["_routing_result"] = routing_result  # type: ignore[typeddict-unknown-key]

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
