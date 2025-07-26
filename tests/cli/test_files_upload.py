"""Tests for the enhanced files upload command."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner
from ostruct.cli.commands.files import files


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files."""
    files = {}

    # Create test files
    files["test1.txt"] = tmp_path / "test1.txt"
    files["test1.txt"].write_text("Test content 1")

    files["test2.pdf"] = tmp_path / "test2.pdf"
    files["test2.pdf"].write_text("PDF content")

    files["doc.csv"] = tmp_path / "doc.csv"
    files["doc.csv"].write_text("col1,col2\nval1,val2")

    # Create subdirectory with files
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    files["sub1.txt"] = subdir / "sub1.txt"
    files["sub1.txt"].write_text("Sub content 1")

    files["sub2.png"] = subdir / "sub2.png"
    files["sub2.png"].write_text("PNG content")

    # Create filelist
    files["filelist.txt"] = tmp_path / "filelist.txt"
    files["filelist.txt"].write_text(
        f"{files['test1.txt']}\n{files['doc.csv']}\n"
    )

    return files


@pytest.fixture
def mock_upload_manager():
    """Mock SharedUploadManager."""
    manager = Mock()
    manager._perform_upload = AsyncMock(return_value="file-123")
    return manager


@pytest.fixture
def mock_cache():
    """Mock UploadCache."""
    cache = Mock()
    cache.compute_file_hash = Mock(return_value="hash123")
    cache.lookup_with_validation = Mock(return_value=None)  # No cache hit
    cache.store = Mock()
    cache.update_metadata = Mock()
    cache.get_vector_store_by_name = Mock(return_value=None)
    cache.register_vector_store = Mock()
    cache.add_file_to_vector_store = Mock()
    return cache


@pytest.fixture
def mock_fs_manager():
    """Mock FileSearchManager."""
    manager = Mock()
    manager.create_vector_store_with_retry = AsyncMock(return_value="vs-123")
    manager._add_files_to_vector_store_with_retry = AsyncMock()
    return manager


@pytest.mark.no_fs
class TestFilesUploadBasic:
    """Test basic upload functionality."""

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.FileSearchManager")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_single_file_upload(
        self,
        mock_client,
        mock_fs_manager_cls,
        mock_cache_cls,
        mock_upload_manager_cls,
        temp_files,
    ):
        """Test uploading a single file."""
        # Setup mocks
        mock_client.return_value = Mock()  # Mock AsyncOpenAI client

        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--tools",
                "user-data",
            ],
        )

        if result.exit_code != 0:
            print(f"Command failed with exit code {result.exit_code}")
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")
        assert result.exit_code == 0
        assert "✅ Uploaded" in result.output
        assert "file-123" in result.output
        mock_manager._perform_upload.assert_called_once()

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_cached_file_upload(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test uploading a file that's already cached."""
        # Setup mocks
        mock_client.return_value = Mock()  # Mock AsyncOpenAI client

        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = "cached-file-123"
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_upload_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--tools",
                "user-data",
            ],
        )

        assert result.exit_code == 0
        assert "✅ Cached" in result.output
        assert "cached-file-123" in result.output
        # Should not call upload since cached
        mock_manager._perform_upload.assert_not_called()


@pytest.mark.no_fs
class TestFilesUploadBatch:
    """Test batch upload functionality."""

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_multiple_files_upload(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test uploading multiple files."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--file",
                str(temp_files["test2.pdf"]),
                "--tools",
                "user-data",
            ],
        )

        assert result.exit_code == 0
        # Check for individual file upload messages (not the summary)
        assert "✅ Uploaded test1.txt" in result.output
        assert "✅ Uploaded test2.pdf" in result.output
        assert mock_manager._perform_upload.call_count == 2

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_directory_upload(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test uploading a directory recursively."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        subdir = temp_files["sub1.txt"].parent
        runner = CliRunner()
        result = runner.invoke(
            files, ["upload", "--dir", str(subdir), "--tools", "user-data"]
        )

        assert result.exit_code == 0
        # Should upload both files in subdirectory
        assert "✅ Uploaded sub1.txt" in result.output
        assert "✅ Uploaded sub2.png" in result.output
        assert mock_manager._perform_upload.call_count == 2

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_collection_upload(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test uploading files from a collection file."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--collect",
                f"@{temp_files['filelist.txt']}",
                "--tools",
                "user-data",
            ],
        )

        assert result.exit_code == 0
        # Should upload 2 files listed in filelist.txt
        assert "✅ Uploaded test1.txt" in result.output
        assert "✅ Uploaded doc.csv" in result.output
        assert mock_manager._perform_upload.call_count == 2


@pytest.mark.no_fs
class TestFilesUploadGlobPatterns:
    """Test glob pattern support."""

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_file_glob_pattern(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test glob pattern for files."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        # Change to temp directory for glob to work
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(temp_files["test1.txt"].parent)

            runner = CliRunner()
            result = runner.invoke(
                files, ["upload", "--file", "*.txt", "--tools", "user-data"]
            )

            assert result.exit_code == 0
            # Should match test1.txt and filelist.txt (both .txt files)
            assert "✅ Uploaded test1.txt" in result.output
            assert "✅ Uploaded filelist.txt" in result.output
            assert mock_manager._perform_upload.call_count == 2
        finally:
            os.chdir(old_cwd)

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_global_pattern_filter(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test global pattern filter."""
        # Setup mocks
        mock_client.return_value = Mock()  # Mock AsyncOpenAI client

        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        subdir = temp_files["sub1.txt"].parent
        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--dir",
                str(subdir),
                "--pattern",
                "*.txt",  # Only match .txt files
                "--tools",
                "user-data",
            ],
        )

        assert result.exit_code == 0
        # Should only upload sub1.txt, not sub2.png
        assert "✅ Uploaded sub1.txt" in result.output
        assert "sub2.png" not in result.output
        assert mock_manager._perform_upload.call_count == 1


@pytest.mark.no_fs
class TestFilesUploadDryRun:
    """Test dry-run functionality."""

    def test_dry_run_preview(self, temp_files):
        """Test dry-run preview mode."""
        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--file",
                str(temp_files["test2.pdf"]),
                "--tools",
                "user-data",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Dry run preview:" in result.output
        assert "Files to upload: 2" in result.output
        assert "Tools: user-data" in result.output

    def test_dry_run_json_output(self, temp_files):
        """Test dry-run with JSON output."""
        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--dry-run",
                "--json",
            ],
        )

        # The --dry-run --json combination now works correctly
        assert result.exit_code == 0

        # Should output empty result since we return early for dry-run + json
        # The actual dry-run preview logic is handled in _batch_upload which we skip
        assert result.output.strip() == ""


@pytest.mark.no_fs
class TestFilesUploadInteractive:
    """Test interactive mode."""

    @patch("ostruct.cli.commands.files.questionary")
    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_interactive_file_selection(
        self,
        mock_client,
        mock_cache_cls,
        mock_upload_manager_cls,
        mock_questionary,
        temp_files,
    ):
        """Test interactive file selection mode."""
        # Setup mocks
        mock_client.return_value = Mock()  # Mock AsyncOpenAI client

        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        # Mock questionary responses
        mock_questionary.checkbox.side_effect = [
            Mock(
                ask=Mock(return_value=[str(temp_files["test1.txt"])])
            ),  # File selection
            Mock(ask=Mock(return_value=["user-data"])),  # Tool selection
        ]

        runner = CliRunner()
        result = runner.invoke(
            files, ["upload"]
        )  # No arguments triggers interactive

        assert result.exit_code == 0
        assert mock_questionary.checkbox.call_count == 2
        assert mock_manager._perform_upload.call_count == 1

    @patch("ostruct.cli.commands.files.questionary")
    def test_interactive_cancelled(self, mock_questionary, temp_files):
        """Test interactive mode cancelled by user."""
        # Mock keyboard interrupt
        mock_questionary.checkbox.side_effect = KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(files, ["upload"])

        assert result.exit_code == 0
        assert "Operation cancelled" in result.output

    @patch("ostruct.cli.commands.files.questionary")
    def test_interactive_no_files_selected(self, mock_questionary, temp_files):
        """Test interactive mode with no files selected."""
        # Mock empty selection
        mock_questionary.checkbox.return_value.ask.return_value = []

        runner = CliRunner()
        result = runner.invoke(files, ["upload"])

        assert result.exit_code == 0
        assert "No files selected" in result.output


@pytest.mark.no_fs
class TestFilesUploadErrorHandling:
    """Test error handling."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False)
    def test_no_api_key(self, temp_files):
        """Test error when no API key is set."""
        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--tools",
                "code-interpreter",
            ],
        )

        assert result.exit_code == 1
        assert "No OpenAI API key found" in result.output

    def test_no_files_specified_json_mode(self):
        """Test error when no files specified in JSON mode."""
        runner = CliRunner()
        result = runner.invoke(files, ["upload", "--json"])

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "data" in data
        assert "error" in data["data"]
        assert "No files specified" in data["data"]["error"]

    def test_invalid_tag_format(self, temp_files):
        """Test error with invalid tag format."""
        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--tag",
                "invalid_tag_format",  # Missing =
                "--tools",
                "user-data",
            ],
        )

        assert result.exit_code != 0
        assert "Tag must be in format KEY=VALUE" in result.output

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_upload_error_handling(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test handling of individual file upload errors."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        # First call succeeds, second fails
        mock_manager._perform_upload = AsyncMock(
            side_effect=["file-123", Exception("Upload failed")]
        )
        mock_upload_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--file",
                str(temp_files["test2.pdf"]),
                "--tools",
                "user-data",
            ],
        )

        assert result.exit_code == 0  # Should continue despite error
        assert "✅ Uploaded" in result.output
        assert "❌ 1 errors:" in result.output
        assert "Upload failed" in result.output


@pytest.mark.no_fs
class TestFilesUploadToolBindings:
    """Test tool binding functionality."""

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.FileSearchManager")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_file_search_binding(
        self,
        mock_client,
        mock_fs_manager_cls,
        mock_cache_cls,
        mock_upload_manager_cls,
        temp_files,
    ):
        """Test file-search tool binding."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache.get_vector_store_by_name.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        mock_fs_manager = Mock()
        mock_fs_manager.create_vector_store_with_retry = AsyncMock(
            return_value="vs-123"
        )
        mock_fs_manager._add_files_to_vector_store_with_retry = AsyncMock()
        mock_fs_manager_cls.return_value = mock_fs_manager

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--tools",
                "file-search",
                "--vector-store",
                "test_store",
            ],
        )

        assert result.exit_code == 0
        assert "✅ Uploaded" in result.output
        mock_fs_manager.create_vector_store_with_retry.assert_called_once()
        mock_fs_manager._add_files_to_vector_store_with_retry.assert_called_once()

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_multiple_tool_bindings(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test binding to multiple tools."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--tools",
                "user-data",
                "--tools",
                "code-interpreter",
            ],
        )

        assert result.exit_code == 0
        assert "✅ Uploaded" in result.output
        # Should use assistants purpose for file-search/code-interpreter
        mock_manager._perform_upload.assert_called_with(
            temp_files["test1.txt"], purpose="assistants"
        )


@pytest.mark.no_fs
class TestFilesUploadJsonOutput:
    """Test JSON output mode."""

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    def test_json_output_empty_files(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls
    ):
        """Test JSON output when no files match criteria."""
        runner = CliRunner()
        # Use --file with a pattern that won't match anything
        result = runner.invoke(
            files, ["upload", "--file", "*.nonexistent", "--json"]
        )

        # With new validation, glob patterns that match no files return FILE_ERROR (9)
        assert result.exit_code == 9
        data = json.loads(result.output)

        # Should be an error response with the new JSON structure
        assert "data" in data
        assert "error" in data["data"]
        assert "No files match pattern" in data["data"]["error"]


@pytest.mark.no_fs
class TestFilesUploadTagsAndMetadata:
    """Test tags and metadata handling."""

    @patch("ostruct.cli.commands.files.SharedUploadManager")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_multiple_tags(
        self, mock_client, mock_cache_cls, mock_upload_manager_cls, temp_files
    ):
        """Test multiple tags application."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.compute_file_hash.return_value = "hash123"
        mock_cache.lookup_with_validation.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_manager = Mock()
        mock_manager._perform_upload = AsyncMock(return_value="file-123")
        mock_upload_manager_cls.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "upload",
                "--file",
                str(temp_files["test1.txt"]),
                "--tools",
                "user-data",
                "--tag",
                "project=alpha",
                "--tag",
                "category=document",
                "--tag",
                "version=1.0",
            ],
        )

        assert result.exit_code == 0
        assert "✅ Uploaded" in result.output

        # Check that update_metadata was called with correct tags
        mock_cache.update_metadata.assert_called_once()
        call_args = mock_cache.update_metadata.call_args
        metadata = call_args[0][1]  # Second argument is metadata

        expected_tags = {
            "project": "alpha",
            "category": "document",
            "version": "1.0",
        }
        assert metadata["tags"] == expected_tags
