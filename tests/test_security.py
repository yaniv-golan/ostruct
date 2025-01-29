"""Tests for security functionality."""

from pathlib import Path

import pytest

from ostruct.cli.errors import PathSecurityError
from ostruct.cli.security import SecurityManager


def test_security_manager_init(tmp_path: Path) -> None:
    """Test SecurityManager initialization."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])
    assert manager.base_dir == base_dir.resolve()
    assert manager.allowed_dirs == [allowed_dir.resolve()]


def test_is_path_allowed(tmp_path: Path) -> None:
    """Test path allowance checks."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])

    # Test paths under base directory
    base_file = base_dir / "test.txt"
    base_file.touch()
    assert manager.is_path_allowed(str(base_file))

    # Test paths under allowed directory
    allowed_file = allowed_dir / "test.txt"
    allowed_file.touch()
    assert manager.is_path_allowed(str(allowed_file))

    # Test paths outside allowed directories
    outside_file = outside_dir / "test.txt"
    outside_file.touch()
    assert not manager.is_path_allowed(str(outside_file))

    # Test non-existent paths
    assert not manager.is_path_allowed(str(base_dir / "nonexistent.txt"))


def test_add_allowed_dir(tmp_path: Path) -> None:
    """Test adding allowed directories."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    new_dir = tmp_path / "new"
    new_dir.mkdir()

    manager = SecurityManager(str(base_dir))
    assert not manager.is_path_allowed(str(new_dir))

    manager.add_allowed_dir(str(new_dir))
    assert manager.is_path_allowed(str(new_dir))


def test_add_allowed_dirs_from_file(tmp_path: Path) -> None:
    """Test adding allowed directories from a file."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    # Create allowed dirs file
    allowed_file = base_dir / "allowed.txt"
    allowed_file.write_text(f"{dir1.resolve()}\n{dir2.resolve()}\n")

    manager = SecurityManager(str(base_dir))
    manager.add_allowed_dirs_from_file(str(allowed_file))

    assert manager.is_path_allowed(str(dir1))
    assert manager.is_path_allowed(str(dir2))


def test_validate_path(tmp_path: Path) -> None:
    """Test path validation."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    manager = SecurityManager(str(base_dir))

    # Test valid path
    valid_file = base_dir / "test.txt"
    valid_file.touch()
    assert manager.validate_path(str(valid_file)) == valid_file.resolve()

    # Test invalid path
    invalid_file = outside_dir / "test.txt"
    invalid_file.touch()
    with pytest.raises(PathSecurityError):
        manager.validate_path(str(invalid_file))


def test_is_allowed_file(tmp_path: Path) -> None:
    """Test file-specific allowance checks."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    manager = SecurityManager(str(base_dir))

    # Test file
    test_file = base_dir / "test.txt"
    test_file.touch()
    assert manager.is_allowed_file(str(test_file))

    # Test directory
    test_dir = base_dir / "test_dir"
    test_dir.mkdir()
    assert not manager.is_allowed_file(str(test_dir))

    # Test non-existent file
    assert not manager.is_allowed_file(str(base_dir / "nonexistent.txt"))


def test_is_allowed_path_string(tmp_path: Path) -> None:
    """Test path string allowance checks."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    manager = SecurityManager(str(base_dir))

    # Test valid path string
    test_file = base_dir / "test.txt"
    test_file.touch()
    assert manager.is_allowed_path(str(test_file))

    # Test invalid path string
    assert not manager.is_allowed_path("/invalid/path")

    # Test malformed path string
    assert not manager.is_allowed_path("\0invalid")
