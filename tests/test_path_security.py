"""Tests for path security functionality."""

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.security import PathSecurityError, SecurityManager


def test_security_manager_base_dir_validation(fs: FakeFilesystem) -> None:
    """Test base directory validation in SecurityManager."""
    # Create test directories
    fs.create_dir("/test_workspace/base")
    fs.create_dir("/test_workspace/outside")

    manager = SecurityManager("/test_workspace/base")

    # Test paths within base directory
    assert manager.is_path_allowed("/test_workspace/base/file.txt")
    assert manager.is_path_allowed("/test_workspace/base/subdir/file.txt")

    # Test paths outside base directory
    assert not manager.is_path_allowed("/test_workspace/outside/file.txt")
    assert not manager.is_path_allowed("/etc/passwd")


def test_security_manager_allowed_dirs(fs: FakeFilesystem) -> None:
    """Test allowed directories functionality."""
    # Create test directories
    fs.create_dir("/test_workspace/base")
    fs.create_dir("/test_workspace/allowed")
    fs.create_dir("/test_workspace/outside")

    manager = SecurityManager(
        "/test_workspace/base", ["/test_workspace/allowed"]
    )

    # Test paths in allowed directories
    assert manager.is_path_allowed("/test_workspace/allowed/file.txt")
    assert manager.is_path_allowed("/test_workspace/allowed/subdir/file.txt")

    # Test paths outside allowed directories
    assert not manager.is_path_allowed("/test_workspace/outside/file.txt")


def test_unicode_normalization_security(fs: FakeFilesystem) -> None:
    """Test that Unicode normalization doesn't allow security bypasses."""
    # Create test directories
    fs.create_dir("/test_workspace/base")
    fs.create_dir("/test_workspace/outside")

    manager = SecurityManager("/test_workspace/base")

    # Test with Unicode normalization tricks
    test_paths = [
        "/test_workspace/base/..\\outside",  # Mixed separators
        "/test_workspace/base/\u2024\u2024/outside",  # Unicode dots
        "/test_workspace/base/\u0085/outside",  # Unicode line break
        "/test_workspace/base/\u2028/outside",  # Unicode line separator
        "/test_workspace/base/\u2029/outside",  # Unicode paragraph separator
    ]

    for path in test_paths:
        assert not manager.is_path_allowed(path)
        with pytest.raises(PathSecurityError):
            manager.validate_path(path)
