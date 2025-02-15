"""Base error classes for CLI error handling."""

import logging
import socket
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import click

from .. import __version__
from .exit_codes import ExitCode

logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Base class for CLI errors.

    Context Dictionary Conventions:
    - schema_path: Path to schema file (preserved for compatibility)
    - source: Origin of error (new standard, falls back to schema_path)
    - path: File or directory path
    - details: Additional structured error information
    - timestamp: When the error occurred
    - host: System hostname
    - version: Software version
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exit_code: int = ExitCode.INTERNAL_ERROR,
        details: Optional[str] = None,
    ) -> None:
        """Initialize CLI error.

        Args:
            message: Error message
            context: Optional context dictionary following conventions
            exit_code: Exit code to use (defaults to INTERNAL_ERROR)
            details: Optional detailed explanation of the error
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.exit_code = exit_code

        # Add standard context fields
        if details:
            self.context["details"] = details

        # Add runtime context
        self.context.update(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "host": socket.gethostname(),
                "version": __version__,
                "python_version": sys.version.split()[0],
            }
        )

    @property
    def source(self) -> Optional[str]:
        """Get error source with backward compatibility."""
        return self.context.get("source") or self.context.get("schema_path")

    def show(self, file: bool = True) -> None:
        """Display error message to user.

        Args:
            file: Whether to write to stderr (True) or stdout (False)
        """
        click.secho(str(self), fg="red", err=file)

    def __str__(self) -> str:
        """Get string representation of error.

        Format:
        [ERROR_TYPE] Primary Message
        Details: Explanation
        Source: Origin
        Path: /path/to/resource
        Additional context fields...
        Troubleshooting:
        1. First step
        2. Second step
        """
        # Get error type from exit code
        error_type = ExitCode(self.exit_code).name

        # Start with error type and message
        lines = [f"[{error_type}] {self.message}"]

        # Add details if present
        if details := self.context.get("details"):
            lines.append(f"Details: {details}")

        # Add source and path information
        if source := self.source:
            lines.append(f"Source: {source}")
        if path := self.context.get("path"):
            lines.append(f"Path: {path}")

        # Add any expanded path information
        if original_path := self.context.get("original_path"):
            lines.append(f"Original Path: {original_path}")
        if expanded_path := self.context.get("expanded_path"):
            lines.append(f"Expanded Path: {expanded_path}")
        if base_dir := self.context.get("base_dir"):
            lines.append(f"Base Directory: {base_dir}")
        if allowed_dirs := self.context.get("allowed_dirs"):
            if isinstance(allowed_dirs, list):
                lines.append(f"Allowed Directories: {allowed_dirs}")
            else:
                lines.append(f"Allowed Directory: {allowed_dirs}")

        # Add other context fields (excluding reserved ones)
        reserved_keys = {
            "source",
            "details",
            "schema_path",
            "timestamp",
            "host",
            "version",
            "python_version",
            "troubleshooting",
            "path",
            "original_path",
            "expanded_path",
            "base_dir",
            "allowed_dirs",
        }
        context_lines = []
        for k, v in sorted(self.context.items()):
            if k not in reserved_keys and v is not None:
                # Convert key to title case and replace underscores with spaces
                formatted_key = k.replace("_", " ").title()
                context_lines.append(f"{formatted_key}: {v}")

        if context_lines:
            lines.extend(["", "Additional Information:"])
            lines.extend(context_lines)

        # Add troubleshooting tips if available
        if tips := self.context.get("troubleshooting"):
            lines.extend(["", "Troubleshooting:"])
            if isinstance(tips, list):
                lines.extend(f"  {i+1}. {tip}" for i, tip in enumerate(tips))
            else:
                lines.append(f"  1. {tips}")

        return "\n".join(lines)


class OstructFileNotFoundError(CLIError):
    """Raised when a file is not found.

    This is Ostruct's custom error for file not found scenarios, distinct from Python's built-in
    FileNotFoundError. It provides additional context and troubleshooting information specific to
    the CLI context.
    """

    def __init__(self, path: str, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        context.update(
            {
                "details": "The specified file does not exist or cannot be accessed",
                "path": path,
                "troubleshooting": [
                    "Check if the file exists",
                    "Verify the path spelling is correct",
                    "Check file permissions",
                    "Ensure parent directories exist",
                ],
            }
        )
        super().__init__(
            f"File not found: {path}",
            exit_code=ExitCode.FILE_ERROR,
            context=context,
        )
