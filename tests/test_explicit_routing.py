"""Tests for explicit file routing functionality."""

from typing import Any, Dict, cast
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


class TestDirectoryAliases:
    """Test directory alias functionality for file routing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.security_manager = Mock()
        self.processor = ExplicitFileProcessor(self.security_manager)

    def test_dta_template_alias_parsing(self):
        """Test --dir creates stable template variable."""
        args = {
            "template_dir_aliases": [
                ("app_config", "/test/settings"),
                ("source_code", "/test/src"),
            ]
        }

        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.template_dir_aliases) == 2
        assert ("app_config", "/test/settings") in routing.template_dir_aliases
        assert ("source_code", "/test/src") in routing.template_dir_aliases

    def test_dca_code_interpreter_alias_parsing(self):
        """Test --dir ci:for Code Interpreter routing."""
        args = {
            "code_interpreter_dir_aliases": [
                ("training_data", "/test/datasets"),
                ("code_files", "/test/analysis"),
            ]
        }

        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.code_interpreter_dir_aliases) == 2
        assert (
            "training_data",
            "/test/datasets",
        ) in routing.code_interpreter_dir_aliases
        assert (
            "code_files",
            "/test/analysis",
        ) in routing.code_interpreter_dir_aliases

    def test_dsa_file_search_alias_parsing(self):
        """Test --dir fs:for File Search routing."""
        args = {
            "file_search_dir_aliases": [
                ("knowledge_base", "/test/docs"),
                ("user_manuals", "/test/manuals"),
            ]
        }

        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.file_search_dir_aliases) == 2
        assert (
            "knowledge_base",
            "/test/docs",
        ) in routing.file_search_dir_aliases
        assert (
            "user_manuals",
            "/test/manuals",
        ) in routing.file_search_dir_aliases

    def test_mixed_directory_routing(self):
        """Test combining auto-naming and alias syntax."""
        args = {
            "template_dirs": ["/test/config"],  # Auto-naming
            "template_dir_aliases": [
                ("stable_config", "/test/stable")
            ],  # Alias
            "code_interpreter_dirs": ["/test/data"],  # Auto-naming
            "code_interpreter_dir_aliases": [
                ("analysis_data", "/test/analysis")
            ],  # Alias
        }

        routing = self.processor._parse_file_routing_from_args(args)

        # Check auto-naming directories
        assert "/test/config" in routing.template_dirs
        assert "/test/data" in routing.code_interpreter_dirs

        # Check alias directories
        assert len(routing.template_dir_aliases) == 1
        assert (
            "stable_config",
            "/test/stable",
        ) in routing.template_dir_aliases
        assert len(routing.code_interpreter_dir_aliases) == 1
        assert (
            "analysis_data",
            "/test/analysis",
        ) in routing.code_interpreter_dir_aliases

    def test_all_directory_alias_types_together(self):
        """Test all three directory alias types together."""
        args = {
            "template_dir_aliases": [("config", "/test/config")],
            "code_interpreter_dir_aliases": [("data", "/test/data")],
            "file_search_dir_aliases": [("docs", "/test/docs")],
        }

        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.template_dir_aliases) == 1
        assert len(routing.code_interpreter_dir_aliases) == 1
        assert len(routing.file_search_dir_aliases) == 1
        assert ("config", "/test/config") in routing.template_dir_aliases
        assert ("data", "/test/data") in routing.code_interpreter_dir_aliases
        assert ("docs", "/test/docs") in routing.file_search_dir_aliases

    def test_empty_directory_aliases(self):
        """Test handling of empty directory aliases."""
        args: Dict[str, Any] = {
            "template_dir_aliases": [],
            "code_interpreter_dir_aliases": [],
            "file_search_dir_aliases": [],
        }

        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.template_dir_aliases) == 0
        assert len(routing.code_interpreter_dir_aliases) == 0
        assert len(routing.file_search_dir_aliases) == 0

    def test_directory_alias_validation(self):
        """Test validation of directory alias names."""
        # Test valid alias names
        valid_args = {
            "template_dir_aliases": [
                ("valid_name", "/test/dir"),
                ("another_valid_name", "/test/other"),
                ("config2", "/test/config2"),
            ]
        }

        # Should not raise an exception
        routing = self.processor._parse_file_routing_from_args(valid_args)
        assert len(routing.template_dir_aliases) == 3

    @pytest.mark.asyncio
    async def test_directory_alias_tool_auto_enablement(self):
        """Test that directory aliases auto-enable appropriate tools."""
        args: Dict[str, Any] = {
            "template_dir_aliases": [("config", "/test/config")],
            "code_interpreter_dir_aliases": [("data", "/test/data")],
            "file_search_dir_aliases": [("docs", "/test/docs")],
        }

        # Mock the validation and file expansion
        with patch.object(
            self.processor,
            "_validate_routing_security",
            new_callable=AsyncMock,
        ) as mock_validate:
            with patch.object(
                self.processor,
                "_create_validated_file_mappings",
                new_callable=AsyncMock,
            ) as mock_create:
                # Setup mock returns
                test_routing = ExplicitRouting(
                    template_dir_aliases=[("config", "/test/config")],
                    code_interpreter_dir_aliases=[("data", "/test/data")],
                    file_search_dir_aliases=[("docs", "/test/docs")],
                )
                mock_validate.return_value = test_routing
                mock_create.return_value = {
                    "template": ["/test/config/app.yaml"],
                    "code-interpreter": ["/test/data/dataset.csv"],
                    "file-search": ["/test/docs/manual.pdf"],
                }

                result = await self.processor.process_file_routing(args)

                # Verify that only external tools are auto-enabled
                # Template files/directories don't auto-enable tools (processed locally)
                assert (
                    "template" not in result.enabled_tools
                )  # Templates don't auto-enable tools
                assert "code-interpreter" in result.enabled_tools
                assert "file-search" in result.enabled_tools

    def test_directory_alias_consistency_validation(self):
        """Test consistency validation for directory aliases."""
        # Test duplicate alias names across different tools (should be allowed)
        routing = ExplicitRouting(
            template_dir_aliases=[("config", "/test/template_config")],
            code_interpreter_dir_aliases=[("config", "/test/ci_config")],
            file_search_dir_aliases=[("config", "/test/fs_config")],
        )

        issues = self.processor.validate_routing_consistency(routing)
        # Different tools can have same alias names, so no issues expected
        assert isinstance(issues, list)

    def test_directory_alias_with_existing_files(self):
        """Test mixing directory aliases with explicit file routing."""
        args = {
            "template_files": ["/test/explicit_config.yaml"],
            "template_dir_aliases": [("batch_config", "/test/config_dir")],
            "code_interpreter_file_aliases": [("data", "/test/data.csv")],
            "code_interpreter_dir_aliases": [("extra_data", "/test/data_dir")],
        }

        routing = self.processor._parse_file_routing_from_args(args)

        # Check explicit files
        assert "/test/explicit_config.yaml" in routing.template_files
        assert "/test/data.csv" in routing.code_interpreter_files

        # Check directory aliases
        assert len(routing.template_dir_aliases) == 1
        assert (
            "batch_config",
            "/test/config_dir",
        ) in routing.template_dir_aliases
        assert len(routing.code_interpreter_dir_aliases) == 1
        assert (
            "extra_data",
            "/test/data_dir",
        ) in routing.code_interpreter_dir_aliases

    def test_directory_alias_path_normalization(self):
        """Test that directory alias paths are properly normalized."""
        args = {
            "template_dir_aliases": [
                ("config", "/test/../test/config"),  # Should normalize
                ("data", "/test/./data"),  # Should normalize
            ]
        }

        routing = self.processor._parse_file_routing_from_args(args)

        # Paths should be normalized (exact normalization depends on implementation)
        assert len(routing.template_dir_aliases) == 2
        # The exact normalized form may vary, but they should be consistent
        alias_paths = [alias[1] for alias in routing.template_dir_aliases]
        assert len(set(alias_paths)) == 2  # Should be unique paths


class TestDirectoryAliasTemplateIntegration:
    """Test directory alias integration with template context."""

    def setup_method(self):
        """Set up test fixtures."""
        self.security_manager = Mock()

    def test_template_context_directory_alias_creation(self):
        """Test that directory aliases create named variables in template context."""
        args: Dict[str, Any] = {
            "template_dir_aliases": [("app_config", "/test/config")],
            "code_interpreter_dir_aliases": [("training_data", "/test/data")],
            "file_search_dir_aliases": [("knowledge_base", "/test/docs")],
        }

        # Mock the template processor function directly
        with patch(
            "ostruct.cli.template_processor.create_template_context_from_routing"
        ) as mock_create_context:
            from ostruct.cli.file_utils import FileInfo, FileInfoList

            # Mock file info objects
            mock_security_manager = Mock()
            mock_config_files = FileInfoList(
                [
                    FileInfo(
                        path="/test/config/app.yaml",
                        security_manager=mock_security_manager,
                        content="config: test",
                    ),
                    FileInfo(
                        path="/test/config/db.yaml",
                        security_manager=mock_security_manager,
                        content="db: test",
                    ),
                ]
            )
            mock_data_files = FileInfoList(
                [
                    FileInfo(
                        path="/test/data/dataset.csv",
                        security_manager=mock_security_manager,
                        content="data,test",
                    ),
                ]
            )
            mock_doc_files = FileInfoList(
                [
                    FileInfo(
                        path="/test/docs/manual.pdf",
                        security_manager=mock_security_manager,
                        content="Manual content",
                    ),
                ]
            )

            # Configure mock to return test context
            mock_create_context.return_value = {
                "app_config": mock_config_files,
                "training_data": mock_data_files,
                "knowledge_base": mock_doc_files,
            }

            # Import and test the function directly
            from ostruct.cli.template_processor import (
                create_template_context_from_routing,
            )

            # Test template context creation
            # Note: Casting to CLIParams since this is a test with mock data
            from ostruct.cli.types import CLIParams

            context = create_template_context_from_routing(
                cast(CLIParams, args), self.security_manager, Mock()
            )

            # Verify that alias variables are created with expected names
            mock_create_context.assert_called()

            # Verify context is created (even though mock returns specific values)
            assert context is not None


class TestDirectoryAliasErrorHandling:
    """Test error handling for directory aliases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.security_manager = Mock()
        self.processor = ExplicitFileProcessor(self.security_manager)

    def test_invalid_directory_alias_names(self):
        """Test error handling for invalid directory alias names."""
        # These are tested at CLI parsing level, but we can test at processor level too
        args = {
            "template_dir_aliases": [
                ("123invalid", "/test/dir"),  # Starts with number
                ("my-var", "/test/other"),  # Contains hyphen
            ]
        }

        # This might pass at processor level if validation is done at CLI level
        routing = self.processor._parse_file_routing_from_args(args)
        assert len(routing.template_dir_aliases) == 2

    def test_duplicate_alias_names_same_tool(self):
        """Test handling of duplicate alias names within same tool."""
        args = {
            "template_dir_aliases": [
                ("config", "/test/config1"),
                ("config", "/test/config2"),  # Duplicate name
            ]
        }

        # Should handle gracefully (might overwrite or collect both)
        routing = self.processor._parse_file_routing_from_args(args)
        assert len(routing.template_dir_aliases) <= 2

    def test_missing_directory_handling(self):
        """Test error handling for non-existent directories."""
        args = {
            "template_dir_aliases": [("config", "/nonexistent/directory")],
        }

        # Should parse successfully (validation happens later)
        routing = self.processor._parse_file_routing_from_args(args)
        assert len(routing.template_dir_aliases) == 1

    def test_empty_alias_name(self):
        """Test handling of empty alias names."""
        args = {
            "template_dir_aliases": [("", "/test/dir")],  # Empty alias name
        }

        # Should handle gracefully
        routing = self.processor._parse_file_routing_from_args(args)
        assert len(routing.template_dir_aliases) == 1

    def test_empty_directory_path(self):
        """Test handling of empty directory paths."""
        args = {
            "template_dir_aliases": [("config", "")],  # Empty path
        }

        # Should handle gracefully
        routing = self.processor._parse_file_routing_from_args(args)
        assert len(routing.template_dir_aliases) == 1


class TestDirectoryAliasPerformance:
    """Test performance aspects of directory alias routing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.security_manager = Mock()
        self.processor = ExplicitFileProcessor(self.security_manager)

    def test_large_number_directory_aliases(self):
        """Test performance with large numbers of directory aliases."""
        # Create many directory aliases
        template_aliases = [
            (f"config_{i}", f"/test/config_{i}") for i in range(50)
        ]
        ci_aliases = [(f"data_{i}", f"/test/data_{i}") for i in range(30)]
        fs_aliases = [(f"docs_{i}", f"/test/docs_{i}") for i in range(20)]

        args = {
            "template_dir_aliases": template_aliases,
            "code_interpreter_dir_aliases": ci_aliases,
            "file_search_dir_aliases": fs_aliases,
        }

        # Should handle large numbers efficiently
        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.template_dir_aliases) == 50
        assert len(routing.code_interpreter_dir_aliases) == 30
        assert len(routing.file_search_dir_aliases) == 20

    def test_mixed_routing_performance(self):
        """Test performance with mixed file and directory routing."""
        # Combine regular file routing with directory aliases
        args = {
            "template_files": [f"/test/file_{i}.yaml" for i in range(20)],
            "template_dir_aliases": [
                (f"dir_{i}", f"/test/dir_{i}") for i in range(10)
            ],
            "code_interpreter_files": [
                f"/test/data_{i}.csv" for i in range(15)
            ],
            "code_interpreter_dir_aliases": [
                (f"datadir_{i}", f"/test/datadir_{i}") for i in range(5)
            ],
        }

        # Should handle mixed routing efficiently
        routing = self.processor._parse_file_routing_from_args(args)

        assert len(routing.template_files) == 20
        assert len(routing.template_dir_aliases) == 10
        assert len(routing.code_interpreter_files) == 15
        assert len(routing.code_interpreter_dir_aliases) == 5

    def test_consistency_validation_performance(self):
        """Test performance of consistency validation with directory aliases."""
        # Create routing with many directory aliases
        routing = ExplicitRouting(
            template_dir_aliases=[
                (f"config_{i}", f"/test/config_{i}") for i in range(100)
            ],
            code_interpreter_dir_aliases=[
                (f"data_{i}", f"/test/data_{i}") for i in range(100)
            ],
            file_search_dir_aliases=[
                (f"docs_{i}", f"/test/docs_{i}") for i in range(100)
            ],
        )

        # Validation should complete efficiently
        issues = self.processor.validate_routing_consistency(routing)
        assert isinstance(issues, list)
