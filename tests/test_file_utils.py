"""Tests for file utilities."""

import logging
import os

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.errors import FileNotFoundError, PathSecurityError
from ostruct.cli.file_info import FileInfo
from ostruct.cli.file_list import FileInfoList
from ostruct.cli.file_utils import (
    collect_files,
    collect_files_from_directory,
    collect_files_from_pattern,
)
from ostruct.cli.security import SecurityManager


def test_file_info_creation(fs: FakeFilesystem) -> None:
    """Test FileInfo creation and properties."""
    # Create test file
    fs.create_file("test.txt", contents="test content")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Create FileInfo instance
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Check basic properties
    assert os.path.basename(file_info.path) == "test.txt"
    assert file_info.path == "test.txt"
    assert file_info.abs_path == os.path.abspath("test.txt")
    assert file_info.extension == "txt"

    # Check initial state
    assert isinstance(file_info.size, int)
    assert isinstance(file_info.mtime, float)
    assert file_info.encoding is not None
    assert file_info.hash is not None

    # Content should be available immediately
    assert file_info.content == "test content"


def test_file_info_cache_update(fs: FakeFilesystem) -> None:
    """Test cache update mechanism."""
    fs.create_file("test.txt", contents="test content")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Update from cache
    cached_content = "cached content"
    file_info.update_cache(
        content=cached_content, encoding="utf-8", hash_value="test_hash"
    )

    # Check updated values
    assert file_info.content == cached_content
    assert file_info.encoding == "utf-8"
    assert file_info.hash == "test_hash"


def test_file_info_property_protection(fs: FakeFilesystem) -> None:
    """Test that private fields cannot be set directly."""
    fs.create_file("test.txt", contents="test content")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Attempt to modify private fields should raise AttributeError
    with pytest.raises(AttributeError):
        file_info.__path = "modified.txt"

    with pytest.raises(AttributeError):
        file_info.__content = "modified content"

    with pytest.raises(AttributeError):
        file_info.__security_manager = SecurityManager(
            base_dir=os.getcwd()
        )  # Fix type error by providing valid SecurityManager


def test_file_info_directory_traversal(fs: FakeFilesystem) -> None:
    """Test FileInfo protection against directory traversal."""
    # Set up directory structure
    fs.create_dir("/base")
    fs.create_file("/base/test.txt", contents="test")
    fs.create_file("/outside/test.txt", contents="test")

    # Change to base directory
    os.chdir("/base")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Try to access file outside base directory
    with pytest.raises(
        PathSecurityError,
        match="Access denied: .* is outside base directory and not in allowed directories",
    ):
        FileInfo.from_path(
            "../outside/test.txt", security_manager=security_manager
        )

    # Try to collect files from outside directory
    with pytest.raises(
        PathSecurityError,
        match="Access denied: .* is outside base directory and not in allowed directories",
    ):
        collect_files(
            file_mappings=["test=../outside/test.txt"],
            security_manager=security_manager,
        )


def test_file_info_missing_file(fs: FakeFilesystem) -> None:
    """Test FileInfo handling of missing files."""
    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    with pytest.raises(
        FileNotFoundError, match="File not found: nonexistent.txt"
    ):
        FileInfo.from_path(
            "nonexistent.txt", security_manager=security_manager
        )


def test_collect_files_from_pattern(fs: FakeFilesystem) -> None:
    """Test collecting files using glob patterns."""
    # Create test files
    fs.create_file("test1.py", contents="test1")
    fs.create_file("test2.py", contents="test2")
    fs.create_file("test.txt", contents="test")
    fs.create_file("subdir/test3.py", contents="test3")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Test basic pattern
    files = collect_files_from_pattern(
        "*.py", security_manager=security_manager
    )
    assert len(files) == 2
    assert {f.path for f in files} == {"test1.py", "test2.py"}

    # Test recursive pattern
    files = collect_files_from_pattern(
        "**/*.py", security_manager=security_manager
    )
    assert len(files) == 3
    assert {f.path for f in files} == {
        "test1.py",
        "test2.py",
        "subdir/test3.py",
    }


def test_collect_files_from_directory(fs: FakeFilesystem) -> None:
    """Test collecting files from directory."""
    # Create test files
    fs.create_file("dir/test1.py", contents="test1")
    fs.create_file("dir/test2.py", contents="test2")
    fs.create_file("dir/test.txt", contents="test")
    fs.create_file("dir/subdir/test3.py", contents="test3")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Test non-recursive collection
    files = collect_files_from_directory(
        directory="dir", security_manager=security_manager
    )
    assert len(files) == 3
    assert {f.path for f in files} == {
        "dir/test1.py",
        "dir/test2.py",
        "dir/test.txt",
    }

    # Test recursive collection
    files = collect_files_from_directory(
        directory="dir", security_manager=security_manager, recursive=True
    )
    assert len(files) == 4
    assert {f.path for f in files} == {
        "dir/test1.py",
        "dir/test2.py",
        "dir/test.txt",
        "dir/subdir/test3.py",
    }

    # Test with extension filter
    files = collect_files_from_directory(
        directory="dir",
        security_manager=security_manager,
        recursive=True,
        allowed_extensions=["py"],
    )
    assert len(files) == 3
    assert {f.path for f in files} == {
        "dir/test1.py",
        "dir/test2.py",
        "dir/subdir/test3.py",
    }


def test_collect_files(fs: FakeFilesystem) -> None:
    """Test collecting files from multiple sources."""
    # Create test files
    fs.create_file("single.txt", contents="single")
    fs.create_file("test1.py", contents="test1")
    fs.create_file("test2.py", contents="test2")
    fs.create_file("dir/test3.py", contents="test3")
    fs.create_file("dir/test4.py", contents="test4")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Test collecting single file
    result = collect_files(
        file_mappings=["single=single.txt"], security_manager=security_manager
    )
    assert len(result) == 1
    assert "single" in result
    assert isinstance(result["single"], FileInfoList)
    assert result["single"].content == "single"  # Test direct content access
    assert (
        result["single"][0].content == "single"
    )  # Test backward compatibility
    assert result["single"].path == "single.txt"

    # Test collecting from pattern
    result = collect_files(
        pattern_mappings=["tests=*.py"], security_manager=security_manager
    )
    assert len(result) == 1
    assert "tests" in result
    assert isinstance(result["tests"], FileInfoList)
    assert len(result["tests"]) == 2
    assert {f.path for f in result["tests"]} == {"test1.py", "test2.py"}

    # Test collecting from directory
    result = collect_files(
        dir_mappings=["dir=dir"], security_manager=security_manager
    )
    assert len(result) == 1
    assert "dir" in result
    assert isinstance(result["dir"], FileInfoList)
    assert len(result["dir"]) == 2
    assert {f.path for f in result["dir"]} == {"dir/test3.py", "dir/test4.py"}

    # Test collecting from directory with extension filter
    result = collect_files(
        dir_mappings=["dir=dir"],
        dir_recursive=True,
        dir_extensions=["py"],
        security_manager=security_manager,
    )
    assert len(result) == 1
    assert "dir" in result
    assert isinstance(result["dir"], FileInfoList)
    assert len(result["dir"]) == 2
    assert {f.path for f in result["dir"]} == {"dir/test3.py", "dir/test4.py"}


def test_collect_files_errors(fs: FakeFilesystem) -> None:
    """Test error handling in collect_files."""
    # Set up directory structure
    fs.create_dir("/base")
    fs.create_dir("/outside")
    fs.create_file("/outside/test.txt", contents="test")
    os.chdir("/base")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Test invalid file mapping
    with pytest.raises(
        ValueError, match="Invalid file mapping format.*missing '=' separator"
    ):
        collect_files(
            file_mappings=["test"], security_manager=security_manager
        )

    # Test missing file
    with pytest.raises(FileNotFoundError):
        collect_files(
            file_mappings=["test=nonexistent.txt"],
            security_manager=security_manager,
        )

    # Test directory traversal
    with pytest.raises(
        PathSecurityError,
        match="Directory mapping error: Access denied: .* is outside base directory and not in allowed directories",
    ):
        collect_files(
            dir_mappings=["test=../outside"], security_manager=security_manager
        )


def test_file_info_stats_loading(fs: FakeFilesystem) -> None:
    """Test that file stats are loaded with content."""
    fs.create_file("test.txt", contents="test content")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Create FileInfo instance
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Check that stats are loaded
    size = file_info.size
    mtime = file_info.mtime
    assert size is not None and size > 0
    assert mtime is not None and mtime > 0


def test_file_info_stats_security(fs: FakeFilesystem) -> None:
    """Test security checks when loading stats."""
    # Set up directory structure
    fs.create_dir("/base")
    fs.create_file("/base/test.txt", contents="test")
    fs.create_file("/outside/test.txt", contents="test")

    # Change to base directory
    os.chdir("/base")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Create FileInfo for file outside base directory
    with pytest.raises(
        PathSecurityError,
        match="Access denied: .* is outside base directory and not in allowed directories",
    ):
        FileInfo.from_path(
            "../outside/test.txt", security_manager=security_manager
        )


def test_file_info_missing_file_stats(fs: FakeFilesystem) -> None:
    """Test stats loading for missing file."""
    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    with pytest.raises(FileNotFoundError, match="File not found"):
        FileInfo.from_path(
            "nonexistent.txt", security_manager=security_manager
        )


def test_file_info_content_errors(fs: FakeFilesystem) -> None:
    """Test error handling in content loading."""
    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Test with missing file
    with pytest.raises(FileNotFoundError):
        FileInfo.from_path(
            "nonexistent.txt", security_manager=security_manager
        )


def test_security_error_single_message(
    caplog: pytest.LogCaptureFixture, fs: FakeFilesystem
) -> None:
    """Test that security errors are logged only once with complete information."""
    # Set up test environment
    fs.create_dir("/base")
    fs.create_file("/outside/test.txt", contents="test")
    os.chdir("/base")

    # Configure logging to capture all levels
    caplog.set_level(logging.DEBUG)  # Capture all log levels
    logger = logging.getLogger("ostruct")
    logger.setLevel(
        logging.DEBUG
    )  # Ensure logger level is set to capture all messages

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Attempt to access file outside allowed directory
    with pytest.raises(PathSecurityError):
        FileInfo.from_path(
            "../outside/test.txt", security_manager=security_manager
        )

    # Check that error was logged only once
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_logs) == 1
    assert "Access denied" in error_logs[0].message
    assert "../outside/test.txt" in error_logs[0].message


def test_security_error_with_allowed_dirs(
    caplog: pytest.LogCaptureFixture, fs: FakeFilesystem
) -> None:
    """Test that security error message includes allowed directories."""
    # Set up test environment
    fs.create_dir("/base")
    fs.create_dir("/allowed")
    fs.create_file("/outside/test.txt", contents="test")
    os.chdir("/base")

    # Configure logging to capture all levels
    caplog.set_level(logging.ERROR)

    # Create security manager with allowed directories
    security_manager = SecurityManager(
        base_dir=os.getcwd(), allowed_dirs=["/allowed"]
    )

    # Attempt to access file with allowed directories specified
    with pytest.raises(PathSecurityError) as exc:
        FileInfo.from_path(
            "../outside/test.txt", security_manager=security_manager
        )

    # Check that error message includes allowed directories
    assert "/allowed" in str(exc.value)


def test_security_error_expanded_paths(fs: FakeFilesystem) -> None:
    """Test security error handling with expanded paths."""
    # Create test error with expanded paths
    error = PathSecurityError.from_expanded_paths(
        original_path="~/test.txt",
        expanded_path="/home/user/test.txt",
        base_dir="/base",
        allowed_dirs=["/allowed"],
        error_logged=True,
    )

    # Verify error message contains all components
    error_msg = str(error)
    assert "~/test.txt" in error_msg
    assert "/home/user/test.txt" in error_msg
    assert "Base directory: /base" in error_msg
    assert "Allowed directories: ['/allowed']" in error_msg
    assert error.error_logged is True


def test_security_error_format_with_context() -> None:
    """Test formatting security error with additional context."""
    # Create basic error
    error = PathSecurityError("Access denied: test.txt")

    # Format with context
    formatted = error.format_with_context(
        original_path="~/test.txt",
        expanded_path="/home/user/test.txt",
        base_dir="/base",
        allowed_dirs=["/allowed"],
    )

    # Verify formatted message contains all components
    assert "Original path: ~/test.txt" in formatted
    assert "Expanded path: /home/user/test.txt" in formatted
    assert "Base directory: /base" in formatted
    assert "Allowed directories: ['/allowed']" in formatted
    assert "Use --allowed-dir" in formatted


def test_security_error_attributes() -> None:
    """Test PathSecurityError attributes and properties."""
    error = PathSecurityError("Access denied", error_logged=True)
    assert error.has_been_logged
    assert not error.wrapped
    assert str(error) == "Access denied"


def test_security_error_wrapping() -> None:
    """Test error wrapping with context preservation."""
    original = PathSecurityError("Access denied", error_logged=True)
    wrapped = PathSecurityError.wrap_error("File collection failed", original)
    assert wrapped.has_been_logged  # Should preserve logged state
    assert wrapped.wrapped  # Should be marked as wrapped
    assert str(wrapped) == "File collection failed: Access denied"


def test_file_info_immutability(fs: FakeFilesystem) -> None:
    """Test that FileInfo attributes are immutable."""
    # Create test file
    fs.create_file("test.txt", contents="test")

    # Create security manager
    security_manager = SecurityManager(base_dir=os.getcwd())

    # Create FileInfo instance
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Attempt to modify private fields should raise AttributeError
    with pytest.raises(AttributeError):
        file_info.__path = "modified.txt"

    with pytest.raises(AttributeError):
        file_info.__content = "modified content"

    with pytest.raises(AttributeError):
        file_info.__security_manager = SecurityManager(
            base_dir=os.getcwd()
        )  # Fix type error by providing valid SecurityManager
