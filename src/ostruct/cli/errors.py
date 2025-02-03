"""Custom error classes for CLI error handling."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, cast

import click


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


class DirectoryNotFoundError(PathError):
    """Raised when a specified directory does not exist."""

    def __init__(self, path: str, context: Optional[Dict[str, Any]] = None):
        # Use path directly as the message without prepending "Directory not found: "
        super().__init__(path, path, context)


class PathSecurityError(PathError):
    """Exception raised when file access is denied due to security constraints.

    Attributes:
        message: The error message with full context
        wrapped: Whether this error has been wrapped by another error
    """

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        error_logged: bool = False,
    ):
        path = path or "unknown"  # Provide default path if none given
        context = context or {}
        context["has_been_logged"] = (
            error_logged  # Store in context to match parent behavior
        )
        context["wrapped"] = False  # Initialize wrapped state
        super().__init__(message, path, context)

    def __str__(self) -> str:
        """Return string representation with allowed directories if present."""
        base = super().__str__()
        if self.context and "allowed_dirs" in self.context:
            allowed = self.context["allowed_dirs"]
            if allowed:  # Only add if there are actually allowed dirs
                return f"{base} (allowed directories: {', '.join(allowed)})"
        return base

    @property
    def has_been_logged(self) -> bool:
        """Whether this error has been logged."""
        return bool(self.context.get("has_been_logged", False))

    @has_been_logged.setter
    def has_been_logged(self, value: bool) -> None:
        """Set whether this error has been logged."""
        self.context["has_been_logged"] = value

    @property
    def error_logged(self) -> bool:
        """Alias for has_been_logged for backward compatibility."""
        return self.has_been_logged

    @error_logged.setter
    def error_logged(self, value: bool) -> None:
        """Alias for has_been_logged for backward compatibility."""
        self.has_been_logged = value

    @property
    def wrapped(self) -> bool:
        """Whether this error has been wrapped by another error."""
        return bool(self.context.get("wrapped", False))

    @wrapped.setter
    def wrapped(self, value: bool) -> None:
        """Set whether this error has been wrapped."""
        self.context["wrapped"] = value

    @staticmethod
    def _format_allowed_dirs(allowed_dirs: List[str]) -> str:
        """Format allowed directories as a list representation."""
        return f"[{', '.join(repr(d) for d in allowed_dirs)}]"

    @staticmethod
    def _create_error_message(
        path: str, base_dir: Optional[str] = None
    ) -> str:
        """Create a standardized error message."""
        if base_dir:
            rel_path = os.path.relpath(path, base_dir)
            return f"Access denied: {rel_path} is outside base directory and not in allowed directories"
        return f"Access denied: {path} is outside base directory and not in allowed directories"

    @classmethod
    def from_expanded_paths(
        cls,
        original_path: str,
        expanded_path: str,
        base_dir: Optional[str] = None,
        allowed_dirs: Optional[List[str]] = None,
        error_logged: bool = False,
    ) -> "PathSecurityError":
        """Create error with expanded path context."""
        message = f"Access denied: {original_path} is outside base directory and not in allowed directories"
        if expanded_path != original_path:
            message += f" (expanded to {expanded_path})"

        context = {
            "original_path": original_path,
            "expanded_path": expanded_path,
            "has_been_logged": error_logged,
        }
        if base_dir:
            context["base_dir"] = base_dir
        if allowed_dirs:
            context["allowed_dirs"] = allowed_dirs

        # Format full message with all context
        parts = [message]
        if base_dir:
            parts.append(f"Base directory: {base_dir}")
        if allowed_dirs:
            parts.append(
                f"Allowed directories: {cls._format_allowed_dirs(allowed_dirs)}"
            )
        parts.append(
            "Use --allowed-dir to specify additional allowed directories"
        )

        return cls(
            "\n".join(parts),
            path=original_path,
            context=context,
            error_logged=error_logged,
        )

    @classmethod
    def access_denied(
        cls,
        path: Path,
        reason: Optional[str] = None,
        error_logged: bool = False,
    ) -> "PathSecurityError":
        """Create access denied error."""
        msg = f"Access denied: {path}"
        if reason:
            msg += f" - {reason}"
        msg += " is outside base directory and not in allowed directories"
        return cls(msg, path=str(path), error_logged=error_logged)

    @classmethod
    def outside_allowed(
        cls,
        path: Path,
        base_dir: Optional[Path] = None,
        error_logged: bool = False,
    ) -> "PathSecurityError":
        """Create error for path outside allowed directories."""
        msg = f"Access denied: {path} is outside base directory and not in allowed directories"
        context = {}
        if base_dir:
            context["base_directory"] = str(base_dir)
        return cls(
            msg, path=str(path), context=context, error_logged=error_logged
        )

    @classmethod
    def traversal_attempt(
        cls, path: Path, error_logged: bool = False
    ) -> "PathSecurityError":
        """Create error for directory traversal attempt."""
        msg = f"Access denied: {path} - directory traversal not allowed"
        return cls(msg, path=str(path), error_logged=error_logged)

    def format_with_context(
        self,
        original_path: Optional[str] = None,
        expanded_path: Optional[str] = None,
        base_dir: Optional[str] = None,
        allowed_dirs: Optional[List[str]] = None,
    ) -> str:
        """Format error message with additional context."""
        parts = [self.message]
        if original_path and expanded_path and original_path != expanded_path:
            parts.append(f"Original path: {original_path}")
            parts.append(f"Expanded path: {expanded_path}")
        if base_dir:
            parts.append(f"Base directory: {base_dir}")
        if allowed_dirs:
            parts.append(
                f"Allowed directories: {self._format_allowed_dirs(allowed_dirs)}"
            )
        parts.append(
            "Use --allowed-dir to specify additional allowed directories"
        )
        return "\n".join(parts)

    @classmethod
    def wrap_error(
        cls, context: str, original: "PathSecurityError"
    ) -> "PathSecurityError":
        """Wrap an error with additional context while preserving attributes."""
        message = f"{context}: {original.message}"
        new_context = original.context.copy()
        new_context["wrapped"] = True  # Mark as wrapped
        error = cls(
            message,
            path=original.context.get("path", "unknown"),
            context=new_context,
            error_logged=original.has_been_logged,
        )
        error.wrapped = True  # Ensure wrapped is set through the property
        return error


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
