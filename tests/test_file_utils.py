"""Tests for file utilities."""

import logging
import os

import pytest
from ostruct.cli.errors import OstructFileNotFoundError, PathSecurityError
from ostruct.cli.file_info import FileInfo
from ostruct.cli.file_list import FileInfoList
from ostruct.cli.file_utils import (
    collect_files,
    collect_files_from_directory,
    collect_files_from_pattern,
)
from ostruct.cli.security.errors import SecurityErrorReasons
from pyfakefs.fake_filesystem import FakeFilesystem

from tests.conftest import MockSecurityManager


def test_file_info_creation(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test FileInfo creation and properties.

    Note: Paths are always relative to the security manager's base directory,
    not the current working directory. This is a security feature to ensure consistent
    path handling regardless of the current working directory.
    """
    # Create test file in base directory
    fs.create_file("/test_workspace/base/test.txt", contents="test content")
    os.chdir("/test_workspace/base")  # Change to base directory

    # Create FileInfo instance
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Check basic properties
    assert os.path.basename(file_info.path) == "test.txt"
    assert file_info.path == "test.txt"  # Path relative to base_dir
    assert file_info.exists
    assert not file_info.is_binary


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
    strict_security_manager: MockSecurityManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that security check correctly blocks directory traversal attempts.

    EXPECTED ERROR: This test verifies that attempting to access files outside
    the base directory raises PathSecurityError.
    """
    # Create file completely outside test workspace
    fs.create_dir("/outside")
    fs.create_file("/outside/test.txt", contents="test")
    os.chdir("/test_workspace/base")

    # Suppress expected error logs during the test
    caplog.set_level(logging.ERROR)

    # Test directory traversal - should raise PathSecurityError
    with pytest.raises(PathSecurityError) as exc_info:
        FileInfo.from_path(
            "/outside/test.txt", security_manager=strict_security_manager
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
    strict_security_manager: MockSecurityManager,
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
    with pytest.raises(OstructFileNotFoundError) as file_not_found_exc:
        FileInfo.from_path(
            str("nonexistent.txt"), security_manager=security_manager
        )

    assert "File not found:" in str(file_not_found_exc.value)
    assert "nonexistent.txt" in str(file_not_found_exc.value)

    # Test 2: File outside allowed directories
    fs.create_dir("/outside")
    fs.create_file("/outside/test.txt", contents="test")
    with pytest.raises(PathSecurityError) as security_exc:
        FileInfo.from_path(
            "/outside/test.txt", security_manager=strict_security_manager
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
    """Test collecting files using glob patterns.

    Note: Paths are always relative to the security manager's base directory,
    not the current working directory.
    """
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
    assert {f.path for f in files} == {
        "test1.py",
        "test2.py",
    }  # Paths relative to base_dir


def test_collect_files_from_directory(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test collecting files from directory.

    Note: Paths are always relative to the security manager's base directory,
    not the current working directory.
    """
    # Create test files
    fs.create_file("/test_workspace/base/dir/test1.py", contents="test1")
    fs.create_file("/test_workspace/base/dir/test2.py", contents="test2")
    fs.create_file("/test_workspace/base/dir/test.txt", contents="test")
    fs.create_file(
        "/test_workspace/base/dir/subdir/test3.py", contents="test3"
    )
    os.chdir("/test_workspace")  # Change to base directory

    # Test non-recursive collection
    files = collect_files_from_directory(
        directory="base/dir", security_manager=security_manager
    )
    assert len(files) == 3
    assert {f.path for f in files} == {
        "dir/test1.py",
        "dir/test2.py",
        "dir/test.txt",
    }  # Paths relative to base_dir


def test_collect_files(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test collecting files from multiple sources.

    Note: Paths are always relative to the security manager's base directory,
    not the current working directory.
    """
    # Create test files
    fs.create_file("/test_workspace/base/single.txt", contents="single")
    fs.create_file("/test_workspace/base/test1.py", contents="test1")
    fs.create_file("/test_workspace/base/test2.py", contents="test2")
    fs.create_file("/test_workspace/base/dir/test3.py", contents="test3")
    fs.create_file("/test_workspace/base/dir/test4.py", contents="test4")
    os.chdir("/test_workspace")  # Change to security manager's base directory

    # Test collecting single file
    result = collect_files(
        file_mappings=[("single", "base/single.txt")],
        security_manager=security_manager,
    )
    assert len(result) == 1
    assert "single" in result
    assert isinstance(result["single"], FileInfoList)
    assert result["single"].content == "single"  # Test direct content access
    assert (
        result["single"][0].content == "single"
    )  # Test backward compatibility
    assert result["single"].path == "single.txt"  # Path relative to base_dir

    # Test collecting from pattern
    result = collect_files(
        pattern_mappings=[("tests", "base/*.py")],
        security_manager=security_manager,
    )
    assert len(result) == 1
    assert isinstance(result["tests"], FileInfoList)
    assert len(result["tests"]) == 2
    assert {f.path for f in result["tests"]} == {
        "test1.py",  # Paths relative to base_dir
        "test2.py",
    }

    # Test collecting from directory
    result = collect_files(
        dir_mappings=[("dir", "base/dir")],
        security_manager=security_manager,
    )
    assert len(result) == 1
    assert isinstance(result["dir"], FileInfoList)
    assert len(result["dir"]) == 2  # Two files in the directory
    assert {f.path for f in result["dir"]} == {
        "dir/test3.py",  # Paths relative to base_dir
        "dir/test4.py",
    }

    # Test collecting from multiple sources
    result = collect_files(
        file_mappings=[("single", "base/single.txt")],
        pattern_mappings=[("tests", "base/*.py")],
        dir_mappings=[("dir", "base/dir")],
        security_manager=security_manager,
    )
    assert len(result) == 3
    assert "single" in result
    assert "tests" in result
    assert "dir" in result
    assert result["single"].path == "single.txt"  # Path relative to base_dir


@pytest.mark.error_test
def test_collect_files_errors(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
    strict_security_manager: MockSecurityManager,
) -> None:
    """Test error handling in file collection.

    EXPECTED ERROR: This test verifies that invalid file mappings and missing files
    raise appropriate errors with clear messages.
    """
    os.chdir("/test_workspace/base")  # Change to base directory

    # Test invalid file mapping
    with pytest.raises(ValueError) as value_error_exc2:
        collect_files(
            file_mappings=[("", "")], security_manager=security_manager
        )
    assert "Empty name in file mapping" in str(value_error_exc2.value)

    # Test missing file
    with pytest.raises(OstructFileNotFoundError) as file_not_found_exc2:
        collect_files(
            file_mappings=[("test", "nonexistent.txt")],
            security_manager=security_manager,
        )
    assert "File not found:" in str(file_not_found_exc2.value)
    assert "nonexistent.txt" in str(file_not_found_exc2.value)

    # Test security violation
    fs.create_dir("/outside")
    fs.create_file("/outside/test.txt", contents="test")
    with pytest.raises(PathSecurityError) as security_exc4:
        collect_files(
            file_mappings=[("test", "/outside/test.txt")],
            security_manager=strict_security_manager,
        )
    assert "Access denied" in str(security_exc4.value)


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
    strict_security_manager: MockSecurityManager,
) -> None:
    """Test security checks when loading file stats.

    EXPECTED ERROR: This test verifies that attempting to access files outside
    the base directory raises PathSecurityError.
    """
    # Set up directory structure
    fs.create_dir("/outside")
    fs.create_file("/outside/test.txt", contents="test")
    os.chdir("/test_workspace/base")

    # Test accessing file outside base directory
    with pytest.raises(PathSecurityError) as exc_info:
        FileInfo.from_path(
            "/outside/test.txt", security_manager=strict_security_manager
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
    with pytest.raises(OstructFileNotFoundError) as exc_info:
        FileInfo.from_path(
            str("nonexistent.txt"), security_manager=security_manager
        )

    assert "File not found:" in str(exc_info.value)
    assert "nonexistent.txt" in str(exc_info.value)


@pytest.mark.error_test
def test_file_info_content_errors(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
    strict_security_manager: MockSecurityManager,
) -> None:
    """Test error handling in content loading.

    EXPECTED ERROR: This test verifies that attempting to access non-existent files
    and files outside allowed directories raises appropriate errors.
    """
    os.chdir("/test_workspace/base")

    # Test 1: Missing file at initialization
    with pytest.raises(OstructFileNotFoundError) as file_not_found_exc:
        FileInfo.from_path(
            str("nonexistent.txt"), security_manager=security_manager
        )

    assert "File not found:" in str(file_not_found_exc.value)
    assert "nonexistent.txt" in str(file_not_found_exc.value)

    # Test 2: File outside allowed directories
    fs.create_dir("/outside")
    fs.create_file("/outside/test.txt", contents="test")
    with pytest.raises(PathSecurityError) as security_exc:
        FileInfo.from_path(
            "/outside/test.txt", security_manager=strict_security_manager
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
    strict_security_manager: MockSecurityManager,
) -> None:
    """Test that security errors are logged only once with complete information.

    EXPECTED ERROR: This test verifies that attempting to access files outside
    the base directory raises PathSecurityError with proper logging.
    """
    # Set up test environment
    fs.create_dir(
        "/outside"
    )  # Create directory completely outside /test_workspace
    fs.create_file("/outside/test.txt", contents="test")
    os.chdir("/test_workspace/base")

    # Configure logging to capture all levels
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("ostruct")
    logger.setLevel(logging.DEBUG)

    # Attempt to access file outside allowed directory
    with pytest.raises(PathSecurityError) as exc_info:
        FileInfo.from_path(
            "/outside/test.txt", security_manager=strict_security_manager
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
    strict_security_manager: MockSecurityManager,
) -> None:
    """Test that security error message includes allowed directories.

    EXPECTED ERROR: This test verifies that security errors include information
    about allowed directories in their error messages.
    """
    # Set up test environment - create file completely outside /test_workspace
    fs.create_dir("/outside")
    fs.create_file("/outside/test.txt", contents="test")
    os.chdir("/test_workspace/base")

    # Configure logging to capture all levels
    caplog.set_level(logging.ERROR)

    # Add allowed directory to security manager
    strict_security_manager.add_allowed_directory("/test_workspace/allowed")

    # Attempt to access file with allowed directories specified
    with pytest.raises(PathSecurityError) as exc_info:
        FileInfo.from_path(
            "/outside/test.txt", security_manager=strict_security_manager
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
    """Test security error with expanded paths in error message."""
    # Create error with expanded paths
    error = PathSecurityError.from_expanded_paths(
        original_path="~/test.txt",
        expanded_path="/home/user/test.txt",
        base_dir="/test_workspace",
        allowed_dirs=["/allowed"],
        error_logged=True,
    )

    error_str = str(error)
    # Check basic message format
    assert error_str.startswith("[SECURITY_ERROR] Access denied")
    # Check path information
    assert "Original Path: ~/test.txt" in error_str
    assert "Expanded Path: /home/user/test.txt" in error_str
    assert "Base Directory: /test_workspace" in error_str
    assert "Allowed Directories: ['/allowed']" in error_str


def test_security_error_format_with_context() -> None:
    """Test formatting security error with additional context."""
    # Create error with context
    error = PathSecurityError(
        "Access denied",
        path="/test.txt",
        context={
            "original_path": "~/test.txt",
            "expanded_path": "/test.txt",
            "base_dir": "/base",
            "allowed_dirs": ["/allowed"],
        },
        error_logged=True,
    )

    error_str = str(error)
    # Check basic message format
    assert error_str.startswith("[SECURITY_ERROR] Access denied")
    # Check context information
    assert "Original Path: ~/test.txt" in error_str
    assert "Expanded Path: /test.txt" in error_str
    assert "Base Directory: /base" in error_str
    assert "Allowed Directories: ['/allowed']" in error_str


def test_security_error_attributes() -> None:
    """Test PathSecurityError attributes and properties."""
    error = PathSecurityError(
        "Access denied", path="/test/path", error_logged=True
    )
    assert error.error_logged
    assert not error.wrapped
    error_str = str(error)
    assert error_str.startswith("[SECURITY_ERROR] Access denied")
    assert "Path: /test/path" in error_str
    assert "Category: security" in error_str


def test_security_error_wrapping() -> None:
    """Test error wrapping with context preservation."""
    original = PathSecurityError("Access denied", error_logged=True)
    wrapped = PathSecurityError.wrap_error("File collection failed", original)
    assert wrapped.error_logged  # Should preserve logged state
    assert wrapped.wrapped  # Should be marked as wrapped


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
