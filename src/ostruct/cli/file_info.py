"""FileInfo class for representing file metadata and content."""

import hashlib
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, Optional

from .errors import FileReadError, OstructFileNotFoundError, PathSecurityError
from .security import SecurityManager


class FileRoutingIntent(Enum):
    """Represents the intended use of a file in the ostruct pipeline.

    This enum helps distinguish between different file routing intentions
    to provide appropriate warnings and optimizations.
    """

    TEMPLATE_ONLY = "template_only"  # --file [alias] (template access only)
    CODE_INTERPRETER = "code_interpreter"  # --file ci:[alias]
    FILE_SEARCH = "file_search"  # --file fs:[alias]
    USER_DATA = (
        "user_data"  # --file ud:[alias] (user-data files for vision models)
    )


logger = logging.getLogger(__name__)


class LazyLoadError(Exception):
    """Exception raised during lazy loading operations."""

    pass


class LazyLoadSizeError(LazyLoadError):
    """Exception raised when file exceeds size limits."""

    pass


class FileInfo:
    """Represents a file with metadata and content.

    This class provides access to file metadata (path, size, etc.) and content,
    with caching support for efficient access. Implements the file-sequence protocol
    by being iterable (yields itself) while maintaining scalar access to properties.

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
        max_size: Optional[int] = None,
        strict_mode: bool = False,
        lazy_loading: bool = True,
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
            max_size: Maximum file size in bytes for lazy loading (uses environment default if None)
            strict_mode: If True, raise exceptions instead of returning fallback content
            lazy_loading: If True, enable lazy loading with size checks

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

        # LazyFileContent integration
        self.__max_size = (
            max_size or self._get_default_max_size() if lazy_loading else None
        )
        self.__strict_mode = strict_mode
        self.__lazy_loading = lazy_loading
        self.__size_checked = False
        self.__actual_size: Optional[int] = None
        self.__loaded = False

        # TSES v2.0 fields for alias tracking
        self.parent_alias: Optional[str] = (
            None  # CLI alias this file came from
        )
        self.relative_path: Optional[str] = (
            None  # Path relative to attachment root
        )
        self.base_path: Optional[str] = None  # Base path of attachment
        self.from_collection: bool = False  # Whether file came from --collect
        self.attachment_type: str = (
            "file"  # Original attachment type: "file", "dir", or "collection"
        )

        # For URL files, add is_url property
        self._is_url: bool = False

        logger.debug(
            "Creating FileInfo for path: %s, routing_type: %s",
            path,
            self.routing_type,
        )

        # Validate path – skip local checks for remote URLs
        if not path:
            raise ValueError("Path cannot be empty")

        if str(path).startswith(("http://", "https://")):
            # Remote URL – mark as such and bypass local filesystem validation
            self._is_url = True
            logger.debug(
                "Remote URL detected, skipping filesystem validation: %s", path
            )
            return

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

    def __iter__(self) -> Iterator["FileInfo"]:
        """Make FileInfo iterable by yielding itself.

        This implements the file-sequence protocol, allowing single files
        to be treated uniformly with file collections in templates.

        Returns:
            Iterator that yields this FileInfo instance
        """
        yield self

    @property
    def first(self) -> "FileInfo":
        """Get the first file in the sequence (itself for single files).

        This provides a uniform interface with FileInfoList.first,
        allowing templates to use .first regardless of whether they're
        dealing with a single file or a collection.

        Returns:
            This FileInfo instance
        """
        return self

    @property
    def is_collection(self) -> bool:
        """Indicate whether this is a collection of files.

        Returns:
            False, since FileInfo represents a single file
        """
        return False

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
            # Path is outside base_dir, check if it's allowed by enhanced security model
            try:
                if self.__security_manager.is_path_allowed_enhanced(abs_path):
                    logger.debug(
                        "Path outside base_dir but allowed, returning absolute path: %s",
                        abs_path,
                    )
                    return str(abs_path)
            except Exception:
                # In strict mode, is_path_allowed_enhanced() raises exceptions
                # If we reach this except block, the path is not allowed
                pass

            # Should never reach here if SecurityManager validation was done properly
            logger.error(
                "Error making path relative: %s is not within base directory %s",
                abs_path,
                base_dir,
            )
            raise ValueError(
                f"Path {abs_path} is not within base directory {base_dir}"
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
        if self.is_url:
            return None

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
        if self.is_url:
            return None

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
            TemplateBinaryError: If trying to access content of a user-data file
        """
        # Check for user-data files and block content access
        if self.routing_intent == FileRoutingIntent.USER_DATA:
            from .errors import TemplateBinaryError

            # Try to get the alias from parent_alias if available
            alias = getattr(self, "parent_alias", None) or "file"

            raise TemplateBinaryError(
                f"Cannot access .content on user-data file '{self.path}'. "
                f"User-data files are sent directly to vision models and not "
                f"included in the template text.",
                alias=alias,
            )

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
                f"consider using --file ci:data (Code Interpreter) or --file fs:docs (File Search) to optimize token usage, "
                f"cost, and avoid exceeding model context limits."
            )

        if self.__content is None:
            if self.__lazy_loading:
                try:
                    return self._load_content_with_size_check()
                except LazyLoadSizeError:
                    if self.__strict_mode:
                        raise  # Re-raise the exception in strict mode
                    return f"[File too large: {self.__actual_size:,} bytes > {self.__max_size:,} bytes]"
                except LazyLoadError as e:
                    if self.__strict_mode:
                        raise  # Re-raise the exception in strict mode
                    return f"[Error: {e}]"
            else:
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
    def is_url(self) -> bool:
        """Check if this is a URL file."""
        return self._is_url

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

    @property
    def basename(self) -> str:
        """Get the filename without directory path (alias for name)."""
        return self.name

    @property
    def dirname(self) -> str:
        """Get the directory name containing this file."""
        return str(Path(self.path).parent)

    @property
    def parent(self) -> str:
        """Get the parent directory path."""
        return str(Path(self.path).parent)

    @property
    def stem(self) -> str:
        """Get the filename without the final suffix."""
        return Path(self.path).stem

    @property
    def suffix(self) -> str:
        """Get the file suffix (extension) including the dot."""
        return Path(self.path).suffix

    @property
    def is_file(self) -> bool:
        """Check if this path points to a regular file."""
        if self.is_url:
            return True  # URL files are considered files
        try:
            return Path(self.abs_path).is_file()
        except (OSError, PathSecurityError):
            return False

    @property
    def is_dir(self) -> bool:
        """Check if this path points to a directory."""
        if self.is_url:
            return False  # URL files are never directories
        try:
            return Path(self.abs_path).is_dir()
        except (OSError, PathSecurityError):
            return False

    @staticmethod
    def _get_default_max_size() -> Optional[int]:
        """Get default max size from config or environment.

        Returns:
            Default maximum file size in bytes, or None for no limit
        """
        import os

        # Check OSTRUCT_TEMPLATE_FILE_LIMIT environment variable
        template_file_limit = os.getenv("OSTRUCT_TEMPLATE_FILE_LIMIT")
        if template_file_limit is not None:
            # Support semantic values: unlimited, none, empty string
            if template_file_limit.lower() in ("none", "unlimited", ""):
                return None
            try:
                return int(template_file_limit)
            except ValueError:
                logger.warning(
                    f"Invalid OSTRUCT_TEMPLATE_FILE_LIMIT value '{template_file_limit}', using default limit"
                )
                # Fall through to default

        # Check OSTRUCT_MAX_FILE_SIZE environment variable (new)
        max_file_size_env = os.getenv("OSTRUCT_MAX_FILE_SIZE")
        if max_file_size_env is not None:
            if max_file_size_env.lower() in ("none", "unlimited", ""):
                return None
            try:
                return int(max_file_size_env)
            except ValueError:
                logger.warning(
                    f"Invalid OSTRUCT_MAX_FILE_SIZE value '{max_file_size_env}', using default limit"
                )
                # Fall through to default

        # Default: 100MB limit for DoS protection
        try:
            from .constants import DefaultConfig

            default_size = DefaultConfig.TEMPLATE["max_file_size"]
            return int(default_size) if default_size is not None else None
        except (ImportError, AttributeError, KeyError):
            # Fallback if DefaultConfig is not available
            return 100 * 1024 * 1024  # 100MB

    def check_size(self) -> bool:
        """Check if file size is within limits.

        Returns:
            True if file size is acceptable

        Raises:
            LazyLoadError: If file cannot be accessed
        """
        if not self.__size_checked:
            try:
                self.__actual_size = Path(self.abs_path).stat().st_size
                self.__size_checked = True
            except OSError as e:
                raise LazyLoadError(f"Cannot access file {self.path}: {e}")

        # If max_size is None, there's no limit
        if self.__max_size is None:
            return True

        return (
            self.__actual_size is not None
            and self.__actual_size <= self.__max_size
        )

    @property
    def actual_size(self) -> Optional[int]:
        """Get the actual file size in bytes.

        Returns:
            File size in bytes, or None if not checked yet
        """
        if not self.__size_checked:
            try:
                self.check_size()
            except LazyLoadError:
                return None
        return self.__actual_size

    def _load_content_with_size_check(self) -> str:
        """Load file content with size checking for lazy loading.

        Returns:
            File content as string

        Raises:
            LazyLoadSizeError: If file exceeds size limits
            LazyLoadError: If file cannot be loaded
        """
        try:
            if not self.check_size():
                error_msg = (
                    f"File {self.path} ({self.__actual_size:,} bytes) "
                    f"exceeds size limit ({self.__max_size:,} bytes)"
                )
                logger.warning(error_msg)
                raise LazyLoadSizeError(error_msg)

            # Use the normal file reading logic
            self._read_file()
            self.__loaded = True
            logger.debug(
                f"Loaded content for {self.path} ({len(self.__content or ''):,} chars)"
            )
            return self.__content or ""

        except LazyLoadSizeError:
            # Re-raise size errors
            raise
        except Exception as e:
            logger.error(f"Failed to load content for {self.path}: {e}")
            raise LazyLoadError(f"Failed to load content for {self.path}: {e}")

    def load_safe(
        self, fallback_content: str = "[File too large or unavailable]"
    ) -> str:
        """Load content safely with fallback for oversized files.

        Args:
            fallback_content: Content to return if file cannot be loaded

        Returns:
            File content or fallback content

        Raises:
            LazyLoadSizeError: If file is too large and strict_mode is True
            LazyLoadError: If file cannot be loaded and strict_mode is True
        """
        if not self.__lazy_loading:
            # For non-lazy loading, just return content
            return self.content

        try:
            if not self.__loaded and self.__content is None:
                return self._load_content_with_size_check()
            return self.__content or ""
        except LazyLoadSizeError:
            if self.__strict_mode:
                raise  # Re-raise the exception in strict mode
            return f"[File too large: {self.__actual_size:,} bytes > {self.__max_size:,} bytes]"
        except LazyLoadError as e:
            if self.__strict_mode:
                raise  # Re-raise the exception in strict mode
            return f"[Error: {e}]"

    def preview(self, max_chars: int = 200) -> str:
        """Get content preview without full loading.

        Args:
            max_chars: Maximum characters to return

        Returns:
            Preview of file content
        """
        if self.__loaded and self.__content:
            return self.__content[:max_chars]

        try:
            # Try to read just the preview amount
            with open(
                self.abs_path, "r", encoding="utf-8", errors="replace"
            ) as f:
                return f.read(max_chars)
        except Exception as e:
            return f"[Preview error: {e}]"

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
        parent_alias: Optional[str] = None,
        relative_path: Optional[str] = None,
        base_path: Optional[str] = None,
        from_collection: bool = False,
        attachment_type: str = "file",
        max_size: Optional[int] = None,
        strict_mode: bool = False,
        lazy_loading: bool = True,
    ) -> "FileInfo":
        """Create FileInfo instance from path.

        Args:
            path: Path to file
            security_manager: Security manager for path validation
            routing_type: How the file was routed (e.g., 'template', 'code-interpreter')
            routing_intent: The intended use of the file in the pipeline
            parent_alias: CLI alias this file came from (for TSES)
            relative_path: Path relative to attachment root (for TSES)
            base_path: Base path of attachment (for TSES)
            from_collection: Whether file came from --collect (for TSES)
            attachment_type: Original attachment type: "file", "dir", or "collection" (for TSES)
            max_size: Maximum file size in bytes for lazy loading
            strict_mode: If True, raise exceptions instead of returning fallback content
            lazy_loading: If True, enable lazy loading with size checks

        Returns:
            FileInfo instance

        Raises:
            FileNotFoundError: If file does not exist
            PathSecurityError: If path is not allowed
        """
        file_info = cls(
            path,
            security_manager,
            routing_type=routing_type,
            routing_intent=routing_intent,
            max_size=max_size,
            strict_mode=strict_mode,
            lazy_loading=lazy_loading,
        )

        # Set TSES fields
        file_info.parent_alias = parent_alias
        file_info.relative_path = relative_path
        file_info.base_path = base_path
        file_info.from_collection = from_collection
        file_info.attachment_type = attachment_type

        return file_info

    def __str__(self) -> str:
        """String representation - for lazy loading, return content; otherwise return path."""
        if self.__lazy_loading:
            return self.content
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

        # Allow setting TSES fields
        if name in (
            "parent_alias",
            "relative_path",
            "base_path",
            "from_collection",
            "attachment_type",
        ):
            object.__setattr__(self, name, value)
            return

        # Allow setting _is_url at any time (idempotent)
        if name == "_is_url":
            object.__setattr__(self, name, value)
            return

        # Allow setting private attributes from internal methods or during initialization
        if name.startswith("_FileInfo__") and (
            self._is_internal_call() or not hasattr(self, "_FileInfo__path")
        ):
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

    def enable_lazy_loading(
        self, max_size: Optional[int] = None, strict_mode: bool = False
    ) -> "FileInfo":
        """Enable lazy loading on this FileInfo instance.

        Args:
            max_size: Maximum file size in bytes for lazy loading
            strict_mode: If True, raise exceptions instead of returning fallback content

        Returns:
            Self for method chaining
        """
        self.__max_size = max_size or self._get_default_max_size()
        self.__strict_mode = strict_mode
        self.__lazy_loading = True
        self.__size_checked = False
        self.__actual_size = None
        self.__loaded = False
        return self

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
