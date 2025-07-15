"""JSON parsing utilities with DoS protection and size limits."""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default limits for JSON parsing to prevent DoS attacks
DEFAULT_MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_MAX_JSON_DEPTH = 100  # Maximum nesting depth
DEFAULT_MAX_JSON_KEYS = 10000  # Maximum number of keys in any object


class JSONSizeError(ValueError):
    """Raised when JSON exceeds size limits."""

    pass


class JSONDepthError(ValueError):
    """Raised when JSON exceeds depth limits."""

    pass


class JSONComplexityError(ValueError):
    """Raised when JSON exceeds complexity limits."""

    pass


class SecureJSONParser:
    """Secure JSON parser with DoS protection."""

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_JSON_SIZE,
        max_depth: int = DEFAULT_MAX_JSON_DEPTH,
        max_keys: int = DEFAULT_MAX_JSON_KEYS,
    ):
        """Initialize secure JSON parser.

        Args:
            max_size: Maximum JSON string size in bytes
            max_depth: Maximum nesting depth
            max_keys: Maximum number of keys in any object
        """
        self.max_size = max_size
        self.max_depth = max_depth
        self.max_keys = max_keys

    def parse(self, content: str) -> Any:
        """Parse JSON content with security checks.

        Args:
            content: JSON string to parse

        Returns:
            Parsed JSON object

        Raises:
            JSONSizeError: If content exceeds size limits
            JSONDepthError: If content exceeds depth limits
            JSONComplexityError: If content exceeds complexity limits
            json.JSONDecodeError: If JSON is malformed
        """
        # Check size limit first
        if len(content) > self.max_size:
            raise JSONSizeError(
                f"JSON content too large: {len(content)} bytes (max: {self.max_size})"
            )

        # Parse JSON with standard library
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parsing failed: {e}")
            raise

        # Check depth and complexity
        self._validate_structure(parsed, depth=0)

        return parsed

    def _validate_structure(self, obj: Any, depth: int = 0) -> None:
        """Validate JSON structure for depth and complexity.

        Args:
            obj: Object to validate
            depth: Current nesting depth

        Raises:
            JSONDepthError: If depth exceeds limits
            JSONComplexityError: If complexity exceeds limits
        """
        if depth > self.max_depth:
            raise JSONDepthError(
                f"JSON nesting too deep: {depth} levels (max: {self.max_depth})"
            )

        if isinstance(obj, dict):
            if len(obj) > self.max_keys:
                raise JSONComplexityError(
                    f"JSON object has too many keys: {len(obj)} (max: {self.max_keys})"
                )
            for value in obj.values():
                self._validate_structure(value, depth + 1)
        elif isinstance(obj, list):
            if len(obj) > self.max_keys:  # Reuse max_keys for array length
                raise JSONComplexityError(
                    f"JSON array too long: {len(obj)} items (max: {self.max_keys})"
                )
            for item in obj:
                self._validate_structure(item, depth + 1)


# Global parser instance with default limits
_default_parser = SecureJSONParser()


def parse_json_secure(
    content: str,
    max_size: Optional[int] = None,
    max_depth: Optional[int] = None,
    max_keys: Optional[int] = None,
) -> Any:
    """Parse JSON content with security checks.

    Args:
        content: JSON string to parse
        max_size: Maximum JSON string size in bytes (None for default)
        max_depth: Maximum nesting depth (None for default)
        max_keys: Maximum number of keys in any object (None for default)

    Returns:
        Parsed JSON object

    Raises:
        JSONSizeError: If content exceeds size limits
        JSONDepthError: If content exceeds depth limits
        JSONComplexityError: If content exceeds complexity limits
        json.JSONDecodeError: If JSON is malformed
    """
    if max_size is None and max_depth is None and max_keys is None:
        # Use default parser for efficiency
        return _default_parser.parse(content)

    # Create custom parser with specified limits
    parser = SecureJSONParser(
        max_size=max_size or DEFAULT_MAX_JSON_SIZE,
        max_depth=max_depth or DEFAULT_MAX_JSON_DEPTH,
        max_keys=max_keys or DEFAULT_MAX_JSON_KEYS,
    )
    return parser.parse(content)


def get_json_size_limit() -> int:
    """Get the current JSON size limit.

    Returns:
        Current JSON size limit in bytes
    """
    return _default_parser.max_size


def set_json_size_limit(max_size: int) -> None:
    """Set the global JSON size limit.

    Args:
        max_size: New maximum JSON size in bytes
    """
    global _default_parser
    _default_parser = SecureJSONParser(
        max_size=max_size,
        max_depth=_default_parser.max_depth,
        max_keys=_default_parser.max_keys,
    )
