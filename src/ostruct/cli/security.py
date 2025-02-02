"""Security management for file access.

This module provides security checks for file access, including:
- Base directory restrictions
- Allowed directory validation
- Path traversal prevention
- Temporary directory handling
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Set, Union
import errno
from contextlib import contextmanager

from .errors import DirectoryNotFoundError, PathSecurityError
from .security_types import SecurityManagerProtocol


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
    # Normalize the input path (resolve symlinks)
    abs_path = os.path.realpath(path)

    # Get the system temp dir (platform independent)
    temp_dir = os.path.realpath(tempfile.gettempdir())

    # Check if file is in the temp directory using normalized paths
    abs_path_parts = os.path.normpath(abs_path).split(os.sep)
    temp_dir_parts = os.path.normpath(temp_dir).split(os.sep)
    
    # Check if the path starts with the temp directory components
    if len(abs_path_parts) >= len(temp_dir_parts) and all(
        a == b
        for a, b in zip(
            abs_path_parts[: len(temp_dir_parts)], temp_dir_parts
        )
    ):
        return True

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

    All paths are normalized using realpath() to handle symlinks consistently across platforms.
    """

    def __init__(self, base_dir: str, allowed_dirs: List[str] = None, allow_temp_paths: bool = False, max_symlink_depth: int = 16):
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

        # Simply resolve paths without extra validation during initialization
        self._base_dir = Path(os.path.realpath(base_dir))
        if not self._base_dir.exists():
            raise DirectoryNotFoundError(f"Base directory does not exist: {base_dir}")
        if not self._base_dir.is_dir():
            raise DirectoryNotFoundError(f"Base path is not a directory: {base_dir}")

        # Set up allowed directories, starting with base_dir
        self._allowed_dirs = [self._base_dir]
        if allowed_dirs:
            for directory in allowed_dirs:
                real_path = Path(os.path.realpath(directory))
                if not real_path.exists():
                    raise DirectoryNotFoundError(f"Allowed path does not exist: {directory}")
                if not real_path.is_dir():
                    raise DirectoryNotFoundError(f"Allowed path is not a directory: {directory}")
                if real_path not in self._allowed_dirs:
                    self._allowed_dirs.append(real_path)

        # Set up temp directory handling
        self.allow_temp_paths = allow_temp_paths
        self._temp_dir = Path(os.path.realpath(tempfile.gettempdir()))
        
        # Set up symlink handling
        self.max_symlink_depth = max_symlink_depth
        self._symlink_cache = {}

    @contextmanager
    def initializing(self):
        """Context manager to disable validation during initialization."""
        self._initialization_context = True
        try:
            yield
        finally:
            self._initialization_context = False

    @contextmanager
    def symlink_context(self):
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
        real_path = Path(os.path.realpath(directory))
        if not real_path.exists():
            raise DirectoryNotFoundError(f"Allowed path does not exist: {directory}")
        if not real_path.is_dir():
            raise DirectoryNotFoundError(f"Allowed path is not a directory: {directory}")
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
        """
        if file_path is None:
            return  # Skip None paths silently
            
        real_path = Path(os.path.realpath(file_path))

        # First validate the file path itself
        try:
            self.validate_path(
                str(real_path), purpose="read allowed directories"
            )
        except PathSecurityError:
            raise PathSecurityError.from_expanded_paths(
                original_path=file_path,
                expanded_path=str(real_path),
                error_logged=True,
                base_dir=str(self._base_dir),
                allowed_dirs=[str(d) for d in self._allowed_dirs],
            )

        if not real_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(real_path) as f:
            for line in f:
                directory = line.strip()
                if directory and not directory.startswith("#"):
                    self.add_allowed_directory(directory)

    def is_path_allowed(self, path: Union[str, Path]) -> bool:
        """Check if a path is allowed.

        Args:
            path: Path to check

        Returns:
            bool: True if the path is allowed
        """
        # Skip validation during initialization
        if getattr(self, "_initialization_context", False):
            return True

        try:
            real_path = Path(os.path.realpath(path))
            
            # Check against allowed directories
            for allowed_dir in self._allowed_dirs:
                try:
                    real_path.relative_to(allowed_dir)
                    return True
                except ValueError:
                    continue
            return False
            
        except OSError:
            return False

    def is_temp_path(self, path: Union[str, Path]) -> bool:
        """Check if a path is in a temporary directory.

        Args:
            path: Path to check

        Returns:
            bool: True if the path is in a temporary directory
        """
        # Convert to absolute path without resolving
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = Path.cwd() / path_obj
        
        # Convert to string for comparison to avoid resolve() call
        path_str = str(path_obj)
        temp_str = str(self._temp_dir)
        
        # Simple string prefix check
        return path_str.startswith(temp_str + os.sep) or path_str == temp_str

    def validate_path(self, path: Union[str, Path], purpose: str = "access") -> Path:
        """Validate and resolve a path.

        Args:
            path: Path to validate
            purpose: Description of the intended use (for error messages)

        Returns:
            Path: Normalized path object

        Raises:
            PathSecurityError: If path is not allowed
        """
        if path is None:
            raise ValueError("Path cannot be None")
            
        logger = logging.getLogger("ostruct")
        logger.debug("Validating path for %s: %s", purpose, path)

        try:
            # Convert input to a Path object and resolve it
            path_obj = Path(os.path.realpath(path))
            logger.debug("Resolved real path: %s", path_obj)

            # First, check if it's a temp path using a simple prefix check
            if str(path_obj).startswith(str(self._temp_dir)):
                logger.debug("Path is in temp directory")
                if not self.allow_temp_paths:
                    logger.error("Temp paths are not allowed")
                    raise PathSecurityError(
                        "Access denied: Temporary paths are not allowed",
                        path=str(path),
                        context={"reason": "temp_paths_not_allowed"},
                        error_logged=True
                    )
                return path_obj

            # Then, check that the path is under the base_dir or one of the allowed_dirs
            if not any(str(path_obj).startswith(str(root)) for root in self._allowed_dirs):
                logger.error(
                    "Access denied: Attempted to %s path outside allowed directories: %s (resolved to %s)",
                    purpose,
                    path,
                    path_obj
                )
                raise PathSecurityError(
                    f"Access denied: {path} is outside base directory and not in allowed directories",
                    path=str(path),
                    context={
                        "reason": "path_not_allowed",
                        "base_dir": str(self._base_dir),
                        "allowed_dirs": [str(d) for d in self._allowed_dirs],
                        "expanded_path": str(path_obj)
                    },
                    error_logged=True
                )

            return path_obj

        except OSError as e:
            if e.errno == errno.ELOOP:
                raise PathSecurityError(
                    "Symlink loop detected",
                    path=str(path),
                    context={"reason": "symlink_loop"}
                )
            elif e.errno == errno.ENOENT:
                raise PathSecurityError(
                    "Error resolving symlink",
                    path=str(path),
                    context={"reason": "symlink_error"}
                )
            raise

    def is_allowed_file(self, path: str) -> bool:
        """Check if file access is allowed.

        Args:
            path: Path to check

        Returns:
            bool: True if file exists and is allowed
        """
        try:
            real_path = Path(os.path.realpath(path))
            return self.is_path_allowed(str(real_path)) and real_path.is_file()
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
            
        p = Path(path)
        if not p.is_absolute():
            p = Path.cwd() / p
        
        # Resolve the path to handle .. components
        try:
            return p.resolve()
        except OSError as e:
            if e.errno == errno.ENOENT:
                # If the file doesn't exist, still normalize the path
                # This allows security checks on non-existent files
                return p.absolute()
            raise

    def _check_security(self, path: Path, context: str) -> None:
        """Check if a path is allowed.
        
        Args:
            path: Path to check
            context: Description of the check (for error messages)
            
        Raises:
            PathSecurityError: If path is not allowed
        """
        logger = logging.getLogger("ostruct")
        logger.debug("Security check (%s) for path: %s", context, path)
        
        # Skip validation during initialization
        if getattr(self, "_initialization_context", False):
            return
        
        # First check if it's in the base directory
        try:
            # Use strict=True to ensure exact path matching
            path.relative_to(self._base_dir)
            return  # If we get here, it's in the base directory
        except ValueError:
            pass
            
        # Not in base directory, check allowed directories
        for allowed_dir in self._allowed_dirs:
            try:
                # Use strict=True to ensure exact path matching
                path.relative_to(allowed_dir)
                return  # If we get here, it's in an allowed directory
            except ValueError:
                continue
        
        # If we get here, path is not allowed
        error_msg = (
            f"Access denied: {path} is outside base directory and not in allowed directories. "
            f"Base directory: {self._base_dir}, "
            f"Allowed directories: {[str(d) for d in self._allowed_dirs]}"
        )
        logger.error(error_msg)  # Log the error
        raise PathSecurityError(
            error_msg,
            path=str(path),
            context={
                "reason": "path_not_allowed",
                "base_dir": str(self._base_dir),
                "allowed_dirs": [str(d) for d in self._allowed_dirs]
            },
            error_logged=True
        )

    def _safe_resolve(self, path: Path) -> Path:
        """Safely resolve symlinks with security checks.
        
        Args:
            path: Path to resolve
            
        Returns:
            Path: Resolved path
            
        Raises:
            PathSecurityError: If symlink resolution fails security checks
        """
        visited = set()
        current = path
        depth = 0
        
        while depth <= self.max_symlink_depth:
            if str(current) in visited:
                raise PathSecurityError(
                    "Symlink loop detected",
                    path=str(path),
                    context={
                        "reason": "symlink_loop",
                        "loop_chain": list(visited) + [str(current)]
                    },
                    error_logged=True
                )
            
            visited.add(str(current))
            
            try:
                if current.is_symlink():
                    # Read target without resolving
                    target = current.readlink()
                    if not target.is_absolute():
                        target = current.parent / target
                    
                    # Check security before following
                    self._check_security(target, "symlink target check")
                    
                    current = target
                    depth += 1
                else:
                    # Not a symlink, we're done
                    return current
                    
            except OSError as e:
                if e.errno == errno.ELOOP:
                    raise PathSecurityError(
                        "Symlink loop detected",
                        path=str(path),
                        context={
                            "reason": "symlink_loop",
                            "loop_chain": list(visited)
                        },
                        error_logged=True
                    )
                elif e.errno == errno.ENOENT:
                    raise PathSecurityError(
                        "Error resolving symlink: target does not exist",
                        path=str(path),
                        context={"reason": "symlink_error"},
                        error_logged=True
                    )
                raise PathSecurityError(
                    f"Error resolving symlink: {e}",
                    path=str(path),
                    context={"reason": "symlink_error"},
                    error_logged=True
                )
        
        raise PathSecurityError(
            "Maximum symlink resolution depth exceeded",
            path=str(path),
            context={
                "reason": "max_depth_exceeded",
                "max_depth": self.max_symlink_depth,
                "resolution_chain": list(visited)
            },
            error_logged=True
        )

    def resolve_path(self, path: str) -> Path:
        """Resolve and validate a path.

        This method implements a three-phase validation approach:
        1. Normalize the input path to absolute path
        2. Perform initial security check before symlink resolution
        3. Safely resolve symlinks with security checks
        4. Perform final security check on resolved path

        Args:
            path: Path to resolve and validate

        Returns:
            Path: Normalized and validated path

        Raises:
            PathSecurityError: If path is not allowed
            ValueError: If path is None
        """
        logger = logging.getLogger("ostruct")
        logger.debug("Resolving path: %s", path)

        try:
            # Phase 1: Normalize input
            normalized = self._normalize_input(path)
            logger.debug("Normalized path: %s", normalized)

            # Phase 2: Initial security check
            self._check_security(normalized, "initial path check")
            logger.debug("Initial security check passed")

            # Phase 3: Safe symlink resolution
            resolved = self._safe_resolve(normalized)
            logger.debug("Resolved path: %s", resolved)

            # Phase 4: Final security check
            self._check_security(resolved, "final resolved path check")
            logger.debug("Final security check passed")

            return resolved

        except OSError as e:
            if e.errno == errno.ELOOP:
                raise PathSecurityError(
                    "Symlink loop detected",
                    path=str(path),
                    context={"reason": "symlink_loop"},
                    error_logged=True
                )
            elif e.errno == errno.ENOENT:
                raise PathSecurityError(
                    "Broken symlink or missing file",
                    path=str(path),
                    context={"reason": "broken_symlink"},
                    error_logged=True
                )
            raise PathSecurityError(
                f"Error resolving path: {e}",
                path=str(path),
                context={"reason": "resolution_error"},
                error_logged=True
            )

    def is_raw_path_allowed(self, path: str) -> bool:
        """
        Check whether a raw path (already cleaned) is allowed without performing full resolution.
        """
        for allowed_dir in self._allowed_dirs:
            if path.startswith(str(allowed_dir)):
                return True
        return False

    def resolve_symlink(self, path: Path, depth: int = 0) -> Path:
        """Resolve a symlink with security checks and loop detection.

        Args:
            path: Path to resolve
            depth: Current resolution depth

        Returns:
            Path: Resolved path

        Raises:
            PathSecurityError: If symlink resolution fails security checks
        """
        if depth > self.max_symlink_depth:
            raise PathSecurityError(
                "Maximum symlink resolution depth exceeded",
                path=str(path),
                context={
                    "reason": "max_depth_exceeded",
                    "max_depth": self.max_symlink_depth,
                    "resolution_chain": list(self._symlink_cache.keys())
                }
            )

        try:
            # First convert to absolute path if needed
            if not path.is_absolute():
                path = Path.cwd() / path
            
            # Check for loops using the original path
            if str(path) in self._symlink_cache:
                raise PathSecurityError(
                    "Symlink loop detected",
                    path=str(path),
                    context={
                        "reason": "symlink_loop",
                        "loop_chain": list(self._symlink_cache.keys()) + [str(path)]
                    }
                )
            
            # If it's a symlink, resolve its target
            if path.is_symlink():
                self._symlink_cache[str(path)] = depth
                
                try:
                    # Read the target without resolving it
                    target = path.readlink()
                    if not target.is_absolute():
                        target = path.parent / target
                    
                    # Validate the target before following it
                    if not self.is_path_allowed(str(target)):
                        raise PathSecurityError(
                            f"Symlink target not allowed: {target}",
                            path=str(path),
                            context={
                                "reason": "symlink_target_not_allowed",
                                "target": str(target)
                            }
                        )
                    
                    # Now resolve the target
                    return self.resolve_symlink(target, depth + 1)
                    
                except OSError as e:
                    if e.errno == errno.ELOOP:
                        # Convert symlink loop error to our custom error
                        raise PathSecurityError(
                            "Symlink loop detected",
                            path=str(path),
                            context={
                                "reason": "symlink_loop",
                                "loop_chain": list(self._symlink_cache.keys()) + [str(path)]
                            }
                        )
                    elif e.errno == errno.ENOENT:
                        raise PathSecurityError(
                            "Error resolving symlink: target does not exist",
                            path=str(path),
                            context={"reason": "symlink_error"}
                        )
                    raise PathSecurityError(
                        f"Error resolving symlink: {e}",
                        path=str(path),
                        context={"reason": "symlink_error"}
                    )
            
            # Check if the path exists before returning
            if not path.exists():
                raise PathSecurityError(
                    "Error resolving symlink: path does not exist",
                    path=str(path),
                    context={"reason": "symlink_error"}
                )
            
            # Not a symlink, return the path itself
            return path
            
        except OSError as e:
            if e.errno == errno.ELOOP:
                raise PathSecurityError(
                    "Symlink loop detected",
                    path=str(path),
                    context={"reason": "symlink_loop"}
                )
            elif e.errno == errno.ENOENT:
                raise PathSecurityError(
                    "Error resolving symlink: path does not exist",
                    path=str(path),
                    context={"reason": "symlink_error"}
                )
            raise PathSecurityError(
                f"Error resolving symlink: {e}",
                path=str(path),
                context={"reason": "symlink_error"}
            )
