"""ReDoS-safe regex patterns and utilities."""

import re
import signal
from typing import Any, List, Optional, Pattern, Union


class RegexTimeoutError(Exception):
    """Raised when regex execution times out."""

    pass


def _timeout_handler(signum: int, frame: Any) -> None:
    """Signal handler for regex timeout."""
    raise RegexTimeoutError("Regex execution timed out")


def safe_regex_search(
    pattern: Union[str, Pattern[str]],
    text: str,
    timeout: float = 1.0,
    flags: int = 0,
) -> Optional[re.Match[str]]:
    """Perform regex search with timeout protection.

    Args:
        pattern: Regex pattern to search for
        text: Text to search in
        timeout: Maximum execution time in seconds
        flags: Regex flags

    Returns:
        Match object if found, None otherwise

    Raises:
        RegexTimeoutError: If regex execution times out
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern, flags)

    # Set up timeout handler
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(int(timeout))

    try:
        return pattern.search(text)
    except RegexTimeoutError:
        raise
    finally:
        signal.alarm(0)  # Cancel timeout
        signal.signal(signal.SIGALRM, old_handler)  # Restore old handler


def safe_regex_findall(
    pattern: Union[str, Pattern[str]],
    text: str,
    timeout: float = 1.0,
    flags: int = 0,
) -> List[str]:
    """Perform regex findall with timeout protection.

    Args:
        pattern: Regex pattern to search for
        text: Text to search in
        timeout: Maximum execution time in seconds
        flags: Regex flags

    Returns:
        List of matches

    Raises:
        RegexTimeoutError: If regex execution times out
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern, flags)

    # Set up timeout handler
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(int(timeout))

    try:
        return pattern.findall(text)
    except RegexTimeoutError:
        raise
    finally:
        signal.alarm(0)  # Cancel timeout
        signal.signal(signal.SIGALRM, old_handler)  # Restore old handler


def safe_regex_sub(
    pattern: Union[str, Pattern[str]],
    repl: str,
    text: str,
    timeout: float = 1.0,
    flags: int = 0,
) -> str:
    """Perform regex substitution with timeout protection.

    Args:
        pattern: Regex pattern to search for
        repl: Replacement string
        text: Text to search in
        timeout: Maximum execution time in seconds
        flags: Regex flags

    Returns:
        Text with substitutions made

    Raises:
        RegexTimeoutError: If regex execution times out
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern, flags)

    # Set up timeout handler
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(int(timeout))

    try:
        return pattern.sub(repl, text)
    except RegexTimeoutError:
        raise
    finally:
        signal.alarm(0)  # Cancel timeout
        signal.signal(signal.SIGALRM, old_handler)  # Restore old handler


# ReDoS-safe patterns for common use cases

# Safe JSON extraction pattern - limits nesting depth
SAFE_JSON_BLOCK_PATTERN = re.compile(
    r"```json\s*\n?"
    r"(\{(?:[^{}]|(?:\{[^{}]*\})){0,10}\})"  # Limit nesting to 10 levels
    r"\n?\s*```",
    re.DOTALL | re.MULTILINE,
)

# Safe sentinel pattern - limits content length
SAFE_SENTINEL_PATTERN = re.compile(
    r"===BEGIN_JSON===\s*"
    r"(\{[^{}]{0,10000}(?:\{[^{}]{0,1000}\}[^{}]{0,1000}){0,10}\})"  # Limit complexity
    r"\s*===END_JSON===",
    re.DOTALL,
)

# Safe Unicode safety pattern - atomic groups to prevent backtracking
SAFE_UNICODE_PATTERN = re.compile(
    r"[\u0000-\u001F\u007F-\u009F\u2028-\u2029\u0085]"  # Control chars
    r"|(?:^|/)\.\.(?:/|$)"  # Directory traversal (atomic)
    r"|[\u2024\u2025\u2026\uFE19\uFE30\uFE52\uFF0E\uFF61]"  # Alt dots
    r"|[\u200B-\u200D\uFEFF]"  # Zero-width chars
    r"|[\u2044\u2215\uFF0F]"  # Alt slashes
    r"|[\u02F8\u0589\u05C3\uFE52\uFF0E]"  # Additional homographs
)

# Safe patterns for Windows paths
SAFE_WINDOWS_DEVICE_PATTERN = re.compile(
    r"^(?:\\\\|//)[?.](?:\\|/)(?!UNC(?:\\|/))", re.IGNORECASE
)

SAFE_WINDOWS_DRIVE_PATTERN = re.compile(
    r"^[A-Za-z]:(?![/\\])",  # Drive letter without separator
    re.IGNORECASE,
)

SAFE_WINDOWS_RESERVED_PATTERN = re.compile(
    r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.IGNORECASE
)

SAFE_WINDOWS_UNC_PATTERN = re.compile(
    r"^(?:\\\\|//)[^?./\\][^/\\]*(?:\\|/)[^/\\]+", re.IGNORECASE
)

SAFE_WINDOWS_INCOMPLETE_UNC_PATTERN = re.compile(
    r"^(?:\\\\|//)[^?./\\][^/\\]*(?:\\|/)?\s*$", re.IGNORECASE
)

SAFE_WINDOWS_ADS_PATTERN = re.compile(
    r"(?<!^[A-Za-z]):[^:]{1,255}$"  # Limit ADS name length, but not drive letters
)

SAFE_WINDOWS_INVALID_CHARS_PATTERN = re.compile(
    r'[<>:"|?*\x00-\x1F]'  # Invalid characters (atomic)
)

SAFE_WINDOWS_TRAILING_PATTERN = re.compile(
    r"[. ]{1,10}$"  # Limit trailing chars to prevent ReDoS
)

# Safe credential patterns
SAFE_API_KEY_PATTERN = re.compile(
    r"sk-[a-zA-Z0-9]{20,50}",  # Limit length to prevent ReDoS
    re.IGNORECASE,
)

SAFE_BEARER_TOKEN_PATTERN = re.compile(
    r"bearer\s+([a-zA-Z0-9_-]{20,100})",  # Limit length
    re.IGNORECASE,
)

SAFE_URL_CREDENTIALS_PATTERN = re.compile(
    r"https?://[^:]{1,100}:([^@]{1,100})@",  # Limit lengths
    re.IGNORECASE,
)

# Safe template patterns
SAFE_TEMPLATE_EXEC_PATTERN = re.compile(
    r"{%\s*(?:exec|eval|import|from|__import__|compile)\s*%}", re.IGNORECASE
)

SAFE_TEMPLATE_PYTHON_PATTERN = re.compile(
    r"{{\s*(?:exec|eval|__import__|compile)\s*\(", re.IGNORECASE
)

SAFE_TEMPLATE_DANGEROUS_ATTRS_PATTERN = re.compile(
    r"{{\s*[^}]{1,100}\.__(?:class|bases|subclasses|mro)__", re.IGNORECASE
)

# Safe file system patterns
SAFE_BACKSLASH_PATTERN = re.compile(r"\\")
SAFE_MULTIPLE_SLASH_PATTERN = re.compile(r"/+")


def test_regex_safety(
    pattern: Pattern[str], test_input: str, timeout: float = 0.1
) -> bool:
    """Test if a regex pattern is safe against ReDoS attacks.

    Args:
        pattern: Compiled regex pattern to test
        test_input: Test input that might cause ReDoS
        timeout: Timeout in seconds for the test

    Returns:
        True if pattern is safe, False if it times out
    """
    try:
        safe_regex_search(pattern, test_input, timeout)
        return True
    except RegexTimeoutError:
        return False


def create_redos_test_string(base_char: str = "a", length: int = 10000) -> str:
    """Create a test string that can trigger ReDoS in vulnerable patterns.

    Args:
        base_char: Base character to repeat
        length: Length of the test string

    Returns:
        Test string that can trigger ReDoS
    """
    return base_char * length + "!"  # Pattern that fails to match at the end
