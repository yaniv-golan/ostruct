"""Custom error classes for CLI error handling."""

import logging
import sys
from typing import Any, Dict, List, Optional

import click

from .exit_codes import ExitCode
from .security.errors import SecurityErrorReasons

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
        import socket
        from datetime import datetime

        from .. import __version__

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


class VariableError(CLIError):
    """Base class for variable-related errors."""

    pass


class VariableNameError(VariableError):
    """Raised when a variable name is invalid or empty."""

    pass


class VariableValueError(VariableError):
    """Raised when a variable value is invalid or missing."""

    pass


class InvalidJSONError(CLIError):
    """Error raised when JSON is invalid."""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize invalid JSON error.

        Args:
            message: Error message
            source: Source of invalid JSON
            context: Additional context for the error
        """
        context = context or {}
        if source:
            context["source"] = source
        super().__init__(
            message,
            exit_code=ExitCode.DATA_ERROR,
            context=context,
        )


class PathError(CLIError):
    """Base class for path-related errors."""

    def __init__(
        self,
        message: str,
        path: str,
        context: Optional[Dict[str, Any]] = None,
        exit_code: int = ExitCode.FILE_ERROR,
    ):
        context = context or {}
        context["path"] = path
        super().__init__(message, context=context, exit_code=exit_code)


class FileNotFoundError(PathError):
    """Raised when a specified file does not exist."""

    def __init__(self, path: str, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        context.update(
            {
                "details": "The specified file does not exist or cannot be accessed",
                "troubleshooting": [
                    "Check if the file exists",
                    "Verify the path spelling is correct",
                    "Check file permissions",
                    "Ensure parent directories exist",
                ],
            }
        )
        super().__init__(f"File not found: {path}", path=path, context=context)


class FileReadError(PathError):
    """Raised when a file cannot be read or decoded.

    This is a wrapper exception that preserves the original cause (FileNotFoundError,
    UnicodeDecodeError, etc) while providing a consistent interface for error handling.
    """

    def __init__(
        self, message: str, path: str, context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, path, context)


class DirectoryNotFoundError(PathError):
    """Raised when a specified directory does not exist."""

    def __init__(self, path: str, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        context.update(
            {
                "details": "The specified directory does not exist or cannot be accessed",
                "troubleshooting": [
                    "Check if the directory exists",
                    "Verify the path spelling is correct",
                    "Check directory permissions",
                    "Ensure parent directories exist",
                    "Use --allowed-dir to specify additional allowed directories",
                ],
            }
        )
        super().__init__(
            f"Directory not found: {path}", path=path, context=context
        )


class SecurityErrorBase(CLIError):
    """Base for security-related errors with standardized context."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize security error.

        Args:
            message: Error message
            context: Optional context dictionary
            **kwargs: Additional arguments passed to CLIError
        """
        context = context or {}
        context.setdefault("category", "security")
        super().__init__(
            message,
            context=context,
            exit_code=ExitCode.SECURITY_ERROR,
            **kwargs,
        )


class PathSecurityError(SecurityErrorBase):
    """Error raised when a path violates security constraints."""

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        error_logged: bool = False,
        wrapped: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize error.

        Args:
            message: Error message
            path: Path that caused the error
            error_logged: Whether error has been logged
            wrapped: Whether this is a wrapped error
            context: Additional error context
        """
        context = context or {}
        if path is not None:
            context["path"] = path
            context.setdefault(
                "details", "The specified path violates security constraints"
            )
            context.setdefault(
                "troubleshooting",
                [
                    "Check if the path is within allowed directories",
                    "Use --allowed-dir to specify additional allowed directories",
                    "Verify path permissions",
                ],
            )

        super().__init__(message, context=context)
        self._wrapped = wrapped
        self._error_logged = error_logged

    @property
    def error_logged(self) -> bool:
        """Whether this error has been logged."""
        return self._error_logged

    @property
    def wrapped(self) -> bool:
        """Whether this is a wrapped error."""
        return self._wrapped

    @classmethod
    def from_expanded_paths(
        cls,
        original_path: str,
        expanded_path: str,
        base_dir: str,
        allowed_dirs: List[str],
        error_logged: bool = False,
    ) -> "PathSecurityError":
        """Create error with expanded path information.

        Args:
            original_path: Original path provided
            expanded_path: Expanded absolute path
            base_dir: Base directory
            allowed_dirs: List of allowed directories
            error_logged: Whether error has been logged

        Returns:
            PathSecurityError instance
        """
        context = {
            "original_path": original_path,
            "expanded_path": expanded_path,
            "base_dir": base_dir,
            "allowed_dirs": allowed_dirs,
            "reason": SecurityErrorReasons.PATH_OUTSIDE_ALLOWED,
            "details": "The path resolves to a location outside the allowed directories",
            "troubleshooting": [
                f"Ensure path is within base directory: {base_dir}",
                "Use --allowed-dir to specify additional allowed directories",
                f"Current allowed directories: {', '.join(allowed_dirs)}",
            ],
        }

        return cls(
            f"Access denied: {original_path!r} resolves to {expanded_path!r} which is "
            f"outside base directory {base_dir!r}",
            path=original_path,
            error_logged=error_logged,
            context=context,
        )

    @classmethod
    def wrap_error(cls, msg: str, original: Exception) -> "PathSecurityError":
        """Wrap an existing error with additional context.

        Args:
            msg: New error message
            original: Original error to wrap

        Returns:
            New PathSecurityError instance
        """
        context = {
            "wrapped_error": type(original).__name__,
            "original_message": str(original),
        }

        if hasattr(original, "context"):
            context.update(original.context)

        return cls(
            f"{msg}: {str(original)}",
            path=getattr(original, "path", None),
            error_logged=getattr(original, "error_logged", False),
            wrapped=True,
            context=context,
        )


class TaskTemplateError(CLIError):
    """Base class for task template-related errors."""

    pass


class TaskTemplateSyntaxError(TaskTemplateError):
    """Raised when a task template has invalid syntax."""

    pass


class TaskTemplateVariableError(TaskTemplateError):
    """Raised when a task template uses undefined variables."""

    pass


class TemplateValidationError(TaskTemplateError):
    """Raised when template validation fails."""

    pass


class SystemPromptError(TaskTemplateError):
    """Raised when there are issues with system prompt loading or processing."""

    pass


class SchemaError(CLIError):
    """Base class for schema-related errors."""

    pass


class SchemaFileError(CLIError):
    """Error raised when schema file cannot be read."""

    def __init__(
        self,
        message: str,
        schema_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize schema file error.

        Args:
            message: Error message
            schema_path: Path to schema file
            context: Additional context for the error
        """
        context = context or {}
        if schema_path and "source" not in context:
            context["schema_path"] = schema_path
            context["source"] = schema_path  # Use new standard field
            context.setdefault(
                "details",
                "The schema file could not be read or contains errors",
            )
            context.setdefault(
                "troubleshooting",
                [
                    "Verify the schema file exists",
                    "Check if the schema file contains valid JSON",
                    "Ensure the schema follows the correct format",
                    "Check file permissions",
                ],
            )

        super().__init__(
            message,
            context=context,
            exit_code=ExitCode.SCHEMA_ERROR,
        )

    @property
    def schema_path(self) -> Optional[str]:
        """Get the schema path."""
        return self.context.get("schema_path")


class SchemaValidationError(CLIError):
    """Raised when a schema fails validation."""

    def __init__(
        self,
        message: str,
        schema_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        context = context or {}
        if schema_path:
            context["schema_path"] = schema_path
            context["source"] = schema_path
            context.setdefault("details", "The schema validation failed")
            context.setdefault(
                "troubleshooting",
                [
                    "Check if the schema follows JSON Schema specification",
                    "Verify all required fields are present",
                    "Ensure field types are correctly specified",
                    "Check for any syntax errors in the schema",
                ],
            )

        super().__init__(
            message,
            context=context,
            exit_code=ExitCode.SCHEMA_ERROR,
        )


class ModelCreationError(CLIError):
    """Base class for model creation errors."""

    pass


class FieldDefinitionError(ModelCreationError):
    """Raised when field definition fails."""

    def __init__(self, field_name: str, field_type: str, error: str):
        self.field_name = field_name
        self.field_type = field_type
        super().__init__(
            f"Failed to define field '{field_name}' of type '{field_type}': {error}"
        )


class NestedModelError(ModelCreationError):
    """Raised when nested model creation fails."""

    def __init__(self, model_name: str, parent_field: str, error: str):
        self.model_name = model_name
        self.parent_field = parent_field
        super().__init__(
            f"Failed to create nested model '{model_name}' for field '{parent_field}': {error}"
        )


class ModelValidationError(ModelCreationError):
    """Raised when model validation fails."""

    def __init__(self, model_name: str, validation_errors: List[str]):
        self.model_name = model_name
        self.validation_errors = validation_errors
        super().__init__(
            f"Model '{model_name}' validation failed:\n"
            + "\n".join(validation_errors)
        )


class ModelNotSupportedError(CLIError):
    """Exception raised when a model doesn't support structured output."""

    pass


class StreamInterruptedError(CLIError):
    """Exception raised when a stream is interrupted."""

    pass


class StreamBufferError(CLIError):
    """Exception raised when there's an error with the stream buffer."""

    pass


class StreamParseError(CLIError):
    """Exception raised when there's an error parsing the stream."""

    pass


class APIResponseError(CLIError):
    """Exception raised when there's an error with the API response."""

    pass


class EmptyResponseError(CLIError):
    """Exception raised when the API returns an empty response."""

    pass


class InvalidResponseFormatError(CLIError):
    """Exception raised when the API response format is invalid."""

    pass


class OpenAIClientError(CLIError):
    """Exception raised when there's an error with the OpenAI client.

    This is a wrapper around openai_structured's OpenAIClientError to maintain
    compatibility with our CLI error handling.
    """

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.API_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


# Export public API
__all__ = [
    "CLIError",
    "VariableError",
    "PathError",
    "PathSecurityError",
    "FileNotFoundError",
    "FileReadError",
    "DirectoryNotFoundError",
    "SchemaValidationError",
    "SchemaFileError",
    "InvalidJSONError",
    "ModelCreationError",
    "ModelNotSupportedError",
    "StreamInterruptedError",
    "StreamBufferError",
    "StreamParseError",
    "APIResponseError",
    "EmptyResponseError",
    "InvalidResponseFormatError",
    "OpenAIClientError",
]
