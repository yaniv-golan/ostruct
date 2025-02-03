"""Tests for FileInfoList class."""

import os

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.file_info import FileInfo
from ostruct.cli.file_list import FileInfoList
from ostruct.cli.security import SecurityManager


@pytest.fixture
def security_manager() -> SecurityManager:
    """Create a SecurityManager instance for testing."""
    return SecurityManager(base_dir=os.getcwd())


def test_file_list_single_file(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test FileInfoList with a single file."""
    fs.create_file("test.txt", contents="hello")
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )
    files = FileInfoList([file_info])
    assert len(files) == 1
    assert files.content == "hello"  # Test direct content access
    assert files[0].content == "hello"  # Test list access
    assert files.path == "test.txt"


def test_file_list_multiple_files(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test FileInfoList with multiple files."""
    fs.create_file("test1.txt", contents="hello")
    fs.create_file("test2.txt", contents="world")
    files = FileInfoList(
        [
            FileInfo.from_path("test1.txt", security_manager=security_manager),
            FileInfo.from_path("test2.txt", security_manager=security_manager),
        ]
    )
    assert len(files) == 2
    assert files.content == ["hello", "world"]  # Test direct content access
    assert files[0].content == "hello"  # Test list access
    assert files[1].content == "world"
    assert files.path == ["test1.txt", "test2.txt"]


def test_file_list_empty() -> None:
    """Test FileInfoList with no files."""
    files = FileInfoList([])
    with pytest.raises(ValueError, match="No files in FileInfoList"):
        _ = files.content
    with pytest.raises(ValueError, match="No files in FileInfoList"):
        _ = files.path
    with pytest.raises(ValueError, match="No files in FileInfoList"):
        _ = files.abs_path
    with pytest.raises(ValueError, match="No files in FileInfoList"):
        _ = files.size


def test_file_list_str_repr(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test string representations of FileInfoList."""
    fs.create_file("test.txt", contents="hello")
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )
    files = FileInfoList([file_info])

    # Test empty list
    empty_files = FileInfoList([])
    assert str(empty_files) == "FileInfoList([])"
    assert repr(empty_files) == "FileInfoList([])"

    # Test single file
    assert str(files) == "FileInfoList(['test.txt'])"
    assert repr(files) == "FileInfoList(['test.txt'])"

    # Test multiple files
    fs.create_file("test2.txt", contents="world")
    file_info2 = FileInfo.from_path(
        "test2.txt", security_manager=security_manager
    )
    files = FileInfoList([file_info, file_info2])
    assert str(files) == "FileInfoList(['test.txt', 'test2.txt'])"
    assert repr(files) == "FileInfoList(['test.txt', 'test2.txt'])"
