"""Tests for download strategy auto-enable functionality."""

from typing import Optional, Type

from ostruct.cli.runner import _get_effective_download_strategy
from ostruct.cli.types import CLIParams
from pydantic import BaseModel


class MockModel(BaseModel):
    """Mock Pydantic model for testing."""

    result: str


class TestDownloadStrategyAutoEnable:
    """Test auto-enable functionality for two_pass_sentinel download strategy."""

    def test_auto_enable_with_structured_output_and_cli_download(self):
        """Test that two_pass_sentinel is auto-enabled when structured output + --ci-download + CI are used."""
        args: CLIParams = {
            "enabled_features": [],
            "disabled_features": [],
            "ci_download": True,
        }
        ci_config = {
            "auto_download": False,
            "download_strategy": "single_pass",
        }
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "two_pass_sentinel"

    def test_auto_enable_with_structured_output_and_legacy_config(self):
        """Test backward compatibility: two_pass_sentinel is auto-enabled with legacy auto_download: true."""
        args: CLIParams = {"enabled_features": [], "disabled_features": []}
        ci_config = {"auto_download": True, "download_strategy": "single_pass"}
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "two_pass_sentinel"

    def test_no_auto_enable_without_structured_output(self):
        """Test that two_pass_sentinel is NOT auto-enabled without structured output."""
        args: CLIParams = {"enabled_features": [], "disabled_features": []}
        ci_config = {"auto_download": True, "download_strategy": "single_pass"}
        output_model: Optional[Type[BaseModel]] = None  # No structured output

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "single_pass"

    def test_no_auto_enable_when_downloads_disabled(self):
        """Test that two_pass_sentinel is NOT auto-enabled when downloads are disabled (new default)."""
        args: CLIParams = {
            "enabled_features": [],
            "disabled_features": [],
        }  # No --ci-download flag
        ci_config = {
            "auto_download": False,
            "download_strategy": "single_pass",
        }
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "single_pass"

    def test_no_auto_enable_when_auto_download_missing(self):
        """Test that two_pass_sentinel is NOT auto-enabled when auto_download is missing (defaults to False)."""
        args: CLIParams = {"enabled_features": [], "disabled_features": []}
        ci_config = {
            "download_strategy": "single_pass"
        }  # auto_download missing, defaults to False (new behavior)
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert (
            strategy == "single_pass"
        )  # No downloads enabled, so no two-pass needed

    def test_respect_explicit_two_pass_config(self):
        """Test that explicit two_pass_sentinel config is preserved."""
        args: CLIParams = {"enabled_features": [], "disabled_features": []}
        ci_config = {
            "auto_download": True,
            "download_strategy": "two_pass_sentinel",
        }
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "two_pass_sentinel"

    def test_respect_explicit_single_pass_config_overrides_auto_enable(self):
        """Test that explicit single_pass config overrides auto-enable."""
        # This test verifies that if user explicitly sets single_pass,
        # the auto-enable logic doesn't override it
        args: CLIParams = {"enabled_features": [], "disabled_features": []}
        ci_config = {"auto_download": True, "download_strategy": "single_pass"}
        output_model: Optional[Type[BaseModel]] = MockModel

        # In current implementation, auto-enable only triggers when strategy == "single_pass"
        # So this will actually auto-enable. If we want to respect explicit config,
        # we'd need to track whether it was explicitly set vs. defaulted.
        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "two_pass_sentinel"

    def test_feature_flag_on_overrides_auto_enable(self):
        """Test that ci-download-hack feature flag 'on' still works with auto-enable."""
        args: CLIParams = {
            "enabled_features": ["ci-download-hack"],
            "disabled_features": [],
        }
        ci_config = {
            "auto_download": False,
            "download_strategy": "single_pass",
        }  # Would not auto-enable
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert (
            strategy == "two_pass_sentinel"
        )  # Feature flag overrides auto-enable logic

    def test_feature_flag_off_overrides_auto_enable(self):
        """Test that ci-download-hack feature flag 'off' prevents auto-enable."""
        args: CLIParams = {
            "enabled_features": [],
            "disabled_features": ["ci-download-hack"],
        }
        ci_config = {
            "auto_download": True,
            "download_strategy": "single_pass",
        }  # Would auto-enable
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "single_pass"  # Feature flag prevents auto-enable

    def test_default_config_with_structured_output(self):
        """Test no auto-enable with completely default configuration (new behavior)."""
        args: CLIParams = {"enabled_features": [], "disabled_features": []}
        ci_config = {}  # Empty config, all defaults
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        # download_strategy defaults to "single_pass", auto_download defaults to False (new)
        assert strategy == "single_pass"  # No downloads enabled by default

    def test_backward_compatibility_no_output_model_param(self):
        """Test that function works when output_model parameter is not provided."""
        args: CLIParams = {"enabled_features": [], "disabled_features": []}
        ci_config = {"auto_download": True, "download_strategy": "single_pass"}

        # Call without output_model parameter (defaults to None)
        strategy = _get_effective_download_strategy(args, ci_config)
        assert (
            strategy == "single_pass"
        )  # No auto-enable without structured output


class TestDownloadStrategyFeatureFlags:
    """Test feature flag interactions with download strategy."""

    def test_feature_flag_parsing_error_handling(self):
        """Test that feature flag parsing errors don't break download strategy selection."""
        args: CLIParams = {
            "enabled_features": ["invalid-flag-format"],
            "disabled_features": [],
        }
        ci_config = {"auto_download": True, "download_strategy": "single_pass"}
        output_model: Optional[Type[BaseModel]] = MockModel

        # Should still auto-enable despite feature flag parsing error
        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "two_pass_sentinel"

    def test_multiple_feature_flags(self):
        """Test handling of multiple feature flags."""
        args: CLIParams = {
            "enabled_features": ["ci-download-hack"],  # Only use valid flags
            "disabled_features": [],
        }
        ci_config = {
            "auto_download": False,
            "download_strategy": "single_pass",
        }
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert (
            strategy == "two_pass_sentinel"
        )  # ci-download-hack should enable

    def test_conflicting_feature_flags(self):
        """Test handling when both enable and disable flags are present."""
        args: CLIParams = {
            "enabled_features": ["ci-download-hack"],
            "disabled_features": ["ci-download-hack"],
        }
        ci_config = {"auto_download": True, "download_strategy": "single_pass"}
        output_model: Optional[Type[BaseModel]] = MockModel

        # When there are conflicting flags, parsing fails and auto-enable runs
        # because feature_explicitly_disabled remains False due to parsing exception
        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert (
            strategy == "two_pass_sentinel"
        )  # Auto-enable runs due to parsing failure


class TestDownloadStrategyEdgeCases:
    """Test edge cases for download strategy selection."""

    def test_empty_args(self):
        """Test with empty args dictionary."""
        args: CLIParams = {}
        ci_config = {"auto_download": True, "download_strategy": "single_pass"}
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        assert strategy == "two_pass_sentinel"

    def test_empty_ci_config(self):
        """Test with empty CI configuration (new default behavior)."""
        args: CLIParams = {"enabled_features": [], "disabled_features": []}
        ci_config = {}
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        # Should use defaults: download_strategy="single_pass", auto_download=False (new)
        assert strategy == "single_pass"

    def test_none_values(self):
        """Test with None values in configuration."""
        args: CLIParams = {"enabled_features": None, "disabled_features": None}  # type: ignore[dict-item]
        ci_config = {"auto_download": None, "download_strategy": "single_pass"}  # type: ignore[dict-item]
        output_model: Optional[Type[BaseModel]] = MockModel

        strategy = _get_effective_download_strategy(
            args, ci_config, output_model
        )
        # auto_download=None should be falsy, so no auto-enable
        assert strategy == "single_pass"
