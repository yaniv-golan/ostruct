"""Tests for template filters, specifically the single filter."""

import pytest
from jinja2 import TemplateRuntimeError
from ostruct.cli.file_info import FileInfo
from ostruct.cli.file_list import FileInfoList
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_env import create_jinja_env
from ostruct.cli.template_filters import (
    files_filter,
    is_fileish,
    single_filter,
)
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


def test_files_filter_with_file_info(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test files filter with FileInfo objects."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="test content")

    file_info = FileInfo.from_path(
        "/test_workspace/base/test.txt", security_manager=security_manager
    )

    # Test with single FileInfo
    result = files_filter(file_info)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] is file_info


def test_files_filter_with_file_info_list(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test files filter with FileInfoList."""
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
    )

    # Test with FileInfoList
    result = files_filter(file_list)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].name == "file1.txt"
    assert result[1].name == "file2.txt"


def test_files_filter_with_regular_list() -> None:
    """Test files filter with regular Python lists."""
    # Test with regular list
    regular_list = ["item1", "item2", "item3"]
    result = files_filter(regular_list)
    assert result == regular_list
    assert isinstance(result, list)


def test_files_filter_with_non_iterable() -> None:
    """Test files filter with non-iterable values."""
    # Test with string (should be wrapped as single item)
    result = files_filter("string")
    assert result == ["string"]  # String should be treated as single item

    # Test with number (non-iterable)
    result = files_filter(42)
    assert result == [42]

    # Test with None (non-iterable)
    result = files_filter(None)
    assert result == [None]


def test_is_fileish_with_file_info(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test is_fileish test with FileInfo objects."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="test content")

    file_info = FileInfo.from_path(
        "/test_workspace/base/test.txt", security_manager=security_manager
    )

    # Single FileInfo should be fileish
    assert is_fileish(file_info) is True


def test_is_fileish_with_file_info_list(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test is_fileish test with FileInfoList."""
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
    )

    # FileInfoList should be fileish
    assert is_fileish(file_list) is True


def test_is_fileish_with_list_of_file_info(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test is_fileish test with regular list of FileInfo objects."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="test content")

    file_info = FileInfo.from_path(
        "/test_workspace/base/test.txt", security_manager=security_manager
    )

    # Regular list containing only FileInfo objects should be fileish
    file_list = [file_info]
    assert is_fileish(file_list) is True


def test_is_fileish_with_non_file_values() -> None:
    """Test is_fileish test with non-file values."""
    # Test with non-file values
    assert is_fileish("string") is False
    assert is_fileish(42) is False
    assert is_fileish([1, 2, 3]) is False
    assert is_fileish({"key": "value"}) is False
    assert is_fileish(None) is False


def test_is_fileish_with_mixed_list(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test is_fileish test with mixed list containing files and non-files."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    fs.create_file("/test_workspace/base/test.txt", contents="test content")

    file_info = FileInfo.from_path(
        "/test_workspace/base/test.txt", security_manager=security_manager
    )

    # Mixed list should not be fileish
    mixed_list = [file_info, "string", 42]
    assert is_fileish(mixed_list) is False


def test_is_fileish_with_empty_list() -> None:
    """Test is_fileish test with empty list."""
    # Empty list should be considered fileish (vacuously true)
    assert is_fileish([]) is True


def test_is_fileish_with_non_iterable() -> None:
    """Test is_fileish test with non-iterable values."""
    # Non-iterable values should not be fileish
    assert is_fileish(42) is False
    assert is_fileish(None) is False


class TestSafeGetFunction:
    """Test the safe_get global function."""

    def test_multi_agent_debate_pattern(self) -> None:
        """Test the specific pattern from multi-agent debate example."""
        env, _ = create_jinja_env()

        # Test with safe_get function
        template = env.from_string(
            "{{ safe_get('transcript.content', 'This is the first round - no previous transcript.') }}"
        )

        # Test with transcript content
        result = template.render(
            {"transcript": {"content": "Previous round content"}}
        )
        assert result == "Previous round content"

        # Test without transcript
        result = template.render({})
        assert result == "This is the first round - no previous transcript."

        # Test with empty transcript content
        result = template.render({"transcript": {"content": ""}})
        assert result == "This is the first round - no previous transcript."

    def test_empty_values(self) -> None:
        """Test that safe_get handles empty values correctly."""
        env, _ = create_jinja_env()

        # Test with None value
        template = env.from_string("{{ safe_get('obj.content', 'Default') }}")
        result = template.render({"obj": {"content": None}})
        assert result == "Default"

        # Test with empty string
        result = template.render({"obj": {"content": ""}})
        assert result == "Default"

        # Test with whitespace-only string
        result = template.render({"obj": {"content": "   "}})
        assert result == "Default"

        # Test with empty collections
        result = template.render({"obj": {"content": []}})
        assert result == "Default"

        result = template.render({"obj": {"content": {}}})
        assert result == "Default"

    def test_safe_get_function(self) -> None:
        """Test the safe_get global function for safe nested access."""
        env, _ = create_jinja_env()

        # Test safe_get with existing nested path
        template = env.from_string(
            "{{ safe_get('obj.nested.value', 'Default') }}"
        )
        result = template.render({"obj": {"nested": {"value": "Found"}}})
        assert result == "Found"

        # Test safe_get with missing intermediate object
        result = template.render({"obj": {}})
        assert result == "Default"

        # Test safe_get with completely missing root object
        result = template.render({})
        assert result == "Default"

        # Test safe_get with empty value
        result = template.render({"obj": {"nested": {"value": ""}}})
        assert result == "Default"

    def test_falsy_values_preserved(self) -> None:
        """Test that safe_get preserves intentional falsy values."""
        env, _ = create_jinja_env()
        template = env.from_string("{{ safe_get('obj.value', 'Default') }}")

        # Boolean False should be preserved (rendered as "False")
        result = template.render({"obj": {"value": False}})
        assert result == "False"

        # Number 0 should be preserved (rendered as "0")
        result = template.render({"obj": {"value": 0}})
        assert result == "0"
