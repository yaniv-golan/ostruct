"""Tests for file error handling behavior in CLI commands."""

import json
import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.ostruct.cli.commands.files import upload
from src.ostruct.cli.exit_codes import ExitCode
from src.ostruct.cli.utils.file_errors import (
    BrokenSymlinkError,
    CollectionFileNotFoundError,
    DirectoryNotFoundError,
    FileFromCollectionNotFoundError,
    FileNotFoundError,
    FilePermissionError,
    NoFilesMatchPatternError,
    NotADirectoryError,
    validate_collection_file_exists,
    validate_directory_exists,
    validate_file_exists,
)


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

    def test_validate_file_exists_permission_denied(self, tmp_path):
        """Test validation of unreadable file."""
        test_file = tmp_path / "unreadable.txt"
        test_file.write_text("content")

        # Remove read permission
        os.chmod(test_file, 0o000)

        try:
            with pytest.raises(FilePermissionError) as exc_info:
                validate_file_exists(test_file)

            assert "Permission denied:" in str(exc_info.value)
            assert str(test_file) in str(exc_info.value)
            assert exc_info.value.exit_code == ExitCode.FILE_ERROR
        finally:
            # Restore permissions for cleanup
            os.chmod(test_file, 0o644)

    def test_validate_file_exists_broken_symlink(self, tmp_path):
        """Test validation of broken symlink."""
        target = tmp_path / "target.txt"
        symlink = tmp_path / "link.txt"

        # Create symlink to non-existent target
        symlink.symlink_to(target)

        with pytest.raises(BrokenSymlinkError) as exc_info:
            validate_file_exists(symlink)

        assert "Broken symlink:" in str(exc_info.value)
        assert str(symlink) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR

    def test_validate_file_exists_valid_symlink(self, tmp_path):
        """Test validation of valid symlink."""
        target = tmp_path / "target.txt"
        target.write_text("content")
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)

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
        """Test validation of file when directory expected."""
        test_file = tmp_path / "not_dir.txt"
        test_file.write_text("content")

        with pytest.raises(NotADirectoryError) as exc_info:
            validate_directory_exists(test_file)

        assert "Path is not a directory:" in str(exc_info.value)
        assert str(test_file) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR

    def test_validate_collection_file_exists_success(self, tmp_path):
        """Test successful collection file validation."""
        collection_file = tmp_path / "collection.txt"
        collection_file.write_text("file1.txt\nfile2.txt\n")

        # Should not raise any exception
        validate_collection_file_exists(collection_file)

    def test_validate_collection_file_exists_missing(self, tmp_path):
        """Test validation of missing collection file."""
        missing_collection = tmp_path / "missing.txt"

        with pytest.raises(CollectionFileNotFoundError) as exc_info:
            validate_collection_file_exists(missing_collection)

        assert "Collection file not found:" in str(exc_info.value)
        assert str(missing_collection) in str(exc_info.value)
        assert exc_info.value.exit_code == ExitCode.FILE_ERROR


class TestFilesUploadErrorHandling:
    """Test error handling in the files upload command."""

    def test_single_missing_file_human_output(self):
        """Test error handling for single missing file with human output."""
        runner = CliRunner()
        result = runner.invoke(upload, ["--file", "nonexistent.txt"])

        assert result.exit_code == ExitCode.FILE_ERROR
        assert "❌ Error: File not found: nonexistent.txt" in result.output

    def test_single_missing_file_json_output(self):
        """Test error handling for single missing file with JSON output."""
        runner = CliRunner()
        result = runner.invoke(upload, ["--file", "nonexistent.txt", "--json"])

        assert result.exit_code == ExitCode.FILE_ERROR

        # Parse JSON output
        output_data = json.loads(result.output)
        assert output_data["data"]["exit_code"] == ExitCode.FILE_ERROR
        assert (
            "File not found: nonexistent.txt" in output_data["data"]["error"]
        )
        assert output_data["metadata"]["operation"] == "upload"

    def test_multiple_files_first_missing(self, tmp_path):
        """Test error handling when first file in multiple files is missing."""
        # Create a valid file
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("content")

        runner = CliRunner()
        result = runner.invoke(
            upload,
            [
                "--file",
                "missing.txt",
                "--file",
                str(valid_file),
                "--file",
                "another.txt",
            ],
        )

        assert result.exit_code == ExitCode.FILE_ERROR
        assert "❌ Error: File not found: missing.txt" in result.output

    def test_glob_pattern_no_matches(self):
        """Test error handling for glob pattern that matches no files."""
        runner = CliRunner()
        result = runner.invoke(upload, ["--file", "*.nonexistent"])

        assert result.exit_code == ExitCode.FILE_ERROR
        assert (
            "❌ Error: No files match pattern: *.nonexistent" in result.output
        )

    def test_glob_pattern_no_matches_json(self):
        """Test JSON error handling for glob pattern that matches no files."""
        runner = CliRunner()
        result = runner.invoke(upload, ["--file", "*.nonexistent", "--json"])

        assert result.exit_code == ExitCode.FILE_ERROR

        output_data = json.loads(result.output)
        assert output_data["data"]["exit_code"] == ExitCode.FILE_ERROR
        assert (
            "No files match pattern: *.nonexistent"
            in output_data["data"]["error"]
        )

    def test_directory_not_found(self):
        """Test error handling for missing directory."""
        runner = CliRunner()
        result = runner.invoke(upload, ["--dir", "nonexistent_dir"])

        assert result.exit_code == ExitCode.FILE_ERROR
        assert (
            "❌ Error: Directory not found: nonexistent_dir" in result.output
        )

    def test_path_not_directory(self, tmp_path):
        """Test error handling when directory path points to file."""
        test_file = tmp_path / "not_dir.txt"
        test_file.write_text("content")

        runner = CliRunner()
        result = runner.invoke(upload, ["--dir", str(test_file)])

        assert result.exit_code == ExitCode.FILE_ERROR
        assert "❌ Error: Path is not a directory:" in result.output

    def test_collection_file_not_found(self):
        """Test error handling for missing collection file."""
        runner = CliRunner()
        result = runner.invoke(upload, ["--collect", "@missing_list.txt"])

        assert result.exit_code == ExitCode.FILE_ERROR
        assert (
            "❌ Error: Collection file not found: missing_list.txt"
            in result.output
        )

    def test_collection_file_contains_missing_file(self, tmp_path):
        """Test error handling for collection file with missing files."""
        # Create collection file with mixed valid/invalid files
        collection_file = tmp_path / "collection.txt"
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("content")

        collection_file.write_text(f"{valid_file}\nmissing.txt\n")

        runner = CliRunner()
        result = runner.invoke(upload, ["--collect", f"@{collection_file}"])

        assert result.exit_code == ExitCode.FILE_ERROR
        assert (
            f"❌ Error: File not found (from collection {collection_file}): missing.txt"
            in result.output
        )

    def test_mixed_input_methods_directory_fails(self, tmp_path):
        """Test error handling with mixed input methods where directory fails."""
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("content")

        collection_file = tmp_path / "collection.txt"
        collection_file.write_text(f"{valid_file}\n")

        runner = CliRunner()
        result = runner.invoke(
            upload,
            [
                "--file",
                str(valid_file),
                "--dir",
                "nonexistent_dir",
                "--collect",
                f"@{collection_file}",
            ],
        )

        assert result.exit_code == ExitCode.FILE_ERROR
        assert (
            "❌ Error: Directory not found: nonexistent_dir" in result.output
        )

    def test_dry_run_prevents_preview_on_error(self):
        """Test that dry-run catches errors before showing preview."""
        runner = CliRunner()
        result = runner.invoke(upload, ["--file", "missing.txt", "--dry-run"])

        assert result.exit_code == ExitCode.FILE_ERROR
        assert "❌ Error: File not found: missing.txt" in result.output
        # Should not contain dry-run preview text
        assert "Dry run preview:" not in result.output
        assert "Files to upload:" not in result.output

    def test_dry_run_json_error_handling(self):
        """Test dry-run JSON error handling."""
        runner = CliRunner()
        result = runner.invoke(
            upload, ["--file", "missing.txt", "--dry-run", "--json"]
        )

        assert result.exit_code == ExitCode.FILE_ERROR

        output_data = json.loads(result.output)
        assert output_data["data"]["exit_code"] == ExitCode.FILE_ERROR
        assert "File not found: missing.txt" in output_data["data"]["error"]

    def test_pattern_as_primary_input_no_matches(self):
        """Test pattern used as primary input method with no matches."""
        runner = CliRunner()
        result = runner.invoke(upload, ["--pattern", "*.nonexistent"])

        assert result.exit_code == ExitCode.FILE_ERROR
        assert (
            "❌ Error: No files match pattern: *.nonexistent" in result.output
        )

    def test_empty_directory_is_warning_not_error(self, tmp_path):
        """Test that empty directories produce warnings, not errors."""
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        runner = CliRunner()
        # Mock the async upload process to avoid API calls
        with patch(
            "src.ostruct.cli.commands.files._batch_upload"
        ) as mock_upload:
            mock_upload.return_value = None
            result = runner.invoke(upload, ["--dir", str(empty_dir)])

        # Should succeed (exit code 0) but show warning about no files
        assert result.exit_code == 0
        assert "No files found matching criteria." in result.output

    def test_empty_collection_is_warning_not_error(self, tmp_path):
        """Test that empty collection files produce warnings, not errors."""
        empty_collection = tmp_path / "empty.txt"
        empty_collection.write_text("# This collection is empty\n")

        runner = CliRunner()
        # Mock the async upload process to avoid API calls
        with patch(
            "src.ostruct.cli.commands.files._batch_upload"
        ) as mock_upload:
            mock_upload.return_value = None
            result = runner.invoke(
                upload, ["--collect", f"@{empty_collection}"]
            )

        # Should succeed (exit code 0) but show warning about no files
        assert result.exit_code == 0
        assert "No files found matching criteria." in result.output

    def test_pattern_filter_no_matches_is_warning(self, tmp_path):
        """Test that pattern filtering with no matches is warning, not error."""
        # Create a valid file
        valid_file = tmp_path / "test.txt"
        valid_file.write_text("content")

        runner = CliRunner()
        # Mock the async upload process to avoid API calls
        with patch(
            "src.ostruct.cli.commands.files._batch_upload"
        ) as mock_upload:
            mock_upload.return_value = None
            result = runner.invoke(
                upload,
                ["--file", str(valid_file), "--pattern", "*.nonexistent"],
            )

        # Should succeed (exit code 0) but show warning about no files after filtering
        assert result.exit_code == 0
        assert "No files found matching criteria." in result.output


class TestErrorMessageFormats:
    """Test that error messages follow the specified formats."""

    def test_file_not_found_message_format(self):
        """Test file not found error message format."""
        error = FileNotFoundError("/path/to/missing.txt")
        assert str(error) == "File not found: /path/to/missing.txt"
        assert error.exit_code == ExitCode.FILE_ERROR

    def test_directory_not_found_message_format(self):
        """Test directory not found error message format."""
        error = DirectoryNotFoundError("/path/to/missing_dir")
        assert str(error) == "Directory not found: /path/to/missing_dir"
        assert error.exit_code == ExitCode.FILE_ERROR

    def test_permission_denied_message_format(self):
        """Test permission denied error message format."""
        error = FilePermissionError("/path/to/unreadable.txt")
        assert str(error) == "Permission denied: /path/to/unreadable.txt"
        assert error.exit_code == ExitCode.FILE_ERROR

    def test_broken_symlink_message_format(self):
        """Test broken symlink error message format."""
        error = BrokenSymlinkError("/path/to/link.txt", "/path/to/target.txt")
        assert (
            str(error)
            == "Broken symlink: /path/to/link.txt -> /path/to/target.txt"
        )
        assert error.exit_code == ExitCode.FILE_ERROR

    def test_broken_symlink_message_format_no_target(self):
        """Test broken symlink error message format without target."""
        error = BrokenSymlinkError("/path/to/link.txt")
        assert str(error) == "Broken symlink: /path/to/link.txt"
        assert error.exit_code == ExitCode.FILE_ERROR

    def test_no_files_match_pattern_message_format(self):
        """Test no files match pattern error message format."""
        error = NoFilesMatchPatternError("*.nonexistent")
        assert str(error) == "No files match pattern: *.nonexistent"
        assert error.exit_code == ExitCode.FILE_ERROR

    def test_collection_file_not_found_message_format(self):
        """Test collection file not found error message format."""
        error = CollectionFileNotFoundError("missing_list.txt")
        assert str(error) == "Collection file not found: missing_list.txt"
        assert error.exit_code == ExitCode.FILE_ERROR

    def test_file_from_collection_not_found_message_format(self):
        """Test file from collection not found error message format."""
        error = FileFromCollectionNotFoundError("missing.txt", "list.txt")
        assert (
            str(error)
            == "File not found (from collection list.txt): missing.txt"
        )
        assert error.exit_code == ExitCode.FILE_ERROR
