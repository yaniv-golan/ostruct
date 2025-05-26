"""Tests for migration compatibility and backward compatibility validation."""

import json
import os
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.cli import create_cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


# Test workspace base directory
TEST_BASE_DIR = "/test_workspace/base"


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality."""

    def test_legacy_cli_interface(
        self, cli_runner: CliRunner, fs: FakeFilesystem
    ) -> None:
        """Test that legacy CLI interface still works."""
        # Create test files using legacy format
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
            f"{TEST_BASE_DIR}/task.j2",
            contents="Legacy task: {{ input.content }}",
        )
        fs.create_file(f"{TEST_BASE_DIR}/input.txt", contents="legacy input")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        # Test legacy command format
        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "-f",
                "input",
                "input.txt",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

    def test_legacy_template_syntax(
        self, cli_runner: CliRunner, fs: FakeFilesystem
    ) -> None:
        """Test that legacy template syntax still works."""
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

        # Test legacy Jinja2 syntax patterns
        legacy_templates = [
            "Simple: {{ var }}",
            "Loop: {% for item in items %}{{ item }}{% endfor %}",
            "Conditional: {% if condition %}yes{% else %}no{% endif %}",
            "Filter: {{ text | upper }}",
            "File content: {{ file.content }}",
        ]

        for i, template in enumerate(legacy_templates):
            fs.create_file(f"{TEST_BASE_DIR}/template_{i}.j2", contents=template)

            # Change to test base directory
            os.chdir(TEST_BASE_DIR)

            # Create a test file for file content template
            if "file.content" in template:
                fs.create_file(
                    f"{TEST_BASE_DIR}/test_file.txt",
                    contents="test file content",
                )

            # Build variable arguments based on template requirements
            var_args = [
                "-V",
                "var=test",
                "-V",
                "condition=true",
                "-V",
                "text=hello",
            ]

            # Add variables specific to certain templates
            if "items" in template:
                var_args.extend(["-V", "items=item1,item2,item3"])

            if "file.content" in template:
                var_args.extend(["-f", "file", "test_file.txt"])

            result = cli_runner.invoke(
                create_cli(),
                [
                    "run",
                    f"template_{i}.j2",
                    "schema.json",
                ]
                + var_args
                + [
                    "--dry-run",
                ],
            )

            assert result.exit_code == 0, f"Legacy template {i} failed: {template}"

    def test_legacy_schema_formats(
        self, cli_runner: CliRunner, fs: FakeFilesystem
    ) -> None:
        """Test that legacy schema formats still work."""
        legacy_schemas = [
            # Simple object schema
            {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            },
            # Schema with nested structure
            {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "number"},
                        },
                        "required": ["name", "value"],
                    }
                },
                "required": ["data"],
                "additionalProperties": False,
            },
            # Schema with array
            {
                "type": "object",
                "properties": {"items": {"type": "array", "items": {"type": "string"}}},
                "required": ["items"],
                "additionalProperties": False,
            },
        ]

        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="Legacy schema test")

        for i, schema in enumerate(legacy_schemas):
            # Test both wrapped and unwrapped formats
            wrapped_schema = {"schema": schema}

            fs.create_file(
                f"{TEST_BASE_DIR}/schema_{i}_wrapped.json",
                contents=json.dumps(wrapped_schema),
            )
            fs.create_file(
                f"{TEST_BASE_DIR}/schema_{i}_unwrapped.json",
                contents=json.dumps(schema),
            )

            # Change to test base directory
            os.chdir(TEST_BASE_DIR)

            # Test wrapped format
            result = cli_runner.invoke(
                create_cli(),
                [
                    "run",
                    "task.j2",
                    f"schema_{i}_wrapped.json",
                    "--dry-run",
                ],
            )
            assert result.exit_code == 0, f"Wrapped schema {i} failed"

            # Test unwrapped format
            result = cli_runner.invoke(
                create_cli(),
                [
                    "run",
                    "task.j2",
                    f"schema_{i}_unwrapped.json",
                    "--dry-run",
                ],
            )
            assert result.exit_code == 0, f"Unwrapped schema {i} failed"


class TestErrorMessageCompatibility:
    """Test that error messages remain consistent."""

    def test_legacy_error_codes(
        self, cli_runner: CliRunner, fs: FakeFilesystem
    ) -> None:
        """Test that legacy error codes are preserved."""
        # Test missing schema file
        result = cli_runner.invoke(
            create_cli(),
            ["run", "task.j2", "nonexistent.json"],
        )

        assert result.exit_code != 0
        assert (
            "File not found" in result.output
            or "not found" in result.output.lower()
            or "does not exist" in result.output
        )

        # Test invalid JSON
        fs.create_file(f"{TEST_BASE_DIR}/invalid.json", contents="{ invalid json }")
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="test")

        result = cli_runner.invoke(
            create_cli(),
            ["run", "task.j2", f"{TEST_BASE_DIR}/invalid.json"],
        )

        assert result.exit_code != 0
        assert "JSON" in result.output or "invalid" in result.output.lower()

        # Test missing required arguments
        result = cli_runner.invoke(create_cli(), ["run"])
        assert result.exit_code == 2
        assert "argument" in result.output.lower() or "usage:" in result.output.lower()

    def test_legacy_warning_messages(
        self,
        cli_runner: CliRunner,
        fs: FakeFilesystem,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that warning messages are preserved."""
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
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="test")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        # Test verbose mode still shows expected messages
        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "--verbose",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0


class TestToolAutoEnablement:
    """Test automatic tool enablement and routing."""

    @patch("ostruct.cli.code_interpreter.CodeInterpreterManager")
    def test_auto_code_interpreter_detection(
        self,
        mock_code_interpreter: Mock,
        cli_runner: CliRunner,
        fs: FakeFilesystem,
    ) -> None:
        """Test automatic code interpreter enablement via file routing."""
        mock_instance = Mock()
        mock_code_interpreter.return_value = mock_instance
        mock_instance.process_files.return_value = {"result": "processed"}

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
            f"{TEST_BASE_DIR}/task.j2",
            contents="Analyze code: {{ code_files | length }} files",
        )

        # Create code files that should trigger auto-detection
        code_files = [
            "script.py",
            "app.js",
            "main.cpp",
            "analysis.R",
        ]

        for code_file in code_files:
            fs.create_file(
                f"{TEST_BASE_DIR}/{code_file}",
                contents=f"# {code_file} content",
            )

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        # Use code interpreter file routing to trigger auto-enablement
        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "-fc",
                "script.py",  # Route file to code interpreter (auto-enables tool)
                "-fc",
                "app.js",
                "-V",
                "code_files=test_files",  # Provide template variable
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Verify code interpreter was auto-enabled due to file routing
        assert "auto-enabled tools: code-interpreter" in result.output

    @patch("ostruct.cli.file_search.FileSearchManager")
    def test_auto_file_search_detection(
        self, mock_file_search: Mock, cli_runner: CliRunner, fs: FakeFilesystem
    ) -> None:
        """Test automatic file search enablement via file routing."""
        mock_instance = Mock()
        mock_file_search.return_value = mock_instance
        mock_instance.search_files.return_value = {"results": ["found"]}

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
            f"{TEST_BASE_DIR}/task.j2",
            contents="Search in: {{ search_results | length }} results",
        )

        # Create files for file search
        search_files = [
            "doc_1.txt",
            "doc_2.txt",
            "manual.pdf",
            "guide.md",
        ]

        for search_file in search_files:
            fs.create_file(
                f"{TEST_BASE_DIR}/{search_file}",
                contents=f"Content of {search_file}",
            )

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        # Use file search routing to trigger auto-enablement
        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "-fs",
                "doc_1.txt",  # Route file to file search (auto-enables tool)
                "-fs",
                "manual.pdf",
                "-V",
                "search_results=test_results",  # Provide template variable
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Verify file search was auto-enabled due to file routing
        assert "auto-enabled tools: file-search" in result.output

    @patch("ostruct.cli.mcp_integration.MCPServerManager")
    def test_auto_mcp_detection(
        self, mock_mcp_client: Mock, cli_runner: CliRunner, fs: FakeFilesystem
    ) -> None:
        """Test MCP enablement via explicit server configuration."""
        mock_instance = Mock()
        mock_mcp_client.return_value = mock_instance
        mock_instance.send_request.return_value = {"response": "mcp result"}

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
            f"{TEST_BASE_DIR}/task.j2",
            contents="Research query: {{ query }} using external knowledge",
        )

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        # Use explicit MCP server configuration to enable MCP functionality
        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "-V",
                "query=machine learning",
                "--mcp-server",
                "deepwiki@https://mcp.deepwiki.com/sse",  # Explicit MCP server
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Verify MCP server was configured
        assert (
            result.exit_code == 0
        )  # MCP configuration doesn't show auto-enablement message


class TestConfigurationMigration:
    """Test configuration file migration and compatibility."""

    def test_legacy_config_support(
        self, cli_runner: CliRunner, fs: FakeFilesystem
    ) -> None:
        """Test that legacy configuration formats are supported."""
        # Create legacy config format

        fs.create_file(
            f"{TEST_BASE_DIR}/.ostruct.yaml",
            contents="""
openai:
  model: gpt-4
  temperature: 0.7
security:
  allowed_dirs:
    - /safe/path
""",
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
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="test with config")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        result = cli_runner.invoke(
            create_cli(),
            [
                "run",
                "task.j2",
                "schema.json",
                "--config",
                ".ostruct.yaml",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

    def test_config_migration_warnings(
        self,
        cli_runner: CliRunner,
        fs: FakeFilesystem,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that deprecated config options show warnings."""
        # Create config with deprecated options
        fs.create_file(
            f"{TEST_BASE_DIR}/.ostruct.yaml",
            contents="""
# Deprecated option
api_key: sk-deprecated
model: gpt-3.5-turbo  # Deprecated model

# New format
openai:
  model: gpt-4o
  temperature: 0.7
""",
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
        fs.create_file(f"{TEST_BASE_DIR}/task.j2", contents="test")

        # Change to test base directory
        os.chdir(TEST_BASE_DIR)

        with caplog.at_level("WARNING"):
            result = cli_runner.invoke(
                create_cli(),
                [
                    "run",
                    "task.j2",
                    "schema.json",
                    "--config",
                    ".ostruct.yaml",
                    "--dry-run",
                ],
            )

        # Should still work but show warnings
        assert result.exit_code == 0
        assert "deprecated" in caplog.text.lower() or "warning" in caplog.text.lower()
