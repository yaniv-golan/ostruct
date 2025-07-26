"""Tests for file error handling behavior in CLI commands."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.ostruct.cli.commands.files import upload
from src.ostruct.cli.exit_codes import ExitCode
from src.ostruct.cli.utils.attachment_utils import AttachmentProcessor
from src.ostruct.cli.utils.file_errors import (
    BrokenSymlinkError,
    CollectionFileNotFoundError,
    DirectoryNotFoundError,
    FileNotFoundError,
    FilePermissionError,
    NoFilesMatchPatternError,
    NotADirectoryError,
    validate_collection_file_exists,
    validate_directory_exists,
    validate_file_exists,
)

# These tests rely heavily on pytest's real ``tmp_path`` fixture to create actual
# temporary files and directories. The pytest_collection_modifyitems hook in
# conftest.py automatically adds the no_fs marker to any test using tmp_path
# to prevent conflicts with the pyfakefs-based setup_test_fs fixture.


class TestFileValidationFunctions:
    """Test the core file validation functions."""

    def test_validate_file_exists_success(self, tmp_path):
        """Test successful file validation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Should not raise any exception
        validate_file_exists(test_file)

    def test_validate_file_exists_missing(self, tmp_path):
        """Test validation of missing file."""
        missing_file = tmp_path / "missing.txt"

        with pytest.raises(FileNotFoundError) as exc_info:
            validate_file_exists(missing_file)

        assert "File not found:" in str(exc_info.value)
        assert str(missing_file) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR

    @patch("os.access")
    def test_validate_file_exists_permission_denied(
        self, mock_access, tmp_path
    ):
        """Test validation of unreadable file."""
        test_file = tmp_path / "unreadable.txt"
        test_file.write_text("content")

        # Mock os.access to return False (permission denied)
        mock_access.return_value = False

        with pytest.raises(FilePermissionError) as exc_info:
            validate_file_exists(test_file)

        assert "Permission denied:" in str(exc_info.value)
        assert str(test_file) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR

    def test_validate_file_exists_broken_symlink(self, tmp_path):
        """Test validation of broken symlink."""
        # Create a symlink to a non-existent target
        target = tmp_path / "nonexistent.txt"
        symlink = tmp_path / "broken_link.txt"

        try:
            symlink.symlink_to(target)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        with pytest.raises(BrokenSymlinkError) as exc_info:
            validate_file_exists(symlink)

        assert "Broken symlink:" in str(exc_info.value)
        assert str(symlink) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR

    def test_validate_file_exists_valid_symlink(self, tmp_path):
        """Test validation of valid symlink."""
        # Create a target file and symlink to it
        target = tmp_path / "target.txt"
        target.write_text("content")
        symlink = tmp_path / "valid_link.txt"

        try:
            symlink.symlink_to(target)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        # Should not raise any exception
        validate_file_exists(symlink)

    def test_validate_directory_exists_success(self, tmp_path):
        """Test successful directory validation."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Should not raise any exception
        validate_directory_exists(test_dir)

    def test_validate_directory_exists_missing(self, tmp_path):
        """Test validation of missing directory."""
        missing_dir = tmp_path / "missing_dir"

        with pytest.raises(DirectoryNotFoundError) as exc_info:
            validate_directory_exists(missing_dir)

        assert "Directory not found:" in str(exc_info.value)
        assert str(missing_dir) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR

    def test_validate_directory_exists_not_directory(self, tmp_path):
        """Test validation when path exists but is not a directory."""
        regular_file = tmp_path / "regular_file.txt"
        regular_file.write_text("content")

        with pytest.raises(NotADirectoryError) as exc_info:
            validate_directory_exists(regular_file)

        assert "Path is not a directory:" in str(exc_info.value)
        assert str(regular_file) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR

    def test_validate_collection_file_exists_success(self, tmp_path):
        """Test successful collection file validation."""
        collection_file = tmp_path / "collection.txt"
        collection_file.write_text("file1.txt\nfile2.txt\n")

        # Should not raise any exception
        validate_collection_file_exists(collection_file)

    def test_validate_collection_file_exists_missing(self, tmp_path):
        """Test validation of missing collection file."""
        missing_collection = tmp_path / "missing_collection.txt"

        with pytest.raises(CollectionFileNotFoundError) as exc_info:
            validate_collection_file_exists(missing_collection)

        assert "Collection file not found:" in str(exc_info.value)
        assert str(missing_collection) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR


class TestFilesUploadErrorHandling:
    """Test error handling in the files upload command."""

    def test_multiple_files_first_missing(self, tmp_path):
        """Test that upload fails on first missing file."""
        # Create one valid file
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("content")

        # Test with first file missing
        runner = CliRunner()
        result = runner.invoke(
            upload,
            [
                "--file",
                str(tmp_path / "missing.txt"),
                "--file",
                str(valid_file),
            ],
        )

        assert result.exit_code == ExitCode.FILE_ERROR
        assert "File not found:" in result.output
        assert "missing.txt" in result.output

    def test_path_not_directory(self, tmp_path):
        """Test that upload fails when --dir points to a file."""
        # Create a regular file
        regular_file = tmp_path / "not_a_dir.txt"
        regular_file.write_text("content")

        runner = CliRunner()
        result = runner.invoke(
            upload,
            [
                "--dir",
                str(regular_file),
            ],
        )

        assert result.exit_code == ExitCode.FILE_ERROR
        assert "Path is not a directory:" in result.output

    def test_collection_file_contains_missing_file(self, tmp_path):
        """Test that upload fails when collection file references missing files."""
        # Create collection file with missing file reference
        collection_file = tmp_path / "collection.txt"
        collection_file.write_text("missing_file.txt\n")

        runner = CliRunner()
        result = runner.invoke(
            upload,
            [
                "--collect",
                f"@{collection_file}",
            ],
        )

        assert result.exit_code == ExitCode.FILE_ERROR
        assert "File not found (from collection" in result.output

    def test_mixed_input_methods_directory_fails(self, tmp_path):
        """Test that upload fails when directory doesn't exist in mixed input."""
        # Create a valid file
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("content")

        runner = CliRunner()
        result = runner.invoke(
            upload,
            [
                "--file",
                str(valid_file),
                "--dir",
                str(tmp_path / "nonexistent_dir"),
            ],
        )

        assert result.exit_code == ExitCode.FILE_ERROR
        assert "Directory not found:" in result.output

    def test_empty_directory_is_warning_not_error(self, tmp_path):
        """Test that empty directory produces warning, not error."""
        # Create empty directory
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        # Use test processor with validation disabled
        processor = AttachmentProcessor(
            support_aliases=False, validate_files=False
        )

        # This should not raise an error
        import asyncio

        files = asyncio.run(
            processor.collect_files((), (str(empty_dir),), (), None)
        )

        # Should return empty list but not error
        assert files == []

    def test_empty_collection_is_warning_not_error(self, tmp_path):
        """Test that empty collection file produces warning, not error."""
        # Create empty collection file
        empty_collection = tmp_path / "empty.txt"
        empty_collection.write_text("")

        # Use test processor with validation disabled
        processor = AttachmentProcessor(
            support_aliases=False, validate_files=False
        )

        # This should not raise an error
        import asyncio

        files = asyncio.run(
            processor.collect_files((), (), (f"@{empty_collection}",), None)
        )

        # Should return empty list but not error
        assert files == []

    def test_pattern_filter_no_matches_is_warning(self, tmp_path):
        """Test that pattern filter with no matches is warning, not error."""
        # Create file that won't match pattern
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Use test processor with validation disabled
        processor = AttachmentProcessor(
            support_aliases=False, validate_files=False
        )

        # This should not raise an error
        import asyncio

        files = asyncio.run(
            processor.collect_files((str(test_file),), (), (), "*.pdf")
        )

        # Should return empty list but not error (pattern filtered out the file)
        assert files == []

    def test_pattern_as_primary_input_no_matches(self, tmp_path):
        """Test that pattern as primary input with no matches raises error."""
        # Use test processor with validation disabled but enable validation for this test
        processor = AttachmentProcessor(
            support_aliases=False, validate_files=True
        )

        # Pattern as primary input that matches nothing should raise error
        import asyncio

        with pytest.raises(NoFilesMatchPatternError):
            asyncio.run(
                processor.collect_files(("*.nonexistent",), (), (), None)
            )

    def test_dry_run_json_error_handling(self, tmp_path):
        """Test that dry-run with JSON flag shows proper error format."""
        runner = CliRunner()
        result = runner.invoke(
            upload,
            [
                "--file",
                str(tmp_path / "missing.txt"),
                "--dry-run",
                "--json",
            ],
        )

        assert result.exit_code == ExitCode.FILE_ERROR

        # Should be valid JSON
        try:
            error_data = json.loads(result.output)
            assert "data" in error_data
            assert "error" in error_data["data"]
            assert "File not found:" in error_data["data"]["error"]
        except json.JSONDecodeError:
            pytest.fail("Output should be valid JSON")
