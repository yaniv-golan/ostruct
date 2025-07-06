"""Path policy helper for security validation.

This module handles base directory validation logic, making the SecurityManager
stateless with respect to project root. This allows the same security manager
instance to work across different working directories (e.g., when downloads
land under downloads/ even though the current cwd has changed).
"""

import os
from pathlib import Path
from typing import List, Union

from .errors import PathSecurityError
from .normalization import normalize_path


class PathPolicy:
    """Helper class for path validation policies."""

    @staticmethod
    def is_within_allowed_directories(
        path: Union[str, Path], allowed_dirs: List[str]
    ) -> bool:
        """Check if a path is within any of the allowed directories.

        Args:
            path: The path to check
            allowed_dirs: List of allowed directory paths

        Returns:
            True if path is within an allowed directory, False otherwise
        """
        if not allowed_dirs:
            return False

        try:
            normalized_path = normalize_path(path).resolve()

            for allowed_dir in allowed_dirs:
                try:
                    allowed_path = normalize_path(allowed_dir).resolve()
                    if PathPolicy._is_path_under_directory(
                        normalized_path, allowed_path
                    ):
                        return True
                except (PathSecurityError, OSError):
                    # Skip invalid allowed directories
                    continue

        except (PathSecurityError, OSError):
            # If we can't normalize the path, it's not allowed
            pass

        return False

    @staticmethod
    def is_within_base_directory(
        path: Union[str, Path], base_dir: str
    ) -> bool:
        """Check if a path is within the base directory.

        Args:
            path: The path to check
            base_dir: The base directory path

        Returns:
            True if path is within base directory, False otherwise
        """
        try:
            normalized_path = normalize_path(path).resolve()
            base_path = normalize_path(base_dir).resolve()
            return PathPolicy._is_path_under_directory(
                normalized_path, base_path
            )
        except (PathSecurityError, OSError):
            return False

    @staticmethod
    def is_temp_path(path: Union[str, Path]) -> bool:
        """Check if a path is in a temporary directory.

        Args:
            path: The path to check

        Returns:
            True if path is in a temp directory, False otherwise
        """
        try:
            normalized_path = normalize_path(path).resolve()
            temp_dirs = [
                Path("/tmp").resolve(),
                Path("/var/tmp").resolve(),
                Path(os.environ.get("TMPDIR", "/tmp")).resolve(),
                Path(os.path.expanduser("~/tmp")).resolve(),
            ]

            # Add system temp directory
            import tempfile

            temp_dirs.append(Path(tempfile.gettempdir()).resolve())

            for temp_dir in temp_dirs:
                if PathPolicy._is_path_under_directory(
                    normalized_path, temp_dir
                ):
                    return True

        except (PathSecurityError, OSError):
            pass

        return False

    @staticmethod
    def _is_path_under_directory(path: Path, directory: Path) -> bool:
        """Check if a path is under a directory.

        Args:
            path: The normalized path to check
            directory: The normalized directory path

        Returns:
            True if path is under directory, False otherwise
        """
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            return False
