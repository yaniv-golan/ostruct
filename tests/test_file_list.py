"""Tests for FileInfoList class."""

import os
import threading

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


def test_file_list_minimal_thread_safety(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test minimal thread safety of FileInfoList operations."""
    fs.create_file("test.txt", contents="hello")
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )
    file_list = FileInfoList([file_info])

    def worker() -> None:
        file_list.append(file_info)
        file_list.remove(file_info)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=1.0)

    if thread.is_alive():
        pytest.fail("Thread did not complete in time - possible deadlock")

    assert len(file_list) == 1


def test_file_list_slicing(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test slicing behavior of FileInfoList."""
    # Create test files
    for i in range(5):
        fs.create_file(f"test{i}.txt", contents=f"content{i}")

    # Create FileInfoList with 5 files
    files = [
        FileInfo.from_path(f"test{i}.txt", security_manager=security_manager)
        for i in range(5)
    ]
    file_list = FileInfoList(files)

    # Test basic slicing
    sliced = file_list[1:3]
    assert isinstance(sliced, FileInfoList)
    assert len(sliced) == 2
    assert sliced[0].content == "content1"
    assert sliced[1].content == "content2"

    # Test step slicing
    stepped = file_list[::2]
    assert isinstance(stepped, FileInfoList)
    assert len(stepped) == 3
    assert [f.content for f in stepped] == ["content0", "content2", "content4"]

    # Test negative indices
    reversed_slice = file_list[-2:]
    assert isinstance(reversed_slice, FileInfoList)
    assert len(reversed_slice) == 2
    assert [f.content for f in reversed_slice] == ["content3", "content4"]

    # Test empty slice
    empty_slice = file_list[2:2]
    assert isinstance(empty_slice, FileInfoList)
    assert len(empty_slice) == 0


def test_file_list_concurrent_iteration(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test concurrent iteration and modification of FileInfoList."""
    print("Starting concurrent iteration test")  # Debug print

    # Create test files
    fs.create_file("test0.txt", contents="content0")

    # Create initial FileInfoList with just one file
    files = [
        FileInfo.from_path("test0.txt", security_manager=security_manager)
    ]
    file_list = FileInfoList(files)

    def modifier() -> None:
        print("Modifier starting")  # Debug print
        for _ in range(2):  # Minimal iterations
            file_info = FileInfo.from_path(
                "test0.txt", security_manager=security_manager
            )
            file_list.append(file_info)
            file_list.pop()
        print("Modifier finished")  # Debug print

    def iterator() -> None:
        print("Iterator starting")  # Debug print
        for _ in range(2):  # Minimal iterations
            for file_info in file_list:
                assert isinstance(file_info, FileInfo)
        print("Iterator finished")  # Debug print

    # Create and start threads
    modifier_thread = threading.Thread(target=modifier, name="modifier")
    iterator_thread = threading.Thread(target=iterator, name="iterator")

    print("Starting threads")  # Debug print
    modifier_thread.start()
    iterator_thread.start()

    # Wait with timeout
    print("Waiting for threads")  # Debug print
    modifier_thread.join(timeout=2.0)  # Shorter timeout
    iterator_thread.join(timeout=2.0)  # Shorter timeout

    if modifier_thread.is_alive() or iterator_thread.is_alive():
        print("Threads are still alive!")  # Debug print
        pytest.fail("Thread did not complete in time - possible deadlock")

    print("All threads completed")  # Debug print
    assert len(file_list) == 1  # Should be back to original length


def test_file_list_thread_safety_with_nested_calls(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test thread safety with nested method calls."""
    # Create test files
    fs.create_file("test1.txt", contents="hello")
    fs.create_file("test2.txt", contents="world")

    # Create FileInfoList with initial file
    file_info1 = FileInfo.from_path(
        "test1.txt", security_manager=security_manager
    )
    file_list = FileInfoList([file_info1])

    def worker() -> None:
        # This will trigger nested lock acquisitions:
        # 1. content property acquires lock
        # 2. len() inside content acquires lock
        # 3. __getitem__ inside content acquires lock
        _ = file_list.content

        # Test modification while holding lock
        file_info2 = FileInfo.from_path(
            "test2.txt", security_manager=security_manager
        )
        with file_list._lock:
            file_list.append(file_info2)
            assert len(file_list) == 2  # Nested lock acquisition

    # Run worker in thread
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=1.0)

    if thread.is_alive():
        pytest.fail("Thread did not complete in time - possible deadlock")

    # Verify final state
    assert len(file_list) == 2


def test_file_list_slicing_thread_safety(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test thread safety of slicing operations."""
    # Create test files
    for i in range(5):
        fs.create_file(f"test{i}.txt", contents=f"content{i}")

    # Create FileInfoList with files
    files = [
        FileInfo.from_path(f"test{i}.txt", security_manager=security_manager)
        for i in range(5)
    ]
    file_list = FileInfoList(files)

    def slicer() -> None:
        # Test various slice operations
        sliced = file_list[1:3]
        assert isinstance(sliced, FileInfoList)
        assert len(sliced) == 2
        assert sliced[0].content == "content1"

        # Test step slicing
        stepped = file_list[::2]
        assert isinstance(stepped, FileInfoList)
        assert len(stepped) == 3

    def modifier() -> None:
        # Modify list while slicing is happening
        file_info = FileInfo.from_path(
            "test0.txt", security_manager=security_manager
        )
        file_list.append(file_info)
        file_list.pop()

    # Run threads
    slicer_thread = threading.Thread(target=slicer)
    modifier_thread = threading.Thread(target=modifier)

    slicer_thread.start()
    modifier_thread.start()

    slicer_thread.join(timeout=1.0)
    modifier_thread.join(timeout=1.0)

    if slicer_thread.is_alive() or modifier_thread.is_alive():
        pytest.fail("Thread(s) did not complete in time - possible deadlock")

    # Verify final state
    assert len(file_list) == 5  # Back to original length
