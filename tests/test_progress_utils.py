"""Tests for progress handling utilities."""

from unittest.mock import Mock, patch

import pytest

from src.ostruct.cli.utils.progress_utils import (
    BatchPhaseContext,
    ProgressHandler,
)


class TestProgressHandler:
    """Test the ProgressHandler class."""

    @patch("src.ostruct.cli.utils.progress_utils.configure_progress_reporter")
    @patch("src.ostruct.cli.utils.progress_utils.get_progress_reporter")
    def test_init_basic(self, mock_get_reporter, mock_configure):
        """Test ProgressHandler initialization with basic settings."""
        mock_reporter = Mock()
        mock_reporter.detailed = False
        mock_get_reporter.return_value = mock_reporter

        handler = ProgressHandler(verbose=False, progress="basic")

        mock_configure.assert_called_once_with(verbose=False, progress="basic")
        mock_get_reporter.assert_called_once()
        assert handler.reporter == mock_reporter
        assert handler.progress_level == "basic"
        assert handler.detailed is False

    @patch("src.ostruct.cli.utils.progress_utils.configure_progress_reporter")
    @patch("src.ostruct.cli.utils.progress_utils.get_progress_reporter")
    def test_init_detailed(self, mock_get_reporter, mock_configure):
        """Test ProgressHandler initialization with detailed settings."""
        mock_reporter = Mock()
        mock_reporter.detailed = True
        mock_get_reporter.return_value = mock_reporter

        handler = ProgressHandler(verbose=True, progress="detailed")

        mock_configure.assert_called_once_with(
            verbose=True, progress="detailed"
        )
        assert handler.detailed is True

    @patch("src.ostruct.cli.utils.progress_utils.configure_progress_reporter")
    @patch("src.ostruct.cli.utils.progress_utils.get_progress_reporter")
    def test_simple_phase(self, mock_get_reporter, mock_configure):
        """Test simple_phase method."""
        mock_reporter = Mock()
        mock_get_reporter.return_value = mock_reporter

        handler = ProgressHandler()
        handler.simple_phase("Test Phase", "🧪")

        mock_reporter.report_phase.assert_called_once_with("Test Phase", "🧪")


class TestBatchPhaseContext:
    """Test the BatchPhaseContext class."""

    def test_context_manager_success(self):
        """Test BatchPhaseContext as successful context manager."""
        mock_handler = Mock()
        mock_handle = {"test": "handle"}

        context = BatchPhaseContext(mock_handler, mock_handle)

        # Test __enter__
        result = context.__enter__()
        assert result == context

        # Test __exit__ with success (no exception)
        context.__exit__(None, None, None)
        mock_handler.reporter.complete.assert_called_once_with(
            mock_handle, success=True
        )

    def test_context_manager_failure(self):
        """Test BatchPhaseContext as failing context manager."""
        mock_handler = Mock()
        mock_handle = {"test": "handle"}

        context = BatchPhaseContext(mock_handler, mock_handle)

        # Test __exit__ with exception
        exc_type = ValueError
        exc_val = ValueError("test error")
        exc_tb = None

        context.__exit__(exc_type, exc_val, exc_tb)
        mock_handler.reporter.complete.assert_called_once_with(
            mock_handle, success=False
        )

    def test_advance(self):
        """Test advance method."""
        mock_handler = Mock()
        mock_handle = {"test": "handle"}

        context = BatchPhaseContext(mock_handler, mock_handle)
        context.advance(advance=2, msg="Test message")

        mock_handler.reporter.advance.assert_called_once_with(
            mock_handle, advance=2, msg="Test message"
        )


class TestIntegration:
    """Integration tests for ProgressHandler and BatchPhaseContext."""

    @patch("src.ostruct.cli.utils.progress_utils.configure_progress_reporter")
    @patch("src.ostruct.cli.utils.progress_utils.get_progress_reporter")
    def test_batch_phase_integration(self, mock_get_reporter, mock_configure):
        """Test full batch phase workflow."""
        mock_reporter = Mock()
        mock_handle = {"phase": "test"}
        mock_reporter.start_phase.return_value = mock_handle
        mock_get_reporter.return_value = mock_reporter

        handler = ProgressHandler(progress="detailed")

        # Use context manager
        with handler.batch_phase("Processing items", "📋", 3) as phase:
            phase.advance(msg="Item 1")
            phase.advance(msg="Item 2")
            phase.advance(msg="Item 3")

        # Verify calls
        mock_reporter.start_phase.assert_called_once_with(
            "Processing items", "📋", 3
        )
        assert mock_reporter.advance.call_count == 3
        mock_reporter.complete.assert_called_once_with(
            mock_handle, success=True
        )

    @patch("src.ostruct.cli.utils.progress_utils.configure_progress_reporter")
    @patch("src.ostruct.cli.utils.progress_utils.get_progress_reporter")
    def test_batch_phase_with_exception(
        self, mock_get_reporter, mock_configure
    ):
        """Test batch phase workflow with exception."""
        mock_reporter = Mock()
        mock_handle = {"phase": "test"}
        mock_reporter.start_phase.return_value = mock_handle
        mock_get_reporter.return_value = mock_reporter

        handler = ProgressHandler()

        # Use context manager with exception
        with pytest.raises(ValueError):
            with handler.batch_phase("Failing process", "❌", 1) as phase:
                phase.advance(msg="Before error")
                raise ValueError("Test error")

        # Verify completion was called with success=False
        mock_reporter.complete.assert_called_once_with(
            mock_handle, success=False
        )
