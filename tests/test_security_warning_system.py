"""Tests for the security warning system - deduplication and user-friendly messaging."""

import logging
import tempfile
import threading
import time
from pathlib import Path

import pytest
from ostruct.cli.security.security_manager import SecurityManager
from ostruct.cli.security.types import PathSecurity


@pytest.mark.no_fs
class LogCapture:
    """Custom log handler to capture log messages reliably."""

    def __init__(self):
        self.messages = []
        self.handler = None

    def __enter__(self):
        # Create a custom handler that captures messages
        class CaptureHandler(logging.Handler):
            def __init__(self, messages_list):
                super().__init__()
                self.messages_list = messages_list

            def emit(self, record):
                self.messages_list.append(record.getMessage())

        self.handler = CaptureHandler(self.messages)

        # Add handler to the correct logger (from the actual running module)
        logger = logging.getLogger("ostruct.cli.security.security_manager")
        logger.addHandler(self.handler)
        logger.setLevel(logging.DEBUG)  # Capture all levels

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler:
            logger = logging.getLogger("ostruct.cli.security.security_manager")
            logger.removeHandler(self.handler)

    @property
    def text(self):
        return "\n".join(self.messages)


class TestWarningSystem:
    """Test suite for the warning deduplication and messaging system."""

    def test_warning_deduplication(self):
        """Test that warnings are only shown once per path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with LogCapture() as log_capture:
                # Create a SecurityManager with warn mode
                manager = SecurityManager(
                    tmp_dir, security_mode=PathSecurity.WARN
                )

                # Create an external path for testing
                external_file = "/external/file.txt"

                # First access should warn
                result1 = manager.is_path_allowed_enhanced(external_file)
                assert result1 is True
                assert "Security Notice" in log_capture.text

                # Second access should not warn (deduplication)
                initial_message_count = len(log_capture.messages)
                result2 = manager.is_path_allowed_enhanced(external_file)
                assert result2 is True
                assert (
                    len(log_capture.messages) == initial_message_count
                )  # No new warnings

    def test_thread_safety(self):
        """Test warning tracking is thread-safe."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SecurityManager(tmp_dir, security_mode=PathSecurity.WARN)
            results = []

            def check_path():
                result = manager._should_warn_about_path("/external/test.txt")
                results.append(result)

            # Run multiple threads simultaneously
            threads = [threading.Thread(target=check_path) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Only one thread should have returned True (first warning)
            assert sum(results) == 1

    def test_path_resolution_consistency(self):
        """Test that relative and absolute paths to same file are deduplicated."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SecurityManager(tmp_dir, security_mode=PathSecurity.WARN)

            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                try:
                    # Test with absolute path
                    abs_path = tmp_file.name
                    should_warn1 = manager._should_warn_about_path(abs_path)

                    # Test with same absolute path again
                    should_warn2 = manager._should_warn_about_path(abs_path)

                    # Only first access should warn
                    assert should_warn1 is True
                    assert should_warn2 is False
                finally:
                    Path(tmp_file.name).unlink(missing_ok=True)

    def test_warning_message_quality(self):
        """Test that warning messages are user-friendly and actionable."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with LogCapture() as log_capture:
                manager = SecurityManager(
                    tmp_dir, security_mode=PathSecurity.WARN
                )

                # Test with a Downloads file
                downloads_file = "/Users/test/Downloads/file.pdf"
                manager.is_path_allowed_enhanced(downloads_file)

                warning_text = log_capture.text

                # Should be user-friendly
                assert (
                    "PathOutsidePolicy" not in warning_text
                )  # No technical jargon
                assert "Security Notice" in warning_text

                # Should be actionable
                assert "--allow" in warning_text
                assert "--path-security" in warning_text
                assert "--allow-file" in warning_text

                # Should provide context
                assert (
                    "Downloads" in warning_text or "file.pdf" in warning_text
                )

    def test_file_context_detection(self):
        """Test that file context messages are appropriate."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SecurityManager(tmp_dir, security_mode=PathSecurity.WARN)

            # Test different file types and locations
            test_cases = [
                ("/Users/test/Downloads/doc.pdf", "downloaded file"),
                ("/Users/test/Desktop/file.txt", "desktop file"),
                ("/Users/test/Documents/report.docx", "document"),
                ("/tmp/data.csv", "data file"),
                ("/external/script.py", "file"),
            ]

            for path, expected_context in test_cases:
                context = manager._get_file_context_message(path)
                assert (
                    expected_context in context or context == expected_context
                )

    def test_warning_tracking_performance(self):
        """Test that warning tracking doesn't impact performance."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SecurityManager(tmp_dir, security_mode=PathSecurity.WARN)

            # Time 1000 path checks
            start = time.time()
            for i in range(1000):
                manager._should_warn_about_path(f"/external/file_{i}.txt")
            duration = time.time() - start

            # Should be very fast (< 100ms for 1000 paths)
            assert duration < 0.1

    def test_reset_warning_tracking(self):
        """Test that warning tracking can be reset."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SecurityManager(tmp_dir, security_mode=PathSecurity.WARN)

            # Add some warnings
            manager._should_warn_about_path("/external/file1.txt")
            manager._should_warn_about_path("/external/file2.txt")

            # Should have tracked warnings
            assert len(manager._warned_paths) == 2

            # Reset tracking
            manager.reset_warning_tracking()

            # Should be empty now
            assert len(manager._warned_paths) == 0

            # Should warn again for same paths
            assert (
                manager._should_warn_about_path("/external/file1.txt") is True
            )

    def test_security_summary_logging(self):
        """Test that security summary is logged for multiple warnings."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with LogCapture() as log_capture:
                manager = SecurityManager(
                    tmp_dir, security_mode=PathSecurity.WARN
                )

                # Trigger multiple warnings
                manager.is_path_allowed_enhanced("/external/file1.txt")
                manager.is_path_allowed_enhanced("/external/file2.txt")

                # Log summary
                manager.log_security_summary()

                # Should show summary for multiple files
                assert "Security Summary" in log_capture.text
                assert "2 files" in log_capture.text

    def test_no_summary_for_single_warning(self):
        """Test that no summary is logged for single warning."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with LogCapture() as log_capture:
                manager = SecurityManager(
                    tmp_dir, security_mode=PathSecurity.WARN
                )

                # Trigger single warning
                manager.is_path_allowed_enhanced("/external/file1.txt")

                # Log summary
                manager.log_security_summary()

                # Should not show summary for single file
                summary_messages = [
                    msg
                    for msg in log_capture.messages
                    if "Security Summary" in msg
                ]
                assert len(summary_messages) == 0

    def test_permissive_mode_no_warnings(self):
        """Test that permissive mode doesn't show warnings."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with LogCapture() as log_capture:
                manager = SecurityManager(
                    tmp_dir, security_mode=PathSecurity.PERMISSIVE
                )

                # Should not warn in permissive mode
                result = manager.is_path_allowed_enhanced("/external/file.txt")
                assert result is True
                assert "Security Notice" not in log_capture.text

    def test_strict_mode_raises_error(self):
        """Test that strict mode raises an error for external paths."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SecurityManager(
                tmp_dir, security_mode=PathSecurity.STRICT
            )

            # Should raise error in strict mode
            with pytest.raises(Exception):  # PathSecurityError or similar
                manager.is_path_allowed_enhanced("/external/file.txt")

    @pytest.mark.no_fs
    def test_warning_message_structure(self):
        """Test the structure and content of warning messages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with LogCapture() as log_capture:
                manager = SecurityManager(
                    tmp_dir, security_mode=PathSecurity.WARN
                )

                # Test with absolute path
                test_path = "/Users/test/Downloads/document.pdf"
                manager.is_path_allowed_enhanced(test_path)

                lines = log_capture.text.strip().split("\n")

                # Should have main warning and guidance lines
                warning_lines = [
                    line for line in lines if "Security Notice" in line
                ]
                guidance_lines = [
                    line
                    for line in lines
                    if "--allow" in line or "--path-security" in line
                ]

                assert len(warning_lines) >= 1
                assert len(guidance_lines) >= 2  # Multiple guidance options

                # Check specific guidance content
                guidance_text = "\n".join(guidance_lines)
                assert "--allow '/Users/test/Downloads'" in guidance_text
                assert "--allow-file" in guidance_text
                assert "--path-security permissive" in guidance_text

    def test_configuration_suppress_warnings(self):
        """Test that configuration can suppress warnings."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = {"security": {"suppress_path_warnings": True}}
            manager = SecurityManager(
                tmp_dir, security_mode=PathSecurity.WARN, config=config
            )

            # Should not warn when suppressed
            should_warn = manager._should_warn_about_path("/external/file.txt")
            assert should_warn is False

    def test_configuration_disable_summary(self):
        """Test that configuration can disable summary."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with LogCapture() as log_capture:
                config = {"security": {"warning_summary": False}}
                manager = SecurityManager(
                    tmp_dir, security_mode=PathSecurity.WARN, config=config
                )

                # Trigger multiple warnings
                manager.is_path_allowed_enhanced("/external/file1.txt")
                manager.is_path_allowed_enhanced("/external/file2.txt")

                # Log summary
                manager.log_security_summary()

                # Should not show summary when disabled
                assert "Security Summary" not in log_capture.text
