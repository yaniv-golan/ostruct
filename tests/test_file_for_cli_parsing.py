"""Test --file-for CLI argument parsing specifically."""

from unittest.mock import Mock

import pytest

from ostruct.cli.explicit_file_processor import ExplicitFileProcessor


class TestFileForCLIParsing:
    """Test CLI parsing of --file-for arguments."""

    def test_file_for_argument_parsing(self):
        """Test that Click correctly parses --file-for arguments."""
        # This tests the core functionality we implemented
        processor = ExplicitFileProcessor(Mock())

        # Simulate what Click would pass to our processor
        # This is the format that Click produces with nargs=2, multiple=True
        args = {
            "tool_files": [
                ("template", "/path/to/config.yaml"),
                ("code-interpreter", "/path/to/data.csv"),
                ("file-search", "/path/to/docs.pdf"),
            ]
        }

        routing = processor._parse_file_routing_from_args(args)

        # Verify the parsing worked correctly
        assert "/path/to/config.yaml" in routing.template_files
        assert "/path/to/data.csv" in routing.code_interpreter_files
        assert "/path/to/docs.pdf" in routing.file_search_files

    def test_windows_path_compatibility(self):
        """Test that Windows paths work without colon conflicts."""
        processor = ExplicitFileProcessor(Mock())

        # Test the exact scenario that was problematic before
        args = {
            "tool_files": [
                ("template", "C:\\Users\\admin\\config.yaml"),
                ("code-interpreter", "D:\\data\\analysis.csv"),
                ("file-search", "C:\\Program Files\\docs\\manual.pdf"),
            ]
        }

        # This should not raise any parsing errors
        routing = processor._parse_file_routing_from_args(args)

        # Verify Windows paths are preserved correctly
        assert "C:\\Users\\admin\\config.yaml" in routing.template_files
        assert "D:\\data\\analysis.csv" in routing.code_interpreter_files
        assert (
            "C:\\Program Files\\docs\\manual.pdf" in routing.file_search_files
        )

    def test_old_syntax_would_have_failed(self):
        """Demonstrate that the old syntax would have been problematic."""
        # This test shows why we needed to change the syntax

        # Old problematic format (colon-based) would have been:
        # "code-interpreter,file-search:C:\\Users\\data.csv"

        # The old format would have been parsed as:
        # tools = ["code-interpreter", "file-search"]
        # file = "C" (everything before first colon)
        # remaining = "\\Users\\data.csv" (everything after first colon)

        # This would have failed on Windows because the drive letter C:
        # would be interpreted as the tool/file separator

        # With our new format, this is not an issue:
        processor = ExplicitFileProcessor(Mock())
        args = {
            "tool_files": [
                ("code-interpreter", "C:\\Users\\data.csv"),
                ("file-search", "C:\\Users\\data.csv"),
            ]
        }

        # No parsing issues - each tool and path is separate
        routing = processor._parse_file_routing_from_args(args)
        assert "C:\\Users\\data.csv" in routing.code_interpreter_files
        assert "C:\\Users\\data.csv" in routing.file_search_files

    def test_multiple_files_same_tool(self):
        """Test routing multiple files to the same tool."""
        processor = ExplicitFileProcessor(Mock())

        args = {
            "tool_files": [
                ("template", "/config/app.yaml"),
                ("template", "/config/db.yaml"),
                ("template", "/config/cache.yaml"),
                ("code-interpreter", "/data/input.csv"),
                ("code-interpreter", "/scripts/analysis.py"),
            ]
        }

        routing = processor._parse_file_routing_from_args(args)

        # All template files should be collected
        assert len(routing.template_files) == 3
        assert "/config/app.yaml" in routing.template_files
        assert "/config/db.yaml" in routing.template_files
        assert "/config/cache.yaml" in routing.template_files

        # All code-interpreter files should be collected
        assert len(routing.code_interpreter_files) == 2
        assert "/data/input.csv" in routing.code_interpreter_files
        assert "/scripts/analysis.py" in routing.code_interpreter_files

    def test_invalid_tool_names(self):
        """Test validation of tool names."""
        processor = ExplicitFileProcessor(Mock())

        # Valid tools should work
        valid_args = {
            "tool_files": [
                ("template", "/test.txt"),
                ("code-interpreter", "/test.txt"),
                ("file-search", "/test.txt"),
            ]
        }
        routing = processor._parse_file_routing_from_args(valid_args)
        assert routing is not None

        # Invalid tool should raise ValueError
        invalid_args = {
            "tool_files": [
                ("invalid-tool", "/test.txt"),
            ]
        }

        with pytest.raises(ValueError) as exc_info:
            processor._parse_file_routing_from_args(invalid_args)

        assert "Invalid tool 'invalid-tool'" in str(exc_info.value)
        assert "Valid tools:" in str(exc_info.value)
        assert "code-interpreter" in str(exc_info.value)
        assert "file-search" in str(exc_info.value)
        assert "template" in str(exc_info.value)

    def test_empty_tool_files(self):
        """Test handling empty tool_files list."""
        processor = ExplicitFileProcessor(Mock())

        args = {"tool_files": []}
        routing = processor._parse_file_routing_from_args(args)

        # Should create empty routing without errors
        assert len(routing.template_files) == 0
        assert len(routing.code_interpreter_files) == 0
        assert len(routing.file_search_files) == 0

    def test_mixed_with_other_options(self):
        """Test --file-for mixed with other routing options."""
        processor = ExplicitFileProcessor(Mock())

        # Mix --file-for with -ft, -fc, -fs options
        args = {
            "tool_files": [
                ("template", "/explicit/config.yaml"),
                ("code-interpreter", "/explicit/data.csv"),
            ],
            "template_files": [("name", "/other/template.txt")],
            "code_interpreter_files": [("data", "/other/code.py")],
            "file_search_files": [("docs", "/other/search.pdf")],
        }

        routing = processor._parse_file_routing_from_args(args)

        # All files should be collected
        assert "/explicit/config.yaml" in routing.template_files
        assert "/other/template.txt" in routing.template_files
        assert "/explicit/data.csv" in routing.code_interpreter_files
        assert "/other/code.py" in routing.code_interpreter_files
        assert "/other/search.pdf" in routing.file_search_files
