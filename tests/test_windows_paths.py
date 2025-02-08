"""Tests for Windows path handling."""

import os

import pytest

from ostruct.cli.security.windows_paths import (
    is_windows_path,
    resolve_windows_symlink,
    validate_windows_path,
)


def test_is_windows_path():
    """Test detection of Windows-specific paths."""
    # Device paths with different formats
    assert is_windows_path(r"\\?\C:\file.txt")  # Windows backslash format
    assert is_windows_path(r"//?/C:/file.txt")  # Forward slash format
    assert is_windows_path(r"\\.\PHYSICALDRIVE0")  # Physical device
    assert is_windows_path(
        r"//./PhysicalDrive0"
    )  # Physical device forward slash

    # Case variations for device paths
    assert is_windows_path(r"\\?\c:\file.txt")  # Lowercase drive
    assert is_windows_path(r"//?/c:/file.txt")  # Lowercase with forward slash

    # Normal paths should not be detected as Windows-specific
    assert not is_windows_path(r"C:\file.txt")  # Normal absolute path
    assert not is_windows_path(r"C:/file.txt")  # Normal with forward slash

    # Reserved names
    assert is_windows_path("CON")
    assert is_windows_path("PRN.txt")
    assert is_windows_path("COM1")
    assert is_windows_path("LPT1.txt")
    assert not is_windows_path("CONSOLE.txt")  # Not a reserved name

    # UNC paths
    assert is_windows_path(r"\\server\share")
    assert not is_windows_path(r"\\?\UNC\server\share")  # Device path

    # Alternate Data Streams
    assert is_windows_path(r"file.txt:stream")
    assert is_windows_path(r"file.txt:Zone.Identifier")


def test_validate_windows_path():
    """Test validation of Windows paths."""
    # Device paths should be rejected consistently
    assert (
        validate_windows_path(r"\\?\C:\file.txt") == "Device paths not allowed"
    )
    assert (
        validate_windows_path(r"//?/C:/file.txt") == "Device paths not allowed"
    )
    assert (
        validate_windows_path(r"\\.\PHYSICALDRIVE0")
        == "Device paths not allowed"
    )
    assert (
        validate_windows_path(r"//./PhysicalDrive0")
        == "Device paths not allowed"
    )

    # Case variations should also be rejected
    assert (
        validate_windows_path(r"\\?\c:\file.txt") == "Device paths not allowed"
    )
    assert (
        validate_windows_path(r"//?/c:/file.txt") == "Device paths not allowed"
    )

    # Normal paths should be allowed
    assert validate_windows_path(r"C:\file.txt") is None
    assert validate_windows_path(r"C:/file.txt") is None

    # Reserved names should be rejected
    assert validate_windows_path("CON") == "Windows reserved names not allowed"
    assert (
        validate_windows_path("PRN.txt")
        == "Windows reserved names not allowed"
    )
    assert (
        validate_windows_path("COM1") == "Windows reserved names not allowed"
    )
    assert validate_windows_path("normal.txt") is None  # Valid name

    # ADS should be rejected
    assert (
        validate_windows_path(r"file.txt:stream")
        == "Alternate Data Streams not allowed"
    )
    assert validate_windows_path(r"file.txt") is None  # Valid file

    # UNC paths should be complete
    assert validate_windows_path(r"\\server") == "Incomplete UNC path"
    assert (
        validate_windows_path(r"\\server\share\file.txt") is None
    )  # Valid UNC


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
def test_resolve_windows_symlink(tmp_path):
    """Test resolution of Windows symlinks."""
    if os.name != "nt":
        return

    # Create test file and symlink
    target_file = tmp_path / "target.txt"
    target_file.write_text("test")
    symlink = tmp_path / "link.txt"

    try:
        os.symlink(str(target_file), str(symlink))
    except OSError as e:
        pytest.skip(f"Symlink creation failed (permissions?): {e}")

    # Test regular symlink resolution
    resolved = resolve_windows_symlink(symlink)
    assert resolved is not None
    assert resolved.resolve() == target_file.resolve()

    # Test non-symlink path
    assert resolve_windows_symlink(target_file) is None

    # Test nonexistent path
    nonexistent = tmp_path / "nonexistent.txt"
    assert resolve_windows_symlink(nonexistent) is None
