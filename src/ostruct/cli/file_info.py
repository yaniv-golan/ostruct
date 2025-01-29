"""FileInfo class for representing file metadata and content."""

import hashlib
import logging
import os
from typing import Any, Optional

from .errors import FileNotFoundError, PathSecurityError
from .security import SecurityManager

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
    """

    def __init__(
        self,
        path: str,
        security_manager: SecurityManager,
        content: Optional[str] = None,
        encoding: Optional[str] = None,
        hash_value: Optional[str] = None,
    ) -> None:
        """Initialize FileInfo instance.

        Args:
            path: Path to the file
            security_manager: Security manager to use for path validation
            content: Optional cached content
            encoding: Optional cached encoding
            hash_value: Optional cached hash value

        Raises:
            FileNotFoundError: If the file does not exist
            PathSecurityError: If the path is not allowed
        """
        # Validate path
        if not path:
            raise ValueError("Path cannot be empty")

        # Initialize private attributes
        self.__path = os.path.expanduser(os.path.expandvars(path))
        self.__security_manager = security_manager
        self.__content = content
        self.__encoding = encoding
        self.__hash = hash_value
        self.__size: Optional[int] = None
        self.__mtime: Optional[float] = None

        # First check if file exists
        abs_path = os.path.abspath(self.__path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {path}")
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"Path is not a file: {path}")

        # Then validate security
        try:
            # This will raise PathSecurityError if path is not allowed
            self.abs_path
        except PathSecurityError:
            raise
        except Exception as e:
            raise FileNotFoundError(f"Invalid file path: {e}")

        # If content/encoding weren't provided, read them now
        if self.__content is None or self.__encoding is None:
            self._read_file()

    @property
    def path(self) -> str:
        """Get the relative path of the file."""
        # If original path was relative, keep it relative
        if not os.path.isabs(self.__path):
            try:
                base_dir = self.__security_manager.base_dir
                abs_path = self.abs_path
                return os.path.relpath(abs_path, base_dir)
            except ValueError:
                pass
        return self.__path

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
                self.__size = os.path.getsize(self.abs_path)
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
                self.__mtime = os.path.getmtime(self.abs_path)
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
        """Get the content of the file."""
        assert (
            self.__content is not None
        ), "Content should be initialized in constructor"
        return self.__content

    @content.setter
    def content(self, value: str) -> None:
        """Prevent setting content directly."""
        raise AttributeError("Cannot modify content directly")

    @property
    def encoding(self) -> str:
        """Get the encoding of the file."""
        assert (
            self.__encoding is not None
        ), "Encoding should be initialized in constructor"
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

    def _read_file(self) -> None:
        """Read file content and encoding from disk."""
        try:
            with open(self.abs_path, "rb") as f:
                raw_content = f.read()
        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found: {self.__path}") from e
        except OSError as e:
            raise FileNotFoundError(
                f"Could not read file {self.__path}: {e}"
            ) from e

        # Try UTF-8 first
        try:
            self.__content = raw_content.decode("utf-8")
            self.__encoding = "utf-8"
            return
        except UnicodeDecodeError:
            pass

        # Fall back to system default encoding
        try:
            self.__content = raw_content.decode()
            self.__encoding = "system"
            return
        except UnicodeDecodeError as e:
            raise ValueError(
                f"Could not decode file {self.__path}: {e}"
            ) from e

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
        cls, path: str, security_manager: SecurityManager
    ) -> "FileInfo":
        """Create FileInfo instance from path.

        Args:
            path: Path to file
            security_manager: Security manager for path validation

        Returns:
            FileInfo instance

        Raises:
            FileNotFoundError: If file does not exist
            PathSecurityError: If path is not allowed
        """
        return cls(path, security_manager)

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
