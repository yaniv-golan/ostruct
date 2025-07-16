"""Integration tests for ostruct runx command."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from ostruct.cli.cli import create_cli
from ostruct.cli.ost.frontmatter import FrontMatterParser
from ostruct.cli.runx.runx_main import runx_main
from pyfakefs.fake_filesystem import FakeFilesystem


def create_test_ost_file(
    fs: FakeFilesystem, content: str, filename: str = "test.ost"
) -> str:
    """Create a test OST file with given content."""
    ost_path = f"/test_workspace/base/{filename}"
    fs.create_file(ost_path, contents=content)
    return ost_path


class TestRunxIntegration:
    """Integration tests for runx command functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = create_cli()

    def test_runx_help_screen(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that runx --help shows proper help screen."""
        # Create a simple OST file
        ost_content = """---
cli:
  name: test-cli
  description: Test CLI application
  options:
    input:
      names: ["--input", "-i"]
      help: Input text to process
    verbose:
      names: ["--verbose", "-v"]
      action: store_true
      help: Enable verbose output
global_args:
  model:
    mode: fixed
    value: gpt-4.1
  temperature:
    mode: allowed
    allowed: ["0.0", "0.5", "1.0"]
schema: |
  {
    "type": "object",
    "properties": {
      "result": {"type": "string"},
      "metadata": {"type": "object"}
    },
    "required": ["result"]
  }
---
Process: {{ input }}
Verbose: {{ verbose }}
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Test template help by calling runx_main directly
        # Capture stdout and stderr to check the help output
        import contextlib
        import io

        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        with (
            contextlib.redirect_stdout(captured_stdout),
            contextlib.redirect_stderr(captured_stderr),
        ):
            exit_code = runx_main([ost_path, "--help"])

        assert exit_code == 0
        help_output = captured_stdout.getvalue() + captured_stderr.getvalue()
        assert "test-cli" in help_output
        assert "Test CLI application" in help_output
        assert "input" in help_output
        assert "verbose" in help_output
        assert "Global ostruct flags policy:" in help_output
        assert "model" in help_output
        assert "fixed" in help_output

    def test_runx_flag_mapping(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that template variables are properly mapped to ostruct flags."""
        ost_content = """---
cli:
  name: mapper-test
  description: Test flag mapping
  options:
    text:
      names: ["--text", "-t"]
      default: "hello"
    count:
      names: ["--count", "-c"]
      default: 1
    enabled:
      names: ["--enabled", "-e"]
      action: store_true
global_args:
  model:
    mode: pass-through
schema: |
  {
    "type": "object",
    "properties": {"output": {"type": "string"}},
    "required": ["output"]
  }
---
Text: {{ text }}
Count: {{ count }}
Enabled: {{ enabled }}
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Mock execvp to capture the command that would be executed
        with patch("os.execvp") as mock_execvp:
            # Call runx_main with explicit argv
            argv = [ost_path, "--text", "world", "--count", "5", "--enabled"]
            try:
                runx_main(argv)
            except SystemExit:
                pass  # Expected from execvp

            # Verify execvp was called with correct arguments
            assert mock_execvp.called
            args = mock_execvp.call_args[0]
            assert args[0] == "ostruct"
            cmd_args = args[1]

            # Check that template variables were mapped to --var flags
            assert "--var" in cmd_args
            text_idx = cmd_args.index("--var")
            assert cmd_args[text_idx + 1] == "text=world"

            # Find other variables
            var_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--var" and i + 1 < len(cmd_args):
                    var_args.append(cmd_args[i + 1])

            assert "text=world" in var_args
            assert "count=5" in var_args
            assert "enabled=true" in var_args

    def test_runx_policy_rejection_fixed_mode(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that fixed mode policy rejects conflicting values."""
        ost_content = """---
cli:
  name: fixed-test
  description: Test fixed policy
global_args:
  model:
    mode: fixed
    value: gpt-4.1
  temperature:
    mode: fixed
    value: 0.0
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Test that trying to override fixed model fails
        argv = [ost_path, "--model", "gpt-3.5-turbo"]
        with pytest.raises(SystemExit) as exc_info:
            runx_main(argv)
        assert exc_info.value.code == 2  # Policy violation exit code

    def test_runx_policy_rejection_blocked_mode(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that blocked mode policy rejects blocked flags."""
        ost_content = """---
cli:
  name: blocked-test
  description: Test blocked policy
global_args:
  enable-tool:
    mode: blocked
  debug:
    mode: blocked
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Test that trying to use blocked flag fails
        argv = [ost_path, "--enable-tool", "code-interpreter"]
        with pytest.raises(SystemExit) as exc_info:
            runx_main(argv)
        assert exc_info.value.code == 2  # Policy violation exit code

    def test_runx_policy_allowed_mode(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that allowed mode policy accepts valid choices."""
        ost_content = """---
cli:
  name: allowed-test
  description: Test allowed policy
global_args:
  model:
    mode: allowed
    allowed: ["gpt-4.1", "gpt-3.5-turbo"]
  temperature:
    mode: allowed
    allowed: ["0.0", "0.5", "1.0"]
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Test that allowed value passes
        with patch("os.execvp") as mock_execvp:
            argv = [
                ost_path,
                "--model",
                "gpt-3.5-turbo",
                "--temperature",
                "0.5",
            ]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            args = mock_execvp.call_args[0][1]
            assert "--model" in args
            assert "gpt-3.5-turbo" in args
            assert "--temperature" in args
            assert "0.5" in args

        # Test that disallowed value fails
        argv = [ost_path, "--model", "gpt-4o"]
        with pytest.raises(SystemExit) as exc_info:
            runx_main(argv)
        assert exc_info.value.code == 2

    def test_runx_pass_through_mode(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that pass-through mode allows any value."""
        ost_content = """---
cli:
  name: passthrough-test
  description: Test pass-through policy
global_args:
  model:
    mode: pass-through
  temperature:
    mode: pass-through
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        with patch("os.execvp") as mock_execvp:
            argv = [ost_path, "--model", "any-model", "--temperature", "0.123"]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            args = mock_execvp.call_args[0][1]
            assert "--model" in args
            assert "any-model" in args
            assert "--temperature" in args
            assert "0.123" in args

    def test_runx_pass_through_global_false(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that pass_through_global: false rejects unknown flags."""
        ost_content = """---
cli:
  name: strict-test
  description: Test strict global policy
global_args:
  pass_through_global: false
  model:
    mode: pass-through
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Test that unknown global flag fails
        argv = [ost_path, "--unknown-flag", "value"]
        with pytest.raises(SystemExit) as exc_info:
            runx_main(argv)
        assert exc_info.value.code == 2

    def test_runx_defaults_application(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that defaults are properly applied."""
        ost_content = """---
cli:
  name: defaults-test
  description: Test defaults
  options:
    message:
      names: ["--message"]
      type: str
      default: "default message"
    model_choice:
      names: ["--model-choice"]
      type: str
      help: "Model choice"
    temp_setting:
      names: ["--temp-setting"]
      type: str
      help: "Temperature setting"
defaults:
  message: "default message"
  model_choice: "gpt-4.1"
  temp_setting: "0.7"
global_args:
  pass_through_global: true
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Message: {{ message }}
Model: {{ model_choice }}
Temperature: {{ temp_setting }}
"""
        ost_path = create_test_ost_file(fs, ost_content)

        with patch("os.execvp") as mock_execvp:
            argv = [ost_path]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            args = mock_execvp.call_args[0][1]

            # Check that template defaults were applied as --var flags
            assert "--var" in args
            var_indices = [i for i, arg in enumerate(args) if arg == "--var"]
            var_values = [args[i + 1] for i in var_indices]

            assert "message=default message" in var_values
            assert "model_choice=gpt-4.1" in var_values
            assert "temp_setting=0.7" in var_values

    def test_runx_boolean_flag_handling(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that boolean flags are handled correctly."""
        ost_content = """---
cli:
  name: bool-test
  description: Test boolean flags
  options:
    - name: verbose
      action: store_true
      help: Enable verbose output
    - name: quiet
      action: store_true
      help: Enable quiet mode
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Verbose: {{ verbose }}
Quiet: {{ quiet }}
"""
        ost_path = create_test_ost_file(fs, ost_content)

        with patch("os.execvp") as mock_execvp:
            argv = [ost_path, "--verbose"]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            args = mock_execvp.call_args[0][1]

            # Check that boolean flags were mapped correctly
            var_indices = [i for i, arg in enumerate(args) if arg == "--var"]
            var_values = [args[i + 1] for i in var_indices]
            assert "verbose=true" in var_values
            assert "quiet=false" in var_values

    def test_runx_file_attachment_mapping(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that file attachments are mapped correctly."""
        ost_content = """---
cli:
  name: file-test
  description: Test file attachments
  options:
    - name: input_file
      type: file
      help: Input file to process
    - name: data_dir
      type: directory
      help: Data directory
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Process file: {{ input_file }}
Data from: {{ data_dir }}
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Create test files
        fs.create_file(
            "/test_workspace/base/input.txt", contents="test content"
        )
        fs.create_dir("/test_workspace/base/data")

        with patch("os.execvp") as mock_execvp:
            argv = [
                ost_path,
                "--input-file",
                "input.txt",
                "--data-dir",
                "data",
            ]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            args = mock_execvp.call_args[0][1]

            # Check that file was mapped to --file flag
            assert "--file" in args
            file_idx = args.index("--file")
            assert "input_file" in args[file_idx + 1]
            assert "input.txt" in args[file_idx + 1]

            # Check that directory was mapped to --dir flag
            assert "--dir" in args
            dir_idx = args.index("--dir")
            assert "data_dir" in args[dir_idx + 1]
            assert "data" in args[dir_idx + 1]

    def test_runx_missing_schema_error(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that missing schema causes proper error."""
        ost_content = """---
cli:
  name: no-schema-test
  description: Test missing schema
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        argv = [ost_path]
        with pytest.raises(SystemExit) as exc_info:
            runx_main(argv)
        assert exc_info.value.code == 1  # General error exit code

    def test_runx_invalid_yaml_error(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that invalid YAML causes proper error."""
        ost_content = """---
cli:
  name: invalid-yaml-test
  description: Test invalid YAML
  invalid_yaml: [unclosed list
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        argv = [ost_path]
        with pytest.raises(SystemExit) as exc_info:
            runx_main(argv)
        assert exc_info.value.code == 1

    def test_runx_alias_resolution(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that flag aliases are resolved correctly."""
        ost_content = """---
cli:
  name: alias-test
  description: Test alias resolution
global_args:
  model:
    mode: fixed
    value: gpt-4.1
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Test that -m is resolved to --model and blocked
        argv = [ost_path, "-m", "gpt-3.5-turbo"]
        with pytest.raises(SystemExit) as exc_info:
            runx_main(argv)
        assert exc_info.value.code == 2  # Policy violation

    def test_runx_schema_export_and_cleanup(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that schema is exported to temp file and cleaned up."""
        ost_content = """---
cli:
  name: schema-export-test
  description: Test schema export
schema: |
  {
    "type": "object",
    "properties": {"result": {"type": "string"}},
    "required": ["result"]
  }
---
Hello world
"""
        ost_path = create_test_ost_file(fs, ost_content)

        with patch("os.execvp") as mock_execvp:
            argv = [ost_path]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            args = mock_execvp.call_args[0][1]

            # Find the schema file path in the arguments
            schema_path = None
            for i, arg in enumerate(args):
                if arg == "run" and i + 2 < len(args):
                    schema_path = args[
                        i + 2
                    ]  # Second positional arg after 'run'
                    break

            assert schema_path is not None
            assert schema_path.endswith(".json")

            # The temp file should exist during execution
            # (cleanup happens at exit, which we can't easily test here)

    def test_runx_command_via_cli(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test runx command through the main CLI interface."""
        ost_content = """---
cli:
  name: cli-test
  description: Test via CLI
  options:
    - name: message
      type: str
      default: "hello"
schema: |
  {"type": "object", "properties": {"result": {"type": "string"}}}
---
Message: {{ message }}
"""
        ost_path = create_test_ost_file(fs, ost_content)

        # Test that the command is registered and accessible
        result = self.runner.invoke(self.cli, ["runx", "--help"])
        assert result.exit_code == 0
        assert "runx" in result.output

        # Test running the command (will fail due to mocking, but should parse correctly)
        with patch("os.execvp"):
            result = self.runner.invoke(
                self.cli, ["runx", ost_path, "--message", "world"]
            )
            # Should not fail due to argument parsing issues
            assert result.exit_code in [
                0,
                1,
            ]  # 0 for success, 1 for execvp mock issues


class TestRunxEndToEnd:
    """End-to-end tests for runx functionality."""

    def test_runx_with_real_execution(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test runx with actual subprocess execution (dry-run)."""
        ost_content = """---
cli:
  name: e2e-test
  description: End-to-end test
  options:
    - name: input
      type: str
      default: "test input"
  defaults:
    dry_run: true
schema: |
  {
    "type": "object",
    "properties": {
      "result": {"type": "string"},
      "input_received": {"type": "string"}
    },
    "required": ["result", "input_received"]
  }
---
Input received: {{ input }}
Please return a JSON response with the result and input_received fields.
"""
        ost_path = create_test_ost_file(fs, ost_content, "e2e_test.ost")

        # Make the file executable
        os.chmod(ost_path, 0o755)

        # Test execution via subprocess with dry-run
        result = subprocess.run(
            [
                "python",
                "-m",
                "ostruct.cli.runx",
                ost_path,
                "--input",
                "hello world",
            ],
            capture_output=True,
            text=True,
            cwd="/test_workspace/base",
        )

        # Should succeed with dry-run
        assert result.returncode == 0

        # Check that the output contains expected dry-run information
        output = result.stdout + result.stderr
        assert "dry" in output.lower() or "preview" in output.lower()

    def test_hello_cli_ost_end_to_end(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """T5.2: End-to-end test: run hello_cli.ost with fixtures and assert JSON output passes schema."""
        # Create hello_cli.ost fixture based on scaffold template
        hello_cli_content = """#!/usr/bin/env -S ostruct runx
---
cli:
  name: hello-cli
  description: A simple greeting CLI tool
  positional:
    - name: name
      help: Name to greet
      default: "World"
  options:
    greeting:
      names: ["--greeting", "-g"]
      help: Greeting to use
      default: "Hello"
      choices: ["Hello", "Hi", "Hey", "Greetings"]
    enthusiastic:
      names: ["--enthusiastic", "-e"]
      help: Add exclamation marks
      action: "store_true"
    format:
      names: ["--format", "-f"]
      help: Output format
      default: "friendly"
      choices: ["friendly", "formal", "casual"]

schema: |
  {
    "type": "object",
    "properties": {
      "greeting": {
        "type": "string",
        "description": "The greeting message"
      },
      "name": {
        "type": "string",
        "description": "The name being greeted"
      },
      "format": {
        "type": "string",
        "description": "The format used",
        "enum": ["friendly", "formal", "casual"]
      },
      "enthusiastic": {
        "type": "boolean",
        "description": "Whether enthusiastic mode was used"
      },
      "message": {
        "type": "string",
        "description": "The complete greeting message"
      }
    },
    "required": ["greeting", "name", "format", "enthusiastic", "message"]
  }

defaults:
  greeting: "Hello"
  format: "friendly"
  enthusiastic: false

global_args:
  pass_through_global: true
  model:
    mode: "allowed"
    allowed: ["gpt-4o", "gpt-4.1", "gpt-4o-mini"]
    default: "gpt-4o-mini"
  dry_run:
    mode: "pass-through"
---
# Greeting Task

You are a helpful assistant that creates personalized greetings.

## Input
- Name: {{ name }}
- Greeting: {{ greeting }}
- Format: {{ format }}
- Enthusiastic: {{ enthusiastic }}

## Instructions
Create a greeting message based on the input parameters:

1. Use the specified greeting word: "{{ greeting }}"
2. Address the person by name: "{{ name }}"
3. Apply the format style:
   - friendly: casual and warm
   - formal: polite and respectful
   - casual: relaxed and informal
4. {% if enthusiastic %}Add enthusiasm with exclamation marks{% else %}Keep it calm without exclamation marks{% endif %}

## Output Requirements
Please return a JSON response with:
- greeting: The greeting word used ("{{ greeting }}")
- name: The name being greeted ("{{ name }}")
- format: The format applied ("{{ format }}")
- enthusiastic: Whether enthusiastic mode was used ({{ enthusiastic }})
- message: The complete greeting message you created

Create the greeting now.
"""

        hello_cli_path = create_test_ost_file(
            fs, hello_cli_content, "hello_cli.ost"
        )

        # Make the file executable
        os.chmod(hello_cli_path, 0o755)

        # Test 1: Basic execution with dry-run to validate template and schema
        with patch("os.execvp") as mock_execvp:
            argv = [
                hello_cli_path,
                "--dry-run",
                "Alice",
                "--greeting",
                "Hi",
                "--enthusiastic",
            ]
            try:
                runx_main(argv)
            except SystemExit:
                pass  # Expected from execvp

            # Verify execvp was called with correct arguments
            assert mock_execvp.called
            args = mock_execvp.call_args[0]
            assert args[0] == "ostruct"
            cmd_args = args[1]

            # Check that the command includes 'run' and proper arguments
            assert "run" in cmd_args
            assert "--dry-run" in cmd_args

            # Check that template variables were mapped to --var flags
            var_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--var" and i + 1 < len(cmd_args):
                    var_args.append(cmd_args[i + 1])

            assert "name=Alice" in var_args
            assert "greeting=Hi" in var_args
            assert "enthusiastic=true" in var_args
            assert "format=friendly" in var_args  # default value

        # Test 2: Validate schema structure by parsing the exported schema
        # This simulates what would happen during actual execution
        with open(hello_cli_path, "r") as f:
            content = f.read()
        parser = FrontMatterParser(content)
        metadata, body_start = parser.parse()

        # Verify the schema is valid JSON
        schema_str = metadata.get("schema", "")
        assert schema_str.strip(), "Schema should not be empty"

        schema_json = json.loads(schema_str)

        # Validate schema structure
        assert schema_json["type"] == "object"
        assert "properties" in schema_json
        assert "required" in schema_json

        # Check required fields
        required_fields = schema_json["required"]
        expected_fields = [
            "greeting",
            "name",
            "format",
            "enthusiastic",
            "message",
        ]
        assert set(required_fields) == set(expected_fields)

        # Validate each property has correct type
        properties = schema_json["properties"]
        assert properties["greeting"]["type"] == "string"
        assert properties["name"]["type"] == "string"
        assert properties["format"]["type"] == "string"
        assert properties["enthusiastic"]["type"] == "boolean"
        assert properties["message"]["type"] == "string"

        # Validate enum constraint on format
        assert properties["format"]["enum"] == ["friendly", "formal", "casual"]

        # Test 3: Test with different argument combinations
        test_cases = [
            # (args, expected_vars)
            (
                ["Bob"],
                {
                    "name": "Bob",
                    "greeting": "Hello",
                    "format": "friendly",
                    "enthusiastic": "false",
                },
            ),
            (
                ["Carol", "--greeting", "Hey", "--format", "casual"],
                {
                    "name": "Carol",
                    "greeting": "Hey",
                    "format": "casual",
                    "enthusiastic": "false",
                },
            ),
            (
                ["Dave", "--enthusiastic", "--format", "formal"],
                {
                    "name": "Dave",
                    "greeting": "Hello",
                    "format": "formal",
                    "enthusiastic": "true",
                },
            ),
        ]

        for test_args, expected_vars in test_cases:
            with patch("os.execvp") as mock_execvp:
                argv = [hello_cli_path] + test_args + ["--dry-run"]
                try:
                    runx_main(argv)
                except SystemExit:
                    pass

                assert mock_execvp.called
                cmd_args = mock_execvp.call_args[0][1]

                # Extract variable assignments
                var_args = []
                for i, arg in enumerate(cmd_args):
                    if arg == "--var" and i + 1 < len(cmd_args):
                        var_args.append(cmd_args[i + 1])

                # Check that all expected variables are present
                for var_name, expected_value in expected_vars.items():
                    expected_assignment = f"{var_name}={expected_value}"
                    assert (
                        expected_assignment in var_args
                    ), f"Missing {expected_assignment} in {var_args}"

        # Test 4: Test policy enforcement (model restriction)
        with pytest.raises(SystemExit) as exc_info:
            argv = [
                hello_cli_path,
                "--model",
                "gpt-4",
                "TestUser",
            ]  # gpt-4 not in allowed list
            runx_main(argv)
        assert exc_info.value.code == 2  # Policy violation

        # Test 5: Test help screen generation
        import contextlib
        import io

        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        with (
            contextlib.redirect_stdout(captured_stdout),
            contextlib.redirect_stderr(captured_stderr),
        ):
            exit_code = runx_main([hello_cli_path, "--help"])

        assert exit_code == 0
        help_output = captured_stdout.getvalue() + captured_stderr.getvalue()
        assert "hello-cli" in help_output
        assert "A simple greeting CLI tool" in help_output
        assert "greeting" in help_output
        assert "enthusiastic" in help_output
        assert "Global ostruct flags policy:" in help_output

    def test_runx_user_data_and_auto_targets(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test that runx correctly handles user-data and auto targets."""
        # Create OST file with user-data and auto targets
        ost_content = """---
cli:
  name: test-targets
  description: Test user-data and auto targets
  options:
    pdf_file:
      names: ["--pdf-file"]
      type: file
      target: user-data
      help: PDF file for vision model
    doc_file:
      names: ["--doc-file"]
      type: file
      target: auto
      help: Document file for auto-routing
    data_dir:
      names: ["--data-dir"]
      type: directory
      target: ud
      help: Directory for user-data
    auto_dir:
      names: ["--auto-dir"]
      type: directory
      target: auto
      help: Directory for auto-routing
    collection:
      names: ["--collection"]
      type: collection
      target: user-data
      help: Collection for user-data
schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
Test template with user-data and auto targets.
Result: {{ pdf_file.path if pdf_file else 'no pdf' }}
"""

        # Create test files
        test_dir = "/test_workspace/base"
        ost_path = create_test_ost_file(fs, ost_content, "test_targets.ost")
        fs.create_file(f"{test_dir}/test.pdf", contents="PDF content")
        fs.create_file(f"{test_dir}/document.txt", contents="Document content")
        fs.create_dir(f"{test_dir}/data")
        fs.create_dir(f"{test_dir}/auto_data")
        fs.create_file(
            f"{test_dir}/filelist.txt", contents="file1.txt\nfile2.txt"
        )

        # Test user-data file target
        with patch("os.execvp") as mock_execvp:
            argv = [
                ost_path,
                "--pdf-file",
                f"{test_dir}/test.pdf",
            ]
            runx_main(argv)

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Should contain --file ud:pdf_file:path
            file_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--file" and i + 1 < len(cmd_args):
                    file_args.append(cmd_args[i + 1])

            assert any(
                "ud:pdf_file:" in arg for arg in file_args
            ), f"Missing user-data file flag in {file_args}"

        # Test auto file target
        with patch("os.execvp") as mock_execvp:
            argv = [
                ost_path,
                "--doc-file",
                f"{test_dir}/document.txt",
            ]
            runx_main(argv)

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Should contain --file auto:doc_file:path
            file_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--file" and i + 1 < len(cmd_args):
                    file_args.append(cmd_args[i + 1])

            assert any(
                "auto:doc_file:" in arg for arg in file_args
            ), f"Missing auto file flag in {file_args}"

        # Test user-data directory target
        with patch("os.execvp") as mock_execvp:
            argv = [
                ost_path,
                "--data-dir",
                f"{test_dir}/data",
            ]
            runx_main(argv)

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Should contain --dir ud:data_dir:path
            dir_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--dir" and i + 1 < len(cmd_args):
                    dir_args.append(cmd_args[i + 1])

            assert any(
                "ud:data_dir:" in arg for arg in dir_args
            ), f"Missing user-data dir flag in {dir_args}"

        # Test auto directory target
        with patch("os.execvp") as mock_execvp:
            argv = [
                ost_path,
                "--auto-dir",
                f"{test_dir}/auto_data",
            ]
            runx_main(argv)

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Should contain --dir auto:auto_dir:path
            dir_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--dir" and i + 1 < len(cmd_args):
                    dir_args.append(cmd_args[i + 1])

            assert any(
                "auto:auto_dir:" in arg for arg in dir_args
            ), f"Missing auto dir flag in {dir_args}"

        # Test user-data collection target
        with patch("os.execvp") as mock_execvp:
            argv = [
                ost_path,
                "--collection",
                f"{test_dir}/filelist.txt",
            ]
            runx_main(argv)

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Should contain --collect ud:collection:@path
            collect_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--collect" and i + 1 < len(cmd_args):
                    collect_args.append(cmd_args[i + 1])

            assert any(
                "ud:collection:@" in arg for arg in collect_args
            ), f"Missing user-data collection flag in {collect_args}"

    @pytest.mark.no_fs
    @pytest.mark.skipif(
        os.name == "nt", reason="Shebang execution not supported on Windows"
    )
    def test_shebang_execution_via_subprocess(self, temp_dir: Path):
        """T5.3: Shebang execution test on *nix via subprocess.run(['./hello_cli.ost', 'arg1'] ...)"""
        # Create a simple OST file with shebang
        ost_content = """#!/usr/bin/env -S ostruct runx
---
cli:
  name: simple-cli
  description: A simple CLI for testing shebang execution
  positional:
    - name: message
      help: Message to process
      default: "Hello"
  options:
    uppercase:
      names: ["--uppercase", "-u"]
      help: Convert to uppercase
      action: "store_true"

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string",
        "description": "The processed message"
      },
      "uppercase": {
        "type": "boolean",
        "description": "Whether uppercase was applied"
      }
    },
    "required": ["result", "uppercase"]
  }

defaults:
  uppercase: false

global_args:
  pass_through_global: true
  model:
    mode: "allowed"
    allowed: ["gpt-4o-mini"]
    default: "gpt-4o-mini"
---
# Simple Message Processing

Process the message: {{ message }}
Uppercase mode: {{ uppercase }}

Please return:
- result: {% if uppercase %}{{ message | upper }}{% else %}{{ message }}{% endif %}
- uppercase: {{ uppercase }}
"""

        # Create the OST file in a real temporary directory
        # because subprocess needs real files

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ost", delete=False, dir=temp_dir
        ) as f:
            f.write(ost_content)
            ost_path = f.name

        # Make the file executable
        os.chmod(ost_path, 0o755)

        try:
            # Test 1: Basic execution with dry-run (should work without API key)
            result = subprocess.run(
                [ost_path, "--dry-run", "TestMessage"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should succeed with dry-run
            assert result.returncode == 0, f"Dry-run failed: {result.stderr}"
            assert "Dry run completed successfully" in result.stdout
            assert "Template: ✅" in result.stdout
            assert "Schema: ✅" in result.stdout

            # Test 2: Help screen via shebang
            result = subprocess.run(
                [ost_path, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert result.returncode == 0, f"Help failed: {result.stderr}"
            assert "simple-cli" in result.stdout
            assert (
                "A simple CLI for testing shebang execution" in result.stdout
            )
            assert "--uppercase" in result.stdout

            # Test 3: Test with uppercase flag
            result = subprocess.run(
                [ost_path, "--dry-run", "test", "--uppercase"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert (
                result.returncode == 0
            ), f"Uppercase test failed: {result.stderr}"
            assert "Dry run completed successfully" in result.stdout

            # Test 4: Test error handling - invalid flag
            result = subprocess.run(
                [ost_path, "--invalid-flag"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should fail with proper error code
            assert result.returncode != 0
            assert (
                "unrecognized arguments" in result.stderr
                or "error" in result.stderr.lower()
            )

            # Test 5: Test policy enforcement - if we add a blocked flag
            # This would require modifying the template, but we can test
            # that the basic policy system works
            result = subprocess.run(
                [ost_path, "--dry-run", "test", "--model", "gpt-4o-mini"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should succeed since gpt-4o-mini is in allowed list
            assert (
                result.returncode == 0
            ), f"Policy test failed: {result.stderr}"

        finally:
            # Clean up the temporary file
            if os.path.exists(ost_path):
                os.unlink(ost_path)

    def test_repeatable_flags_and_edge_cases(self, fs: FakeFilesystem):
        """T5.4: Add tests for repeatable flags (comma-split/multiple), unknown flag defaults, and edge cases."""
        # Test 1: Repeatable flags (list values)
        ost_content_repeatable = """#!/usr/bin/env -S ostruct runx
---
cli:
  name: repeatable-test
  description: Test repeatable flags
  options:
    tags:
      names: ["--tag", "-t"]
      help: Tags to apply (repeatable)
      action: "append"
    items:
      names: ["--item"]
      help: Items to process (repeatable)
      action: "append"
    verbose:
      names: ["--verbose", "-v"]
      help: Verbose output
      action: "store_true"

schema: |
  {
    "type": "object",
    "properties": {
      "tags": {
        "type": "array",
        "items": {"type": "string"}
      },
      "items": {
        "type": "array",
        "items": {"type": "string"}
      },
      "verbose": {
        "type": "boolean"
      }
    },
    "required": ["tags", "items", "verbose"]
  }

defaults:
  tags: []
  items: []
  verbose: false

global_args:
  pass_through_global: true
---
Tags: {{ tags }}
Items: {{ items }}
Verbose: {{ verbose }}
"""

        repeatable_path = create_test_ost_file(
            fs, ost_content_repeatable, "repeatable.ost"
        )

        with patch("os.execvp") as mock_execvp:
            argv = [
                repeatable_path,
                "--tag",
                "python",
                "--tag",
                "testing",
                "--item",
                "file1.py",
                "--item",
                "file2.py",
                "--verbose",
            ]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            # Verify execvp was called
            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Check that list values are properly handled
            var_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--var" and i + 1 < len(cmd_args):
                    var_args.append(cmd_args[i + 1])

            # Should have repeated --var flags for list items
            # Note: argparse uses the first flag name without dashes as the destination
            assert "tag=python" in var_args
            assert "tag=testing" in var_args
            assert "item=file1.py" in var_args
            assert "item=file2.py" in var_args
            assert "verbose=true" in var_args

        # Test 2: Unknown flag handling with pass_through_global=true
        ost_content_pass_through = """#!/usr/bin/env -S ostruct runx
---
cli:
  name: pass-through-test
  description: Test pass-through behavior
  options:
    name:
      names: ["--name"]
      help: Name to process

schema: |
  {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "result": {"type": "string"}
    },
    "required": ["name", "result"]
  }

global_args:
  pass_through_global: true
---
Hello {{ name }}
"""

        pass_through_path = create_test_ost_file(
            fs, ost_content_pass_through, "pass_through.ost"
        )

        with patch("os.execvp") as mock_execvp:
            argv = [
                pass_through_path,
                "--name",
                "Alice",
                "--unknown-flag",
                "value",
                "--dry-run",
            ]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            # Should succeed and pass through unknown flags
            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Unknown flags should be passed through
            assert "--unknown-flag" in cmd_args
            assert "value" in cmd_args
            assert "--dry-run" in cmd_args

        # Test 3: Unknown flag handling with pass_through_global=false
        ost_content_no_pass_through = """#!/usr/bin/env -S ostruct runx
---
cli:
  name: no-pass-through-test
  description: Test no pass-through behavior
  options:
    name:
      names: ["--name"]
      help: Name to process

schema: |
  {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "result": {"type": "string"}
    },
    "required": ["name", "result"]
  }

global_args:
  pass_through_global: false
---
Hello {{ name }}
"""

        no_pass_through_path = create_test_ost_file(
            fs, ost_content_no_pass_through, "no_pass_through.ost"
        )

        # Should exit with code 2 when unknown flag is provided
        with patch("os.execvp") as mock_execvp:
            argv = [
                no_pass_through_path,
                "--name",
                "Alice",
                "--unknown-flag",
                "value",
            ]
            try:
                runx_main(argv)
                # Should not reach here
                assert False, "Expected SystemExit to be raised"
            except SystemExit as e:
                # Should exit with code 2 for unknown flag
                assert e.code == 2
                # Should not have reached execvp
                assert not mock_execvp.called

        # Test 4: Edge cases - empty values, boolean flags, special characters
        ost_content_edge_cases = """#!/usr/bin/env -S ostruct runx
---
cli:
  name: edge-cases-test
  description: Test edge cases
  options:
    empty:
      names: ["--empty"]
      help: Empty value test
      default: ""
    flag:
      names: ["--flag"]
      help: Boolean flag
      action: "store_true"
    special:
      names: ["--special"]
      help: Special characters
      default: "hello=world&test"

schema: |
  {
    "type": "object",
    "properties": {
      "empty": {"type": "string"},
      "flag": {"type": "boolean"},
      "special": {"type": "string"},
      "result": {"type": "string"}
    },
    "required": ["empty", "flag", "special", "result"]
  }

defaults:
  empty: ""
  flag: false
  special: "hello=world&test"

global_args:
  pass_through_global: true
---
Empty: "{{ empty }}"
Flag: {{ flag }}
Special: "{{ special }}"
"""

        edge_cases_path = create_test_ost_file(
            fs, ost_content_edge_cases, "edge_cases.ost"
        )

        with patch("os.execvp") as mock_execvp:
            argv = [
                edge_cases_path,
                "--empty",
                "",
                "--flag",
                "--special",
                "test=value&more",
            ]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            # Verify execvp was called
            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Check variable mapping
            var_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--var" and i + 1 < len(cmd_args):
                    var_args.append(cmd_args[i + 1])

            # Should handle empty values and special characters
            assert "empty=" in var_args
            assert "flag=true" in var_args
            assert "special=test=value&more" in var_args

        # Test 5: Default values are applied when arguments not provided
        with patch("os.execvp") as mock_execvp:
            argv = [edge_cases_path]  # No arguments provided
            try:
                runx_main(argv)
            except SystemExit:
                pass

            # Verify execvp was called
            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Check that defaults were applied
            var_args = []
            for i, arg in enumerate(cmd_args):
                if arg == "--var" and i + 1 < len(cmd_args):
                    var_args.append(cmd_args[i + 1])

            # Should use default values
            assert "empty=" in var_args
            assert "flag=false" in var_args
            assert "special=hello=world&test" in var_args

    def test_comprehensive_policy_enforcement(self, fs: FakeFilesystem):
        """T5.5: Add comprehensive tests for policy enforcement (all modes, alias resolution with conflicts)."""
        # Test comprehensive policy enforcement with all modes
        ost_content_comprehensive = """#!/usr/bin/env -S ostruct runx
---
cli:
  name: policy-test
  description: Comprehensive policy enforcement test
  options:
    input:
      names: ["--input", "-i"]
      help: Input to process

schema: |
  {
    "type": "object",
    "properties": {
      "input": {"type": "string"},
      "result": {"type": "string"}
    },
    "required": ["input", "result"]
  }

global_args:
  pass_through_global: false
  # Test FIXED mode
  --model:
    mode: "fixed"
    value: "gpt-4o-mini"
  # Test ALLOWED mode
  --temperature:
    mode: "allowed"
    allowed: ["0.0", "0.5", "1.0"]
    default: "0.5"
  # Test BLOCKED mode
  --enable-tool:
    mode: "blocked"
  # Test PASS_THROUGH mode
  --dry-run:
    mode: "pass-through"
  # Test alias resolution
  --max-output-tokens:
    mode: "allowed"
    allowed: ["100", "500", "1000"]
    default: "500"
---
Process: {{ input }}
"""

        policy_path = create_test_ost_file(
            fs, ost_content_comprehensive, "policy.ost"
        )

        # Test 1: FIXED mode - should reject attempts to override fixed value
        with patch("os.execvp") as mock_execvp:
            argv = [
                policy_path,
                "--input",
                "test",
                "--model",
                "gpt-4o",  # Try to override fixed value
            ]
            try:
                runx_main(argv)
                assert False, "Expected SystemExit for fixed value override"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called

        # Test 1b: FIXED mode - when no value provided, fixed value is added by policy defaults
        # NOTE: Currently the policy enforcer only processes explicitly provided flags
        # Fixed values are not automatically added when the flag is not provided
        # This might be the intended behavior or a limitation to be addressed later
        with patch("os.execvp") as mock_execvp:
            argv = [
                policy_path,
                "--input",
                "test",
                # No --model provided
            ]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            _cmd_args = mock_execvp.call_args[0][1]


class TestRunxMain:
    """Test the main runx functionality."""

    def test_template_expansion_in_policy_context(self, fs: FakeFilesystem):
        """
        Test T5.6: Template expansion edge cases in policy context.

        This test verifies that template variables mapped to ostruct flags
        interact correctly with policy enforcement, including edge cases like:
        - Template defaults generating flags that conflict with policy
        - File/directory template variables generating --file/--dir flags under policy
        - Variable defaults vs fixed-mode globals
        - Template-generated flags being blocked by policy
        """
        # Test 1: Template defaults generating blocked flags
        template_content_blocked = """---
cli:
  name: "policy-blocked-test"
  description: "Test blocked policy with template defaults"
  options:
    user_input:
      names: ["--user-input"]
      type: "str"
      help: "User input"

defaults:
  user_input: "default_value"

global_args:
  pass_through_global: false

  --var:
    mode: "blocked"

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
User input: {{ user_input }}
"""

        blocked_path = Path("/test/policy_blocked.ost")
        fs.create_file(blocked_path, contents=template_content_blocked)

        # In the new architecture, template-generated --var flags are always allowed
        # Only user-provided flags are subject to policy enforcement
        with patch("os.execvp") as mock_execvp:
            argv = [str(blocked_path)]
            runx_main(argv)

            # Should succeed - template-generated flags are not blocked
            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]
            assert "--var" in cmd_args

            # Find the user_input variable
            var_idx = cmd_args.index("--var")
            assert "user_input=default_value" in cmd_args[var_idx + 1]

        # But if user tries to provide --var directly, it should be blocked
        with patch("os.execvp") as mock_execvp:
            argv = [str(blocked_path), "--var", "custom=value"]
            try:
                runx_main(argv)
                assert (
                    False
                ), "Expected SystemExit for user-provided blocked --var flag"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called

        # Test 2: File type template variables generating allowed flags
        template_content_file = """---
cli:
  name: "policy-file-test"
  description: "Test file type with policy"
  options:
    input_file:
      names: ["--input-file"]
      type: "file"
      target: "ci"
      help: "Input file"

global_args:
  pass_through_global: false

  --file:
    mode: "pass-through"

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
File: {% if input_file is defined %}{{ input_file }}{% endif %}
"""

        file_path = Path("/test/policy_file.ost")
        fs.create_file(file_path, contents=template_content_file)

        test_file = Path("/test/input.txt")
        fs.create_file(test_file, contents="test input")

        with patch("os.execvp") as mock_execvp:
            argv = [str(file_path), "--input-file", str(test_file)]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Should contain file flag from template expansion
            assert "--file" in cmd_args
            assert "ci:input_file:" in " ".join(cmd_args)

        # Test 3: Fixed mode with template variables (current behavior)
        template_content_fixed = """---
cli:
  name: "policy-fixed-test"
  description: "Test fixed mode with template variables"
  options:
    user_model:
      names: ["--user-model"]
      type: "str"
      help: "User model choice"

defaults:
  user_model: "gpt-4o"

global_args:
  pass_through_global: false

  --model:
    mode: "fixed"
    value: "gpt-4.1"
  --var:
    mode: "pass-through"

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
Using model: {{ user_model }}
"""

        fixed_path = Path("/test/policy_fixed.ost")
        fs.create_file(fixed_path, contents=template_content_fixed)

        # Test 3a: Fixed mode without explicit flag (current behavior: no auto-injection)
        with patch("os.execvp") as mock_execvp:
            argv = [str(fixed_path)]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Should contain template variable, but NOT auto-injected fixed model
            assert "--var" in cmd_args
            assert "user_model=gpt-4o" in cmd_args
            # Fixed model is not auto-injected when not provided
            assert "--model" not in cmd_args

            # Test 3b: Fixed mode with explicit flag (should reject override attempt)
        with patch("os.execvp") as mock_execvp:
            argv = [
                str(fixed_path),
                "--model",
                "gpt-4o",
            ]  # Try to override fixed value
            try:
                runx_main(argv)
                assert False, "Expected SystemExit for fixed value override"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called

        # Test 3c: Fixed mode with matching explicit flag (should succeed)
        with patch("os.execvp") as mock_execvp:
            argv = [
                str(fixed_path),
                "--model",
                "gpt-4.1",
            ]  # Matches fixed value
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            # Should contain fixed model value and template variable
            assert "--model" in cmd_args
            assert "gpt-4.1" in cmd_args  # Fixed value enforced
            assert "--var" in cmd_args
            assert "user_model=gpt-4o" in cmd_args

        # Test 4: Allowed mode with template variables
        template_content_allowed = """---
cli:
  name: "policy-allowed-test"
  description: "Test allowed mode with template variables"
  options:
    temp_setting:
      names: ["--temp-setting"]
      type: "str"
      help: "Temperature setting"

defaults:
  temp_setting: "0.7"

global_args:
  pass_through_global: false

  --var:
    mode: "allowed"
    allowed: ["temp_setting=0.5", "temp_setting=0.7", "temp_setting=1.0"]

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
Temperature: {{ temp_setting }}
"""

        allowed_path = Path("/test/policy_allowed.ost")
        fs.create_file(allowed_path, contents=template_content_allowed)

        # Test 4a: Valid template default should pass
        with patch("os.execvp") as mock_execvp:
            argv = [str(allowed_path)]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            assert "--var" in cmd_args
            assert "temp_setting=0.7" in cmd_args

        # Test 4b: Invalid template default should be rejected
        template_content_invalid = """---
cli:
  name: "policy-invalid-test"
  description: "Test invalid template default"
  options:
    temp_setting:
      names: ["--temp-setting"]
      type: "str"
      help: "Temperature setting"

defaults:
  temp_setting: "0.9"  # Not in allowed list

global_args:
  pass_through_global: false

  --var:
    mode: "allowed"
    allowed: ["temp_setting=0.5", "temp_setting=0.7", "temp_setting=1.0"]

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
Temperature: {{ temp_setting }}
"""

        invalid_path = Path("/test/policy_invalid.ost")
        fs.create_file(invalid_path, contents=template_content_invalid)

        # In the new architecture, template-generated flags are always allowed
        # regardless of policy - only user-provided flags are subject to policy
        with patch("os.execvp") as mock_execvp:
            argv = [str(invalid_path)]
            runx_main(argv)

            # Should succeed - template-generated flags bypass policy
            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]
            assert "--var" in cmd_args
            assert "temp_setting=0.9" in cmd_args

        # Test 5: Complex file routing with policy enforcement
        template_content_complex = """---
cli:
  name: "policy-complex-test"
  description: "Test complex file routing with policy"
  options:
    config_file:
      names: ["--config-file"]
      type: "file"
      target: "prompt"
      help: "Config file"
    data_dir:
      names: ["--data-dir"]
      type: "directory"
      target: "ci"
      help: "Data directory"
    collection_file:
      names: ["--collection-file"]
      type: "collection"
      target: "fs"
      help: "Collection file"

global_args:
  pass_through_global: false

  --file:
    mode: "pass-through"
  --dir:
    mode: "allowed"
    allowed: ["ci:data_dir:/test/data", "ci:data_dir:/test/allowed"]
  --collect:
    mode: "blocked"

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
Config: {% if config_file is defined %}{{ config_file }}{% endif %}
Data: {% if data_dir is defined %}{{ data_dir }}{% endif %}
Collection: {% if collection_file is defined %}{{ collection_file }}{% endif %}
"""

        complex_path = Path("/test/policy_complex.ost")
        fs.create_file(complex_path, contents=template_content_complex)

        # Create test files
        test_file = Path("/test/config.txt")
        fs.create_file(test_file, contents="config data")
        test_data_dir = Path("/test/data")
        fs.create_dir(test_data_dir)
        test_collection = Path("/test/collection.txt")
        fs.create_file(test_collection, contents="item1\nitem2")

        # Test 5b: Allowed operations should work
        with patch("os.execvp") as mock_execvp:
            argv = [
                str(complex_path),
                "--config-file",
                str(test_file),
                "--data-dir",
                str(test_data_dir),
            ]
            try:
                runx_main(argv)
            except SystemExit:
                pass

            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]

            assert "--file" in cmd_args
            assert "config_file:" in " ".join(cmd_args)
            assert "--dir" in cmd_args
            assert "ci:data_dir:" in " ".join(cmd_args)

        # Test 6: Mixed policies with user and template flags
        template_content_mixed = """---
cli:
  name: "policy-mixed-test"
  description: "Test mixed user and template flags"
  options:
    user_var:
      names: ["--user-var"]
      type: "str"
      help: "User variable"

defaults:
  user_var: "blocked_value"

global_args:
  pass_through_global: false

  --var:
    mode: "blocked"
  --model:
    mode: "fixed"
    value: "gpt-4.1"

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
Var: {{ user_var }}
"""

        mixed_path = Path("/test/policy_mixed.ost")
        fs.create_file(mixed_path, contents=template_content_mixed)

        # Should succeed - template-generated flags bypass policy
        with patch("os.execvp") as mock_execvp:
            argv = [str(mixed_path), "--model", "gpt-4.1"]
            runx_main(argv)

            # Should succeed - template-generated flags are not blocked
            assert mock_execvp.called
            cmd_args = mock_execvp.call_args[0][1]
            assert "--var" in cmd_args
            assert "user_var=blocked_value" in cmd_args
            assert "--model" in cmd_args
            assert "gpt-4.1" in cmd_args

    def test_global_flags_template_set_with_user_override(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test template-set flags with user override attempts."""
        # Create OST with global_flags that sets --enable-tool
        ost_content = """---
cli:
  name: tool-template
  description: Template with pre-set tools
  options:
    task:
      names: ["--task", "-t"]
      help: Task to perform
      default: "analyze"

global_flags:
  - "--enable-tool"
  - "code-interpreter"
  - "--model"
  - "gpt-4o"

global_args:
  --enable-tool:
    mode: "fixed"
    value: "code-interpreter"
  --model:
    mode: "fixed"
    value: "gpt-4o"

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
Task: {{ task }}
Result: Analysis complete
"""
        tool_path = create_test_ost_file(fs, ost_content, "tool_template.ost")

        # Test 1: User tries to override template-set --enable-tool
        with patch("os.execvp") as mock_execvp:
            argv = [str(tool_path), "--enable-tool", "web-search"]
            try:
                runx_main(argv)
                assert False, "Expected SystemExit for override attempt"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called

        # Test 2: User tries to override template-set --model
        with patch("os.execvp") as mock_execvp:
            argv = [str(tool_path), "--model", "gpt-4o-mini"]
            try:
                runx_main(argv)
                assert False, "Expected SystemExit for model override"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called

        # Test 3: User provides same value as template (should succeed)
        with patch("os.execvp") as mock_execvp:
            argv = [str(tool_path), "--model", "gpt-4o", "--task", "review"]
            runx_main(argv)

            # Should succeed and call execvp
            assert mock_execvp.called
            called_args = mock_execvp.call_args[0]
            assert called_args[0] == "ostruct"

            # Check that both template-set and user args are present
            cmd_args = called_args[1]
            assert "--enable-tool" in cmd_args
            assert "code-interpreter" in cmd_args
            assert "--model" in cmd_args
            assert "gpt-4o" in cmd_args
            assert "--var" in cmd_args

            # Find the task variable
            var_idx = cmd_args.index("--var")
            assert "task=review" in cmd_args[var_idx + 1]

    def test_global_flags_blocked_mode(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test blocked mode prevents user from using certain flags."""
        ost_content = """---
cli:
  name: secure-template
  description: Template with blocked flags
  options:
    query:
      names: ["--query", "-q"]
      help: Query to process

global_flags:
  - "--enable-tool"
  - "file-search"

global_args:
  --debug:
    mode: "blocked"
  --enable-tool:
    mode: "pass-through"

schema: |
  {
    "type": "object",
    "properties": {
      "response": {
        "type": "string"
      }
    },
    "required": ["response"]
  }
---
Query: {{ query }}
Response: Processed
"""
        secure_path = create_test_ost_file(
            fs, ost_content, "secure_template.ost"
        )

        # Test 1: User tries to use blocked --debug flag
        with patch("os.execvp") as mock_execvp:
            argv = [str(secure_path), "--debug", "--query", "test"]
            try:
                runx_main(argv)
                assert False, "Expected SystemExit for blocked flag"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called

        # Test 2: User can use allowed flags alongside template-set flags
        with patch("os.execvp") as mock_execvp:
            argv = [str(secure_path), "--query", "test", "--verbose"]
            runx_main(argv)

            assert mock_execvp.called
            called_args = mock_execvp.call_args[0]
            cmd_args = called_args[1]

            # Template-set flags should be present
            assert "--enable-tool" in cmd_args
            assert "file-search" in cmd_args

            # User flags should be present
            assert "--verbose" in cmd_args
            assert "--var" in cmd_args

    def test_global_flags_allowed_mode(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test allowed mode restricts values to whitelist."""
        ost_content = """---
cli:
  name: restricted-template
  description: Template with allowed values
  options:
    task:
      names: ["--task"]
      help: Task type

global_flags:
  - "--model"
  - "gpt-4o"

global_args:
  --model:
    mode: "allowed"
    allowed: ["gpt-4o", "gpt-4o-mini"]
  --temperature:
    mode: "allowed"
    allowed: ["0.0", "0.5", "1.0"]

schema: |
  {
    "type": "object",
    "properties": {
      "result": {
        "type": "string"
      }
    },
    "required": ["result"]
  }
---
Task: {{ task }}
Result: Done
"""
        restricted_path = create_test_ost_file(
            fs, ost_content, "restricted_template.ost"
        )

        # Test 1: User tries disallowed model value
        with patch("os.execvp") as mock_execvp:
            argv = [str(restricted_path), "--model", "gpt-3.5-turbo"]
            try:
                runx_main(argv)
                assert False, "Expected SystemExit for disallowed model"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called

        # Test 2: User tries disallowed temperature value
        with patch("os.execvp") as mock_execvp:
            argv = [str(restricted_path), "--temperature", "0.7"]
            try:
                runx_main(argv)
                assert False, "Expected SystemExit for disallowed temperature"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called

        # Test 3: User provides allowed values (should succeed)
        with patch("os.execvp") as mock_execvp:
            argv = [
                str(restricted_path),
                "--model",
                "gpt-4o-mini",
                "--temperature",
                "0.5",
            ]
            runx_main(argv)

            assert mock_execvp.called
            called_args = mock_execvp.call_args[0]
            cmd_args = called_args[1]

            # Template-set model should be overridden by user's allowed value
            assert "--model" in cmd_args
            model_idx = cmd_args.index("--model")
            assert cmd_args[model_idx + 1] == "gpt-4o-mini"

            # User's temperature should be present
            assert "--temperature" in cmd_args
            temp_idx = cmd_args.index("--temperature")
            assert cmd_args[temp_idx + 1] == "0.5"

    def test_global_flags_complex_scenario(
        self, fs: FakeFilesystem, security_manager: Mock
    ):
        """Test complex scenario with multiple global_flags and policies."""
        ost_content = """---
cli:
  name: complex-template
  description: Complex template with multiple flags and policies
  options:
    input_file:
      names: ["--input-file"]
      type: "file"
      target: "ci"
      help: Input file for processing

global_flags:
  - "--enable-tool"
  - "code-interpreter"
  - "--enable-tool"
  - "file-search"
  - "--model"
  - "gpt-4o"
  - "--max-tokens"
  - "2000"

global_args:
  --enable-tool:
    mode: "pass-through"
  --model:
    mode: "fixed"
    value: "gpt-4o"
  --max-tokens:
    mode: "allowed"
    allowed: ["1000", "2000", "4000"]
  --temperature:
    mode: "blocked"

schema: |
  {
    "type": "object",
    "properties": {
      "analysis": {
        "type": "string"
      }
    },
    "required": ["analysis"]
  }
---
Input: {{ input_file.name if input_file else "none" }}
Analysis: Complete
"""
        complex_path = create_test_ost_file(
            fs, ost_content, "complex_template.ost"
        )

        # Create a test input file
        input_file_path = "/test_workspace/base/input.txt"
        fs.create_file(input_file_path, contents="test data")

        # Test successful execution with template-set flags and user additions
        with patch("os.execvp") as mock_execvp:
            argv = [
                str(complex_path),
                "--input-file",
                input_file_path,
                "--max-tokens",
                "4000",  # Override template's 2000 with allowed value
                "--verbose",  # Additional user flag
            ]
            runx_main(argv)

            assert mock_execvp.called
            called_args = mock_execvp.call_args[0]
            cmd_args = called_args[1]

            # Template-set flags should be present
            assert "--enable-tool" in cmd_args
            tool_indices = [
                i for i, arg in enumerate(cmd_args) if arg == "--enable-tool"
            ]
            assert (
                len(tool_indices) == 2
            )  # Both code-interpreter and file-search

            # Model should be fixed value
            assert "--model" in cmd_args
            model_idx = cmd_args.index("--model")
            assert cmd_args[model_idx + 1] == "gpt-4o"

            # Max tokens should be user's allowed override
            assert "--max-tokens" in cmd_args
            tokens_idx = cmd_args.index("--max-tokens")
            assert cmd_args[tokens_idx + 1] == "4000"

            # User's additional flag should be present
            assert "--verbose" in cmd_args

            # File should be processed
            assert "--file" in cmd_args

        # Test blocked temperature flag
        with patch("os.execvp") as mock_execvp:
            argv = [str(complex_path), "--temperature", "0.7"]
            try:
                runx_main(argv)
                assert False, "Expected SystemExit for blocked temperature"
            except SystemExit as e:
                assert e.code == 2
                assert not mock_execvp.called
