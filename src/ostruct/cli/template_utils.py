"""Template utilities for the CLI.

This module serves as the main entry point for template processing functionality.
It re-exports the public APIs from specialized modules:

- template_schema: Schema validation and proxy objects
- template_validation: Template validation using Jinja2
- template_rendering: Template rendering with Jinja2
- template_io: File I/O operations and metadata extraction
"""

import logging
from typing import Any, Dict, List, Optional, Set

import jsonschema
from jinja2 import Environment, TemplateSyntaxError, meta
from jinja2.nodes import Node

from .errors import (
    CLIError,
    SchemaError,
    SchemaValidationError,
    SystemPromptError,
    TaskTemplateError,
    TaskTemplateSyntaxError,
    TaskTemplateVariableError,
)
from .file_utils import FileInfo
from .template_io import extract_metadata, extract_template_metadata, read_file
from .template_rendering import DotDict, render_template
from .template_schema import (
    DictProxy,
    FileInfoProxy,
    ValidationProxy,
    create_validation_context,
)
from .template_validation import SafeUndefined, validate_template_placeholders

logger = logging.getLogger(__name__)


# Custom error classes
class TemplateMetadataError(TaskTemplateError):
    """Raised when there are issues extracting template metadata."""

    pass


def validate_json_schema(schema: Dict[str, Any]) -> None:
    """Validate a JSON schema.

    Args:
        schema: The schema to validate

    Raises:
        SchemaValidationError: If the schema is invalid
    """
    try:
        # 1. Quick structural validation
        if not isinstance(schema, dict):
            raise SchemaValidationError(
                "Invalid JSON Schema: Schema must be a JSON object",
                context={
                    "validation_type": "schema",
                    "found": type(schema).__name__,
                    "tips": ["Ensure your schema is a valid JSON object"],
                },
            )

        # 2. Extract and validate schema wrapper
        schema_to_validate = schema.get("schema", schema)
        if not isinstance(schema_to_validate, dict):
            raise SchemaValidationError(
                "Invalid JSON Schema: Inner schema must be a JSON object",
                context={
                    "validation_type": "schema",
                    "found": type(schema_to_validate).__name__,
                    "tips": [
                        "If using a schema wrapper, ensure the inner schema is a valid JSON object"
                    ],
                },
            )

        # 3. Check for circular references with enhanced detection
        def resolve_ref(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
            """Resolve a JSON reference to its target object."""
            if not ref.startswith("#/"):
                raise SchemaValidationError(
                    "Invalid JSON Schema: Only local references are supported",
                    context={
                        "validation_type": "schema",
                        "ref": ref,
                        "tips": [
                            "Use only local references (starting with #/)"
                        ],
                    },
                )

            parts = ref[2:].split("/")
            current = root
            for part in parts:
                if part not in current:
                    raise SchemaValidationError(
                        f"Invalid JSON Schema: Reference {ref} not found",
                        context={
                            "validation_type": "schema",
                            "ref": ref,
                            "tips": [
                                "Check that all references point to existing definitions"
                            ],
                        },
                    )
                current = current[part]
            return current

        def check_refs(
            obj: Any,
            path: List[str],
            seen_refs: List[str],
            root: Dict[str, Any],
        ) -> None:
            """Check for circular references in the schema."""
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref = obj["$ref"]
                    if ref in seen_refs:
                        raise SchemaValidationError(
                            "Invalid JSON Schema: Circular reference found",
                            context={
                                "validation_type": "schema",
                                "path": "/".join(path),
                                "ref": ref,
                                "found": "circular reference",
                                "tips": [
                                    "Remove circular references in your schema",
                                    "Use unique identifiers instead of nested references",
                                    "Consider flattening your schema structure",
                                ],
                            },
                        )

                    # Resolve the reference and check its contents
                    seen_refs.append(ref)
                    try:
                        resolved = resolve_ref(ref, root)
                        check_refs(resolved, path, seen_refs.copy(), root)
                    except SchemaValidationError:
                        raise
                    except Exception as e:
                        raise SchemaValidationError(
                            f"Invalid JSON Schema: Failed to resolve reference {ref}",
                            context={
                                "validation_type": "schema",
                                "path": "/".join(path),
                                "ref": ref,
                                "error": str(e),
                                "tips": [
                                    "Check that all references are properly formatted"
                                ],
                            },
                        )

                for key, value in obj.items():
                    if key != "$ref":  # Skip checking the reference itself
                        check_refs(value, path + [key], seen_refs.copy(), root)
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    check_refs(value, path + [str(i)], seen_refs.copy(), root)

        check_refs(schema_to_validate, [], [], schema_to_validate)

        # 4. Check required root properties
        if "type" not in schema_to_validate:
            raise SchemaValidationError(
                "Invalid JSON Schema: Missing required 'type' property",
                context={
                    "validation_type": "schema",
                    "tips": ["Add a 'type' property to your schema root"],
                },
            )

        # 5. Check for required fields not defined in properties
        if schema_to_validate.get("type") == "object":
            required_fields = schema_to_validate.get("required", [])
            properties = schema_to_validate.get("properties", {})
            missing_fields = [
                field for field in required_fields if field not in properties
            ]
            if missing_fields:
                raise SchemaValidationError(
                    "Invalid JSON Schema: Required fields must be defined in properties",
                    context={
                        "validation_type": "schema",
                        "missing_fields": missing_fields,
                        "tips": [
                            "Add the following fields to 'properties':",
                            *[f"  - {field}" for field in missing_fields],
                            "Or remove them from 'required' if they are not needed",
                        ],
                    },
                )

        # 6. Validate against JSON Schema meta-schema
        try:
            validator = jsonschema.validators.validator_for(schema_to_validate)
            validator.check_schema(schema_to_validate)
        except jsonschema.exceptions.SchemaError as e:
            raise SchemaValidationError(
                f"Invalid JSON Schema: {str(e)}",
                context={
                    "validation_type": "schema",
                    "path": "/".join(str(p) for p in e.path),
                    "details": e.message,
                    "tips": [
                        "Ensure your schema follows JSON Schema specification",
                        "Check property types and formats",
                        "Validate schema structure",
                    ],
                },
            )

    except SchemaValidationError:
        raise  # Re-raise SchemaValidationError without wrapping
    except Exception as e:
        raise SchemaValidationError(
            f"Invalid JSON Schema: {str(e)}",
            context={
                "validation_type": "schema",
                "error": str(e),
                "tips": ["Check schema syntax", "Validate JSON structure"],
            },
        )


def validate_response(
    response: Dict[str, Any], schema: Dict[str, Any]
) -> None:
    """Validate that a response dictionary matches a JSON Schema.

    This function validates that the response dictionary conforms to the provided
    JSON Schema specification.

    Args:
        response: Dictionary to validate
        schema: JSON Schema to validate against

    Raises:
        ValueError: If the response does not match the schema
    """
    try:
        # Create a validator for the schema
        validator = jsonschema.validators.validator_for(schema)(schema)

        # Validate the response
        validator.validate(response)
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Response validation failed: {e}")
    except Exception as e:
        raise ValueError(f"Response validation error: {e}")


def find_all_template_variables(
    template: str, env: Optional[Environment] = None
) -> Set[str]:
    """Find all variables used in a template and its dependencies.

    This function recursively parses the template and any included/imported/extended
    templates to find all variables that might be used.

    Args:
        template: The template string to parse
        env: Optional Jinja2 environment. If not provided, a new one will be created.

    Returns:
        Set of all variable names used in the template and its dependencies

    Raises:
        jinja2.TemplateSyntaxError: If the template has invalid syntax
    """
    if env is None:
        env = Environment(undefined=SafeUndefined)

    try:
        ast = env.parse(template)
    except TemplateSyntaxError as e:
        logger.error("Failed to parse template: %s", str(e))
        return set()  # Return empty set on parse error

    variables: Set[str] = set()

    # Find all variables in this template
    variables = meta.find_undeclared_variables(ast)

    # Filter out built-in functions and filters
    builtin_vars = {
        # Core functions
        "range",
        "dict",
        "lipsum",
        "cycler",
        "joiner",
        "namespace",
        "loop",
        "super",
        "self",
        "varargs",
        "kwargs",
        "items",
        # String filters
        "upper",
        "lower",
        "title",
        "capitalize",
        "trim",
        "strip",
        "lstrip",
        "rstrip",
        "center",
        "ljust",
        "rjust",
        "wordcount",
        "truncate",
        "striptags",
        # List filters
        "first",
        "last",
        "length",
        "max",
        "min",
        "sum",
        "sort",
        "unique",
        "reverse",
        "reject",
        "select",
        "map",
        "join",
        "count",
        # Type conversion
        "abs",
        "round",
        "int",
        "float",
        "string",
        "list",
        "bool",
        "batch",
        "slice",
        "attr",
        # Common filters
        "default",
        "replace",
        "safe",
        "urlencode",
        "indent",
        "format",
        "escape",
        "e",
        "nl2br",
        "urlize",
        # Dictionary operations
        "items",
        "keys",
        "values",
        "dictsort",
        # Math operations
        "round",
        "ceil",
        "floor",
        "abs",
        "max",
        "min",
        # Date/time
        "now",
        "strftime",
        "strptime",
        "datetimeformat",
    }

    variables = variables - builtin_vars

    # Find template dependencies (include, extends, import)
    def visit_nodes(nodes: List[Node]) -> None:
        """Visit AST nodes recursively to find template dependencies.

        Args:
            nodes: List of AST nodes to visit
        """
        for node in nodes:
            if node.__class__.__name__ in (
                "Include",
                "Extends",
                "Import",
                "FromImport",
            ):
                # Get the template name
                if hasattr(node, "template"):
                    template_name = node.template.value
                    try:
                        # Load and parse the referenced template
                        if env.loader is not None:
                            included_template = env.loader.get_source(
                                env, template_name
                            )[0]
                            # Recursively find variables in the included template
                            variables.update(
                                find_all_template_variables(
                                    included_template, env
                                )
                            )
                    except Exception:
                        # Skip if template can't be loaded - it will be caught during rendering
                        pass

            # Recursively visit child nodes
            if hasattr(node, "body"):
                visit_nodes(node.body)
            if hasattr(node, "else_"):
                visit_nodes(node.else_)

    visit_nodes(ast.body)
    return variables


__all__ = [
    # Schema types and validation
    "ValidationProxy",
    "FileInfoProxy",
    "DictProxy",
    "create_validation_context",
    "validate_json_schema",
    "validate_response",
    # Template validation
    "SafeUndefined",
    "validate_template_placeholders",
    "find_all_template_variables",
    # Template rendering
    "render_template",
    "DotDict",
    # File I/O
    "read_file",
    "extract_metadata",
    "extract_template_metadata",
    # File info
    "FileInfo",
    # Error classes
    "CLIError",
    "TaskTemplateError",
    "TaskTemplateSyntaxError",
    "TaskTemplateVariableError",
    "SchemaError",
    "SchemaValidationError",
    "SystemPromptError",
    "TemplateMetadataError",
]
