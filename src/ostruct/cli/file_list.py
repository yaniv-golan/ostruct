"""FileInfoList implementation providing smart file content access."""

import logging
import threading
from typing import Iterable, Iterator, List, SupportsIndex, Union, overload

from .file_info import FileInfo

__all__ = ["FileInfoList", "FileInfo"]

logger = logging.getLogger(__name__)


class FileInfoList(List[FileInfo]):
    """List of FileInfo objects with smart content access.

    This class extends List[FileInfo] to provide convenient access to file contents
    and metadata. When the list contains exactly one file from a single file mapping,
    properties like content return the value directly. For multiple files or directory
    mappings, properties return a list of values.

    This class is thread-safe. All operations that access or modify the internal list
    are protected by a reentrant lock (RLock). This allows nested method calls while
    holding the lock, preventing deadlocks in cases like:
        content property → __len__ → lock
        content property → __getitem__ → lock

    Examples:
        Single file (--file):
            files = FileInfoList([file_info], from_dir=False)
            content = files.content  # Returns "file contents"

        Multiple files or directory (--files or --dir):
            files = FileInfoList([file1, file2])  # or FileInfoList([file1], from_dir=True)
            content = files.content  # Returns ["contents1", "contents2"] or ["contents1"]

        Backward compatibility:
            content = files[0].content  # Still works

    Properties:
        content: File content(s) - string for single file mapping, list for multiple files or directory
        path: File path(s)
        abs_path: Absolute file path(s)
        size: File size(s) in bytes

    Raises:
        ValueError: When accessing properties on an empty list
    """

    def __init__(self, files: List[FileInfo], from_dir: bool = False) -> None:
        """Initialize FileInfoList.

        Args:
            files: List of FileInfo objects
            from_dir: Whether this list was created from a directory mapping
        """
        logger.debug(
            "Creating FileInfoList with %d files, from_dir=%s",
            len(files),
            from_dir,
        )
        self._lock = threading.RLock()  # Use RLock for nested method calls
        super().__init__(files)
        self._from_dir = from_dir

    @property
    def content(self) -> Union[str, List[str]]:
        """Get the content of the file(s).

        Returns:
            Union[str, List[str]]: For a single file from file mapping, returns its content as a string.
                                  For multiple files, directory mapping, or empty list, returns a list of contents.
        """
        # Take snapshot under lock
        with self._lock:
            if not self:
                logger.debug("FileInfoList.content called but list is empty")
                return []

            # Make a copy of the files we need to access
            if len(self) == 1 and not self._from_dir:
                file_info = self[0]
                is_single = True
            else:
                files = list(self)
                is_single = False

        # Access file contents outside lock to prevent deadlocks
        try:
            if is_single:
                logger.debug(
                    "FileInfoList.content returning single file content (not from dir)"
                )
                return file_info.content

            logger.debug(
                "FileInfoList.content returning list of %d contents (from_dir=%s)",
                len(files),
                self._from_dir,
            )
            return [f.content for f in files]
        except Exception as e:
            logger.error("Error accessing file content: %s", e)
            raise

    @property
    def path(self) -> Union[str, List[str]]:
        """Get the path of the file(s).

        Returns:
            Union[str, List[str]]: For a single file from file mapping, returns its path as a string.
                                  For multiple files, directory mapping, or empty list, returns a list of paths.
        """
        # First get a snapshot of the list state under the lock
        with self._lock:
            if not self:
                return []
            if len(self) == 1 and not self._from_dir:
                file_info = self[0]
                is_single = True
            else:
                files = list(self)
                is_single = False

        # Now access file paths outside the lock
        try:
            if is_single:
                return file_info.path
            return [f.path for f in files]
        except Exception as e:
            logger.error("Error accessing file path: %s", e)
            raise

    @property
    def abs_path(self) -> Union[str, List[str]]:
        """Get the absolute path of the file(s).

        Returns:
            Union[str, List[str]]: For a single file from file mapping, returns its absolute path as a string.
                                  For multiple files or directory mapping, returns a list of absolute paths.

        Raises:
            ValueError: If the list is empty
        """
        # First get a snapshot of the list state under the lock
        with self._lock:
            if not self:
                raise ValueError("No files in FileInfoList")
            if len(self) == 1 and not self._from_dir:
                file_info = self[0]
                is_single = True
            else:
                files = list(self)
                is_single = False

        # Now access file paths outside the lock
        try:
            if is_single:
                return file_info.abs_path
            return [f.abs_path for f in files]
        except Exception as e:
            logger.error("Error accessing absolute path: %s", e)
            raise

    @property
    def size(self) -> Union[int, List[int]]:
        """Get file size(s) in bytes.

        Returns:
            Union[int, List[int]]: For a single file from file mapping, returns its size in bytes.
                                  For multiple files or directory mapping, returns a list of sizes.

        Raises:
            ValueError: If the list is empty or if any file size is None
        """
        # First get a snapshot of the list state under the lock
        with self._lock:
            if not self:
                raise ValueError("No files in FileInfoList")

            # Make a copy of the files we need to access
            if len(self) == 1 and not self._from_dir:
                file_info = self[0]
                is_single = True
            else:
                files = list(self)
                is_single = False

        # Now access file sizes outside the lock
        try:
            if is_single:
                size = file_info.size
                if size is None:
                    raise ValueError(
                        f"Could not get size for file: {file_info.path}"
                    )
                return size

            sizes = []
            for f in files:
                size = f.size
                if size is None:
                    raise ValueError(f"Could not get size for file: {f.path}")
                sizes.append(size)
            return sizes
        except Exception as e:
            logger.error("Error accessing file size: %s", e)
            raise

    def __str__(self) -> str:
        """Get string representation of the file list.

        Returns:
            str: String representation in format FileInfoList([paths])
        """
        with self._lock:
            if not self:
                return "FileInfoList([])"
            if len(self) == 1:
                return f"FileInfoList(['{self[0].path}'])"
            return f"FileInfoList({[f.path for f in self]})"

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
