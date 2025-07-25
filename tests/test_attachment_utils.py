"""Tests for attachment processing utilities."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ostruct.cli.utils.attachment_utils import AttachmentProcessor
from src.ostruct.cli.utils.progress_utils import ProgressHandler


class TestAttachmentProcessor:
    """Test the AttachmentProcessor class."""

    def test_init_without_aliases(self):
        """Test AttachmentProcessor initialization without alias support."""
        processor = AttachmentProcessor(support_aliases=False)

        assert processor.support_aliases is False
        assert processor.progress_handler is None

    def test_init_with_aliases_and_handler(self):
        """Test AttachmentProcessor initialization with aliases and progress handler."""
        mock_handler = Mock(spec=ProgressHandler)
        processor = AttachmentProcessor(
            support_aliases=True, progress_handler=mock_handler
        )

        assert processor.support_aliases is True
        assert processor.progress_handler == mock_handler

    @pytest.mark.asyncio
    async def test_collect_files_empty_inputs(self):
        """Test collect_files with empty inputs."""
        processor = AttachmentProcessor()

        files = await processor.collect_files((), (), (), None)

        assert files == []

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.resolve")
    async def test_collect_files_single_file(
        self, mock_resolve, mock_is_file, mock_exists
    ):
        """Test collect_files with a single file."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_path = Path("/test/file.txt")
        mock_resolve.return_value = mock_path

        processor = AttachmentProcessor(support_aliases=False)

        files = await processor.collect_files(("file.txt",), (), (), None)

        assert len(files) == 1
        assert files[0] == mock_path

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.resolve")
    async def test_collect_files_with_aliases(
        self, mock_resolve, mock_is_file, mock_exists
    ):
        """Test collect_files with alias support."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_path = Path("/test/file.txt")
        mock_resolve.return_value = mock_path

        processor = AttachmentProcessor(support_aliases=True)

        files = await processor.collect_files(
            ("alias:file.txt",), (), (), None
        )

        assert len(files) == 1
        assert files[0] == mock_path

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_dir")
    @patch("pathlib.Path.rglob")
    async def test_collect_files_directory(
        self, mock_rglob, mock_is_dir, mock_exists
    ):
        """Test collect_files with directory input."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_dir.return_value = True

        mock_file1 = Mock()
        mock_file1.is_file.return_value = True
        mock_file1.resolve.return_value = Path("/test/dir/file1.txt")

        mock_file2 = Mock()
        mock_file2.is_file.return_value = True
        mock_file2.resolve.return_value = Path("/test/dir/file2.txt")

        mock_rglob.return_value = [mock_file1, mock_file2]

        processor = AttachmentProcessor()

        files = await processor.collect_files((), ("test_dir",), (), None)

        assert len(files) == 2
        mock_rglob.assert_called_once_with("*")

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    @patch("builtins.open")
    async def test_collect_files_collection(
        self, mock_open, mock_is_file, mock_exists
    ):
        """Test collect_files with collection file."""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_file.return_value = True

        # Mock file content
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_file.__iter__ = Mock(
            return_value=iter(["file1.txt\n", "file2.txt\n", "# comment\n"])
        )
        mock_open.return_value = mock_file

        # Mock Path objects for files in collection
        with patch("pathlib.Path") as mock_path_class:
            mock_path_instances = []

            def path_side_effect(path_str):
                mock_path = Mock()
                mock_path.exists.return_value = True
                mock_path.is_file.return_value = True
                mock_path.resolve.return_value = Path(f"/test/{path_str}")
                mock_path_instances.append(mock_path)
                return mock_path

            mock_path_class.side_effect = path_side_effect

            processor = AttachmentProcessor()

            files = await processor.collect_files(
                (), (), ("@filelist.txt",), None
            )

            assert len(files) == 2

    @pytest.mark.asyncio
    @pytest.mark.no_fs  # Use real filesystem for this test
    async def test_collect_files_with_pattern_filter(self, tmp_path):
        """Test collect_files with pattern filtering."""
        # Create real test files in a temporary directory
        test_file1 = tmp_path / "file1.txt"
        test_file2 = tmp_path / "file2.py"
        test_file1.write_text("content1")
        test_file2.write_text("content2")

        # Change to the temp directory so relative paths work
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            processor = AttachmentProcessor()

            files = await processor.collect_files(
                ("file1.txt", "file2.py"), (), (), "*.txt"
            )

            # Should only return .txt files
            assert len(files) == 1
            assert files[0].name == "file1.txt"
        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_process_batch_dry_run(self):
        """Test process_batch in dry-run mode."""
        processor = AttachmentProcessor()

        files = [Path("/test/file1.txt"), Path("/test/file2.txt")]
        mock_func = AsyncMock()

        result = await processor.process_batch(files, mock_func, dry_run=True)

        assert result["summary"]["total"] == 2
        assert result["summary"]["processed"] == 2
        assert result["summary"]["errors"] == 0
        assert len(result["results"]) == 2
        assert len(result["errors"]) == 0

        # Function should not be called in dry-run
        mock_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_batch_success(self):
        """Test process_batch with successful processing."""
        processor = AttachmentProcessor()

        files = [Path("/test/file1.txt"), Path("/test/file2.txt")]
        mock_func = AsyncMock(side_effect=["result1", "result2"])

        result = await processor.process_batch(
            files, mock_func, ("tool1", "tool2")
        )

        assert result["summary"]["total"] == 2
        assert result["summary"]["processed"] == 2
        assert result["summary"]["errors"] == 0
        assert result["results"] == ["result1", "result2"]
        assert result["errors"] == []

        # Function should be called twice with tools
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self):
        """Test process_batch with some processing errors."""
        processor = AttachmentProcessor()

        files = [Path("/test/file1.txt"), Path("/test/file2.txt")]
        mock_func = AsyncMock(
            side_effect=["result1", Exception("Upload failed")]
        )

        result = await processor.process_batch(files, mock_func)

        assert result["summary"]["total"] == 2
        assert result["summary"]["processed"] == 1
        assert result["summary"]["errors"] == 1
        assert result["results"] == ["result1"]
        assert len(result["errors"]) == 1
        assert "Upload failed" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_process_batch_with_progress_handler(self):
        """Test process_batch with progress handler."""
        mock_handler = Mock(spec=ProgressHandler)
        mock_handler.detailed = True

        mock_phase = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_phase)
        mock_context.__exit__ = Mock(return_value=None)
        mock_handler.batch_phase.return_value = mock_context

        processor = AttachmentProcessor(progress_handler=mock_handler)

        files = [Path("/test/file1.txt")]
        mock_func = AsyncMock(return_value="result1")

        await processor.process_batch(files, mock_func)

        # Verify progress tracking
        mock_handler.batch_phase.assert_called_once_with(
            "Processing files", "📂", 1
        )
        mock_phase.advance.assert_called_once_with(msg="Processed file1.txt")
