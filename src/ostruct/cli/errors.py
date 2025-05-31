"""Custom error classes for CLI error handling."""

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAIError

from .base_errors import CLIError, OstructFileNotFoundError
from .exit_codes import ExitCode
from .security.base import SecurityErrorBase
from .security.errors import SecurityErrorReasons

logger = logging.getLogger(__name__)


class VariableError(CLIError):
    """Base class for variable-related errors."""

    pass


class VariableNameError(VariableError):
    """Raised when a variable name is invalid or empty."""

    pass


class VariableValueError(VariableError):
    """Raised when a variable value is invalid or missing."""

    pass


class DuplicateFileMappingError(VariableError):
    """Raised when duplicate file mappings are detected."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize error.

        Args:
            message: Error message
            context: Additional error context
        """
        super().__init__(
            message,
            context=context,
            exit_code=ExitCode.USAGE_ERROR,
        )


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

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize error.

        Args:
            message: Error message
            context: Additional error context
        """
        super().__init__(
            message,
            context=context,
            exit_code=ExitCode.VALIDATION_ERROR,
        )


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
    """Raised when the response format is invalid."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        if "schema must be a JSON Schema of 'type: \"object\"'" in message:
            message = (
                "The schema must have a root type of 'object', but got 'array'. "
                "To fix this, wrap your array in an object. For example:\n\n"
                "{\n"
                '  "type": "object",\n'
                '  "properties": {\n'
                '    "items": {\n'
                '      "type": "array",\n'
                '      "items": { ... your array items schema ... }\n'
                "    }\n"
                "  },\n"
                '  "required": ["items"]\n'
                "}\n\n"
                "Then update your template to handle the wrapper object."
            )
        super().__init__(
            message,
            exit_code=ExitCode.API_ERROR,
            context=context,
        )


# Tool-specific error classes (T3.1)


class FileSearchError(CLIError):
    """File Search tool failures with retry guidance."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.API_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


class FileSearchUploadError(FileSearchError):
    """File upload to vector store failed."""

    pass


class MCPConnectionError(CLIError):
    """MCP server connection failures."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.API_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


class ContainerExpiredError(CLIError):
    """Code Interpreter container expired (20-minute limit)."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.API_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


class UnattendedOperationTimeoutError(CLIError):
    """Operation timed out during unattended execution."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.OPERATION_TIMEOUT,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


class PromptTooLargeError(CLIError):
    """Prompt exceeds context window limits."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.VALIDATION_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


class AuthenticationError(CLIError):
    """API authentication failures."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.API_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


class RateLimitError(CLIError):
    """API rate limiting errors."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.API_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


class APIError(CLIError):
    """Generic API errors."""

    def __init__(
        self,
        message: str,
        exit_code: ExitCode = ExitCode.API_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, exit_code=exit_code, context=context)


# API Error Mapping (T3.1)


class APIErrorMapper:
    """Maps OpenAI SDK errors to ostruct-specific errors with actionable guidance."""

    @staticmethod
    def map_openai_error(error: OpenAIError) -> CLIError:
        """Map OpenAI SDK errors to ostruct errors (validated patterns).

        Args:
            error: OpenAI SDK error to map

        Returns:
            Appropriate ostruct error with actionable guidance
        """
        error_msg = str(error).lower()

        # Context window errors (confirmed pattern)
        if (
            "context_length_exceeded" in error_msg
            or "maximum context length" in error_msg
        ):
            return PromptTooLargeError(
                f"Prompt exceeds model context window (128,000 token limit). "
                f"Tip: Use explicit file routing (-fc for code, -fs for docs, -ft for config). "
                f"Original error: {error}"
            )

        # Authentication errors (confirmed pattern)
        if "invalid_api_key" in error_msg or "incorrect api key" in error_msg:
            return AuthenticationError(
                f"Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable. "
                f"Original error: {error}"
            )

        # Rate limiting (standard pattern)
        if "rate_limit" in error_msg:
            return RateLimitError(
                f"OpenAI API rate limit exceeded. Please wait and try again. "
                f"Original error: {error}"
            )

        # Schema validation errors (Responses API specific)
        if "invalid schema for response_format" in error_msg:
            return SchemaValidationError(
                f"Schema validation failed for Responses API. "
                f"Ensure your schema is compatible with strict mode. "
                f"Original error: {error}"
            )

        # Container expiration errors (Code Interpreter specific)
        if "container" in error_msg and (
            "expired" in error_msg or "timeout" in error_msg
        ):
            return ContainerExpiredError(
                f"Code Interpreter container expired (20-minute runtime limit, 2-minute idle timeout). "
                f"Please retry your request. Original error: {error}"
            )

        # File Search errors
        if "vector_store" in error_msg or "file_search" in error_msg:
            return FileSearchError(
                f"File Search operation failed. This can be intermittent - consider retrying. "
                f"Original error: {error}"
            )

        # MCP connection errors
        if "mcp" in error_msg or "model context protocol" in error_msg:
            return MCPConnectionError(
                f"MCP server connection failed. Check server URL and network connectivity. "
                f"Original error: {error}"
            )

        # Generic API error
        return APIError(f"OpenAI API error: {error}")

    @staticmethod
    def map_tool_error(tool_name: str, error: Exception) -> CLIError:
        """Map tool-specific errors to ostruct errors.

        Args:
            tool_name: Name of the tool that failed
            error: The original error

        Returns:
            Appropriate ostruct error with tool-specific guidance
        """
        error_msg = str(error).lower()

        if tool_name == "file-search":
            if "upload" in error_msg or "vector_store" in error_msg:
                return FileSearchUploadError(
                    f"File Search upload failed: {error}. "
                    f"This can be intermittent - retry with --file-search-retry-count option."
                )
            return FileSearchError(f"File Search error: {error}")

        elif tool_name == "code-interpreter":
            if "container" in error_msg:
                return ContainerExpiredError(
                    f"Code Interpreter container error: {error}. "
                    f"Container has 20-minute runtime and 2-minute idle limits."
                )
            return APIError(f"Code Interpreter error: {error}")

        elif tool_name == "mcp":
            return MCPConnectionError(
                f"MCP server error: {error}. "
                f"Check server connectivity and require_approval='never' setting."
            )

        return APIError(f"{tool_name} error: {error}")


class SchemaValidationError(ModelCreationError):
    """Raised when schema validation fails."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exit_code: ExitCode = ExitCode.SCHEMA_ERROR,
    ):
        context = context or {}
        # Preserve validation type for error handling
        context.setdefault("validation_type", "schema")

        # Format error message with tips
        formatted_message = []

        if "path" in context:
            formatted_message.append(f"\nLocation: {context['path']}")

        if "found" in context:
            formatted_message.append(f"Found: {context['found']}")

        if "reference" in context:
            formatted_message.append(f"Reference: {context['reference']}")

        if "count" in context:
            formatted_message.append(f"Count: {context['count']}")

        if "missing_required" in context:
            formatted_message.append(
                f"Missing required: {context['missing_required']}"
            )

        if "extra_required" in context:
            formatted_message.append(
                f"Extra required: {context['extra_required']}"
            )

        if "prohibited_used" in context:
            formatted_message.append(
                f"Prohibited keywords used: {context['prohibited_used']}"
            )

        if "tips" in context:
            formatted_message.append("\nHow to fix:")
            for tip in context["tips"]:
                if isinstance(tip, dict):
                    # Format JSON example
                    formatted_message.append("Example schema:")
                    formatted_message.append(json.dumps(tip, indent=2))
                else:
                    formatted_message.append(f"- {tip}")

        # Combine message with details
        final_message = message
        if formatted_message:
            final_message += "\n" + "\n".join(formatted_message)

        super().__init__(final_message, context=context, exit_code=exit_code)


def handle_error(e: Exception) -> None:
    """Handle CLI errors and display appropriate messages.

    Maintains specific error type handling while reducing duplication.
    Provides enhanced debug logging for CLI errors.
    """
    import sys

    import click

    # 1. Determine error type and message
    if isinstance(e, SchemaValidationError):
        msg = str(e)  # Already formatted in SchemaValidationError
        exit_code = e.exit_code
    elif isinstance(e, ModelCreationError):
        # Unwrap ModelCreationError that might wrap SchemaValidationError
        if isinstance(e.__cause__, SchemaValidationError):
            return handle_error(e.__cause__)
        msg = f"Model creation error: {str(e)}"
        exit_code = ExitCode.SCHEMA_ERROR
    elif isinstance(e, click.UsageError):
        msg = f"Usage error: {str(e)}"
        exit_code = ExitCode.USAGE_ERROR
    elif isinstance(e, SchemaFileError):
        msg = str(e)  # Use existing __str__ formatting
        exit_code = ExitCode.SCHEMA_ERROR
    elif isinstance(e, (InvalidJSONError, json.JSONDecodeError)):
        msg = f"Invalid JSON error: {str(e)}"
        exit_code = ExitCode.DATA_ERROR
    elif isinstance(e, CLIError):
        msg = str(e)  # Use existing __str__ formatting
        exit_code = ExitCode(e.exit_code)  # Convert int to ExitCode
    else:
        msg = f"Unexpected error: {str(e)}"
        exit_code = ExitCode.INTERNAL_ERROR

    # 2. Debug logging
    if isinstance(e, CLIError) and logger.isEnabledFor(logging.DEBUG):
        # Format context fields with lowercase keys and simple values
        context_str = ""
        if hasattr(e, "context") and e.context:
            for key, value in sorted(e.context.items()):
                if key not in {
                    "timestamp",
                    "host",
                    "version",
                    "python_version",
                }:
                    if isinstance(value, dict):
                        context_str += (
                            f"{key.lower()}:\n{json.dumps(value, indent=2)}\n"
                        )
                    else:
                        context_str += f"{key.lower()}: {value}\n"

            logger.debug(
                f"Error details:\nType: {type(e).__name__}\n{context_str.rstrip()}"
            )
    elif not isinstance(
        e,
        (
            click.UsageError,
            DuplicateFileMappingError,
            VariableNameError,
            VariableValueError,
        ),
    ):
        logger.error(msg, exc_info=True)

    # 3. User output
    click.secho(msg, fg="red", err=True)
    sys.exit(exit_code)


# Export public API
__all__ = [
    "VariableError",
    "VariableNameError",
    "VariableValueError",
    "DuplicateFileMappingError",
    "PathError",
    "PathSecurityError",
    "OstructFileNotFoundError",
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
    "handle_error",
]
