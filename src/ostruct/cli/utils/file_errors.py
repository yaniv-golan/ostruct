"""File-specific exception classes for ostruct CLI."""

import os
from pathlib import Path
from typing import Optional

from ..exit_codes import ExitCode


class FileError(Exception):
    """Base exception for file-related errors."""

    def __init__(self, message: str, exit_code: int = ExitCode.FILE_ERROR):
        super().__init__(message)
        self.exit_code = exit_code


class FileNotFoundError(FileError):
    """Exception for missing files."""

    def __init__(self, file_path: str):
        self.file_path = str(file_path)
        super().__init__(f"File not found: {self.file_path}")


class DirectoryNotFoundError(FileError):
    """Exception for missing directories."""

    def __init__(self, directory_path: str):
        self.directory_path = str(directory_path)
        super().__init__(f"Directory not found: {self.directory_path}")


class NotADirectoryError(FileError):
    """Exception for paths that exist but are not directories."""

    def __init__(self, path: str):
        self.path = str(path)
        super().__init__(f"Path is not a directory: {self.path}")


class FilePermissionError(FileError):
    """Exception for permission denied errors."""

    def __init__(self, file_path: str):
        self.file_path = str(file_path)
        super().__init__(f"Permission denied: {self.file_path}")


class BrokenSymlinkError(FileError):
    """Exception for broken symlinks."""

    def __init__(self, symlink_path: str, target_path: Optional[str] = None):
        self.symlink_path = str(symlink_path)
        self.target_path = target_path

        if target_path:
            message = f"Broken symlink: {self.symlink_path} -> {target_path}"
        else:
            message = f"Broken symlink: {self.symlink_path}"

        super().__init__(message)


class NoFilesMatchPatternError(FileError):
    """Exception for glob patterns that match no files."""

    def __init__(self, pattern: str):
        self.pattern = pattern
        super().__init__(f"No files match pattern: {pattern}")


class CollectionFileNotFoundError(FileError):
    """Exception for missing collection files."""

    def __init__(self, collection_file: str):
        self.collection_file = str(collection_file)
        super().__init__(f"Collection file not found: {collection_file}")


class FileFromCollectionNotFoundError(FileError):
    """Exception for missing files referenced in collection."""

    def __init__(self, file_path: str, collection_file: str):
        self.file_path = str(file_path)
        self.collection_file = str(collection_file)
        super().__init__(
            f"File not found (from collection {collection_file}): {file_path}"
        )


def validate_file_exists(file_path: Path) -> None:
    """Validate that a file exists and is readable.

    Args:
        file_path: Path to validate

    Raises:
        FileNotFoundError: If file doesn't exist
        FilePermissionError: If file exists but is not readable
        BrokenSymlinkError: If file is a broken symlink
    """
    if file_path.is_symlink():
        # Check if symlink target exists
        try:
            target = file_path.resolve()
            if not target.exists():
                raise BrokenSymlinkError(str(file_path), str(target))
        except (OSError, RuntimeError):
            # resolve() can fail for deeply nested or circular symlinks
            raise BrokenSymlinkError(str(file_path))

    if not file_path.exists():
        raise FileNotFoundError(str(file_path))

    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        raise FilePermissionError(str(file_path))


def validate_directory_exists(dir_path: Path) -> None:
    """Validate that a directory exists and is readable.

    Args:
        dir_path: Directory path to validate

    Raises:
        DirectoryNotFoundError: If directory doesn't exist
        NotADirectoryError: If path exists but is not a directory
        FilePermissionError: If directory exists but is not readable
    """
    if not dir_path.exists():
        raise DirectoryNotFoundError(str(dir_path))

    if not dir_path.is_dir():
        raise NotADirectoryError(str(dir_path))

    # Check if directory is readable
    if not os.access(dir_path, os.R_OK):
        raise FilePermissionError(str(dir_path))


def validate_collection_file_exists(collection_path: Path) -> None:
    """Validate that a collection file exists and is readable.

    Args:
        collection_path: Path to collection file

    Raises:
        CollectionFileNotFoundError: If collection file doesn't exist
        FilePermissionError: If collection file exists but is not readable
    """
    if not collection_path.exists():
        raise CollectionFileNotFoundError(str(collection_path))

    # Check if file is readable
    if not os.access(collection_path, os.R_OK):
        raise FilePermissionError(str(collection_path))
