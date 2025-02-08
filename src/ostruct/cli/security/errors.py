"""Error definitions for the security package.

This module defines custom exceptions and error reason constants used throughout
the security modules.
"""

from typing import Any, Dict, List, Optional


class PathSecurityError(Exception):
    """Base exception for security-related errors.
    
    This class provides rich error information for security-related issues,
    including context and error wrapping capabilities.
    """

    def __init__(
        self,
        message: str,
        path: str = "",
        context: Optional[Dict[str, Any]] = None,
        error_logged: bool = False,
    ) -> None:
        """Initialize the error.

        Args:
            message: The error message.
            path: The path that caused the error.
            context: Additional context about the error.
            error_logged: Whether this error has already been logged.
        """
        super().__init__(message)
        self.path = path
        self.context = context or {}
        self._error_logged = error_logged
        self._wrapped = False

    def __str__(self) -> str:
        """Format the error message with context if available."""
        msg = super().__str__()
        
        # Add expanded path information if available
        if self.context:
            if "original_path" in self.context and "expanded_path" in self.context:
                msg = f"{msg}\nOriginal path: {self.context['original_path']}\nExpanded path: {self.context['expanded_path']}"
            if "base_dir" in self.context:
                msg = f"{msg}\nBase directory: {self.context['base_dir']}"
            if "allowed_dirs" in self.context:
                msg = f"{msg}\nAllowed directories: {self.context['allowed_dirs']!r}"
        
        return msg

    @property
    def has_been_logged(self) -> bool:
        """Whether this error has been logged."""
        return self._error_logged

    @has_been_logged.setter
    def has_been_logged(self, value: bool) -> None:
        """Set whether this error has been logged."""
        self._error_logged = value

    @property
    def wrapped(self) -> bool:
        """Whether this error is wrapping another error."""
        return self._wrapped

    def format_with_context(
        self,
        original_path: str,
        expanded_path: str,
        base_dir: str,
        allowed_dirs: List[str],
    ) -> str:
        """Format the error message with additional context.

        Args:
            original_path: The original path that caused the error
            expanded_path: The expanded/absolute path
            base_dir: The base directory for security checks
            allowed_dirs: List of allowed directories

        Returns:
            A formatted error message with context
        """
        lines = [
            str(self),
            f"Original path: {original_path}",
            f"Expanded path: {expanded_path}",
            f"Base directory: {base_dir}",
            f"Allowed directories: {allowed_dirs}",
            "Use --allowed-dir to add more allowed directories"
        ]
        return "\n".join(lines)

    @classmethod
    def wrap_error(cls, message: str, original: 'PathSecurityError') -> 'PathSecurityError':
        """Wrap an existing error with additional context.

        Args:
            message: The new error message
            original: The original error to wrap

        Returns:
            A new PathSecurityError instance wrapping the original
        """
        wrapped = cls(
            f"{message}: {str(original)}",
            path=original.path,
            context=original.context,
            error_logged=original.has_been_logged
        )
        wrapped._wrapped = True
        return wrapped

    @classmethod
    def from_expanded_paths(
        cls,
        original_path: str,
        expanded_path: str,
        base_dir: str,
        allowed_dirs: List[str],
        error_logged: bool = False,
    ) -> 'PathSecurityError':
        """Create an error instance with expanded path information.

        Args:
            original_path: The original path that caused the error
            expanded_path: The expanded/absolute path
            base_dir: The base directory for security checks
            allowed_dirs: List of allowed directories
            error_logged: Whether this error has already been logged

        Returns:
            A new PathSecurityError instance with expanded path context
        """
        message = f"Path '{original_path}' is outside the base directory and not in allowed directories"
        context = {
            "original_path": original_path,
            "expanded_path": expanded_path,
            "base_dir": base_dir,
            "allowed_dirs": allowed_dirs,
        }
        return cls(message, path=original_path, context=context, error_logged=error_logged)


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