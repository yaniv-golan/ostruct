"""Shared error handling utilities for CLI commands."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class ErrorCollector:
    """Centralized error collection and formatting for batch operations.

    This class provides standardized error handling patterns across CLI commands,
    with customizable message formatting for common error types.

    Usage:
        collector = ErrorCollector()

        # Add errors during processing
        try:
            process_file(file_path)
        except Exception as e:
            collector.add_error(file_path, e)

        # Get formatted results
        if collector.has_errors():
            summary = collector.get_summary()
            formatted_errors = collector.get_formatted_errors()
    """

    def __init__(self) -> None:
        """Initialize the error collector."""
        self.errors: List[Dict[str, Any]] = []
        self._formatters: Dict[str, Callable[[str, Exception], str]] = {}

        # Register default formatters for common error types
        self._register_default_formatters()

    def _register_default_formatters(self) -> None:
        """Register default error formatters for common issues."""

        def format_file_extension_error(
            file_path: str, error: Exception
        ) -> str:
            """Format file extension errors for file-search."""
            error_str = str(error)
            if (
                "Files without extensions" in error_str
                and "not supported for file-search" in error_str
            ):
                filename = Path(file_path).name
                return f"{filename}: Cannot use with file-search (no file extension). File was uploaded successfully for template use."
            return f"{file_path}: {error_str}"

        def format_vector_store_error(file_path: str, error: Exception) -> str:
            """Format vector store binding errors."""
            error_str = str(error)
            if "Failed to add files to vector store" in error_str:
                filename = Path(file_path).name
                return f"{filename}: Upload succeeded but file-search binding failed. File available for template use."
            return f"{file_path}: {error_str}"

        def format_permission_error(file_path: str, error: Exception) -> str:
            """Format permission errors."""
            if isinstance(error, PermissionError):
                filename = Path(file_path).name
                return (
                    f"{filename}: Permission denied - check file access rights"
                )
            return f"{file_path}: {str(error)}"

        def format_file_not_found_error(
            file_path: str, error: Exception
        ) -> str:
            """Format file not found errors."""
            if isinstance(error, FileNotFoundError):
                return f"File not found: {file_path}"
            return f"{file_path}: {str(error)}"

        def format_network_error(file_path: str, error: Exception) -> str:
            """Format network-related errors."""
            error_str = str(error).lower()
            if any(
                keyword in error_str
                for keyword in ["timeout", "connection", "network"]
            ):
                filename = Path(file_path).name
                return f"{filename}: Network error - check connection and try again"
            return f"{file_path}: {str(error)}"

        # Register formatters by priority (most specific first)
        self._formatters["file_extension"] = format_file_extension_error
        self._formatters["vector_store"] = format_vector_store_error
        self._formatters["permission"] = format_permission_error
        self._formatters["file_not_found"] = format_file_not_found_error
        self._formatters["network"] = format_network_error

    def add_error(
        self,
        file_path: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an error to the collection.

        Args:
            file_path: Path to the file that caused the error
            error: The exception that occurred
            context: Optional additional context information
        """
        error_entry = {
            "file_path": file_path,
            "error": error,
            "error_type": type(error).__name__,
            "context": context or {},
            "formatted_message": None,  # Will be set when formatting
        }
        self.errors.append(error_entry)

    def format_error(self, file_path: str, error: Exception) -> str:
        """Format an error message using registered formatters.

        Args:
            file_path: Path to the file that caused the error
            error: The exception that occurred

        Returns:
            Formatted error message
        """
        # Try each formatter in order
        for formatter_name, formatter in self._formatters.items():
            try:
                formatted = formatter(file_path, error)
                # If formatter returned a different message, it handled the error
                if formatted != f"{file_path}: {str(error)}":
                    return formatted
            except Exception:
                # If formatter fails, continue to next one
                continue

        # Fallback to basic formatting
        return f"{file_path}: {str(error)}"

    def get_formatted_errors(self) -> List[str]:
        """Get all errors as formatted strings.

        Returns:
            List of formatted error messages
        """
        formatted_errors = []
        for error_entry in self.errors:
            if error_entry["formatted_message"] is None:
                # Format on demand
                error_entry["formatted_message"] = self.format_error(
                    error_entry["file_path"], error_entry["error"]
                )
            formatted_errors.append(error_entry["formatted_message"])
        return formatted_errors

    def has_errors(self) -> bool:
        """Check if any errors have been collected.

        Returns:
            True if there are errors, False otherwise
        """
        return len(self.errors) > 0

    def get_error_count(self) -> int:
        """Get the total number of errors.

        Returns:
            Number of errors collected
        """
        return len(self.errors)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of collected errors.

        Returns:
            Dictionary with error statistics and breakdown
        """
        if not self.errors:
            return {"total": 0, "by_type": {}, "by_file": {}}

        # Count errors by type
        by_type: Dict[str, int] = {}
        by_file: Dict[str, int] = {}

        for error_entry in self.errors:
            error_type = error_entry["error_type"]
            file_path = error_entry["file_path"]

            by_type[error_type] = by_type.get(error_type, 0) + 1
            by_file[file_path] = by_file.get(file_path, 0) + 1

        return {
            "total": len(self.errors),
            "by_type": by_type,
            "by_file": by_file,
            "formatted_errors": self.get_formatted_errors(),
        }

    def clear(self) -> None:
        """Clear all collected errors."""
        self.errors.clear()

    def register_formatter(
        self, name: str, formatter: Callable[[str, Exception], str]
    ) -> None:
        """Register a custom error formatter.

        Args:
            name: Name of the formatter
            formatter: Function that takes (file_path, error) and returns formatted message
        """
        self._formatters[name] = formatter

    def get_errors_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Get all errors for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of error entries for the specified file
        """
        return [
            error_entry
            for error_entry in self.errors
            if error_entry["file_path"] == file_path
        ]
