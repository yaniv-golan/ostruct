"""Allowed directory checker module.

This module provides functionality to verify that a given path is within
one of a set of allowed directories.
"""

import logging
from pathlib import Path
from typing import List, Union

from .normalization import normalize_path

logger = logging.getLogger(__name__)


def is_path_in_allowed_dirs(
    path: Union[str, Path], allowed_dirs: List[Path]
) -> bool:
    """Check if a given path is inside any of the allowed directories.

    This function normalizes both the input path and allowed directories
    before comparison to ensure consistent results across platforms.
    It also handles symlink resolution to ensure that resolved paths
    can be compared correctly with allowed directories.

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

    # Check with normalized paths first
    for allowed in norm_allowed:
        try:
            # If path.relative_to(allowed) does not raise an error,
            # then path is within allowed.
            norm_path.relative_to(allowed)
            return True
        except ValueError:
            continue

    # If normalized comparison failed, try with resolved paths
    # This handles the case where the input path is already resolved (e.g., from validate_file_access)
    # but the allowed directories are not resolved
    try:
        # Check if the input path might already be resolved by comparing it with its own resolution
        path_as_path = Path(path) if isinstance(path, str) else path

        # If the input path is already resolved, resolve allowed dirs to match
        # We determine this by checking if the path starts with common temp resolved prefixes
        path_str = str(path_as_path)
        if path_str.startswith("/var/folders/") or path_str.startswith(
            "/private/"
        ):
            # This looks like an already-resolved path on macOS, resolve allowed dirs
            resolved_allowed = [d.resolve() for d in norm_allowed]
            for allowed in resolved_allowed:
                try:
                    path_as_path.relative_to(allowed)
                    return True
                except ValueError:
                    continue
        else:
            # Try resolving both path and allowed dirs
            resolved_path = norm_path.resolve()
            resolved_allowed = [d.resolve() for d in norm_allowed]
            for allowed in resolved_allowed:
                try:
                    resolved_path.relative_to(allowed)
                    return True
                except ValueError:
                    continue
    except (OSError, RuntimeError):
        # If resolution fails, fall back to normalized comparison result
        pass

    return False
