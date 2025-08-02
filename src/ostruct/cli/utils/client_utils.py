"""Shared utilities for OpenAI client creation and validation."""

import logging
import os
from typing import Optional

from openai import AsyncOpenAI

from ..errors import CLIError
from ..exit_codes import ExitCode

logger = logging.getLogger(__name__)


def _get_effective_api_key(api_key: Optional[str] = None) -> Optional[str]:
    """Get the effective API key from CLI argument or environment.

    Args:
        api_key: Optional API key from command line.

    Returns:
        The effective API key or None if not found.
    """
    return api_key or os.getenv("OPENAI_API_KEY")


def _get_api_key_error_message() -> str:
    """Get the standard API key error message."""
    return (
        "No OpenAI API key found. Please:\n"
        "  • Set OPENAI_API_KEY environment variable, or\n"
        "  • Create a .env file with OPENAI_API_KEY=your-key-here, or\n"
        "  • Use --api-key option (not recommended for production)\n"
        "\n"
        "Get your API key from: https://platform.openai.com/api-keys"
    )


def create_openai_client(
    api_key: Optional[str] = None,
    timeout: float = 60.0,
    *,
    max_timeout: float = 300.0,
) -> AsyncOpenAI:
    """Create and validate an AsyncOpenAI client instance.

    Args:
        api_key: Optional API key (falls back to OPENAI_API_KEY env var).
        timeout: Requested timeout in seconds.
        max_timeout: Maximum allowed timeout (defaults to 300s).

    Returns:
        Configured AsyncOpenAI client.

    Raises:
        CLIError: If API key is missing or invalid.
    """
    # Reuse the validation logic (will raise CLIError if key is missing)
    validate_api_key_availability(api_key=api_key, warn_only=False)

    # We know the key exists now, so get it again
    effective_key = _get_effective_api_key(api_key)
    effective_timeout = min(timeout, max_timeout)
    return AsyncOpenAI(api_key=effective_key, timeout=effective_timeout)


def validate_api_key_availability(
    api_key: Optional[str] = None,
    warn_only: bool = False,
) -> bool:
    """Validate that an OpenAI API key is available from any source.

    Args:
        api_key: Optional API key (falls back to OPENAI_API_KEY env var).
        warn_only: If True, only log a warning instead of raising an error.

    Returns:
        True if API key is available, False otherwise.

    Raises:
        CLIError: If API key is missing and warn_only=False.
    """
    effective_key = _get_effective_api_key(api_key)
    if not effective_key:
        error_msg = _get_api_key_error_message()

        if warn_only:
            logger.warning(
                "⚠️  API key validation failed (dry-run mode):\n%s", error_msg
            )
            return False
        else:
            raise CLIError(error_msg, exit_code=ExitCode.API_ERROR)

    return True
