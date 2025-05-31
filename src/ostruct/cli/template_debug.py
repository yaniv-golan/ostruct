"""Template debugging infrastructure for ostruct CLI.

This module provides debugging capabilities for template expansion and optimization,
including proper logging configuration and template visibility features.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import click


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
    show_templates: bool = False,
    debug: bool = False,
) -> None:
    """Show template content with appropriate formatting.

    Args:
        system_prompt: System prompt content
        user_prompt: User prompt content
        show_templates: Show templates flag
        debug: Debug flag
    """
    logger = logging.getLogger(__name__)

    if show_templates or debug:
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
        if hasattr(value, "content"):  # FileInfo object
            logger.debug(
                f"  → {key}: {getattr(value, 'path', 'unknown')} ({len(value.content)} chars)"
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


def show_pre_optimization_template(template_content: str) -> None:
    """Display template content before optimization is applied.

    Args:
        template_content: Raw template content before optimization
    """
    click.echo("🔧 Template Before Optimization:", err=True)
    click.echo("=" * 50, err=True)
    click.echo(template_content, err=True)
    click.echo("=" * 50, err=True)


def show_optimization_diff(original: str, optimized: str) -> None:
    """Show template optimization changes in a readable diff format.

    Args:
        original: Original template content
        optimized: Optimized template content
    """
    click.echo("🔄 Template Optimization Changes:", err=True)
    click.echo("=" * 50, err=True)

    # Simple line-by-line comparison
    original_lines = original.split("\n")
    optimized_lines = optimized.split("\n")

    # Show basic statistics
    click.echo(
        f"Original: {len(original_lines)} lines, {len(original)} chars",
        err=True,
    )
    click.echo(
        f"Optimized: {len(optimized_lines)} lines, {len(optimized)} chars",
        err=True,
    )

    if original == optimized:
        click.echo("✅ No optimization changes made", err=True)
        click.echo("=" * 50, err=True)
        return

    click.echo("\nChanges:", err=True)

    # Find differences line by line
    max_lines = max(len(original_lines), len(optimized_lines))
    changes_found = False

    for i in range(max_lines):
        orig_line = original_lines[i] if i < len(original_lines) else ""
        opt_line = optimized_lines[i] if i < len(optimized_lines) else ""

        if orig_line != opt_line:
            changes_found = True
            click.echo(f"  Line {i + 1}:", err=True)
            if orig_line:
                click.echo(f"    - {orig_line}", err=True)
            if opt_line:
                click.echo(f"    + {opt_line}", err=True)

    if not changes_found:
        # If no line-by-line differences but content differs, show character-level diff
        click.echo(
            "  Content differs but not at line level (whitespace/formatting changes)",
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


@dataclass
class OptimizationStep:
    """Information about a single optimization step."""

    name: str
    before: str
    after: str
    reason: str
    timestamp: float
    chars_changed: int = 0

    def __post_init__(self) -> None:
        """Calculate character changes after initialization."""
        self.chars_changed = len(self.after) - len(self.before)


class OptimizationStepTracker:
    """Tracker for detailed optimization step analysis."""

    def __init__(self, enabled: bool = False):
        """Initialize the optimization step tracker.

        Args:
            enabled: Whether step tracking is enabled
        """
        self.enabled = enabled
        self.steps: List[OptimizationStep] = []

    def log_step(
        self,
        step_name: str,
        before: str,
        after: str,
        reason: str,
    ) -> None:
        """Log an optimization step.

        Args:
            step_name: Name/description of the optimization step
            before: Content before this step
            after: Content after this step
            reason: Explanation of why this step was applied
        """
        if self.enabled:
            step = OptimizationStep(
                name=step_name,
                before=before,
                after=after,
                reason=reason,
                timestamp=time.time(),
            )
            self.steps.append(step)

    def show_step_summary(self) -> None:
        """Show a summary of optimization steps."""
        if not self.enabled or not self.steps:
            return

        click.echo("🔧 Optimization Steps Summary:", err=True)
        click.echo("=" * 50, err=True)

        total_chars_changed = 0
        for i, step in enumerate(self.steps, 1):
            total_chars_changed += step.chars_changed
            change_indicator = (
                "📈"
                if step.chars_changed > 0
                else "📉" if step.chars_changed < 0 else "📊"
            )

            click.echo(f"  {i}. {step.name}: {step.reason}", err=True)
            if step.before != step.after:
                click.echo(
                    f"     {change_indicator} Changed: {len(step.before)} → {len(step.after)} chars ({step.chars_changed:+d})",
                    err=True,
                )
            else:
                click.echo("     📊 No changes made", err=True)

        click.echo(
            f"\n📊 Total: {total_chars_changed:+d} characters changed",
            err=True,
        )
        click.echo("=" * 50, err=True)

    def show_detailed_steps(self) -> None:
        """Show detailed information for each optimization step."""
        if not self.enabled or not self.steps:
            return

        click.echo("🔍 Detailed Optimization Steps:", err=True)
        click.echo("=" * 50, err=True)

        for i, step in enumerate(self.steps, 1):
            click.echo(f"\n--- Step {i}: {step.name} ---", err=True)
            click.echo(f"Reason: {step.reason}", err=True)
            click.echo(f"Character change: {step.chars_changed:+d}", err=True)

            if step.before != step.after:
                click.echo("Changes:", err=True)
                _show_step_diff(step.before, step.after)
            else:
                click.echo("✅ No changes made", err=True)

        click.echo("=" * 50, err=True)

    def get_step_stats(self) -> Dict[str, Any]:
        """Get statistics about optimization steps.

        Returns:
            Dictionary with step statistics
        """
        if not self.steps:
            return {}

        total_steps = len(self.steps)
        total_chars_changed = sum(step.chars_changed for step in self.steps)
        steps_with_changes = sum(
            1 for step in self.steps if step.before != step.after
        )

        return {
            "total_steps": total_steps,
            "steps_with_changes": steps_with_changes,
            "total_chars_changed": total_chars_changed,
            "step_names": [step.name for step in self.steps],
        }


def _show_step_diff(before: str, after: str) -> None:
    """Show a simple diff between before and after content.

    Args:
        before: Content before changes
        after: Content after changes
    """
    before_lines = before.split("\n")
    after_lines = after.split("\n")

    max_lines = max(len(before_lines), len(after_lines))
    changes_shown = 0
    max_changes = 5  # Limit output for readability

    for i in range(max_lines):
        if changes_shown >= max_changes:
            click.echo(
                f"  ... ({max_lines - i} more lines not shown)", err=True
            )
            break

        before_line = before_lines[i] if i < len(before_lines) else ""
        after_line = after_lines[i] if i < len(after_lines) else ""

        if before_line != after_line:
            changes_shown += 1
            click.echo(f"  Line {i + 1}:", err=True)
            if before_line:
                click.echo(f"    - {before_line}", err=True)
            if after_line:
                click.echo(f"    + {after_line}", err=True)


def show_optimization_steps(
    steps: List[OptimizationStep], detail_level: str = "summary"
) -> None:
    """Show optimization steps with specified detail level.

    Args:
        steps: List of optimization steps
        detail_level: Level of detail ("summary" or "detailed")
    """
    if not steps:
        click.echo("ℹ️  No optimization steps were recorded", err=True)
        return

    tracker = OptimizationStepTracker(enabled=True)
    tracker.steps = steps

    if detail_level == "detailed":
        tracker.show_detailed_steps()
    else:
        tracker.show_step_summary()
