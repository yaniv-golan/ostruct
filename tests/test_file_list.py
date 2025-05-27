"""Tests for FileInfoList class."""

import threading

import pytest
from ostruct.cli.file_info import FileInfo
from ostruct.cli.file_list import FileInfoList
from ostruct.cli.security import SecurityManager
from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.fixture
def security_manager() -> SecurityManager:
    """Create a SecurityManager instance for testing."""
    return SecurityManager(base_dir="/test_workspace/base")


def test_file_list_single_file(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test FileInfoList with a single file."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    test_file = "/test_workspace/base/test.txt"
    fs.create_file(test_file, contents="hello")
    file_info = FileInfo.from_path(
        test_file, security_manager=security_manager
    )
    files = FileInfoList([file_info])
    assert len(files) == 1
    assert files.content == "hello"  # Test direct content access
    assert files[0].content == "hello"  # Test list access
    assert files.path == "test.txt"  # Path relative to base_dir


def test_file_list_multiple_files(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test FileInfoList with multiple files."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test1.txt", contents="hello")
    fs.create_file("/test_workspace/base/test2.txt", contents="world")
    files = FileInfoList(
        [
            FileInfo.from_path(
                "/test_workspace/base/test1.txt",
                security_manager=security_manager,
            ),
            FileInfo.from_path(
                "/test_workspace/base/test2.txt",
                security_manager=security_manager,
            ),
        ]
    )
    assert len(files) == 2
    assert files.content == ["hello", "world"]  # Test direct content access
    assert files[0].content == "hello"  # Test list access
    assert files[1].content == "world"
    assert files.path == [
        "test1.txt",
        "test2.txt",
    ]  # Paths relative to base_dir


def test_file_list_empty(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test empty FileInfoList."""
    files = FileInfoList([])
    assert len(files) == 0
    assert files.path == []  # Empty list for path
    assert files.content == []  # Empty list for content


def test_file_list_str_repr(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test string representations of FileInfoList."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="hello")
    file_info = FileInfo.from_path(
        "/test_workspace/base/test.txt", security_manager=security_manager
    )
    files = FileInfoList([file_info])

    # Test empty list
    empty_files = FileInfoList([])
    assert str(empty_files) == "FileInfoList([])"
    assert repr(empty_files) == "FileInfoList([])"

    # Test single file
    assert (
        str(files) == "FileInfoList(['test.txt'])"
    )  # Path relative to base_dir
    assert (
        repr(files) == "FileInfoList(['test.txt'])"
    )  # Path relative to base_dir


def test_file_list_minimal_thread_safety(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test minimal thread safety of FileInfoList operations."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="hello")
    file_info = FileInfo.from_path(
        "/test_workspace/base/test.txt", security_manager=security_manager
    )
    files = FileInfoList([file_info])

    # Test concurrent access to content and path
    def read_content() -> None:
        assert files.content == "hello"

    def read_path() -> None:
        assert files.path == "test.txt"

    threads = [
        threading.Thread(target=read_content),
        threading.Thread(target=read_path),
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def test_file_list_slicing(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test slicing behavior of FileInfoList."""
    # Create test files
    fs.makedirs("/test_workspace/base", exist_ok=True)
    for i in range(5):
        fs.create_file(
            f"/test_workspace/base/test{i}.txt", contents=f"content{i}"
        )

    # Create FileInfoList with 5 files
    files = [
        FileInfo.from_path(
            f"/test_workspace/base/test{i}.txt",
            security_manager=security_manager,
        )
        for i in range(5)
    ]
    file_list = FileInfoList(files)

    # Test various slicing operations
    assert len(file_list[1:3]) == 2
    assert file_list[1:3].content == ["content1", "content2"]
    assert file_list[1:3].path == ["test1.txt", "test2.txt"]


def test_file_list_concurrent_iteration(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test concurrent iteration and modification of FileInfoList."""
    # Create test files
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test0.txt", contents="content0")

    # Create initial FileInfoList with just one file
    files = [
        FileInfo.from_path(
            "/test_workspace/base/test0.txt", security_manager=security_manager
        )
    ]
    file_list = FileInfoList(files)

    # Create additional files during the test
    def add_files() -> None:
        for i in range(1, 3):
            fs.create_file(
                f"/test_workspace/base/test{i}.txt", contents=f"content{i}"
            )
            file_info = FileInfo.from_path(
                f"/test_workspace/base/test{i}.txt",
                security_manager=security_manager,
            )
            file_list.append(file_info)

    def iterate_files() -> None:
        for file_info in file_list:
            assert file_info.content.startswith("content")

    threads = [
        threading.Thread(target=add_files),
        threading.Thread(target=iterate_files),
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(file_list) == 3


def test_file_list_thread_safety_with_nested_calls(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test thread safety with nested method calls."""
    # Create test files
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test1.txt", contents="hello")
    fs.create_file("/test_workspace/base/test2.txt", contents="world")

    # Create FileInfoList with initial file
    file_info1 = FileInfo.from_path(
        "/test_workspace/base/test1.txt", security_manager=security_manager
    )
    file_info2 = FileInfo.from_path(
        "/test_workspace/base/test2.txt", security_manager=security_manager
    )
    files = FileInfoList([file_info1])

    # Use a lock to ensure only one thread appends at a time
    append_lock = threading.Lock()

    def modify_and_read() -> None:
        # Ensure only one thread appends the file
        with append_lock:
            if len(files) == 1:  # Only append if not already done
                files.append(file_info2)
        # These operations are thread-safe and can be done concurrently
        assert len(files) > 0
        assert files.content  # This will acquire the lock
        assert files.path  # This will also acquire the lock

    threads = [threading.Thread(target=modify_and_read) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(files) == 2  # Should have both files


def test_file_list_slicing_thread_safety(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test thread safety of slicing operations."""
    # Create test files
    fs.makedirs("/test_workspace/base", exist_ok=True)
    for i in range(5):
        fs.create_file(
            f"/test_workspace/base/test{i}.txt", contents=f"content{i}"
        )

    # Create FileInfoList with files
    files = [
        FileInfo.from_path(
            f"/test_workspace/base/test{i}.txt",
            security_manager=security_manager,
        )
        for i in range(5)
    ]
    file_list = FileInfoList(files)

    def slice_and_read() -> None:
        sliced = file_list[1:3]
        assert len(sliced) == 2
        assert sliced.content == ["content1", "content2"]
        assert sliced.path == ["test1.txt", "test2.txt"]

    threads = [threading.Thread(target=slice_and_read) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
