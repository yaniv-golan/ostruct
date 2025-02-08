"""Tests for allowed directory checking functionality."""

import os
from pathlib import Path

import pytest

from ostruct.cli.security import (
    PathSecurityError,
    SecurityErrorReasons,
    is_path_in_allowed_dirs,
)


def test_is_path_in_allowed_dirs_basic():
    """Test basic allowed directory checking."""
    allowed_dirs = [Path("/base"), Path("/tmp")]

    # Test paths in allowed directories
    assert is_path_in_allowed_dirs("/base/file.txt", allowed_dirs)
    assert is_path_in_allowed_dirs("/tmp/file.txt", allowed_dirs)

    # Test paths outside allowed directories
    assert not is_path_in_allowed_dirs("/etc/passwd", allowed_dirs)
    assert not is_path_in_allowed_dirs("/usr/local/file.txt", allowed_dirs)


def test_is_path_in_allowed_dirs_subdirs():
    """Test subdirectory handling."""
    allowed_dirs = [Path("/base")]

    # Test subdirectories
    assert is_path_in_allowed_dirs("/base/subdir/file.txt", allowed_dirs)
    assert is_path_in_allowed_dirs("/base/deep/nested/file.txt", allowed_dirs)


def test_is_path_in_allowed_dirs_symlinks(fs):
    """Test handling of symlinks."""
    # Use an absolute fake path instead of tmp_path
    base_dir = Path("/tmp/test/base")
    allowed_dir = Path("/tmp/test/allowed")
    fs.create_dir(str(base_dir))
    fs.create_dir(str(allowed_dir))

    # Create test file and symlink within the fake temp directory
    test_file = base_dir / "test.txt"
    test_file.write_text("test")
    symlink = allowed_dir / "link.txt"
    os.symlink(str(test_file), str(symlink))

    allowed_dirs = [allowed_dir]

    # Test symlink in allowed directory
    assert is_path_in_allowed_dirs(str(symlink), allowed_dirs)

    # Test symlink target outside allowed directories
    assert not is_path_in_allowed_dirs(str(test_file), allowed_dirs)


def test_is_path_in_allowed_dirs_case_sensitivity():
    """Test case sensitivity handling."""
    allowed_dirs = [Path("/Base")]

    # Test different cases
    assert is_path_in_allowed_dirs("/Base/file.txt", allowed_dirs)
    if os.name == "nt":  # Windows is case-insensitive
        assert is_path_in_allowed_dirs("/base/file.txt", allowed_dirs)
    else:  # Unix-like systems are case-sensitive
        assert not is_path_in_allowed_dirs("/base/file.txt", allowed_dirs)


def test_is_path_in_allowed_dirs_normalization():
    """Test path normalization."""
    allowed_dirs = [Path("/base")]

    # Test with redundant separators
    assert is_path_in_allowed_dirs("/base//file.txt", allowed_dirs)
    assert is_path_in_allowed_dirs("/base/./file.txt", allowed_dirs)

    # Test with Unicode normalization
    assert is_path_in_allowed_dirs("/base/café/file.txt", allowed_dirs)
    assert is_path_in_allowed_dirs("/base/café/file.txt", allowed_dirs)


def test_is_path_in_allowed_dirs_edge_cases():
    """Test edge cases."""
    allowed_dirs = [Path("/base")]

    # Test empty path
    assert not is_path_in_allowed_dirs("", allowed_dirs)

    # Test None path
    with pytest.raises(TypeError):
        is_path_in_allowed_dirs(None, allowed_dirs)

    # Test empty allowed_dirs
    assert not is_path_in_allowed_dirs("/base/file.txt", [])
