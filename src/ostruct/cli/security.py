"""Security management for file access.

This module provides security checks for file access, including:
- Base directory restrictions
- Allowed directory validation
- Path traversal prevention
- Temporary directory handling
"""

import errno
import logging
import os
import posixpath
import re
import sys
import tempfile
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Union
from unicodedata import category  # noqa: F401 - Used in docstring
from unicodedata import normalize  # noqa: F401 - Used in docstring

from .errors import DirectoryNotFoundError, PathSecurityError
from .security_types import SecurityManagerProtocol

# Compute alternative separators (if any) that differ from "/"
_os_alt_seps = list(
    {sep for sep in [os.path.sep, os.path.altsep] if sep and sep != "/"}
)

# Add these constants
_UNICODE_SAFETY_PATTERN = re.compile(
    r"[\u0000-\u001F\u007F-\u009F\u2028-\u2029\u0085]"  # Control chars and line separators
    r"|\.{2,}"  # Directory traversal attempts
    r"|[\\/]{2,}"  # Multiple consecutive separators
    r"|[\u2024\u2025\uFE52\u2024\u2025\u2026\uFE19\uFE30\uFE52\uFF0E\uFF61]"  # Alternative dots and separators
)


class CaseManager:
    """Manages original case preservation for paths.

    This class provides a thread-safe way to track original path cases
    without modifying Path objects. This is particularly important on
    case-insensitive systems (macOS, Windows) where we normalize paths
    to lowercase but want to preserve the original case for display.
    """

    _case_mapping: dict[str, str] = {}

    @classmethod
    def set_original_case(
        cls, normalized_path: Path, original_case: str
    ) -> None:
        """Store the original case for a normalized path.

        Args:
            normalized_path: The normalized (potentially lowercased) Path
            original_case: The original case string to preserve
        """
        cls._case_mapping[str(normalized_path)] = original_case

    @classmethod
    def get_original_case(cls, normalized_path: Path) -> str:
        """Retrieve the original case for a normalized path.

        Args:
            normalized_path: The normalized Path to look up

        Returns:
            The original case string if found, otherwise the normalized path string
        """
        path_str = str(normalized_path)
        return cls._case_mapping.get(path_str, path_str)

    @classmethod
    def clear(cls) -> None:
        """Clear all stored case mappings."""
        cls._case_mapping.clear()


class SecurityErrorReasons:
    """Constants for security error reasons to ensure consistency."""

    SYMLINK_LOOP = "symlink_loop"
    MAX_DEPTH_EXCEEDED = "max_depth_exceeded"
    BROKEN_SYMLINK = "broken_symlink"
    PATH_TRAVERSAL = "path_traversal"
    SYMLINK_ERROR = "symlink_error"
    PATH_NOT_ALLOWED = "path_not_allowed"
    TEMP_PATHS_NOT_ALLOWED = "temp_paths_not_allowed"
    VALIDATION_ERROR = "validation_error"
    UNSAFE_UNICODE = "unsafe_unicode"
    NORMALIZATION_ERROR = "normalization_error"
    SYMLINK_TARGET_NOT_ALLOWED = "symlink_target_not_allowed"
    RESOLUTION_ERROR = "resolution_error"
    FILE_NOT_FOUND = "file_not_found"
    OUTSIDE_ALLOWED_DIRS = "outside_allowed_dirs"
    CASE_MISMATCH = "case_mismatch"


def normalize_path(
    path: Union[str, Path], check_traversal: bool = True
) -> Path:
    """
    Normalize a path following secure path handling best practices.

    Order of operations:
    1. Input normalization (Unicode NFKC)
    2. Security checks for dangerous Unicode
    3. Convert to absolute path
    4. Handle case sensitivity
    5. Final validation
    """
    try:
        # Step 1: Input normalization
        path_str = str(path)
        path_str = unicodedata.normalize("NFKC", path_str)

        # Normalize path separators
        path_str = path_str.replace("\\", "/")

        # Remove redundant separators and normalize dots
        path_str = os.path.normpath(path_str)

        # Step 2: Security checks for dangerous Unicode
        if _UNICODE_SAFETY_PATTERN.search(path_str):
            raise PathSecurityError(
                f"Path contains potentially dangerous Unicode characters: {path_str}",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.UNSAFE_UNICODE,
                    "path": path_str,
                },
            )

        # Step 3: Convert to Path object and make absolute
        path_obj = Path(path_str)
        if not path_obj.is_absolute():
            path_obj = Path.cwd() / path_obj

        # Normalize path without resolving symlinks
        path_obj = path_obj.absolute()

        # Step 4: Handle case sensitivity based on platform
        if sys.platform == "darwin" or os.name == "nt":
            try:
                # Store original case before normalization
                original_case = str(path_obj)
                normalized_case = original_case.lower()

                # Create new path object with normalized case
                path_obj = Path(normalized_case)

                # Store original case in CaseManager
                CaseManager.set_original_case(path_obj, original_case)

            except (OSError, RuntimeError) as e:
                raise PathSecurityError(
                    f"Error normalizing path case: {e}",
                    path=str(path),
                    context={
                        "reason": SecurityErrorReasons.CASE_MISMATCH,
                        "error": str(e),
                    },
                )

        # Step 5: Final validation - check for path traversal
        if check_traversal:
            # Check for path traversal without resolving symlinks
            clean_parts: list[str] = []
            for part in path_obj.parts:
                if part == "..":
                    if not clean_parts:
                        raise PathSecurityError(
                            f"Path traversal attempt detected: {path}",
                            path=str(path),
                            context={
                                "reason": SecurityErrorReasons.PATH_TRAVERSAL,
                                "path": str(path_obj),
                            },
                        )
                    clean_parts.pop()
                elif part not in ("", "."):
                    clean_parts.append(part)

            # Reconstruct path from clean parts
            path_obj = Path(*clean_parts)

        return path_obj

    except OSError as e:
        raise PathSecurityError(
            f"Error normalizing path: {e}",
            path=str(path),
            context={
                "reason": SecurityErrorReasons.NORMALIZATION_ERROR,
                "error": str(e),
            },
        )


def safe_join(directory: str, *pathnames: str) -> Optional[str]:
    """Safely join path components with a base directory.

    This function:
    1. Normalizes each path component
    2. Rejects absolute paths and traversal attempts
    3. Handles alternative separators
    4. Normalizes Unicode and case (on case-insensitive systems)

    Args:
        directory: Base directory to join with
        *pathnames: Path components to join

    Returns:
        Optional[str]: Joined path if safe, None if unsafe
    """
    if not directory:
        directory = "."

    # Normalize Unicode and case for base directory
    directory = unicodedata.normalize("NFC", str(directory))
    if os.name == "nt" or (os.name == "posix" and sys.platform == "darwin"):
        directory = directory.lower()

    parts = [directory]

    for filename in pathnames:
        if not filename:
            continue

        # Normalize Unicode and case
        filename = unicodedata.normalize("NFC", str(filename))
        if os.name == "nt" or (
            os.name == "posix" and sys.platform == "darwin"
        ):
            filename = filename.lower()

        # Normalize path separators and collapse dots
        filename = posixpath.normpath(filename.replace("\\", "/"))

        # Reject unsafe components
        if (
            os.path.isabs(filename)
            or filename == ".."
            or filename.startswith("../")
            or filename.startswith("/")
            or any(sep in filename for sep in _os_alt_seps)
        ):
            return None

        parts.append(filename)

    return posixpath.join(*parts)


def is_temp_file(path: str) -> bool:
    """Check if a file is in a temporary directory.

    Args:
        path: Path to check (will be converted to absolute path)

    Returns:
        True if the path is in a temporary directory, False otherwise

    Note:
        This function handles platform-specific path normalization, including symlinks
        (e.g., on macOS where /var is symlinked to /private/var).
    """
    try:
        # Normalize paths for comparison
        abs_path = normalize_path(path)
        temp_dir = normalize_path(tempfile.gettempdir())

        # Check if file is in the temp directory using is_relative_to
        return abs_path.is_relative_to(temp_dir)
    except (ValueError, OSError):
        return False


class SecurityManager(SecurityManagerProtocol):
    """Manages security for file access.

    Validates all file access against a base directory and optional
    allowed directories. Prevents unauthorized access and directory
    traversal attacks.

    The security model is based on:
    1. A base directory that serves as the root for all file operations
    2. A set of explicitly allowed directories that can be accessed outside the base directory
    3. Special handling for temporary directories that are always allowed
    4. Case-sensitive or case-insensitive path handling based on platform

    Case Sensitivity Handling:
    - All paths are normalized using normalize_path() before comparison
    - On case-insensitive systems (macOS, Windows):
      * Directory comparisons are case-insensitive
      * Base and allowed directories are stored in normalized case
      * Path validation preserves original case in error messages
    - On case-sensitive systems (Linux):
      * Directory comparisons are case-sensitive
      * Base and allowed directories maintain original case
      * Path validation requires exact case matches

    Security Implications of Case Sensitivity:
    - Path traversal checks work on normalized paths
    - Symlink resolution uses case-aware path comparison
    - Allowed directory checks respect platform case sensitivity
    - Error messages maintain original case for debugging
    - Temporary path detection is case-aware

    Example:
        >>> # On macOS (case-insensitive):
        >>> sm = SecurityManager("/base/dir")
        >>> sm.is_path_allowed("/base/DIR/file.txt")  # True
        >>> sm.is_path_allowed("/BASE/dir/file.txt")  # True

        >>> # On Linux (case-sensitive):
        >>> sm = SecurityManager("/base/dir")
        >>> sm.is_path_allowed("/base/DIR/file.txt")  # False
        >>> sm.is_path_allowed("/base/dir/file.txt")  # True

    All paths are normalized using realpath() to handle symlinks consistently across platforms.
    """

    def __init__(
        self,
        base_dir: str,
        allowed_dirs: Optional[List[str]] = None,
        allow_temp_paths: bool = False,
        max_symlink_depth: int = 16,
    ):
        """Initialize the SecurityManager.

        Args:
            base_dir: Base directory for path validation
            allowed_dirs: Additional allowed directories
            allow_temp_paths: Whether to allow paths in temporary directories
            max_symlink_depth: Maximum depth for symlink resolution

        Raises:
            DirectoryNotFoundError: If base_dir or any allowed directory does not exist or is not a directory
        """
        logger = logging.getLogger("ostruct")
        logger.debug("Initializing SecurityManager")

        # Normalize base directory
        try:
            self._base_dir = normalize_path(base_dir)
            if not self._base_dir.is_dir():
                raise DirectoryNotFoundError(
                    f"Base path is not a directory: {base_dir}"
                )
        except OSError as e:
            raise DirectoryNotFoundError(
                f"Base directory does not exist: {base_dir}"
            ) from e

        # Set up allowed directories, starting with base_dir
        self._allowed_dirs = [self._base_dir]
        if allowed_dirs:
            for directory in allowed_dirs:
                try:
                    real_path = normalize_path(directory)
                    if not real_path.is_dir():
                        raise DirectoryNotFoundError(
                            f"Allowed path is not a directory: {directory}"
                        )
                    if real_path not in self._allowed_dirs:
                        self._allowed_dirs.append(real_path)
                except OSError as e:
                    raise DirectoryNotFoundError(
                        f"Allowed path does not exist: {directory}"
                    ) from e

        # Set up temp directory handling - resolve it to handle platform symlinks
        self.allow_temp_paths = allow_temp_paths
        self._temp_dir = Path(tempfile.gettempdir()).resolve()
        logger.debug("Resolved temp directory: %s", self._temp_dir)

        # Set up symlink handling
        self.max_symlink_depth = max_symlink_depth
        self._symlink_cache: dict[str, str] = {}

    @contextmanager
    def initializing(self) -> Generator[None, None, None]:
        """Context manager to disable validation during initialization."""
        self._initialization_context = True
        try:
            yield
        finally:
            self._initialization_context = False

    @contextmanager
    def symlink_context(self) -> Generator[None, None, None]:
        """Clear symlink tracking cache for a fresh symlink resolution context."""
        old_cache = self._symlink_cache
        self._symlink_cache = {}
        try:
            yield
        finally:
            self._symlink_cache = old_cache

    @property
    def base_dir(self) -> Path:
        """Get the base directory."""
        return self._base_dir

    @property
    def allowed_dirs(self) -> List[Path]:
        """Get the list of allowed directories."""
        return sorted(self._allowed_dirs)  # Sort for consistent ordering

    def add_allowed_directory(self, directory: str) -> None:
        """Add a directory to the list of allowed directories.

        Args:
            directory: Directory to allow

        Raises:
            DirectoryNotFoundError: If directory does not exist or is not a directory
        """
        real_path = normalize_path(directory)
        if not real_path.is_dir():
            raise DirectoryNotFoundError(
                f"Allowed path is not a directory: {directory}"
            )
        if real_path not in self._allowed_dirs:
            self._allowed_dirs.append(real_path)

    def add_allowed_dirs_from_file(self, file_path: str) -> None:
        """Add allowed directories from a file.

        Args:
            file_path: Path to file containing allowed directories (one per line)

        Raises:
            PathSecurityError: If file_path is outside allowed directories
            FileNotFoundError: If file does not exist
            ValueError: If file contains invalid directories

        Note:
            This code is known to trigger a mypy "unreachable" error due to limitations
            in mypy's flow analysis. The code is actually reachable and works correctly
            at runtime, as verified by tests. A bug report should be filed with mypy.
        """
        if file_path is None:
            return  # Skip None paths silently

        real_path = normalize_path(file_path)
        try:
            validated_path = self.validate_path(
                str(real_path), purpose="read allowed directories"
            )
        except PathSecurityError as e:
            raise PathSecurityError.from_expanded_paths(
                original_path=file_path,
                expanded_path=str(real_path),
                error_logged=True,
                base_dir=str(self._base_dir),
                allowed_dirs=[str(d) for d in self._allowed_dirs],
            ) from e

        with open(validated_path) as f:
            for line in f:
                directory = line.strip()
                if directory and not directory.startswith("#"):
                    self.add_allowed_directory(directory)

    def is_temp_path(self, path: Union[str, Path]) -> bool:
        """Check if a path is in a temporary directory.

        Args:
            path: Path to check

        Returns:
            bool: True if path is in a temporary directory

        Note:
            This method handles platform-specific path normalization, including symlinks
            (e.g., on macOS where /tmp is symlinked to /private/tmp).
        """
        try:
            # Resolve both paths to handle symlinks
            resolved_path = Path(path).resolve()
            return resolved_path.is_relative_to(self._temp_dir)
        except (OSError, ValueError):
            return False

    def is_path_allowed(self, path: Union[str, Path]) -> bool:
        """Check if a path is allowed.

        A path is allowed if:
        1. It is under the base directory, or
        2. It is under one of the allowed directories, or
        3. It is in a temporary directory and temp paths are allowed

        Args:
            path: Path to check

        Returns:
            bool: True if path is allowed
        """
        try:
            # First check if it's a temp path
            if self.allow_temp_paths and self.is_temp_path(path):
                return True

            # Normalize the path without resolving symlinks
            path_obj = normalize_path(path, check_traversal=True)

            # Check unresolved path first
            for allowed_dir in self._allowed_dirs:
                try:
                    if path_obj.is_relative_to(allowed_dir):
                        return True
                except ValueError:
                    continue

            # Only resolve if necessary and the path exists
            try:
                if path_obj.exists():
                    resolved = path_obj.resolve(strict=True)
                    for allowed_dir in self._allowed_dirs:
                        try:
                            if resolved.is_relative_to(allowed_dir):
                                return True
                        except ValueError:
                            continue
            except (OSError, RuntimeError):
                return False

            return False

        except (OSError, PathSecurityError):
            return False

    def validate_path(
        self, path: Union[str, Path], purpose: str = "access"
    ) -> Path:
        """Validate and resolve a path.

        Args:
            path: Path to validate
            purpose: Description of the intended use (for error messages)

        Returns:
            Path: Normalized path object

        Raises:
            PathSecurityError: If path is not allowed
            FileNotFoundError: If path does not exist
        """
        if path is None:
            raise ValueError("Path cannot be None")

        logger = logging.getLogger("ostruct")
        logger.debug("Validating path for %s: %s", purpose, path)

        try:
            # First normalize the path without security checks
            path_obj = normalize_path(path, check_traversal=False)

            # Check if it's a temp path first (this is always safe to check)
            if self.is_temp_path(path_obj):
                if not self.allow_temp_paths:
                    logger.error("Temp paths are not allowed")
                    raise PathSecurityError(
                        "Access denied: Temporary paths are not allowed",
                        path=str(path),
                        context={
                            "reason": SecurityErrorReasons.TEMP_PATHS_NOT_ALLOWED
                        },
                        error_logged=True,
                    )
                # For temp paths, we check existence after allowing them
                if not path_obj.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                return path_obj

            # For non-temp paths, check existence first
            if not path_obj.exists():
                raise FileNotFoundError(f"File not found: {path}")

            # Resolve symlinks using our security-aware resolver
            try:
                if path_obj.is_symlink():
                    resolved = self.resolve_symlink(path_obj)
                else:
                    resolved = path_obj
            except PathSecurityError:
                raise  # Re-raise security errors
            except FileNotFoundError:
                raise  # Re-raise file not found errors

            # Final security check on resolved path
            if not self.is_path_allowed(resolved):
                logger.error(
                    "Access denied: Attempted to %s path outside allowed directories: %s",
                    purpose,
                    resolved,
                )
                raise PathSecurityError(
                    f"Access denied: {path} is outside base directory and not in allowed directories",
                    path=str(path),
                    context={
                        "reason": SecurityErrorReasons.OUTSIDE_ALLOWED_DIRS,
                        "base_dir": str(self._base_dir),
                        "allowed_dirs": [str(d) for d in self._allowed_dirs],
                        "expanded_path": str(resolved),
                    },
                    error_logged=True,
                )

            return resolved

        except OSError as e:
            if e.errno == errno.ENOENT:
                raise FileNotFoundError(f"File not found: {path}")

            logger.error("Error validating path: %s", e)
            raise PathSecurityError(
                f"Error validating path: {e}",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.VALIDATION_ERROR,
                    "error": str(e),
                },
                error_logged=True,
            ) from e

    def is_allowed_file(self, path: str) -> bool:
        """Check if file access is allowed.

        Args:
            path: Path to check

        Returns:
            bool: True if file exists and is allowed
        """
        try:
            real_path = normalize_path(path)
            return self.is_path_allowed(real_path) and real_path.is_file()
        except (ValueError, OSError):
            return False

    def is_allowed_path(self, path_str: str) -> bool:
        """Check if string path is allowed.

        Args:
            path_str: Path string to check

        Returns:
            bool: True if path is allowed
        """
        try:
            return self.is_path_allowed(path_str)
        except (ValueError, OSError):
            return False

    def _normalize_input(self, path: Union[str, Path]) -> Path:
        """Normalize input path to absolute path.

        Args:
            path: Input path to normalize

        Returns:
            Path: Normalized absolute path

        Raises:
            ValueError: If path is None
        """
        if path is None:
            raise ValueError("Path cannot be None")

        p = normalize_path(path)
        if not p.is_absolute():
            p = normalize_path(str(p))

        # Resolve the path to handle .. components
        try:
            return p.resolve()
        except OSError as e:
            if e.errno == errno.ENOENT:
                # If the file doesn't exist, still normalize the path
                # This allows security checks on non-existent files
                return p.absolute()
            raise

    def _check_security(self, path: Path, purpose: str) -> None:
        """Check if a path is allowed for a specific purpose.

        Args:
            path: Path to check
            purpose: Description of the intended use

        Raises:
            PathSecurityError: If path is not allowed
        """
        logger = logging.getLogger("ostruct")

        # First check if it's a temp path
        if self.is_temp_path(path):
            if not self.allow_temp_paths:
                logger.error("Temp paths are not allowed")
                raise PathSecurityError(
                    "Access denied: Temporary paths are not allowed",
                    path=str(path),
                    context={"reason": "temp_paths_not_allowed"},
                    error_logged=True,
                )
            return

        # Check against allowed directories
        if not self.is_path_allowed(path):
            logger.error(
                "Access denied: Attempted to %s path outside allowed directories: %s",
                purpose,
                path,
            )
            raise PathSecurityError(
                f"Access denied: {path} is outside base directory and not in allowed directories",
                path=str(path),
                context={
                    "reason": "path_not_allowed",
                    "base_dir": str(self._base_dir),
                    "allowed_dirs": [str(d) for d in self._allowed_dirs],
                    "expanded_path": str(path),
                },
                error_logged=True,
            )

    def resolve_path(self, path: str) -> Path:
        """Resolve and validate a path.

        Order of operations:
        1. Normalize the input path
        2. Check existence
        3. Validate security permissions
        4. Safely resolve symlinks with security checks at each step
        """
        logger = logging.getLogger("ostruct")
        logger.debug("Resolving path: %s", path)

        try:
            # Phase 1: Normalize input without security checks
            normalized = normalize_path(path, check_traversal=False)
            logger.debug("Normalized path: %s", normalized)

            # Phase 2: Check existence first
            if not normalized.exists():
                logger.error("File not found: %s", normalized)
                raise FileNotFoundError(f"File not found: {path}")

            # Phase 3: Initial security check
            if not self.is_path_allowed(normalized):
                logger.error(
                    "Access denied: Path outside allowed directories: %s",
                    normalized,
                )
                raise PathSecurityError(
                    f"Access denied: {normalized} is outside base directory and not in allowed directories",
                    path=str(path),
                    context={
                        "reason": SecurityErrorReasons.PATH_NOT_ALLOWED,
                        "base_dir": str(self._base_dir),
                        "allowed_dirs": [str(d) for d in self._allowed_dirs],
                        "expanded_path": str(normalized),
                    },
                    error_logged=True,
                )

            # Phase 4: Safe symlink resolution with security checks at each step
            if normalized.is_symlink():
                resolved = self.resolve_symlink(normalized)
                logger.debug(
                    "Resolved symlink: %s -> %s", normalized, resolved
                )

                # Final security check on resolved path
                if not self.is_path_allowed(resolved):
                    logger.error(
                        "Access denied: Symlink target outside allowed directories: %s -> %s",
                        normalized,
                        resolved,
                    )
                    raise PathSecurityError(
                        f"Access denied: Symlink target {resolved} is outside allowed directories",
                        path=str(path),
                        context={
                            "reason": SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED,
                            "target": str(resolved),
                            "source": str(normalized),
                        },
                        error_logged=True,
                    )

                return resolved

            return normalized

        except FileNotFoundError:
            # Re-raise FileNotFoundError without wrapping
            raise
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise FileNotFoundError(f"File not found: {path}")
            elif e.errno == errno.ELOOP:
                raise PathSecurityError(
                    f"Symlink loop detected at {path}",
                    path=str(path),
                    context={"reason": SecurityErrorReasons.SYMLINK_LOOP},
                    error_logged=True,
                )
            raise PathSecurityError(
                f"Error resolving path {path}: {e}",
                path=str(path),
                context={"reason": SecurityErrorReasons.RESOLUTION_ERROR},
                error_logged=True,
            )

    def resolve_symlink(
        self,
        path: Path,
        depth: int = 0,
        resolution_chain: Optional[List[str]] = None,
    ) -> Path:
        """
        Resolve a symlink with security checks at each step.

        Order of checks:
        1. Loop detection (prevent infinite loops)
        2. Max depth check (prevent resource exhaustion)
        3. Process symlink and check existence
        4. Security validation (prevent unauthorized access)
        """
        logger = logging.getLogger("ostruct")
        resolution_chain = resolution_chain or []

        # Convert to absolute path manually without resolve()
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.absolute()

        # Track current path before any operations
        current_path = str(path)
        new_chain = resolution_chain + [current_path]
        logger.debug("Processing path: %s (depth: %d)", current_path, depth)
        logger.debug("Resolution chain: %s", new_chain)

        # 1. Check for loops using the new chain
        if current_path in resolution_chain:
            loop_start = resolution_chain.index(current_path)
            loop_chain = resolution_chain[loop_start:] + [current_path]
            raise PathSecurityError(
                f"Symlink loop detected: {' -> '.join(loop_chain)}",
                path=current_path,
                context={
                    "reason": SecurityErrorReasons.SYMLINK_LOOP,
                    "resolution_chain": resolution_chain,
                    "loop_chain": loop_chain,
                },
            )

        # 2. Check max depth
        if depth >= self.max_symlink_depth:
            raise PathSecurityError(
                f"Maximum symlink depth ({self.max_symlink_depth}) exceeded",
                path=current_path,
                context={
                    "reason": SecurityErrorReasons.MAX_DEPTH_EXCEEDED,
                    "max_depth": self.max_symlink_depth,
                    "depth": depth,
                    "resolution_chain": new_chain,
                },
            )

        try:
            # 3. Process symlink and check existence
            if path.is_symlink():
                # Read target without resolving
                target = path.readlink()
                logger.debug("Found symlink: %s -> %s", path, target)

                # Convert relative target to absolute
                if not target.is_absolute():
                    target = path.parent / target
                target = target.absolute()

                # Check if target exists (using lstat to avoid resolving)
                try:
                    target.lstat()
                except FileNotFoundError:
                    raise PathSecurityError(
                        f"Broken symlink detected: {path} -> {target}",
                        path=current_path,
                        context={
                            "reason": SecurityErrorReasons.BROKEN_SYMLINK,
                            "target": str(target),
                            "resolution_chain": new_chain,
                        },
                    )

                # Check if target is allowed
                if not self.is_path_allowed(target):
                    raise PathSecurityError(
                        f"Symlink target not allowed: {path} -> {target}",
                        path=current_path,
                        context={
                            "reason": SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED,
                            "target": str(target),
                            "resolution_chain": new_chain,
                        },
                    )

                # Recurse to resolve target
                return self.resolve_symlink(target, depth + 1, new_chain)

            # 4. Final security check on non-symlink
            if not self.is_path_allowed(path):
                raise PathSecurityError(
                    f"Path not allowed: {path}",
                    path=current_path,
                    context={
                        "reason": SecurityErrorReasons.PATH_NOT_ALLOWED,
                        "path": str(path),
                    },
                )

            return path

        except OSError as e:
            if e.errno == errno.ENOENT:
                raise FileNotFoundError(f"File not found: {path}")
            elif e.errno == errno.ELOOP:
                raise PathSecurityError(
                    f"Symlink loop detected at {path}",
                    path=current_path,
                    context={
                        "reason": SecurityErrorReasons.SYMLINK_LOOP,
                        "resolution_chain": new_chain,
                    },
                )
            raise PathSecurityError(
                f"Error resolving symlink {path}: {e}",
                path=current_path,
                context={
                    "reason": SecurityErrorReasons.SYMLINK_ERROR,
                    "error": str(e),
                    "resolution_chain": new_chain,
                },
            )

    def is_raw_path_allowed(self, path: str) -> bool:
        """
        Check whether a raw path (already cleaned) is allowed without performing full resolution.
        """
        path_str = str(path)
        for allowed_dir in self._allowed_dirs:
            if path_str.startswith(str(allowed_dir)):
                return True
        return False
