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

    # Test empty list
    empty_files = FileInfoList([])
    assert str(empty_files) == "FileInfoList([])"
    assert repr(empty_files) == "FileInfoList([])"

    # Test single file from file mapping (not from_dir)
    files = FileInfoList([file_info], from_dir=False, var_alias="test_file")
    expected_str = (
        "[File 'test.txt' - Use { test_file.content } to access file content]"
    )
    assert str(files) == expected_str
    assert repr(files) == expected_str

    # Test single file from directory mapping (from_dir=True)
    files_from_dir = FileInfoList(
        [file_info], from_dir=True, var_alias="dir_files"
    )
    expected_dir_str = "[Directory file 'test.txt' - Use { dir_files[0].content } or { dir_files|single.content } to access content]"
    assert str(files_from_dir) == expected_dir_str

    # Test multiple files
    fs.create_file("/test_workspace/base/test2.txt", contents="world")
    file_info2 = FileInfo.from_path(
        "/test_workspace/base/test2.txt", security_manager=security_manager
    )
    multi_files = FileInfoList(
        [file_info, file_info2], var_alias="multi_files"
    )
    expected_multi_str = "[2 files: test.txt, test2.txt - Use { multi_files[0].content } or loop over files]"
    assert str(multi_files) == expected_multi_str


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


def test_file_list_name_property_adaptive_behavior(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test FileInfoList.name adaptive behavior."""
    fs.makedirs("/test_workspace/base", exist_ok=True)

    # Test empty list
    empty_files = FileInfoList([])
    assert empty_files.name == []

    # Test single file from file mapping (not from_dir)
    fs.create_file("/test_workspace/base/single.txt", contents="content")
    single_file = FileInfo.from_path(
        "/test_workspace/base/single.txt", security_manager=security_manager
    )
    single_files = FileInfoList(
        [single_file], from_dir=False, var_alias="single_var"
    )
    assert single_files.name == "single.txt"  # Returns scalar string
    assert isinstance(single_files.name, str)

    # Test single file from directory mapping (from_dir=True)
    single_files_from_dir = FileInfoList(
        [single_file], from_dir=True, var_alias="dir_var"
    )
    assert single_files_from_dir.name == ["single.txt"]  # Returns list
    assert isinstance(single_files_from_dir.name, list)

    # Test multiple files
    fs.create_file("/test_workspace/base/file1.txt", contents="content1")
    fs.create_file("/test_workspace/base/file2.txt", contents="content2")
    multi_files = FileInfoList(
        [
            FileInfo.from_path(
                "/test_workspace/base/file1.txt",
                security_manager=security_manager,
            ),
            FileInfo.from_path(
                "/test_workspace/base/file2.txt",
                security_manager=security_manager,
            ),
        ],
        from_dir=False,
        var_alias="multi_var",
    )
    assert multi_files.name == ["file1.txt", "file2.txt"]  # Returns list
    assert isinstance(multi_files.name, list)


def test_file_list_names_property_always_list(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test FileInfoList.names always returns a list."""
    fs.makedirs("/test_workspace/base", exist_ok=True)

    # Test empty list
    empty_files = FileInfoList([])
    assert empty_files.names == []
    assert isinstance(empty_files.names, list)

    # Test single file (should still return list)
    fs.create_file("/test_workspace/base/single.txt", contents="content")
    single_file = FileInfo.from_path(
        "/test_workspace/base/single.txt", security_manager=security_manager
    )
    single_files = FileInfoList(
        [single_file], from_dir=False, var_alias="single_var"
    )
    assert single_files.names == ["single.txt"]  # Always returns list
    assert isinstance(single_files.names, list)

    # Test multiple files
    fs.create_file("/test_workspace/base/file1.txt", contents="content1")
    fs.create_file("/test_workspace/base/file2.txt", contents="content2")
    multi_files = FileInfoList(
        [
            FileInfo.from_path(
                "/test_workspace/base/file1.txt",
                security_manager=security_manager,
            ),
            FileInfo.from_path(
                "/test_workspace/base/file2.txt",
                security_manager=security_manager,
            ),
        ],
        from_dir=False,
        var_alias="multi_var",
    )
    assert multi_files.names == ["file1.txt", "file2.txt"]
    assert isinstance(multi_files.names, list)


def test_file_list_getattr_error_messages(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test FileInfoList.__getattr__ provides helpful error messages."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/file1.txt", contents="content1")
    fs.create_file("/test_workspace/base/file2.txt", contents="content2")

    # Test multi-file list trying to access FileInfo attributes
    multi_files = FileInfoList(
        [
            FileInfo.from_path(
                "/test_workspace/base/file1.txt",
                security_manager=security_manager,
            ),
            FileInfo.from_path(
                "/test_workspace/base/file2.txt",
                security_manager=security_manager,
            ),
        ],
        from_dir=False,
        var_alias="test_files",
    )

    # Should raise AttributeError with helpful message for known FileInfo attributes
    with pytest.raises(AttributeError) as exc_info:
        _ = multi_files.encoding

    error_msg = str(exc_info.value)
    assert "test_files" in error_msg
    assert "contains 2 files" in error_msg
    assert "test_files[0].encoding" in error_msg
    assert "test_files|single.encoding" in error_msg

    # Test directory mapping (from_dir=True) with single file
    single_file_from_dir = FileInfoList(
        [
            FileInfo.from_path(
                "/test_workspace/base/file1.txt",
                security_manager=security_manager,
            )
        ],
        from_dir=True,
        var_alias="dir_files",
    )

    with pytest.raises(AttributeError) as exc_info:
        _ = single_file_from_dir.hash

    error_msg = str(exc_info.value)
    assert "dir_files" in error_msg
    assert "contains 1 files" in error_msg

    # Test unknown attribute (should get default AttributeError)
    with pytest.raises(AttributeError) as exc_info:
        _ = multi_files.unknown_attribute

    error_msg = str(exc_info.value)
    assert "FileInfoList" in error_msg
    assert "has no attribute 'unknown_attribute'" in error_msg


def test_file_list_var_alias_in_error_messages(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test that var_alias is properly used in error messages."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="content")

    # Test with custom var_alias
    files_with_alias = FileInfoList(
        [
            FileInfo.from_path(
                "/test_workspace/base/test.txt",
                security_manager=security_manager,
            )
        ],
        from_dir=True,
        var_alias="my_custom_files",
    )

    with pytest.raises(AttributeError) as exc_info:
        _ = (
            files_with_alias.encoding
        )  # This should trigger __getattr__ since from_dir=True

    error_msg = str(exc_info.value)
    assert "my_custom_files" in error_msg

    # Test without var_alias (should use fallback)
    files_no_alias = FileInfoList(
        [
            FileInfo.from_path(
                "/test_workspace/base/test.txt",
                security_manager=security_manager,
            )
        ],
        from_dir=True,
    )  # No var_alias provided

    with pytest.raises(AttributeError) as exc_info:
        _ = files_no_alias.encoding

    error_msg = str(exc_info.value)
    assert "file_list" in error_msg  # Should use fallback name
