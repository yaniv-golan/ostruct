"""Error definitions for the security package.

This module defines custom exceptions and error reason constants used throughout
the security modules.
"""

from typing import Any, Dict, List, Optional

from .base import SecurityErrorBase


class PathSecurityError(SecurityErrorBase):
    """Security error for path-related issues."""

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        details: Optional[str] = None,
        error_logged: bool = False,
        wrapped: bool = False,
    ) -> None:
        """Initialize the error.

        Args:
            message: The error message.
            path: The path that caused the error.
            context: Additional context for the error.
            details: Detailed explanation of the error.
            error_logged: Whether the error has been logged.
            wrapped: Whether this is a wrapped error.
        """
        if context is None:
            context = {}
        if path is not None:
            context["path"] = path
        if details is None:
            details = "The specified path violates security constraints"
            context["troubleshooting"] = [
                "Check if the path is within allowed directories",
                "Use --allowed-dir to specify additional allowed directories",
                "Verify path permissions",
            ]
        self._wrapped = wrapped
        super().__init__(
            message,
            context=context,
            details=details,
            has_been_logged=error_logged,
        )

    @property
    def error_logged(self) -> bool:
        """Alias for has_been_logged for backward compatibility."""
        return self.has_been_logged

    @property
    def wrapped(self) -> bool:
        """Whether this is a wrapped error."""
        return self._wrapped

    @property
    def details(self) -> str:
        """Get the detailed explanation of the error."""
        return str(self.context.get("details", ""))

    @classmethod
    def from_expanded_paths(
        cls,
        original_path: str,
        expanded_path: str,
        base_dir: str,
        allowed_dirs: List[str],
        error_logged: bool = False,
    ) -> "PathSecurityError":
        """Create an error from expanded paths.

        Args:
            original_path: The original path.
            expanded_path: The expanded path.
            base_dir: The base directory.
            allowed_dirs: List of allowed directories.
            error_logged: Whether the error has been logged.

        Returns:
            A new PathSecurityError instance.
        """
        context = {
            "original_path": original_path,
            "expanded_path": expanded_path,
            "base_dir": base_dir,
            "allowed_dirs": allowed_dirs,
            "reason": SecurityErrorReasons.PATH_OUTSIDE_ALLOWED,
            "troubleshooting": [
                "Check if the path is within allowed directories",
                f"Ensure the path is within base directory: {base_dir}",
                f"Current allowed directories: {', '.join(allowed_dirs)}",
            ],
        }
        return cls(
            "Access denied",
            context=context,
            details="Path is outside allowed directories",
            error_logged=error_logged,
        )

    @classmethod
    def wrap_error(
        cls, message: str, original_error: Exception
    ) -> "PathSecurityError":
        """Wrap another error with a security error.

        Args:
            message: The security error message.
            original_error: The original error to wrap.

        Returns:
            A new PathSecurityError instance.
        """
        context = {
            "wrapped_error": original_error.__class__.__name__,
            "original_message": str(original_error),
            "wrapped": True,
            "troubleshooting": [
                "Check if the path is within allowed directories",
                "Verify path permissions",
                "Check if the original error has been resolved",
            ],
        }
        if hasattr(original_error, "context"):
            context.update(original_error.context)
        return cls(
            message,
            context=context,
            wrapped=True,
            error_logged=getattr(original_error, "error_logged", False),
        )


class DirectoryNotFoundError(PathSecurityError):
    """Raised when a directory that is expected to exist does not."""


class SecurityErrorReasons:
    """Constants for common security error reasons."""

    # Path validation errors
    PATH_TRAVERSAL = "path_traversal"
    UNSAFE_UNICODE = "unsafe_unicode"
    NORMALIZATION_ERROR = "normalization_error"
    CASE_MISMATCH = "case_mismatch"

    # Symlink-related errors
    SYMLINK_LOOP = "symlink_loop"
    SYMLINK_ERROR = "symlink_error"
    SYMLINK_TARGET_NOT_ALLOWED = "symlink_target_not_allowed"
    SYMLINK_MAX_DEPTH = "symlink_max_depth"
    SYMLINK_BROKEN = "symlink_broken"

    # Directory access errors
    PATH_NOT_IN_BASE = "path_not_in_base"
    PATH_OUTSIDE_ALLOWED = "path_outside_allowed"
    TEMP_PATHS_NOT_ALLOWED = "temp_paths_not_allowed"
