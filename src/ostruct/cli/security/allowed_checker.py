"""Allowed directory checker module.

This module provides functionality to verify that a given path is within
one of a set of allowed directories.
"""

from pathlib import Path
from typing import List, Union

from .normalization import normalize_path


def is_path_in_allowed_dirs(
    path: Union[str, Path], allowed_dirs: List[Path]
) -> bool:
    """Check if a given path is inside any of the allowed directories.

    This function normalizes both the input path and allowed directories
    before comparison to ensure consistent results across platforms.

    Args:
        path: The path to check.
        allowed_dirs: A list of allowed directory paths.

    Returns:
        True if path is within one of the allowed directories; False otherwise.

    Raises:
        TypeError: If path is None or not a string/Path object.

    Example:
        >>> allowed = [Path("/base"), Path("/tmp")]
        >>> is_path_in_allowed_dirs("/base/file.txt", allowed)
        True
        >>> is_path_in_allowed_dirs("/etc/passwd", allowed)
        False
    """
    if path is None:
        raise TypeError("path must be a string or Path object")
    if not isinstance(path, (str, Path)):
        raise TypeError("path must be a string or Path object")

    norm_path = normalize_path(path)
    norm_allowed = [normalize_path(d) for d in allowed_dirs]

    for allowed in norm_allowed:
        try:
            # If path.relative_to(allowed) does not raise an error,
            # then path is within allowed.
            norm_path.relative_to(allowed)
            return True
        except ValueError:
            continue

    return False
