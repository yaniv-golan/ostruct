"""Tests for symlink resolution through the public API."""

import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.security import (
    PathSecurityError,
    SecurityErrorReasons,
    SecurityManager,
)


def test_resolve_symlink_basic(fs: FakeFilesystem) -> None:
    """Test basic symlink resolution."""
    # Create test file and symlink
    fs.create_file("/test_workspace/base/target.txt", contents="test")
    fs.create_symlink(
        "/test_workspace/base/link.txt", "/test_workspace/base/target.txt"
    )

    # Resolve symlink
    manager = SecurityManager(base_dir="/test_workspace/base")
    result = manager.resolve_path("/test_workspace/base/link.txt")
    assert result == Path("/test_workspace/base/target.txt").resolve()
    assert result.is_file()


def test_resolve_symlink_nested(fs: FakeFilesystem) -> None:
    """Test resolution of nested symlinks."""
    # Create nested symlink chain
    fs.create_file("/test_workspace/base/target.txt", contents="test")
    fs.create_symlink(
        "/test_workspace/base/link1.txt", "/test_workspace/base/target.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link1.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link3.txt", "/test_workspace/base/link2.txt"
    )

    # Resolve final symlink
    manager = SecurityManager(base_dir="/test_workspace/base")
    result = manager.resolve_path("/test_workspace/base/link3.txt")
    assert result == Path("/test_workspace/base/target.txt").resolve()
    assert result.is_file()


def test_resolve_symlink_loop(fs: FakeFilesystem) -> None:
    """Test detection of symlink loops."""
    # Create a symlink loop
    fs.create_symlink(
        "/test_workspace/base/link1.txt", "/test_workspace/base/link2.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link1.txt"
    )

    # Attempt to resolve loop
    manager = SecurityManager(base_dir="/test_workspace/base")
    with pytest.raises(PathSecurityError) as exc_info:
        manager.resolve_path("/test_workspace/base/link1.txt")
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.SYMLINK_LOOP
    )
    assert len(exc_info.value.context["chain"]) > 0  # Chain should be logged


def test_resolve_symlink_max_depth(fs: FakeFilesystem) -> None:
    """Test maximum symlink depth enforcement."""
    # Create a long chain of symlinks
    fs.create_file("/test_workspace/base/target.txt", contents="test")

    current = "/test_workspace/base/target.txt"
    for i in range(5):
        link = f"/test_workspace/base/link_{i}.txt"
        fs.create_symlink(link, current)
        current = link

    # Test with sufficient depth
    manager = SecurityManager(base_dir="/test_workspace/base")
    result = manager.resolve_path("/test_workspace/base/link_4.txt")
    assert result == Path("/test_workspace/base/target.txt").resolve()

    # Test with insufficient depth
    manager = SecurityManager(
        base_dir="/test_workspace/base", max_symlink_depth=2
    )
    with pytest.raises(PathSecurityError) as exc_info:
        manager.resolve_path("/test_workspace/base/link_4.txt")
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_MAX_DEPTH
    )
    assert exc_info.value.context.get("depth", 0) == 2


def test_resolve_symlink_normalized_loop_detection(fs: FakeFilesystem) -> None:
    """Test loop detection with path variants."""
    # Create files with different path representations
    fs.create_dir("/test_workspace/base/subdir")
    fs.create_symlink(
        "/test_workspace/base/link1.txt", "/test_workspace/base/link2.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link1.txt"
    )

    # Both paths should detect the same loop
    manager = SecurityManager(base_dir="/test_workspace/base")
    with pytest.raises(PathSecurityError) as exc_info:
        manager.resolve_path("/test_workspace/base/link1.txt")
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.SYMLINK_LOOP
    )

    with pytest.raises(PathSecurityError) as exc_info:
        manager.resolve_path("/test_workspace/base/link2.txt")
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.SYMLINK_LOOP
    )


def test_resolve_symlink_final_validation(fs: FakeFilesystem) -> None:
    """Test validation of final resolved path."""
    # Create test file and symlink
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/outside/target.txt", contents="test")
    fs.create_symlink(
        "/test_workspace/base/link.txt", "/test_workspace/outside/target.txt"
    )

    # Resolve with only base directory allowed (should fail)
    manager = SecurityManager(base_dir="/test_workspace/base")
    with pytest.raises(PathSecurityError) as exc_info:
        manager.resolve_path("/test_workspace/base/link.txt")
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )

    # Resolve with outside directory allowed (should succeed)
    manager = SecurityManager(
        base_dir="/test_workspace/base",
        allowed_dirs=["/test_workspace/outside"],
    )
    result = manager.resolve_path("/test_workspace/base/link.txt")
    assert result == Path("/test_workspace/outside/target.txt").resolve()


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
def test_resolve_symlink_windows_specific(fs: FakeFilesystem) -> None:
    """Test Windows-specific symlink handling."""
    fs.is_windows_fs = True

    # Create test file and symlink
    fs.create_file("/test_workspace/base/target.txt", contents="test")
    fs.create_symlink(
        "/test_workspace/base/link.txt", "/test_workspace/base/target.txt"
    )

    # Test with Windows device path (should fail)
    fs.create_file(
        "/test_workspace/base/device_path.txt", contents="\\\\?\\C:\\file.txt"
    )
    manager = SecurityManager(base_dir="/test_workspace/base")
    with pytest.raises(PathSecurityError) as exc_info:
        manager.resolve_path("/test_workspace/base/device_path.txt")
    assert exc_info.value.context.get("windows_specific") is True


def test_resolve_symlink_nonexistent(fs: FakeFilesystem) -> None:
    """Test handling of nonexistent symlinks."""
    # Create target file first
    fs.create_file("/test_workspace/base/target.txt", contents="test")
    fs.create_symlink(
        "/test_workspace/base/link.txt", "/test_workspace/base/target.txt"
    )

    # Now remove the target to create a broken symlink
    fs.remove("/test_workspace/base/target.txt")

    # Attempt to resolve
    manager = SecurityManager(base_dir="/test_workspace/base")
    with pytest.raises(FileNotFoundError):
        manager.resolve_path("/test_workspace/base/link.txt")


def test_resolve_symlink_non_symlink(fs: FakeFilesystem) -> None:
    """Test handling of non-symlink paths."""
    # Create regular file
    fs.create_file("/test_workspace/base/file.txt", contents="test")

    # Resolve regular file
    manager = SecurityManager(base_dir="/test_workspace/base")
    result = manager.resolve_path("/test_workspace/base/file.txt")
    assert result == Path("/test_workspace/base/file.txt").resolve()


def test_resolve_symlink_directory(fs: FakeFilesystem) -> None:
    """Test resolution of directory symlinks."""
    # Create test directory and symlink
    fs.create_dir("/test_workspace/base/target_dir")
    fs.create_symlink(
        "/test_workspace/base/link_dir", "/test_workspace/base/target_dir"
    )

    # Resolve directory symlink
    manager = SecurityManager(base_dir="/test_workspace/base")
    result = manager.resolve_path("/test_workspace/base/link_dir")
    assert result == Path("/test_workspace/base/target_dir").resolve()
    assert result.is_dir()


def test_resolve_symlink_permissions(fs: FakeFilesystem) -> None:
    """Test symlink resolution with different permissions."""
    # Create test file with restricted permissions
    fs.create_file(
        "/test_workspace/base/target.txt", contents="test", st_mode=0o000
    )
    fs.create_symlink(
        "/test_workspace/base/link.txt", "/test_workspace/base/target.txt"
    )

    # Resolve symlink to inaccessible target
    manager = SecurityManager(base_dir="/test_workspace/base")
    result = manager.resolve_path("/test_workspace/base/link.txt")
    assert result == Path("/test_workspace/base/target.txt").resolve()
