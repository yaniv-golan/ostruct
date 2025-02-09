"""Tests for safe path joining functionality."""

import os
from pathlib import Path

import pytest

from ostruct.cli.security import safe_join


def test_safe_join_basic():
    """Test basic path joining."""
    # Test joining simple paths
    result = safe_join("/base", "subdir", "file.txt")
    assert result == os.path.normpath("/base/subdir/file.txt")

    # Test with Path objects - convert to strings
    result = safe_join(str(Path("/base")), str(Path("subdir")), "file.txt")
    assert result == os.path.normpath("/base/subdir/file.txt")


def test_safe_join_empty():
    """Test joining with empty components."""
    # Test with empty directory
    assert safe_join("", "file.txt") is None

    # Test with empty filename
    assert safe_join("/base", "") == os.path.normpath("/base")

    # Test with None components
    assert safe_join("/base", None) is None  # type: ignore[arg-type]


def test_safe_join_directory_traversal():
    """Test directory traversal prevention."""
    # Test with parent directory references
    assert safe_join("/base", "../etc/passwd") is None
    assert safe_join("/base", "subdir", "../../etc/passwd") is None

    # Test with absolute paths in components
    assert safe_join("/base", "/etc/passwd") is None


def test_safe_join_special_characters():
    """Test joining paths with special characters."""
    # Test with spaces
    result = safe_join("/base", "sub dir", "file name.txt")
    assert result == os.path.normpath("/base/sub dir/file name.txt")

    # Test with Unicode characters
    result = safe_join("/base", "café", "résumé.txt")
    assert result == os.path.normpath("/base/café/résumé.txt")


def test_safe_join_normalization():
    """Test path normalization during joining."""
    # Test with redundant separators
    result = safe_join("/base", "subdir", "file.txt")
    assert result == os.path.normpath("/base/subdir/file.txt")

    # Test with . and .. in safe ways
    result = safe_join("/base", ".", "file.txt")
    assert result == os.path.normpath("/base/file.txt")

    result = safe_join("/base", "subdir", ".", "file.txt")
    assert result == os.path.normpath("/base/subdir/file.txt")


def test_safe_join_edge_cases():
    """Test edge cases for path joining."""
    # Test with only base directory
    assert safe_join("/base") == os.path.normpath("/base")

    # Test with multiple nested subdirectories
    result = safe_join("/base", "sub1", "sub2", "sub3", "file.txt")
    assert result == os.path.normpath("/base/sub1/sub2/sub3/file.txt")

    # Test with current directory references
    result = safe_join("/base", "./subdir", "./file.txt")
    assert result == os.path.normpath("/base/subdir/file.txt")


def test_safe_join_windows_device_paths():
    """Test handling of Windows device paths."""
    if os.name != "nt":
        pytest.skip("Windows-specific test")

    # Device paths should be rejected
    assert safe_join(r"\\?\C:\base", "file.txt") is None
    assert safe_join(r"\\.\C:\base", "file.txt") is None
    assert safe_join("/base", r"\\?\file.txt") is None
    assert safe_join("/base", r"\\.\file.txt") is None


def test_safe_join_windows_drive_relative():
    """Test handling of Windows drive-relative paths."""
    if os.name != "nt":
        pytest.skip("Windows-specific test")

    # Drive-relative paths without slash should be rejected
    assert safe_join("C:base", "file.txt") is None
    assert safe_join("/base", "C:file.txt") is None

    # Drive paths with slash should work
    assert safe_join("C:/base", "file.txt") == "C:/base/file.txt"
    assert safe_join("C:\\base", "file.txt") == "C:/base/file.txt"


def test_safe_join_windows_reserved_names():
    """Test handling of Windows reserved device names."""
    if os.name != "nt":
        pytest.skip("Windows-specific test")

    # Reserved names should be rejected
    assert safe_join("/base", "CON") is None
    assert safe_join("/base", "PRN") is None
    assert safe_join("/base", "AUX") is None
    assert safe_join("/base", "NUL") is None
    assert safe_join("/base", "COM1") is None
    assert safe_join("/base", "LPT1") is None

    # Reserved names with extensions should be rejected
    assert safe_join("/base", "CON.txt") is None
    assert safe_join("/base", "PRN.doc") is None

    # Case variations should be rejected
    assert safe_join("/base", "con") is None
    assert safe_join("/base", "Con.txt") is None


def test_safe_join_windows_ads():
    """Test handling of Windows Alternate Data Streams."""
    if os.name != "nt":
        pytest.skip("Windows-specific test")

    # ADS should be rejected
    assert safe_join("/base", "file.txt:stream") is None
    assert safe_join("/base", "file.txt:Zone.Identifier") is None
    assert safe_join("/base", "file.txt:$DATA") is None

    # ADS in base directory should be rejected
    assert safe_join("/base/file.txt:stream", "other.txt") is None


def test_safe_join_windows_unc():
    """Test handling of Windows UNC paths."""
    if os.name != "nt":
        pytest.skip("Windows-specific test")

    # Valid UNC paths should work
    assert (
        safe_join("\\\\server\\share\\base", "file.txt")
        == "//server/share/base/file.txt"
    )

    # Incomplete UNC paths should be rejected
    assert safe_join("\\\\server", "file.txt") is None
    assert safe_join("\\\\server\\", "file.txt") is None

    # UNC in components should be rejected
    assert safe_join("/base", "\\\\server\\share\\file.txt") is None


def test_safe_join_mixed_slashes():
    """Test handling of mixed forward and back slashes."""
    # Mixed slashes should be normalized
    assert safe_join("/base", "sub\\dir/file.txt") == "/base/sub/dir/file.txt"
    assert safe_join("\\base", "sub/dir\\file.txt") == "/base/sub/dir/file.txt"

    # Multiple slashes should be collapsed
    assert (
        safe_join("/base", "sub//dir\\\\file.txt") == "/base/sub/dir/file.txt"
    )


def test_safe_join_empty_components():
    """Test handling of empty path components."""
    # Empty components should be ignored
    assert safe_join("/base", "", "file.txt") == "/base/file.txt"
    assert safe_join("/base", "dir", "", "file.txt") == "/base/dir/file.txt"

    # Multiple empty components should be handled
    assert safe_join("/base", "", "", "file.txt") == "/base/file.txt"


def test_safe_join_dot_components():
    """Test handling of current directory components."""
    # Single dots should be normalized away
    assert safe_join("/base", ".", "file.txt") == "/base/file.txt"
    assert safe_join("/base", "dir", ".", "file.txt") == "/base/dir/file.txt"

    # Multiple dots should be normalized
    assert safe_join("/base", ".", ".", "file.txt") == "/base/file.txt"
