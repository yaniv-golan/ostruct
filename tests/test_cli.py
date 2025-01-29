"""Test CLI functionality."""

import json
import logging
import os
from io import StringIO
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.cli import ExitCode, _main, create_template_context
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


# Core CLI Tests


class TestCLICore:
    """Test core CLI functionality."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_help_text(self) -> None:
        """Test help text display."""
        with (
            patch("sys.argv", ["ostruct", "--help"]),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            with pytest.raises(SystemExit) as exc_info:
                await _main()
            assert exc_info.value.code == 0
            output = mock_stdout.getvalue().lower()
            assert "usage:" in output
            assert "--help" in output

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_version_info(self) -> None:
        """Test version info display."""
        with (
            patch("sys.argv", ["ostruct", "--version"]),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            with pytest.raises(SystemExit) as exc_info:
                await _main()
            assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            # Check that output starts with "ostruct" and includes a version string
            assert output.startswith("ostruct ")
            # Version should be non-empty after "ostruct "
            assert len(output.strip()) > len("ostruct ")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_missing_required_args(self) -> None:
        """Test error handling for missing required arguments."""
        with (
            patch("sys.argv", ["ostruct"]),
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
        ):
            with pytest.raises(SystemExit) as exc_info:
                await _main()
            assert exc_info.value.code != 0
            output = mock_stderr.getvalue().lower()
            assert "required" in output

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_invalid_json_var(
        self, fs: FakeFilesystem, mock_logging: StringIO
    ) -> None:
        """Test error handling for invalid JSON variable."""
        # Create required schema file
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))

        with patch(
            "sys.argv",
            [
                "ostruct",
                "--task",
                "test task",  # Simple task template
                "--schema",
                "schema.json",  # Required schema argument
                "--json-var",
                "invalid_json={not json}",  # Invalid JSON to test
            ],
        ):
            result = await _main()
            assert result == ExitCode.DATA_ERROR
            output = mock_logging.getvalue().lower()
            assert "invalid json value" in output


# OpenAI-dependent tests
class TestCLIPreExecution:
    """Test CLI execution without OpenAI API."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_basic_execution_setup(
        self, fs: FakeFilesystem, mock_logging: StringIO
    ) -> None:
        """Test basic CLI execution setup without OpenAI."""
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

        with patch(
            "sys.argv",
            [
                "ostruct",
                "--task",
                "@task.txt",
                "--schema",
                "schema.json",
                "--file",
                "input=input.txt",
                "--debug-validation",
                "--verbose",
                "--dry-run",
            ],
        ):
            result = await _main()
            assert result == ExitCode.SUCCESS
            output = mock_logging.getvalue()
            assert "Process this: test content" in output
            assert "DRY RUN MODE" in output

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_stdin_setup(
        self, fs: FakeFilesystem, mock_logging: StringIO
    ) -> None:
        """Test stdin setup without OpenAI."""
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="Input: {{ stdin }}")

        with (
            patch(
                "sys.argv",
                [
                    "ostruct",
                    "--task",
                    "@task.txt",
                    "--schema",
                    "schema.json",
                    "--dry-run",
                ],
            ),
            patch("sys.stdin.isatty", return_value=False),
            patch("sys.stdin.read", return_value="test input"),
        ):
            result = await _main()
            assert result == ExitCode.SUCCESS
            output = mock_logging.getvalue()
            assert "Input: test input" in output
            assert "DRY RUN MODE" in output

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_directory_traversal(
        self, fs: FakeFilesystem, mock_logging: StringIO
    ) -> None:
        """Test directory traversal without OpenAI."""
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

        with patch(
            "sys.argv",
            [
                "ostruct",
                "--task",
                "@task.txt",
                "--schema",
                "schema.json",
                "--dir",
                "files=test_dir",
                "--dir-recursive",
                "--dir-ext",
                "txt",
                "--dry-run",
            ],
        ):
            result = await _main()
            assert result == ExitCode.SUCCESS
            output = mock_logging.getvalue()
            assert "Files: 3" in output
            assert "DRY RUN MODE" in output

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_template_rendering_mixed(
        self, fs: FakeFilesystem, mock_logging: StringIO
    ) -> None:
        """Test template rendering with mixed inputs."""
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

        with patch(
            "sys.argv",
            [
                "ostruct",
                "--task",
                "@task.txt",
                "--schema",
                "schema.json",
                "--file",
                "input=input.txt",
                "--var",
                "var1=test value",
                "--json-var",
                'config={"key": "value"}',
                "--verbose",
                "--dry-run",
            ],
        ):
            result = await _main()
            assert result == ExitCode.SUCCESS
            output = mock_logging.getvalue()
            assert (
                "File: file content, Var: test value, Config: value" in output
            )
            assert "DRY RUN MODE" in output


@pytest.mark.live
class TestCLIExecution:
    """Test CLI execution that requires OpenAI API."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_basic_execution(
        self, fs: FakeFilesystem, mock_logging: StringIO
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

        with patch(
            "sys.argv",
            [
                "ostruct",
                "--task",
                "@task.txt",
                "--schema",
                "schema.json",
                "--file",
                "input=input.txt",
                "--debug-validation",
                "--verbose",
            ],
        ):
            result = await _main()
            assert result == ExitCode.SUCCESS

    @pytest.mark.live  # type: ignore[misc]
    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_file_input(
        self, fs: FakeFilesystem, mock_logging: StringIO
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

        with patch(
            "sys.argv",
            [
                "ostruct",
                "--task",
                "@task.txt",
                "--schema",
                "schema.json",
                "--file",
                "input=input.txt",
            ],
        ):
            result = await _main()
            assert result == ExitCode.SUCCESS

    @pytest.mark.live  # type: ignore[misc]
    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_stdin_input(
        self, fs: FakeFilesystem, mock_logging: StringIO
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

        with (
            patch(
                "sys.argv",
                [
                    "ostruct",
                    "--task",
                    "@task.txt",
                    "--schema",
                    "schema.json",
                ],
            ),
            patch("sys.stdin.isatty", return_value=False),
            patch("sys.stdin.read", return_value="test input"),
        ):
            result = await _main()
            assert result == ExitCode.SUCCESS

    @pytest.mark.live  # type: ignore[misc]
    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_directory_input(
        self, fs: FakeFilesystem, mock_logging: StringIO
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

        with patch(
            "sys.argv",
            [
                "ostruct",
                "--task",
                "@task.txt",
                "--schema",
                "schema.json",
                "--dir",
                "files=test_dir",
            ],
        ):
            result = await _main()
            assert result == ExitCode.SUCCESS


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
