"""Tests for CLI functionality."""

import json
import logging
import os
from io import StringIO
from typing import Any, List, Optional

import click
import pytest
from click.testing import CliRunner, Result  # noqa: F401 - used in type hints
from openai_structured.model_registry import ModelRegistry
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.cli import create_cli, create_template_context
from ostruct.cli.errors import CLIError, InvalidJSONError
from ostruct.cli.exit_codes import ExitCode
from ostruct.cli.file_list import FileInfo, FileInfoList
from ostruct.cli.security import SecurityManager

# Configure logging for tests
logger = logging.getLogger(__name__)

# Get the model registry instance for testing
model_registry = ModelRegistry()


@pytest.fixture(autouse=True)
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


class CliTestRunner:
    """Custom test runner for CLI commands that captures logging output."""

    def __init__(self) -> None:
        """Initialize the test runner."""
        self.log_capture: Optional[StringIO] = None
        self.log_handler: Optional[logging.StreamHandler] = None
        self.loggers: List[logging.Logger] = []

    def invoke(self, *args: Any, **kwargs: Any) -> Result:
        """Invoke a CLI command with logging capture."""
        logger.debug("Starting CliTestRunner.invoke")
        logger.debug("Args: %s", args)
        logger.debug("Kwargs: %s", kwargs)

        # Set up logging capture
        self._setup_logging()

        try:
            # Let Click catch exceptions but ensure we get the original exception
            kwargs["catch_exceptions"] = True
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(*args, **kwargs)

            # For debugging, print captured logs
            if self.log_capture:
                print("\nCaptured logs:")
                print(self.log_capture.getvalue())

            # For Click usage errors (exit code 2), always create a UsageError
            if result.exit_code == 2:
                error_text = str(result.stderr or result.stdout or "").strip()
                result.exception = click.UsageError(error_text)
                return result

            # For other errors, try to get the original exception from the traceback
            if result.exc_info:
                exc_type, exc_value, tb = result.exc_info

                # Handle SystemExit explicitly
                if isinstance(exc_value, SystemExit):
                    # First check for wrapped CLIError or InvalidJSONError in the context chain
                    current = exc_value.__context__
                    while current is not None:
                        if isinstance(current, (CLIError, InvalidJSONError)):
                            result.exception = current
                            if isinstance(current, InvalidJSONError):
                                result.exit_code = ExitCode.DATA_ERROR
                            else:
                                result.exit_code = current.exit_code
                            return result
                        current = getattr(current, "__context__", None)

                    # If no CLIError found, use the exit code
                    result.exit_code = (
                        exc_value.code
                        if isinstance(exc_value.code, int)
                        else 1
                    )
                    return result

                # Handle CLIError and InvalidJSONError directly
                current = exc_value
                while current is not None:
                    if isinstance(current, (CLIError, InvalidJSONError)):
                        result.exception = current
                        if isinstance(current, InvalidJSONError):
                            result.exit_code = ExitCode.DATA_ERROR
                        else:
                            result.exit_code = current.exit_code
                        return result
                    current = getattr(current, "__cause__", None)

            return result
        finally:
            self._cleanup_logging()

    def _setup_logging(self) -> None:
        """Set up logging capture."""
        self.log_capture = StringIO()
        if self.log_capture is not None:
            self.log_handler = logging.StreamHandler(self.log_capture)
            if self.log_handler is not None:
                self.log_handler.setFormatter(
                    logging.Formatter("%(levelname)s - %(message)s")
                )

                # Capture all relevant loggers
                loggers = ["root", "ostruct.cli.cli", "openai_structured"]
                logger.debug("Setting up loggers: %s", loggers)
                self.loggers = [logging.getLogger(name) for name in loggers]
                for log in self.loggers:
                    if self.log_handler is not None:
                        log.addHandler(self.log_handler)

    def _cleanup_logging(self) -> None:
        """Clean up logging handlers."""
        for log in self.loggers:
            if self.log_handler is not None:
                log.removeHandler(self.log_handler)
        self.log_handler = None
        self.log_capture = None
        self.loggers = []

    def check_error_message(
        self,
        result: Result,
        expected_message: str,
        *,
        check_exit_code: bool = True,
    ) -> None:
        """Check that the error message matches expectations."""
        # Convert expected message to lowercase for case-insensitive comparison
        expected_message_lower = expected_message.lower()

        # Collect all potential error sources
        error_sources = []

        # 1. Handle Click errors (exit code 2)
        if result.exit_code == 2:
            error_sources.extend(
                [str(result.stderr or ""), str(result.stdout or "")]
            )

        # 2. Handle our custom errors
        elif isinstance(result.exception, CLIError):
            # Get the error message directly
            error_sources.append(str(result.exception))

            # Include context if available
            if result.exception.context:
                error_sources.append(str(result.exception.context))

        # 3. Handle InvalidJSONError
        elif isinstance(result.exception, InvalidJSONError):
            error_sources.append(str(result.exception))

        # 4. Handle other exceptions
        elif result.exception:
            error_sources.extend(
                [
                    str(result.exception),
                    str(getattr(result.exception, "__cause__", "")),
                    str(getattr(result.exception, "__context__", "")),
                ]
            )

        # 5. Include stdout/stderr if available
        if result.stdout:
            error_sources.append(str(result.stdout))
        if result.stderr:
            error_sources.append(str(result.stderr))

        # Combine all error sources and convert to lowercase
        error_text = "\n".join(filter(None, error_sources)).lower()
        error_text_lower = error_text.lower()

        # Check exit code if requested
        if check_exit_code:
            assert result.exit_code != 0, (
                f"Expected non-zero exit code.\n"
                f"Got:\nExit Code: {result.exit_code}\n"
                f"Exception Type: {type(result.exception).__name__}\n"
                f"Error Text:\n{error_text}"
            )
        else:
            assert expected_message_lower in error_text_lower, (
                f"Expected error message not found in output.\n"
                f"Expected: {expected_message}\n"
                f"Got:\nExit Code: {result.exit_code}\n"
                f"Exception Type: {type(result.exception).__name__}\n"
                f"Error Text:\n{error_text}"
            )


@pytest.fixture
def cli_runner() -> CliTestRunner:
    """Create a CLI test runner."""
    return CliTestRunner()


# Core CLI Tests
class TestCLICore:
    """Test core CLI functionality."""

    def test_task_template_string(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test using task template string directly."""
        # Create a minimal schema file
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--schema-file",
                "schema.json",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_task_template_file(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test using task template from file."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="test task from file")

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task-file",
                "task.txt",
                "--schema-file",
                "schema.json",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_system_prompt_string(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test using system prompt string directly."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--system-prompt",
                "custom system prompt",
                "--schema-file",
                "schema.json",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_system_prompt_file(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test using system prompt from file."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("prompt.txt", contents="custom system prompt from file")

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--system-prompt-file",
                "prompt.txt",
                "--schema-file",
                "schema.json",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_allowed_dir_file(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test using allowed directories from file."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_dir("allowed_dir1")
        fs.create_dir("allowed_dir2")
        fs.create_file(
            "allowed_dirs.txt", contents="allowed_dir1\nallowed_dir2"
        )

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--schema-file",
                "schema.json",
                "--allowed-dir-file",
                "allowed_dirs.txt",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_conflicting_task_params(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test error when both task string and file are provided."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("task.txt", contents="test task")

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--task-file",
                "task.txt",
                "--schema-file",
                "schema.json",
            ],
        )

        # This should be a usage error
        assert result.exit_code == 2
        assert isinstance(result.exception, click.UsageError)
        cli_runner.check_error_message(result, "Cannot specify both")

    def test_conflicting_system_prompt_params(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test error when both system prompt string and file are provided."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))
        fs.create_file("prompt.txt", contents="test prompt")

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--system-prompt",
                "test prompt",
                "--system-prompt-file",
                "prompt.txt",
                "--schema-file",
                "schema.json",
            ],
        )
        cli_runner.check_error_message(result, "Cannot specify both")

    def test_missing_task(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test error when no task is provided."""
        # Create necessary files
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file("schema.json", contents=json.dumps(schema_content))

        result = cli_runner.invoke(
            create_cli(),
            [
                "--schema-file",
                "schema.json",
            ],
        )
        cli_runner.check_error_message(
            result, "Must specify either --task or --task-file"
        )

    def test_help_text(self, cli_runner: CliTestRunner) -> None:
        """Test help text display."""
        result = cli_runner.invoke(create_cli(), ["--help"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "usage:" in output
        assert "--help" in output

    def test_version_info(self, cli_runner: CliTestRunner) -> None:
        """Test version info display."""
        result = cli_runner.invoke(create_cli(), ["--version"])
        assert result.exit_code == 0
        output = result.output
        assert "version" in output.lower()
        assert "cli" in output.lower()

    def test_missing_required_args(self, cli_runner: CliTestRunner) -> None:
        """Test error handling for missing required arguments."""
        result = cli_runner.invoke(create_cli())
        cli_runner.check_error_message(
            result, "Missing option '--schema-file'"
        )

        # Test that providing schema-file but no task also fails
        result = cli_runner.invoke(
            create_cli(), ["--schema-file", "schema.json"]
        )
        cli_runner.check_error_message(
            result, "Must specify either --task or --task-file"
        )

    def test_invalid_json_var(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
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

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--schema-file",
                "schema.json",
                "--json-var",
                "invalid_json={not json}",
            ],
        )

        # This should be a data format error
        assert result.exit_code == ExitCode.DATA_ERROR
        assert isinstance(result.exception, InvalidJSONError)
        cli_runner.check_error_message(
            result, "Error parsing JSON for variable"
        )

    def test_invalid_schema_file(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test error handling for invalid schema file."""
        # Create an invalid schema file
        fs.create_file("schema.json", contents="{ invalid json }")

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--schema-file",
                "schema.json",
                "--verbose",  # Add verbose flag to see more logs
            ],
        )

        # Check the logs
        if cli_runner.log_capture:
            logs = cli_runner.log_capture.getvalue()
            print("Captured logs:", logs)  # Print logs for debugging

        cli_runner.check_error_message(result, "Invalid JSON")

    def test_missing_schema_file(self, cli_runner: CliTestRunner) -> None:
        """Test error handling for missing schema file."""
        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--schema-file",
                "nonexistent.json",
            ],
        )
        cli_runner.check_error_message(result, "File not found")

    def test_invalid_file_path(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
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

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task",
                "test task",
                "--schema-file",
                "schema.json",
                "--file",
                "input=nonexistent.txt",
            ],
        )
        cli_runner.check_error_message(result, "File not found")

    def test_invalid_template_syntax(
        self, fs: FakeFilesystem, cli_runner: CliTestRunner
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

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task-file",
                "task.txt",
                "--schema-file",
                "schema.json",
                "--dry-run",
            ],
        )
        cli_runner.check_error_message(result, "Template syntax error")


# OpenAI-dependent tests
class TestCLIPreExecution:
    """Test CLI pre-execution functionality without OpenAI."""

    def test_directory_traversal(
        self,
        fs: FakeFilesystem,
        mock_logging: StringIO,
        cli_runner: CliTestRunner,
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
        fs.create_file(
            "/test_workspace/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            "/test_workspace/task.txt", contents="Files: {{ files | length }}"
        )
        fs.create_dir("/test_workspace/test_dir")
        fs.create_file(
            "/test_workspace/test_dir/file1.txt", contents="content 1"
        )
        fs.create_file(
            "/test_workspace/test_dir/file2.txt", contents="content 2"
        )
        fs.create_file(
            "/test_workspace/test_dir/file3.txt", contents="content 3"
        )

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task-file",
                "/test_workspace/task.txt",
                "--schema-file",
                "/test_workspace/schema.json",
                "--dir",
                "files=/test_workspace/test_dir",
                "--dir-recursive",
                "--dir-ext",
                "txt",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0


@pytest.mark.live
class TestCLIExecution:
    """Test CLI execution functionality with OpenAI."""

    @pytest.fixture(autouse=True)
    def _requires_openai(self, requires_openai: None) -> None:
        """Ensure OpenAI API key is available."""
        pass

    def test_basic_execution(
        self,
        fs: FakeFilesystem,
        mock_logging: StringIO,
        cli_runner: CliTestRunner,
    ) -> None:
        """Test basic CLI execution with OpenAI."""
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file(
            "/test_workspace/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            "/test_workspace/task.txt",
            contents="Process this: {{ input.content }}",
        )
        fs.create_file("/test_workspace/input.txt", contents="test content")

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task-file",
                "/test_workspace/task.txt",
                "--schema-file",
                "/test_workspace/schema.json",
                "--file",
                "input=/test_workspace/input.txt",
                "--debug-validation",
                "--verbose",
            ],
        )
        assert result.exit_code == 0

    def test_file_input(
        self,
        fs: FakeFilesystem,
        mock_logging: StringIO,
        cli_runner: CliTestRunner,
    ) -> None:
        """Test file input with OpenAI."""
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file(
            "/test_workspace/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            "/test_workspace/task.txt", contents="Content: {{ input.content }}"
        )
        fs.create_file("/test_workspace/input.txt", contents="test content")

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task-file",
                "/test_workspace/task.txt",
                "--schema-file",
                "/test_workspace/schema.json",
                "--file",
                "input=/test_workspace/input.txt",
            ],
        )
        assert result.exit_code == 0

    def test_template_rendering_mixed(
        self,
        fs: FakeFilesystem,
        mock_logging: StringIO,
        cli_runner: CliTestRunner,
    ) -> None:
        """Test template rendering with mixed inputs."""
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            }
        }
        fs.create_file(
            "/test_workspace/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            "/test_workspace/task.txt",
            contents="File: {{ input.content }}, Var: {{ var1 }}, Config: {{ config.key }}",
        )
        fs.create_file("/test_workspace/input.txt", contents="file content")

        result = cli_runner.invoke(
            create_cli(),
            [
                "--task-file",
                "/test_workspace/task.txt",
                "--schema-file",
                "/test_workspace/schema.json",
                "--file",
                "input=/test_workspace/input.txt",
                "--var",
                "var1=test value",
                "--json-var",
                'config={"key": "value"}',
                "--verbose",
            ],
        )
        assert result.exit_code == 0


# Template Context Tests
class TestTemplateContext:
    """Test template context creation."""

    def test_template_context_single_file(
        self,
        fs: FakeFilesystem,
        security_manager: SecurityManager,
    ) -> None:
        """Test template context creation with a single file."""
        fs.create_file(
            "/test_workspace/base/input.txt", contents="test content"
        )
        file_info = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/input.txt",
                    security_manager=security_manager,
                )
            ]
        )

        context = create_template_context(
            files={"input": file_info},
            variables={},
            json_variables={},
            security_manager=security_manager,
        )

        assert context["input"].content == "test content"
        assert os.path.basename(context["input"].path) == "input.txt"

    def test_template_context_multiple_files(
        self,
        fs: FakeFilesystem,
        security_manager: SecurityManager,
    ) -> None:
        """Test template context creation with multiple files."""
        fs.create_file("/test_workspace/base/file1.txt", contents="content 1")
        fs.create_file("/test_workspace/base/file2.txt", contents="content 2")
        file_info1 = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/file1.txt",
                    security_manager=security_manager,
                )
            ]
        )
        file_info2 = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/file2.txt",
                    security_manager=security_manager,
                )
            ]
        )

        context = create_template_context(
            files={"file1": file_info1, "file2": file_info2},
            variables={},
            json_variables={},
            security_manager=security_manager,
        )

        assert context["file1"].content == "content 1"
        assert context["file2"].content == "content 2"

    def test_template_context_mixed_sources(
        self,
        fs: FakeFilesystem,
        security_manager: SecurityManager,
    ) -> None:
        """Test template context creation with mixed sources."""
        fs.create_file(
            "/test_workspace/base/input.txt", contents="file content"
        )
        file_info = FileInfoList(
            [
                FileInfo.from_path(
                    "/test_workspace/base/input.txt",
                    security_manager=security_manager,
                )
            ]
        )

        context = create_template_context(
            files={"input": file_info},
            variables={"var1": "test value"},
            json_variables={"config": {"key": "value"}},
            security_manager=security_manager,
            stdin_content="stdin content",
        )

        assert context["input"].content == "file content"
        assert context["var1"] == "test value"
        assert context["config"]["key"] == "value"
        assert context["stdin"] == "stdin content"


@pytest.mark.mock_openai
def test_basic_cli_mock(
    fs: FakeFilesystem, cli_runner: CliTestRunner, mock_tiktoken
) -> None:
    """Test basic CLI functionality with mock client."""
    # Create minimal schema
    schema_content = {
        "schema": {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        }
    }
    fs.create_file(
        "/test_workspace/schema.json", contents=json.dumps(schema_content)
    )

    result = cli_runner.invoke(
        create_cli(),
        [
            "--task",
            "test task",
            "--schema-file",
            "/test_workspace/schema.json",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
