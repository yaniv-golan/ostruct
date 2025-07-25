"""Shared utilities for OpenAI client creation and validation."""

import os
from typing import Optional

from openai import AsyncOpenAI

from ..errors import CLIError
from ..exit_codes import ExitCode


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
    effective_key = api_key or os.getenv("OPENAI_API_KEY")
    if not effective_key:
        raise CLIError(
            "No OpenAI API key found. Please:\n"
            "  • Set OPENAI_API_KEY environment variable, or\n"
            "  • Create a .env file with OPENAI_API_KEY=your-key-here, or\n"
            "  • Use --api-key option (not recommended for production)\n"
            "\n"
            "Get your API key from: https://platform.openai.com/api-keys",
            exit_code=ExitCode.API_ERROR,
        )
    effective_timeout = min(timeout, max_timeout)
    return AsyncOpenAI(api_key=effective_key, timeout=effective_timeout)
