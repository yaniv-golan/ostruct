"""Tests for models command group functionality."""

import pytest
from click.testing import CliRunner
from ostruct.cli.cli import create_cli


class TestModelsCommand:
    """Test the models command group and its subcommands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def cli(self):
        """Create the CLI."""
        return create_cli()

    def test_models_group_help(self, runner, cli):
        """Test models group shows help correctly."""
        result = runner.invoke(cli, ["models", "--help"])
        assert result.exit_code == 0
        assert (
            "Manage model registry and list available models" in result.output
        )
        assert "list" in result.output
        assert "update" in result.output

    def test_models_list_basic(self, runner, cli, mock_model_registry):
        """Test models list command basic functionality."""
        result = runner.invoke(cli, ["models", "list"])
        assert result.exit_code == 0
        assert "Available Models:" in result.output
        # Should show mock models from the registry
        assert "gpt-4o" in result.output

    def test_models_list_json_format(self, runner, cli, mock_model_registry):
        """Test models list with JSON format."""
        result = runner.invoke(cli, ["models", "list", "--format", "json"])
        assert result.exit_code == 0
        # Should output valid JSON
        import json

        try:
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) > 0
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_models_list_simple_format(self, runner, cli, mock_model_registry):
        """Test models list with simple format."""
        result = runner.invoke(cli, ["models", "list", "--format", "simple"])
        assert result.exit_code == 0
        # Should just list model names
        assert "gpt-4o" in result.output
        assert "Available Models:" not in result.output

    def test_models_list_show_deprecated(
        self, runner, cli, mock_model_registry
    ):
        """Test models list with show-deprecated flag."""
        result = runner.invoke(cli, ["models", "list", "--show-deprecated"])
        assert result.exit_code == 0
        assert "Available Models:" in result.output

    def test_models_update_basic(self, runner, cli, mock_model_registry):
        """Test models update command basic functionality."""
        result = runner.invoke(cli, ["models", "update"])
        assert result.exit_code == 0
        assert "Current registry file:" in result.output
        # Should show either update result or already current message
        assert (
            "Registry successfully updated!" in result.output
            or "Registry is already up to date" in result.output
            or "Checking for registry updates..." in result.output
        )

    def test_models_update_force(self, runner, cli, mock_model_registry):
        """Test models update with force flag."""
        result = runner.invoke(cli, ["models", "update", "--force"])
        assert result.exit_code == 0
        assert "Current registry file:" in result.output
        assert "Forcing registry update..." in result.output

    def test_models_update_custom_url(self, runner, cli, mock_model_registry):
        """Test models update with custom URL."""
        result = runner.invoke(
            cli,
            ["models", "update", "--url", "https://example.com/models.yml"],
        )
        assert result.exit_code == 0
        assert "Current registry file:" in result.output

    def test_deprecated_list_models_warning(
        self, runner, cli, mock_model_registry, capsys
    ):
        """Test that list-models shows deprecation warning."""
        result = runner.invoke(cli, ["list-models"])
        assert result.exit_code == 0
        # Check that warning is in stderr
        assert (
            "Warning: 'list-models' is deprecated"
            in result.stderr_bytes.decode()
        )
        assert (
            "Use 'ostruct models list' instead" in result.stderr_bytes.decode()
        )
        # Should still show the actual output
        assert "Available Models:" in result.output

    def test_deprecated_update_registry_warning(
        self, runner, cli, mock_model_registry, capsys
    ):
        """Test that update-registry shows deprecation warning."""
        result = runner.invoke(cli, ["update-registry"])
        assert result.exit_code == 0
        # Check that warning is in stderr
        assert (
            "Warning: 'update-registry' is deprecated"
            in result.stderr_bytes.decode()
        )
        assert (
            "Use 'ostruct models update' instead"
            in result.stderr_bytes.decode()
        )
        # Should still show the actual output
        assert "Current registry file:" in result.output

    def test_dynamic_version_warning(self, runner, cli, mock_model_registry):
        """Test that deprecation warnings show dynamic version numbers."""
        result = runner.invoke(cli, ["list-models"])
        assert result.exit_code == 0
        # Should contain a version number (e.g., "v1.5.0")
        import re

        version_pattern = r"v\d+\.\d+\.\d+"
        assert re.search(version_pattern, result.stderr_bytes.decode())

    def test_models_with_global_options(
        self, runner, cli, mock_model_registry, monkeypatch
    ):
        """Test that models subcommands work with global CLI options."""
        # Test with OSTRUCT_UNICODE environment variable instead of CLI flag
        monkeypatch.setenv("OSTRUCT_UNICODE", "1")
        result = runner.invoke(cli, ["models", "list"])
        assert result.exit_code == 0
        assert "Available Models:" in result.output

    def test_models_list_help(self, runner, cli):
        """Test models list subcommand help."""
        result = runner.invoke(cli, ["models", "list", "--help"])
        assert result.exit_code == 0
        assert "List available models from the registry" in result.output
        assert "--format" in result.output
        assert "--show-deprecated" in result.output

    def test_models_update_help(self, runner, cli):
        """Test models update subcommand help."""
        result = runner.invoke(cli, ["models", "update", "--help"])
        assert result.exit_code == 0
        assert "Update the model registry" in result.output
        assert "--url" in result.output
        assert "--force" in result.output
        assert (
            "ostruct models update" in result.output
        )  # Should show new command in examples
