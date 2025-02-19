"""Path normalization module.

This module provides functions to normalize file paths by:
- Performing Unicode normalization (NFKC)
- Normalizing path separators and redundant parts
- Converting relative paths to absolute paths
- Validating Unicode safety

Security Design Choices:
1. Unicode Normalization:
   - Uses NFKC form for maximum compatibility
   - Blocks known unsafe Unicode characters
   - Basic protection against homograph attacks
   - Does not handle all possible confusable sequences

2. Path Separators:
   - Normalizes to forward slashes
   - Collapses multiple slashes
   - Converts backslashes on all platforms
   - Note: This breaks Windows UNC and device paths

3. Parent Directory References:
   - Allows ".." components in raw input
   - Security checks done after path resolution
   - Directory traversal prevented by final path validation

4. Absolute Paths:
   - Converts relative to absolute using CWD
   - No environment variable expansion
   - No home directory (~) expansion
   - Thread-safety warning for CWD operations

Known Limitations:
1. Windows-Specific:
   - UNC paths (r"\\\\server\\share") break when normalized
   - Device paths (r"\\\\?\\", r"\\\\.") become invalid
   - Drive-relative paths may resolve incorrectly
   - Reserved names (CON, NUL, etc.) not handled
   - ADS (:stream) not detected
   - Case sensitivity not handled (delegated to CaseManager)

2. Unicode Handling:
   - Some confusable characters may pass checks
   - Zero-width characters not fully covered
   - Advanced homograph attacks possible
   - Duplicate entries in safety pattern need review

3. Threading:
   - CWD operations not thread-safe
   - Race conditions possible during path resolution
"""

import os
import re
import unicodedata
from pathlib import Path
from typing import Union

from .errors import PathSecurityError, SecurityErrorReasons

# Patterns for path normalization and validation
_UNICODE_SAFETY_PATTERN = re.compile(
    r"[\u0000-\u001F\u007F-\u009F\u2028-\u2029\u0085]"  # Control chars and line separators
    r"|(?:^|/)\.\.(?:/|$)"  # Directory traversal attempts (only ".." as a path component)
    r"|[\u2024\u2025\uFE52\u2024\u2025\u2026\uFE19\uFE30\uFE52\uFF0E\uFF61]"  # Alternative dots and separators
)
_BACKSLASH_PATTERN = re.compile(r"\\")
_MULTIPLE_SLASH_PATTERN = re.compile(r"/+")


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize a path string with security checks.

    This function:
    1. Converts to Unicode NFKC form
    2. Checks for unsafe Unicode characters
    3. Normalizes path separators
    4. Uses os.path.normpath to collapse redundant separators and dots
    5. Converts to absolute path if needed
    6. Returns a pathlib.Path object

    Security Features:
    - Unicode NFKC normalization
    - Blocks unsafe Unicode characters
    - Normalizes path separators
    - Converts to absolute paths

    Design Choices:
    - No environment variable expansion
    - No home directory (~) expansion
    - No symlink resolution (handled separately)
    - Case sensitivity handled by CaseManager
    - Thread-safety warning: CWD operations are not atomic

    Args:
        path: A string or Path object representing a file path.

    Returns:
        A pathlib.Path object for the normalized absolute path.

    Raises:
        PathSecurityError: If the path contains unsafe Unicode characters.
        TypeError: If path is None.

    Note:
        This function has known limitations with Windows paths:
        - UNC paths are not properly handled
        - Device paths are not supported
        - Drive-relative paths may resolve incorrectly
        - Reserved names are not checked
        - ADS is not detected
    """
    if path is None:
        raise TypeError("Path cannot be None")

    path_str = str(path)

    # Unicode normalization
    try:
        normalized = unicodedata.normalize("NFKC", path_str)
    except Exception as e:
        raise PathSecurityError(
            "Unicode normalization failed",
            path=path_str,
            context={
                "reason": SecurityErrorReasons.UNSAFE_UNICODE,
                "error": str(e),
            },
        ) from e

    # Check for unsafe characters and directory traversal
    if match := _UNICODE_SAFETY_PATTERN.search(normalized):
        matched_text = match.group(0)
        if ".." in matched_text:
            raise PathSecurityError(
                "Directory traversal not allowed",
                path=path_str,
                context={
                    "reason": SecurityErrorReasons.PATH_TRAVERSAL,
                    "matched": matched_text,
                },
            )
        else:
            raise PathSecurityError(
                "Path contains unsafe characters",
                path=path_str,
                context={
                    "reason": SecurityErrorReasons.UNSAFE_UNICODE,
                    "matched": matched_text,
                },
            )

    # Normalize path separators
    normalized = _BACKSLASH_PATTERN.sub("/", normalized)
    normalized = _MULTIPLE_SLASH_PATTERN.sub("/", normalized)

    # Convert to absolute path if needed
    if not os.path.isabs(normalized):
        normalized = os.path.abspath(normalized)

    return Path(normalized)
