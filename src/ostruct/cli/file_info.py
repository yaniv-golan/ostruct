"""FileInfo class for representing file metadata and content."""

import hashlib
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .errors import FileReadError, OstructFileNotFoundError, PathSecurityError
from .security import SecurityManager


class FileRoutingIntent(Enum):
    """Represents the intended use of a file in the ostruct pipeline.

    This enum helps distinguish between different file routing intentions
    to provide appropriate warnings and optimizations.
    """

    TEMPLATE_ONLY = "template_only"  # -ft, --fta, legacy -f, -d
    CODE_INTERPRETER = "code_interpreter"  # -fc, --fca
    FILE_SEARCH = "file_search"  # -fs, --fsa


logger = logging.getLogger(__name__)


class FileInfo:
    """Represents a file with metadata and content.

    This class provides access to file metadata (path, size, etc.) and content,
    with caching support for efficient access.

    Args:
        path: Path to the file
        security_manager: Security manager to use for path validation
        content: Optional cached content
        encoding: Optional cached encoding
        hash_value: Optional cached hash value
        routing_type: How the file was routed (e.g., 'template', 'code-interpreter')
    """

    def __init__(
        self,
        path: str,
        security_manager: SecurityManager,
        content: Optional[str] = None,
        encoding: Optional[str] = None,
        hash_value: Optional[str] = None,
        routing_type: Optional[str] = None,
        routing_intent: Optional[FileRoutingIntent] = None,
    ) -> None:
        """Initialize FileInfo instance.

        Args:
            path: Path to the file
            security_manager: Security manager to use for path validation
            content: Optional cached content
            encoding: Optional cached encoding
            hash_value: Optional cached hash value
            routing_type: How the file was routed (e.g., 'template', 'code-interpreter')
            routing_intent: The intended use of the file in the pipeline

        Raises:
            FileNotFoundError: If the file does not exist
            PathSecurityError: If the path is not allowed
            PermissionError: If access is denied
        """
        self.__path = str(path)
        self.__security_manager = security_manager
        self.__content = content
        self.__encoding = encoding
        self.__hash = hash_value
        self.__size: Optional[int] = None
        self.__mtime: Optional[float] = None
        self.routing_type = routing_type
        self.routing_intent = routing_intent

        logger.debug(
            "Creating FileInfo for path: %s, routing_type: %s",
            path,
            self.routing_type,
        )

        # Validate path
        if not path:
            raise ValueError("Path cannot be empty")

        try:
            # This will raise PathSecurityError if path is not allowed
            # And FileNotFoundError if the file doesn't exist
            resolved_path = self.__security_manager.resolve_path(self.__path)
            logger.debug(
                "Security-resolved path for %s: %s", path, resolved_path
            )

            # Check if it's a regular file (not a directory, device, etc.)
            if not resolved_path.is_file():
                logger.debug("Not a regular file: %s", resolved_path)
                raise OstructFileNotFoundError(
                    f"Not a regular file: {os.path.basename(str(path))}"
                )

        except PathSecurityError as e:
            # Let security errors propagate directly with context
            logger.error(
                "Security error accessing file %s: %s",
                path,
                str(e),
                extra={
                    "path": path,
                    "resolved_path": (
                        str(resolved_path)
                        if "resolved_path" in locals()
                        else None
                    ),
                    "base_dir": str(self.__security_manager.base_dir),
                    "allowed_dirs": [
                        str(d) for d in self.__security_manager.allowed_dirs
                    ],
                },
            )
            raise

        except OstructFileNotFoundError as e:
            # Re-raise with standardized message format
            logger.debug("File not found error: %s", e)
            raise OstructFileNotFoundError(
                f"File not found: {os.path.basename(str(path))}"
            ) from e

        except PermissionError as e:
            # Handle permission errors with context
            logger.error(
                "Permission denied accessing file %s: %s",
                path,
                str(e),
                extra={
                    "path": path,
                    "resolved_path": (
                        str(resolved_path)
                        if "resolved_path" in locals()
                        else None
                    ),
                },
            )
            raise PermissionError(
                f"Permission denied: {os.path.basename(str(path))}"
            ) from e

    @property
    def path(self) -> str:
        """Get the path relative to security manager's base directory.

        Returns a path relative to the security manager's base directory.
        This ensures consistent path handling across the entire codebase.

        For paths outside the base directory but within allowed directories,
        returns the absolute path.

        Example:
            security_manager = SecurityManager(base_dir="/base")
            file_info = FileInfo("/base/file.txt", security_manager)
            print(file_info.path)  # Outputs: "file.txt"

            # With allowed directory outside base:
            file_info = FileInfo("/tmp/file.txt", security_manager)
            print(file_info.path)  # Outputs: "/tmp/file.txt"

        Returns:
            str: Path relative to security manager's base directory, or absolute path
                 if outside base directory but within allowed directories

        Raises:
            ValueError: If the path is not within the base directory or allowed directories
        """
        abs_path = Path(self.abs_path)
        base_dir = Path(self.__security_manager.base_dir)

        try:
            return str(abs_path.relative_to(base_dir))
        except ValueError:
            # Path is outside base_dir, check if it's in allowed directories
            if self.__security_manager.is_path_allowed(abs_path):
                logger.debug(
                    "Path outside base_dir but allowed, returning absolute path: %s",
                    abs_path,
                )
                return str(abs_path)

            # Should never reach here if SecurityManager validation was done properly
            logger.error(
                "Error making path relative: %s is not within base directory %s",
                abs_path,
                base_dir,
            )
            raise ValueError(
                f"Path {abs_path} must be within base directory {base_dir}"
            )

    @path.setter
    def path(self, value: str) -> None:
        """Prevent setting path directly."""
        raise AttributeError("Cannot modify path directly")

    @property
    def abs_path(self) -> str:
        """Get the absolute path of the file.

        Returns:
            str: The absolute path of the file.

        Raises:
            PathSecurityError: If the path is not allowed.
        """
        # Get the resolved absolute path through security manager
        resolved = self.__security_manager.resolve_path(self.__path)

        # Always return absolute path
        return str(resolved)

    @property
    def extension(self) -> str:
        """Get file extension without dot."""
        return os.path.splitext(self.__path)[1].lstrip(".")

    @property
    def name(self) -> str:
        """Get the filename without directory path."""
        return os.path.basename(self.__path)

    @name.setter
    def name(self, value: str) -> None:
        """Prevent setting name directly."""
        raise AttributeError("Cannot modify name directly")

    @property
    def size(self) -> Optional[int]:
        """Get file size in bytes."""
        if self.__size is None:
            try:
                size = os.path.getsize(self.abs_path)
                self.__size = size
            except OSError:
                logger.warning("Could not get size for %s", self.__path)
                return None
        return self.__size

    @size.setter
    def size(self, value: int) -> None:
        """Prevent setting size directly."""
        raise AttributeError("Cannot modify size directly")

    @property
    def mtime(self) -> Optional[float]:
        """Get file modification time as Unix timestamp."""
        if self.__mtime is None:
            try:
                mtime = os.path.getmtime(self.abs_path)
                self.__mtime = mtime
            except OSError:
                logger.warning("Could not get mtime for %s", self.__path)
                return None
        return self.__mtime

    @mtime.setter
    def mtime(self, value: float) -> None:
        """Prevent setting mtime directly."""
        raise AttributeError("Cannot modify mtime directly")

    @property
    def content(self) -> str:
        """Get the content of the file.

        Returns:
            str: The file content

        Raises:
            FileReadError: If the file cannot be read, wrapping the underlying cause
                         (FileNotFoundError, UnicodeDecodeError, etc)
        """
        # Add warning for large template-only files accessed via .content
        # Use intent-based logic with fallback to routing_type for backward compatibility
        template_only_intents = {FileRoutingIntent.TEMPLATE_ONLY}

        # Determine if this is template-only routing
        is_template_only = False
        if self.routing_intent is not None:
            # Use intent if available (new logic)
            is_template_only = self.routing_intent in template_only_intents
        else:
            # Fallback to old logic for backward compatibility
            is_template_only = (
                self.routing_type == "template" or self.routing_type is None
            )

        if (
            is_template_only and self.size and self.size > 100 * 1024
        ):  # 100KB threshold
            logger.warning(
                f"File '{self.path}' ({self.size / 1024:.1f}KB) was routed for template-only access "
                f"but its .content is being accessed. This will include the entire file content "
                f"in the prompt sent to the AI. For large files intended for analysis or search, "
                f"consider using -fc (Code Interpreter) or -fs (File Search) to optimize token usage, "
                f"cost, and avoid exceeding model context limits."
            )

        if self.__content is None:
            try:
                self._read_file()
            except Exception as e:
                raise FileReadError(
                    f"Failed to load content: {self.__path}", self.__path
                ) from e
        assert (
            self.__content is not None
        )  # Help mypy understand content is set
        return self.__content

    @content.setter
    def content(self, value: str) -> None:
        """Prevent setting content directly."""
        raise AttributeError("Cannot modify content directly")

    @property
    def encoding(self) -> str:
        """Get the encoding of the file.

        Returns:
            str: The file encoding (utf-8 or system)

        Raises:
            FileReadError: If the file cannot be read or decoded
        """
        if self.__encoding is None:
            # This will trigger content loading and may raise FileReadError
            self.content
        assert (
            self.__encoding is not None
        )  # Help mypy understand encoding is set
        return self.__encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        """Prevent setting encoding directly."""
        raise AttributeError("Cannot modify encoding directly")

    @property
    def hash(self) -> Optional[str]:
        """Get SHA-256 hash of file content."""
        if self.__hash is None and self.__content is not None:
            self.__hash = hashlib.sha256(
                self.__content.encode("utf-8")
            ).hexdigest()
        return self.__hash

    @hash.setter
    def hash(self, value: str) -> None:
        """Prevent setting hash directly."""
        raise AttributeError("Cannot modify hash directly")

    @property
    def exists(self) -> bool:
        """Check if the file exists.

        Returns:
            bool: True if the file exists, False otherwise
        """
        try:
            return os.path.exists(self.abs_path)
        except (OSError, PathSecurityError):
            return False

    @property
    def is_binary(self) -> bool:
        """Check if the file appears to be binary.

        Returns:
            bool: True if the file appears to be binary, False otherwise
        """
        try:
            with open(self.abs_path, "rb") as f:
                chunk = f.read(1024)
                return b"\0" in chunk
        except (OSError, PathSecurityError):
            return False

    def _read_file(self) -> None:
        """Read and decode file content.

        Implementation detail: Attempts UTF-8 first, falls back to system encoding.
        All exceptions will be caught and wrapped by the content property.
        """
        try:
            with open(self.abs_path, "rb") as f:
                raw_content = f.read()
            try:
                self.__content = raw_content.decode("utf-8")
                self.__encoding = "utf-8"
            except UnicodeDecodeError:
                # Fall back to system encoding
                self.__content = raw_content.decode()
                self.__encoding = "system"
        except Exception:
            # Let content property handle all errors
            raise

    def update_cache(
        self,
        content: Optional[str] = None,
        encoding: Optional[str] = None,
        hash_value: Optional[str] = None,
    ) -> None:
        """Update cached values.

        Args:
            content: New content to cache
            encoding: New encoding to cache
            hash_value: New hash value to cache
        """
        if content is not None:
            self.__content = content
        if encoding is not None:
            self.__encoding = encoding
        if hash_value is not None:
            self.__hash = hash_value

    @classmethod
    def from_path(
        cls,
        path: str,
        security_manager: SecurityManager,
        routing_type: Optional[str] = None,
        routing_intent: Optional[FileRoutingIntent] = None,
    ) -> "FileInfo":
        """Create FileInfo instance from path.

        Args:
            path: Path to file
            security_manager: Security manager for path validation
            routing_type: How the file was routed (e.g., 'template', 'code-interpreter')
            routing_intent: The intended use of the file in the pipeline

        Returns:
            FileInfo instance

        Raises:
            FileNotFoundError: If file does not exist
            PathSecurityError: If path is not allowed
        """
        return cls(
            path,
            security_manager,
            routing_type=routing_type,
            routing_intent=routing_intent,
        )

    def __str__(self) -> str:
        """String representation showing path."""
        return f"FileInfo({self.__path})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"FileInfo(path={self.__path!r}, "
            f"size={self.size!r}, "
            f"encoding={self.encoding!r}, "
            f"hash={self.hash!r})"
        )

    def __setattr__(self, name: str, value: Any) -> None:
        """Control attribute modification.

        Internal methods can modify private attributes, but external access is prevented.
        """
        # Allow setting routing_type and routing_intent if they're not already set (i.e., during __init__)
        if name in ("routing_type", "routing_intent") and not hasattr(
            self, name
        ):
            object.__setattr__(self, name, value)
            return

        # Allow setting private attributes from internal methods
        if name.startswith("_FileInfo__") and self._is_internal_call():
            object.__setattr__(self, name, value)
            return

        # Prevent setting other attributes
        raise AttributeError(f"Cannot modify {name} directly")

    def _is_internal_call(self) -> bool:
        """Check if the call is from an internal method."""
        import inspect

        frame = inspect.currentframe()
        try:
            # Get the caller's frame (2 frames up: _is_internal_call -> __setattr__ -> caller)
            caller = frame.f_back.f_back if frame and frame.f_back else None
            if not caller:
                return False

            # Check if the caller is a method of this class
            return (
                caller.f_code.co_name in type(self).__dict__
                and "self" in caller.f_locals
                and caller.f_locals["self"] is self
            )
        finally:
            del frame  # Avoid reference cycles

    def to_dict(self) -> dict[str, Any]:
        """Convert file info to a dictionary.

        Returns:
            Dictionary containing file metadata and content
        """
        # Get file stats
        stats = os.stat(self.abs_path)

        return {
            "path": self.path,
            "abs_path": str(self.abs_path),
            "exists": self.exists,
            "size": self.size,
            "content": self.content,
            "encoding": self.encoding,
            "hash": self.hash,
            "mtime": self.mtime,
            "mtime_ns": (
                int(self.mtime * 1e9) if self.mtime is not None else None
            ),
            "mode": stats.st_mode,
        }
