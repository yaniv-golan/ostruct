"""Tests for client utilities."""

import os
from unittest.mock import patch

import pytest
from openai import AsyncOpenAI

from src.ostruct.cli.errors import CLIError
from src.ostruct.cli.exit_codes import ExitCode
from src.ostruct.cli.utils.client_utils import create_openai_client


class TestCreateOpenAIClient:
    """Test the create_openai_client function."""

    def test_success_with_env_var(self):
        """Test successful client creation with environment variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-from-env"}):
            client = create_openai_client()

            assert isinstance(client, AsyncOpenAI)
            assert client.api_key == "test-key-from-env"
            assert client.timeout == 60.0

    def test_success_with_explicit_key(self):
        """Test successful client creation with explicit API key."""
        with patch.dict(os.environ, {}, clear=True):
            client = create_openai_client(api_key="explicit-test-key")

            assert isinstance(client, AsyncOpenAI)
            assert client.api_key == "explicit-test-key"
            assert client.timeout == 60.0

    def test_explicit_key_overrides_env(self):
        """Test that explicit API key takes precedence over environment variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            client = create_openai_client(api_key="explicit-key")

            assert client.api_key == "explicit-key"

    def test_custom_timeout(self):
        """Test client creation with custom timeout."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = create_openai_client(timeout=120.0)

            assert client.timeout == 120.0

    def test_timeout_capped_at_max(self):
        """Test that timeout is capped at max_timeout."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = create_openai_client(timeout=999.0)

            assert client.timeout == 300.0  # Default max_timeout

    def test_custom_max_timeout(self):
        """Test client creation with custom max_timeout."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = create_openai_client(timeout=999.0, max_timeout=500.0)

            assert client.timeout == 500.0

    def test_timeout_under_max_not_capped(self):
        """Test that timeout under max is not modified."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = create_openai_client(timeout=200.0, max_timeout=300.0)

            assert client.timeout == 200.0

    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises CLIError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(CLIError) as exc_info:
                create_openai_client()

            assert exc_info.value.exit_code == ExitCode.API_ERROR
            assert "No OpenAI API key found" in str(exc_info.value)
            assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_error_message_contains_helpful_instructions(self):
        """Test that error message contains helpful instructions."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(CLIError) as exc_info:
                create_openai_client()

            error_msg = str(exc_info.value)
            assert "Set OPENAI_API_KEY environment variable" in error_msg
            assert ".env file" in error_msg
            assert "--api-key option" in error_msg
            assert "https://platform.openai.com/api-keys" in error_msg

    def test_default_timeout_value(self):
        """Test that default timeout is 60.0 seconds."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = create_openai_client()

            assert client.timeout == 60.0

    def test_zero_timeout_allowed(self):
        """Test that zero timeout is allowed."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client = create_openai_client(timeout=0.0)

            assert client.timeout == 0.0
