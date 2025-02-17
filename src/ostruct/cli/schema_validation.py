from enum import IntEnum
from typing import Any, Dict, List, Optional

from .errors import SchemaValidationError


class SchemaLimits(IntEnum):
    """Limits for OpenAI schema validation."""

    MAX_NESTING_DEPTH = 5
    MAX_PROPERTIES = 100
    MAX_ENUM_VALUES = 500
    MAX_ENUM_VALUES_CHAR_CHECK = 250
    MAX_ENUM_TOTAL_CHARS = 7500


# Validates the schema against OpenAI's structured output requirements.
# https://platform.openai.com/docs/guides/structured-outputs


def validate_openai_schema(
    schema: Dict[str, Any], path: Optional[List[str]] = None
) -> None:
    """Validate schema against OpenAI's structured output requirements.

    Args:
        schema: The JSON schema to validate
        path: Current path in schema for nested validation

    Raises:
        SchemaValidationError: If schema violates any OpenAI requirements
    """
    path = path or []
    current_path = "/".join(path) or "<root>"

    # Root level validation
    if not path:  # Only check at root
        if schema.get("type") != "object":
            raise SchemaValidationError(
                "Root schema must be type 'object'",
                context={
                    "path": current_path,
                    "found": schema.get("type"),
                    "tips": [
                        "The root of your schema must be an object type",
                        "If you have an array, wrap it in an object property:",
                        {
                            "type": "object",
                            "properties": {
                                "items": {
                                    "type": "array",
                                    "items": "...your array schema...",
                                }
                            },
                            "required": ["items"],
                            "additionalProperties": False,
                        },
                    ],
                },
            )

        if schema.get("additionalProperties") is not False:
            raise SchemaValidationError(
                "Root schema must set additionalProperties: false",
                context={
                    "path": current_path,
                    "tips": [
                        "Add 'additionalProperties: false' to your root schema",
                        "This ensures only defined properties are allowed",
                    ],
                },
            )

        # Validate required properties
        root_properties = set(schema.get("properties", {}).keys())
        required = set(schema.get("required", []))

        if not root_properties:
            raise SchemaValidationError(
                "Root schema must define at least one property",
                context={
                    "path": current_path,
                    "tips": [
                        "Add properties to your schema",
                        "Each property should define its type and any constraints",
                    ],
                },
            )

        if required != root_properties:
            missing = root_properties - required
            extra = required - root_properties
            tips = []
            if missing:
                tips.append(
                    f"Add these properties to 'required': {list(missing)}"
                )
            if extra:
                tips.append(
                    f"Remove these from 'required' as they aren't defined: {list(extra)}"
                )

            raise SchemaValidationError(
                "All properties must be required in root schema",
                context={
                    "path": current_path,
                    "missing_required": list(missing),
                    "extra_required": list(extra),
                    "tips": tips,
                },
            )

    # Structural validation
    if len(path) > SchemaLimits.MAX_NESTING_DEPTH:
        raise SchemaValidationError(
            f"Schema exceeds maximum nesting depth of {SchemaLimits.MAX_NESTING_DEPTH} levels",
            context={
                "path": current_path,
                "tips": [
                    "Flatten your schema structure",
                    "Consider combining nested objects",
                    "Move complex structures to root level properties",
                ],
            },
        )

    # Property count validation
    if schema.get("type") == "object":
        obj_properties: Dict[str, Any] = schema.get("properties", {})
        if len(obj_properties) > SchemaLimits.MAX_PROPERTIES:
            raise SchemaValidationError(
                f"Schema exceeds maximum of {SchemaLimits.MAX_PROPERTIES} properties",
                context={
                    "path": current_path,
                    "count": len(obj_properties),
                    "tips": [
                        "Reduce the number of properties",
                        "Consider grouping related properties into sub-objects",
                        "Remove any unused or optional properties",
                    ],
                },
            )

        # Validate each property
        for prop_name, prop_schema in obj_properties.items():
            validate_openai_schema(prop_schema, path + [prop_name])

    # Array validation
    elif schema.get("type") == "array":
        if "items" in schema:
            validate_openai_schema(schema["items"], path + ["items"])

    # Enum validation
    if "enum" in schema:
        enum_values = schema["enum"]
        if len(enum_values) > SchemaLimits.MAX_ENUM_VALUES:
            raise SchemaValidationError(
                f"Enum exceeds maximum of {SchemaLimits.MAX_ENUM_VALUES} values",
                context={
                    "path": current_path,
                    "count": len(enum_values),
                    "tips": [
                        "Reduce the number of enum values",
                        "Consider using a different type or structure",
                        "Split into multiple smaller enums if possible",
                    ],
                },
            )

        # Check enum string length for large enums
        if len(enum_values) > SchemaLimits.MAX_ENUM_VALUES_CHAR_CHECK:
            total_chars = sum(len(str(v)) for v in enum_values)
            if total_chars > SchemaLimits.MAX_ENUM_TOTAL_CHARS:
                raise SchemaValidationError(
                    f"Enum values exceed maximum total length of {SchemaLimits.MAX_ENUM_TOTAL_CHARS} characters",
                    context={
                        "path": current_path,
                        "total_chars": total_chars,
                        "tips": [
                            "Reduce the length of enum values",
                            "Consider using shorter identifiers",
                            "Split into multiple smaller enums",
                        ],
                    },
                )

    # Prohibited keywords by type
    type_prohibited = {
        "object": ["patternProperties", "minProperties"],
        "array": ["minItems", "maxItems", "uniqueItems"],
        "string": ["pattern", "format", "minLength", "maxLength"],
        "number": ["minimum", "maximum", "multipleOf"],
        "integer": ["exclusiveMinimum", "exclusiveMaximum"],
    }

    schema_type = schema.get("type")
    if schema_type in type_prohibited:
        prohibited = set(type_prohibited[schema_type])
        used_prohibited = prohibited.intersection(schema.keys())
        if used_prohibited:
            raise SchemaValidationError(
                f"Schema uses prohibited keywords for type '{schema_type}'",
                context={
                    "path": current_path,
                    "type": schema_type,
                    "prohibited_used": list(used_prohibited),
                    "tips": [
                        f"Remove these prohibited keywords: {list(used_prohibited)}",
                        "OpenAI structured output has limited keyword support",
                        "Use only basic type constraints",
                    ],
                },
            )
