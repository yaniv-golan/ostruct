"""Tests for JSON output formatting utilities."""

import json

import pytest

from src.ostruct.cli.utils.json_output import JSONOutputHandler


class TestJSONOutputHandler:
    """Test the JSONOutputHandler class."""

    def test_init_default(self):
        """Test JSONOutputHandler initialization with defaults."""
        handler = JSONOutputHandler()

        assert handler.include_metadata is True
        assert handler.indent is None

    def test_init_custom(self):
        """Test JSONOutputHandler initialization with custom settings."""
        handler = JSONOutputHandler(include_metadata=False, indent=2)

        assert handler.include_metadata is False
        assert handler.indent == 2

    def test_format_results_basic(self):
        """Test basic results formatting."""
        handler = JSONOutputHandler(include_metadata=False)

        success_items = [{"id": "file1", "path": "/test/file1.txt"}]
        errors = ["error1", "error2"]

        result = handler.format_results(
            success_items=success_items, errors=errors, operation="test"
        )

        assert result["results"] == success_items
        assert result["errors"] == errors
        assert result["summary"]["total"] == 3  # 1 success + 2 errors
        assert result["summary"]["processed"] == 1
        assert result["summary"]["errors"] == 2
        assert "metadata" not in result

    def test_format_results_with_cached(self):
        """Test results formatting with cached items."""
        handler = JSONOutputHandler(include_metadata=False)

        success_items = [{"id": "file1"}]
        cached_items = [{"id": "file2"}]
        errors = ["error1"]

        result = handler.format_results(
            success_items=success_items,
            cached_items=cached_items,
            errors=errors,
        )

        assert result["uploaded"] == success_items
        assert result["cached"] == cached_items
        assert result["errors"] == errors
        assert result["summary"]["total"] == 3
        assert result["summary"]["uploaded"] == 1
        assert result["summary"]["cached"] == 1
        assert result["summary"]["errors"] == 1

    def test_format_results_with_metadata(self):
        """Test results formatting with metadata."""
        handler = JSONOutputHandler(include_metadata=True)

        metadata = {"tool": "upload", "version": "1.0"}

        result = handler.format_results(
            success_items=[{"id": "file1"}],
            metadata=metadata,
            operation="upload",
        )

        assert "metadata" in result
        assert result["metadata"]["operation"] == "upload"
        assert "timestamp" in result["metadata"]
        assert result["metadata"]["tool"] == "upload"
        assert result["metadata"]["version"] == "1.0"

    def test_format_results_empty(self):
        """Test results formatting with no items."""
        handler = JSONOutputHandler(include_metadata=False)

        result = handler.format_results()

        assert result["errors"] == []
        assert result["summary"]["total"] == 0
        assert result["summary"]["processed"] == 0
        assert result["summary"]["errors"] == 0

    def test_format_error_response_basic(self):
        """Test basic error response formatting."""
        handler = JSONOutputHandler(include_metadata=False)

        result = handler.format_error_response("Test error")

        assert result["error"] == "Test error"
        assert "error_code" not in result
        assert "metadata" not in result

    def test_format_error_response_with_code(self):
        """Test error response formatting with error code."""
        handler = JSONOutputHandler(include_metadata=False)

        result = handler.format_error_response("Test error", "E001")

        assert result["error"] == "Test error"
        assert result["error_code"] == "E001"

    def test_format_error_response_with_metadata(self):
        """Test error response formatting with metadata."""
        handler = JSONOutputHandler(include_metadata=True)

        result = handler.format_error_response("Test error")

        assert result["error"] == "Test error"
        assert "metadata" in result
        assert "timestamp" in result["metadata"]
        assert result["metadata"]["success"] is False

    def test_format_dry_run_response(self):
        """Test dry-run response formatting."""
        handler = JSONOutputHandler(include_metadata=False)

        preview_data = {
            "files": ["file1.txt", "file2.txt"],
            "total_size": 1024,
            "tools": ["user-data"],
        }

        result = handler.format_dry_run_response(preview_data, "upload")

        assert result["dry_run"] is True
        assert result["files"] == ["file1.txt", "file2.txt"]
        assert result["total_size"] == 1024
        assert result["tools"] == ["user-data"]

    def test_format_dry_run_response_with_metadata(self):
        """Test dry-run response formatting with metadata."""
        handler = JSONOutputHandler(include_metadata=True)

        preview_data = {"files": ["file1.txt"]}

        result = handler.format_dry_run_response(preview_data, "test")

        assert result["dry_run"] is True
        assert "metadata" in result
        assert result["metadata"]["operation"] == "test"
        assert result["metadata"]["mode"] == "dry_run"
        assert "timestamp" in result["metadata"]

    @pytest.mark.parametrize(
        "indent,expect_newlines,expect_spaces",
        [
            (None, False, False),  # compact
            (2, True, True),  # indented
        ],
    )
    def test_to_json_formatting(self, indent, expect_newlines, expect_spaces):
        """Test JSON string conversion with different formatting options."""
        handler = JSONOutputHandler(indent=indent)

        data = {"test": "value", "nested": {"key": "value"}}
        json_str = handler.to_json(data)

        # Check formatting expectations
        assert ("\n" in json_str) == expect_newlines
        assert ("  " in json_str) == expect_spaces

        # Verify content is preserved
        parsed = json.loads(json_str)
        assert parsed == data

    def test_should_output_json(self):
        """Test should_output_json static method."""
        assert JSONOutputHandler.should_output_json(True) is True
        assert JSONOutputHandler.should_output_json(False) is False

    def test_is_json_mode_compatible(self):
        """Test is_json_mode_compatible static method."""
        # Compatible cases
        assert (
            JSONOutputHandler.is_json_mode_compatible(False) is True
        )  # Not JSON mode
        assert (
            JSONOutputHandler.is_json_mode_compatible(
                True, interactive=False, progress="none"
            )
            is True
        )

        # Incompatible cases
        assert (
            JSONOutputHandler.is_json_mode_compatible(True, interactive=True)
            is False
        )
        assert (
            JSONOutputHandler.is_json_mode_compatible(True, progress="basic")
            is False
        )
        assert (
            JSONOutputHandler.is_json_mode_compatible(
                True, progress="detailed"
            )
            is False
        )

    def test_format_list_response(self):
        """Test list response formatting."""
        handler = JSONOutputHandler(include_metadata=False)

        items = [
            {"id": "file1", "name": "test1.txt"},
            {"id": "file2", "name": "test2.txt"},
        ]

        result = handler.format_list_response(items, "list_files")

        assert result["items"] == items
        assert result["count"] == 2
        assert "metadata" not in result

    def test_format_list_response_with_metadata(self):
        """Test list response formatting with metadata."""
        handler = JSONOutputHandler(include_metadata=True)

        items = [{"id": "file1"}]
        metadata = {"filter": "*.txt"}

        result = handler.format_list_response(items, "list_files", metadata)

        assert result["items"] == items
        assert result["count"] == 1
        assert "metadata" in result
        assert result["metadata"]["operation"] == "list_files"
        assert result["metadata"]["filter"] == "*.txt"
        assert "timestamp" in result["metadata"]

    def test_format_status_response_basic(self):
        """Test basic status response formatting."""
        handler = JSONOutputHandler(include_metadata=False)

        result = handler.format_status_response("success")

        assert result["status"] == "success"
        assert "message" not in result
        assert "data" not in result
        assert "metadata" not in result

    def test_format_status_response_with_message_and_data(self):
        """Test status response formatting with message and data."""
        handler = JSONOutputHandler(include_metadata=False)

        data = {"files_processed": 5}

        result = handler.format_status_response(
            "completed", "Operation finished", data
        )

        assert result["status"] == "completed"
        assert result["message"] == "Operation finished"
        assert result["data"] == data

    def test_format_status_response_with_metadata(self):
        """Test status response formatting with metadata."""
        handler = JSONOutputHandler(include_metadata=True)

        result = handler.format_status_response("success")

        assert result["status"] == "success"
        assert "metadata" in result
        assert "timestamp" in result["metadata"]
        assert result["metadata"]["success"] is True

        # Test failure status
        result_error = handler.format_status_response("error")
        assert result_error["metadata"]["success"] is False

    def test_format_summary_basic(self):
        """Test basic summary formatting."""
        handler = JSONOutputHandler()

        summary = handler.format_summary(total=10, processed=8, errors=2)

        assert summary["total"] == 10
        assert summary["processed"] == 8
        assert summary["errors"] == 2
        assert "uploaded" not in summary
        assert "cached" not in summary

    def test_format_results_with_custom_summary(self):
        """Test format_results using a custom summary."""
        handler = JSONOutputHandler(include_metadata=False)

        custom_summary = {
            "total": 100,
            "processed": 90,
            "errors": 10,
            "custom_field": "value",
        }
        success_items = [{"id": "item1"}]

        result = handler.format_results(
            success_items=success_items, summary=custom_summary
        )

        assert result["results"] == success_items
        assert result["summary"] == custom_summary
        # Ensure auto-generated summary is not used
        assert result["summary"]["total"] == 100  # Not len(success_items)
        assert result["summary"]["custom_field"] == "value"


class TestJSONOutputHandlerIntegration:
    """Integration tests for JSONOutputHandler."""

    def test_complete_upload_workflow(self):
        """Test complete upload workflow JSON formatting."""
        handler = JSONOutputHandler(include_metadata=True, indent=2)

        # Simulate upload results
        uploaded_files = [
            {"id": "file-123", "path": "/test/file1.txt", "size": 1024},
            {"id": "file-456", "path": "/test/file2.txt", "size": 2048},
        ]
        cached_files = [
            {"id": "file-789", "path": "/test/cached.txt", "size": 512}
        ]
        errors = ["file3.txt: Permission denied"]
        metadata = {"operation_id": "upload-001", "user": "test_user"}

        result = handler.format_results(
            success_items=uploaded_files,
            cached_items=cached_files,
            errors=errors,
            metadata=metadata,
            operation="upload",
        )

        # Verify structure
        assert result["uploaded"] == uploaded_files
        assert result["cached"] == cached_files
        assert result["errors"] == errors
        assert (
            result["summary"]["total"] == 4
        )  # 2 uploaded + 1 cached + 1 error
        assert result["summary"]["uploaded"] == 2
        assert result["summary"]["cached"] == 1
        assert result["summary"]["errors"] == 1

        # Verify metadata
        assert result["metadata"]["operation"] == "upload"
        assert result["metadata"]["operation_id"] == "upload-001"
        assert result["metadata"]["user"] == "test_user"
        assert "timestamp" in result["metadata"]

        # Verify JSON serialization
        json_str = handler.to_json(result)
        parsed = json.loads(json_str)
        assert parsed == result
        assert "\n" in json_str  # Should be indented

    def test_error_handling_workflow(self):
        """Test error handling workflow JSON formatting."""
        handler = JSONOutputHandler(include_metadata=True)

        # Test error response
        error_result = handler.format_error_response(
            "Failed to connect to API", "CONN_001"
        )

        assert error_result["error"] == "Failed to connect to API"
        assert error_result["error_code"] == "CONN_001"
        assert error_result["metadata"]["success"] is False

        # Verify JSON serialization
        json_str = handler.to_json(error_result)
        parsed = json.loads(json_str)
        assert parsed == error_result

    def test_dry_run_workflow(self):
        """Test dry-run workflow JSON formatting."""
        handler = JSONOutputHandler(include_metadata=True)

        preview_data = {
            "files": ["/test/file1.txt", "/test/file2.txt"],
            "total_files": 2,
            "total_size": 3072,
            "tools": ["user-data", "file-search"],
            "vector_store": "test_store",
        }

        result = handler.format_dry_run_response(preview_data, "upload")

        assert result["dry_run"] is True
        assert result["files"] == preview_data["files"]
        assert result["total_files"] == 2
        assert result["total_size"] == 3072
        assert result["tools"] == ["user-data", "file-search"]
        assert result["vector_store"] == "test_store"

        # Verify metadata
        assert result["metadata"]["operation"] == "upload"
        assert result["metadata"]["mode"] == "dry_run"
        assert "timestamp" in result["metadata"]

        # Verify JSON serialization
        json_str = handler.to_json(result)
        parsed = json.loads(json_str)
        assert parsed == result
