"""Test file-sequence protocol implementation.

This module tests the file-sequence protocol that makes every file-bearing value
iterable while maintaining scalar access for single files.
"""

import pytest
from ostruct.cli.file_info import FileInfo
from ostruct.cli.file_list import FileInfoList
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_filters import files_filter, is_fileish
from pyfakefs.fake_filesystem import FakeFilesystem


class TestFileSequenceProtocol:
    """Test the file-sequence protocol implementation."""

    def test_file_info_is_iterable(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that FileInfo objects are iterable."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )

        file_info = FileInfo.from_path(
            "/test_workspace/base/test.txt", security_manager=security_manager
        )

        # Should be iterable
        files = list(file_info)
        assert len(files) == 1
        assert files[0] is file_info

        # Should work in for loop
        count = 0
        for file in file_info:
            count += 1
            assert file is file_info
        assert count == 1

    def test_file_info_first_property(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that FileInfo.first returns itself."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )

        file_info = FileInfo.from_path(
            "/test_workspace/base/test.txt", security_manager=security_manager
        )

        assert file_info.first is file_info

    def test_file_info_is_collection_property(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that FileInfo.is_collection returns False."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )

        file_info = FileInfo.from_path(
            "/test_workspace/base/test.txt", security_manager=security_manager
        )

        assert file_info.is_collection is False

    def test_file_info_list_first_property(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that FileInfoList.first returns the first file."""
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

        first_file = file_list.first
        assert first_file.name == "file1.txt"
        assert first_file.content == "content1"

    def test_file_info_list_first_property_empty(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that FileInfoList.first raises error on empty list."""
        file_list = FileInfoList([])

        with pytest.raises(ValueError) as exc_info:
            _ = file_list.first

        assert "No files in 'file_list'" in str(exc_info.value)
        assert "Cannot access .first property" in str(exc_info.value)

    def test_file_info_list_is_collection_property(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that FileInfoList.is_collection returns True."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )

        file_list = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/test.txt",
                    security_manager=security_manager,
                )
            ]
        )

        assert file_list.is_collection is True

    def test_uniform_iteration_pattern(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that the same iteration pattern works for both single files and collections."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/single.txt", contents="single content"
        )
        fs.create_file(
            "/test_workspace/base/multi1.txt", contents="multi content 1"
        )
        fs.create_file(
            "/test_workspace/base/multi2.txt", contents="multi content 2"
        )

        # Single file
        single_file = FileInfo.from_path(
            "/test_workspace/base/single.txt",
            security_manager=security_manager,
        )

        # Multiple files
        multi_files = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/multi1.txt",
                    security_manager=security_manager,
                ),
                FileInfo.from_path(
                    "/test_workspace/base/multi2.txt",
                    security_manager=security_manager,
                ),
            ]
        )

        # Test uniform iteration pattern
        def process_files(files):
            """Process files using uniform iteration pattern."""
            results = []
            for file in files:
                results.append(f"{file.name}: {file.content}")
            return results

        # Should work the same way for both
        single_results = process_files(single_file)
        multi_results = process_files(multi_files)

        assert single_results == ["single.txt: single content"]
        assert multi_results == [
            "multi1.txt: multi content 1",
            "multi2.txt: multi content 2",
        ]

    def test_uniform_first_access_pattern(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that .first works uniformly for both single files and collections."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/single.txt", contents="single content"
        )
        fs.create_file(
            "/test_workspace/base/multi1.txt", contents="multi content 1"
        )
        fs.create_file(
            "/test_workspace/base/multi2.txt", contents="multi content 2"
        )

        # Single file
        single_file = FileInfo.from_path(
            "/test_workspace/base/single.txt",
            security_manager=security_manager,
        )

        # Multiple files
        multi_files = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/multi1.txt",
                    security_manager=security_manager,
                ),
                FileInfo.from_path(
                    "/test_workspace/base/multi2.txt",
                    security_manager=security_manager,
                ),
            ]
        )

        # Test uniform .first access
        def get_first_content(files):
            """Get content of first file using uniform pattern."""
            return files.first.content

        # Should work the same way for both
        assert get_first_content(single_file) == "single content"
        assert get_first_content(multi_files) == "multi content 1"

    def test_scalar_access_still_works(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that scalar access still works for single files."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )

        file_info = FileInfo.from_path(
            "/test_workspace/base/test.txt", security_manager=security_manager
        )

        # Scalar access should still work
        assert file_info.path == "test.txt"
        assert file_info.content == "test content"
        assert file_info.name == "test.txt"

    def test_files_filter(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test the files filter that ensures iterability."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/single.txt", contents="single content"
        )
        fs.create_file(
            "/test_workspace/base/multi1.txt", contents="multi content 1"
        )
        fs.create_file(
            "/test_workspace/base/multi2.txt", contents="multi content 2"
        )

        # Single file
        single_file = FileInfo.from_path(
            "/test_workspace/base/single.txt",
            security_manager=security_manager,
        )

        # Multiple files
        multi_files = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/multi1.txt",
                    security_manager=security_manager,
                ),
                FileInfo.from_path(
                    "/test_workspace/base/multi2.txt",
                    security_manager=security_manager,
                ),
            ]
        )

        # Test files filter
        single_filtered = files_filter(single_file)
        multi_filtered = files_filter(multi_files)

        # Should return lists in both cases
        assert isinstance(single_filtered, list)
        assert isinstance(multi_filtered, list)

        assert len(single_filtered) == 1
        assert len(multi_filtered) == 2

        assert single_filtered[0] is single_file
        assert multi_filtered[0].name == "multi1.txt"
        assert multi_filtered[1].name == "multi2.txt"

    def test_files_filter_with_non_iterable(self) -> None:
        """Test files filter with non-iterable values."""
        # Test with a non-iterable value
        result = files_filter("not iterable")
        assert result == ["not iterable"]

        # Test with number
        result = files_filter(42)
        assert result == [42]

    def test_is_fileish_test(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test the is_fileish template test function."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )

        # Single file
        single_file = FileInfo.from_path(
            "/test_workspace/base/test.txt", security_manager=security_manager
        )

        # Multiple files
        multi_files = FileInfoList([single_file])

        # Test is_fileish
        assert is_fileish(single_file) is True
        assert is_fileish(multi_files) is True

        # Test with non-file values
        assert is_fileish("string") is False
        assert is_fileish(42) is False
        assert is_fileish([1, 2, 3]) is False
        assert is_fileish({"key": "value"}) is False

        # Test with mixed list (should be False)
        mixed_list = [single_file, "string"]
        assert is_fileish(mixed_list) is False

    def test_is_fileish_with_empty_list(self) -> None:
        """Test is_fileish with empty list."""
        assert (
            is_fileish([]) is True
        )  # Empty list should be considered fileish

    def test_template_usage_examples(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test template usage examples from the specification."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/code1.py", contents="print('hello')"
        )
        fs.create_file(
            "/test_workspace/base/code2.py", contents="print('world')"
        )

        # Single file case
        single_code = FileInfo.from_path(
            "/test_workspace/base/code1.py", security_manager=security_manager
        )

        # Multiple files case
        multi_code = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/code1.py",
                    security_manager=security_manager,
                ),
                FileInfo.from_path(
                    "/test_workspace/base/code2.py",
                    security_manager=security_manager,
                ),
            ]
        )

        # Test the main template pattern from the spec:
        # {% for file in code %}
        # ## {{ file.path }}
        # {{ file.content }}
        # {% endfor %}

        def template_logic(code_var):
            """Simulate the template logic."""
            results = []
            for file in code_var:
                results.append(f"## {file.path}")
                results.append(file.content)
            return results

        # Should work identically for both cases
        single_result = template_logic(single_code)
        multi_result = template_logic(multi_code)

        assert single_result == ["## code1.py", "print('hello')"]
        assert multi_result == [
            "## code1.py",
            "print('hello')",
            "## code2.py",
            "print('world')",
        ]

        # Test .first access pattern from the spec:
        # {{ code.first.content }}
        assert single_code.first.content == "print('hello')"
        assert multi_code.first.content == "print('hello')"

    def test_backward_compatibility(
        self, fs: FakeFilesystem, security_manager: SecurityManager
    ) -> None:
        """Test that existing template patterns still work."""
        fs.makedirs("/test_workspace/base", exist_ok=True)
        fs.create_file(
            "/test_workspace/base/single.txt", contents="single content"
        )
        fs.create_file(
            "/test_workspace/base/multi1.txt", contents="multi content 1"
        )
        fs.create_file(
            "/test_workspace/base/multi2.txt", contents="multi content 2"
        )

        # Single file from file mapping (should allow scalar access)
        single_file_list = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/single.txt",
                    security_manager=security_manager,
                )
            ],
            from_dir=False,
        )  # from_dir=False indicates single file mapping

        # Multiple files (should require indexing)
        multi_files = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/multi1.txt",
                    security_manager=security_manager,
                ),
                FileInfo.from_path(
                    "/test_workspace/base/multi2.txt",
                    security_manager=security_manager,
                ),
            ]
        )

        # Single file scalar access should still work
        assert single_file_list.content == "single content"
        assert single_file_list.path == "single.txt"

        # Multiple files should still require explicit indexing
        with pytest.raises(ValueError):
            _ = multi_files.content

        # But indexing should work
        assert multi_files[0].content == "multi content 1"
        assert multi_files[1].content == "multi content 2"

        # New iteration pattern should work for both
        single_results = [f.content for f in single_file_list]
        multi_results = [f.content for f in multi_files]

        assert single_results == ["single content"]
        assert multi_results == ["multi content 1", "multi content 2"]
