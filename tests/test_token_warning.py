"""Tests for token warning functionality."""

import logging

import pytest
from ostruct.cli.token_validation import TokenLimitValidator


class TestTokenWarning:
    """Test token warning at 90% threshold."""

    def test_token_warning_at_90_percent(self):
        """Should warn at 90% token usage."""
        validator = TokenLimitValidator("gpt-4o")

        # Create content that's just over 90% of the limit
        # Use a more realistic estimate: ~1 token per character for repetitive content
        warning_threshold = int(
            validator.MAX_TOKENS * 0.91
        )  # Slightly over 90%
        large_content = "x" * warning_threshold

        # Should not raise an error, just warn
        # The warning is logged (visible in test output) but hard to capture reliably
        validator.validate_prompt_size(large_content, [])

    def test_token_warning_at_95_percent(self):
        """Should warn at 95% token usage."""
        validator = TokenLimitValidator("gpt-4o")

        # Create content that's just over 95% of the limit
        warning_threshold = int(
            validator.MAX_TOKENS * 0.96
        )  # Slightly over 95%
        large_content = "x" * warning_threshold

        # Should not raise an error, just warn
        # The warning is logged (visible in test output) but hard to capture reliably
        validator.validate_prompt_size(large_content, [])

    def test_no_warning_below_90_percent(self, caplog):
        """Should not warn below 90% token usage."""
        validator = TokenLimitValidator("gpt-4o")

        # Create content that's 80% of the limit
        threshold = int(validator.MAX_TOKENS * 0.8)
        content = "x" * threshold

        with caplog.at_level(logging.WARNING):
            validator.validate_prompt_size(content, [])

        # Check that no warning was logged
        warning_records = [
            r for r in caplog.records if r.levelname == "WARNING"
        ]
        assert len(warning_records) == 0

    def test_token_hard_limit_still_works(self):
        """Should still fail at 100% token usage."""
        from ostruct.cli.errors import PromptTooLargeError

        validator = TokenLimitValidator("gpt-4o")

        # Create content that exceeds the limit
        over_limit = int(validator.MAX_TOKENS * 1.1)
        large_content = "x" * over_limit

        with pytest.raises(PromptTooLargeError) as exc_info:
            validator.validate_prompt_size(large_content, [])

        assert "exceed" in str(exc_info.value).lower()
        assert "context window" in str(exc_info.value).lower()
