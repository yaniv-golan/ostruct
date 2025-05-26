"""Schema utilities for ostruct CLI."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from openai_model_registry import ModelRegistry

from .errors import SchemaFileError

logger = logging.getLogger(__name__)


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


def supports_structured_output(model: str) -> bool:
    """Check if model supports structured output."""
    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)
        return getattr(capabilities, "supports_structured_output", True)
    except Exception:
        return True


def validate_schema_file(
    schema_path: str, schema_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Validate and load schema file.

    Args:
        schema_path: Path to schema file
        schema_context: Optional context for error reporting

    Returns:
        Dict containing the loaded schema

    Raises:
        SchemaFileError: If schema file is invalid or cannot be read
    """
    try:
        with Path(schema_path).open("r") as f:
            schema_data = json.load(f)

        # Validate basic schema structure
        if not isinstance(schema_data, dict):
            raise SchemaFileError(
                f"Schema file must contain a JSON object, got {type(schema_data).__name__}",
                schema_path=schema_path,
                context=schema_context,
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
                schema_path=schema_path,
                context=schema_context,
            )

        # Validate that root type is object for structured output
        if actual_schema.get("type") != "object":
            raise SchemaFileError(
                f"Schema root type must be 'object', got '{actual_schema.get('type')}'",
                schema_path=schema_path,
                context=schema_context,
            )

        return schema_data

    except json.JSONDecodeError as e:
        raise SchemaFileError(
            f"Invalid JSON in schema file: {e}",
            schema_path=schema_path,
            context=schema_context,
        ) from e
    except FileNotFoundError as e:
        raise SchemaFileError(
            f"Schema file not found: {schema_path}",
            schema_path=schema_path,
            context=schema_context,
        ) from e
    except Exception as e:
        raise SchemaFileError(
            f"Error reading schema file: {e}",
            schema_path=schema_path,
            context=schema_context,
        ) from e
