"""Tests for sentinel JSON extraction utility."""

from ostruct.cli.sentinel import extract_json_block


def test_extract_json_block():
    """Test basic JSON block extraction."""
    # Basic extraction
    result = extract_json_block('x===BEGIN_JSON===\n{"a":1}\n===END_JSON===')
    assert result == {"a": 1}


def test_extract_json_block_no_markers():
    """Test extraction when no markers are present."""
    result = extract_json_block("just text")
    assert result is None


def test_extract_json_block_invalid_json():
    """Test extraction with invalid JSON."""
    result = extract_json_block("===BEGIN_JSON==={invalid}===END_JSON===")
    assert result is None


def test_extract_json_block_multiline():
    """Test extraction with multiline JSON."""
    text = """Some text
===BEGIN_JSON===
{
  "key": "value",
  "number": 42
}
===END_JSON===
More text"""
    result = extract_json_block(text)
    assert result == {"key": "value", "number": 42}


def test_extract_json_block_whitespace():
    """Test extraction with extra whitespace."""
    result = extract_json_block(
        '===BEGIN_JSON===   {"test": true}   ===END_JSON==='
    )
    assert result == {"test": True}


def test_extract_json_block_non_dict():
    """Test extraction when JSON is not a dict."""
    result = extract_json_block("===BEGIN_JSON===[1, 2, 3]===END_JSON===")
    assert result is None
