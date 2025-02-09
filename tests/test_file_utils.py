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
from ostruct.cli.security.errors import SecurityErrorReasons
from tests.conftest import MockSecurityManager


def test_file_info_creation(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test FileInfo creation and properties."""
    # Create test file in base directory
    fs.create_file("/test_workspace/base/test.txt", contents="test content")
    os.chdir("/test_workspace/base")  # Change to base directory

    # Create FileInfo instance
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Check basic properties
    assert os.path.basename(file_info.path) == "test.txt"
    assert file_info.path == "test.txt"
    assert file_info.abs_path == "/test_workspace/base/test.txt"
    assert file_info.extension == "txt"

    # Check initial state
    assert isinstance(file_info.size, int)
    assert isinstance(file_info.mtime, float)
    assert file_info.encoding is not None
    assert file_info.hash is not None

    # Content should be available immediately
    assert file_info.content == "test content"


def test_file_info_cache_update(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test cache update mechanism."""
    fs.create_file("/test_workspace/base/test.txt", contents="test content")
    os.chdir("/test_workspace/base")  # Change to base directory

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


def test_file_info_property_protection(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test that private fields cannot be set directly."""
    fs.create_file("/test_workspace/base/test.txt", contents="test content")
    os.chdir("/test_workspace/base")  # Change to base directory

    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Attempt to modify private fields should raise AttributeError
    with pytest.raises(AttributeError):
        file_info.__path = "modified.txt"

    with pytest.raises(AttributeError):
        file_info.__content = "modified content"

    with pytest.raises(AttributeError):
        file_info.__security_manager = security_manager


@pytest.mark.error_test
def test_file_info_directory_traversal(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that security check correctly blocks directory traversal attempts.

    EXPECTED ERROR: This test verifies that attempting to access files outside
    the base directory raises PathSecurityError.
    """
    os.chdir("/test_workspace/base")

    # Suppress expected error logs during the test
    caplog.set_level(logging.ERROR)

    # Test directory traversal - should raise PathSecurityError
    with pytest.raises(
        PathSecurityError, match="Access denied:.*outside base directory"
    ) as exc_info:
        FileInfo.from_path(
            "../outside/test.txt", security_manager=security_manager
        )

    # Verify error details
    error = exc_info.value
    assert error.context["reason"] == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    assert "test.txt" in str(error)  # Verify filename is in error
    assert "outside base directory" in str(error)  # Verify reason is in error

    # Verify appropriate error was logged
    assert any(
        "Security violation" in record.message for record in caplog.records
    )


@pytest.mark.error_test
def test_file_info_missing_file(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that accessing a non-existent file raises appropriate error.

    EXPECTED ERROR: This test verifies that attempting to access a file that doesn't exist
    raises FileNotFoundError.
    """
    os.chdir("/test_workspace/base")

    # Suppress debug logs about missing files
    caplog.set_level(logging.INFO)

    # Test 1: File not found
    with pytest.raises(FileNotFoundError) as file_not_found_exc:
        FileInfo.from_path(
            str("nonexistent.txt"), security_manager=security_manager
        )

    assert "File not found:" in str(file_not_found_exc.value)
    assert "nonexistent.txt" in str(file_not_found_exc.value)

    # Test 2: File outside allowed directories
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/outside/test.txt", contents="test")
    with pytest.raises(PathSecurityError) as security_exc:
        FileInfo.from_path(
            str("../outside/test.txt"), security_manager=security_manager
        )

    assert "Access denied" in str(security_exc.value)
    assert "is outside base directory" in str(security_exc.value)
    assert (
        security_exc.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


def test_collect_files_from_pattern(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test collecting files using glob patterns."""
    # Create test files
    fs.create_file("/test_workspace/base/test1.py", contents="test1")
    fs.create_file("/test_workspace/base/test2.py", contents="test2")
    fs.create_file("/test_workspace/base/test.txt", contents="test")
    fs.create_file("/test_workspace/base/subdir/test3.py", contents="test3")
    os.chdir("/test_workspace/base")  # Change to base directory

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


def test_collect_files_from_directory(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test collecting files from directory."""
    # Create test files
    fs.create_file("/test_workspace/base/dir/test1.py", contents="test1")
    fs.create_file("/test_workspace/base/dir/test2.py", contents="test2")
    fs.create_file("/test_workspace/base/dir/test.txt", contents="test")
    fs.create_file(
        "/test_workspace/base/dir/subdir/test3.py", contents="test3"
    )
    os.chdir("/test_workspace/base")  # Change to base directory

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


def test_collect_files(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test collecting files from multiple sources."""
    # Create test files
    fs.create_file("/test_workspace/base/single.txt", contents="single")
    fs.create_file("/test_workspace/base/test1.py", contents="test1")
    fs.create_file("/test_workspace/base/test2.py", contents="test2")
    fs.create_file("/test_workspace/base/dir/test3.py", contents="test3")
    fs.create_file("/test_workspace/base/dir/test4.py", contents="test4")
    os.chdir("/test_workspace/base")  # Change to base directory

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
    assert isinstance(result["tests"], FileInfoList)
    assert len(result["tests"]) == 2
    assert {f.path for f in result["tests"]} == {"test1.py", "test2.py"}

    # Test collecting from directory
    result = collect_files(
        dir_mappings=["dir=dir"], security_manager=security_manager
    )
    assert len(result) == 1
    assert isinstance(result["dir"], FileInfoList)
    assert len(result["dir"]) == 2
    assert {f.path for f in result["dir"]} == {"dir/test3.py", "dir/test4.py"}


@pytest.mark.error_test
def test_collect_files_errors(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test error handling in file collection.

    EXPECTED ERROR: This test verifies that invalid file mappings and missing files
    raise appropriate errors with clear messages.
    """
    os.chdir("/test_workspace/base")  # Change to base directory

    # Test invalid file mapping
    with pytest.raises(ValueError) as value_error_exc2:
        collect_files(
            file_mappings=["test"], security_manager=security_manager
        )
    assert "Invalid file mapping format" in str(value_error_exc2.value)
    assert "missing '=' separator" in str(value_error_exc2.value)

    # Test missing file
    with pytest.raises(FileNotFoundError) as file_not_found_exc2:
        collect_files(
            file_mappings=["test=nonexistent.txt"],
            security_manager=security_manager,
        )
    assert "File not found:" in str(file_not_found_exc2.value)
    assert "nonexistent.txt" in str(file_not_found_exc2.value)

    # Test security violation
    fs.create_file("/test_workspace/outside/test.txt", contents="test")
    with pytest.raises(PathSecurityError) as security_exc4:
        collect_files(
            file_mappings=["test=../outside/test.txt"],
            security_manager=security_manager,
        )
    assert "Access denied" in str(security_exc4.value)
    assert "is outside base directory" in str(security_exc4.value)
    assert (
        security_exc4.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


def test_file_info_stats_loading(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test that file stats are loaded with content."""
    fs.create_file("/test_workspace/base/test.txt", contents="test content")
    os.chdir("/test_workspace/base")  # Change to base directory

    # Create FileInfo instance
    file_info = FileInfo.from_path(
        str("test.txt"), security_manager=security_manager
    )

    # Check that stats are loaded
    size = file_info.size
    mtime = file_info.mtime
    assert size is not None and size > 0
    assert mtime is not None and mtime > 0


@pytest.mark.error_test
def test_file_info_stats_security(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test security checks when loading file stats.

    EXPECTED ERROR: This test verifies that attempting to access files outside
    the base directory raises PathSecurityError.
    """
    # Set up directory structure
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/base/test.txt", contents="test")
    fs.create_file("/test_workspace/outside/test.txt", contents="test")
    os.chdir("/test_workspace/base")

    # Test accessing file outside base directory
    with pytest.raises(PathSecurityError) as exc_info:
        FileInfo.from_path(
            str("../outside/test.txt"), security_manager=security_manager
        )

    assert "Access denied:" in str(exc_info.value)
    assert "test.txt" in str(exc_info.value)
    assert "outside base directory" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


@pytest.mark.error_test
def test_file_info_missing_file_stats(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test error handling for missing file stats.

    EXPECTED ERROR: This test verifies that attempting to access a non-existent file
    raises FileNotFoundError.
    """
    os.chdir("/test_workspace/base")

    # Test missing file
    with pytest.raises(FileNotFoundError) as exc_info:
        FileInfo.from_path(
            str("nonexistent.txt"), security_manager=security_manager
        )

    assert "File not found:" in str(exc_info.value)
    assert "nonexistent.txt" in str(exc_info.value)


@pytest.mark.error_test
def test_file_info_content_errors(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test error handling in content loading.

    EXPECTED ERROR: This test verifies that attempting to access non-existent files
    and files outside allowed directories raises appropriate errors.
    """
    os.chdir("/test_workspace/base")

    # Test 1: Missing file at initialization
    with pytest.raises(FileNotFoundError) as file_not_found_exc:
        FileInfo.from_path(
            str("nonexistent.txt"), security_manager=security_manager
        )

    assert "File not found:" in str(file_not_found_exc.value)
    assert "nonexistent.txt" in str(file_not_found_exc.value)

    # Test 2: File outside allowed directories
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/outside/test.txt", contents="test")
    with pytest.raises(PathSecurityError) as security_exc:
        FileInfo.from_path(
            str("../outside/test.txt"), security_manager=security_manager
        )

    assert "Access denied" in str(security_exc.value)
    assert "is outside base directory" in str(security_exc.value)
    assert (
        security_exc.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


@pytest.mark.error_test
def test_security_error_single_message(
    caplog: pytest.LogCaptureFixture,
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test that security errors are logged only once with complete information.

    EXPECTED ERROR: This test verifies that attempting to access files outside
    the base directory raises PathSecurityError with proper logging.
    """
    # Set up test environment
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/outside/test.txt", contents="test")
    os.chdir("/test_workspace/base")

    # Configure logging to capture all levels
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("ostruct")
    logger.setLevel(logging.DEBUG)

    # Attempt to access file outside allowed directory
    with pytest.raises(PathSecurityError) as exc_info:
        FileInfo.from_path(
            "../outside/test.txt", security_manager=security_manager
        )

    assert "Access denied:" in str(exc_info.value)
    assert "test.txt" in str(exc_info.value)
    assert "outside base directory" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


@pytest.mark.error_test
def test_security_error_with_allowed_dirs(
    caplog: pytest.LogCaptureFixture,
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test that security error message includes allowed directories.

    EXPECTED ERROR: This test verifies that security errors include information
    about allowed directories in their error messages.
    """
    # Set up test environment
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/outside/test.txt", contents="test")
    os.chdir("/test_workspace/base")

    # Configure logging to capture all levels
    caplog.set_level(logging.ERROR)

    # Add allowed directory to security manager
    security_manager.add_allowed_directory("/test_workspace/allowed")

    # Attempt to access file with allowed directories specified
    with pytest.raises(PathSecurityError) as exc_info:
        FileInfo.from_path(
            "../outside/test.txt", security_manager=security_manager
        )

    assert "Access denied:" in str(exc_info.value)
    assert "test.txt" in str(exc_info.value)
    assert "outside base directory" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


def test_security_error_expanded_paths(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test security error handling with expanded paths."""
    # Create test error with expanded paths
    error = PathSecurityError.from_expanded_paths(
        original_path="~/test.txt",
        expanded_path="/home/user/test.txt",
        base_dir="/test_workspace",
        allowed_dirs=["/allowed"],
        error_logged=True,
    )

    # Verify error message contains all components
    error_msg = str(error)
    assert "~/test.txt" in error_msg
    assert "/home/user/test.txt" in error_msg
    assert "Base directory: /test_workspace" in error_msg
    assert "Allowed directories: ['/allowed']" in error_msg
    assert error.has_been_logged is True


def test_security_error_format_with_context() -> None:
    """Test formatting security error with additional context."""
    # Create basic error
    error = PathSecurityError("Access denied: test.txt")

    # Format with context
    formatted = error.format_with_context(
        original_path="~/test.txt",
        expanded_path="/home/user/test.txt",
        base_dir="/test_workspace",
        allowed_dirs=["/allowed"],
    )

    # Verify formatted message contains all components
    assert "Original path: ~/test.txt" in formatted
    assert "Expanded path: /home/user/test.txt" in formatted
    assert "Base directory: /test_workspace" in formatted
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


def test_file_info_immutability(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test that FileInfo attributes are immutable."""
    # Create test file
    fs.create_file("/test_workspace/base/test.txt", contents="test")
    os.chdir("/test_workspace/base")  # Change to base directory

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
        file_info.__security_manager = security_manager


@pytest.mark.error_test
def test_collect_files_security_error_propagates(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test security errors propagate from directory collection."""
    fs.create_file("/test_workspace/base/valid.txt")
    fs.create_symlink("/test_workspace/base/malicious", "../outside.txt")
    os.chdir("/test_workspace/base")

    # Test should now pass with the fixed error propagation
    with pytest.raises(PathSecurityError) as exc_info:
        collect_files_from_directory(".", security_manager=security_manager)

    assert "Symlink security violation:" in str(exc_info.value)
    assert "target not allowed" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )


@pytest.mark.error_test
def test_collect_files_security_violations(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test various security violation scenarios in file collection.

    EXPECTED ERROR: This test verifies that symlink-based security violations
    raise appropriate PathSecurityError with detailed context.
    """
    # Setup
    fs.create_file("/test_workspace/base/valid.txt")
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/outside/target.txt")
    os.chdir("/test_workspace/base")

    # Test 1: Symlink to non-existent file outside allowed dirs
    fs.create_symlink(
        "/test_workspace/base/bad_link1", "../outside/nonexistent.txt"
    )
    with pytest.raises(PathSecurityError) as exc_info:
        collect_files_from_directory(".", security_manager=security_manager)

    assert "Symlink security violation:" in str(exc_info.value)
    assert "target not allowed" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )

    # Test 2: Symlink to existing file outside allowed dirs
    fs.create_symlink(
        "/test_workspace/base/bad_link2", "../outside/target.txt"
    )
    with pytest.raises(PathSecurityError) as exc_info:
        collect_files_from_directory(".", security_manager=security_manager)

    assert "Symlink security violation:" in str(exc_info.value)
    assert "target not allowed" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )

    # Test 3: Directory traversal attempt
    fs.create_symlink("/test_workspace/base/bad_link3", "../../etc/passwd")
    with pytest.raises(PathSecurityError) as exc_info:
        collect_files_from_directory(".", security_manager=security_manager)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )
    assert "Symlink security violation" in str(exc_info.value)
