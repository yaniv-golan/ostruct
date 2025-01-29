"""Template utilities for the CLI.

This module serves as the main entry point for template processing functionality.
It re-exports the public APIs from specialized modules:

- template_schema: Schema validation and proxy objects
- template_validation: Template validation using Jinja2
- template_rendering: Template rendering with Jinja2
- template_io: File I/O operations and metadata extraction
"""

from typing import Any, Dict, List, Optional, Set

import jsonschema
from jinja2 import Environment, meta
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


# Custom error classes
class TemplateMetadataError(TaskTemplateError):
    """Raised when there are issues extracting template metadata."""

    pass


def validate_json_schema(schema: Dict[str, Any]) -> None:
    """Validate that a dictionary follows JSON Schema structure.

    This function checks that the provided dictionary is a valid JSON Schema,
    following the JSON Schema specification.

    Args:
        schema: Dictionary to validate as a JSON Schema

    Raises:
        SchemaValidationError: If the schema is invalid
    """
    try:
        # Get the validator class for the schema
        validator_cls = jsonschema.validators.validator_for(schema)

        # Check schema itself is valid
        validator_cls.check_schema(schema)

        # Create validator instance
        validator_cls(schema)
    except jsonschema.exceptions.SchemaError as e:
        raise SchemaValidationError(f"Invalid JSON Schema: {e}")
    except Exception as e:
        raise SchemaValidationError(f"Schema validation error: {e}")


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

    # Parse template
    ast = env.parse(template)

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
    return variables  # type: ignore[no-any-return]


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
