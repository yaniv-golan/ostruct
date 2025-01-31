"""Test CLI functionality."""

import json
import logging
import os
import asyncio
from io import StringIO
from typing import Generator, Any, Callable
from unittest.mock import MagicMock, patch

import pytest
import asyncclick.testing
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.cli import ExitCode, create_cli, create_template_context, Namespace, _main
from ostruct.cli.file_list import FileInfo, FileInfoList
from ostruct.cli.security import SecurityManager


# Mock tiktoken for all tests
@pytest.fixture(autouse=True)  # type: ignore[misc]
def mock_tiktoken() -> Generator[None, None, None]:
    """Mock tiktoken to avoid filesystem issues."""
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3]  # Simple token count

    with (
        patch("tiktoken.encoding_for_model", return_value=mock_encoding),
        patch("tiktoken.get_encoding", return_value=mock_encoding),
    ):
        yield


@pytest.fixture(autouse=True)  # type: ignore[misc]
def mock_logging(fs: FakeFilesystem) -> StringIO:
    """Mock logging configuration to avoid file system issues and capture output."""
    # Create a mock log directory
    fs.create_dir(os.path.expanduser("~/.ostruct/logs"))

    # Reset logging to avoid interference between tests
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create StringIO for capturing log output
    log_stream = StringIO()

    # Create handlers that write to StringIO
    stream_handler = logging.StreamHandler(log_stream)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(
        os.path.expanduser("~/.ostruct/logs/ostruct.log")
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    )

    # Configure root logger
    logging.root.setLevel(logging.DEBUG)
    logging.root.addHandler(stream_handler)
    logging.root.addHandler(file_handler)

    return log_stream


class AsyncCliRunner(asyncclick.testing.CliRunner):
    """Custom CliRunner that supports async commands."""
    
    async def invoke(self, cli: Callable[..., Any], args: Any = None, **kwargs: Any) -> Any:
        """Override invoke method to handle async commands correctly."""
        result = await super().invoke(cli, args, **kwargs)
        return result


@pytest.fixture  # type: ignore[misc]
def cli_runner() -> AsyncCliRunner:
    """Create an async-compatible Click CLI test runner."""
    return AsyncCliRunner()


# Core CLI Tests
class TestCLICore:
    """Test core CLI functionality."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_help_text(self, cli_runner: AsyncCliRunner) -> None:
        """Test help text display."""
        result = await cli_runner.invoke(create_cli(), ["--help"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "usage:" in output
        assert "--help" in output

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_version_info(self, cli_runner: AsyncCliRunner) -> None:
        """Test version info display."""
        result = await cli_runner.invoke(create_cli(), ["--version"])
        assert result.exit_code == 0
        output = result.output
        assert "version" in output.lower()
        assert "cli" in output.lower()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_missing_required_args(self, cli_runner: AsyncCliRunner) -> None:
        """Test error handling for missing required arguments."""
        result = await cli_runner.invoke(create_cli())
        assert result.exit_code == 2  # AsyncClick uses exit code 2 for missing required args
        assert isinstance(result.exception, SystemExit)
        output = result.output.lower()
        assert "missing option" in output
        assert "--task" in output

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_invalid_json_var(self, cli_runner: AsyncCliRunner, fs: FakeFilesystem) -> None:
        """Test error handling for invalid JSON variable."""
        # Create a minimal schema file
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))

        result = await cli_runner.invoke(create_cli(), [
            "--task", "test task",
            "--schema", "schema.json",
            "--json-var", "invalid_json={not json}",
        ])
    
        assert result.exit_code != 0
        expected_error = "error parsing json for variable 'invalid_json'"
        assert expected_error in str(result.exception).lower(), f"Expected error message containing '{expected_error}' but got: {result.exception}"

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_invalid_schema_file(self, cli_runner: AsyncCliRunner, fs: FakeFilesystem) -> None:
        """Test error handling for invalid schema file."""
        # Create an invalid schema file
        fs.create_file("schema.json", contents="{ invalid json }")
        
        result = await cli_runner.invoke(create_cli(), [
            "--task", "test task",
            "--schema", "schema.json",
        ])
        
        assert result.exit_code != 0
        error_msg = str(result.exception).lower()
        # Check for both the error type and specific details
        assert "invalid json in schema file" in error_msg
        assert "expecting" in error_msg  # Common part of JSON parse errors

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_missing_schema_file(self, cli_runner: AsyncCliRunner) -> None:
        """Test error handling for missing schema file."""
        result = await cli_runner.invoke(create_cli(), [
            "--task", "test task",
            "--schema", "nonexistent.json",
        ])
        
        assert result.exit_code != 0
        error_msg = str(result.exception).lower()
        # Check for both the error type and specific details
        assert "failed to read schema file" in error_msg
        assert "no such file or directory" in error_msg
        assert "nonexistent.json" in error_msg

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_invalid_file_path(self, cli_runner: AsyncCliRunner, fs: FakeFilesystem) -> None:
        """Test error handling for invalid file path."""
        # Create a minimal schema file
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        
        result = await cli_runner.invoke(create_cli(), [
            "--task", "test task",
            "--schema", "schema.json",
            "--file", "input=nonexistent.txt",
        ])
        
        assert result.exit_code != 0
        error_msg = str(result.exception).lower()
        # Check for both the error type and specific details
        assert "file access error" in error_msg
        assert "nonexistent.txt" in error_msg

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_invalid_template_syntax(
        self, fs: FakeFilesystem, cli_runner: AsyncCliRunner
    ) -> None:
        """Test error handling for invalid template syntax."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="Invalid syntax: {{ unclosed")

        result = await cli_runner.invoke(create_cli(), [
            "--task", "@task.txt",
            "--schema", "schema.json",
            "--dry-run",
        ])
        
        assert result.exit_code != 0
        error_msg = str(result.exception).lower()
        # Check for both the error type and specific details
        assert "invalid task template syntax" in error_msg
        assert "line" in error_msg  # Template errors include line numbers
        # Jinja2 provides specific syntax error details
        assert "unexpected end of template" in error_msg or "end of print statement" in error_msg


# OpenAI-dependent tests
class TestCLIPreExecution:
    """Test CLI execution without OpenAI API."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_basic_execution_setup(
        self, fs: FakeFilesystem, mock_logging: StringIO, cli_runner: AsyncCliRunner
    ) -> None:
        """Test basic CLI execution setup without OpenAI."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="Process this: {{ input.content }}")
        fs.create_file("input.txt", contents="test content")

        result = await cli_runner.invoke(create_cli(), [
            "--task", "@task.txt",
            "--schema", "schema.json",
            "--file", "input=input.txt",
            "--debug-validation",
            "--verbose",
            "--dry-run",
        ])
        
        assert result.exit_code == 0
        log_output = mock_logging.getvalue()
        expected_messages = [
            "Process this: test content",
            "DRY RUN MODE"
        ]
        for msg in expected_messages:
            assert msg in log_output, f"Expected message '{msg}' not found in log output"

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_stdin_setup(
        self, fs: FakeFilesystem, mock_logging: StringIO, cli_runner: AsyncCliRunner
    ) -> None:
        """Test stdin setup without OpenAI."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="Input: {{ stdin }}")

        with patch("sys.stdin.isatty", return_value=False):  # Mock isatty only
            result = await cli_runner.invoke(create_cli(), [
                "--task", "@task.txt",
                "--schema", "schema.json",
                "--dry-run",
            ], input="test input")  # Provide input via Click's runner
            
            assert result.exit_code == 0
            log_output = mock_logging.getvalue()
            expected_messages = [
                "Input: test input",
                "DRY RUN MODE"
            ]
            for msg in expected_messages:
                assert msg in log_output, f"Expected message '{msg}' not found in log output"

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_directory_traversal(
        self, fs: FakeFilesystem, mock_logging: StringIO, cli_runner: AsyncCliRunner
    ) -> None:
        """Test directory traversal without OpenAI."""
        # Create necessary files and directories
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="Files: {{ files | length }}")
        fs.create_dir("test_dir")
        fs.create_file("test_dir/file1.txt", contents="content 1")
        fs.create_file("test_dir/file2.txt", contents="content 2")
        fs.create_file("test_dir/file3.txt", contents="content 3")

        result = await cli_runner.invoke(create_cli(), [
            "--task", "@task.txt",
            "--schema", "schema.json",
            "--dir", "files=test_dir",
            "--dir-recursive",
            "--dir-ext", "txt",
            "--dry-run",
        ])
        
        assert result.exit_code == 0
        log_output = mock_logging.getvalue()
        expected_messages = [
            "Files: 3",
            "DRY RUN MODE"
        ]
        for msg in expected_messages:
            assert msg in log_output, f"Expected message '{msg}' not found in log output"

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_template_rendering_mixed(
        self, fs: FakeFilesystem, mock_logging: StringIO, cli_runner: AsyncCliRunner
    ) -> None:
        """Test template rendering with mixed inputs."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file(
            "task.txt",
            contents="File: {{ input.content }}, Var: {{ var1 }}, Config: {{ config.key }}",
        )
        fs.create_file("input.txt", contents="file content")

        result = await cli_runner.invoke(create_cli(), [
            "--task", "@task.txt",
            "--schema", "schema.json",
            "--file", "input=input.txt",
            "--var", "var1=test value",
            "--json-var", 'config={"key": "value"}',
            "--verbose",
            "--dry-run",
        ])
        
        assert result.exit_code == 0
        log_output = mock_logging.getvalue()
        expected_messages = [
            "File: file content, Var: test value, Config: value",
            "DRY RUN MODE"
        ]
        for msg in expected_messages:
            assert msg in log_output, f"Expected message '{msg}' not found in log output"


@pytest.mark.live
class TestCLIExecution:
    """Test CLI execution that requires OpenAI API."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_basic_execution(
        self, fs: FakeFilesystem, mock_logging: StringIO, cli_runner: AsyncCliRunner
    ) -> None:
        """Test basic CLI execution with OpenAI."""
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file(
            "task.txt", contents="Process this: {{ input.content }}"
        )
        fs.create_file("input.txt", contents="test content")

        result = await cli_runner.invoke(create_cli(), [
            "--task", "@task.txt",
            "--schema", "schema.json",
            "--file", "input=input.txt",
            "--debug-validation",
            "--verbose",
        ])
        assert result.exit_code == 0
        output = mock_logging.getvalue()
        assert "Process this: test content" in output

    @pytest.mark.live  # type: ignore[misc]
    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_file_input(
        self, fs: FakeFilesystem, mock_logging: StringIO, cli_runner: AsyncCliRunner
    ) -> None:
        """Test file input with OpenAI."""
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="Content: {{ input.content }}")
        fs.create_file("input.txt", contents="test content")

        result = await cli_runner.invoke(create_cli(), [
            "--task", "@task.txt",
            "--schema", "schema.json",
            "--file", "input=input.txt",
        ])
        assert result.exit_code == 0
        output = mock_logging.getvalue()
        assert "Content: test content" in output

    @pytest.mark.live  # type: ignore[misc]
    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_stdin_input(
        self, fs: FakeFilesystem, mock_logging: StringIO, cli_runner: AsyncCliRunner
    ) -> None:
        """Test stdin input with OpenAI."""
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="Input: {{ stdin }}")

        result = await cli_runner.invoke(create_cli(), [
            "--task", "@task.txt",
            "--schema", "schema.json",
        ], input="test input")  # Provide input directly to invoke
            
        assert result.exit_code == 0
        output = mock_logging.getvalue()
        assert "Input: test input" in output

    @pytest.mark.live  # type: ignore[misc]
    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_directory_input(
        self, fs: FakeFilesystem, mock_logging: StringIO, cli_runner: AsyncCliRunner
    ) -> None:
        """Test directory input with OpenAI."""
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="Files: {{ files | length }}")
        fs.create_dir("test_dir")
        fs.create_file("test_dir/file1.txt", contents="content 1")
        fs.create_file("test_dir/file2.txt", contents="content 2")

        result = await cli_runner.invoke(create_cli(), [
            "--task", "@task.txt",
            "--schema", "schema.json",
            "--dir", "files=test_dir",
        ])
        assert result.exit_code == 0
        output = mock_logging.getvalue()
        assert "Files: 2" in output


# Template Context Tests
class TestTemplateContext:
    """Test template context creation (no OpenAI needed)."""

    def test_template_context_single_file(self, fs: FakeFilesystem) -> None:
        """Test template context creation with a single file."""
        fs.create_file("input.txt", contents="test content")
        security = SecurityManager()
        file_info = FileInfoList(
            [FileInfo.from_path("input.txt", security_manager=security)]
        )

        context = create_template_context(
            files={"input": file_info},
            variables={},
            json_variables={},
            security_manager=security,
        )

        assert context["input"].content == "test content"
        assert context["input"].path == "input.txt"

    def test_template_context_multiple_files(self, fs: FakeFilesystem) -> None:
        """Test template context creation with multiple files."""
        fs.create_file("file1.txt", contents="content 1")
        fs.create_file("file2.txt", contents="content 2")
        security = SecurityManager()
        file_info1 = FileInfoList(
            [FileInfo.from_path("file1.txt", security_manager=security)]
        )
        file_info2 = FileInfoList(
            [FileInfo.from_path("file2.txt", security_manager=security)]
        )

        context = create_template_context(
            files={"file1": file_info1, "file2": file_info2},
            variables={},
            json_variables={},
            security_manager=security,
        )

        assert context["file1"].content == "content 1"
        assert context["file2"].content == "content 2"

    def test_template_context_mixed_sources(self, fs: FakeFilesystem) -> None:
        """Test template context creation with mixed sources."""
        fs.create_file("input.txt", contents="file content")
        security = SecurityManager()
        file_info = FileInfoList(
            [FileInfo.from_path("input.txt", security_manager=security)]
        )

        context = create_template_context(
            files={"input": file_info},
            variables={"var1": "test value"},
            json_variables={"config": {"key": "value"}},
            security_manager=security,
        )

        assert context["input"].content == "file content"
        assert context["var1"] == "test value"
        assert context["config"]["key"] == "value"
