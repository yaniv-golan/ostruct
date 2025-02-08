"""Tests for security functionality."""

import tempfile
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.security import (
    DirectoryNotFoundError,
    PathSecurityError,
    SecurityErrorReasons,
    SecurityManager,
)


def test_security_manager_init(fs: FakeFilesystem) -> None:
    """Test SecurityManager initialization."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    allowed_dir = Path("/test_workspace/allowed")
    fs.create_dir(base_dir)
    fs.create_dir(allowed_dir)

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])
    assert str(manager.base_dir) == str(base_dir.resolve())
    assert any(
        str(d) == str(allowed_dir.resolve()) for d in manager.allowed_dirs
    )


def test_security_manager_init_nonexistent_base(fs: FakeFilesystem) -> None:
    """Test SecurityManager initialization with nonexistent base directory."""
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager("/nonexistent/base")


def test_security_manager_init_nonexistent_allowed(fs: FakeFilesystem) -> None:
    """Test SecurityManager initialization with nonexistent allowed directory."""
    base_dir = Path("/test_workspace/base")
    fs.create_dir(base_dir)

    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(base_dir), ["/nonexistent/allowed"])


def test_security_manager_validate_path(fs: FakeFilesystem) -> None:
    """Test path validation."""
    # Create test directories and files
    base_dir = Path("/test_workspace/base")
    allowed_dir = Path("/test_workspace/allowed")
    fs.create_dir(base_dir)
    fs.create_dir(allowed_dir)
    fs.create_file(base_dir / "test.txt")
    fs.create_file(allowed_dir / "test.txt")

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])

    # Test valid paths
    assert manager.validate_path(base_dir / "test.txt")
    assert manager.validate_path(allowed_dir / "test.txt")

    # Test invalid paths
    with pytest.raises(PathSecurityError) as exc_info:
        manager.validate_path("/etc/passwd")
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


def test_security_manager_temp_paths(fs: FakeFilesystem) -> None:
    """Test temporary path handling."""
    base_dir = Path("/test_workspace/base")
    fs.create_dir(base_dir)

    # Create a test file in temp directory
    temp_file = Path(tempfile.gettempdir()) / "test.txt"
    fs.create_file(temp_file)

    # Test with temp paths allowed
    manager = SecurityManager(str(base_dir), allow_temp_paths=True)
    assert manager.validate_path(temp_file)

    # Test with temp paths disallowed
    manager = SecurityManager(str(base_dir), allow_temp_paths=False)
    with pytest.raises(PathSecurityError) as exc_info:
        manager.validate_path(temp_file)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )
