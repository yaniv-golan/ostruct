"""Tests for configuration management."""

import os
from unittest.mock import Mock, patch

import pytest
import yaml

from ostruct.cli.config import OstructConfig, get_config


class TestOstructConfig:
    """Test configuration loading and management."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OstructConfig()

        assert config.models.default == "gpt-4o"
        assert config.tools.code_interpreter["auto_download"] is True
        assert config.tools.file_search["max_results"] == 10
        assert config.operation.timeout_minutes == 60
        assert config.limits.max_cost_per_run == 10.00

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid configuration
        config_data = {
            "models": {"default": "gpt-4o"},
            "operation": {"require_approval": "never"},
        }
        config = OstructConfig(**config_data)
        assert config.operation.require_approval == "never"

        # Invalid approval setting
        with pytest.raises(
            ValueError, match="require_approval must be one of"
        ):
            OstructConfig(operation={"require_approval": "invalid"})

    @pytest.mark.no_fs
    def test_load_from_file(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "test_config.yaml"
        config_data = {
            "models": {"default": "gpt-4o-mini"},
            "tools": {
                "code_interpreter": {"auto_download": False},
                "file_search": {"max_results": 20},
            },
            "limits": {"max_cost_per_run": 5.00},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = OstructConfig.load(config_file)
        assert config.models.default == "gpt-4o-mini"
        assert config.tools.code_interpreter["auto_download"] is False
        assert config.tools.file_search["max_results"] == 20
        assert config.limits.max_cost_per_run == 5.00

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file returns defaults."""
        config = OstructConfig.load("nonexistent.yaml")
        assert config.models.default == "gpt-4o"

    @pytest.mark.no_fs
    def test_invalid_yaml_file(self, tmp_path):
        """Test handling of invalid YAML file."""
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        # Should return defaults when YAML is invalid
        config = OstructConfig.load(config_file)
        assert config.models.default == "gpt-4o"

    @patch.dict(os.environ, {"MCP_STRIPE_URL": "https://custom.stripe.com"})
    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        # Test the _apply_env_overrides method directly to avoid filesystem issues
        config_data = {}
        result = OstructConfig._apply_env_overrides(config_data)

        assert "mcp" in result
        assert result["mcp"].get("stripe") == "https://custom.stripe.com"

    @patch.dict(os.environ, {"MCP_CUSTOM_URL": "https://custom.mcp.com"})
    def test_mcp_environment_variables(self):
        """Test MCP environment variable processing."""
        # Test the _apply_env_overrides method directly to avoid filesystem issues
        config_data = {}
        result = OstructConfig._apply_env_overrides(config_data)

        assert "mcp" in result
        assert result["mcp"].get("custom") == "https://custom.mcp.com"

    def test_get_methods(self):
        """Test configuration getter methods."""
        config = OstructConfig()

        assert config.get_model_default() == "gpt-4o"
        assert isinstance(config.get_mcp_servers(), dict)
        assert isinstance(config.get_code_interpreter_config(), dict)
        assert isinstance(config.get_file_search_config(), dict)

    def test_approval_logic(self):
        """Test approval requirement logic."""
        config = OstructConfig()

        # Never require approval
        config.operation.require_approval = "never"
        assert not config.should_require_approval(1.0)
        assert not config.should_require_approval(10.0)

        # Always require approval
        config.operation.require_approval = "always"
        assert config.should_require_approval(0.1)
        assert config.should_require_approval(10.0)

        # Expensive operations only
        config.operation.require_approval = "expensive"
        assert not config.should_require_approval(1.0)  # Below threshold
        assert config.should_require_approval(8.0)  # Above threshold

    def test_cost_limits(self):
        """Test cost limit checking."""
        config = OstructConfig()
        config.limits.max_cost_per_run = 5.00

        assert config.is_within_cost_limits(3.0)
        assert config.is_within_cost_limits(5.0)
        assert not config.is_within_cost_limits(6.0)

    def test_warning_thresholds(self):
        """Test expensive operation warnings."""
        config = OstructConfig()
        config.limits.max_cost_per_run = 10.0
        config.limits.warn_expensive_operations = True

        assert not config.should_warn_expensive(1.0)  # Below threshold
        assert config.should_warn_expensive(4.0)  # Above 30% threshold

        config.limits.warn_expensive_operations = False
        assert not config.should_warn_expensive(4.0)  # Warnings disabled

    @pytest.mark.no_fs
    def test_config_discovery(self, tmp_path):
        """Test automatic configuration file discovery."""
        # Test current directory discovery
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            config_file = tmp_path / "ostruct.yaml"
            config_data = {"models": {"default": "gpt-4o-mini"}}

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            config = OstructConfig.load()
            assert config.models.default == "gpt-4o-mini"

        finally:
            os.chdir(original_cwd)

    @pytest.mark.no_fs
    def test_home_directory_config(self, tmp_path, monkeypatch):
        """Test home directory configuration discovery."""
        # Mock home directory
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))

        # Create config in home directory
        config_dir = fake_home / ".ostruct"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_data = {"models": {"default": "gpt-4o-mini"}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock Path.home() to return our fake home
        with patch("pathlib.Path.home", return_value=fake_home):
            config = OstructConfig.load()
            assert config.models.default == "gpt-4o-mini"


class TestGetConfig:
    """Test global configuration function."""

    def test_get_config_returns_instance(self):
        """Test that get_config returns a valid instance."""
        config = get_config()
        assert isinstance(config, OstructConfig)
        assert config.models.default == "gpt-4o"


class TestConfigurationIntegration:
    """Test configuration integration with CLI."""

    @patch("ostruct.cli.config.OstructConfig.load")
    def test_config_loading_in_cli(self, mock_load):
        """Test configuration loading integration."""
        mock_config = Mock()
        mock_config.get_model_default.return_value = "gpt-4o-mini"
        mock_load.return_value = mock_config

        # Test that config is loaded correctly
        get_config()
        mock_load.assert_called_once()

    def test_example_config_content(self):
        """Test that example configuration is valid."""
        from ostruct.cli.config import create_example_config

        example_content = create_example_config()
        assert "models:" in example_content
        assert "gpt-4o" in example_content
        assert "tools:" in example_content
        assert "mcp:" in example_content

        # Validate it's valid YAML
        config_data = yaml.safe_load(example_content)
        assert isinstance(config_data, dict)
        assert "models" in config_data
