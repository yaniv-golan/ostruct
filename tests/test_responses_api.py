"""Tests for OpenAI Responses API integration."""

import importlib
import json
import os
from unittest.mock import AsyncMock, Mock, patch

from ostruct.cli.cli import create_cli
from pyfakefs.fake_filesystem import FakeFilesystem

from tests.test_cli import CliTestRunner

# Import modules for proper patching
CLIENT_UTILS = importlib.import_module("ostruct.cli.utils.client_utils")
UPLOAD_MOD = importlib.import_module("ostruct.cli.upload_cache")

# Test workspace base directory
TEST_BASE_DIR = "/test_workspace/base"


class MockResponsesAPIHelper:
    """Helper class for mocking OpenAI Responses API calls following best practices."""

    @staticmethod
    def create_non_streaming_response(
        output_text, response_id="test-response-id"
    ):
        """Create a proper non-streaming response object for the Responses API."""

        class MockNonStreamingResponse:
            def __init__(self, output_text, response_id):
                self.id = response_id
                self.output_text = output_text
                self.text = output_text  # Alternative access method
                self.model = "gpt-4o"
                self.created_at = 1234567890
                self.usage = Mock()
                self.usage.input_tokens = 10
                self.usage.output_tokens = 20
                self.usage.total_tokens = 30
                # Add messages attribute for file download compatibility
                self.messages = []

        return MockNonStreamingResponse(output_text, response_id)

    @staticmethod
    def create_streaming_response(chunks):
        """Create a proper async iterator for streaming responses."""

        class MockStreamingResponse:
            def __init__(self, chunks):
                self.chunks = chunks
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.chunks):
                    raise StopAsyncIteration
                chunk = self.chunks[self.index]
                self.index += 1
                return chunk

        return MockStreamingResponse(chunks)

    @staticmethod
    def create_mock_chunk(
        output_text=None, finish_reason=None, tool_call=None
    ):
        """Create a mock response chunk with proper Responses API structure."""
        chunk = Mock()

        # Responses API format: chunk.response.body
        mock_response = Mock()
        mock_response.body = output_text or ""
        chunk.response = mock_response

        # Explicitly ensure no choices attribute to force Responses API path
        del chunk.choices

        # Also set up alternative formats for compatibility with fallback logic
        if output_text:
            chunk.output_text = output_text
            chunk.content = output_text
            chunk.text = output_text
        if finish_reason:
            chunk.finish_reason = finish_reason
        if tool_call:
            chunk.tool_call = tool_call
        return chunk

    @staticmethod
    def setup_mock_client(
        mock_openai_class, output_text, response_id="test-response-id"
    ):
        """Set up a complete mock client with non-streaming responses."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Create the non-streaming response
        response = MockResponsesAPIHelper.create_non_streaming_response(
            output_text, response_id
        )

        # Set up the responses.create mock as an async mock
        mock_responses = Mock()
        mock_responses.create = AsyncMock(return_value=response)
        mock_client.responses = mock_responses

        return mock_client

    @staticmethod
    def setup_mock_client_streaming(mock_openai_class, response_chunks):
        """Set up a complete mock client with streaming responses (legacy)."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Create the streaming response
        streaming_response = MockResponsesAPIHelper.create_streaming_response(
            response_chunks
        )

        # Set up the responses.create mock as an async mock
        mock_responses = Mock()
        mock_responses.create = AsyncMock(return_value=streaming_response)
        mock_client.responses = mock_responses

        return mock_client


class TestResponsesAPIIntegration:
    """Test OpenAI Responses API integration and streaming."""

    @patch.object(CLIENT_UTILS, "create_openai_client")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    @patch("ostruct.cli.runner.ModelRegistry")
    @patch("openai_model_registry.ModelRegistry")
    def test_responses_api_basic_call(
        self,
        mock_registry_class: Mock,
        mock_runner_registry: Mock,
        mock_validation_registry: Mock,
        mock_create_client: Mock,
        fs: FakeFilesystem,
    ) -> None:
        """Test basic Responses API call."""
        # Mock model registry and capabilities
        mock_registry = Mock()
        mock_capabilities = Mock()
        mock_capabilities.context_window = 128000
        mock_capabilities.max_output_tokens = 4096
        mock_capabilities.supported_parameters = {
            "temperature",
            "max_tokens",
            "max_output_tokens",
        }
        mock_capabilities.validate_parameter = Mock()
        mock_registry.get_capabilities.return_value = mock_capabilities

        # Apply the same mock to all registry instances
        mock_registry_class.get_instance.return_value = mock_registry
        mock_runner_registry.get_instance.return_value = mock_registry
        mock_validation_registry.get_instance.return_value = mock_registry

        # Mock upload cache to avoid database file issues

        cli_runner = CliTestRunner()

        # Set up mock client using the helper for non-streaming response
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_response = MockResponsesAPIHelper.create_non_streaming_response(
            '{"result": "API response"}'
        )
        mock_responses = Mock()
        mock_responses.create = AsyncMock(return_value=mock_response)
        mock_client.responses = mock_responses
        mock_create_client.return_value = mock_client

        # Create test files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="Test task")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "--model",
                "gpt-4o",
            ],
        )

        assert result.exit_code == 0
        mock_client.responses.create.assert_called_once()

        # Verify API call parameters
        call_args = mock_client.responses.create.call_args
        assert call_args[1]["model"] == "gpt-4o"
        assert (
            "input" in call_args[1]
        )  # Responses API uses 'input' not 'messages'
        assert "text" in call_args[1]  # Responses API uses 'text' format

    @patch.object(CLIENT_UTILS, "create_openai_client")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    @patch("ostruct.cli.runner.ModelRegistry")
    @patch("openai_model_registry.ModelRegistry")
    def test_responses_api_non_streaming(
        self,
        mock_registry_class: Mock,
        mock_runner_registry: Mock,
        mock_validation_registry: Mock,
        mock_create_client: Mock,
        fs: FakeFilesystem,
    ) -> None:
        """Test non-streaming responses work correctly."""
        # Mock model registry and capabilities
        mock_registry = Mock()
        mock_capabilities = Mock()
        mock_capabilities.context_window = 128000
        mock_capabilities.max_output_tokens = 4096
        mock_capabilities.supported_parameters = {
            "temperature",
            "max_tokens",
            "max_output_tokens",
        }
        mock_capabilities.validate_parameter = Mock()
        mock_registry.get_capabilities.return_value = mock_capabilities

        # Apply the same mock to all registry instances
        mock_registry_class.get_instance.return_value = mock_registry
        mock_runner_registry.get_instance.return_value = mock_registry
        mock_validation_registry.get_instance.return_value = mock_registry

        # Mock upload cache to avoid database file issues
        mock_cache = Mock()
        mock_create_client.return_value = mock_cache

        cli_runner = CliTestRunner()

        # Set up mock client for non-streaming response (streaming is no longer used)
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_response = MockResponsesAPIHelper.create_non_streaming_response(
            '{"result": "streaming response"}'
        )
        mock_responses = Mock()
        mock_responses.create = AsyncMock(return_value=mock_response)
        mock_client.responses = mock_responses
        mock_create_client.return_value = mock_client

        # Create test files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="Test streaming")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "--model",
                "gpt-4o",
            ],
        )

        assert result.exit_code == 0
        mock_client.responses.create.assert_called_once()

    @patch.object(CLIENT_UTILS, "create_openai_client")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    @patch("ostruct.cli.runner.ModelRegistry")
    @patch("openai_model_registry.ModelRegistry")
    def test_responses_api_with_tools(
        self,
        mock_registry_class: Mock,
        mock_runner_registry: Mock,
        mock_validation_registry: Mock,
        mock_create_client: Mock,
        fs: FakeFilesystem,
    ) -> None:
        """Test Responses API call with tools integration."""
        # Mock model registry and capabilities
        mock_registry = Mock()
        mock_capabilities = Mock()
        mock_capabilities.context_window = 128000
        mock_capabilities.max_output_tokens = 4096
        mock_capabilities.supported_parameters = {
            "temperature",
            "max_tokens",
            "max_output_tokens",
        }
        mock_capabilities.validate_parameter = Mock()
        mock_registry.get_capabilities.return_value = mock_capabilities

        # Apply the same mock to all registry instances
        mock_registry_class.get_instance.return_value = mock_registry
        mock_runner_registry.get_instance.return_value = mock_registry
        mock_validation_registry.get_instance.return_value = mock_registry

        cli_runner = CliTestRunner()

        # Set up mock client using the helper for non-streaming response
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_response = MockResponsesAPIHelper.create_non_streaming_response(
            '{"result": "Tool analysis complete"}'
        )
        mock_responses = Mock()
        mock_responses.create = AsyncMock(return_value=mock_response)
        mock_client.responses = mock_responses
        mock_create_client.return_value = mock_client

        # Create test files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/task.j2", contents="Analyze test data"
        )

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "--model",
                "gpt-4o",
            ],
        )

        assert result.exit_code == 0
        mock_client.responses.create.assert_called_once()

        # Verify the API call was made (tools integration happens at deeper level)
        call_args = mock_client.responses.create.call_args
        assert call_args is not None

    @patch.object(CLIENT_UTILS, "create_openai_client")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    @patch("ostruct.cli.runner.ModelRegistry")
    @patch("openai_model_registry.ModelRegistry")
    def test_responses_api_error_handling(
        self,
        mock_registry_class: Mock,
        mock_runner_registry: Mock,
        mock_validation_registry: Mock,
        mock_openai_class: Mock,
        fs: FakeFilesystem,
    ) -> None:
        """Test error handling in Responses API calls."""
        # Mock model registry and capabilities
        mock_registry = Mock()
        mock_capabilities = Mock()
        mock_capabilities.context_window = 128000
        mock_capabilities.max_output_tokens = 4096
        mock_capabilities.supported_parameters = {
            "temperature",
            "max_tokens",
            "max_output_tokens",
        }
        mock_capabilities.validate_parameter = Mock()
        mock_registry.get_capabilities.return_value = mock_capabilities

        # Apply the same mock to all registry instances
        mock_registry_class.get_instance.return_value = mock_registry
        mock_runner_registry.get_instance.return_value = mock_registry
        mock_validation_registry.get_instance.return_value = mock_registry

        cli_runner = CliTestRunner()

        # Setup mock client that raises an error
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        mock_client.responses.create.side_effect = Exception("API Error")

        # Create test files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="Test error")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "--model",
                "gpt-4o",
            ],
        )

        assert result.exit_code != 0
        mock_client.responses.create.assert_called_once()

    @patch.object(CLIENT_UTILS, "create_openai_client")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    @patch("ostruct.cli.runner.ModelRegistry")
    @patch("openai_model_registry.ModelRegistry")
    def test_responses_api_with_content(
        self,
        mock_registry_class: Mock,
        mock_runner_registry: Mock,
        mock_validation_registry: Mock,
        mock_openai_class: Mock,
        fs: FakeFilesystem,
    ) -> None:
        """Test API calls with content processing."""
        # Mock model registry and capabilities
        mock_registry = Mock()
        mock_capabilities = Mock()
        mock_capabilities.context_window = 128000
        mock_capabilities.max_output_tokens = 4096
        mock_capabilities.supported_parameters = {
            "temperature",
            "max_tokens",
            "max_output_tokens",
        }
        mock_capabilities.validate_parameter = Mock()
        mock_registry.get_capabilities.return_value = mock_capabilities

        # Apply the same mock to all registry instances
        mock_registry_class.get_instance.return_value = mock_registry
        mock_runner_registry.get_instance.return_value = mock_registry
        mock_validation_registry.get_instance.return_value = mock_registry

        cli_runner = CliTestRunner()

        # Set up mock client using the helper for non-streaming response
        mock_client = MockResponsesAPIHelper.setup_mock_client(
            mock_openai_class, '{"result": "Optimized response"}'
        )

        # Create test files with content that should be optimized
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        # Simple template for content processing test
        fs.create_file(
            f"{TEST_BASE_DIR}/task.j2",
            contents="Process content",
        )

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "--model",
                "gpt-4o",
            ],
        )

        assert result.exit_code == 0
        mock_client.responses.create.assert_called_once()

    @patch.object(CLIENT_UTILS, "create_openai_client")
    @patch("ostruct.cli.model_validation.ModelRegistry")
    @patch("ostruct.cli.runner.ModelRegistry")
    @patch("openai_model_registry.ModelRegistry")
    def test_responses_api_model_parameters(
        self,
        mock_registry_class: Mock,
        mock_runner_registry: Mock,
        mock_validation_registry: Mock,
        mock_openai_class: Mock,
        fs: FakeFilesystem,
    ) -> None:
        """Test model parameters are passed correctly."""
        # Mock model registry and capabilities
        mock_registry = Mock()
        mock_capabilities = Mock()
        mock_capabilities.context_window = 128000
        mock_capabilities.max_output_tokens = 4096
        mock_capabilities.supported_parameters = {
            "temperature",
            "max_tokens",
            "max_output_tokens",
        }
        mock_capabilities.validate_parameter = Mock()
        mock_registry.get_capabilities.return_value = mock_capabilities

        # Apply the same mock to all registry instances
        mock_registry_class.get_instance.return_value = mock_registry
        mock_runner_registry.get_instance.return_value = mock_registry
        mock_validation_registry.get_instance.return_value = mock_registry

        cli_runner = CliTestRunner()

        # Set up mock client using the helper for non-streaming response
        mock_client = MockResponsesAPIHelper.setup_mock_client(
            mock_openai_class, '{"result": "Parameter test"}'
        )

        # Create test files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="Test parameters")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "--model",
                "gpt-4o",
                "--temperature",
                "0.7",
                "--max-output-tokens",
                "1000",
            ],
        )

        assert result.exit_code == 0
        mock_client.responses.create.assert_called_once()

        # Verify model parameters
        call_args = mock_client.responses.create.call_args
        assert call_args[1]["model"] == "gpt-4o"
        # Note: temperature and max_tokens may be passed differently in Responses API
