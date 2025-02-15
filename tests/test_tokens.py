"""Tests for token limits.

Note on tiktoken:
---------------
Token estimation tests have been removed due to issues with tiktoken's
filesystem access through Rust/C bindings, which cannot be properly mocked
or intercepted by pyfakefs.

Only token limit validation tests are included here since they don't rely
on tiktoken's encoding functionality.
"""

import pytest
from openai_structured.model_registry import ModelRegistry

from ostruct.cli.cli import validate_token_limits

# Get the model registry instance for testing
model_registry = ModelRegistry()
get_context_window_limit = model_registry.get_context_window


class TestTokenLimits:
    """Test token limit functionality."""

    def test_context_window_limits(self) -> None:
        """Test context window limits for different models."""
        # Test gpt-4o model
        assert get_context_window_limit("gpt-4o") == 128_000
        assert get_context_window_limit("o1") == 200_000
        assert get_context_window_limit("o3-mini") == 200_000

    def test_validate_token_limits_success(self) -> None:
        """Test successful token limit validation."""
        # Test with default limit
        validate_token_limits("gpt-4o", total_tokens=1000)

        # Test with custom limit
        validate_token_limits(
            "gpt-4o", total_tokens=1000, max_token_limit=5000
        )

    def test_validate_token_limits_exceed_context(self) -> None:
        """Test validation when exceeding context window."""
        with pytest.raises(ValueError) as exc_info:
            validate_token_limits("gpt-4o", total_tokens=130_000)
        assert "exceed model's context window limit" in str(exc_info.value)

    def test_validate_token_limits_insufficient_room(self) -> None:
        """Test validation when insufficient room for output."""
        with pytest.raises(ValueError) as exc_info:
            validate_token_limits("gpt-4o", total_tokens=127_000)
        assert "remaining in context window" in str(exc_info.value)
