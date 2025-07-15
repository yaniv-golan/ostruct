"""Sentinel JSON extraction utility for two-pass Code Interpreter workaround."""

import json
from typing import Any, Dict, Optional

from .safe_regex import (
    SAFE_SENTINEL_PATTERN,
    RegexTimeoutError,
    safe_regex_search,
)

_SENT_RE = SAFE_SENTINEL_PATTERN


def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON block from sentinel markers in text.

    Args:
        text: Response text that may contain sentinel-wrapped JSON

    Returns:
        Parsed JSON dict if found, None otherwise
    """
    try:
        m = safe_regex_search(_SENT_RE, text, timeout=2.0)
        if not m:
            return None

        from .json_limits import parse_json_secure

        result = parse_json_secure(m.group(1))
        # Ensure we return a dict, not other JSON types
        if isinstance(result, dict):
            return result
        return None
    except (RegexTimeoutError, json.JSONDecodeError, ValueError):
        # ValueError includes JSONSizeError, JSONDepthError, JSONComplexityError
        # RegexTimeoutError indicates potential ReDoS attack
        return None
