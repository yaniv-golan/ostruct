"""Custom error classes for CLI error handling."""

import logging
from typing import Any, Dict, List, Optional

import click

from .exit_codes import ExitCode
from .security.errors import SecurityErrorReasons

logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Base class for CLI errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exit_code: int = ExitCode.INTERNAL_ERROR,
    ) -> None:
        """Initialize CLI error.

        Args:
            message: Error message
            context: Optional context dictionary
            exit_code: Exit code to use (defaults to INTERNAL_ERROR)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.exit_code = exit_code

    def show(self, file: bool = True) -> None:
        """Display error message to user.

        Args:
            file: Whether to write to stderr (True) or stdout (False)
        """
        click.secho(str(self), fg="red", err=file)

    def __str__(self) -> str:
        """Get string representation of error."""
        if self.context:
            context_str = "\n".join(
                f"{k}: {v}" for k, v in self.context.items()
            )
            return f"{self.message}\nContext:\n{context_str}"
        return self.message


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
        self, message: str, path: str, context: Optional[Dict[str, Any]] = None
    ):
        context = context or {}
        context["path"] = path
        super().__init__(message, context=context)


class FileNotFoundError(PathError):
    """Raised when a specified file does not exist."""

    def __init__(self, path: str, context: Optional[Dict[str, Any]] = None):
        # Use path directly as the message without prepending "File not found: "
        super().__init__(path, path=path, context=context)


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
        # Use path directly as the message without prepending "Directory not found: "
        super().__init__(path, path=path, context=context)


class PathSecurityError(CLIError):
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
        if context is None:
            context = {}
        if path is not None:
            context["path"] = path
        super().__init__(
            message,
            exit_code=ExitCode.SECURITY_ERROR,
            context=context,
        )
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
        # Create initial error instance
        error = cls(
            f"Access denied: {original_path!r} resolves to {expanded_path!r} which is "
            f"outside base directory {base_dir!r}",
            path=original_path,
            error_logged=error_logged,
            context={
                "original_path": original_path,
                "expanded_path": expanded_path,
                "base_dir": base_dir,
                "allowed_dirs": allowed_dirs,
                "reason": SecurityErrorReasons.PATH_OUTSIDE_ALLOWED,
            },
        )

        # Format the message with full context
        formatted_msg = error.format_with_context(
            original_path=original_path,
            expanded_path=expanded_path,
            base_dir=base_dir,
            allowed_dirs=allowed_dirs,
        )

        # Return new instance with formatted message
        return cls(
            formatted_msg,
            path=original_path,
            error_logged=error_logged,
            context=error.context,
        )

    def format_with_context(
        self,
        original_path: str,
        expanded_path: str,
        base_dir: str,
        allowed_dirs: List[str],
    ) -> str:
        """Format error message with path context.

        Args:
            original_path: Original path provided
            expanded_path: Expanded absolute path
            base_dir: Base directory
            allowed_dirs: List of allowed directories

        Returns:
            Formatted error message
        """
        lines = [
            str(self),
            "",
            "Path Details:",
            f"  Original path: {original_path}",
            f"  Expanded path: {expanded_path}",
            f"  Base directory: {base_dir}",
            f"  Allowed directories: {allowed_dirs}",
            "",
            "Use --allowed-dir to specify additional allowed directories",
        ]
        return "\n".join(lines)

    @classmethod
    def wrap_error(
        cls, msg: str, original: "PathSecurityError"
    ) -> "PathSecurityError":
        """Wrap an existing error with additional context.

        Args:
            msg: New error message
            original: Original error to wrap

        Returns:
            New PathSecurityError instance
        """
        return cls(
            f"{msg}: {str(original)}",
            error_logged=original.error_logged,
            wrapped=True,
            context=original.context if hasattr(original, "context") else None,
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
    ):
        """Initialize schema file error.

        Args:
            message: Error message
            schema_path: Path to schema file
            context: Additional context for the error
        """
        context = context or {}
        if schema_path:
            context["schema_path"] = schema_path
        super().__init__(
            message,
            exit_code=ExitCode.SCHEMA_ERROR,
            context=context,
        )


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
        super().__init__(message, context=context)


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
