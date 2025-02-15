"""Base class for security-related errors."""

from typing import Any, Dict, Optional

from ostruct.cli.base_errors import CLIError
from ostruct.cli.exit_codes import ExitCode


class SecurityErrorBase(CLIError):
    """Base class for security-related errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        details: Optional[str] = None,
        has_been_logged: bool = False,
    ) -> None:
        """Initialize security error.

        Args:
            message: The error message.
            context: Additional context for the error.
            details: Detailed explanation of the error.
            has_been_logged: Whether the error has been logged.
        """
        if context is None:
            context = {}
        context["category"] = "security"
        super().__init__(
            message,
            context=context,
            exit_code=ExitCode.SECURITY_ERROR,
            details=details,
        )
        self._has_been_logged = has_been_logged

    @property
    def has_been_logged(self) -> bool:
        """Whether this error has been logged."""
        return self._has_been_logged

    @has_been_logged.setter
    def has_been_logged(self, value: bool) -> None:
        """Set whether this error has been logged."""
        self._has_been_logged = value
