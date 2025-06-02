"""Tests for file routing intent functionality and large file warnings."""

import logging
import os
from typing import List

import pytest
from ostruct.cli.file_info import FileInfo, FileRoutingIntent
from pyfakefs.fake_filesystem import FakeFilesystem

from tests.conftest import MockSecurityManager


class LogCapture(logging.Handler):
    """Custom log capture handler for testing."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        """Capture a log record."""
        self.records.append(record)

    def setup(self, logger_name: str, level: int = logging.WARNING):
        """Set up log capture for a specific logger."""
        self.records.clear()
        logger = logging.getLogger(logger_name)

        # Set level and add handler
        self.setLevel(level)
        logger.addHandler(self)
        logger.setLevel(level)
        logger.propagate = True

    def teardown(self, logger_name: str):
        """Clean up the log capture."""
        logger = logging.getLogger(logger_name)
        logger.removeHandler(self)


class TestFileRoutingIntent:
    """Test FileRoutingIntent enum and its usage."""

    def test_routing_intent_enum_values(self) -> None:
        """Test that FileRoutingIntent enum has correct values."""
        assert FileRoutingIntent.TEMPLATE_ONLY.value == "template_only"
        assert FileRoutingIntent.CODE_INTERPRETER.value == "code_interpreter"
        assert FileRoutingIntent.FILE_SEARCH.value == "file_search"

    def test_routing_intent_enum_members(self) -> None:
        """Test that all expected enum members exist."""
        expected_members = {"TEMPLATE_ONLY", "CODE_INTERPRETER", "FILE_SEARCH"}
        actual_members = {member.name for member in FileRoutingIntent}
        assert actual_members == expected_members


class TestFileInfoRoutingIntent:
    """Test FileInfo with routing intent functionality."""

    def test_file_info_with_routing_intent(
        self, fs: FakeFilesystem, security_manager: MockSecurityManager
    ) -> None:
        """Test FileInfo creation with routing_intent parameter."""
        # Create test file
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        # Test with different routing intents
        for intent in FileRoutingIntent:
            file_info = FileInfo.from_path(
                "test.txt",
                security_manager=security_manager,
                routing_intent=intent,
            )
            assert file_info.routing_intent == intent

    def test_file_info_without_routing_intent(
        self, fs: FakeFilesystem, security_manager: MockSecurityManager
    ) -> None:
        """Test FileInfo creation without routing_intent parameter."""
        fs.create_file(
            "/test_workspace/base/test.txt", contents="test content"
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        file_info = FileInfo.from_path(
            "test.txt", security_manager=security_manager
        )
        assert file_info.routing_intent is None


class TestLargeFileWarnings:
    """Test large file warning behavior with routing intent."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.large_content = "A" * 200000  # 200KB content

    def test_large_file_warning_template_only(
        self,
        fs: FakeFilesystem,
        security_manager: MockSecurityManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that large file warning appears for TEMPLATE_ONLY intent."""
        # Create large file
        fs.create_file(
            "/test_workspace/base/large.txt", contents=self.large_content
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        file_info = FileInfo.from_path(
            "large.txt",
            security_manager=security_manager,
            routing_intent=FileRoutingIntent.TEMPLATE_ONLY,
        )

        # Use custom log capture to ensure we catch the warning
        log_capture = LogCapture()
        log_capture.setup("ostruct.cli.file_info", logging.WARNING)

        try:
            # Access content to trigger warning
            _ = file_info.content

            # Check that warning was logged
            warning_messages = [
                record.getMessage()
                for record in log_capture.records
                if record.levelname == "WARNING"
                and "large file" in record.getMessage().lower()
            ]
            assert (
                len(warning_messages) > 0
            ), f"Expected warning message not found. All records: {[r.getMessage() for r in log_capture.records]}"
        finally:
            log_capture.teardown("ostruct.cli.file_info")

    def test_large_file_no_warning_code_interpreter(
        self,
        fs: FakeFilesystem,
        security_manager: MockSecurityManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that large file warning does NOT appear for CODE_INTERPRETER intent."""
        # Create large file
        fs.create_file(
            "/test_workspace/base/large.txt", contents=self.large_content
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        file_info = FileInfo.from_path(
            "large.txt",
            security_manager=security_manager,
            routing_intent=FileRoutingIntent.CODE_INTERPRETER,
        )

        with caplog.at_level(logging.WARNING):
            # Access content to trigger potential warning
            _ = file_info.content

        # Check that NO warning was logged
        warning_records: List[logging.LogRecord] = [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and "large file" in r.message.lower()
        ]
        assert len(warning_records) == 0

    def test_large_file_no_warning_file_search(
        self,
        fs: FakeFilesystem,
        security_manager: MockSecurityManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that large file warning does NOT appear for FILE_SEARCH intent."""
        # Create large file
        fs.create_file(
            "/test_workspace/base/large.txt", contents=self.large_content
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        file_info = FileInfo.from_path(
            "large.txt",
            security_manager=security_manager,
            routing_intent=FileRoutingIntent.FILE_SEARCH,
        )

        with caplog.at_level(logging.WARNING):
            # Access content to trigger potential warning
            _ = file_info.content

        # Check that NO warning was logged
        warning_records: List[logging.LogRecord] = [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and "large file" in r.message.lower()
        ]
        assert len(warning_records) == 0

    def test_large_file_warning_fallback_behavior(
        self,
        fs: FakeFilesystem,
        security_manager: MockSecurityManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test fallback behavior when routing_intent is None."""
        # Create large file
        fs.create_file(
            "/test_workspace/base/large.txt", contents=self.large_content
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        # Create FileInfo without routing_intent (None) but with routing_type="template"
        file_info = FileInfo.from_path(
            "large.txt",
            security_manager=security_manager,
            routing_type="template",  # Set during initialization
        )

        # Use custom log capture to ensure we catch the warning
        log_capture = LogCapture()
        log_capture.setup("ostruct.cli.file_info", logging.WARNING)

        try:
            # Access content to trigger warning
            _ = file_info.content

            # Check that warning was logged (fallback to old logic)
            warning_messages = [
                record.getMessage()
                for record in log_capture.records
                if record.levelname == "WARNING"
                and "large file" in record.getMessage().lower()
            ]
            assert (
                len(warning_messages) > 0
            ), f"Expected warning message not found. All records: {[r.getMessage() for r in log_capture.records]}"
        finally:
            log_capture.teardown("ostruct.cli.file_info")

    def test_small_file_no_warning(
        self,
        fs: FakeFilesystem,
        security_manager: MockSecurityManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that small files don't trigger warnings regardless of intent."""
        # Create small file
        fs.create_file(
            "/test_workspace/base/small.txt", contents="small content"
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        for intent in FileRoutingIntent:
            caplog.clear()

            file_info = FileInfo.from_path(
                "small.txt",
                security_manager=security_manager,
                routing_intent=intent,
            )

            with caplog.at_level(logging.WARNING):
                # Access content
                _ = file_info.content

            # Check that NO warning was logged
            warning_records: List[logging.LogRecord] = [
                r
                for r in caplog.records
                if r.levelname == "WARNING"
                and "large file" in r.message.lower()
            ]
            assert len(warning_records) == 0


class TestIntentMappingEdgeCases:
    """Test edge cases for intent mapping."""

    def test_none_routing_intent_with_template_routing_type(
        self,
        fs: FakeFilesystem,
        security_manager: MockSecurityManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test fallback logic when routing_intent is None but routing_type is template."""
        # Create large file to trigger warning
        large_content = "A" * 200000
        fs.create_file(
            "/test_workspace/base/large.txt", contents=large_content
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        file_info = FileInfo.from_path(
            "large.txt",
            security_manager=security_manager,
            routing_intent=None,  # Explicitly None
            routing_type="template",  # Set during initialization
        )

        # Use custom log capture to ensure we catch the warning
        log_capture = LogCapture()
        log_capture.setup("ostruct.cli.file_info", logging.WARNING)

        try:
            # Access content to trigger warning
            _ = file_info.content

            # Should trigger warning due to fallback logic
            warning_messages = [
                record.getMessage()
                for record in log_capture.records
                if record.levelname == "WARNING"
                and "large file" in record.getMessage().lower()
            ]
            assert (
                len(warning_messages) > 0
            ), f"Expected warning message not found. All records: {[r.getMessage() for r in log_capture.records]}"
        finally:
            log_capture.teardown("ostruct.cli.file_info")

    def test_none_routing_intent_with_non_template_routing_type(
        self,
        fs: FakeFilesystem,
        security_manager: MockSecurityManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test fallback logic when routing_intent is None and routing_type is not template."""
        # Create large file
        large_content = "A" * 200000
        fs.create_file(
            "/test_workspace/base/large.txt", contents=large_content
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        file_info = FileInfo.from_path(
            "large.txt",
            security_manager=security_manager,
            routing_intent=None,  # Explicitly None
            routing_type="code-interpreter",  # Non-template type set during initialization
        )

        with caplog.at_level(logging.WARNING):
            # Access content
            _ = file_info.content

        # Should NOT trigger warning due to fallback logic
        warning_records: List[logging.LogRecord] = [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and "large file" in r.message.lower()
        ]
        assert len(warning_records) == 0

    def test_routing_intent_precedence_over_routing_type(
        self,
        fs: FakeFilesystem,
        security_manager: MockSecurityManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that routing_intent takes precedence over routing_type."""
        # Create large file
        large_content = "A" * 200000
        fs.create_file(
            "/test_workspace/base/large.txt", contents=large_content
        )
        os.chdir("/test_workspace/base")  # Change to base directory

        file_info = FileInfo.from_path(
            "large.txt",
            security_manager=security_manager,
            routing_intent=FileRoutingIntent.CODE_INTERPRETER,
            routing_type="template",  # Conflicting routing_type set during initialization
        )

        with caplog.at_level(logging.WARNING):
            # Access content
            _ = file_info.content

        # Should NOT trigger warning because routing_intent takes precedence
        warning_records: List[logging.LogRecord] = [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and "large file" in r.message.lower()
        ]
        assert len(warning_records) == 0
