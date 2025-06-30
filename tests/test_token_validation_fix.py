"""Tests for token validation fix - ensuring tool files are not double-counted."""

from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from ostruct.cli.file_info import FileRoutingIntent
from ostruct.cli.model_validation import validate_model_and_schema
from ostruct.cli.security import SecurityManager
from ostruct.cli.types import CLIParams


class TestTokenValidationFix:
    """Test suite for the token validation fix."""

    @pytest.fixture
    def mock_security_manager(self) -> SecurityManager:
        """Create a mock security manager."""
        mock_sm = Mock(spec=SecurityManager)
        mock_sm.base_dir = "/test/base"
        mock_sm.resolve_path.return_value = Mock()
        mock_sm.resolve_path.return_value.is_file.return_value = True
        return mock_sm

    @pytest.fixture
    def sample_cli_args(self) -> CLIParams:
        """Create sample CLI arguments."""
        return {
            "model": "gpt-4o",
            "temperature": None,
            "max_output_tokens": None,
            "top_p": None,
            "frequency_penalty": None,
            "presence_penalty": None,
            "reasoning_effort": None,
            "show_model_schema": False,
            "debug_validation": False,
        }

    @pytest.fixture
    def sample_schema(self) -> Dict[str, Any]:
        """Create a sample schema."""
        return {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        }

    def create_mock_file_info(
        self, path: str, routing_intent: FileRoutingIntent
    ) -> Mock:
        """Helper to create mock FileInfo with routing intent."""
        mock_file = Mock()
        mock_file.path = path
        mock_file.routing_intent = routing_intent
        return mock_file

    @pytest.mark.asyncio
    @patch("ostruct.cli.model_validation.validate_token_limits")
    @patch("ostruct.cli.model_validation.create_dynamic_model")
    @patch("ostruct.cli.model_validation.supports_structured_output")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    async def test_template_only_files_counted(
        self,
        mock_registry,
        mock_supports_structured,
        mock_create_model,
        mock_validate_token_limits,
        mock_security_manager,
        sample_cli_args,
        sample_schema,
    ):
        """Files with TEMPLATE_ONLY routing should be counted in validation."""
        # Setup mocks
        mock_supports_structured.return_value = True
        mock_create_model.return_value = Mock()
        mock_registry.get_instance.return_value = Mock()

        # Create template files
        template_file1 = self.create_mock_file_info(
            "template1.txt",
            FileRoutingIntent.TEMPLATE_ONLY,
        )
        template_file2 = self.create_mock_file_info(
            "template2.txt",
            FileRoutingIntent.TEMPLATE_ONLY,
        )

        template_context = {"files": [template_file1, template_file2]}

        # Call the function
        await validate_model_and_schema(
            sample_cli_args,
            sample_schema,
            "System prompt",
            "User prompt",
            template_context,
        )

        # Verify validate_token_limits was called with both template files
        mock_validate_token_limits.assert_called_once()
        call_args = mock_validate_token_limits.call_args

        combined_content = call_args[0][0]
        file_paths = call_args[0][1]
        model = call_args[0][2]

        assert combined_content == "System promptUser prompt"
        assert len(file_paths) == 2
        assert "template1.txt" in file_paths
        assert "template2.txt" in file_paths
        assert model == "gpt-4o"

    @pytest.mark.asyncio
    @patch("ostruct.cli.model_validation.validate_token_limits")
    @patch("ostruct.cli.model_validation.create_dynamic_model")
    @patch("ostruct.cli.model_validation.supports_structured_output")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    async def test_tool_files_not_counted(
        self,
        mock_registry,
        mock_supports_structured,
        mock_create_model,
        mock_validate_token_limits,
        mock_security_manager,
        sample_cli_args,
        sample_schema,
    ):
        """Files with FILE_SEARCH/CODE_INTERPRETER routing should not be counted."""
        # Setup mocks
        mock_supports_structured.return_value = True
        mock_create_model.return_value = Mock()
        mock_registry.get_instance.return_value = Mock()

        # Create tool files
        fs_file = self.create_mock_file_info(
            "search_doc.pdf",
            FileRoutingIntent.FILE_SEARCH,
        )
        ci_file = self.create_mock_file_info(
            "data.csv",
            FileRoutingIntent.CODE_INTERPRETER,
        )

        template_context = {"files": [fs_file, ci_file]}

        # Call the function
        await validate_model_and_schema(
            sample_cli_args,
            sample_schema,
            "System prompt",
            "User prompt",
            template_context,
        )

        # Verify validate_token_limits was called with empty file list
        mock_validate_token_limits.assert_called_once()
        call_args = mock_validate_token_limits.call_args

        combined_content = call_args[0][0]
        file_paths = call_args[0][1]
        model = call_args[0][2]

        assert combined_content == "System promptUser prompt"
        assert len(file_paths) == 0  # No tool files should be counted
        assert model == "gpt-4o"

    @pytest.mark.asyncio
    @patch("ostruct.cli.model_validation.validate_token_limits")
    @patch("ostruct.cli.model_validation.create_dynamic_model")
    @patch("ostruct.cli.model_validation.supports_structured_output")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    async def test_mixed_routing_scenarios(
        self,
        mock_registry,
        mock_supports_structured,
        mock_create_model,
        mock_validate_token_limits,
        mock_security_manager,
        sample_cli_args,
        sample_schema,
    ):
        """Mixed routing scenarios should count only template files."""
        # Setup mocks
        mock_supports_structured.return_value = True
        mock_create_model.return_value = Mock()
        mock_registry.get_instance.return_value = Mock()

        # Create mixed files
        template_file = self.create_mock_file_info(
            "prompt.txt",
            FileRoutingIntent.TEMPLATE_ONLY,
        )
        fs_file = self.create_mock_file_info(
            "large_doc.pdf",
            FileRoutingIntent.FILE_SEARCH,
        )
        ci_file = self.create_mock_file_info(
            "analysis_data.csv",
            FileRoutingIntent.CODE_INTERPRETER,
        )

        template_context = {"files": [template_file, fs_file, ci_file]}

        # Call the function
        await validate_model_and_schema(
            sample_cli_args,
            sample_schema,
            "System prompt",
            "User prompt",
            template_context,
        )

        # Verify validate_token_limits was called with only template file
        mock_validate_token_limits.assert_called_once()
        call_args = mock_validate_token_limits.call_args

        combined_content = call_args[0][0]
        file_paths = call_args[0][1]
        model = call_args[0][2]

        assert combined_content == "System promptUser prompt"
        assert len(file_paths) == 1
        assert "prompt.txt" in file_paths
        # Tool files should not be included
        assert not any("large_doc.pdf" in path for path in file_paths)
        assert not any("analysis_data.csv" in path for path in file_paths)
        assert model == "gpt-4o"

    @pytest.mark.asyncio
    @patch("ostruct.cli.model_validation.validate_token_limits")
    @patch("ostruct.cli.model_validation.create_dynamic_model")
    @patch("ostruct.cli.model_validation.supports_structured_output")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    async def test_backward_compatibility(
        self,
        mock_registry,
        mock_supports_structured,
        mock_create_model,
        mock_validate_token_limits,
        mock_security_manager,
        sample_cli_args,
        sample_schema,
    ):
        """Existing template-only workflows should work unchanged."""
        # Setup mocks
        mock_supports_structured.return_value = True
        mock_create_model.return_value = Mock()
        mock_registry.get_instance.return_value = Mock()

        # Create mock file without routing_intent (backward compatibility)
        old_style_file = Mock()
        old_style_file.path = "legacy_file.txt"
        old_style_file.routing_intent = None

        template_context = {"files": [old_style_file]}

        # Call the function
        await validate_model_and_schema(
            sample_cli_args,
            sample_schema,
            "System prompt",
            "User prompt",
            template_context,
        )

        # Verify validate_token_limits was called with empty file list
        # (since routing_intent is None, it doesn't match TEMPLATE_ONLY)
        mock_validate_token_limits.assert_called_once()
        call_args = mock_validate_token_limits.call_args

        combined_content = call_args[0][0]
        file_paths = call_args[0][1]
        model = call_args[0][2]

        assert combined_content == "System promptUser prompt"
        assert len(file_paths) == 0  # No routing_intent means not counted
        assert model == "gpt-4o"

    @pytest.mark.asyncio
    @patch("ostruct.cli.model_validation.validate_token_limits")
    @patch("ostruct.cli.model_validation.create_dynamic_model")
    @patch("ostruct.cli.model_validation.supports_structured_output")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    async def test_empty_files_list(
        self,
        mock_registry,
        mock_supports_structured,
        mock_create_model,
        mock_validate_token_limits,
        sample_cli_args,
        sample_schema,
    ):
        """Empty files list should work correctly."""
        # Setup mocks
        mock_supports_structured.return_value = True
        mock_create_model.return_value = Mock()
        mock_registry.get_instance.return_value = Mock()

        template_context = {"files": []}

        # Call the function
        await validate_model_and_schema(
            sample_cli_args,
            sample_schema,
            "System prompt",
            "User prompt",
            template_context,
        )

        # Verify validate_token_limits was called with empty file list
        mock_validate_token_limits.assert_called_once()
        call_args = mock_validate_token_limits.call_args

        combined_content = call_args[0][0]
        file_paths = call_args[0][1]
        model = call_args[0][2]

        assert combined_content == "System promptUser prompt"
        assert len(file_paths) == 0
        assert model == "gpt-4o"

    @pytest.mark.asyncio
    @patch("ostruct.cli.model_validation.validate_token_limits")
    @patch("ostruct.cli.model_validation.create_dynamic_model")
    @patch("ostruct.cli.model_validation.supports_structured_output")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    async def test_missing_files_key(
        self,
        mock_registry,
        mock_supports_structured,
        mock_create_model,
        mock_validate_token_limits,
        sample_cli_args,
        sample_schema,
    ):
        """Missing 'files' key in template_context should work correctly."""
        # Setup mocks
        mock_supports_structured.return_value = True
        mock_create_model.return_value = Mock()
        mock_registry.get_instance.return_value = Mock()

        template_context = {}  # No 'files' key

        # Call the function
        await validate_model_and_schema(
            sample_cli_args,
            sample_schema,
            "System prompt",
            "User prompt",
            template_context,
        )

        # Verify validate_token_limits was called with empty file list
        mock_validate_token_limits.assert_called_once()
        call_args = mock_validate_token_limits.call_args

        combined_content = call_args[0][0]
        file_paths = call_args[0][1]
        model = call_args[0][2]

        assert combined_content == "System promptUser prompt"
        assert len(file_paths) == 0
        assert model == "gpt-4o"
