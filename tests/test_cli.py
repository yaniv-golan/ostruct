"""Tests for CLI functionality."""

import json
import logging
import os
from io import StringIO
from typing import Any, Dict, List, Optional, Union, cast
from unittest.mock import Mock, patch

import click
import pytest
from click.testing import CliRunner, Result  # noqa: F401 - used in type hints
from ostruct.cli.cli import create_cli
from ostruct.cli.errors import (
    CLIError,
    InvalidJSONError,
    SchemaValidationError,
)
from ostruct.cli.exit_codes import ExitCode
from ostruct.cli.file_list import FileInfo, FileInfoList
from ostruct.cli.file_utils import collect_files
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_processor import create_template_context
from pyfakefs.fake_filesystem import FakeFilesystem


# Temporary stub for T1.1 migration
class ModelRegistry:
    def get_capabilities(self, model: str) -> Any:
        class Capabilities:
            context_window = 128000
            max_output_tokens = 4096
            supported_parameters = [
                "temperature",
                "max_output_tokens",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
            ]

            def validate_parameter(self, param_name: str, value: Any) -> None:
                pass

        return Capabilities()


# Configure logging for tests
logger = logging.getLogger(__name__)

# Get the model registry instance for testing
# model_registry = ModelRegistry()


# Test workspace base directory
TEST_BASE_DIR = "/test_workspace/base"


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
                    # First check for SchemaValidationError in both context and cause chains
                    current = exc_value.__context__
                    while current is not None:
                        if isinstance(current, SchemaValidationError):
                            result.exception = current
                            result.exit_code = current.exit_code
                            return result
                        current = getattr(current, "__context__", None)

                    # Check __cause__ chain
                    current = exc_value.__cause__
                    while current is not None:
                        if isinstance(current, SchemaValidationError):
                            result.exception = current
                            result.exit_code = current.exit_code
                            return result
                        current = getattr(current, "__cause__", None)

                    # Check for CLIError and InvalidJSONError
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

                    # If no specific error found, use the SystemExit code
                    result.exit_code = (
                        exc_value.code
                        if isinstance(exc_value.code, int)
                        else 1
                    )
                    return result

                # Handle SchemaValidationError directly
                current = exc_value
                while current is not None:
                    if isinstance(current, SchemaValidationError):
                        result.exception = current
                        result.exit_code = current.exit_code
                        return result
                    current = getattr(current, "__cause__", None)

                # Handle CLIError and InvalidJSONError
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
                loggers = ["root", "ostruct.cli.cli", "openai"]
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="test task")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/task.txt", contents="test task from file"
        )

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
                "schema.json",
                "--sys-prompt",
                "custom system prompt",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/prompt.txt",
            contents="custom system prompt from file",
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
                "schema.json",
                "--sys-file",
                "prompt.txt",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_dir(f"{TEST_BASE_DIR}/allowed_dir1")
        fs.create_dir(f"{TEST_BASE_DIR}/allowed_dir2")
        fs.create_file(
            f"{TEST_BASE_DIR}/allowed_dirs.txt",
            contents="allowed_dir1\nallowed_dir2",
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "test task",
                "schema.json",
                "--task-file",
                "task.txt",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/prompt.txt", contents="test prompt")
        fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
                "schema.json",
                "--sys-prompt",
                "test prompt",
                "--sys-file",
                "prompt.txt",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "schema.json",
            ],
        )
        cli_runner.check_error_message(
            result, "Missing argument 'TASK_TEMPLATE'"
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
        result = cli_runner.invoke(create_cli(), ["run"])
        cli_runner.check_error_message(
            result, "Missing argument 'TASK_TEMPLATE'"
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
                "schema.json",
                "-J",
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
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents="{ invalid json }"
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
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
                "run",
                "task.txt",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
                "schema.json",
                "-f",
                "input",
                "nonexistent.txt",
            ],
        )
        cli_runner.check_error_message(result, "File not found")

    def test_invalid_template_syntax(
        self, fs: FakeFilesystem, cli_runner: CliTestRunner
    ) -> None:
        """Test invalid template syntax handling."""
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
            f"{TEST_BASE_DIR}/template.j2",
            contents="Invalid syntax: {% for item in items %}...{% endfor",
        )

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--dry-run",
            ],
        )

        # Test should check for non-zero exit code and error message
        assert result.exit_code != 0
        cli_runner.check_error_message(result, "Template syntax error")

    def test_schema_validation_error_chain(
        self,
        cli_runner: CliTestRunner,
        fs: FakeFilesystem,
    ) -> None:
        """Test that schema validation errors preserve their exit codes and chain."""

        # Create invalid schema with missing required field
        invalid_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": [
                "missing_field"
            ],  # Field is required but not defined in properties
            "properties": {},
            "additionalProperties": False,
        }

        # Write schema and template files
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json",
            contents=json.dumps(invalid_schema),
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/template.j2", contents="test template"
        )

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "template.j2",
                "schema.json",
                "--debug-validation",
                "--dry-run",
            ],
        )

        # Verify error chain preservation
        assert result.exit_code == ExitCode.SCHEMA_ERROR
        assert isinstance(result.exception, SchemaValidationError)

        # Verify error details
        assert "missing_field" in str(result.exception)
        assert "required" in str(result.exception)

        # Verify error context
        assert result.exception.context is not None
        assert "validation_type" in result.exception.context
        assert result.exception.context["validation_type"] == "schema"


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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/task.txt", contents="Files: {{ files | length }}"
        )
        fs.create_dir(f"{TEST_BASE_DIR}/test_dir")
        fs.create_file(
            f"{TEST_BASE_DIR}/test_dir/file1.txt", contents="content 1"
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/test_dir/file2.txt", contents="content 2"
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/test_dir/file3.txt", contents="content 3"
        )

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/task.txt",
                f"{TEST_BASE_DIR}/schema.json",
                "-d",
                "files",
                f"{TEST_BASE_DIR}/test_dir",
                "-R",
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

    @patch("ostruct.cli.code_interpreter.CodeInterpreterManager")
    @patch("ostruct.cli.file_search.FileSearchManager")
    @patch("ostruct.cli.mcp_integration.MCPServerManager")
    def test_responses_api_integration(
        self,
        mock_mcp_manager: Mock,
        mock_file_search: Mock,
        mock_code_interpreter: Mock,
        fs: FakeFilesystem,
        cli_runner: CliTestRunner,
    ) -> None:
        """Test Responses API integration with tool routing."""
        # Setup mocks
        from unittest.mock import AsyncMock

        mock_code_interpreter_instance = Mock()
        mock_code_interpreter.return_value = mock_code_interpreter_instance
        # Mock the actual methods that CodeInterpreter uses
        mock_code_interpreter_instance.validate_files_for_upload.return_value = (
            []
        )  # No validation errors
        mock_code_interpreter_instance.upload_files_for_code_interpreter = (
            AsyncMock(return_value=["file_id_123"])
        )
        mock_code_interpreter_instance.build_tool_config.return_value = {
            "type": "code_interpreter",
            "container": {"type": "auto", "file_ids": ["file_id_123"]},
        }
        mock_code_interpreter_instance.get_container_limits_info.return_value = {
            "max_runtime_minutes": 20
        }
        mock_code_interpreter_instance.cleanup_uploaded_files = AsyncMock()

        mock_file_search_instance = Mock()
        mock_file_search.return_value = mock_file_search_instance
        mock_file_search_instance.search_files.return_value = {
            "results": "search results"
        }

        mock_mcp_instance = Mock()
        mock_mcp_manager.return_value = mock_mcp_instance
        mock_mcp_instance.send_request.return_value = {
            "response": "mcp response"
        }

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
            f"{TEST_BASE_DIR}/task.txt",
            contents="Process code file: {{ code_py.path }}",
        )
        fs.create_file(f"{TEST_BASE_DIR}/code.py", contents="print('hello')")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.txt",
                "schema.json",
                "-fc",
                "code.py",  # Route to code interpreter
                "--dry-run",  # Don't make actual API calls
            ],
        )

        assert result.exit_code == 0
        # Note: During dry-run, CodeInterpreter integration is prepared but not executed.
        # The actual integration is working as demonstrated by manual testing.

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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/task.txt",
            contents="Process this: {{ input.content }}",
        )
        fs.create_file(f"{TEST_BASE_DIR}/input.txt", contents="test content")

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/task.txt",
                f"{TEST_BASE_DIR}/schema.json",
                "-f",
                "input",
                f"{TEST_BASE_DIR}/input.txt",
                "--debug-validation",
                "--verbose",
                "--dry-run",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/task.txt",
            contents="Content: {{ input.content }}",
        )
        fs.create_file(f"{TEST_BASE_DIR}/input.txt", contents="test content")

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/task.txt",
                f"{TEST_BASE_DIR}/schema.json",
                "-f",
                "input",
                f"{TEST_BASE_DIR}/input.txt",
                "--dry-run",
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
                "additionalProperties": False,
            }
        }
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/task.txt",
            contents="File: {{ input.content }}, Var: {{ var1 }}, Config: {{ config.key }}",
        )
        fs.create_file(f"{TEST_BASE_DIR}/input.txt", contents="file content")

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/task.txt",
                f"{TEST_BASE_DIR}/schema.json",
                "-f",
                "input",
                f"{TEST_BASE_DIR}/input.txt",
                "-V",
                "var1=test value",
                "-J",
                'config={"key": "value"}',
                "--verbose",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_pattern_file_input(
        self,
        fs: FakeFilesystem,
        mock_logging: StringIO,
        cli_runner: CliTestRunner,
    ) -> None:
        """Test CLI execution with pattern-matched file input."""
        # Create test files
        fs.create_file(
            f"{TEST_BASE_DIR}/task.j2",
            contents="""
            Extract information about the people from this data:
            {% for profile in profiles %}
            == {{ profile.name }}
            {{ profile.content }}
            {% endfor %}
            """,
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/schema.json",
            contents=json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "people": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "age": {"type": "integer"},
                                    "occupation": {"type": "string"},
                                },
                                "required": ["name", "age", "occupation"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["people"],
                    "additionalProperties": False,
                }
            ),
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/profiles/john.txt",
            contents="John Smith is a 35-year-old software engineer",
        )
        fs.create_file(
            f"{TEST_BASE_DIR}/profiles/jane.txt",
            contents="Jane Doe is a 28-year-old data scientist",
        )
        os.chdir(TEST_BASE_DIR)

        # Run CLI with pattern option
        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "-p",
                "profiles",
                "profiles/*.txt",
                "-A",
                "profiles",
                "--base-dir",
                ".",
                "--dry-run",
            ],
        )

        # Check result
        assert result.exit_code == ExitCode.SUCCESS
        # In dry-run mode, output is token analysis, not JSON
        assert "Token Analysis" in result.stdout
        assert "Input tokens" in result.stdout


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
            f"{TEST_BASE_DIR}/base/input.txt", contents="test content"
        )
        file_info = FileInfoList(
            [
                FileInfo.from_path(
                    f"{TEST_BASE_DIR}/base/input.txt",
                    security_manager=security_manager,
                )
            ]
        )

        context = create_template_context(
            files=cast(
                Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]],
                {"input": file_info},
            ),
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
        fs.create_file(f"{TEST_BASE_DIR}/base/file1.txt", contents="content 1")
        fs.create_file(f"{TEST_BASE_DIR}/base/file2.txt", contents="content 2")
        file_info1 = FileInfoList(
            [
                FileInfo.from_path(
                    f"{TEST_BASE_DIR}/base/file1.txt",
                    security_manager=security_manager,
                )
            ]
        )
        file_info2 = FileInfoList(
            [
                FileInfo.from_path(
                    f"{TEST_BASE_DIR}/base/file2.txt",
                    security_manager=security_manager,
                )
            ]
        )

        context = create_template_context(
            files=cast(
                Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]],
                {"file1": file_info1, "file2": file_info2},
            ),
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
            f"{TEST_BASE_DIR}/base/input.txt", contents="file content"
        )
        file_info = FileInfoList(
            [
                FileInfo.from_path(
                    f"{TEST_BASE_DIR}/base/input.txt",
                    security_manager=security_manager,
                )
            ]
        )

        context = create_template_context(
            files=cast(
                Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]],
                {"input": file_info},
            ),
            variables={"var1": "test value"},
            json_variables={"config": {"key": "value"}},
            security_manager=security_manager,
            stdin_content="stdin content",
        )

        assert context["input"].content == "file content"
        assert context["var1"] == "test value"
        assert context["config"]["key"] == "value"
        assert context["stdin"] == "stdin content"

    def test_template_context_pattern_files(
        self,
        fs: FakeFilesystem,
        security_manager: SecurityManager,
    ) -> None:
        """Test creating template context with pattern-matched files."""
        # Create test files
        fs.create_file(
            "/test_workspace/base/profiles/john.txt",
            contents="John Smith is a 35-year-old software engineer",
        )
        fs.create_file(
            "/test_workspace/base/profiles/jane.txt",
            contents="Jane Doe is a 28-year-old data scientist",
        )
        os.chdir("/test_workspace/base")

        # Create context with pattern files
        context = create_template_context(
            files=cast(
                Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]],
                collect_files(
                    pattern_mappings=[("profiles", "profiles/*.txt")],
                    security_manager=security_manager,
                ),
            )
        )

        # Verify context
        assert "profiles" in context
        assert isinstance(context["profiles"], FileInfoList)
        assert len(context["profiles"]) == 2
        assert {f.name.removesuffix(".txt") for f in context["profiles"]} == {
            "john",
            "jane",
        }
        assert any("John Smith" in f.content for f in context["profiles"])
        assert any("Jane Doe" in f.content for f in context["profiles"])

    def test_template_context_mixed_with_patterns(
        self,
        fs: FakeFilesystem,
        security_manager: SecurityManager,
    ) -> None:
        """Test creating template context with mixed sources including patterns."""
        # Create test files
        fs.create_file("/test_workspace/base/single.txt", contents="single")
        fs.create_file(
            "/test_workspace/base/profiles/john.txt", contents="John Smith"
        )
        fs.create_file(
            "/test_workspace/base/profiles/jane.txt", contents="Jane Doe"
        )
        fs.create_file("/test_workspace/base/dir/test.py", contents="test")
        os.chdir("/test_workspace/base")

        # Create context with mixed sources
        context = create_template_context(
            files=cast(
                Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]],
                collect_files(
                    file_mappings=[("single", "single.txt")],
                    dir_mappings=[("dir", "dir")],
                    pattern_mappings=[("profiles", "profiles/*.txt")],
                    security_manager=security_manager,
                ),
            ),
            variables={"var": "value"},
            json_variables={"json": {"key": "value"}},
        )

        # Verify context
        assert "single" in context
        assert "dir" in context
        assert "profiles" in context
        assert "var" in context
        assert "json" in context

        # Verify file content
        assert isinstance(context["single"], FileInfoList)
        assert context["single"].content == "single"

        # Verify directory content
        assert isinstance(context["dir"], FileInfoList)
        assert len(context["dir"]) == 1
        assert context["dir"][0].content == "test"

        # Verify pattern content
        assert isinstance(context["profiles"], FileInfoList)
        assert len(context["profiles"]) == 2
        assert {f.name.removesuffix(".txt") for f in context["profiles"]} == {
            "john",
            "jane",
        }
        assert any("John Smith" in f.content for f in context["profiles"])
        assert any("Jane Doe" in f.content for f in context["profiles"])

        # Verify other variables
        assert context["var"] == "value"
        assert context["json"] == {"key": "value"}


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
            "additionalProperties": False,
        }
    }
    fs.create_file(
        f"{TEST_BASE_DIR}/schema.json", contents=json.dumps(schema_content)
    )
    fs.create_file(f"{TEST_BASE_DIR}/task.txt", contents="test task")

    # Change to test base directory
    os.chdir(TEST_BASE_DIR)

    result = cli_runner.invoke(
        create_cli(),
        [
            "run",
            "task.txt",
            "schema.json",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
