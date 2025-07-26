"""Shared Pydantic models for JSON output across CLI commands."""

from pydantic import BaseModel


class ErrorResult(BaseModel):
    """Standard error result for JSON output."""

    exit_code: int
    error: str


class FileNotFoundError(BaseModel):
    """Specific error for missing files."""

    exit_code: int = 9  # ExitCode.FILE_ERROR
    error: str
    file_path: str
    error_type: str = "file_not_found"


class DirectoryNotFoundError(BaseModel):
    """Specific error for missing directories."""

    exit_code: int = 9  # ExitCode.FILE_ERROR
    error: str
    directory_path: str
    error_type: str = "directory_not_found"


class PermissionError(BaseModel):
    """Specific error for permission denied."""

    exit_code: int = 9  # ExitCode.FILE_ERROR
    error: str
    file_path: str
    error_type: str = "permission_denied"


class BrokenSymlinkError(BaseModel):
    """Specific error for broken symlinks."""

    exit_code: int = 9  # ExitCode.FILE_ERROR
    error: str
    symlink_path: str
    target_path: str
    error_type: str = "broken_symlink"


class NoFilesMatchPatternError(BaseModel):
    """Specific error for glob patterns that match no files."""

    exit_code: int = 9  # ExitCode.FILE_ERROR
    error: str
    pattern: str
    error_type: str = "no_files_match_pattern"


class CollectionFileNotFoundError(BaseModel):
    """Specific error for missing collection files."""

    exit_code: int = 9  # ExitCode.FILE_ERROR
    error: str
    collection_file: str
    error_type: str = "collection_file_not_found"
