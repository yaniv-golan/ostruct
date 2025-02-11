"""Security manager module.

This module provides a high-level SecurityManager class that uses the other modules to:
- Normalize paths
- Safely join paths
- Validate that paths are within allowed directories
- Resolve symlinks securely with depth and loop checking
- Manage case differences on case-insensitive systems
"""

import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Union

from .allowed_checker import is_path_in_allowed_dirs
from .case_manager import CaseManager
from .errors import (
    DirectoryNotFoundError,
    PathSecurityError,
    SecurityErrorReasons,
)
from .normalization import normalize_path
from .symlink_resolver import _resolve_symlink

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages security for file access.

    Validates all file access against a base directory and optional
    allowed directories. Prevents unauthorized access and directory
    traversal attacks.

    The security model is based on:
    1. A base directory that serves as the root for all file operations
    2. A set of explicitly allowed directories that can be accessed outside the base directory
    3. Special handling for temporary directories that are always allowed
    4. Case-sensitive or case-insensitive path handling based on platform

    Example:
        >>> sm = SecurityManager("/base/dir")
        >>> sm.add_allowed_directory("/tmp")
        >>> sm.validate_path("/base/dir/file.txt")  # OK
        >>> sm.validate_path("/etc/passwd")  # Raises PathSecurityError
    """

    MAX_SYMLINK_DEPTH = 16

    def __init__(
        self,
        base_dir: Union[str, Path],
        allowed_dirs: Optional[List[Union[str, Path]]] = None,
        allow_temp_paths: bool = False,
        max_symlink_depth: int = MAX_SYMLINK_DEPTH,
    ):
        """Initialize the SecurityManager.

        Args:
            base_dir: The root directory for file operations.
            allowed_dirs: Additional directories allowed for access.
            allow_temp_paths: Whether to allow temporary directory paths.
            max_symlink_depth: Maximum depth for symlink resolution.

        Raises:
            DirectoryNotFoundError: If base_dir or any allowed directory doesn't exist.
        """
        # Normalize and verify base directory
        self._base_dir = normalize_path(base_dir)
        if not self._base_dir.is_dir():
            raise DirectoryNotFoundError(
                f"Base directory not found: {base_dir}",
                path=str(base_dir),
            )

        # Initialize allowed directories with the base directory
        self._allowed_dirs: List[Path] = [self._base_dir]
        if allowed_dirs:
            for d in allowed_dirs:
                self.add_allowed_directory(d)

        self._allow_temp_paths = allow_temp_paths
        self._max_symlink_depth = max_symlink_depth
        self._temp_dir = (
            normalize_path(tempfile.gettempdir()) if allow_temp_paths else None
        )

        logger.debug(
            "\n=== Initialized SecurityManager ===\n"
            "Base dir: %s\n"
            "Allowed dirs: %s\n"
            "Allow temp: %s\n"
            "Temp dir: %s\n"
            "Max symlink depth: %d",
            self._base_dir,
            self._allowed_dirs,
            self._allow_temp_paths,
            self._temp_dir,
            self._max_symlink_depth,
        )

    @property
    def base_dir(self) -> Path:
        """Return the base directory."""
        return self._base_dir

    @property
    def allowed_dirs(self) -> List[Path]:
        """Return the list of allowed directories."""
        return self._allowed_dirs.copy()

    def add_allowed_directory(self, directory: Union[str, Path]) -> None:
        """Add a new directory to the allowed directories list.

        Args:
            directory: The directory to add.

        Raises:
            DirectoryNotFoundError: If the directory doesn't exist.
        """
        norm_dir = normalize_path(directory)
        if not norm_dir.is_dir():
            raise DirectoryNotFoundError(
                f"Allowed directory not found: {directory}",
                path=str(directory),
            )
        if norm_dir not in self._allowed_dirs:
            self._allowed_dirs.append(norm_dir)

    def is_temp_path(self, path: Union[str, Path]) -> bool:
        """Check if a path is in the system's temporary directory.

        Args:
            path: The path to check.

        Returns:
            True if the path is a temporary path; False otherwise.

        Raises:
            PathSecurityError: If there's an error checking the path.
        """
        if not self._allow_temp_paths or not self._temp_dir:
            return False

        try:
            # Use string-based comparison instead of resolving
            norm_path = normalize_path(path)
            temp_path_str = str(self._temp_dir)
            norm_path_str = str(norm_path)
            return norm_path_str.startswith(temp_path_str)
        except Exception as e:
            raise PathSecurityError(
                f"Error checking temporary path: {e}",
                path=str(path),
            ) from e

    def is_path_allowed(self, path: Union[str, Path]) -> bool:
        """Check if a path is allowed based on security rules.

        Args:
            path: The path to check.

        Returns:
            True if the path is allowed; False otherwise.
        """
        try:
            norm_path = normalize_path(path)
        except PathSecurityError:
            return False

        # Check if the path is within one of the allowed directories
        if is_path_in_allowed_dirs(norm_path, self._allowed_dirs):
            return True

        # Allow temp paths if configured
        if self._allow_temp_paths and self.is_temp_path(norm_path):
            return True

        return False

    def validate_path(self, path: Union[str, Path]) -> Path:
        """Validate a path against security rules.

        This method:
        1. Checks if it's a symlink first
        2. Normalizes the input
        3. Validates against security rules
        4. Checks existence (only after security validation)

        Args:
            path: The path to validate.

        Returns:
            A validated and resolved Path object.

        Raises:
            PathSecurityError: If the path fails security validation
            FileNotFoundError: If the file doesn't exist (only checked after security validation)
        """
        # First normalize the path
        norm_path = normalize_path(path)

        # Handle symlinks first - delegate to symlink_resolver
        if norm_path.is_symlink():
            try:
                return _resolve_symlink(
                    norm_path,
                    self._max_symlink_depth,
                    self._allowed_dirs,
                )
            except RuntimeError as e:
                if "Symlink loop" in str(e):
                    raise PathSecurityError(
                        "Symlink security violation: loop detected",
                        path=str(path),
                        context={"reason": SecurityErrorReasons.SYMLINK_LOOP},
                    ) from e
                raise PathSecurityError(
                    f"Symlink security violation: failed to resolve symlink - {e}",
                    path=str(path),
                    context={"reason": SecurityErrorReasons.SYMLINK_ERROR},
                ) from e

        # For non-symlinks, just check if the normalized path is allowed
        if not self.is_path_allowed(norm_path):
            logger.error(
                "Security violation: Path %s is outside allowed directories",
                path,
            )
            raise PathSecurityError(
                (
                    f"Access denied: {os.path.basename(str(path))} is outside "
                    "base directory and not in allowed directories"
                ),
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.PATH_OUTSIDE_ALLOWED,
                    "base_dir": str(self._base_dir),
                    "allowed_dirs": [str(d) for d in self._allowed_dirs],
                },
            )

        # Only check existence after security validation passes
        if not norm_path.exists():
            logger.debug("Path allowed but not found: %s", norm_path)
            raise FileNotFoundError(
                f"File not found: {os.path.basename(str(path))}"
            )

        return norm_path

    def resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve a path with security checks.

        This method maintains backward compatibility by translating
        internal security errors to standard filesystem errors where appropriate.

        Args:
            path: Path to resolve

        Returns:
            Resolved Path object

        Raises:
            FileNotFoundError: If path doesn't exist or is a broken symlink
            PathSecurityError: For other security violations
        """
        try:
            norm_path = normalize_path(path)

            # Early return for allowed temp paths
            if self._allow_temp_paths and self.is_temp_path(norm_path):
                logger.debug("Allowing temp path: %s", norm_path)
                if not norm_path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                return norm_path

            # Handle symlinks with security checks
            if norm_path.is_symlink():
                try:
                    return _resolve_symlink(
                        norm_path, self._max_symlink_depth, self._allowed_dirs
                    )
                except PathSecurityError as e:
                    reason = e.context.get("reason")
                    # First check for loop errors (highest precedence)
                    if reason == SecurityErrorReasons.SYMLINK_LOOP:
                        raise  # Propagate loop errors unchanged
                    # Then check for max depth errors
                    elif reason == SecurityErrorReasons.SYMLINK_MAX_DEPTH:
                        raise  # Propagate max depth errors unchanged
                    # Finally handle broken links (lowest precedence)
                    elif reason == SecurityErrorReasons.SYMLINK_BROKEN:
                        msg = f"Broken symlink: {e.context['source']} -> {e.context['target']}"
                        logger.debug(msg)
                        raise FileNotFoundError(msg) from e
                    # Any other security errors propagate unchanged
                    raise

            # For non-symlinks, check if the normalized path is allowed
            if not self.is_path_allowed(norm_path):
                logger.error(
                    "Security violation: Path %s is outside allowed directories",
                    path,
                )
                raise PathSecurityError(
                    f"Access denied: {os.path.basename(str(path))} is outside base directory",
                    path=str(path),
                    context={
                        "reason": SecurityErrorReasons.PATH_OUTSIDE_ALLOWED,
                        "base_dir": str(self._base_dir),
                        "allowed_dirs": [str(d) for d in self._allowed_dirs],
                    },
                )

            # Only check existence after security validation
            if not norm_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            return norm_path

        except OSError as e:
            if isinstance(e, FileNotFoundError):
                raise
            logger.error("Error resolving path: %s - %s", path, e)
            raise PathSecurityError(
                f"Failed to resolve path: {e}",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.SYMLINK_ERROR,
                    "error": str(e),
                },
            ) from e

    @contextmanager
    def symlink_context(self) -> Generator[None, None, None]:
        """Context manager for symlink resolution.

        This context manager ensures that symlink resolution state is properly
        cleaned up, even if an error occurs during resolution.

        Example:
            >>> with security_manager.symlink_context():
            ...     resolved = security_manager.resolve_path("/path/to/symlink")
        """
        try:
            yield
        finally:
            # Clean up any case mappings that were created during symlink resolution
            CaseManager.clear()
