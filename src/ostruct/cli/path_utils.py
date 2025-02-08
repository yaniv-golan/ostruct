"""Path validation utilities for the CLI."""

from pathlib import Path
from typing import Optional, Tuple

from ostruct.cli.errors import (
    DirectoryNotFoundError,
    FileNotFoundError,
    VariableNameError,
    VariableValueError,
)
from ostruct.cli.security.errors import PathSecurityError, SecurityErrorReasons
from ostruct.cli.security.security_manager import SecurityManager


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
    # Split into name and path parts
    try:
        name, path_str = mapping.split("=", 1)
    except ValueError:
        raise ValueError(f"Invalid mapping format (missing '='): {mapping}")

    # Validate name
    name = name.strip()
    if not name:
        raise VariableNameError("Variable name cannot be empty")
    if not name.isidentifier():
        raise VariableNameError(f"Invalid variable name: {name}")

    # Normalize path
    path_str = path_str.strip()
    if not path_str:
        raise VariableValueError("Path cannot be empty")

    # Create a Path object
    path = Path(path_str)
    if not path.is_absolute() and base_dir:
        path = Path(base_dir) / path

    # Validate path with security manager if provided
    if security_manager:
        try:
            path = security_manager.validate_path(path)
        except PathSecurityError as e:
            if (
                e.context.get("reason")
                == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
            ):
                raise PathSecurityError(
                    f"Path '{path}' is outside the base directory and not in allowed directories",
                    path=str(path),
                    context=e.context,
                ) from e
            raise PathSecurityError(
                f"Path validation failed: {e}",
                path=str(path),
                context=e.context,
            ) from e

    # Check path existence and type
    if not path.exists():
        if is_dir:
            raise DirectoryNotFoundError(f"Directory not found: {path}")
        raise FileNotFoundError(f"File not found: {path}")

    # Check path type
    if is_dir and not path.is_dir():
        raise DirectoryNotFoundError(
            f"Path exists but is not a directory: {path}"
        )
    elif not is_dir and not path.is_file():
        raise FileNotFoundError(f"Path exists but is not a file: {path}")

    return name, str(path)
