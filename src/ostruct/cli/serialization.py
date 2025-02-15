"""Serialization utilities for CLI logging."""

import json
from typing import Any, Dict


class LogSerializer:
    """Utility class for serializing log data."""

    @staticmethod
    def serialize_log_extra(extra: Dict[str, Any]) -> str:
        """Serialize extra log data to a formatted string.

        Args:
            extra: Dictionary of extra log data

        Returns:
            Formatted string representation of the extra data
        """
        try:
            # Try to serialize with nice formatting
            return json.dumps(extra, indent=2, default=str)
        except Exception:
            # Fall back to basic string representation if JSON fails
            return str(extra)
