"""Tests for files commands: bind, rm, gc, diagnose, vector-stores, list."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner
from ostruct.cli.commands.files import files


@pytest.fixture
def mock_upload_cache():
    """Mock UploadCache for testing."""
    cache = Mock()

    # Mock file info object with serializable data
    file_info = Mock()
    file_info.file_id = "file-123"
    file_info.metadata = {"bindings": {"user_data": False}}
    file_info.path = "/test/file.txt"
    file_info.size = 1024
    file_info.created_at = 1640995200  # 2022-01-01
    file_info.hash = "hash123"

    # Make the file_info attributes return values instead of Mock objects
    file_info.to_dict.return_value = {
        "file_id": "file-123",
        "path": "/test/file.txt",
        "size": 1024,
        "cached": True,
        "bindings": {"user_data": False},
        "tags": [],
    }

    cache.list_all.return_value = [file_info]
    cache.update_metadata = Mock()
    cache.invalidate_by_file_id = Mock()
    cache.list_vector_stores.return_value = [
        {
            "vector_store_id": "vs-123",
            "name": "ostruct_test_store",
            "created_at": 1640995200,
            "last_used": 1640995200,
            "file_count": 3,
            "total_size": 2048,
        }
    ]

    return cache


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = Mock()

    # Mock file object
    file_obj = Mock()
    file_obj.bytes = 1024
    client.files.retrieve.return_value = file_obj
    client.files.delete = AsyncMock()

    # Mock chat completions
    response = Mock()
    response.choices = [Mock()]
    client.chat.completions.create = AsyncMock(return_value=response)

    return client


class TestFilesBindCommand:
    """Tests for files bind command."""

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_bind_file_to_tools(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test binding a file to tools."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache

        # Set up the mock to return a file with the expected file_id
        file_info = Mock()
        file_info.file_id = "file-123"
        file_info.metadata = {"bindings": {"user_data": False}}
        mock_upload_cache.list_all.return_value = [file_info]

        runner = CliRunner()
        result = runner.invoke(
            files,
            [
                "bind",
                "file-123",
                "--tools",
                "user-data",
                "--tools",
                "file-search",
            ],
        )

        assert result.exit_code == 0
        assert "Bound file-123 to: user-data, file-search" in result.output

        # Verify cache was updated
        mock_upload_cache.update_metadata.assert_called_once()
        call_args = mock_upload_cache.update_metadata.call_args
        assert call_args[0][0] == "file-123"  # file_id
        metadata = call_args[0][1]
        assert metadata["bindings"]["user_data"] is True
        assert metadata["bindings"]["file_search"] is True

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_bind_file_json_output(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test bind command with JSON output."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache

        # Set up the mock to return a file with the expected file_id
        file_info = Mock()
        file_info.file_id = "file-123"
        file_info.metadata = {"bindings": {"user_data": False}}
        mock_upload_cache.list_all.return_value = [file_info]

        runner = CliRunner()
        result = runner.invoke(
            files,
            ["bind", "file-123", "--tools", "code-interpreter", "--json"],
        )

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["status"] == "success"
        assert output_data["file_id"] == "file-123"
        assert "bindings" in output_data

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_bind_file_not_found(self, mock_cache_path, mock_cache_class):
        """Test bind command with non-existent file."""
        mock_cache_path.return_value = "/test/cache.db"
        cache = Mock()
        cache.list_all.return_value = []
        mock_cache_class.return_value = cache

        runner = CliRunner()
        result = runner.invoke(
            files, ["bind", "file-nonexistent", "--tools", "user-data"]
        )

        assert result.exit_code != 0
        assert "File not found in cache" in result.output


class TestFilesRmCommand:
    """Tests for files rm command."""

    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch("ostruct.cli.upload_cache.UploadCache")
    @patch("ostruct.cli.cache_utils.get_default_cache_path")
    def test_rm_file_success(
        self,
        mock_cache_path,
        mock_cache_class,
        mock_client_func,
    ):
        """Test successful file deletion."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_upload_cache = Mock()
        mock_cache_class.return_value = mock_upload_cache
        mock_openai_client = AsyncMock()
        mock_client_func.return_value = mock_openai_client

        runner = CliRunner()
        result = runner.invoke(files, ["rm", "file-123"])

        assert result.exit_code == 0
        assert "Deleted: file-123" in result.output

        # Verify OpenAI deletion was called
        mock_openai_client.files.delete.assert_called_once_with("file-123")

        # Verify cache invalidation was called
        mock_upload_cache.invalidate_by_file_id.assert_called_once_with(
            "file-123"
        )

    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_rm_file_json_output(
        self,
        mock_cache_path,
        mock_cache_class,
        mock_client_func,
        mock_upload_cache,
        mock_openai_client,
    ):
        """Test rm command with JSON output."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache
        mock_client_func.return_value = mock_openai_client

        runner = CliRunner()
        result = runner.invoke(files, ["rm", "file-123", "--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["status"] == "success"
        assert output_data["file_id"] == "file-123"

    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    @patch("ostruct.cli.upload_cache.UploadCache")
    @patch("ostruct.cli.cache_utils.get_default_cache_path")
    def test_rm_file_openai_404_ignored(
        self,
        mock_cache_path,
        mock_cache_class,
        mock_client_func,
    ):
        """Test that 404 errors from OpenAI are ignored."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_upload_cache = Mock()
        mock_cache_class.return_value = mock_upload_cache
        mock_openai_client = AsyncMock()
        mock_client_func.return_value = mock_openai_client

        # Make OpenAI deletion fail with 404
        mock_openai_client.files.delete.side_effect = Exception(
            "404 not found"
        )

        runner = CliRunner()
        result = runner.invoke(files, ["rm", "file-123"])

        assert result.exit_code == 0
        assert "Deleted: file-123" in result.output

        # Cache should still be invalidated
        mock_upload_cache.invalidate_by_file_id.assert_called_once_with(
            "file-123"
        )


class TestFilesGcCommand:
    """Tests for files gc command."""

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_gc_basic(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test basic garbage collection."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache

        # Mock file with proper attributes for age-based cleanup
        import time

        file_info = Mock()
        file_info.path = "/nonexistent/file.txt"
        file_info.created_at = int(time.time()) - (
            35 * 24 * 60 * 60
        )  # 35 days ago (older than 30d cutoff)
        file_info.hash = "test_hash_123"
        file_info.file_id = "file_123"
        mock_upload_cache.list_all.return_value = [file_info]

        runner = CliRunner()
        result = runner.invoke(files, ["gc", "--older-than", "30d"])

        assert result.exit_code == 0
        assert (
            "Cleaned up" in result.output
            or "No cleanup needed" in result.output
        )

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_gc_json_output(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test gc command with JSON output."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache
        mock_upload_cache.list_all.return_value = []

        runner = CliRunner()
        result = runner.invoke(files, ["gc", "--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["status"] == "success"
        assert "deleted_count" in output_data
        assert "cutoff_date" in output_data

    def test_gc_invalid_duration(self):
        """Test gc command with invalid duration format."""
        runner = CliRunner()
        result = runner.invoke(files, ["gc", "--older-than", "invalid"])

        assert result.exit_code != 0
        assert "Error during garbage collection" in result.output


class TestFilesDiagnoseCommand:
    """Tests for files diagnose command."""

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    def test_diagnose_all_probes_pass(
        self, mock_client_func, mock_cache_path, mock_cache_class
    ):
        """Test diagnose command when all probes pass."""
        # Create a mock client with async methods
        mock_client = Mock()

        # Mock file object for head probe
        file_obj = Mock()
        file_obj.bytes = 1024
        mock_client.files.retrieve = AsyncMock(return_value=file_obj)

        # Mock responses.create for vector and sandbox probes (not chat.completions.create!)
        response = Mock()
        response.output = (
            "test response"  # The actual command checks response.output
        )
        mock_client.responses.create = AsyncMock(return_value=response)

        mock_client_func.return_value = mock_client

        # Mock cache setup
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache = Mock()
        mock_cache_class.return_value = mock_cache

        # Create file info with proper metadata structure
        file_info = Mock()
        file_info.file_id = "file-123"
        file_info.metadata = {"bindings": {"vector_store_ids": ["vs_123"]}}
        mock_cache.list_all.return_value = [file_info]

        runner = CliRunner()
        result = runner.invoke(files, ["diagnose", "file-123"])

        assert result.exit_code == 0
        assert "Diagnostic results for file-123" in result.output
        assert "head" in result.output
        assert "vector" in result.output
        assert "sandbox" in result.output

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    def test_diagnose_json_output(
        self, mock_client_func, mock_cache_path, mock_cache_class
    ):
        """Test diagnose command JSON output format."""
        # Create a mock client with async methods
        mock_client = Mock()

        # Mock file object for head probe
        file_obj = Mock()
        file_obj.bytes = 1024
        mock_client.files.retrieve = AsyncMock(return_value=file_obj)

        # Mock responses.create for vector and sandbox probes (not chat.completions.create!)
        response = Mock()
        response.output = (
            "test response"  # The actual command checks response.output
        )
        mock_client.responses.create = AsyncMock(return_value=response)

        mock_client_func.return_value = mock_client

        # Mock cache setup
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache = Mock()
        mock_cache_class.return_value = mock_cache

        # Create file info with proper metadata structure
        file_info = Mock()
        file_info.file_id = "file-123"
        file_info.metadata = {"bindings": {"vector_store_ids": ["vs_123"]}}
        mock_cache.list_all.return_value = [file_info]

        runner = CliRunner()
        result = runner.invoke(files, ["diagnose", "file-123", "--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["status"] == "complete"
        assert output_data["file_id"] == "file-123"
        assert "probes" in output_data
        assert "exit_code" in output_data

    @patch("ostruct.cli.utils.client_utils.create_openai_client")
    def test_diagnose_probe_failures(self, mock_client_func):
        """Test diagnose command when probes fail."""
        # Create a mock client with failing async methods
        mock_client = Mock()

        # Make head probe fail
        mock_client.files.retrieve = AsyncMock(
            side_effect=Exception("File not found")
        )

        # Mock chat completions (these will also fail due to the exception)
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        mock_client_func.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(files, ["diagnose", "file-123"])

        assert (
            result.exit_code != 0
        )  # Should exit with error code when probes fail


class TestFilesVectorStoresCommand:
    """Tests for files vector-stores command."""

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_vector_stores_list(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test listing vector stores."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache

        runner = CliRunner()
        result = runner.invoke(files, ["vector-stores"])

        assert result.exit_code == 0
        assert "Vector Store" in result.output
        assert (
            "test_store" in result.output
        )  # From mock data (ostruct_ prefix removed)

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_vector_stores_json_output(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test vector-stores command with JSON output."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache

        runner = CliRunner()
        result = runner.invoke(files, ["vector-stores", "--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["status"] == "success"
        assert "vector_stores" in output_data
        assert len(output_data["vector_stores"]) == 1

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_vector_stores_empty(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test vector-stores command when no stores exist."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache
        mock_upload_cache.list_vector_stores.return_value = []

        runner = CliRunner()
        result = runner.invoke(files, ["vector-stores"])

        assert result.exit_code == 0
        assert "No vector stores found" in result.output


class TestFilesListCommand:
    """Tests for files list command."""

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_list_files(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test listing files."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache

        runner = CliRunner()
        result = runner.invoke(files, ["list"])

        assert result.exit_code == 0
        assert "File ID" in result.output
        assert "file-123" in result.output

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_list_files_json_output(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test list command with JSON output."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache

        runner = CliRunner()
        result = runner.invoke(files, ["list", "--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert "data" in output_data
        assert "metadata" in output_data
        assert isinstance(output_data["data"], list)
        if output_data["data"]:  # If there are files
            assert "file_id" in output_data["data"][0]
            assert "path" in output_data["data"][0]

    @patch("ostruct.cli.commands.files.UploadCache")
    @patch("ostruct.cli.commands.files.get_default_cache_path")
    def test_list_files_with_vector_store_filter(
        self, mock_cache_path, mock_cache_class, mock_upload_cache
    ):
        """Test list command with vector store filter."""
        mock_cache_path.return_value = "/test/cache.db"
        mock_cache_class.return_value = mock_upload_cache

        # Mock vector store methods
        mock_upload_cache.get_vector_store_by_name.return_value = "vs-123"
        mock_upload_cache.get_files_in_vector_store.return_value = ["hash123"]

        # Mock file with matching hash
        file_info = Mock()
        file_info.file_id = "file-123"
        file_info.hash = "hash123"
        file_info.metadata = {}
        file_info.path = "/test/file.txt"
        file_info.size = 1024
        file_info.created_at = 1640995200
        mock_upload_cache.list_all.return_value = [file_info]

        runner = CliRunner()
        result = runner.invoke(files, ["list", "--vector-store", "test_store"])

        assert result.exit_code == 0
        # Should call vector store filtering methods
        mock_upload_cache.get_vector_store_by_name.assert_called_once_with(
            "ostruct_test_store"
        )
        mock_upload_cache.get_files_in_vector_store.assert_called_once_with(
            "vs-123"
        )
