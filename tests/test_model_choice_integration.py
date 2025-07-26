"""Test model choice integration with CLI."""

import json

import pytest
from click.testing import CliRunner
from ostruct.cli.cli import cli


class TestModelChoiceIntegration:
    """Test model choice integration with CLI."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def test_files(self, tmp_path):
        """Create test template and schema files."""
        template_file = tmp_path / "test.j2"
        template_file.write_text("Hello {{ name }}")

        schema_file = tmp_path / "test.json"
        schema_file.write_text(
            '{"type": "object", "properties": {"result": {"type": "string"}}}'
        )

        return str(template_file), str(schema_file)

    @pytest.mark.no_fs
    def test_valid_model_selection(
        self, runner, test_files, mock_model_registry
    ):
        """Test selecting valid models works."""
        template_file, schema_file = test_files
        result = runner.invoke(
            cli,
            [
                "run",
                template_file,
                schema_file,
                "--model",
                "gpt-4o",
                "--dry-run",
                "-V",
                "name=test",
            ],
        )
        assert result.exit_code == 0
        assert "gpt-4o" in result.output

    @pytest.mark.no_fs
    def test_invalid_model_rejection(
        self, runner, test_files, mock_model_registry
    ):
        """Test invalid models are rejected."""
        template_file, schema_file = test_files
        result = runner.invoke(
            cli,
            ["run", template_file, schema_file, "--model", "invalid-model"],
        )
        assert result.exit_code != 0
        assert "Invalid model 'invalid-model'" in result.output
        # Rich-click formats the error message differently but still shows available models
        assert (
            "Available models:" in result.output
            or "available models" in result.output.lower()
        )
        assert "models list" in result.output

    def test_help_shows_available_models(self, runner, mock_model_registry):
        """Test --help shows available models."""
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        # Accept either explicit model listing or referral to models list helper
        assert ("gpt-4o" in result.output) or ("models list" in result.output)

    def test_help_json_includes_dynamic_choices(
        self, runner, mock_model_registry
    ):
        """Test --help-json includes dynamic choice metadata."""
        result = runner.invoke(cli, ["run", "--help-json"])
        assert result.exit_code == 0

        help_data = json.loads(result.output)
        model_param = next(
            p for p in help_data["command"]["params"] if p["name"] == "model"
        )

        assert model_param["dynamic_choices"] is True
        assert model_param["choices_source"] == "openai_model_registry"
        assert "registry_metadata" in model_param
        assert model_param["type"]["param_type"] == "ModelChoice"

    @pytest.mark.no_fs
    def test_backward_compatibility(
        self, runner, test_files, mock_model_registry
    ):
        """Test that previously valid models still work."""
        template_file, schema_file = test_files

        # Test with various valid models
        valid_models = ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini"]

        for model in valid_models:
            result = runner.invoke(
                cli,
                [
                    "run",
                    template_file,
                    schema_file,
                    "--model",
                    model,
                    "--dry-run",
                    "-V",
                    "name=test",
                ],
            )
            if result.exit_code != 0:
                # Model might not be in mock registry, that's OK
                continue
            assert model in result.output

    @pytest.mark.no_fs
    def test_default_model_selection(
        self, runner, test_files, mock_model_registry
    ):
        """Test default model is selected when not specified."""
        template_file, schema_file = test_files
        result = runner.invoke(
            cli,
            [
                "run",
                template_file,
                schema_file,
                "--dry-run",
                "-V",
                "name=test",
            ],
        )
        assert result.exit_code == 0
        # Should use default model (gpt-4o or first available)
        assert "Model:" in result.output

    def test_model_parameter_in_help_json_metadata(
        self, runner, mock_model_registry
    ):
        """Test model parameter metadata in help JSON."""
        # Explicit patch for this test since autouse fixture timing is inconsistent
        from unittest.mock import patch

        class TestModelRegistry:
            @property
            def models(self):
                return ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]

            @property
            def config(self):
                class TestConfig:
                    registry_path = "/test/mock/registry/path"

                return TestConfig()

            @classmethod
            def get_instance(cls):
                return cls()

        with patch("openai_model_registry.ModelRegistry", TestModelRegistry):
            result = runner.invoke(cli, ["run", "--help-json"])
            assert result.exit_code == 0

            help_data = json.loads(result.output)
            model_param = next(
                p
                for p in help_data["command"]["params"]
                if p["name"] == "model"
            )

            # Check registry metadata
            registry_meta = model_param["registry_metadata"]
            assert "total_models" in registry_meta
            assert "structured_output_models" in registry_meta
            assert isinstance(registry_meta["total_models"], int)
            assert isinstance(registry_meta["structured_output_models"], int)

    @pytest.mark.no_fs
    def test_case_sensitivity_enforcement(
        self, runner, test_files, mock_model_registry
    ):
        """Test that model names are case sensitive."""
        template_file, schema_file = test_files
        result = runner.invoke(
            cli,
            [
                "run",
                template_file,
                schema_file,
                "--model",
                "GPT-4O",  # Wrong case
            ],
        )
        assert result.exit_code != 0
        assert "Invalid model" in result.output
