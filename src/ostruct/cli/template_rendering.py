"""Template rendering with Jinja2.

This module provides functionality for rendering Jinja2 templates with support for:
1. Custom filters and functions
2. Dot notation access for dictionaries
3. Error handling and reporting

Key Components:
    - render_template: Main rendering function
    - DotDict: Dictionary wrapper for dot notation access
    - Custom filters for code formatting and data manipulation

Examples:
    Basic template rendering:
    >>> template = "Hello {{ name }}!"
    >>> context = {'name': 'World'}
    >>> result = render_template(template, context)
    >>> print(result)
    Hello World!

    Dictionary access with dot notation:
    >>> template = '''
    ... Debug: {{ config.debug }}
    ... Mode: {{ config.settings.mode }}
    ... '''
    >>> config = {
    ...     'debug': True,
    ...     'settings': {'mode': 'test'}
    ... }
    >>> result = render_template(template, {'config': config})
    >>> print(result)
    Debug: True
    Mode: test

    Using custom filters:
    >>> template = '''
    ... {{ code | format_code('python') }}
    ... {{ data | dict_to_table }}
    ... '''
    >>> context = {
    ...     'code': 'def hello(): print("Hello")',
    ...     'data': {'name': 'test', 'value': 42}
    ... }
    >>> result = render_template(template, context)

    File content rendering:
    >>> template = "Content: {{ file.content }}"
    >>> context = {'file': FileInfo('test.txt')}
    >>> result = render_template(template, context)

Notes:
    - All dictionaries are wrapped in DotDict for dot notation access
    - Custom filters are registered automatically
    - Provides detailed error messages for rendering failures
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Union

import jinja2
from jinja2 import Environment

from .errors import TaskTemplateVariableError, TemplateValidationError
from .file_utils import FileInfo
from .progress import ProgressContext
from .template_env import create_jinja_env
from .template_schema import DotDict, StdinProxy

__all__ = [
    "create_jinja_env",
    "render_template",
    "render_template_file",
    "DotDict",
]

logger = logging.getLogger("ostruct")

# Type alias for template context values
TemplateContextValue = Union[
    str,
    int,
    float,
    bool,
    Dict[str, Any],
    List[Any],
    FileInfo,
    DotDict,
    StdinProxy,
]


def _extract_variable_name_from_jinja_error(error_message: str) -> str:
    """Extract the actual variable name from a Jinja2 UndefinedError message.

    Handles various Jinja2 error message formats:
    - "'variable_name' is undefined"
    - "'object_description' has no attribute 'property_name'"
    - Other formats

    Args:
        error_message: The string representation of the Jinja2 UndefinedError

    Returns:
        The extracted variable name, or a sanitized version if parsing fails
    """
    # Pattern 1: Standard undefined variable: "'variable_name' is undefined"
    match = re.match(r"'([^']+)' is undefined", error_message)
    if match:
        return match.group(1)

    # Pattern 2: Attribute access on object: "'object' has no attribute 'property'"
    # In this case, we want to extract just the property name, not the object description
    match = re.match(r"'[^']+' has no attribute '([^']+)'", error_message)
    if match:
        property_name = match.group(1)
        return property_name

    # Pattern 3: Try to find any quoted identifier that looks like a variable name
    # Look for quoted strings that contain only valid Python identifier characters
    quoted_parts: List[str] = re.findall(r"'([^']+)'", error_message)
    for part in quoted_parts:
        # Check if this looks like a variable name (not a class name or description)
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", part) and "." not in part:
            return part

    # Fallback: If we can't parse it properly, return a generic message
    # This avoids exposing internal class names to users
    return "unknown_variable"


def render_template(
    template_str: str,
    context: Dict[str, Any],
    env: Optional[Environment] = None,
    progress: Optional[ProgressContext] = None,
) -> str:
    """Render a template with the given context.

    Args:
        template_str: Template string to render
        context: Context dictionary for template variables
        env: Optional Jinja2 environment to use
        progress: Optional progress bar to update

    Returns:
        str: The rendered template string

    Raises:
        TaskTemplateVariableError: If template variables are undefined
        TemplateValidationError: If template rendering fails for other reasons
    """
    from .progress import (
        ProgressContext,
    )

    with ProgressContext(
        description="Rendering task template",
        level="basic" if progress else "none",
    ) as progress:
        try:
            if progress:
                progress.update(1)  # Update progress for setup

            if env is None:
                env, _ = create_jinja_env(loader=jinja2.FileSystemLoader("."))

            logger.debug("=== Raw Input ===")
            logger.debug(
                "Template string type: %s", type(template_str).__name__
            )
            logger.debug("Template string length: %d", len(template_str))
            logger.debug(
                "Template string first 500 chars: %r", template_str[:500]
            )
            logger.debug("Raw context keys: %r", list(context.keys()))

            logger.debug("=== Template Details ===")
            logger.debug("Raw template string:\n%s", template_str)
            logger.debug("Context keys and types:")
            for key, value in context.items():
                if isinstance(value, list):
                    logger.debug(
                        "  %s (list[%d]): %s",
                        key,
                        len(value),
                        [type(x).__name__ for x in value],
                    )
                else:
                    logger.debug("  %s: %s", key, type(value).__name__)

            # Wrap JSON variables in DotDict and handle special cases
            wrapped_context: Dict[str, TemplateContextValue] = {}
            for key, value in context.items():
                if isinstance(value, dict) and not isinstance(value, DotDict):
                    wrapped_context[key] = DotDict(value)
                else:
                    wrapped_context[key] = value

            # Add stdin only if not already in context
            if "stdin" not in wrapped_context:
                wrapped_context["stdin"] = StdinProxy()

            if progress:
                progress.update(1)  # Update progress for template creation

            # Create template from string or file
            template: Optional[jinja2.Template] = None
            if template_str.endswith((".j2", ".jinja2", ".md")):
                if not os.path.isfile(template_str):
                    raise TemplateValidationError(
                        f"Task template file not found: {template_str}"
                    )
                try:
                    template = env.get_template(template_str)
                except jinja2.TemplateNotFound as e:
                    raise TemplateValidationError(
                        f"Task template file not found: {e.name}"
                    ) from e
            else:
                logger.debug(
                    "Creating template from string. Template string: %r",
                    template_str,
                )
                try:
                    template = env.from_string(template_str)

                    # Add debug log for loop rendering
                    def debug_file_render(f: FileInfo) -> Any:
                        logger.info("Rendering file: %s", f.path)
                        return ""

                    template.globals["debug_file_render"] = debug_file_render
                except jinja2.TemplateSyntaxError as e:
                    raise TemplateValidationError(
                        f"Task template syntax error: {str(e)}"
                    ) from e

            if template is None:
                raise TemplateValidationError("Failed to create task template")
            assert template is not None  # Help mypy understand control flow

            # Add template globals
            template.globals["template_name"] = getattr(
                template, "name", "<string>"
            )
            template.globals["template_path"] = getattr(
                template, "filename", None
            )
            logger.debug("Template globals: %r", template.globals)

            try:
                # Attempt to render the template
                logger.debug("=== Starting template render ===")
                logger.info("=== Template Context ===")
                for key, value in wrapped_context.items():
                    if isinstance(value, list):
                        logger.info(
                            "  %s: list with %d items", key, len(value)
                        )
                        if value and isinstance(value[0], FileInfo):
                            logger.info(
                                "    First file: %s",
                                value[0].path,
                            )
                    elif isinstance(value, FileInfo):
                        logger.info(
                            "  %s: FileInfo(%s)",
                            key,
                            value.path,
                        )
                    else:
                        logger.info("  %s: %s", key, type(value).__name__)
                logger.debug(
                    "Template source: %r",
                    (
                        template.source
                        if hasattr(template, "source")
                        else "<no source>"
                    ),
                )
                logger.debug("Wrapped context before render:")
                for key, value in wrapped_context.items():
                    if isinstance(value, list):
                        logger.debug(
                            "  %s is a list with %d items", key, len(value)
                        )
                        for i, item in enumerate(value):
                            if isinstance(item, FileInfo):
                                logger.debug("    [%d] FileInfo details:", i)
                                logger.debug("      path: %r", item.path)
                                logger.debug(
                                    "      exists: %r",
                                    os.path.exists(item.path),
                                )
                    else:
                        logger.debug(
                            "  %s: %s (%r)", key, type(value).__name__, value
                        )

                result = template.render(**wrapped_context)
                if not isinstance(result, str):
                    raise TemplateValidationError(
                        f"Template rendered to non-string type: {type(result)}"
                    )
                logger.info(
                    "Template render result (first 100 chars): %r",
                    result[:100],
                )
                logger.debug(
                    "=== Rendered result (first 1000 chars) ===\n%s",
                    result[:1000],
                )
                if progress:
                    progress.update(1)
                return result
            except jinja2.UndefinedError as e:
                # Extract variable name from error message
                var_name = _extract_variable_name_from_jinja_error(str(e))
                error_msg = (
                    f"Missing required template variable: {var_name}\n"
                    f"Available variables: {', '.join(sorted(context.keys()))}\n"
                    "To fix this, please provide the variable using:\n"
                    f"  -V {var_name}='value'"
                )
                raise TaskTemplateVariableError(error_msg) from e
            except TypeError as e:
                error_str = str(e)
                # Handle iteration errors with user-friendly messages
                if "object is not iterable" in error_str:
                    # Extract variable name from iteration context
                    # Look for patterns like "'ClassName' object is not iterable"
                    # and provide helpful guidance
                    user_friendly_msg = (
                        "Template iteration error: A variable used in a loop ({% for ... %}) "
                        "is not iterable. This usually means:\n"
                        "1. The variable is not a file object, list, or other iterable type\n"
                        "2. Check that your template variable names match the expected data\n"
                        "3. Verify the variable contains the expected data type\n"
                        f"Available variables: {', '.join(sorted(context.keys()))}"
                    )
                    logger.error("Template iteration error: %s", error_str)
                    raise TemplateValidationError(user_friendly_msg) from e
                else:
                    # Other TypeError - preserve original behavior
                    logger.error("Template rendering failed: %s", str(e))
                    raise TemplateValidationError(
                        f"Template rendering failed: {str(e)}"
                    ) from e
            except Exception as e:
                # Import here to avoid circular imports
                from .template_filters import (
                    TemplateStructureError,
                    format_tses_error,
                )

                # Handle TemplateStructureError with helpful formatting
                if isinstance(e, TemplateStructureError):
                    formatted_error = format_tses_error(e)
                    logger.error(
                        "Template structure error: %s", formatted_error
                    )
                    raise TemplateValidationError(formatted_error) from e
                elif isinstance(e, jinja2.TemplateError):
                    logger.error("Template rendering failed: %s", str(e))
                    raise TemplateValidationError(
                        f"Template rendering failed: {str(e)}"
                    ) from e
                else:
                    logger.error("Template rendering failed: %s", str(e))
                    raise TemplateValidationError(
                        f"Template rendering failed: {str(e)}"
                    ) from e

        except ValueError as e:
            # Re-raise with original context
            raise e


def render_template_file(
    template_path: str,
    context: Dict[str, Any],
    jinja_env: Optional[Environment] = None,
    progress_enabled: bool = True,
) -> str:
    """Render a template file with the given context.

    Args:
        template_path: Path to the template file
        context: Dictionary containing template variables
        jinja_env: Optional Jinja2 environment to use
        progress_enabled: Whether to show progress indicators

    Returns:
        The rendered template string

    Raises:
        TemplateValidationError: If template rendering fails
    """
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    # Create a progress context if enabled
    progress = (
        ProgressContext(
            description="Rendering template file",
            level="basic" if progress_enabled else "none",
        )
        if progress_enabled
        else None
    )

    return render_template(template_str, context, jinja_env, progress)
