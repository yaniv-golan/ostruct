"""Windows Unicode compatibility utilities.

This module provides smart emoji handling for Windows terminals:
- Modern terminals (Windows Terminal, PowerShell, Win11 Console) get full emoji
- Legacy terminals (cmd.exe with cp1252) get clean text without emoji
- Detection is automatic and graceful with user overrides available

Environment Variables:
- OSTRUCT_UNICODE=auto: Auto-detect terminal capabilities (default)
- OSTRUCT_UNICODE=1/true/yes: Force emoji display regardless of detection
- OSTRUCT_UNICODE=0/false/no: Force plain text regardless of detection
- OSTRUCT_UNICODE=debug: Show detection details and use auto-detection
"""

import os
import sys
from typing import Any, Optional


def _get_unicode_setting() -> str:
    """Get the Unicode setting from environment variable."""
    return os.environ.get("OSTRUCT_UNICODE", "auto").lower()


def _is_debug_mode() -> bool:
    """Check if Unicode debugging is enabled."""
    return _get_unicode_setting() == "debug"


def _debug_log(message: str) -> None:
    """Log debug message if unicode debugging is enabled."""
    if _is_debug_mode():
        print(f"[UNICODE DEBUG] {message}", file=sys.stderr)


def _detect_modern_windows_terminal() -> bool:
    """Detect if we're running in a modern Windows terminal that supports Unicode.

    Returns:
        True if running in Windows Terminal, PowerShell, or Win11 Console Host
        False if running in legacy cmd.exe or other limited terminals
    """
    # Check for explicit user overrides first
    unicode_setting = _get_unicode_setting()

    if unicode_setting in ("1", "true", "yes", "on"):
        _debug_log("Unicode forced ON via OSTRUCT_UNICODE")
        return True

    if unicode_setting in ("0", "false", "no", "off"):
        _debug_log("Unicode forced OFF via OSTRUCT_UNICODE")
        return False

    # For "auto" and "debug", proceed with detection

    if not sys.platform.startswith("win"):
        # Non-Windows systems generally support Unicode well
        _debug_log(f"Non-Windows platform ({sys.platform}): Unicode enabled")
        return True

    _debug_log("Windows platform detected, checking terminal capabilities...")

    # Check for Windows Terminal
    if os.environ.get("WT_SESSION"):
        _debug_log("Windows Terminal detected via WT_SESSION")
        return True

    # Check for PowerShell (both Windows PowerShell and PowerShell Core)
    if os.environ.get("PSModulePath"):
        _debug_log("PowerShell detected via PSModulePath")
        return True

    # Check for modern console host (Windows 11+)
    # The TERMINAL_EMULATOR environment variable is set by modern terminals
    if os.environ.get("TERMINAL_EMULATOR"):
        _debug_log(
            f"Modern terminal detected via TERMINAL_EMULATOR: {os.environ.get('TERMINAL_EMULATOR')}"
        )
        return True

    # Check for VS Code integrated terminal
    if os.environ.get("VSCODE_INJECTION"):
        _debug_log("VS Code integrated terminal detected")
        return True

    # Check for GitHub Codespaces
    if os.environ.get("CODESPACES"):
        _debug_log("GitHub Codespaces detected")
        return True

    # Check console code page - UTF-8 indicates modern setup
    try:
        import locale

        encoding = locale.getpreferredencoding()
        if encoding.lower() in ("utf-8", "utf8"):
            _debug_log(f"UTF-8 locale detected: {encoding}")
            return True
        else:
            _debug_log(f"Non-UTF-8 locale: {encoding}")
    except Exception as e:
        _debug_log(f"Locale detection failed: {e}")

    # Check if stdout encoding supports Unicode
    try:
        stdout_encoding = getattr(sys.stdout, "encoding", None)
        if stdout_encoding and stdout_encoding.lower() in ("utf-8", "utf8"):
            _debug_log(f"UTF-8 stdout encoding: {stdout_encoding}")
            return True
        else:
            _debug_log(f"Non-UTF-8 stdout encoding: {stdout_encoding}")
    except Exception as e:
        _debug_log(f"Stdout encoding detection failed: {e}")

    # Check Windows version (Windows 10 1903+ has better Unicode support)
    try:
        import platform

        version = platform.version()
        # Windows 10 build 18362 (1903) and later have better Unicode support
        if version and "10.0." in version:
            build = version.split(".")[-1]
            if build.isdigit() and int(build) >= 18362:
                _debug_log(f"Modern Windows version detected: {version}")
                return True
        _debug_log(f"Windows version: {version}")
    except Exception as e:
        _debug_log(f"Windows version detection failed: {e}")

    # Default to False for safety on Windows
    _debug_log(
        "No modern terminal indicators found, defaulting to legacy mode"
    )
    return False


def safe_emoji(emoji: str, text_without_emoji: Optional[str] = None) -> str:
    """Return emoji on Unicode-capable terminals, clean text on legacy terminals.

    Args:
        emoji: The emoji character to display
        text_without_emoji: Optional clean text version. If None, emoji is simply omitted.

    Returns:
        Emoji on modern terminals, clean text on legacy terminals

    Examples:
        safe_emoji("🚀", "START") -> "🚀" or "START"
        safe_emoji("🔍") -> "🔍" or ""
    """
    if _detect_modern_windows_terminal():
        # Modern terminal - try to use emoji
        try:
            # Test if we can encode the emoji
            emoji.encode(sys.stdout.encoding or "utf-8")
            return emoji
        except (UnicodeEncodeError, LookupError, AttributeError):
            # Fallback even on modern terminals if encoding fails
            return text_without_emoji or ""
    else:
        # Legacy terminal - use clean text
        return text_without_emoji or ""


def safe_format(format_string: str, *args: Any, **kwargs: Any) -> str:
    """Format string with emoji safety.

    Processes format strings containing emoji through safe_emoji() automatically.
    Optimized to skip processing when no emoji are present.

    Args:
        format_string: Format string that may contain emoji
        *args, **kwargs: Format arguments

    Returns:
        Formatted string with emoji handled appropriately for the terminal
    """
    # Quick check: if no emoji characters are present, skip processing entirely
    # This optimizes the common case of plain text messages
    # Check for the specific emoji we handle rather than broad Unicode ranges
    emoji_chars = {
        "🚀",
        "🔍",
        "⚙️",
        "ℹ️",
        "📖",
        "💻",
        "📄",
        "🌐",
        "🕐",
        "📋",
        "🤖",
        "🔒",
        "🛠️",
        "📎",
        "📥",
        "📊",
        "💰",
        "✅",
        "❌",
        "⚠️",
        "⏱️",
    }
    if not any(emoji in format_string for emoji in emoji_chars):
        return format_string.format(*args, **kwargs)

    # Common emoji replacements for CLI output
    emoji_map = {
        "🚀": "",  # Just omit, the text context is clear
        "🔍": "",  # Just omit, "Plan" or "Execution Plan" is clear
        "⚙️": "",  # Just omit for progress reporting
        "ℹ️": "",  # Just omit for info messages
        "📖": "",  # Just omit for help references
        "💻": "",  # Just omit for Code Interpreter
        "📄": "",  # Just omit for file references
        "🌐": "",  # Just omit for web search
        "🕐": "",  # Just omit for timestamp
        "📋": "",  # Just omit for schema
        "🤖": "",  # Just omit for model
        "🔒": "",  # Just omit for security
        "🛠️": "",  # Just omit for tools
        "📎": "",  # Just omit for attachments
        "📥": "",  # Just omit for downloads
        "📊": "",  # Just omit for variables
        "💰": "",  # Just omit for cost
        "✅": "[OK]",  # Show status indicator
        "❌": "[ERROR]",  # Show status indicator
        "⚠️": "[WARNING]",  # Show status indicator
        "⏱️": "",  # Just omit for timing
    }

    # Apply emoji safety to the format string
    safe_format_string = format_string
    for emoji, fallback in emoji_map.items():
        if emoji in format_string:  # Only process if emoji is actually present
            safe_format_string = safe_format_string.replace(
                emoji, safe_emoji(emoji, fallback)
            )

    # Format with the processed string
    return safe_format_string.format(*args, **kwargs)


def safe_print(message: str, **print_kwargs: Any) -> None:
    """Print message with emoji safety.

    Convenience function for safe printing with automatic emoji handling.

    Args:
        message: Message to print (may contain emoji)
        **print_kwargs: Additional arguments passed to print()
    """
    # Fast path for messages without emoji
    emoji_chars = {
        "🚀",
        "🔍",
        "⚙️",
        "ℹ️",
        "📖",
        "💻",
        "📄",
        "🌐",
        "🕐",
        "📋",
        "🤖",
        "🔒",
        "🛠️",
        "📎",
        "📥",
        "📊",
        "💰",
        "✅",
        "❌",
        "⚠️",
        "⏱️",
    }
    if not any(emoji in message for emoji in emoji_chars):
        print(message, **print_kwargs)
        return

    # Process emoji for compatibility
    safe_message = safe_format(message)
    print(safe_message, **print_kwargs)
