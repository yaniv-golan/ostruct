"""FileInfoList implementation providing smart file content access."""

from typing import List, Union

from .file_info import FileInfo


class FileInfoList(List[FileInfo]):
    """List of FileInfo objects with smart content access.

    This class extends List[FileInfo] to provide convenient access to file contents
    and metadata. When the list contains exactly one file from a single file mapping,
    properties like content return the value directly. For multiple files or directory
    mappings, properties return a list of values.

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
        super().__init__(files)
        self._from_dir = from_dir

    @property
    def content(self) -> Union[str, List[str]]:
        """Get the content of the file(s).

        Returns:
            Union[str, List[str]]: For a single file from file mapping, returns its content as a string.
                                  For multiple files or directory mapping, returns a list of contents.

        Raises:
            ValueError: If the list is empty
        """
        if not self:
            raise ValueError("No files in FileInfoList")
        if len(self) == 1 and not self._from_dir:
            return self[0].content
        return [f.content for f in self]

    @property
    def path(self) -> Union[str, List[str]]:
        """Get the path of the file(s).

        Returns:
            Union[str, List[str]]: For a single file from file mapping, returns its path as a string.
                                  For multiple files or directory mapping, returns a list of paths.

        Raises:
            ValueError: If the list is empty
        """
        if not self:
            raise ValueError("No files in FileInfoList")
        if len(self) == 1 and not self._from_dir:
            return self[0].path
        return [f.path for f in self]

    @property
    def abs_path(self) -> Union[str, List[str]]:
        """Get the absolute path of the file(s).

        Returns:
            Union[str, List[str]]: For a single file from file mapping, returns its absolute path as a string.
                                  For multiple files or directory mapping, returns a list of absolute paths.

        Raises:
            ValueError: If the list is empty
        """
        if not self:
            raise ValueError("No files in FileInfoList")
        if len(self) == 1 and not self._from_dir:
            return self[0].abs_path
        return [f.abs_path for f in self]

    @property
    def size(self) -> Union[int, List[int]]:
        """Get file size(s) in bytes.

        Returns:
            Union[int, List[int]]: For a single file from file mapping, returns its size in bytes.
                                  For multiple files or directory mapping, returns a list of sizes.

        Raises:
            ValueError: If the list is empty or if any file size is None
        """
        if not self:
            raise ValueError("No files in FileInfoList")

        # For single file not from directory, return its size
        if len(self) == 1 and not self._from_dir:
            size = self[0].size
            if size is None:
                raise ValueError(
                    f"Could not get size for file: {self[0].path}"
                )
            return size

        # For multiple files, collect all sizes
        sizes = []
        for f in self:
            size = f.size
            if size is None:
                raise ValueError(f"Could not get size for file: {f.path}")
            sizes.append(size)
        return sizes

    def __str__(self) -> str:
        """Get string representation of the file list.

        Returns:
            str: String representation in format FileInfoList([paths])
        """
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
