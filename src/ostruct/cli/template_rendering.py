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
from typing import Any, Dict, List, Optional, Union

import jinja2
from jinja2 import Environment

from .errors import TemplateValidationError
from .file_utils import FileInfo
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


def render_template(
    template_str: str,
    context: Dict[str, Any],
    jinja_env: Optional[Environment] = None,
    progress_enabled: bool = True,
) -> str:
    """Render a task template with the given context.

    Args:
        template_str: Task template string or path to task template file
        context: Task template variables
        jinja_env: Optional Jinja2 environment to use
        progress_enabled: Whether to show progress indicators

    Returns:
        Rendered task template string

    Raises:
        TemplateValidationError: If task template cannot be loaded or rendered. The original error
                  will be chained using `from` for proper error context.
    """
    from .progress import (  # Import here to avoid circular dependency
        ProgressContext,
    )

    with ProgressContext(
        description="Rendering task template",
        level="basic" if progress_enabled else "none",
    ) as progress:
        try:
            if progress:
                progress.update(1)  # Update progress for setup

            if jinja_env is None:
                jinja_env = create_jinja_env(
                    loader=jinja2.FileSystemLoader(".")
                )

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
                if isinstance(value, dict):
                    wrapped_context[key] = DotDict(value)
                else:
                    wrapped_context[key] = value

            # Add stdin only if not already in context
            if "stdin" not in wrapped_context:
                wrapped_context["stdin"] = StdinProxy()

            # Load file content for FileInfo objects
            for key, value in context.items():
                if isinstance(value, FileInfo):
                    # Access content property to trigger loading
                    _ = value.content
                elif (
                    isinstance(value, list)
                    and value
                    and isinstance(value[0], FileInfo)
                ):
                    for file_info in value:
                        # Access content property to trigger loading
                        _ = file_info.content

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
                    template = jinja_env.get_template(template_str)
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
                    template = jinja_env.from_string(template_str)

                    # Add debug log for loop rendering
                    def debug_file_render(f: FileInfo) -> str:
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
                                "    First file: %s (content length: %d)",
                                value[0].path,
                                (
                                    len(value[0].content)
                                    if hasattr(value[0], "content")
                                    else -1
                                ),
                            )
                    elif isinstance(value, FileInfo):
                        logger.info(
                            "  %s: FileInfo(%s) content length: %d",
                            key,
                            value.path,
                            (
                                len(value.content)
                                if hasattr(value, "content")
                                else -1
                            ),
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
                                logger.debug(
                                    "      content length: %d",
                                    (
                                        len(item.content)
                                        if hasattr(item, "content")
                                        else -1
                                    ),
                                )
                    else:
                        logger.debug(
                            "  %s: %s (%r)", key, type(value).__name__, value
                        )
                result = template.render(**wrapped_context)
                logger.info(
                    "Template render result (first 100 chars): %r",
                    result[:100],
                )
                logger.debug(
                    "=== Rendered result (first 1000 chars) ===\n%s",
                    result[:1000],
                )
                if "## File:" not in result:
                    logger.error(
                        "WARNING: File headers missing from rendered output!"
                    )
                    logger.error(
                        "Template string excerpt: %r", template_str[:200]
                    )
                    logger.error("Result excerpt: %r", result[:200])
                if progress:
                    progress.update(1)
                return result  # type: ignore[no-any-return]
            except (jinja2.TemplateError, Exception) as e:
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
    return render_template(template_str, context, jinja_env, progress_enabled)
