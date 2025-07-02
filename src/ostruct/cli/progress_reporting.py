"""Enhanced progress reporting with user-centric language."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import click

logger = logging.getLogger(__name__)


@dataclass
class CostBreakdown:
    """Cost breakdown for transparency."""

    total: float
    input_cost: float
    output_cost: float
    input_tokens: int
    output_tokens: int
    code_interpreter_cost: Optional[float] = None
    file_search_cost: Optional[float] = None
    model: str = "gpt-4o"

    @property
    def has_tool_costs(self) -> bool:
        """Check if there are additional tool costs."""
        return bool(self.code_interpreter_cost or self.file_search_cost)


@dataclass
class ProcessingResult:
    """Processing result summary for user reporting."""

    model: str
    analysis_summary: str
    search_summary: Optional[str] = None
    completion_summary: str = "Processing completed successfully"
    files_processed: int = 0
    tools_used: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.tools_used is None:
            self.tools_used = []


class EnhancedProgressReporter:
    """Enhanced progress reporter with user-friendly language and transparency."""

    def __init__(self, verbose: bool = False, progress: str = "basic"):
        """Initialize the progress reporter.

        Args:
            verbose: Enable verbose logging output
            progress: Progress level (none, basic, detailed)
        """
        self.verbose = verbose
        self.progress = progress
        self.should_report = progress != "none"
        self.detailed = progress == "detailed" or verbose

    def report_phase(self, phase_name: str, emoji: str = "⚙️") -> None:
        """Report the start of a major processing phase.

        Args:
            phase_name: Name of the processing phase
            emoji: Emoji icon for the phase
        """
        if self.should_report:
            click.echo(f"{emoji} {phase_name}...", err=True)

    def report_file_routing(
        self,
        template_files: List[str],
        container_files: List[str],
        vector_files: List[str],
    ) -> None:
        """Report file routing decisions in user-friendly terms.

        Args:
            template_files: Files routed to template access
            container_files: Files routed to Code Interpreter
            vector_files: Files routed to File Search
        """
        if not self.should_report:
            return

        total_files = (
            len(template_files) + len(container_files) + len(vector_files)
        )
        if total_files == 0:
            return

        if self.detailed:
            click.echo("📂 File routing:", err=True)
            for file in template_files:
                click.echo(
                    f"  → {file}: available in template for direct access",
                    err=True,
                )
            for file in container_files:
                click.echo(
                    f"  → {file}: uploaded to Code Interpreter for analysis",
                    err=True,
                )
            for file in vector_files:
                click.echo(
                    f"  → {file}: uploaded to File Search for semantic search",
                    err=True,
                )
        else:
            tools_used = []
            if container_files:
                tools_used.append(
                    f"Code Interpreter ({len(container_files)} files)"
                )
            if vector_files:
                tools_used.append(f"File Search ({len(vector_files)} files)")
            if template_files:
                tools_used.append(f"Template ({len(template_files)} files)")

            tools_str = ", ".join(tools_used)
            click.echo(
                f"📂 Routed {total_files} files to: {tools_str}", err=True
            )

    def report_processing_start(
        self, model: str, tools_used: List[str]
    ) -> None:
        """Report the start of AI processing with clear context.

        Args:
            model: Model being used for processing
            tools_used: List of tools being utilized
        """
        if not self.should_report:
            return

        tools_str = ", ".join(tools_used) if tools_used else "template only"
        click.echo(
            f"🤖 Processing with {model} using {tools_str}...", err=True
        )

    def report_processing_results(self, result: ProcessingResult) -> None:
        """Report AI processing outcomes in a user-friendly way.

        Args:
            result: Processing result with summary information
        """
        if not self.should_report:
            return

        if self.detailed:
            click.echo("📦 Processing results:", err=True)
            click.echo(f"├── Model: {result.model}", err=True)
            if result.files_processed > 0:
                click.echo(
                    f"├── Files processed: {result.files_processed}", err=True
                )
            if result.tools_used:
                click.echo(
                    f"├── Tools used: {', '.join(result.tools_used)}", err=True
                )
            if result.search_summary:
                click.echo(f"├── 🔍 {result.search_summary}", err=True)
            click.echo(f"└── ✅ {result.completion_summary}", err=True)
        else:
            click.echo(f"✅ {result.completion_summary}", err=True)

    def report_cost_breakdown(self, cost_info: CostBreakdown) -> None:
        """Report transparent cost information to build user trust.

        Args:
            cost_info: Detailed cost breakdown information
        """
        if not self.should_report:
            return

        if self.detailed:
            click.echo(
                f"💰 Cost breakdown: ${cost_info.total:.4f} total", err=True
            )
            click.echo(
                f"  ├── Input tokens ({cost_info.input_tokens:,}): ${cost_info.input_cost:.4f}",
                err=True,
            )
            click.echo(
                f"  ├── Output tokens ({cost_info.output_tokens:,}): ${cost_info.output_cost:.4f}",
                err=True,
            )
            if cost_info.code_interpreter_cost:
                click.echo(
                    f"  ├── Code Interpreter: ${cost_info.code_interpreter_cost:.4f}",
                    err=True,
                )
            if cost_info.file_search_cost:
                click.echo(
                    f"  └── File Search: ${cost_info.file_search_cost:.4f}",
                    err=True,
                )
        else:
            if cost_info.total > 0.01:  # Only show cost if significant
                if cost_info.has_tool_costs:
                    click.echo(
                        f"💰 Total cost: ${cost_info.total:.3f} (model + tools)",
                        err=True,
                    )
                else:
                    click.echo(
                        f"💰 Total cost: ${cost_info.total:.3f}", err=True
                    )

    def report_file_downloads(
        self, downloaded_files: List[str], download_dir: str
    ) -> None:
        """Report file download operations clearly.

        Args:
            downloaded_files: List of downloaded file paths
            download_dir: Directory where files were downloaded
        """
        if not self.should_report or not downloaded_files:
            return

        if self.detailed:
            click.echo(
                f"📥 Downloaded {len(downloaded_files)} generated files to {download_dir}:",
                err=True,
            )
            for file_path in downloaded_files:
                click.echo(f"  → {file_path}", err=True)
        else:
            click.echo(
                f"📥 Downloaded {len(downloaded_files)} files to {download_dir}",
                err=True,
            )

    def report_error(
        self,
        error_message: str,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        """Report error with actionable suggestions.

        Args:
            error_message: Main error message
            suggestions: Optional list of suggested solutions
        """
        if not self.should_report:
            return

        click.echo(f"❌ {error_message}", err=True)
        if suggestions and self.detailed:
            for i, suggestion in enumerate(suggestions, 1):
                click.echo(f"   {i}. {suggestion}", err=True)

    def report_cache_summary(self, cache_summary: Dict[str, Any]) -> None:
        """Report cache performance summary at end of run.

        Args:
            cache_summary: Cache statistics from SharedUploadManager
        """
        if not self.should_report or not cache_summary:
            return

        hits = cache_summary.get("hits", 0)
        misses = cache_summary.get("misses", 0)

        # Only show summary if there was cache activity
        if hits == 0 and misses == 0:
            return

        if self.detailed:
            # Detailed cache summary with decorative border
            click.echo("", err=True)  # Empty line for spacing
            click.echo(
                "─ Cache Summary ──────────────────────────────────", err=True
            )
            click.echo(
                f"Hits: {hits}   Misses: {misses}   Space saved: ~{cache_summary.get('space_saved_mb', 0)}MB",
                err=True,
            )
            click.echo(
                f"Cache DB: {cache_summary.get('cache_path', 'N/A')}", err=True
            )
            if cache_summary.get("total_entries", 0) > 0:
                click.echo(
                    f"Total entries: {cache_summary['total_entries']} ({cache_summary.get('db_size_mb', 0):.1f}MB)",
                    err=True,
                )
        else:
            # Basic cache summary - only show if there were hits
            if hits > 0:
                total_ops = hits + misses
                hit_rate = (hits / total_ops * 100) if total_ops > 0 else 0
                click.echo(
                    f"♻️  Cache: {hits}/{total_ops} hits ({hit_rate:.0f}%), ~{cache_summary.get('space_saved_mb', 0)}MB saved",
                    err=True,
                )

    def report_validation_results(
        self,
        schema_valid: bool,
        template_valid: bool,
        token_count: int,
        token_limit: int,
    ) -> None:
        """Report validation results with clear status indicators.

        Args:
            schema_valid: Whether schema validation passed
            template_valid: Whether template validation passed
            token_count: Current token count
            token_limit: Token limit for the model
        """
        if not self.should_report:
            return

        if self.detailed:
            click.echo("✅ Validation results:", err=True)
            click.echo(
                f"  ├── Schema: {'✅ Valid' if schema_valid else '❌ Invalid'}",
                err=True,
            )
            click.echo(
                f"  ├── Template: {'✅ Valid' if template_valid else '❌ Invalid'}",
                err=True,
            )
            click.echo(
                f"  └── Tokens: {token_count:,} / {token_limit:,} ({(token_count / token_limit) * 100:.1f}%)",
                err=True,
            )
        else:
            if schema_valid and template_valid:
                usage_pct = (token_count / token_limit) * 100
                if usage_pct > 80:
                    click.echo(
                        f"✅ Validation passed (⚠️  {usage_pct:.0f}% token usage)",
                        err=True,
                    )
                else:
                    click.echo("✅ Validation passed", err=True)


# Global progress reporter instance
_progress_reporter: Optional[EnhancedProgressReporter] = None


def get_progress_reporter() -> EnhancedProgressReporter:
    """Get the global progress reporter instance.

    Returns:
        Global progress reporter instance
    """
    global _progress_reporter
    if _progress_reporter is None:
        _progress_reporter = EnhancedProgressReporter()
    return _progress_reporter


def configure_progress_reporter(
    verbose: bool = False, progress: str = "basic"
) -> None:
    """Configure the global progress reporter.

    Args:
        verbose: Enable verbose logging output
        progress: Progress level (none, basic, detailed)
    """
    global _progress_reporter
    _progress_reporter = EnhancedProgressReporter(verbose, progress)


def report_phase(phase_name: str, emoji: str = "⚙️") -> None:
    """Convenience function to report a processing phase."""
    get_progress_reporter().report_phase(phase_name, emoji)


def report_success(message: str) -> None:
    """Convenience function to report success."""
    reporter = get_progress_reporter()
    if reporter.should_report:
        click.echo(f"✅ {message}", err=True)


def report_info(message: str, emoji: str = "ℹ️") -> None:
    """Convenience function to report information."""
    reporter = get_progress_reporter()
    if reporter.should_report:
        click.echo(f"{emoji} {message}", err=True)
