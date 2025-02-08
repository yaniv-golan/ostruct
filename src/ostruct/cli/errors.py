"""Custom error classes for CLI error handling."""

import logging
from typing import Any, Dict, List, Optional, TextIO, cast

import click

from .security.errors import PathSecurityError as SecurityPathSecurityError

logger = logging.getLogger(__name__)


class CLIError(click.ClickException):
    """Base class for all CLI errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}
        self._has_been_logged = False  # Use underscore for private attribute

    @property
    def has_been_logged(self) -> bool:
        """Whether this error has been logged."""
        return self._has_been_logged

    @has_been_logged.setter
    def has_been_logged(self, value: bool) -> None:
        """Set whether this error has been logged."""
        self._has_been_logged = value

    def show(self, file: Optional[TextIO] = None) -> None:
        """Show the error message with optional context."""
        if file is None:
            file = cast(TextIO, click.get_text_stream("stderr"))

        # Format message with context if available
        if self.context:
            context_str = "\n".join(
                f"  {k}: {v}" for k, v in self.context.items()
            )
            click.secho(
                f"Error: {self.message}\nContext:\n{context_str}",
                fg="red",
                file=file,
            )
        else:
            click.secho(f"Error: {self.message}", fg="red", file=file)


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
    """Raised when JSON parsing fails for a variable value."""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        context = context or {}
        if source:
            context["source"] = source
        super().__init__(message, context)


class PathError(CLIError):
    """Base class for path-related errors."""

    def __init__(
        self, message: str, path: str, context: Optional[Dict[str, Any]] = None
    ):
        context = context or {}
        context["path"] = path
        super().__init__(message, context)


class FileNotFoundError(PathError):
    """Raised when a specified file does not exist."""

    def __init__(self, path: str, context: Optional[Dict[str, Any]] = None):
        # Use path directly as the message without prepending "File not found: "
        super().__init__(path, path, context)


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
        super().__init__(path, path, context)


class PathSecurityError(CLIError, SecurityPathSecurityError):
    """CLI wrapper for security package's PathSecurityError.

    This class bridges the security package's error handling with the CLI's
    error handling system, providing both sets of functionality.
    """

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        error_logged: bool = False,
    ):
        """Initialize both parent classes properly.

        Args:
            message: The error message
            path: The path that caused the error
            context: Additional context about the error
            error_logged: Whether this error has been logged
        """
        # Initialize security error first
        SecurityPathSecurityError.__init__(
            self,
            message,
            path=path or "",
            context=context,
            error_logged=error_logged,
        )
        # Initialize CLI error with the same context
        CLIError.__init__(self, message, context=self.context)
        # Ensure error_logged state is consistent
        self._has_been_logged = error_logged
        logger.debug(
            "Created CLI PathSecurityError with message=%r, path=%r, context=%r, error_logged=%r",
            message,
            path,
            self.context,
            error_logged,
        )

    def show(self, file: Optional[TextIO] = None) -> None:
        """Show the error with CLI formatting."""
        logger.debug("Showing error with context: %r", self.context)
        super().show(file)

    @property
    def has_been_logged(self) -> bool:
        """Whether this error has been logged."""
        return self._has_been_logged or super().has_been_logged

    @has_been_logged.setter
    def has_been_logged(self, value: bool) -> None:
        """Set whether this error has been logged."""
        self._has_been_logged = value
        super().has_been_logged = value  # type: ignore[misc]

    @property
    def error_logged(self) -> bool:
        """Whether this error has been logged (alias for has_been_logged)."""
        return self.has_been_logged

    @error_logged.setter
    def error_logged(self, value: bool) -> None:
        """Set whether this error has been logged (alias for has_been_logged)."""
        self.has_been_logged = value

    def __str__(self) -> str:
        """Format the error message with context."""
        msg = SecurityPathSecurityError.__str__(self)
        logger.debug("Formatted error message: %r", msg)
        return msg


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
    """Raised when a schema file is invalid or inaccessible."""

    def __init__(
        self,
        message: str,
        schema_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        context = context or {}
        if schema_path:
            context["schema_path"] = schema_path
        super().__init__(message, context)


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
        super().__init__(message, context)


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


class ModelVersionError(CLIError):
    """Exception raised when a model version is not supported."""

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
    """Exception raised when there's an error with the OpenAI client."""

    pass


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
    "ModelVersionError",
    "StreamInterruptedError",
    "StreamBufferError",
    "StreamParseError",
    "APIResponseError",
    "EmptyResponseError",
    "InvalidResponseFormatError",
    "OpenAIClientError",
]
