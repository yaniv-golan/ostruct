"""Model creation utilities for the CLI."""

import json
import logging
import sys
from datetime import date, datetime, time
from enum import Enum, IntEnum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
    get_origin,
)

if sys.version_info >= (3, 11):
    from enum import StrEnum

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationError,
    create_model,
)
from pydantic.fields import FieldInfo
from pydantic.functional_validators import BeforeValidator
from pydantic.types import constr

from .errors import (
    FieldDefinitionError,
    ModelCreationError,
    ModelValidationError,
    NestedModelError,
    SchemaValidationError,
)

logger = logging.getLogger(__name__)

# Type aliases
FieldType = Type[
    Any
]  # Changed from Type[Any] to allow both concrete types and generics
FieldDefinition = Tuple[Any, FieldInfo]  # Changed to Any to handle generics


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


def is_container_type(tp: Type[Any]) -> bool:
    """Check if a type is a container type (List, Dict, etc).

    Args:
        tp: Type to check

    Returns:
        bool: True if type is a container type
    """
    origin = get_origin(tp)
    return origin is not None and origin in (list, dict, List, Dict)


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
            return (List[Any], Field(**field_kwargs))  # Direct generic type

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
            return (List[array_item_model], Field(**field_kwargs))  # type: ignore[valid-type]

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


def create_dynamic_model(
    schema: Dict[str, Any],
    base_name: str = "DynamicModel",
    show_schema: bool = False,
    debug_validation: bool = False,
) -> Type[BaseModel]:
    """Create a Pydantic model from a JSON schema.

    Args:
        schema: JSON schema to create model from
        base_name: Name for the model class
        show_schema: Whether to show the generated model schema
        debug_validation: Whether to show detailed validation errors

    Returns:
        Type[BaseModel]: The generated Pydantic model class

    Raises:
        ModelValidationError: If the schema is invalid
        SchemaValidationError: If the schema violates OpenAI requirements
    """
    if debug_validation:
        logger.info("Creating dynamic model from schema:")
        logger.info(json.dumps(schema, indent=2))

    try:
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

        # Validate against OpenAI requirements
        from .schema_validation import validate_openai_schema

        validate_openai_schema(schema)

        # Create model configuration
        config = ConfigDict(
            title=schema.get("title", base_name),
            extra="forbid",  # OpenAI requires additionalProperties: false
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

        # Process schema properties into fields
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        field_definitions: Dict[str, Tuple[Type[Any], FieldInfo]] = {}
        for field_name, field_schema in properties.items():
            if debug_validation:
                logger.info("Processing field %s:", field_name)
                logger.info("  Schema: %s", json.dumps(field_schema, indent=2))

            try:
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
        field_defs: Dict[str, Any] = {
            name: (
                (
                    cast(Type[Any], field_type)
                    if is_container_type(field_type)
                    else field_type
                ),
                field,
            )
            for name, (field_type, field) in field_definitions.items()
        }
        model: Type[BaseModel] = create_model(
            base_name, __config__=config, **field_defs
        )

        # Set the model config after creation
        model.model_config = config

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
            validation_errors = (
                [str(err) for err in e.errors()]
                if hasattr(e, "errors")
                else [str(e)]
            )
            if debug_validation:
                logger.error("Schema validation failed:")
                logger.error("  Error type: %s", type(e).__name__)
                logger.error("  Error message: %s", str(e))
            raise ModelValidationError(base_name, validation_errors)

        return model

    except SchemaValidationError as e:
        # Always log basic error info
        logger.error("Schema validation error: %s", str(e))

        # Log additional debug info if requested
        if debug_validation:
            logger.error("  Error type: %s", type(e).__name__)
            logger.error("  Error details: %s", str(e))
        # Always raise schema validation errors directly
        raise

    except Exception as e:
        # Always log basic error info
        logger.error("Model creation error: %s", str(e))

        # Log additional debug info if requested
        if debug_validation:
            logger.error("  Error type: %s", type(e).__name__)
            logger.error("  Error details: %s", str(e))
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
        # Always wrap other errors as ModelCreationError
        raise ModelCreationError(
            f"Failed to create model {base_name}",
            context={"error": str(e)},
        ) from e
