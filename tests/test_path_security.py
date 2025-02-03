"""Tests for enhanced path security validation."""

import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.errors import PathSecurityError
from ostruct.cli.security import SecurityManager, normalize_path


@pytest.fixture(autouse=True)
def patch_filesystem_case(fs: FakeFilesystem) -> Generator[None, None, None]:
    """Configure pyfakefs case sensitivity based on platform."""
    if sys.platform == "darwin" or os.name == "nt":
        fs.is_case_sensitive = False
        fs.case_sensitive = (
            False  # Ensure both properties are set for compatibility
        )
        fs.path_separator = "/"  # Ensure consistent path separators
    yield


def test_normalize_path_case_sensitivity(fs: FakeFilesystem) -> None:
    """Test path normalization handles case sensitivity correctly."""
    # Create test directories
    fs.create_dir("/test_workspace/Base")
    fs.create_dir("/test_workspace/base/subdir")

    # Test case sensitivity handling
    path1 = normalize_path("/test_workspace/Base")
    path2 = normalize_path("/test_workspace/base")

    # Debug prints
    print("Path details:")
    print(f"path1: {path1} (exists: {path1.exists()})")
    print(f"path2: {path2} (exists: {path2.exists()})")
    print(f"fs.is_case_sensitive: {fs.is_case_sensitive}")
    print(f"Resolved path1: {path1.resolve()}")
    print(f"Resolved path2: {path2.resolve()}")

    if os.name == "nt" or (os.name == "posix" and sys.platform == "darwin"):
        # On case-insensitive systems, paths should match
        assert path1 == path2
    else:
        # On case-sensitive systems, paths should differ
        assert path1 != path2


def test_normalize_path_unicode(fs: FakeFilesystem) -> None:
    """Test path normalization handles Unicode correctly."""
    # Create test directory with Unicode name
    fs.create_dir("/test_workspace/café")

    # Test different Unicode normalizations
    path1 = normalize_path("/test_workspace/café")  # NFC
    path2 = normalize_path("/test_workspace/cafe\u0301")  # NFD

    # Both should normalize to the same path
    assert path1 == path2


def test_path_traversal_prevention(fs: FakeFilesystem) -> None:
    """Test prevention of path traversal attacks."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    fs.create_dir(base_dir)
    fs.create_dir("/test_workspace/outside")

    manager = SecurityManager(str(base_dir))

    # Test various path traversal attempts
    traversal_attempts = [
        "../outside",
        "subdir/../../outside",
        "./subdir/../../../outside",
        "subdir/./../../outside",
        "subdir//../../outside",
        "subdir/\u2024\u2024/\u2024\u2024/outside",  # Unicode dots
    ]

    for attempt in traversal_attempts:
        path = base_dir / attempt
        assert not manager.is_path_allowed(path)
        with pytest.raises(PathSecurityError) as exc:
            manager.validate_path(path)
        assert "outside" in str(exc.value)


def test_symlink_security(fs: FakeFilesystem) -> None:
    """Test secure handling of symlinks."""
    # Create test directories and files
    fs.create_dir("/test_workspace/base")
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/outside/target.txt")

    # Create symlink in base pointing outside
    fs.create_symlink(
        "/test_workspace/base/link", "/test_workspace/outside/target.txt"
    )

    manager = SecurityManager("/test_workspace/base")

    # Symlink should not be allowed as it points outside
    with pytest.raises(PathSecurityError) as exc:
        manager.validate_path("/test_workspace/base/link")
    assert "outside" in str(exc.value)


def test_allowed_paths_normalization(fs: FakeFilesystem) -> None:
    """Test path normalization in allowed paths checking."""
    # Create test directories
    fs.create_dir("/test_workspace/base")
    fs.create_dir("/test_workspace/allowed")

    # Create manager with lowercase paths
    manager = SecurityManager(
        "/test_workspace/base", ["/test_workspace/allowed"]
    )

    # Test paths that won't conflict on case-sensitive systems
    test_paths = [
        ("/test_workspace/base/file1.txt", True),
        (
            "/test_workspace/base/FILE2.txt",
            os.name != "posix" or sys.platform == "darwin",
        ),
        ("/test_workspace/allowed/file3.txt", True),
        (
            "/test_workspace/allowed/FILE4.txt",
            os.name != "posix" or sys.platform == "darwin",
        ),
    ]

    for path, expected in test_paths:
        try:
            fs.create_file(path)
        except FileExistsError:
            continue  # Skip if case-insensitive FS already has file

        assert manager.is_path_allowed(path) == expected, f"Failed for {path}"


def test_path_separator_normalization(fs: FakeFilesystem) -> None:
    """Test normalization of path separators."""
    # Create test directory
    fs.create_dir("/test_workspace/base")

    manager = SecurityManager("/test_workspace/base")

    # Test with different path separator styles
    path1 = "/test_workspace/base/subdir"
    path2 = "/test_workspace/base\\subdir"
    path3 = "\\test_workspace\\base\\subdir"

    fs.create_dir(path1)

    # All should normalize to the same path
    assert manager.is_path_allowed(path1)
    assert manager.is_path_allowed(path2)
    assert manager.is_path_allowed(path3)


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
