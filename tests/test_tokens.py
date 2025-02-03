"""Tests for token estimation and limits.

Important Notes on Testing with Tiktoken:
----------------------------------------
Tiktoken has a unique way of handling its encoding data files:

1. File Storage:
   - Tiktoken doesn't bundle encoding files with the package
   - Instead, it downloads them on first use and caches them locally
   - Cache location is determined by (in order):
     a. TIKTOKEN_CACHE_DIR environment variable
     b. DATA_GYM_CACHE_DIR environment variable
     c. Fallback: <temp_dir>/data-gym-cache

2. Testing with pyfakefs:
   - Since tiktoken needs to download and cache files, special handling is needed
   - We must allow access to:
     a. The tiktoken package directory (for the library code)
     b. The cache directory (for storing downloaded files)
     c. The temp directory (for initial downloads)
   - Network access must be temporarily enabled during initialization

3. Test Setup:
   - Use setup_tiktoken() method before any test that uses tiktoken
   - This ensures proper filesystem access and initialization
   - The method handles:
     a. Adding real directories to pyfakefs
     b. Creating cache directory if needed
     c. Temporarily enabling network access
     d. Initializing tiktoken with a base encoding
"""

import os
import tempfile
import textwrap
from typing import Dict, List, Literal, TypedDict, cast

import pytest
import tiktoken
from pyfakefs.fake_filesystem import FakeFilesystem

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

    def setup_tiktoken(self, fs: FakeFilesystem) -> None:
        """Set up tiktoken with proper filesystem access.

        This method handles the complex requirements of tiktoken in a test environment:

        1. File System Access:
           - Adds tiktoken's package directory to pyfakefs
           - Sets up and adds cache directory to pyfakefs
           - Adds temp directory for initial downloads

        2. Cache Directory:
           - Uses TIKTOKEN_CACHE_DIR or DATA_GYM_CACHE_DIR if set
           - Falls back to <temp_dir>/data-gym-cache
           - Creates directory if it doesn't exist

        3. Network Access:
           - Temporarily disables pyfakefs (fs.pause)
           - Allows tiktoken to download necessary files
           - Re-enables pyfakefs after initialization

        Args:
            fs: The pyfakefs fixture

        Note:
            This setup is required because tiktoken downloads its encoding files
            on first use and caches them locally. When running with pyfakefs,
            we need to ensure these operations can succeed while still maintaining
            test isolation.
        """
        # Allow access to tiktoken's files
        tiktoken_path = os.path.dirname(tiktoken.__file__)
        fs.add_real_directory(tiktoken_path)

        # Set up cache directory path
        cache_dir = os.environ.get("TIKTOKEN_CACHE_DIR") or os.environ.get(
            "DATA_GYM_CACHE_DIR"
        )
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "data-gym-cache")

        # Temporarily disable pyfakefs to create real directories and download files
        fs.pause()

        try:
            # Create real cache directory
            os.makedirs(cache_dir, exist_ok=True)

            # Force tiktoken to initialize its registry and download files
            try:
                tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                print("Error initializing cl100k_base:", str(e))
        finally:
            # Resume fake filesystem
            fs.resume()

        # Now add the real directories to pyfakefs, ignoring existing files
        try:
            fs.add_real_directory(cache_dir)
        except FileExistsError:
            pass

        try:
            fs.add_real_directory(tempfile.gettempdir())
        except FileExistsError:
            pass

    def test_estimate_tokens_basic(self, fs: FakeFilesystem) -> None:
        """Test basic token estimation for chat messages."""
        self.setup_tiktoken(fs)

        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]],
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
        )

        # Use real tiktoken for accurate token counting
        tokens = estimate_tokens_for_chat(messages, "gpt-4o")

        # We can assert it's within a reasonable range rather than exact number
        assert 10 <= tokens <= 30  # Reasonable range for these messages

    def test_estimate_tokens_with_name(self, fs: FakeFilesystem) -> None:
        """Test token estimation with name field."""
        self.setup_tiktoken(fs)

        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]],
            [{"role": "assistant", "name": "bot", "content": "Hello"}],
        )

        tokens = estimate_tokens_for_chat(messages, "gpt-4o")
        assert 5 <= tokens <= 15  # Reasonable range for this message

    def test_estimate_tokens_long_message(self, fs: FakeFilesystem) -> None:
        """Test token estimation with longer content."""
        self.setup_tiktoken(fs)

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

        tokens = estimate_tokens_for_chat(messages, "gpt-4o")
        assert tokens > 100  # Long message should be well over 100 tokens


class TestTokenLimits:
    """Test token limit functionality."""

    def test_context_window_limits(self) -> None:
        """Test context window limits for different models."""
        # Test gpt-4o model
        assert get_context_window_limit("gpt-4o") == 128_000
        assert get_context_window_limit("o1-mini") == 200_000
        assert get_context_window_limit("o3-mini") == 128_000

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


class TestTokenEdgeCases:
    """Test edge cases in token handling."""

    def setup_tiktoken(self, fs: FakeFilesystem) -> None:
        """Set up tiktoken with proper filesystem access."""
        # Allow access to tiktoken's files
        tiktoken_path = os.path.dirname(tiktoken.__file__)
        fs.add_real_directory(tiktoken_path)

        # Allow access to tiktoken's cache directory
        cache_dir = os.environ.get("TIKTOKEN_CACHE_DIR") or os.environ.get(
            "DATA_GYM_CACHE_DIR"
        )
        if not cache_dir:
            cache_dir = os.path.join(tempfile.gettempdir(), "data-gym-cache")

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Add real directories, ignoring existing files
        try:
            fs.add_real_directory(cache_dir)
        except FileExistsError:
            pass

        try:
            fs.add_real_directory(tempfile.gettempdir())
        except FileExistsError:
            pass

        # Allow network access for downloading encoding files
        fs.pause()

        # Force tiktoken to initialize its registry and download files
        try:
            tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            print("Error initializing cl100k_base:", str(e))

        # Resume fake filesystem after downloads
        fs.resume()

    def test_empty_messages(self, fs: FakeFilesystem) -> None:
        """Test token estimation with empty messages."""
        self.setup_tiktoken(fs)

        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]], [{"role": "user", "content": ""}]
        )
        tokens = estimate_tokens_for_chat(messages, "gpt-4o")
        assert tokens > 0  # Should still count message overhead

    def test_special_characters(self, fs: FakeFilesystem) -> None:
        """Test token estimation with special characters."""
        self.setup_tiktoken(fs)

        messages: List[Dict[str, str]] = cast(
            List[Dict[str, str]],
            [{"role": "user", "content": "Hello 👋 World! 🌍"}],
        )
        tokens = estimate_tokens_for_chat(messages, "gpt-4o")
        assert tokens > 5  # Emojis typically take multiple tokens

    def test_code_blocks(self, fs: FakeFilesystem) -> None:
        """Test token counting with code blocks."""
        self.setup_tiktoken(fs)

        code_message = textwrap.dedent(
            """
            def hello_world():
                print("Hello, world!")
                return 42
            """
        )
        tokens = estimate_tokens_for_chat(
            [{"role": "user", "content": code_message}], "gpt-4o"
        )
        # Code typically uses more tokens than words, so this is a basic sanity check
        assert tokens > len(
            code_message.split()
        )  # Code typically uses more tokens than words
