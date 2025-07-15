"""Credential sanitization utilities for preventing API key exposure."""

import re
from typing import Any, Dict

# Import safe regex patterns
from ..safe_regex import (
    SAFE_API_KEY_PATTERN,
    SAFE_BEARER_TOKEN_PATTERN,
    SAFE_URL_CREDENTIALS_PATTERN,
)


class CredentialSanitizer:
    """Sanitizes sensitive credentials from logs, error messages, and debug output."""

    # Patterns for detecting API keys and other sensitive data (ReDoS-safe)
    API_KEY_PATTERNS = [
        # OpenAI API keys (sk-...)
        SAFE_API_KEY_PATTERN,
        # Generic API key patterns (length limited)
        re.compile(
            r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,100})',
            re.IGNORECASE,
        ),
        # Bearer tokens
        SAFE_BEARER_TOKEN_PATTERN,
        # Authorization headers (length limited)
        re.compile(
            r'authorization["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-+=\/]{20,200})',
            re.IGNORECASE,
        ),
        # MCP server URLs with embedded credentials
        SAFE_URL_CREDENTIALS_PATTERN,
    ]

    # Environment variable names that contain sensitive data
    SENSITIVE_ENV_VARS = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "HUGGINGFACE_API_KEY",
        "COHERE_API_KEY",
        "REPLICATE_API_TOKEN",
    }

    @classmethod
    def sanitize_string(
        cls, text: str, replacement: str = "[REDACTED]"
    ) -> str:
        """Sanitize sensitive credentials from a string.

        Args:
            text: Input string that may contain credentials
            replacement: Replacement text for sanitized credentials

        Returns:
            Sanitized string with credentials replaced
        """
        if not text:
            return text

        sanitized = text
        for pattern in cls.API_KEY_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        # Sanitize environment variables
        for env_var in cls.SENSITIVE_ENV_VARS:
            # Pattern: ENV_VAR=value or ENV_VAR: value
            env_pattern = re.compile(
                rf'{env_var}["\']?\s*[:=]\s*["\']?([^\s"\']+)', re.IGNORECASE
            )
            sanitized = env_pattern.sub(f"{env_var}={replacement}", sanitized)

        return sanitized

    @classmethod
    def sanitize_dict(
        cls, data: Dict[str, Any], replacement: str = "[REDACTED]"
    ) -> Dict[str, Any]:
        """Sanitize sensitive credentials from a dictionary.

        Args:
            data: Input dictionary that may contain credentials
            replacement: Replacement text for sanitized credentials

        Returns:
            New dictionary with credentials sanitized
        """
        if not isinstance(data, dict):
            return data

        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            # Sanitize keys that might contain sensitive data
            if any(
                sensitive in key.lower()
                for sensitive in ["key", "token", "password", "secret"]
            ):
                sanitized[key] = replacement
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value, replacement)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, replacement)
            elif isinstance(value, list):
                sanitized_list: list[Any] = []
                for item in value:
                    if isinstance(item, str):
                        sanitized_list.append(
                            cls.sanitize_string(item, replacement)
                        )
                    elif isinstance(item, dict):
                        sanitized_list.append(
                            cls.sanitize_dict(item, replacement)
                        )
                    else:
                        sanitized_list.append(item)
                sanitized[key] = sanitized_list
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def sanitize_exception(
        cls, exception: Exception, replacement: str = "[REDACTED]"
    ) -> str:
        """Sanitize sensitive credentials from exception messages.

        Args:
            exception: Exception that may contain credentials in its message
            replacement: Replacement text for sanitized credentials

        Returns:
            Sanitized exception message
        """
        return cls.sanitize_string(str(exception), replacement)

    @classmethod
    def sanitize_for_logging(
        cls, obj: Any, replacement: str = "[REDACTED]"
    ) -> Any:
        """Sanitize an object for safe logging.

        Args:
            obj: Object to sanitize (string, dict, list, etc.)
            replacement: Replacement text for sanitized credentials

        Returns:
            Sanitized object safe for logging
        """
        if isinstance(obj, str):
            return cls.sanitize_string(obj, replacement)
        elif isinstance(obj, dict):
            return cls.sanitize_dict(obj, replacement)
        elif isinstance(obj, list):
            return [
                cls.sanitize_for_logging(item, replacement) for item in obj
            ]
        else:
            return obj
