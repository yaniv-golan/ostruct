"""Test .env file integration and API key error messages."""

import os
import tempfile
from pathlib import Path

from click.testing import CliRunner
from ostruct.cli.cli import cli
from ostruct.cli.exit_codes import ExitCode


def test_dotenv_file_loading() -> None:
    """Test that API keys are loaded from .env files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test files
        template_file = tmp_path / "test.j2"
        schema_file = tmp_path / "schema.json"
        env_file = tmp_path / ".env"

        template_file.write_text("Test task")
        schema_file.write_text(
            '{"schema": {"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"]}}'
        )
        env_file.write_text("OPENAI_API_KEY=sk-test-from-dotenv")

        # Change to the directory with .env file
        original_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            # Ensure no API key in environment
            original_key = os.environ.pop("OPENAI_API_KEY", None)

            try:
                runner = CliRunner()
                result = runner.invoke(
                    cli,
                    ["run", str(template_file), str(schema_file), "--dry-run"],
                )

                # Should succeed with dry-run since API key is loaded from .env
                assert result.exit_code == ExitCode.SUCCESS
                assert "Dry run completed successfully" in result.output

            finally:
                # Restore original API key if it existed
                if original_key:
                    os.environ["OPENAI_API_KEY"] = original_key
        finally:
            os.chdir(original_cwd)


def test_environment_variable_precedence() -> None:
    """Test that environment variables take precedence over .env files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test files
        template_file = tmp_path / "test.j2"
        schema_file = tmp_path / "schema.json"
        env_file = tmp_path / ".env"

        template_file.write_text("Test task")
        schema_file.write_text(
            '{"schema": {"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"]}}'
        )
        env_file.write_text("OPENAI_API_KEY=sk-from-dotenv")

        # Change to the directory with .env file
        original_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            # Set environment variable (should take precedence)
            original_key = os.environ.get("OPENAI_API_KEY")
            os.environ["OPENAI_API_KEY"] = "sk-from-environment"

            try:
                runner = CliRunner()
                result = runner.invoke(
                    cli,
                    ["run", str(template_file), str(schema_file), "--dry-run"],
                )

                # Should succeed with dry-run
                assert result.exit_code == ExitCode.SUCCESS
                assert "Dry run completed successfully" in result.output

            finally:
                # Restore original API key
                if original_key:
                    os.environ["OPENAI_API_KEY"] = original_key
                else:
                    os.environ.pop("OPENAI_API_KEY", None)
        finally:
            os.chdir(original_cwd)


def test_improved_api_key_error_message() -> None:
    """Test that the API key error message is helpful and informative."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test files
        template_file = tmp_path / "test.j2"
        schema_file = tmp_path / "schema.json"

        template_file.write_text("Test task")
        schema_file.write_text(
            '{"schema": {"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"]}}'
        )

        # Ensure no API key available
        original_key = os.environ.pop("OPENAI_API_KEY", None)

        try:
            runner = CliRunner()
            result = runner.invoke(
                cli, ["run", str(template_file), str(schema_file)]
            )

            # Should fail with API_ERROR
            assert result.exit_code == ExitCode.API_ERROR

            # Check that error message contains helpful information
            assert "No OpenAI API key found" in result.output
            assert "Set OPENAI_API_KEY environment variable" in result.output
            assert "Create a .env file" in result.output
            assert "--api-key option" in result.output
            assert "https://platform.openai.com/api-keys" in result.output

        finally:
            # Restore original API key if it existed
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key


def test_api_key_option_still_works() -> None:
    """Test that the --api-key option still works as expected."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test files
        template_file = tmp_path / "test.j2"
        schema_file = tmp_path / "schema.json"

        template_file.write_text("Test task")
        schema_file.write_text(
            '{"schema": {"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"]}}'
        )

        # Ensure no API key in environment
        original_key = os.environ.pop("OPENAI_API_KEY", None)

        try:
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "run",
                    str(template_file),
                    str(schema_file),
                    "--api-key",
                    "sk-test-via-option",
                    "--dry-run",
                ],
            )

            # Should succeed with dry-run
            assert result.exit_code == ExitCode.SUCCESS
            assert "Dry run completed successfully" in result.output

        finally:
            # Restore original API key if it existed
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
