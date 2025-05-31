"""Tests for explicit file routing functionality."""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ostruct.cli.explicit_file_processor import (
    ExplicitFileProcessor,
    ExplicitRouting,
    ProcessingResult,
)


class TestExplicitFileProcessor:
    """Test explicit file routing and processing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.security_manager = Mock()
        self.processor = ExplicitFileProcessor(self.security_manager)

    def test_initialization(self):
        """Test processor initialization."""
        assert self.processor.security_manager == self.security_manager
        assert hasattr(self.processor, "_parse_file_routing_from_args")

    def test_tool_files_parsing(self):
        """Test that tool_files parameter is parsed correctly."""
        # Test the new --file-for syntax
        args = {
            "tool_files": [
                ("template", "/test/config.yaml"),
                ("code-interpreter", "/test/analysis.py"),
                ("file-search", "/test/docs.pdf"),
            ]
        }

        routing = self.processor._parse_file_routing_from_args(args)

        assert "/test/config.yaml" in routing.template_files
        assert "/test/analysis.py" in routing.code_interpreter_files
        assert "/test/docs.pdf" in routing.file_search_files

    def test_invalid_tool_validation(self):
        """Test validation of invalid tool names."""
        args = {
            "tool_files": [
                ("invalid-tool", "/test/file.txt"),
            ]
        }

        with pytest.raises(ValueError) as exc_info:
            self.processor._parse_file_routing_from_args(args)

        assert "Invalid tool 'invalid-tool'" in str(exc_info.value)
        assert "Valid tools:" in str(exc_info.value)

    def test_valid_tool_names(self):
        """Test that all valid tool names are accepted."""
        valid_tools = ["template", "code-interpreter", "file-search"]

        for tool in valid_tools:
            args: Dict[str, Any] = {
                "tool_files": [
                    (tool, "/test/file.txt"),
                ]
            }

            # Should not raise an exception
            routing = self.processor._parse_file_routing_from_args(args)
            assert routing is not None

    def test_multiple_files_same_tool(self):
        """Test routing multiple files to the same tool."""
        args = {
            "tool_files": [
                ("template", "/test/config1.yaml"),
                ("template", "/test/config2.yaml"),
                ("code-interpreter", "/test/data.csv"),
            ]
        }

        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.template_files) == 2
        assert "/test/config1.yaml" in routing.template_files
        assert "/test/config2.yaml" in routing.template_files
        assert len(routing.code_interpreter_files) == 1
        assert "/test/data.csv" in routing.code_interpreter_files

    def test_empty_tool_files(self):
        """Test handling of empty tool_files list."""
        args: Dict[str, Any] = {"tool_files": []}

        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.template_files) == 0
        assert len(routing.code_interpreter_files) == 0
        assert len(routing.file_search_files) == 0

    def test_mixed_routing_options(self):
        """Test mixing --file-for with other routing options."""
        args = {
            "tool_files": [
                ("template", "/test/config.yaml"),
            ],
            "template_file_aliases": [("custom_name", "/test/other.yaml")],
            "code_interpreter_file_aliases": [("data", "/test/data.csv")],
        }

        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.template_files) == 2
        assert "/test/config.yaml" in routing.template_files
        assert "/test/other.yaml" in routing.template_files
        assert "/test/data.csv" in routing.code_interpreter_files

    @pytest.mark.asyncio
    async def test_process_file_routing_basic(self):
        """Test basic file routing processing."""
        args: Dict[str, Any] = {
            "tool_files": [
                ("template", "/test/config.yaml"),
                ("code-interpreter", "/test/data.csv"),
            ]
        }

        # Mock the validation methods
        with patch.object(
            self.processor,
            "_validate_routing_security",
            new_callable=AsyncMock,
        ) as mock_validate:
            mock_validate.return_value = ExplicitRouting(
                template_files=["/test/config.yaml"],
                code_interpreter_files=["/test/data.csv"],
            )

            result = await self.processor.process_file_routing(args)

            assert isinstance(result, ProcessingResult)
            assert len(result.enabled_tools) > 0
            assert "code-interpreter" in result.enabled_tools

    def test_routing_summary(self):
        """Test routing summary generation."""
        routing = ExplicitRouting(
            template_files=["/test/config.yaml"],
            code_interpreter_files=["/test/data.csv", "/test/script.py"],
            file_search_files=["/test/docs.pdf"],
        )

        enabled_tools = {"template", "code-interpreter", "file-search"}
        validated_files = {
            "template": ["/test/config.yaml"],
            "code-interpreter": ["/test/data.csv", "/test/script.py"],
            "file-search": ["/test/docs.pdf"],
        }

        result = ProcessingResult(
            routing=routing,
            enabled_tools=enabled_tools,
            validated_files=validated_files,
        )

        summary = self.processor.get_routing_summary(result)

        assert summary["total_files"] == 4
        assert len(summary["enabled_tools"]) == 3
        assert "template" in summary["enabled_tools"]
        assert "code-interpreter" in summary["enabled_tools"]
        assert "file-search" in summary["enabled_tools"]
        assert summary["file_counts"]["template"] == 1
        assert summary["file_counts"]["code_interpreter"] == 2
        assert summary["file_counts"]["file_search"] == 1


class TestFileRoutingIntegration:
    """Test integration of file routing with CLI."""

    def test_cli_integration_basic(self):
        """Test basic CLI integration."""
        processor = ExplicitFileProcessor(Mock())

        # Test that processor can be instantiated and has required methods
        assert hasattr(processor, "process_file_routing")
        assert hasattr(processor, "_parse_file_routing_from_args")

    def test_routing_validation_consistency(self):
        """Test routing validation for consistency."""
        processor = ExplicitFileProcessor(Mock())

        # Test valid routing
        routing = ExplicitRouting(
            template_files=["/test/config.yaml"],
            code_interpreter_files=["/test/data.csv"],
        )

        issues = processor.validate_routing_consistency(routing)
        assert isinstance(issues, list)

    def test_windows_path_compatibility(self):
        """Test that Windows paths work correctly with new syntax."""
        processor = ExplicitFileProcessor(Mock())

        # Test Windows-style paths
        args = {
            "tool_files": [
                ("template", "C:\\Users\\test\\config.yaml"),
                ("code-interpreter", "D:\\data\\analysis.csv"),
            ]
        }

        # Should parse without errors
        routing = processor._parse_file_routing_from_args(args)

        assert "C:\\Users\\test\\config.yaml" in routing.template_files
        assert "D:\\data\\analysis.csv" in routing.code_interpreter_files


class TestFileRoutingPerformance:
    """Test performance aspects of file routing."""

    def test_large_file_list_processing(self):
        """Test processing of large file lists."""
        processor = ExplicitFileProcessor(Mock())

        # Create a large list of files
        large_file_list = [
            ("template", f"/test/file_{i}.py") for i in range(100)
        ]

        args = {"tool_files": large_file_list}

        # Should handle large file lists efficiently
        routing = processor._parse_file_routing_from_args(args)
        assert len(routing.template_files) == 100

    def test_mixed_tool_performance(self):
        """Test performance with files distributed across tools."""
        processor = ExplicitFileProcessor(Mock())

        # Mix files across different tools
        tool_files = []
        tools = ["template", "code-interpreter", "file-search"]
        for i in range(50):
            tool = tools[i % len(tools)]
            tool_files.append((tool, f"/test/file_{i}.txt"))

        args = {"tool_files": tool_files}

        routing = processor._parse_file_routing_from_args(args)

        # Verify distribution
        total_files = (
            len(routing.template_files)
            + len(routing.code_interpreter_files)
            + len(routing.file_search_files)
        )
        assert total_files == 50
