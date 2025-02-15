"""Path validation utilities for the CLI."""

import logging
from pathlib import Path
from typing import Optional, Tuple

from ostruct.cli.errors import (
    DirectoryNotFoundError,
    OstructFileNotFoundError,
    PathSecurityError,
    VariableNameError,
    VariableValueError,
)
from ostruct.cli.security.errors import SecurityErrorReasons
from ostruct.cli.security.security_manager import SecurityManager

logger = logging.getLogger(__name__)


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
    logger.debug(
        "Validating path mapping: %s (is_dir=%s, base_dir=%s)",
        mapping,
        is_dir,
        base_dir,
    )

    # Split into name and path parts
    try:
        name, path_str = mapping.split("=", 1)
    except ValueError:
        logger.error("Invalid mapping format (missing '='): %s", mapping)
        raise ValueError(f"Invalid mapping format (missing '='): {mapping}")

    # Validate name
    name = name.strip()
    if not name:
        logger.error("Variable name cannot be empty: %s", mapping)
        raise VariableNameError("Variable name cannot be empty")
    if not name.isidentifier():
        logger.error("Invalid variable name: %s", name)
        raise VariableNameError(f"Invalid variable name: {name}")

    # Normalize path
    path_str = path_str.strip()
    if not path_str:
        logger.error("Path cannot be empty: %s", mapping)
        raise VariableValueError("Path cannot be empty")

    logger.debug("Creating Path object for: %s", path_str)
    # Create a Path object
    path = Path(path_str)
    if not path.is_absolute() and base_dir:
        logger.debug(
            "Converting relative path to absolute using base_dir: %s", base_dir
        )
        path = Path(base_dir) / path

    # Validate path with security manager if provided
    if security_manager:
        logger.debug("Validating path with security manager: %s", path)
        try:
            path = security_manager.validate_path(path)
            logger.debug("Security validation passed: %s", path)
        except PathSecurityError as e:
            logger.error("Security validation failed: %s - %s", path, e)
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
        logger.error("Path does not exist: %s", path)
        if is_dir:
            raise DirectoryNotFoundError(f"Directory not found: {path}")
        raise OstructFileNotFoundError(f"File not found: {path}")

    # Check path type
    if is_dir and not path.is_dir():
        logger.error("Path exists but is not a directory: %s", path)
        raise DirectoryNotFoundError(
            f"Path exists but is not a directory: {path}"
        )
    elif not is_dir and not path.is_file():
        logger.error("Path exists but is not a file: %s", path)
        raise OstructFileNotFoundError(
            f"Path exists but is not a file: {path}"
        )

    logger.debug("Path validation successful: %s -> %s", name, path)
    return name, str(path)
