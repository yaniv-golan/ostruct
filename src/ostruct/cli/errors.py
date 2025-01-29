"""Custom error classes for CLI error handling."""

from pathlib import Path
from typing import List, Optional


class CLIError(Exception):
    """Base class for all CLI errors."""

    pass


class VariableError(CLIError):
    """Base class for variable-related errors."""

    pass


class VariableNameError(VariableError):
    """Raised when a variable name is invalid or empty."""

    pass


class VariableValueError(VariableError):
    """Raised when a variable value is invalid or missing."""

    pass


class InvalidJSONError(VariableError):
    """Raised when JSON parsing fails for a variable value."""

    pass


class PathError(CLIError):
    """Base class for path-related errors."""

    pass


class FileNotFoundError(PathError):
    """Raised when a specified file does not exist."""

    pass


class DirectoryNotFoundError(PathError):
    """Raised when a specified directory does not exist."""

    pass


class PathSecurityError(Exception):
    """Exception raised when file access is denied due to security constraints.

    Attributes:
        message: The error message with full context
        error_logged: Whether this error has already been logged
        wrapped: Whether this error has been wrapped by another error
    """

    def __init__(
        self, message: str, error_logged: bool = False, wrapped: bool = False
    ) -> None:
        """Initialize PathSecurityError.

        Args:
            message: Detailed error message with context
            error_logged: Whether this error has already been logged
            wrapped: Whether this error has been wrapped by another error
        """
        super().__init__(message)
        self.error_logged = error_logged
        self.message = message
        self.wrapped = wrapped

    @property
    def has_been_logged(self) -> bool:
        """Check if this error has been logged, more readable than accessing error_logged directly."""
        return self.error_logged

    def __str__(self) -> str:
        """Get string representation of the error."""
        return self.message

    @classmethod
    def access_denied(
        cls,
        path: Path,
        reason: Optional[str] = None,
        error_logged: bool = False,
    ) -> "PathSecurityError":
        """Create access denied error.

        Args:
            path: Path that was denied
            reason: Optional reason for denial
            error_logged: Whether this error has already been logged

        Returns:
            PathSecurityError with standardized message
        """
        msg = f"Access denied: {path}"
        if reason:
            msg += f" - {reason}"
        return cls(msg, error_logged=error_logged)

    @classmethod
    def outside_allowed(
        cls,
        path: Path,
        base_dir: Optional[Path] = None,
        error_logged: bool = False,
    ) -> "PathSecurityError":
        """Create error for path outside allowed directories.

        Args:
            path: Path that was outside
            base_dir: Optional base directory for context
            error_logged: Whether this error has already been logged

        Returns:
            PathSecurityError with standardized message
        """
        parts = [
            f"Access denied: {path} is outside base directory and not in allowed directories"
        ]
        if base_dir:
            parts.append(f"Base directory: {base_dir}")
        parts.append(
            "Use --allowed-dir to specify additional allowed directories"
        )
        return cls("\n".join(parts), error_logged=error_logged)

    @classmethod
    def traversal_attempt(
        cls, path: Path, error_logged: bool = False
    ) -> "PathSecurityError":
        """Create error for directory traversal attempt.

        Args:
            path: Path that attempted traversal
            error_logged: Whether this error has already been logged

        Returns:
            PathSecurityError with standardized message
        """
        return cls(
            f"Access denied: {path} - directory traversal not allowed",
            error_logged=error_logged,
        )

    @classmethod
    def from_expanded_paths(
        cls,
        original_path: str,
        expanded_path: str,
        base_dir: Optional[str] = None,
        allowed_dirs: Optional[List[str]] = None,
        error_logged: bool = False,
    ) -> "PathSecurityError":
        """Create error with expanded path context.

        Args:
            original_path: Original path as provided by user
            expanded_path: Expanded absolute path
            base_dir: Optional base directory
            allowed_dirs: Optional list of allowed directories
            error_logged: Whether this error has already been logged

        Returns:
            PathSecurityError with detailed path context
        """
        parts = [
            f"Access denied: {original_path} is outside base directory and not in allowed directories",
            f"File absolute path: {expanded_path}",
        ]
        if base_dir:
            parts.append(f"Base directory: {base_dir}")
        if allowed_dirs:
            parts.append(f"Allowed directories: {allowed_dirs}")
        parts.append(
            "Use --allowed-dir to specify additional allowed directories"
        )
        return cls("\n".join(parts), error_logged=error_logged)

    def format_with_context(
        self,
        original_path: Optional[str] = None,
        expanded_path: Optional[str] = None,
        base_dir: Optional[str] = None,
        allowed_dirs: Optional[List[str]] = None,
    ) -> str:
        """Format error message with additional context.

        Args:
            original_path: Optional original path as provided by user
            expanded_path: Optional expanded absolute path
            base_dir: Optional base directory
            allowed_dirs: Optional list of allowed directories

        Returns:
            Formatted error message with context
        """
        parts = [self.message]
        if original_path and expanded_path and original_path != expanded_path:
            parts.append(f"Original path: {original_path}")
            parts.append(f"Expanded path: {expanded_path}")
        if base_dir:
            parts.append(f"Base directory: {base_dir}")
        if allowed_dirs:
            parts.append(f"Allowed directories: {allowed_dirs}")
        if not any(
            p.endswith(
                "Use --allowed-dir to specify additional allowed directories"
            )
            for p in parts
        ):
            parts.append(
                "Use --allowed-dir to specify additional allowed directories"
            )
        return "\n".join(parts)

    @classmethod
    def wrap_error(
        cls, context: str, original: "PathSecurityError"
    ) -> "PathSecurityError":
        """Wrap an error with additional context while preserving attributes.

        Args:
            context: Additional context to add to the error message
            original: The original PathSecurityError to wrap

        Returns:
            PathSecurityError with additional context and preserved attributes
        """
        base_message = str(original)
        message = f"{context}: {base_message}"
        return cls(message, error_logged=original.error_logged, wrapped=True)


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


class SchemaFileError(SchemaError):
    """Raised when a schema file is invalid or inaccessible."""

    pass


class SchemaValidationError(SchemaError):
    """Raised when a schema fails validation."""

    pass


class ModelCreationError(SchemaError):
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
