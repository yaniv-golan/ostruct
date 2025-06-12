"""Common utilities for the CLI package."""

from typing import Tuple

from .errors import VariableNameError, VariableValueError


def fix_surrogate_escapes(text: str) -> str:
    """Fix UTF-8 encoding issues caused by surrogate escapes.

    This function addresses the issue where Python's sys.argv contains
    surrogate characters (e.g., a backslash followed by 'udce2') when
    processing command line arguments with non-ASCII characters. This
    commonly happens with filenames containing characters like en dash (–)
    or other Unicode characters.

    Args:
        text: String that may contain surrogate escape characters

    Returns:
        String with surrogate escapes converted back to proper UTF-8
    """
    try:
        # Check if the text contains surrogate characters
        if any(0xDC00 <= ord(c) <= 0xDFFF for c in text):
            # Convert surrogate escapes back to bytes, then decode as UTF-8
            # This handles the case where Python used surrogateescape error handling
            byte_data = text.encode("utf-8", "surrogateescape")
            return byte_data.decode("utf-8")
        else:
            # No surrogate characters, return as-is
            return text
    except (UnicodeError, UnicodeDecodeError, UnicodeEncodeError):
        # If conversion fails, return the original text
        return text


def parse_mapping(mapping: str) -> Tuple[str, str]:
    """Parse a mapping string in the format 'name=value'.

    Args:
        mapping: Mapping string in format 'name=value'

    Returns:
        Tuple of (name, value) with whitespace stripped from both parts

    Raises:
        ValueError: If mapping format is invalid
        VariableNameError: If name part is empty
        VariableValueError: If value part is empty
    """
    if not mapping or "=" not in mapping:
        raise ValueError("Invalid mapping format")

    name, value = mapping.split("=", 1)
    name = name.strip()
    value = value.strip()
    if not name:
        raise VariableNameError("Empty name in mapping")
    if not value:
        raise VariableValueError("Empty value in mapping")

    return name, value
