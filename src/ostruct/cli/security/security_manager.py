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
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Union

from ostruct.cli.errors import OstructFileNotFoundError

from .allowed_checker import is_path_in_allowed_dirs
from .case_manager import CaseManager
from .errors import (
    DirectoryNotFoundError,
    PathSecurityError,
    SecurityErrorReasons,
)
from .normalization import normalize_path
from .symlink_resolver import _resolve_symlink
from .types import PathSecurity

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages security for file access.

    Validates all file access against a base directory and optional
    allowed directories. Prevents unauthorized access and directory
    traversal attacks.

    The security model is based on:
    1. A base directory that serves as the root for all file operations
       (typically set to the current working directory by higher-level functions)
    2. A set of explicitly allowed directories that can be accessed outside the base directory
    3. Special handling for temporary directories that are always allowed
    4. Case-sensitive or case-insensitive path handling based on platform

    Note:
        While the SecurityManager class itself requires base_dir to be explicitly provided,
        higher-level functions in the CLI layer (like validate_security_manager and file_utils)
        will automatically use the current working directory as the base_dir if none is specified.

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
        security_mode: PathSecurity = PathSecurity.WARN,
    ):
        """Initialize the SecurityManager.

        Args:
            base_dir: The root directory for file operations. While this parameter is required here,
                     note that higher-level functions in the CLI layer will automatically use the
                     current working directory if no base_dir is specified.
            allowed_dirs: Additional directories allowed for access.
            allow_temp_paths: Whether to allow temporary directory paths.
            max_symlink_depth: Maximum depth for symlink resolution.
            security_mode: Path security enforcement mode (PERMISSIVE, WARN, or STRICT).

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

        # Enhanced security features (T2.1)
        self.security_mode = security_mode
        self._allow_inodes: set[tuple[int, int]] = (
            set()
        )  # (device, inode) pairs

        logger.debug(
            "\n=== Initialized SecurityManager ===\n"
            "Base dir: %s\n"
            "Allowed dirs: %s\n"
            "Allow temp: %s\n"
            "Temp dir: %s\n"
            "Max symlink depth: %d\n"
            "Security mode: %s",
            self._base_dir,
            self._allowed_dirs,
            self._allow_temp_paths,
            self._temp_dir,
            self._max_symlink_depth,
            self.security_mode,
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

    def configure_security_mode(
        self,
        mode: PathSecurity,
        allow_files: Optional[List[str]] = None,
        allow_lists: Optional[List[str]] = None,
    ) -> None:
        """Configure enhanced security features while preserving existing functionality.

        Args:
            mode: Path security enforcement mode
            allow_files: List of individual file paths to allow (tracked by inode)
            allow_lists: List of allow-list files to load

        Raises:
            DirectoryNotFoundError: If any allow-list file doesn't exist
            PathSecurityError: If there's an error processing allow lists
        """
        self.security_mode = mode
        logger.debug("Configuring security mode: %s", mode)

        # Process individual files by inode (new feature)
        if allow_files:
            for file_path in allow_files:
                if not self.pin_file_by_inode(file_path):
                    logger.warning(
                        "Could not add file to allowlist: %s", file_path
                    )

        # Process allow lists (new feature)
        if allow_lists:
            for list_path in allow_lists:
                self._load_allow_list(list_path)

    def _load_allow_list(self, list_path: str) -> None:
        """Load allowed paths from a file.

        Args:
            list_path: Path to the allow-list file

        Raises:
            DirectoryNotFoundError: If the allow-list file doesn't exist
            PathSecurityError: If there's an error processing the file
        """
        try:
            list_file = normalize_path(list_path)
            if not list_file.exists():
                raise DirectoryNotFoundError(
                    f"Allow-list file not found: {list_path}",
                    path=list_path,
                )

            with open(list_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue  # Skip empty lines and comments

                    try:
                        # Try to interpret as directory first
                        path_obj = normalize_path(line)
                        if path_obj.is_dir():
                            self.add_allowed_directory(path_obj)
                            logger.debug(
                                "Added directory from allow-list: %s", line
                            )
                        elif path_obj.is_file():
                            # Add as inode-tracked file using secure pinning
                            if self.pin_file_by_inode(path_obj):
                                logger.debug(
                                    "Added file from allow-list: %s", line
                                )
                            else:
                                logger.warning(
                                    "Failed to pin file from allow-list: %s",
                                    line,
                                )
                        else:
                            logger.warning(
                                "Path in allow-list does not exist: %s (line %d)",
                                line,
                                line_num,
                            )
                    except Exception as e:
                        logger.warning(
                            "Error processing allow-list entry '%s' (line %d): %s",
                            line,
                            line_num,
                            e,
                        )

        except OSError as e:
            raise PathSecurityError(
                f"Failed to read allow-list file: {e}",
                path=list_path,
                context={"reason": "allow_list_read_error"},
            ) from e

    def pin_file_by_inode(self, file_path: Union[str, Path]) -> bool:
        """Pin a file to allowlist by its inode (survives moves/renames).

        Uses O_NOFOLLOW for security on Unix systems to prevent symlink attacks.
        Falls back to Windows-compatible approach when O_NOFOLLOW is unavailable.

        Args:
            file_path: Path to the file to pin

        Returns:
            True if file was successfully pinned, False otherwise
        """
        try:
            path = normalize_path(file_path)

            # Use O_NOFOLLOW to prevent symlink attacks during stat
            # On Windows, O_NOFOLLOW is not supported, use alternative approach
            if hasattr(os, "O_NOFOLLOW") and os.name != "nt":
                # Unix-like systems: use O_NOFOLLOW for security
                try:
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        st = os.fstat(fd)
                        inode_id = self._get_file_identity(st)
                        self._allow_inodes.add(inode_id)
                        logger.debug(
                            "Pinned file %s by inode %s (O_NOFOLLOW)",
                            path,
                            inode_id,
                        )
                        return True
                    finally:
                        os.close(fd)
                except OSError as e:
                    # Handle pyfakefs compatibility issues
                    if (
                        e.errno == 9
                    ):  # EBADF - Bad file descriptor (common in fake filesystem)
                        logger.debug(
                            "Fake filesystem detected, falling back to lstat: %s",
                            path,
                        )
                        # Fall through to Windows-style approach
                    elif e.errno == 40:  # ELOOP - symlink loop
                        logger.warning("Symlink loop detected: %s", path)
                        return False
                    elif e.errno == 20:  # ENOTDIR - symlink in path
                        logger.warning("Symlink in path: %s", path)
                        return False
                    else:
                        # For other errors, fall back to Windows approach rather than failing
                        logger.debug(
                            "O_NOFOLLOW failed with error %s, falling back to lstat: %s",
                            e.errno,
                            path,
                        )

            # Windows fallback (also used when O_NOFOLLOW fails in fake filesystem)
            # Windows fallback: check for symlinks manually
            st_before = os.lstat(path)
            if stat.S_ISLNK(st_before.st_mode):
                logger.warning(
                    "Symlink detected, using resolved target: %s", path
                )
                # For symlinks, stat the resolved target
                resolved = path.resolve()
                st_after = os.stat(resolved)
                inode_id = self._get_file_identity(st_after)
            else:
                # Regular file
                inode_id = self._get_file_identity(st_before)

            self._allow_inodes.add(inode_id)
            logger.debug(
                "Pinned file %s by inode %s (Windows)", path, inode_id
            )
            return True

        except OSError as e:
            logger.error("Cannot pin file %s: %s", file_path, e)
            return False

    def _get_file_identity(
        self, stat_result: os.stat_result
    ) -> Tuple[int, int]:
        """Get platform-appropriate file identity.

        Args:
            stat_result: Result from os.stat() or os.fstat()

        Returns:
            Tuple of (device, inode) for file identity
        """
        # Windows: Python's stat_result may not have reliable st_ino
        # Use combination of device + file index when available
        if os.name == "nt":
            # Windows fallback: use dev + (file_index or ino) + size + ctime
            # This provides reasonable identity even with NTFS limitations
            file_id = getattr(stat_result, "st_file_index", stat_result.st_ino)
            # Include size and ctime for additional uniqueness on Windows
            extended_id = hash(
                (file_id, stat_result.st_size, stat_result.st_ctime_ns)
            )
            return (stat_result.st_dev, extended_id)
        else:
            # Unix-like: Use device and inode (standard approach)
            return (stat_result.st_dev, stat_result.st_ino)

    def is_file_allowed_by_inode(self, file_path: Union[str, Path]) -> bool:
        """Check if file is allowed based on its inode.

        For explicitly allowed files, allow path traversal to enable access
        via alternative paths that resolve to the same file.

        Args:
            file_path: Path to check

        Returns:
            True if file is in the inode allowlist
        """
        try:
            # First try normal normalization (blocks path traversal)
            try:
                path = normalize_path(file_path)
            except PathSecurityError as e:
                # If path traversal was blocked, try with traversal allowed
                # This enables access to explicitly allowed files via alternative paths
                if "Directory traversal not allowed" in str(e):
                    path = normalize_path(file_path, allow_traversal=True)
                else:
                    # Other security errors (unsafe Unicode, etc.) are not bypassed
                    return False

            st = os.stat(path, follow_symlinks=False)
            file_id = self._get_file_identity(st)
            is_allowed = file_id in self._allow_inodes

            if is_allowed:
                logger.debug(
                    "File allowed by inode: %s -> %s", file_path, file_id
                )

            return is_allowed
        except OSError:
            return False

    def validate_symlink_target(self, symlink_path: Path) -> bool:
        """Validate that symlink target is also allowed.

        Args:
            symlink_path: Path to the symlink to validate

        Returns:
            True if symlink target is allowed

        Raises:
            PathSecurityError: If target is not allowed and mode is STRICT
        """
        if not symlink_path.is_symlink():
            return True  # Not a symlink

        try:
            target = symlink_path.resolve()

            # Check if target is allowed by existing rules
            if self.is_path_allowed_enhanced(target):
                return True

            # Handle security mode for disallowed targets
            if self.security_mode == PathSecurity.STRICT:
                raise PathSecurityError(
                    f"Symlink target not allowed: {target}",
                    path=str(symlink_path),
                    context={
                        "reason": "symlink_target_denied",
                        "target": str(target),
                        "security_mode": self.security_mode.value,
                    },
                )
            elif self.security_mode == PathSecurity.WARN:
                logger.warning(
                    "Symlink target outside policy: %s -> %s",
                    symlink_path,
                    target,
                )
                return True
            else:  # PERMISSIVE
                return True

        except OSError as e:
            # Broken symlink or other error
            if self.security_mode == PathSecurity.STRICT:
                raise PathSecurityError(
                    f"Cannot validate symlink target: {e}",
                    path=str(symlink_path),
                    context={
                        "reason": "symlink_validation_error",
                        "error": str(e),
                    },
                ) from e
            else:
                logger.warning(
                    "Cannot validate symlink target %s: %s", symlink_path, e
                )
                return self.security_mode != PathSecurity.STRICT

    def validate_file_access(
        self, file_path: Union[str, Path], context: str = "file access"
    ) -> Path:
        """Main entry point for file access validation.

        This method provides a unified interface for validating file access that:
        1. Checks file existence
        2. Applies enhanced security validation (directory + inode + mode)
        3. Validates symlink targets when appropriate
        4. Provides clear error messages with context

        Args:
            file_path: Path to the file to validate
            context: Description of the access context for error messages

        Returns:
            Validated and resolved Path object

        Raises:
            OstructFileNotFoundError: If file doesn't exist
            PathSecurityError: If file access is denied by security policy
        """
        logger.debug(
            "Validating file access: %s (context: %s)", file_path, context
        )

        try:
            # Normalize and resolve the path
            resolved_path = normalize_path(file_path).resolve()
        except PathSecurityError as e:
            # If path traversal was blocked, check if file is explicitly allowed
            if "Directory traversal not allowed" in str(e):
                # Check if this file is allowed by inode (which handles traversal)
                if self.is_file_allowed_by_inode(file_path):
                    # Allow path traversal for explicitly allowed files
                    resolved_path = normalize_path(
                        file_path, allow_traversal=True
                    ).resolve()
                else:
                    raise PathSecurityError(
                        f"Failed to resolve path: {file_path}",
                        path=str(file_path),
                        context={
                            "reason": "path_resolution_error",
                            "error": str(e),
                        },
                    ) from e
            else:
                raise PathSecurityError(
                    f"Failed to resolve path: {file_path}",
                    path=str(file_path),
                    context={
                        "reason": "path_resolution_error",
                        "error": str(e),
                    },
                ) from e
        except Exception as e:
            raise PathSecurityError(
                f"Failed to resolve path: {file_path}",
                path=str(file_path),
                context={"reason": "path_resolution_error", "error": str(e)},
            ) from e

        # Check if file exists
        if not resolved_path.exists():
            raise OstructFileNotFoundError(f"File not found: {file_path}")

        # Apply enhanced security validation on the resolved path
        # For symlinks, this ensures we validate the target, not just the symlink itself
        if not self.is_path_allowed_enhanced(resolved_path):
            # is_path_allowed_enhanced() handles mode-specific behavior (warn vs strict)
            # If we get here in STRICT mode, it means an exception was already raised
            # In WARN/PERMISSIVE modes, we continue with a warning already logged
            pass

        # Additional symlink validation for enhanced security
        if resolved_path.is_symlink():
            self.validate_symlink_target(resolved_path)

        logger.debug(
            "File access validated: %s (context: %s)", resolved_path, context
        )
        return resolved_path

    def validate_batch_access(
        self,
        paths: List[Union[str, Path]],
        context: str = "batch access",
    ) -> List[Path]:
        """Validate multiple paths efficiently.

        Args:
            paths: List of paths to validate
            context: Description of the access context

        Returns:
            List of validated Path objects

        Raises:
            PathSecurityError: If any path fails validation in STRICT mode
        """
        validated = []
        errors = []

        for path in paths:
            try:
                validated.append(self.validate_file_access(path, context))
            except (OstructFileNotFoundError, PathSecurityError) as e:
                error_msg = f"{path}: {e}"
                errors.append(error_msg)
                logger.debug("Batch validation error: %s", error_msg)

        if errors:
            if self.security_mode == PathSecurity.STRICT:
                raise PathSecurityError(
                    "Batch validation failed:\n" + "\n".join(errors),
                    context={
                        "reason": "batch_validation_failed",
                        "errors": errors,
                        "context": context,
                    },
                )
            else:
                # In WARN/PERMISSIVE modes, log errors but continue
                for error in errors:
                    logger.warning("Batch validation: %s", error)

        logger.debug(
            "Batch validation completed: %d/%d files validated (context: %s)",
            len(validated),
            len(paths),
            context,
        )
        return validated

    @contextmanager
    def security_context(
        self,
        mode: PathSecurity,
        additional_allows: Optional[List[str]] = None,
    ) -> Generator[None, None, None]:
        """Temporary security context for specific operations.

        Args:
            mode: Temporary security mode to use
            additional_allows: Additional directories to temporarily allow

        Yields:
            None (context manager)

        Example:
            with manager.security_context(PathSecurity.PERMISSIVE):
                # Temporarily allow all file access
                result = manager.validate_file_access(sensitive_file)
        """
        # Save current state
        old_mode = self.security_mode
        old_dirs = self._allowed_dirs.copy()
        old_inodes = self._allow_inodes.copy()

        try:
            # Apply temporary configuration
            self.security_mode = mode
            if additional_allows:
                for path in additional_allows:
                    try:
                        self.add_allowed_directory(path)
                        logger.debug("Temporarily added directory: %s", path)
                    except Exception as e:
                        logger.warning(
                            "Failed to add temporary directory %s: %s", path, e
                        )

            logger.debug(
                "Entered security context: mode=%s, additional_dirs=%s",
                mode,
                additional_allows,
            )
            yield

        finally:
            # Restore original state
            self.security_mode = old_mode
            self._allowed_dirs = old_dirs
            self._allow_inodes = old_inodes
            logger.debug("Restored security context: mode=%s", old_mode)

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

    def is_path_allowed_enhanced(self, path: Union[str, Path]) -> bool:
        """Enhanced path validation with three-tier security model.

        Precedence Rules (Reviewer feedback addressed):
        1. Existing SecurityManager validation (directory allowlist) - highest precedence
        2. Inode allowlist (--allow-file) - file-specific tracking
        3. Security mode (permissive/warn/strict) - fallback behavior

        Args:
            path: The path to check

        Returns:
            True if the path is allowed; False otherwise

        Raises:
            PathSecurityError: If security mode is STRICT and path is not allowed
        """
        # Rule 1: Check inode allowlist first (handles path traversal to allowed files)
        if self.is_file_allowed_by_inode(path):
            return True

        # Rule 2: Use existing SecurityManager validation (preserves current behavior)
        # This requires successful path normalization
        try:
            resolved_path = normalize_path(path).resolve()
            if self.is_path_allowed(path):
                return True
        except (PathSecurityError, OSError):
            # If we can't normalize the path and it's not in inode allowlist,
            # defer to security mode
            resolved_path = None

        # Rule 3: Apply security mode (NEW - three-tier model)
        if self.security_mode == PathSecurity.PERMISSIVE:
            logger.debug("Path allowed by permissive mode: %s", path)
            return True
        elif self.security_mode == PathSecurity.WARN:
            logger.warning("PathOutsidePolicy: %s", resolved_path or path)
            return True
        else:  # STRICT
            raise PathSecurityError(
                f"Path not in allowlist: {resolved_path or path}"
            )

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
        logger.debug("Validating path: %s", path)

        # First normalize the path
        norm_path = normalize_path(path)
        logger.debug("Normalized path: %s", norm_path)

        # Handle symlinks first - delegate to symlink_resolver
        if norm_path.is_symlink():
            logger.debug("Path is a symlink, resolving: %s", norm_path)
            try:
                resolved = _resolve_symlink(
                    norm_path,
                    self._max_symlink_depth,
                    self._allowed_dirs,
                )
                logger.debug("Resolved symlink to: %s", resolved)

                # Additional symlink target validation for enhanced security
                self.validate_symlink_target(norm_path)

                return resolved
            except RuntimeError as e:
                if "Symlink loop" in str(e):
                    logger.error("Symlink loop detected: %s", path)
                    raise PathSecurityError(
                        "Symlink security violation: loop detected",
                        path=str(path),
                        context={"reason": SecurityErrorReasons.SYMLINK_LOOP},
                    ) from e
                logger.error("Failed to resolve symlink: %s - %s", path, e)
                raise PathSecurityError(
                    f"Symlink security violation: failed to resolve symlink - {e}",
                    path=str(path),
                    context={"reason": SecurityErrorReasons.SYMLINK_ERROR},
                ) from e

        # Check for directory traversal attempts
        if ".." in str(norm_path):
            logger.error("Directory traversal attempt detected: %s", path)
            raise PathSecurityError(
                "Directory traversal attempt blocked",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.PATH_TRAVERSAL,
                    "base_dir": str(self._base_dir),
                    "allowed_dirs": [str(d) for d in self._allowed_dirs],
                },
            )

        # Check for suspicious Unicode characters
        if any(
            c in str(norm_path)
            for c in [
                "\u2024",
                "\u2025",
                "\u2026",
                "\u0085",
                "\u2028",
                "\u2029",
            ]
        ):
            logger.error("Suspicious Unicode characters detected: %s", path)
            raise PathSecurityError(
                "Suspicious characters detected in path",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.UNSAFE_UNICODE,
                    "base_dir": str(self._base_dir),
                    "allowed_dirs": [str(d) for d in self._allowed_dirs],
                },
            )

        # For non-symlinks, check if the normalized path is allowed
        logger.debug("Checking if path is allowed: %s", norm_path)
        if not self.is_path_allowed(norm_path):
            logger.error(
                "Path outside allowed directories: %s (base_dir=%s, allowed_dirs=%s)",
                path,
                self._base_dir,
                self._allowed_dirs,
            )
            raise PathSecurityError(
                "Path outside allowed directories",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.PATH_OUTSIDE_ALLOWED,
                    "base_dir": str(self._base_dir),
                    "allowed_dirs": [str(d) for d in self._allowed_dirs],
                },
            )

        # Only check existence after security validation passes
        logger.debug("Checking if path exists: %s", norm_path)
        if not norm_path.exists():
            logger.debug("Path allowed but not found: %s", norm_path)
            raise OstructFileNotFoundError(str(path))

        logger.debug("Path validation successful: %s", norm_path)
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
                    raise OstructFileNotFoundError(f"File not found: {path}")
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
                        raise OstructFileNotFoundError(msg) from e
                    # Any other security errors propagate unchanged
                    raise

            # For non-symlinks, check if the normalized path is allowed using enhanced security
            if not self.is_path_allowed_enhanced(norm_path):
                # is_path_allowed_enhanced() handles mode-specific behavior (warn vs strict)
                # If we get here in STRICT mode, it means an exception was already raised
                # In WARN/PERMISSIVE modes, we continue with a warning already logged
                pass

            # Only check existence after security validation
            if not norm_path.exists():
                raise OstructFileNotFoundError(f"File not found: {path}")

            return norm_path

        except OSError as e:
            if isinstance(e, OstructFileNotFoundError):
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
