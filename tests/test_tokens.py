"""Tests for token estimation and limits."""

from typing import Dict, List, Literal, TypedDict, cast

import pytest

from ostruct.cli.cli import (
    estimate_tokens_for_chat,
    get_context_window_limit,
    validate_token_limits,
)


class ChatMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant"]
    content: str
    name: str


class TestTokenEstimation:
    """Test token estimation functionality."""

    def test_estimate_tokens_basic(self) -> None:
        """Test basic token estimation for chat messages."""
        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]],
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
        )

        # Use real tiktoken for accurate token counting
        tokens = estimate_tokens_for_chat(messages, "gpt-4o-2024-08-06")

        # We can assert it's within a reasonable range rather than exact number
        assert 10 <= tokens <= 30  # Reasonable range for these messages

    def test_estimate_tokens_with_name(self) -> None:
        """Test token estimation with name field."""
        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]],
            [{"role": "assistant", "name": "bot", "content": "Hello"}],
        )

        tokens = estimate_tokens_for_chat(messages, "gpt-4o-2024-08-06")
        assert 5 <= tokens <= 15  # Reasonable range for this message

    def test_estimate_tokens_long_message(self) -> None:
        """Test token estimation with longer content."""
        long_content = (
            "This is a longer message that should be more than twenty tokens. "
            "It includes various words and phrases to ensure we exceed the token threshold. "
            "We need to make sure this message is long enough to properly test our token "
            "estimation functionality. Let's add some technical terms like machine learning, "
            "artificial intelligence, and natural language processing to make it more realistic."
        ) * 2
        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]], [{"role": "user", "content": long_content}]
        )

        tokens = estimate_tokens_for_chat(messages, "gpt-4o-2024-08-06")
        assert tokens > 100  # Long message should be well over 100 tokens


class TestTokenLimits:
    """Test token limit functionality."""

    def test_context_window_limits(self) -> None:
        """Test context window limits for different models."""
        # Test gpt-4o model
        assert get_context_window_limit("gpt-4o-2024-08-06") == 128_000
        assert get_context_window_limit("gpt-4o-mini-2024-07-18") == 128_000
        assert get_context_window_limit("o1-2024-12-17") == 200_000

    def test_validate_token_limits_success(self) -> None:
        """Test successful token limit validation."""
        # Test with default limit
        validate_token_limits("gpt-4o-2024-08-06", total_tokens=1000)

        # Test with custom limit
        validate_token_limits(
            "gpt-4o-2024-08-06", total_tokens=1000, max_token_limit=5000
        )

    def test_validate_token_limits_exceed_context(self) -> None:
        """Test validation when exceeding context window."""
        with pytest.raises(ValueError) as exc_info:
            validate_token_limits("gpt-4o-2024-08-06", total_tokens=130_000)
        assert "exceed model's context window limit" in str(exc_info.value)

    def test_validate_token_limits_insufficient_room(self) -> None:
        """Test validation when insufficient room for output."""
        with pytest.raises(ValueError) as exc_info:
            validate_token_limits("gpt-4o-2024-08-06", total_tokens=127_000)
        assert "remaining in context window" in str(exc_info.value)


class TestTokenEdgeCases:
    """Test edge cases in token handling."""

    def test_empty_messages(self) -> None:
        """Test token estimation with empty messages."""
        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]], [{"role": "user", "content": ""}]
        )
        tokens = estimate_tokens_for_chat(messages, "gpt-4o-2024-08-06")
        assert tokens > 0  # Should still count message overhead

    def test_special_characters(self) -> None:
        """Test token estimation with special characters."""
        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]],
            [{"role": "user", "content": "Hello 👋 World! 🌍"}],
        )
        tokens = estimate_tokens_for_chat(messages, "gpt-4o-2024-08-06")
        assert tokens > 5  # Emojis typically take multiple tokens

    def test_code_blocks(self) -> None:
        """Test token estimation with code blocks."""
        code_message = """{"role": "user", "content": "```python\ndef hello():\n    print('world')\n```"}"""
        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]], [{"role": "user", "content": code_message}]
        )
        tokens = estimate_tokens_for_chat(messages, "gpt-4o-2024-08-06")
        assert tokens > len(
            code_message.split()
        )  # Code typically uses more tokens than words
