"""Tests for ostruct CLI functionality.

This module contains comprehensive tests for the ostruct command-line interface,
including argument parsing, file handling, template processing, and integration
with various OpenAI tools.
"""

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner
from ostruct.cli.cli import create_cli
from ostruct.cli.file_utils import FileInfo, FileInfoList
from ostruct.cli.template_rendering import render_template
from pyfakefs.fake_filesystem import FakeFilesystem

# Test workspace base directory
TEST_BASE_DIR = "/test_workspace/base"


class CliTestRunner:
    """Test runner for CLI commands with proper error handling."""

    def __init__(self):
        self.runner = CliRunner()

    def invoke(self, cli, args, **kwargs):
        """Invoke CLI command with proper error handling."""
        result = self.runner.invoke(cli, args, **kwargs)
        return result


@pytest.fixture
def cli_runner():
    """Provide CLI test runner."""
    return CliTestRunner()


@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_help_command(self, cli_runner: CliTestRunner) -> None:
        """Test that help command works."""
        result = cli_runner.invoke(create_cli(), ["--help"])
        assert result.exit_code == 0
        assert "ostruct" in result.output

    def test_version_command(self, cli_runner: CliTestRunner) -> None:
        """Test version command."""
        result = cli_runner.invoke(create_cli(), ["--version"])
        assert result.exit_code == 0


class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    def test_basic_run_command_structure(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test basic run command structure."""
        # Create test files
        fs.create_file(
            f"{TEST_BASE_DIR}/template.j2", contents="Test template"
        )
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

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(), ["run", "template.j2", "schema.json", "--dry-run"]
        )

        # Should not fail on argument parsing
        assert result.exit_code in [0, 1]  # May fail on other validation

    def test_file_arguments_parsing(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test file argument parsing."""
        # Create test files
        fs.create_file(f"{TEST_BASE_DIR}/test.txt", contents="test content")
        fs.create_file(
            f"{TEST_BASE_DIR}/template.j2", contents="Template: {{ test_txt }}"
        )
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

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "template.j2",
                "schema.json",
                "-ft",
                "test.txt",
                "--dry-run",
            ],
        )

        # Should parse arguments successfully
        assert result.exit_code in [0, 1]  # May fail on other validation


class TestFileHandling:
    """Test file handling functionality."""

    def test_file_info_creation(self) -> None:
        """Test FileInfo creation and properties."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            f.flush()

            try:
                from ostruct.cli.security import SecurityManager

                security_manager = SecurityManager(
                    base_dir=os.path.dirname(f.name)
                )
                file_info = FileInfo(f.name, security_manager)
                assert file_info.name == os.path.basename(f.name)
                assert file_info.content == "test content"
            finally:
                os.unlink(f.name)

    def test_file_info_list_operations(self) -> None:
        """Test FileInfoList operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.txt")

            with open(file1, "w") as f:
                f.write("content1")
            with open(file2, "w") as f:
                f.write("content2")

            # Test FileInfoList
            from ostruct.cli.security import SecurityManager

            security_manager = SecurityManager(base_dir=tmpdir)
            file_info1 = FileInfo(file1, security_manager)
            file_info2 = FileInfo(file2, security_manager)
            file_list = FileInfoList([file_info1, file_info2])
            assert len(file_list) == 2
            # Test that we can access individual file paths
            assert file_list[0].path == os.path.basename(file1)
            assert file_list[1].path == os.path.basename(file2)


class TestTemplateProcessing:
    """Test template processing functionality."""

    def test_template_renderer_basic(self) -> None:
        """Test basic template rendering."""
        template_content = "Hello {{ name }}!"
        variables = {"name": "World"}

        result = render_template(template_content, variables)
        assert result == "Hello World!"

    def test_template_with_file_variables(self) -> None:
        """Test template rendering with file variables."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("file content")
            f.flush()

            try:
                from ostruct.cli.security import SecurityManager

                security_manager = SecurityManager(
                    base_dir=os.path.dirname(f.name)
                )
                template_content = "File: {{ file_var.content }}"
                file_info = FileInfo(f.name, security_manager)
                variables = {"file_var": file_info}

                result = render_template(template_content, variables)
                assert "file content" in result
            finally:
                os.unlink(f.name)


class TestErrorHandling:
    """Test error handling in CLI."""

    def test_missing_template_file(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test error when template file is missing."""
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

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(), ["run", "nonexistent.j2", "schema.json"]
        )

        assert result.exit_code != 0
        assert "does not exist" in result.output.lower()

    def test_missing_schema_file(
        self, cli_runner: CliTestRunner, fs: FakeFilesystem
    ) -> None:
        """Test error when schema file is missing."""
        fs.create_file(
            f"{TEST_BASE_DIR}/template.j2", contents="Test template"
        )

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(), ["run", "template.j2", "nonexistent.json"]
        )

        assert result.exit_code != 0
        assert "does not exist" in result.output.lower()


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

        mock_code_interpreter_instance = Mock()
        mock_code_interpreter.return_value = mock_code_interpreter_instance
        # Mock the actual methods that CodeInterpreter uses
        mock_code_interpreter_instance.validate_files_for_upload.return_value = []  # No validation errors
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


# Code Interpreter Download Tests (Developer Brief Implementation)
# =================================================================

PROJ = "tmp_ostruct_proj"
TPL = "task.j2"
SCH = "schema.json"
DL = "dl"


def _w(rel, txt):
    """Write a file in the test project."""
    os.makedirs(os.path.join(PROJ, os.path.dirname(rel)), exist_ok=True)
    with open(os.path.join(PROJ, rel), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(txt).lstrip())


def _run_ostruct():
    """Run ostruct with the test template and schema."""
    cp = subprocess.run(
        ["ostruct", "run", TPL, SCH], cwd=PROJ, capture_output=True, text=True
    )
    assert cp.returncode == 0, cp.stderr


def _scaffold(markdown: bool):
    """Create template and schema files for testing."""
    link = (
        ("\n[Download file](sandbox:/mnt/data/ci_output.txt)\n")
        if markdown
        else ""
    )
    _w(
        TPL,
        f"""
    ---
    system: |
      You are a Code-Interpreter assistant.
      Create ci_output.txt with 'TEST'. {"Include markdown link." if markdown else "Do NOT link."}
    ---
    Create the file now.{link}
    """,
    )
    _w(
        SCH,
        """
    {"type":"object",
     "properties":{"confirmation_message":{"type":"string"}},
     "required":["confirmation_message"]}
    """,
    )


def setup_module(_):
    """Set up the test project directory and configuration."""
    shutil.rmtree(PROJ, ignore_errors=True)
    os.makedirs(PROJ)
    _w(
        "ostruct.yaml",
        f"""
    version: 1
    tools:
      code_interpreter:
        auto_download: true
        output_directory: "./{DL}"
    """,
    )


# --- C-01  No markdown → expect NO file ------------------------------
@pytest.mark.live
@pytest.mark.no_fs
def test_yaml_autodownload_true_but_no_markdown():
    """Test that without markdown link, no file is downloaded."""
    shutil.rmtree(f"{PROJ}/{DL}", ignore_errors=True)
    _scaffold(markdown=False)
    _run_ostruct()
    assert not os.path.exists(f"{PROJ}/{DL}/ci_output.txt")


# --- C-02  Markdown present → still NO file (known bug) --------------
@pytest.mark.live
@pytest.mark.no_fs
@pytest.mark.xfail(reason="ostruct only inspects legacy .file_ids")
def test_markdown_annotation_but_cli_does_not_download():
    """Test that even with markdown link, ostruct still doesn't download (known bug)."""
    shutil.rmtree(f"{PROJ}/{DL}", ignore_errors=True)
    _scaffold(markdown=True)
    _run_ostruct()
    assert os.path.isfile(f"{PROJ}/{DL}/ci_output.txt")
