"""Tests for TTL configuration functionality."""

import os
import tempfile

import pytest

from src.ostruct.cli.config import OstructConfig, UploadConfig


class TestUploadConfig:
    """Test UploadConfig dataclass functionality."""

    def test_default_values(self):
        """Test default configuration values."""
        config = UploadConfig()

        assert config.persistent_cache is True
        assert config.preserve_cached_files is True
        assert config.cache_max_age_days == 14
        assert config.cache_path is None
        assert config.hash_algorithm == "sha256"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = UploadConfig(
            persistent_cache=False,
            preserve_cached_files=False,
            cache_max_age_days=7,
            cache_path="/custom/path/cache.db",
            hash_algorithm="md5",
        )

        assert config.persistent_cache is False
        assert config.preserve_cached_files is False
        assert config.cache_max_age_days == 7
        assert config.cache_path == "/custom/path/cache.db"
        assert config.hash_algorithm == "md5"

    def test_cache_max_age_days_validation(self):
        """Test validation of cache_max_age_days."""
        # Valid values
        UploadConfig(cache_max_age_days=0)  # Should not raise
        UploadConfig(cache_max_age_days=30)  # Should not raise

        # Invalid values
        with pytest.raises(
            ValueError, match="cache_max_age_days must be non-negative"
        ):
            UploadConfig(cache_max_age_days=-1)

    def test_hash_algorithm_validation(self):
        """Test validation of hash_algorithm."""
        # Valid algorithms
        UploadConfig(hash_algorithm="sha256")  # Should not raise
        UploadConfig(hash_algorithm="sha1")  # Should not raise
        UploadConfig(hash_algorithm="md5")  # Should not raise

        # Invalid algorithm
        with pytest.raises(ValueError, match="hash_algorithm must be one of"):
            UploadConfig(hash_algorithm="invalid")


class TestOstructConfigTTL:
    """Test OstructConfig TTL integration."""

    def test_upload_config_default(self):
        """Test that OstructConfig includes upload config with defaults."""
        config = OstructConfig()

        upload_config = config.get_upload_config()
        assert isinstance(upload_config, UploadConfig)
        assert upload_config.cache_max_age_days == 14
        assert upload_config.preserve_cached_files is True

    def test_config_from_yaml(self):
        """Test loading TTL config from YAML file."""
        yaml_content = """
uploads:
  persistent_cache: true
  preserve_cached_files: false
  cache_max_age_days: 7
  cache_path: /custom/cache.db
  hash_algorithm: sha1
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = OstructConfig.load(config_path)
            upload_config = config.get_upload_config()

            assert upload_config.persistent_cache is True
            assert upload_config.preserve_cached_files is False
            assert upload_config.cache_max_age_days == 7
            assert upload_config.cache_path == "/custom/cache.db"
            assert upload_config.hash_algorithm == "sha1"
        finally:
            os.unlink(config_path)

    def test_environment_variable_overrides(self):
        """Test environment variable overrides for upload config."""
        # Set environment variables
        env_vars = {
            "OSTRUCT_CACHE_UPLOADS": "false",
            "OSTRUCT_PRESERVE_CACHED_FILES": "false",
            "OSTRUCT_CACHE_MAX_AGE_DAYS": "30",
            "OSTRUCT_CACHE_PATH": "/env/cache.db",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("uploads:\n  cache_max_age_days: 14\n")  # Base config
            config_path = f.name

        try:
            # Patch environment
            with pytest.MonkeyPatch().context() as m:
                for key, value in env_vars.items():
                    m.setenv(key, value)

                config = OstructConfig.load(config_path)
                upload_config = config.get_upload_config()

                assert upload_config.persistent_cache is False  # From env
                assert upload_config.preserve_cached_files is False  # From env
                assert upload_config.cache_max_age_days == 30  # From env
                assert upload_config.cache_path == "/env/cache.db"  # From env
        finally:
            os.unlink(config_path)

    def test_invalid_env_var_handling(self):
        """Test handling of invalid environment variable values."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("uploads: {}\n")
            config_path = f.name

        try:
            with pytest.MonkeyPatch().context() as m:
                # Set invalid cache_max_age_days
                m.setenv("OSTRUCT_CACHE_MAX_AGE_DAYS", "invalid")

                # Should not raise exception, should ignore invalid value
                config = OstructConfig.load(config_path)
                upload_config = config.get_upload_config()

                # Should use default value
                assert upload_config.cache_max_age_days == 14
        finally:
            os.unlink(config_path)

    def test_privacy_compliance_options(self):
        """Test privacy/compliance configuration options."""
        # Test immediate deletion (cache_max_age_days=0)
        config = OstructConfig(uploads=UploadConfig(cache_max_age_days=0))
        upload_config = config.get_upload_config()
        assert upload_config.cache_max_age_days == 0

        # Test disabled preservation
        config = OstructConfig(
            uploads=UploadConfig(preserve_cached_files=False)
        )
        upload_config = config.get_upload_config()
        assert upload_config.preserve_cached_files is False

    def test_backward_compatibility(self):
        """Test that existing configs without TTL settings work."""
        yaml_content = """
models:
  default: gpt-4o

uploads:
  persistent_cache: true
  hash_algorithm: sha256
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            config_path = f.name

        try:
            config = OstructConfig.load(config_path)
            upload_config = config.get_upload_config()

            # Should use defaults for new TTL fields
            assert upload_config.preserve_cached_files is True
            assert upload_config.cache_max_age_days == 14

            # Should preserve existing fields
            assert upload_config.persistent_cache is True
            assert upload_config.hash_algorithm == "sha256"
        finally:
            os.unlink(config_path)

    def test_cost_optimization_scenarios(self):
        """Test configuration for different cost optimization scenarios."""
        # High-frequency development (shorter TTL)
        dev_config = UploadConfig(cache_max_age_days=3)
        assert dev_config.cache_max_age_days == 3

        # Production/CI (longer TTL for stability)
        prod_config = UploadConfig(cache_max_age_days=30)
        assert prod_config.cache_max_age_days == 30

        # Compliance (immediate deletion)
        compliance_config = UploadConfig(
            preserve_cached_files=False, cache_max_age_days=0
        )
        assert compliance_config.preserve_cached_files is False
        assert compliance_config.cache_max_age_days == 0
