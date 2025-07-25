"""Tests for error handling utilities."""

from pathlib import Path

from src.ostruct.cli.utils.error_utils import ErrorCollector


class TestErrorCollector:
    """Test the ErrorCollector class."""

    def test_init(self):
        """Test ErrorCollector initialization."""
        collector = ErrorCollector()

        assert collector.errors == []
        assert not collector.has_errors()
        assert collector.get_error_count() == 0

    def test_add_error_basic(self):
        """Test adding a basic error."""
        collector = ErrorCollector()
        error = ValueError("Test error")

        collector.add_error("/test/file.txt", error)

        assert collector.has_errors()
        assert collector.get_error_count() == 1

        errors = collector.errors
        assert len(errors) == 1
        assert errors[0]["file_path"] == "/test/file.txt"
        assert errors[0]["error"] == error
        assert errors[0]["error_type"] == "ValueError"

    def test_add_error_with_context(self):
        """Test adding an error with context."""
        collector = ErrorCollector()
        error = RuntimeError("Context error")
        context = {"tool": "file-search", "attempt": 2}

        collector.add_error("/test/data.csv", error, context)

        errors = collector.errors
        assert errors[0]["context"] == context

    def test_format_error_file_extension(self):
        """Test formatting file extension errors."""
        collector = ErrorCollector()
        error = Exception(
            "Files without extensions are not supported for file-search"
        )

        formatted = collector.format_error("/test/README", error)

        assert "Cannot use with file-search (no file extension)" in formatted
        assert "README:" in formatted
        assert "uploaded successfully for template use" in formatted

    def test_format_error_vector_store(self):
        """Test formatting vector store errors."""
        collector = ErrorCollector()
        error = Exception("Failed to add files to vector store")

        formatted = collector.format_error("/test/document.pdf", error)

        assert "Upload succeeded but file-search binding failed" in formatted
        assert "document.pdf:" in formatted
        assert "available for template use" in formatted

    def test_format_error_permission(self):
        """Test formatting permission errors."""
        collector = ErrorCollector()
        error = PermissionError("Access denied")

        formatted = collector.format_error("/test/protected.txt", error)

        assert "Permission denied - check file access rights" in formatted
        assert "protected.txt:" in formatted

    def test_format_error_network(self):
        """Test formatting network errors."""
        collector = ErrorCollector()
        error = Exception("Connection timeout occurred")

        formatted = collector.format_error("/test/upload.txt", error)

        assert "Network error - check connection and try again" in formatted
        assert "upload.txt:" in formatted

    def test_format_error_fallback(self):
        """Test fallback formatting for unknown errors."""
        collector = ErrorCollector()
        error = Exception("Unknown error type")

        formatted = collector.format_error("/test/file.txt", error)

        assert formatted == "/test/file.txt: Unknown error type"

    def test_get_formatted_errors(self):
        """Test getting all formatted errors."""
        collector = ErrorCollector()

        # Add different types of errors
        collector.add_error("/test/file1.txt", ValueError("Error 1"))
        collector.add_error("/test/file2.txt", RuntimeError("Error 2"))

        formatted_errors = collector.get_formatted_errors()

        assert len(formatted_errors) == 2
        assert "/test/file1.txt: Error 1" in formatted_errors
        assert "/test/file2.txt: Error 2" in formatted_errors

    def test_get_formatted_errors_caching(self):
        """Test that formatted errors are cached."""
        collector = ErrorCollector()
        error = ValueError("Test error")

        collector.add_error("/test/file.txt", error)

        # First call should format the error
        formatted1 = collector.get_formatted_errors()

        # Second call should use cached result
        formatted2 = collector.get_formatted_errors()

        assert formatted1 == formatted2
        assert collector.errors[0]["formatted_message"] is not None

    def test_get_summary_empty(self):
        """Test getting summary with no errors."""
        collector = ErrorCollector()

        summary = collector.get_summary()

        assert summary["total"] == 0
        assert summary["by_type"] == {}
        assert summary["by_file"] == {}

    def test_get_summary_with_errors(self):
        """Test getting summary with multiple errors."""
        collector = ErrorCollector()

        # Add errors of different types
        collector.add_error("/test/file1.txt", ValueError("Error 1"))
        collector.add_error("/test/file2.txt", ValueError("Error 2"))
        collector.add_error("/test/file1.txt", RuntimeError("Error 3"))

        summary = collector.get_summary()

        assert summary["total"] == 3
        assert summary["by_type"]["ValueError"] == 2
        assert summary["by_type"]["RuntimeError"] == 1
        assert summary["by_file"]["/test/file1.txt"] == 2
        assert summary["by_file"]["/test/file2.txt"] == 1
        assert len(summary["formatted_errors"]) == 3

    def test_register_custom_formatter(self):
        """Test registering a custom error formatter."""
        collector = ErrorCollector()

        def custom_formatter(file_path: str, error: Exception) -> str:
            if "custom" in str(error):
                return f"CUSTOM: {Path(file_path).name} had a custom error"
            return f"{file_path}: {str(error)}"

        collector.register_formatter("custom", custom_formatter)

        # Test custom formatter is used
        error1 = Exception("This is a custom error")
        formatted1 = collector.format_error("/test/file.txt", error1)
        assert "CUSTOM: file.txt had a custom error" == formatted1

        # Test fallback still works
        error2 = Exception("Regular error")
        formatted2 = collector.format_error("/test/file.txt", error2)
        assert "/test/file.txt: Regular error" == formatted2

    def test_get_errors_for_file(self):
        """Test getting errors for a specific file."""
        collector = ErrorCollector()

        # Add errors for different files
        collector.add_error("/test/file1.txt", ValueError("Error 1"))
        collector.add_error("/test/file2.txt", RuntimeError("Error 2"))
        collector.add_error("/test/file1.txt", TypeError("Error 3"))

        file1_errors = collector.get_errors_for_file("/test/file1.txt")
        file2_errors = collector.get_errors_for_file("/test/file2.txt")
        file3_errors = collector.get_errors_for_file("/test/nonexistent.txt")

        assert len(file1_errors) == 2
        assert len(file2_errors) == 1
        assert len(file3_errors) == 0

        # Check error types
        assert file1_errors[0]["error_type"] == "ValueError"
        assert file1_errors[1]["error_type"] == "TypeError"
        assert file2_errors[0]["error_type"] == "RuntimeError"


class TestErrorCollectorIntegration:
    """Integration tests for ErrorCollector."""

    def test_realistic_file_upload_scenario(self):
        """Test ErrorCollector in a realistic file upload scenario."""
        collector = ErrorCollector()

        # Simulate various upload errors
        files_and_errors = [
            (
                "/docs/README",
                Exception(
                    "Files without extensions are not supported for file-search"
                ),
            ),
            (
                "/data/large.csv",
                Exception(
                    "Failed to add files to vector store: size limit exceeded"
                ),
            ),
            ("/private/secret.txt", PermissionError("Access denied")),
            (
                "/missing/file.txt",
                FileNotFoundError("No such file or directory"),
            ),
            (
                "/remote/data.json",
                Exception("Connection timeout occurred while uploading"),
            ),
        ]

        # Add all errors
        for file_path, error in files_and_errors:
            collector.add_error(file_path, error)

        # Verify error collection
        assert collector.get_error_count() == 5
        assert collector.has_errors()

        # Get formatted errors
        formatted_errors = collector.get_formatted_errors()
        assert len(formatted_errors) == 5

        # Verify specific formatting
        assert any(
            "Cannot use with file-search (no file extension)" in error
            for error in formatted_errors
        )
        assert any(
            "Upload succeeded but file-search binding failed" in error
            for error in formatted_errors
        )
        assert any(
            "Permission denied - check file access rights" in error
            for error in formatted_errors
        )
        assert any("File not found:" in error for error in formatted_errors)
        assert any(
            "Network error - check connection and try again" in error
            for error in formatted_errors
        )

        # Get summary
        summary = collector.get_summary()
        assert summary["total"] == 5
        assert summary["by_type"]["Exception"] == 3
        assert summary["by_type"]["PermissionError"] == 1
        assert summary["by_type"]["FileNotFoundError"] == 1

    def test_batch_processing_with_mixed_results(self):
        """Test ErrorCollector with mixed success/failure batch processing."""
        collector = ErrorCollector()

        # Simulate batch processing results
        files = [
            "/data/file1.txt",
            "/data/file2.txt",
            "/data/file3.txt",
            "/data/file4.txt",
        ]

        # Some succeed, some fail
        for i, file_path in enumerate(files):
            if i % 2 == 0:  # Even indices succeed (no error added)
                continue
            else:  # Odd indices fail
                error = Exception(f"Processing failed for item {i}")
                collector.add_error(file_path, error)

        # Should have 2 errors out of 4 files
        assert collector.get_error_count() == 2

        formatted_errors = collector.get_formatted_errors()
        assert len(formatted_errors) == 2
        assert any("file2.txt" in error for error in formatted_errors)
        assert any("file4.txt" in error for error in formatted_errors)
