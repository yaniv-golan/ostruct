"""Path validation utilities for the CLI."""

import os
from pathlib import Path
from typing import Optional, Tuple

from .errors import (
    DirectoryNotFoundError,
    FileNotFoundError,
    PathSecurityError,
    VariableNameError,
    VariableValueError,
)
from .security import SecurityManager


def validate_path_mapping(
    mapping: str,
    is_dir: bool = False,
    base_dir: Optional[str] = None,
    security_manager: Optional[SecurityManager] = None,
) -> Tuple[str, str]:
    """Validate a path mapping in the format "name=path".

    Args:
        mapping: The path mapping string (e.g., "myvar=/path/to/file").
        is_dir: Whether the path is expected to be a directory (True) or file (False).
        base_dir: Optional base directory to resolve relative paths against.
        security_manager: Optional security manager to validate paths.

    Returns:
        A (name, path) tuple.

    Raises:
        VariableNameError: If the variable name portion is empty or invalid.
        DirectoryNotFoundError: If is_dir=True and the path is not a directory or doesn't exist.
        FileNotFoundError: If is_dir=False and the path is not a file or doesn't exist.
        PathSecurityError: If the path is inaccessible or outside the allowed directory.
        ValueError: If the format is invalid (missing "=").
        OSError: If there is an underlying OS error (permissions, etc.).

    Example:
        >>> validate_path_mapping("config=settings.txt")  # Validates file
        ('config', 'settings.txt')
        >>> validate_path_mapping("data=config/", is_dir=True)  # Validates directory
        ('data', 'config/')
    """
    try:
        if not mapping or "=" not in mapping:
            raise ValueError("Invalid mapping format")

        name, path = mapping.split("=", 1)
        if not name:
            raise VariableNameError(
                f"Empty name in {'directory' if is_dir else 'file'} mapping"
            )

        if not path:
            raise VariableValueError("Path cannot be empty")

        # Expand user home directory and environment variables
        path = os.path.expanduser(os.path.expandvars(path))

        # Convert to Path object and resolve against base_dir if provided
        path_obj = Path(path)
        if base_dir:
            path_obj = Path(base_dir) / path_obj

        # Resolve the path to catch directory traversal attempts
        try:
            resolved_path = path_obj.resolve()
        except OSError as e:
            raise OSError(f"Failed to resolve path: {e}")

        # Check if path exists
        if not resolved_path.exists():
            if is_dir:
                raise DirectoryNotFoundError(f"Directory not found: {path!r}")
            else:
                raise FileNotFoundError(f"File not found: {path!r}")

        # Check if path is correct type
        if is_dir and not resolved_path.is_dir():
            raise DirectoryNotFoundError(f"Path is not a directory: {path!r}")
        elif not is_dir and not resolved_path.is_file():
            raise FileNotFoundError(f"Path is not a file: {path!r}")

        # Check if path is accessible
        try:
            if is_dir:
                os.listdir(str(resolved_path))
            else:
                with open(str(resolved_path), "r", encoding="utf-8") as f:
                    f.read(1)
        except OSError as e:
            if e.errno == 13:  # Permission denied
                raise PathSecurityError(
                    f"Permission denied accessing path: {path!r}"
                )
            raise

        # Check security constraints
        if security_manager:
            if not security_manager.is_path_allowed(str(resolved_path)):
                raise PathSecurityError.from_expanded_paths(
                    original_path=str(path),
                    expanded_path=str(resolved_path),
                    base_dir=str(security_manager.base_dir),
                    allowed_dirs=[
                        str(d) for d in security_manager.allowed_dirs
                    ],
                )

        # Return the original path to maintain relative paths in the output
        return name, path

    except ValueError as e:
        if "not enough values to unpack" in str(e):
            raise VariableValueError(
                f"Invalid {'directory' if is_dir else 'file'} mapping "
                f"(expected name=path format): {mapping!r}"
            )
        raise
