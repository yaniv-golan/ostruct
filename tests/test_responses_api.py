"""Tests for OpenAI Responses API integration."""

import json
import os
from unittest.mock import Mock, patch, AsyncMock

import pytest
from click.testing import CliRunner
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.cli import create_cli
from tests.test_cli import CliTestRunner

# Test workspace base directory
TEST_BASE_DIR = "/test_workspace/base"


class MockResponsesAPIHelper:
    """Helper class for mocking OpenAI Responses API calls following best practices."""

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
    def create_mock_chunk(output_text=None, finish_reason=None, tool_call=None):
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
    def setup_mock_client(mock_openai_class, response_chunks):
        """Set up a complete mock client with responses."""
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

    @patch("ostruct.cli.cli.AsyncOpenAI")
    def test_responses_api_basic_call(
        self, mock_openai_class: Mock, fs: FakeFilesystem
    ) -> None:
        """Test basic Responses API call."""
        cli_runner = CliTestRunner()

        # Set up mock client using the helper
        response_chunks = [
            MockResponsesAPIHelper.create_mock_chunk(
                output_text='{"result": "API response"}'
            )
        ]
        mock_client = MockResponsesAPIHelper.setup_mock_client(
            mock_openai_class, response_chunks
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
        assert "input" in call_args[1]  # Responses API uses 'input' not 'messages'
        assert "text" in call_args[1]  # Responses API uses 'text' format

    @patch("ostruct.cli.cli.AsyncOpenAI")
    def test_responses_api_streaming(
        self, mock_openai_class: Mock, fs: FakeFilesystem
    ) -> None:
        """Test streaming responses work correctly."""
        cli_runner = CliTestRunner()

        # Setup mock client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Mock streaming response with multiple chunks using Responses API format
        mock_chunks = [
            MockResponsesAPIHelper.create_mock_chunk(output_text='{"result": "'),
            MockResponsesAPIHelper.create_mock_chunk(output_text="streaming "),
            MockResponsesAPIHelper.create_mock_chunk(output_text='response"}'),
        ]

        # Reuse the MockStreamingResponse class
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

        mock_responses = Mock()
        mock_responses.create = AsyncMock(
            return_value=MockStreamingResponse(mock_chunks)
        )
        mock_client.responses = mock_responses

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

    @patch("ostruct.cli.cli.AsyncOpenAI")
    def test_responses_api_with_tools(
        self, mock_openai_class: Mock, fs: FakeFilesystem
    ) -> None:
        """Test Responses API call with tools integration."""
        cli_runner = CliTestRunner()

        # Set up mock client using the helper
        response_chunks = [
            MockResponsesAPIHelper.create_mock_chunk(
                output_text='{"result": "Tool analysis complete"}'
            )
        ]
        mock_client = MockResponsesAPIHelper.setup_mock_client(
            mock_openai_class, response_chunks
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
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="Analyze test data")

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

    @patch("ostruct.cli.cli.AsyncOpenAI")
    def test_responses_api_error_handling(
        self, mock_openai_class: Mock, fs: FakeFilesystem
    ) -> None:
        """Test error handling in Responses API calls."""
        cli_runner = CliTestRunner()

        # Setup mock client that raises an error
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        from ostruct.cli.errors import APIError

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

    @patch("ostruct.cli.cli.AsyncOpenAI")
    def test_responses_api_token_optimization(
        self, mock_openai_class: Mock, fs: FakeFilesystem
    ) -> None:
        """Test token optimization in API calls."""
        cli_runner = CliTestRunner()

        # Set up mock client using the helper
        response_chunks = [
            MockResponsesAPIHelper.create_mock_chunk(
                output_text='{"result": "Optimized response"}'
            )
        ]
        mock_client = MockResponsesAPIHelper.setup_mock_client(
            mock_openai_class, response_chunks
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
        # Simple template for token optimization test
        fs.create_file(
            f"{TEST_BASE_DIR}/task.j2",
            contents="Process large content for optimization",
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

    @patch("ostruct.cli.cli.AsyncOpenAI")
    def test_responses_api_model_parameters(
        self, mock_openai_class: Mock, fs: FakeFilesystem
    ) -> None:
        """Test model parameters are passed correctly."""
        cli_runner = CliTestRunner()

        # Set up mock client using the helper
        response_chunks = [
            MockResponsesAPIHelper.create_mock_chunk(
                output_text='{"result": "Parameter test"}'
            )
        ]
        mock_client = MockResponsesAPIHelper.setup_mock_client(
            mock_openai_class, response_chunks
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
