"""Sentinel JSON extraction utility for two-pass Code Interpreter workaround."""

import json
import re
from typing import Any, Dict, Optional

_SENT_RE = re.compile(r"===BEGIN_JSON===\s*(\{.*?})\s*===END_JSON===", re.S)


def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON block from sentinel markers in text.

    Args:
        text: Response text that may contain sentinel-wrapped JSON

    Returns:
        Parsed JSON dict if found, None otherwise
    """
    m = _SENT_RE.search(text)
    if not m:
        return None
    try:
        result = json.loads(m.group(1))
        # Ensure we return a dict, not other JSON types
        if isinstance(result, dict):
            return result
        return None
    except json.JSONDecodeError:
        return None
