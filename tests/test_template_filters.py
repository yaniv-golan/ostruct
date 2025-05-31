"""Tests for template filters, specifically the single filter."""

import pytest
from jinja2 import TemplateRuntimeError
from ostruct.cli.file_info import FileInfo
from ostruct.cli.file_list import FileInfoList
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_filters import single_filter
from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.fixture
def security_manager() -> SecurityManager:
    """Create a SecurityManager instance for testing."""
    return SecurityManager(base_dir="/test_workspace/base")


def test_single_filter_with_file_info_list_single_item(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test single filter with FileInfoList containing exactly one item."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="content")

    file_info = FileInfo.from_path(
        "/test_workspace/base/test.txt", security_manager=security_manager
    )
    file_list = FileInfoList([file_info], var_alias="test_file")

    # Should return the single FileInfo object
    result = single_filter(file_list)
    assert isinstance(result, FileInfo)
    assert result.content == "content"
    assert result.name == "test.txt"


def test_single_filter_with_file_info_list_empty(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test single filter with empty FileInfoList raises error."""
    empty_list = FileInfoList([], var_alias="empty_files")

    with pytest.raises(TemplateRuntimeError) as exc_info:
        single_filter(empty_list)

    error_msg = str(exc_info.value)
    assert "expected exactly 1 file for 'empty_files'" in error_msg
    assert "got 0" in error_msg


def test_single_filter_with_file_info_list_multiple_items(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test single filter with FileInfoList containing multiple items raises error."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/file1.txt", contents="content1")
    fs.create_file("/test_workspace/base/file2.txt", contents="content2")

    file_list = FileInfoList(
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
        var_alias="multiple_files",
    )

    with pytest.raises(TemplateRuntimeError) as exc_info:
        single_filter(file_list)

    error_msg = str(exc_info.value)
    assert "expected exactly 1 file for 'multiple_files'" in error_msg
    assert "got 2" in error_msg


def test_single_filter_with_file_info_list_no_var_alias(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test single filter with FileInfoList without var_alias uses fallback."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/file1.txt", contents="content1")
    fs.create_file("/test_workspace/base/file2.txt", contents="content2")

    file_list = FileInfoList(
        [
            FileInfo.from_path(
                "/test_workspace/base/file1.txt",
                security_manager=security_manager,
            ),
            FileInfo.from_path(
                "/test_workspace/base/file2.txt",
                security_manager=security_manager,
            ),
        ]
    )  # No var_alias provided

    with pytest.raises(TemplateRuntimeError) as exc_info:
        single_filter(file_list)

    error_msg = str(exc_info.value)
    assert (
        "expected exactly 1 file for 'list'" in error_msg
    )  # Should use fallback
    assert "got 2" in error_msg


def test_single_filter_with_regular_list_single_item() -> None:
    """Test single filter with regular Python list containing one item."""
    test_list = ["single_item"]
    result = single_filter(test_list)
    assert result == "single_item"


def test_single_filter_with_regular_list_empty() -> None:
    """Test single filter with empty regular Python list raises error."""
    empty_list: list[str] = []

    with pytest.raises(TemplateRuntimeError) as exc_info:
        single_filter(empty_list)

    error_msg = str(exc_info.value)
    assert "expected exactly 1 item" in error_msg
    assert "got 0" in error_msg


def test_single_filter_with_regular_list_multiple_items() -> None:
    """Test single filter with regular Python list containing multiple items raises error."""
    multi_list = ["item1", "item2", "item3"]

    with pytest.raises(TemplateRuntimeError) as exc_info:
        single_filter(multi_list)

    error_msg = str(exc_info.value)
    assert "expected exactly 1 item" in error_msg
    assert "got 3" in error_msg


def test_single_filter_with_file_info_passthrough(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test single filter passes through FileInfo objects unchanged."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="content")

    file_info = FileInfo.from_path(
        "/test_workspace/base/test.txt", security_manager=security_manager
    )

    # Should pass through unchanged
    result = single_filter(file_info)
    assert result is file_info
    assert result.content == "content"


def test_single_filter_with_non_list_types() -> None:
    """Test single filter passes through non-list types unchanged."""
    # Test string
    result = single_filter("test_string")
    assert result == "test_string"

    # Test integer
    result = single_filter(42)
    assert result == 42

    # Test None
    result = single_filter(None)
    assert result is None

    # Test dict
    test_dict = {"key": "value"}
    result = single_filter(test_dict)
    assert result is test_dict


def test_single_filter_with_tuple() -> None:
    """Test single filter with tuple (has __len__ and __getitem__)."""
    # Single item tuple
    single_tuple = ("item",)
    result = single_filter(single_tuple)
    assert result == "item"

    # Multiple item tuple
    multi_tuple = ("item1", "item2")
    with pytest.raises(TemplateRuntimeError) as exc_info:
        single_filter(multi_tuple)

    error_msg = str(exc_info.value)
    assert "expected exactly 1 item" in error_msg
    assert "got 2" in error_msg


def test_single_filter_import_fallback() -> None:
    """Test single filter behavior when imports fail."""
    # This test simulates the fallback behavior when FileInfoList/FileInfo imports fail
    # We can't easily mock the imports, but we can test with objects that look like lists

    class MockList:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            return iter(self.items)

    # Single item
    mock_single = MockList(["item"])
    result = single_filter(mock_single)
    assert result == "item"

    # Multiple items
    mock_multi = MockList(["item1", "item2"])
    with pytest.raises(TemplateRuntimeError) as exc_info:
        single_filter(mock_multi)

    error_msg = str(exc_info.value)
    assert "expected exactly 1 item" in error_msg
    assert "got 2" in error_msg
