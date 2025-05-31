"""FileInfoList implementation providing smart file content access."""

import logging
import threading
from typing import (
    Iterable,
    Iterator,
    List,
    Optional,
    SupportsIndex,
    Union,
    overload,
)

from .file_info import FileInfo

__all__ = ["FileInfoList", "FileInfo"]

logger = logging.getLogger(__name__)


class FileInfoList(List[FileInfo]):
    """List of FileInfo objects with strict single-file content access.

    This class extends List[FileInfo] to provide convenient access to file contents
    and metadata. Properties like content, path, name, etc. are designed for single-file
    access only and will raise ValueError for multiple files or directory mappings.

    This prevents accidental data exposure and template errors by requiring explicit
    handling of multi-file scenarios through indexing (files[0].content) or the
    |single filter (files|single.content).

    This class is thread-safe. All operations that access or modify the internal list
    are protected by a reentrant lock (RLock). This allows nested method calls while
    holding the lock, preventing deadlocks in cases like:
        content property → __len__ → lock
        content property → __getitem__ → lock

    Examples:
        Single file (--file):
            files = FileInfoList([file_info], from_dir=False)
            content = files.content  # Returns "file contents"

        Multiple files or directory (raises error):
            files = FileInfoList([file1, file2])  # or FileInfoList([file1], from_dir=True)
            content = files.content  # Raises ValueError with helpful message

        Safe multi-file access:
            content = files[0].content  # Access first file explicitly
            content = files|single.content  # Use |single filter for validation

    Properties:
        content: File content - only for single file from file mapping (not directory)
        path: File path - only for single file from file mapping
        abs_path: Absolute file path - only for single file from file mapping
        size: File size in bytes - only for single file from file mapping
        name: Filename without directory path - only for single file from file mapping
        names: Always returns list of all filenames (safe for multi-file access)

    Raises:
        ValueError: When accessing scalar properties on empty list, multiple files, or directory mappings
    """

    def __init__(
        self,
        files: List[FileInfo],
        from_dir: bool = False,
        var_alias: Optional[str] = None,
    ) -> None:
        """Initialize FileInfoList.

        Args:
            files: List of FileInfo objects
            from_dir: Whether this list was created from a directory mapping
            var_alias: Variable name used in template (for error messages)
        """
        logger.debug(
            "Creating FileInfoList with %d files, from_dir=%s, var_alias=%s",
            len(files),
            from_dir,
            var_alias,
        )
        self._lock = threading.RLock()  # Use RLock for nested method calls
        super().__init__(files)
        self._from_dir = from_dir
        self._var_alias = var_alias

    @property
    def content(self) -> str:
        """Get the content of a single file.

        Returns:
            str: Content of the single file from file mapping.

        Raises:
            ValueError: If the list is empty or contains multiple files.
        """
        # Take snapshot under lock
        with self._lock:
            if not self:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"No files in '{var_name}'. Cannot access .content property."
                )

            # Check for multiple files or directory mapping
            if len(self) > 1:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains {len(self)} files. "
                    f"Use '{{{{ {var_name}[0].content }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.content }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.content }}}}{{%% endfor %%}}'."
                )

            if self._from_dir:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains files from directory mapping. "
                    f"Use '{{{{ {var_name}[0].content }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.content }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.content }}}}{{%% endfor %%}}'."
                )

            # Single file from file mapping
            file_info = self[0]

        # Access file content outside lock to prevent deadlocks
        try:
            logger.debug(
                "FileInfoList.content returning single file content (not from dir)"
            )
            return file_info.content
        except Exception as e:
            logger.error("Error accessing file content: %s", e)
            raise

    @property
    def path(self) -> str:
        """Get the path of a single file.

        Returns:
            str: Path of the single file from file mapping.

        Raises:
            ValueError: If the list is empty or contains multiple files.
        """
        # First get a snapshot of the list state under the lock
        with self._lock:
            if not self:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"No files in '{var_name}'. Cannot access .path property."
                )

            # Check for multiple files or directory mapping
            if len(self) > 1:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains {len(self)} files. "
                    f"Use '{{{{ {var_name}[0].path }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.path }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.path }}}}{{%% endfor %%}}'."
                )

            if self._from_dir:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains files from directory mapping. "
                    f"Use '{{{{ {var_name}[0].path }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.path }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.path }}}}{{%% endfor %%}}'."
                )

            # Single file from file mapping
            file_info = self[0]

        # Now access file path outside the lock
        try:
            return file_info.path
        except Exception as e:
            logger.error("Error accessing file path: %s", e)
            raise

    @property
    def abs_path(self) -> str:
        """Get the absolute path of a single file.

        Returns:
            str: Absolute path of the single file from file mapping.

        Raises:
            ValueError: If the list is empty or contains multiple files.
        """
        # First get a snapshot of the list state under the lock
        with self._lock:
            if not self:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"No files in '{var_name}'. Cannot access .abs_path property."
                )

            # Check for multiple files or directory mapping
            if len(self) > 1:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains {len(self)} files. "
                    f"Use '{{{{ {var_name}[0].abs_path }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.abs_path }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.abs_path }}}}{{%% endfor %%}}'."
                )

            if self._from_dir:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains files from directory mapping. "
                    f"Use '{{{{ {var_name}[0].abs_path }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.abs_path }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.abs_path }}}}{{%% endfor %%}}'."
                )

            # Single file from file mapping
            file_info = self[0]

        # Now access file path outside the lock
        try:
            return file_info.abs_path
        except Exception as e:
            logger.error("Error accessing absolute path: %s", e)
            raise

    @property
    def size(self) -> int:
        """Get file size of a single file in bytes.

        Returns:
            int: Size of the single file from file mapping in bytes.

        Raises:
            ValueError: If the list is empty, contains multiple files, or file size is None.
        """
        # First get a snapshot of the list state under the lock
        with self._lock:
            if not self:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"No files in '{var_name}'. Cannot access .size property."
                )

            # Check for multiple files or directory mapping
            if len(self) > 1:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains {len(self)} files. "
                    f"Use '{{{{ {var_name}[0].size }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.size }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.size }}}}{{%% endfor %%}}'."
                )

            if self._from_dir:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains files from directory mapping. "
                    f"Use '{{{{ {var_name}[0].size }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.size }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.size }}}}{{%% endfor %%}}'."
                )

            # Single file from file mapping
            file_info = self[0]

        # Now access file size outside the lock
        try:
            size = file_info.size
            if size is None:
                raise ValueError(
                    f"Could not get size for file: {file_info.path}"
                )
            return size
        except Exception as e:
            logger.error("Error accessing file size: %s", e)
            raise

    @property
    def name(self) -> str:
        """Get the filename of a single file without directory path.

        Returns:
            str: Name of the single file from file mapping.

        Raises:
            ValueError: If the list is empty or contains multiple files.
        """
        with self._lock:
            if not self:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"No files in '{var_name}'. Cannot access .name property."
                )

            # Check for multiple files or directory mapping
            if len(self) > 1:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains {len(self)} files. "
                    f"Use '{{{{ {var_name}[0].name }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.name }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.name }}}}{{%% endfor %%}}'."
                )

            if self._from_dir:
                var_name = self._var_alias or "file_list"
                raise ValueError(
                    f"'{var_name}' contains files from directory mapping. "
                    f"Use '{{{{ {var_name}[0].name }}}}' for the first file, "
                    f"'{{{{ {var_name}|single.name }}}}' if expecting exactly one file, "
                    f"or loop over files with '{{%% for file in {var_name} %%}}{{{{ file.name }}}}{{%% endfor %%}}'."
                )

            # Single file from file mapping
            return self[0].name

    @property
    def names(self) -> List[str]:
        """Get all filenames as a list."""
        with self._lock:
            if not self:
                return []
            try:
                return [f.name for f in self]
            except Exception as e:
                logger.error(
                    f"Error accessing file names for .names property in '{self._var_alias or 'FileInfoList'}': {e}"
                )
                raise

    def __getattr__(self, attr_name: str) -> None:
        """Provide helpful error messages for FileInfo attributes accessed on multi-file lists."""
        # Import here to avoid circular imports
        try:
            from .template_schema import FileInfoProxy

            # Try to get _valid_attrs as a class attribute, but it's actually an instance attribute
            # So we'll get an empty set and fall back to our hardcoded list
            valid_attrs = getattr(FileInfoProxy, "_valid_attrs", None)
            if not valid_attrs:
                # Use the same attributes that FileInfoProxy uses
                valid_attrs = {
                    "name",
                    "path",
                    "content",
                    "ext",
                    "basename",
                    "dirname",
                    "abs_path",
                    "exists",
                    "is_file",
                    "is_dir",
                    "size",
                    "mtime",
                    "encoding",
                    "hash",
                    "extension",
                    "parent",
                    "stem",
                    "suffix",
                }
        except ImportError:
            # Fallback list of common FileInfo attributes
            valid_attrs = {
                "name",
                "path",
                "content",
                "size",
                "abs_path",
                "exists",
                "encoding",
                "hash",
            }

        # Only provide enhanced errors for known FileInfo attributes
        if attr_name in valid_attrs:
            # Check if this is a non-scalar list trying to access FileInfo attributes
            if len(self) != 1 or self._from_dir:
                var_name = getattr(self, "_var_alias", None) or "file_list"
                raise AttributeError(
                    f"'{var_name}' contains {len(self)} files. "
                    f"Use '{{{{ {var_name}[0].{attr_name} }}}}' for the first file, "
                    f"or '{{{{ {var_name}|single.{attr_name} }}}}' if expecting exactly one file."
                )

        # Let the default AttributeError occur for truly missing attributes
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{attr_name}'"
        )

    def __str__(self) -> str:
        """Get string representation of the file list.

        Returns:
            str: Helpful guidance message for template usage
        """
        with self._lock:
            if not self:
                return "FileInfoList([])"

            # For single file from file mapping (--fta, -ft, etc.)
            if len(self) == 1 and not self._from_dir:
                var_name = self._var_alias or "file_var"
                return f"[File '{self[0].path}' - Use {{ {var_name}.content }} to access file content]"

            # For multiple files or directory mapping
            var_name = self._var_alias or "file_list"
            if len(self) == 1:
                return f"[Directory file '{self[0].path}' - Use {{ {var_name}[0].content }} or {{ {var_name}|single.content }} to access content]"
            else:
                paths_preview = [f.path for f in self[:2]]
                if len(self) > 2:
                    paths_preview.append(f"... +{len(self) - 2} more")
                return f"[{len(self)} files: {', '.join(paths_preview)} - Use {{ {var_name}[0].content }} or loop over files]"

    def __repr__(self) -> str:
        """Get detailed string representation of the file list.

        Returns:
            str: Same as str() for consistency
        """
        return str(self)

    def __iter__(self) -> Iterator[FileInfo]:
        """Return iterator over files."""
        with self._lock:
            # Create a copy of the list to avoid concurrent modification issues
            items = list(super().__iter__())
        logger.debug(
            "Starting iteration over FileInfoList with %d files", len(items)
        )
        return iter(items)

    def __len__(self) -> int:
        """Return number of files."""
        with self._lock:
            return super().__len__()

    def __bool__(self) -> bool:
        """Return True if there are files."""
        with self._lock:
            return super().__len__() > 0

    @overload
    def __getitem__(self, index: SupportsIndex, /) -> FileInfo: ...

    @overload
    def __getitem__(self, index: slice, /) -> "FileInfoList": ...

    def __getitem__(
        self, index: Union[SupportsIndex, slice], /
    ) -> Union[FileInfo, "FileInfoList"]:
        """Get file at index.

        This method is thread-safe and handles both integer indexing and slicing.
        For slicing, it ensures the result is always converted to a list before
        creating a new FileInfoList instance.
        """
        with self._lock:
            logger.debug("Getting file at index %s", index)
            result = super().__getitem__(index)
            if isinstance(index, slice):
                # Always convert to list to handle any sequence type
                # Cast to Iterable[FileInfo] to satisfy mypy
                result_list = list(
                    result if isinstance(result, list) else [result]
                )
                return FileInfoList(result_list, self._from_dir)
            if not isinstance(result, FileInfo):
                raise TypeError(
                    f"Expected FileInfo from index, got {type(result)}"
                )
            return result

    def append(self, value: FileInfo) -> None:
        """Append a FileInfo object to the list."""
        with self._lock:
            super().append(value)

    def extend(self, values: Iterable[FileInfo]) -> None:
        """Extend the list with FileInfo objects.

        Args:
            values: Iterable of FileInfo objects to add
        """
        with self._lock:
            super().extend(values)

    def insert(self, index: SupportsIndex, value: FileInfo) -> None:
        """Insert a FileInfo object at the given index.

        Args:
            index: Position to insert at
            value: FileInfo object to insert
        """
        with self._lock:
            super().insert(index, value)

    def pop(self, index: SupportsIndex = -1) -> FileInfo:
        """Remove and return item at index (default last).

        Args:
            index: Position to remove from (default: -1 for last item)

        Returns:
            The removed FileInfo object
        """
        with self._lock:
            return super().pop(index)

    def remove(self, value: FileInfo) -> None:
        """Remove first occurrence of value."""
        with self._lock:
            super().remove(value)

    def clear(self) -> None:
        """Remove all items from list."""
        with self._lock:
            super().clear()
