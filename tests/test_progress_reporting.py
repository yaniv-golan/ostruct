"""Test enhanced progress reporting functionality."""

from unittest.mock import Mock, patch

from ostruct.cli.progress_reporting import (
    EnhancedProgressReporter,
    configure_progress_reporter,
    get_progress_reporter,
)


class TestEnhancedProgressReporter:
    """Test the EnhancedProgressReporter class."""

    def test_init_basic_level(self):
        """Test reporter initialization with basic level."""
        reporter = EnhancedProgressReporter(verbose=False, progress="basic")
        assert reporter.progress == "basic"
        assert reporter.should_report is True
        assert reporter.detailed is False

    def test_init_detailed_level(self):
        """Test reporter initialization with detailed level."""
        reporter = EnhancedProgressReporter(verbose=False, progress="detailed")
        assert reporter.progress == "detailed"
        assert reporter.should_report is True
        assert reporter.detailed is True

    def test_init_none_level(self):
        """Test reporter initialization with none level."""
        reporter = EnhancedProgressReporter(verbose=False, progress="none")
        assert reporter.progress == "none"
        assert reporter.should_report is False
        assert reporter.detailed is False

    def test_init_verbose_mode(self):
        """Test reporter initialization with verbose mode."""
        reporter = EnhancedProgressReporter(verbose=True, progress="basic")
        assert reporter.verbose is True
        assert reporter.detailed is True  # verbose enables detailed

    @patch("click.echo")
    def test_start_phase_without_progress_bar(self, mock_echo):
        """Test starting a phase without progress bar."""
        reporter = EnhancedProgressReporter(verbose=False, progress="basic")

        handle = reporter.start_phase("Test Phase", "🔧")

        # Should echo the phase message
        mock_echo.assert_called_once_with("🔧 Test Phase...", err=True)

        # Handle should not have progress bar
        assert handle["phase_name"] == "Test Phase"
        assert handle["emoji"] == "🔧"
        assert handle["expected_steps"] is None
        assert handle["progress"] is None
        assert handle["task"] is None

    @patch("click.echo")
    @patch("ostruct.cli.progress_reporting.Progress")
    def test_start_phase_with_progress_bar(self, mock_progress_cls, mock_echo):
        """Test starting a phase with progress bar."""
        # Setup mock progress bar
        mock_progress = Mock()
        mock_progress.add_task.return_value = "task-123"
        mock_progress_cls.return_value = mock_progress

        reporter = EnhancedProgressReporter(verbose=False, progress="basic")

        handle = reporter.start_phase("Upload Files", "📤", expected_steps=5)

        # Should echo the phase message
        mock_echo.assert_called_once_with("📤 Upload Files...", err=True)

        # Should create and start progress bar
        mock_progress_cls.assert_called_once()
        mock_progress.start.assert_called_once()
        mock_progress.add_task.assert_called_once_with("Upload Files", total=5)

        # Handle should have progress bar info
        assert handle["phase_name"] == "Upload Files"
        assert handle["expected_steps"] == 5
        assert handle["progress"] == mock_progress
        assert handle["task"] == "task-123"

    @patch("click.echo")
    def test_start_phase_none_level(self, mock_echo):
        """Test starting a phase with none level does nothing."""
        reporter = EnhancedProgressReporter(verbose=False, progress="none")

        handle = reporter.start_phase("Test Phase", "🔧", expected_steps=3)

        # Should not echo anything
        mock_echo.assert_not_called()

        # Handle should still be created but with no progress
        assert handle["progress"] is None
        assert handle["task"] is None

    def test_advance_without_progress_bar(self):
        """Test advancing without progress bar."""
        reporter = EnhancedProgressReporter(verbose=False, progress="basic")
        handle = {
            "phase_name": "Test",
            "progress": None,
            "task": None,
        }

        # Should not raise any errors
        reporter.advance(handle, advance=1, msg="Test message")

    @patch("click.echo")
    def test_advance_with_progress_bar(self, mock_echo):
        """Test advancing with progress bar."""
        mock_progress = Mock()
        reporter = EnhancedProgressReporter(verbose=False, progress="basic")
        handle = {
            "phase_name": "Test",
            "progress": mock_progress,
            "task": "task-123",
        }

        reporter.advance(handle, advance=2, msg="Processing file")

        # Should update progress bar
        mock_progress.update.assert_called_once_with("task-123", advance=2)

        # Should not echo message in basic mode
        mock_echo.assert_not_called()

    @patch("click.echo")
    def test_advance_detailed_mode_with_message(self, mock_echo):
        """Test advancing in detailed mode with message."""
        mock_progress = Mock()
        reporter = EnhancedProgressReporter(verbose=False, progress="detailed")
        handle = {
            "phase_name": "Test",
            "progress": mock_progress,
            "task": "task-123",
        }

        reporter.advance(handle, advance=1, msg="Uploaded file.txt")

        # Should update progress bar
        mock_progress.update.assert_called_once_with("task-123", advance=1)

        # Should echo detailed message
        mock_echo.assert_called_once_with("  Uploaded file.txt", err=True)

    @patch("click.echo")
    def test_advance_none_level(self, mock_echo):
        """Test advancing with none level does nothing."""
        mock_progress = Mock()
        reporter = EnhancedProgressReporter(verbose=False, progress="none")
        handle = {
            "phase_name": "Test",
            "progress": mock_progress,
            "task": "task-123",
        }

        reporter.advance(handle, advance=1, msg="Test message")

        # Should not update progress or echo
        mock_progress.update.assert_not_called()
        mock_echo.assert_not_called()

    @patch("click.echo")
    def test_complete_success(self, mock_echo):
        """Test completing a phase successfully."""
        mock_progress = Mock()
        reporter = EnhancedProgressReporter(verbose=False, progress="basic")
        handle = {
            "phase_name": "Upload Files",
            "progress": mock_progress,
            "task": "task-123",
            "expected_steps": 5,
        }

        reporter.complete(
            handle, success=True, final_message="All files uploaded"
        )

        # Should complete progress bar
        mock_progress.update.assert_called_once_with("task-123", completed=5)
        mock_progress.stop.assert_called_once()

        # Should echo success message
        mock_echo.assert_called_once_with("✅ All files uploaded", err=True)

    @patch("click.echo")
    def test_complete_failure(self, mock_echo):
        """Test completing a phase with failure."""
        mock_progress = Mock()
        reporter = EnhancedProgressReporter(verbose=False, progress="basic")
        handle = {
            "phase_name": "Upload Files",
            "progress": mock_progress,
            "task": "task-123",
            "expected_steps": 5,
        }

        reporter.complete(handle, success=False)

        # Should complete progress bar
        mock_progress.update.assert_called_once_with("task-123", completed=5)
        mock_progress.stop.assert_called_once()

        # Should echo failure message
        mock_echo.assert_called_once_with("❌ Upload Files failed", err=True)

    @patch("click.echo")
    def test_complete_without_progress_bar(self, mock_echo):
        """Test completing without progress bar."""
        reporter = EnhancedProgressReporter(verbose=False, progress="basic")
        handle = {
            "phase_name": "Simple Phase",
            "progress": None,
            "task": None,
        }

        reporter.complete(handle, success=True)

        # Should only echo completion message
        mock_echo.assert_called_once_with(
            "✅ Simple Phase completed", err=True
        )


class TestProgressReporterGlobals:
    """Test global progress reporter functions."""

    def test_configure_progress_reporter(self):
        """Test configuring the global progress reporter."""
        configure_progress_reporter(verbose=True, progress="detailed")

        reporter = get_progress_reporter()
        assert reporter.verbose is True
        assert reporter.progress == "detailed"
        assert reporter.detailed is True

    def test_get_progress_reporter_default(self):
        """Test getting default progress reporter."""
        # Reset global state
        import ostruct.cli.progress_reporting

        ostruct.cli.progress_reporting._progress_reporter = None

        reporter = get_progress_reporter()
        assert isinstance(reporter, EnhancedProgressReporter)
        assert reporter.progress == "basic"  # default
        assert reporter.verbose is False  # default
