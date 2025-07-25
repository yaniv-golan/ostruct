"""Shared progress handling utilities for unified reporting across CLI commands."""

from typing import Any, Dict, Optional

from ..progress_reporting import (
    configure_progress_reporter,
    get_progress_reporter,
)


class ProgressHandler:
    """Unified handler for progress reporting with batch operation support.

    This class wraps the EnhancedProgressReporter to provide a consistent interface
    for configuring and using progress reporting in different CLI commands.

    Usage:
        handler = ProgressHandler(verbose=False, progress="basic")
        with handler.batch_phase("Uploading files", "📤", len(files)) as phase:
            for file in files:
                # Process file
                phase.advance(msg=f"Processed {file}" if handler.detailed else None)
    """

    def __init__(self, verbose: bool = False, progress: str = "basic") -> None:
        """Initialize the progress handler."""
        configure_progress_reporter(verbose=verbose, progress=progress)
        self.reporter = get_progress_reporter()
        self.progress_level = progress
        self.detailed = self.reporter.detailed

    def batch_phase(
        self,
        phase_name: str,
        emoji: str = "⚙️",
        expected_steps: Optional[int] = None,
    ) -> "BatchPhaseContext":
        """Start a batch phase with optional progress bar."""
        handle = self.reporter.start_phase(phase_name, emoji, expected_steps)
        return BatchPhaseContext(self, handle)

    def simple_phase(self, phase_name: str, emoji: str = "⚙️") -> None:
        """Report a simple phase without progress bar."""
        self.reporter.report_phase(phase_name, emoji)


class BatchPhaseContext:
    """Context manager for batch phases."""

    def __init__(
        self, handler: ProgressHandler, handle: Dict[str, Any]
    ) -> None:
        self.handler = handler
        self.handle = handle

    def __enter__(self) -> "BatchPhaseContext":
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        success = exc_type is None
        self.handler.reporter.complete(self.handle, success=success)

    def advance(self, advance: int = 1, msg: Optional[str] = None) -> None:
        """Advance the progress."""
        self.handler.reporter.advance(self.handle, advance=advance, msg=msg)
