"""Template debugging infrastructure for ostruct CLI.

This module provides debugging capabilities for template expansion and optimization,
including proper logging configuration and template visibility features.
"""

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import click


class TDCap(str, Enum):
    """Template Debug Capacity enum for granular debugging control."""

    PRE_EXPAND = "pre-expand"
    VARS = "vars"
    PREVIEW = "preview"
    STEPS = "steps"
    POST_EXPAND = "post-expand"


ALL_CAPS: Set[TDCap] = set(TDCap)

# Tag mapping for consistent output prefixes
TAG_MAP = {
    TDCap.PRE_EXPAND: "PRE",
    TDCap.VARS: "VARS",
    TDCap.PREVIEW: "PREVIEW",
    TDCap.STEPS: "STEP",
    TDCap.POST_EXPAND: "TPL",
}


def parse_td(value: str | None) -> Set[TDCap]:
    """Parse template debug capacity string into set of capacities.

    Args:
        value: Comma-separated capacity list or "all" or None

    Returns:
        Set of TDCap enum values

    Raises:
        click.BadParameter: If invalid capacity specified
    """
    if value is None or value.lower() == "all":
        return ALL_CAPS

    caps = set()
    for tok in value.split(","):
        tok = tok.strip()
        try:
            caps.add(TDCap(tok))
        except ValueError:
            valid_caps = ", ".join(c.value for c in TDCap)
            raise click.BadParameter(
                f"Unknown template-debug capacity '{tok}'. "
                f"Valid: all, {valid_caps}"
            )
    return caps


def td_log(ctx: click.Context, cap: TDCap, msg: str) -> None:
    """Log template debug message if capacity is enabled.

    Args:
        ctx: Click context containing template debug configuration
        cap: Template debug capacity for this message
        msg: Message to log
    """
    if not ctx.obj:
        return

    active: Set[TDCap] | None = ctx.obj.get("_template_debug_caps")
    if active and cap in active:
        tag = TAG_MAP[cap]
        click.echo(f"[{tag}] {msg}", err=True)


MAX_PREVIEW = int(os.getenv("OSTRUCT_TEMPLATE_PREVIEW_LIMIT", "4096"))


def preview_snip(val: Any, max_size: int | None = None) -> str:
    """Create size-aware preview of variable content.

    Args:
        val: Variable value to preview
        max_size: Maximum preview size (default: OSTRUCT_TEMPLATE_PREVIEW_LIMIT)

    Returns:
        Preview string with truncation info if needed
    """
    if max_size is None:
        max_size = MAX_PREVIEW

    # Handle FileInfoList objects specially to avoid multi-file content access errors
    from .file_list import FileInfoList

    if isinstance(val, FileInfoList):
        if len(val) == 0:
            txt = "No files attached"
            type_info = ""
        elif len(val) == 1:
            try:
                txt = str(val.content)
                type_info = f" ({type(val).__name__})"
            except Exception:
                txt = "1 file attached (content not accessible)"
                type_info = ""
        else:
            txt = f"{len(val)} files attached (use indexing or loop to access individual files)"
            type_info = ""
    # Handle other objects with content property
    elif hasattr(
        val, "content"
    ):  # FileInfo objects and other content-bearing objects
        try:
            txt = str(val.content)
            type_info = f" ({type(val).__name__})"
        except ValueError:
            # Handle other content access failures
            txt = f"Content access failed for {type(val).__name__}"
            type_info = ""
    elif isinstance(val, (dict, list)):
        import json

        txt = json.dumps(val, indent=2)
        type_info = f" ({type(val).__name__} with {len(val)} items)"
    else:
        txt = str(val)
        type_info = f" ({type(val).__name__})"

    if len(txt) > max_size:
        return f"{txt[:max_size]}... [truncated {len(txt) - max_size} chars]{type_info}"
    return f"{txt}{type_info}"


def get_active_capacities(ctx: click.Context | None = None) -> Set[TDCap]:
    """Get currently active template debug capacities.

    Args:
        ctx: Click context (auto-detected if None)

    Returns:
        Set of active capacities, empty if none
    """
    if ctx is None:
        try:
            ctx = click.get_current_context()
        except RuntimeError:
            return set()

    if not ctx.obj:
        return set()

    result = ctx.obj.get("_template_debug_caps", set())
    return result if isinstance(result, set) else set()


def is_capacity_active(cap: TDCap, ctx: click.Context | None = None) -> bool:
    """Check if specific template debug capacity is active.

    Args:
        cap: Capacity to check
        ctx: Click context (auto-detected if None)

    Returns:
        True if capacity is active
    """
    active_caps = get_active_capacities(ctx)
    return cap in active_caps


def td_log_if_active(
    cap: TDCap, msg: str, ctx: click.Context | None = None
) -> None:
    """Log template debug message if capacity is active (convenience wrapper).

    Args:
        cap: Template debug capacity
        msg: Message to log
        ctx: Click context (auto-detected if None)
    """
    if ctx is None:
        try:
            ctx = click.get_current_context()
        except RuntimeError:
            return

    td_log(ctx, cap, msg)


def td_log_vars(
    variables: Dict[str, Any], ctx: click.Context | None = None
) -> None:
    """Log variable summary for VARS capacity.

    Args:
        variables: Dictionary of template variables
        ctx: Click context (auto-detected if None)
    """
    if not is_capacity_active(TDCap.VARS, ctx):
        return

    for name, value in variables.items():
        type_name = type(value).__name__
        td_log_if_active(TDCap.VARS, f"{name} : {type_name}", ctx)


def td_log_preview(
    variables: Dict[str, Any], ctx: click.Context | None = None
) -> None:
    """Log variable content preview for PREVIEW capacity.

    Args:
        variables: Dictionary of template variables
        ctx: Click context (auto-detected if None)
    """
    if not is_capacity_active(TDCap.PREVIEW, ctx):
        return

    for name, value in variables.items():
        preview = preview_snip(value)
        td_log_if_active(TDCap.PREVIEW, f"{name} → {preview}", ctx)


def td_log_step(
    step_num: int, description: str, ctx: click.Context | None = None
) -> None:
    """Log template expansion step for STEPS capacity.

    Args:
        step_num: Step number in expansion process
        description: Description of what this step does
        ctx: Click context (auto-detected if None)
    """
    td_log_if_active(TDCap.STEPS, f"Step {step_num}: {description}", ctx)


def configure_debug_logging(
    verbose: bool = False, debug: bool = False
) -> None:
    """Configure debug logging system to properly show template expansion.

    Args:
        verbose: Enable verbose logging (INFO level)
        debug: Enable debug logging (DEBUG level)
    """
    # Configure the root ostruct logger
    logger = logging.getLogger("ostruct")

    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler()

    # Set logging level based on flags
    if debug:
        logger.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    elif verbose:
        logger.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    else:
        logger.setLevel(logging.WARNING)
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter("%(levelname)s:%(message)s")

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False


def log_template_expansion(
    template_content: str,
    context: Dict[str, Any],
    expanded: str,
    template_file: Optional[str] = None,
) -> None:
    """Log template expansion with structured debug information.

    Args:
        template_content: Raw template content
        context: Template context variables
        expanded: Expanded template result
        template_file: Optional template file path
    """
    logger = logging.getLogger(__name__)

    logger.debug("=== TEMPLATE EXPANSION DEBUG ===")
    logger.debug(f"Template file: {template_file or 'inline'}")
    logger.debug(f"Context variables: {list(context.keys())}")
    logger.debug("Raw template content:")
    logger.debug(template_content)
    logger.debug("Expanded template:")
    logger.debug(expanded)
    logger.debug("=== END TEMPLATE EXPANSION ===")


def show_template_content(
    system_prompt: str,
    user_prompt: str,
    debug: bool = False,
) -> None:
    """Show template content with appropriate formatting.

    Args:
        system_prompt: System prompt content
        user_prompt: User prompt content
        debug: Debug flag
    """
    logger = logging.getLogger(__name__)

    # Show if debug mode or if post-expand capacity is active
    should_show = debug or is_capacity_active(TDCap.POST_EXPAND)

    if should_show:
        # Use click.echo for immediate output that bypasses logging
        click.echo("📝 Template Content:", err=True)
        click.echo("=" * 50, err=True)
        click.echo("System Prompt:", err=True)
        click.echo("-" * 20, err=True)
        click.echo(system_prompt, err=True)
        click.echo("\nUser Prompt:", err=True)
        click.echo("-" * 20, err=True)
        click.echo(user_prompt, err=True)
        click.echo("=" * 50, err=True)

    # Also log for debug mode
    if debug:
        logger.debug("System Prompt:")
        logger.debug("-" * 40)
        logger.debug(system_prompt)
        logger.debug("User Prompt:")
        logger.debug("-" * 40)
        logger.debug(user_prompt)


def show_file_content_expansions(context: Dict[str, Any]) -> None:
    """Show file content expansions for debugging.

    Args:
        context: Template context containing file information
    """
    logger = logging.getLogger(__name__)

    logger.debug("📁 File Content Expansions:")
    for key, value in context.items():
        # Check for specific file-related types more safely
        from .attachment_template_bridge import LazyFileContent
        from .file_info import FileInfo
        from .file_list import FileInfoList

        if isinstance(value, FileInfo):
            try:
                content_len = len(value.content) if value.content else 0
                logger.debug(f"  → {key}: {value.path} ({content_len} chars)")
            except Exception as e:
                logger.debug(
                    f"  → {key}: FileInfo at {value.path} (content access failed: {e})"
                )
        elif isinstance(value, FileInfoList):
            try:
                file_count = len(value)
                if file_count > 0:
                    # Try to get content length safely
                    try:
                        content_len = (
                            len(value.content) if value.content else 0
                        )
                        logger.debug(
                            f"  → {key}: FileInfoList with {file_count} files ({content_len} chars)"
                        )
                    except ValueError:
                        logger.debug(
                            f"  → {key}: FileInfoList with {file_count} files (empty)"
                        )
                else:
                    logger.debug(f"  → {key}: FileInfoList (empty)")
            except Exception as e:
                logger.debug(f"  → {key}: FileInfoList (access failed: {e})")
        elif isinstance(value, LazyFileContent):
            try:
                # Show user-friendly file information instead of class name
                file_size = getattr(value, "actual_size", None) or 0
                if file_size > 0:
                    size_str = f"{file_size:,} bytes"
                else:
                    size_str = "unknown size"
                logger.debug(
                    f"  → {key}: file {value.name} ({size_str}) at {value.path}"
                )
            except Exception as e:
                logger.debug(
                    f"  → {key}: file {getattr(value, 'name', 'unknown')} (access failed: {e})"
                )
        elif isinstance(value, str) and len(value) > 100:
            logger.debug(f"  → {key}: {len(value)} chars")
        elif isinstance(value, dict):
            logger.debug(f"  → {key}: dict with {len(value)} keys")
        elif isinstance(value, list):
            logger.debug(f"  → {key}: list with {len(value)} items")
        else:
            logger.debug(f"  → {key}: {type(value).__name__}")


class TemplateDebugger:
    """Template debugging helper for tracking expansion steps."""

    def __init__(self, enabled: bool = False):
        """Initialize the debugger.

        Args:
            enabled: Whether debugging is enabled
        """
        self.enabled = enabled
        self.expansion_log: List[Dict[str, Any]] = []

    def log_expansion_step(
        self,
        step: str,
        before: str,
        after: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a template expansion step.

        Args:
            step: Description of the expansion step
            before: Content before expansion
            after: Content after expansion
            context: Optional context information
        """
        if self.enabled:
            self.expansion_log.append(
                {
                    "step": step,
                    "before": before,
                    "after": after,
                    "context": context,
                    "timestamp": time.time(),
                }
            )

    def show_expansion_summary(self) -> None:
        """Show a summary of expansion steps."""
        if not self.enabled or not self.expansion_log:
            return

        logger = logging.getLogger(__name__)
        logger.debug("🔧 Template Expansion Summary:")
        for step in self.expansion_log:
            logger.debug(f"  → {step['step']}")
            if step["context"]:
                logger.debug(f"    Variables: {list(step['context'].keys())}")

    def show_detailed_expansion(self) -> None:
        """Show detailed expansion information for each step."""
        if not self.enabled or not self.expansion_log:
            return

        logger = logging.getLogger(__name__)
        logger.debug("🔍 Detailed Template Expansion:")
        for i, step_info in enumerate(self.expansion_log, 1):
            logger.debug(f"\n--- Step {i}: {step_info['step']} ---")
            if step_info["before"]:
                logger.debug("Before:")
                before_preview = step_info["before"][:200] + (
                    "..." if len(step_info["before"]) > 200 else ""
                )
                logger.debug(before_preview)
            logger.debug("After:")
            after_preview = step_info["after"][:200] + (
                "..." if len(step_info["after"]) > 200 else ""
            )
            logger.debug(after_preview)
            if step_info["context"]:
                logger.debug(f"Context: {list(step_info['context'].keys())}")

    def get_expansion_stats(self) -> Dict[str, Any]:
        """Get statistics about template expansion.

        Returns:
            Dictionary with expansion statistics
        """
        if not self.expansion_log:
            return {}

        total_steps = len(self.expansion_log)
        context_vars = set()
        for step in self.expansion_log:
            if step["context"]:
                context_vars.update(step["context"].keys())

        return {
            "total_steps": total_steps,
            "unique_variables": len(context_vars),
            "variable_names": sorted(list(context_vars)),
        }


@dataclass
class FileInspection:
    """Information about a file variable."""

    path: str
    size: int
    type: str


@dataclass
class StringInspection:
    """Information about a string variable."""

    length: int
    multiline: bool


@dataclass
class ObjectInspection:
    """Information about an object variable."""

    type: str
    keys: List[str]


@dataclass
class ContextReport:
    """Report of template context inspection."""

    files: Dict[str, FileInspection]
    strings: Dict[str, StringInspection]
    objects: Dict[str, ObjectInspection]

    def __init__(self) -> None:
        self.files = {}
        self.strings = {}
        self.objects = {}


class TemplateContextInspector:
    """Inspector for template variable context."""

    @staticmethod
    def inspect_context(context: Dict[str, Any]) -> ContextReport:
        """Inspect template context and generate a report.

        Args:
            context: Template context dictionary

        Returns:
            ContextReport with inspection results
        """
        report = ContextReport()

        for key, value in context.items():
            # Check for FileInfo objects (from ostruct file system)
            if hasattr(value, "content") and hasattr(value, "path"):
                # Single FileInfo object
                mime_type = getattr(value, "mime_type", "unknown")
                report.files[key] = FileInspection(
                    path=getattr(value, "path", "unknown"),
                    size=(
                        len(value.content) if hasattr(value, "content") else 0
                    ),
                    type=mime_type or "unknown",
                )
            elif hasattr(value, "__iter__") and not isinstance(
                value, (str, bytes)
            ):
                # Check if it's a list/collection of FileInfo objects
                try:
                    items = list(value)
                    if (
                        items
                        and hasattr(items[0], "content")
                        and hasattr(items[0], "path")
                    ):
                        # FileInfoList - collect info about all files
                        total_size = sum(
                            (
                                len(item.content)
                                if hasattr(item, "content")
                                else 0
                            )
                            for item in items
                        )
                        paths = [
                            getattr(item, "path", "unknown") for item in items
                        ]
                        report.files[key] = FileInspection(
                            path=f"{len(items)} files: {', '.join(paths[:3])}{'...' if len(paths) > 3 else ''}",
                            size=total_size,
                            type="file_collection",
                        )
                    else:
                        # Regular list/collection
                        report.objects[key] = ObjectInspection(
                            type=f"list[{len(items)}]",
                            keys=[
                                str(i) for i in range(min(5, len(items)))
                            ],  # Show first 5 indices
                        )
                except (TypeError, AttributeError):
                    # Fallback for non-iterable or problematic objects
                    report.objects[key] = ObjectInspection(
                        type=type(value).__name__, keys=[]
                    )
            elif isinstance(value, str):
                report.strings[key] = StringInspection(
                    length=len(value), multiline="\n" in value
                )
            elif isinstance(value, dict):
                report.objects[key] = ObjectInspection(
                    type="dict",
                    keys=list(value.keys())[:10],  # Show first 10 keys
                )
            else:
                # Other types (int, bool, etc.)
                report.objects[key] = ObjectInspection(
                    type=type(value).__name__, keys=[]
                )

        return report


def display_context_summary(context: Dict[str, Any]) -> None:
    """Display a summary of template context variables.

    Args:
        context: Template context dictionary
    """
    click.echo("📋 Template Context Summary:", err=True)
    click.echo("=" * 50, err=True)

    inspector = TemplateContextInspector()
    report = inspector.inspect_context(context)

    if report.files:
        click.echo(f"📄 Files ({len(report.files)}):", err=True)
        for name, info in report.files.items():
            size_str = f"{info.size:,} chars" if info.size > 0 else "empty"
            click.echo(
                f"  → {name}: {info.path} ({size_str}, {info.type})", err=True
            )

    if report.strings:
        click.echo(f"📝 Strings ({len(report.strings)}):", err=True)
        for name, string_info in report.strings.items():
            multiline_str = " (multiline)" if string_info.multiline else ""
            click.echo(
                f"  → {name}: {string_info.length} chars{multiline_str}",
                err=True,
            )

    if report.objects:
        click.echo(f"🗂️ Objects ({len(report.objects)}):", err=True)
        for name, object_info in report.objects.items():
            if object_info.keys:
                keys_preview = ", ".join(object_info.keys[:5])
                if len(object_info.keys) > 5:
                    keys_preview += "..."
                click.echo(
                    f"  → {name}: {object_info.type} ({keys_preview})",
                    err=True,
                )
            else:
                click.echo(f"  → {name}: {object_info.type}", err=True)

    click.echo("=" * 50, err=True)


def display_context_detailed(context: Dict[str, Any]) -> None:
    """Display detailed template context with content previews.

    Args:
        context: Template context dictionary
    """
    click.echo("📋 Detailed Template Context:", err=True)
    click.echo("=" * 50, err=True)

    inspector = TemplateContextInspector()
    report = inspector.inspect_context(context)

    # Show files with content preview
    if report.files:
        click.echo("📄 File Variables:", err=True)
        for name, info in report.files.items():
            click.echo(f"\n  {name}:", err=True)
            click.echo(f"    Path: {info.path}", err=True)
            click.echo(f"    Size: {info.size:,} chars", err=True)
            click.echo(f"    Type: {info.type}", err=True)

            # Show content preview for single files
            if name in context and hasattr(context[name], "content"):
                content = context[name].content
                if len(content) > 200:
                    preview = content[:200] + "..."
                else:
                    preview = content
                click.echo(f"    Preview: {repr(preview)}", err=True)

    # Show strings with content preview
    if report.strings:
        click.echo("\n📝 String Variables:", err=True)
        for name, string_info in report.strings.items():
            click.echo(f"\n  {name}:", err=True)
            click.echo(f"    Length: {string_info.length} chars", err=True)
            click.echo(f"    Multiline: {string_info.multiline}", err=True)

            # Show content preview
            content = context[name]
            if len(content) > 100:
                preview = content[:100] + "..."
            else:
                preview = content
            click.echo(f"    Preview: {repr(preview)}", err=True)

    # Show objects with structure
    if report.objects:
        click.echo("\n🗂️ Object Variables:", err=True)
        for name, object_info in report.objects.items():
            click.echo(f"\n  {name}:", err=True)
            click.echo(f"    Type: {object_info.type}", err=True)
            if object_info.keys:
                click.echo(
                    f"    Keys/Indices: {', '.join(object_info.keys)}",
                    err=True,
                )

    click.echo("=" * 50, err=True)


def detect_undefined_variables(
    template_content: str, context: Dict[str, Any]
) -> List[str]:
    """Detect undefined variables in template content.

    Args:
        template_content: Template content to analyze
        context: Available context variables

    Returns:
        List of undefined variable names
    """
    # This is a simple implementation - could be enhanced with proper Jinja2 AST parsing
    import re

    # Find all variable references in the template
    variable_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*[|\}]"
    variables = re.findall(variable_pattern, template_content)

    # Check which variables are not in context
    undefined_vars = []
    for var in set(variables):
        if var not in context:
            undefined_vars.append(var)

    return undefined_vars
