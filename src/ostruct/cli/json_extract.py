import json
import re
from typing import Tuple

from .safe_regex import (
    SAFE_JSON_BLOCK_PATTERN,
    RegexTimeoutError,
    safe_regex_search,
)

# Regex to match JSON fenced blocks, handling newlines and indentation flexibly
# Uses ReDoS-safe pattern with limited nesting depth
JSON_RE = SAFE_JSON_BLOCK_PATTERN


def split_json_and_text(raw: str) -> Tuple[dict, str]:
    """
    Extract JSON from fenced code blocks and return markdown-only text.

    Args:
        raw: Raw response text containing fenced JSON and markdown

    Returns:
        Tuple of (parsed_json_dict, markdown_text_after_json)

    Raises:
        ValueError: If no JSON block found or JSON is invalid

    Note:
        Returns first JSON block if multiple exist. Markdown text is everything
        after the JSON block for downstream annotation processing.

    Example:
        >>> content = '''```json
        ... {"result": "success"}
        ... ```
        ...
        ... [Download file.txt](sandbox:/mnt/data/file.txt)'''
        >>> data, markdown = split_json_and_text(content)
        >>> data
        {'result': 'success'}
        >>> markdown.strip()
        '[Download file.txt](sandbox:/mnt/data/file.txt)'
    """
    # Try safe regex pattern first (ReDoS protection)
    try:
        match = safe_regex_search(JSON_RE, raw, timeout=2.0)
        if match:
            # Extract JSON content and parse with security limits
            from .json_limits import parse_json_secure

            potential_json = match.group(1).strip()
            data = parse_json_secure(potential_json)

            # Find markdown content after the JSON block
            json_end = match.end()
            markdown_text = raw[json_end:].lstrip()

            return data, markdown_text
    except RegexTimeoutError:
        # Potential ReDoS attack detected
        raise ValueError("JSON extraction timed out - potential ReDoS attack")
    except (json.JSONDecodeError, ValueError) as e:
        # JSON parsing failed or security limits exceeded
        if "JSON extraction timed out" in str(e):
            raise  # Re-raise timeout errors
        # Fall through to original logic for complex cases

    # Fallback to original iterative approach for complex cases
    # Find the start of the JSON block
    start_pattern = re.compile(r"```json\s*", re.MULTILINE)
    start_match = start_pattern.search(raw)
    if not start_match:
        raise ValueError("No ```json ... ``` block found")

    # Find the content after the opening ```json
    content_start = start_match.end()

    # Look for the closing ``` that's not inside a JSON string
    # We'll try multiple potential end positions and validate the JSON
    end_pattern = re.compile(r"```", re.MULTILINE)

    for end_match in end_pattern.finditer(raw, content_start):
        # Extract potential JSON content
        potential_json = raw[content_start : end_match.start()].strip()

        try:
            # Try to parse as JSON with security limits
            from .json_limits import parse_json_secure

            data = parse_json_secure(potential_json)
            # If successful, we found the right closing ```
            markdown_text = raw[end_match.end() :].lstrip()
            return data, markdown_text
        except (json.JSONDecodeError, ValueError):
            # This ``` might be inside a JSON string, continue looking
            # But if this is the only ``` we found, it's likely invalid JSON
            # ValueError includes JSONSizeError, JSONDepthError, JSONComplexityError
            continue

    # If we get here, check if we found any closing ``` at all
    if not list(end_pattern.finditer(raw, content_start)):
        # No closing ``` found
        raise ValueError("No ```json ... ``` block found")
    else:
        # Found closing ``` but JSON was invalid
        raise ValueError("Invalid JSON in fenced block")
