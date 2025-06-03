import json
import re
from typing import Tuple

# Regex to match JSON fenced blocks, handling newlines and indentation flexibly
# Uses non-greedy matching but ensures we get the complete JSON block
JSON_RE = re.compile(
    r"```json\s*\n?([\s\S]*?)\n?\s*```", re.DOTALL | re.MULTILINE
)


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
            # Try to parse as JSON
            data = json.loads(potential_json)
            # If successful, we found the right closing ```
            markdown_text = raw[end_match.end() :].lstrip()
            return data, markdown_text
        except json.JSONDecodeError:
            # This ``` might be inside a JSON string, continue looking
            # But if this is the only ``` we found, it's likely invalid JSON
            continue

    # If we get here, check if we found any closing ``` at all
    if not list(end_pattern.finditer(raw, content_start)):
        # No closing ``` found
        raise ValueError("No ```json ... ``` block found")
    else:
        # Found closing ``` but JSON was invalid
        raise ValueError("Invalid JSON in fenced block")
