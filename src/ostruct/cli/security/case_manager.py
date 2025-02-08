"""Case management module.

This module provides a class for tracking and preserving the original case
of file paths on case-insensitive systems.
"""

from pathlib import Path
from threading import Lock
from typing import Dict


class CaseManager:
    """Manages original case preservation for paths.

    This class provides a thread-safe way to track original case preservation
    without modifying Path objects. This is particularly important on
    case-insensitive systems (macOS, Windows) where we normalize paths
    to lowercase but want to preserve the original case for display.

    Example:
        >>> CaseManager.set_original_case(Path("/tmp/file.txt"), "/TMP/File.txt")
        >>> CaseManager.get_original_case(Path("/tmp/file.txt"))
        '/TMP/File.txt'
    """

    _case_mapping: Dict[str, str] = {}
    _lock = Lock()

    @classmethod
    def set_original_case(
        cls, normalized_path: Path, original_case: str
    ) -> None:
        """Store the original case for a normalized path.

        Args:
            normalized_path: The normalized (potentially lowercased) Path.
            original_case: The original path string with its original case.

        Raises:
            TypeError: If normalized_path or original_case is None.
        """
        if normalized_path is None:
            raise TypeError("normalized_path cannot be None")
        if original_case is None:
            raise TypeError("original_case cannot be None")

        with cls._lock:
            cls._case_mapping[str(normalized_path)] = original_case

    @classmethod
    def get_original_case(cls, normalized_path: Path) -> str:
        """Retrieve the original case for a normalized path.

        Args:
            normalized_path: The normalized Path.

        Returns:
            The original case string if stored; otherwise the normalized path string.

        Raises:
            TypeError: If normalized_path is None.
        """
        if normalized_path is None:
            raise TypeError("normalized_path cannot be None")

        with cls._lock:
            return cls._case_mapping.get(
                str(normalized_path), str(normalized_path)
            )

    @classmethod
    def clear(cls) -> None:
        """Clear all stored case mappings."""
        with cls._lock:
            cls._case_mapping.clear()
