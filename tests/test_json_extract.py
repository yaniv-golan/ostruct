import json

import pytest
from hypothesis import given, strategies as st
from ostruct.cli.json_extract import split_json_and_text


def test_basic_json_extraction():
    """Test basic JSON extraction from fenced blocks."""
    content = """```json
{"result": "success", "data": "test"}
```

Download file: [test.txt](sandbox:/mnt/data/test.txt)"""

    data, markdown_text = split_json_and_text(content)
    assert data == {"result": "success", "data": "test"}
    assert (
        markdown_text.strip()
        == "Download file: [test.txt](sandbox:/mnt/data/test.txt)"
    )


def test_multiple_fenced_blocks():
    """Test that first JSON block is returned."""
    content = """```json
{"first": "block"}
```

Some text

```json
{"second": "block"}
```"""

    data, markdown_text = split_json_and_text(content)
    assert data == {"first": "block"}
    assert "Some text" in markdown_text
    assert "```json" in markdown_text  # Second block should be in markdown


def test_no_json_block_error():
    """Test error when no JSON block found."""
    content = "No JSON here"
    with pytest.raises(ValueError, match="No.*json.*block found"):
        split_json_and_text(content)


def test_invalid_json_error():
    """Test error when JSON is malformed."""
    content = """```json
{"invalid": json}
```"""
    with pytest.raises(ValueError, match="Invalid JSON"):
        split_json_and_text(content)


def test_empty_json_block():
    """Test handling of empty JSON blocks."""
    content = """```json
```

Some markdown text"""

    with pytest.raises(ValueError, match="Invalid JSON"):
        split_json_and_text(content)


def test_whitespace_handling():
    """Test proper handling of whitespace around JSON."""
    content = """```json

  {"data": "value"}

```

  Markdown content with leading spaces"""

    data, markdown_text = split_json_and_text(content)
    assert data == {"data": "value"}
    assert markdown_text == "Markdown content with leading spaces"


def test_nested_backticks_in_json():
    """Test handling of backticks within JSON strings."""
    content = """```json
{"code": "```python\\nprint('hello')\\n```", "type": "code_block"}
```

Download link here"""

    data, markdown_text = split_json_and_text(content)
    assert data == {
        "code": "```python\nprint('hello')\n```",
        "type": "code_block",
    }
    assert markdown_text.strip() == "Download link here"


def test_complex_json_structure():
    """Test with complex nested JSON structure."""
    complex_json = {
        "converted_text": {
            "content_file": "extracted_full_text.txt",
            "metadata": {
                "source_file": "document.pdf",
                "conversion_method": "pymupdf_multicolumn",
                "page_count": 15,
                "content_length": 45000,
                "document_type": "academic",
                "extraction_quality": "complete",
            },
        }
    }

    content = f"""```json
{json.dumps(complex_json, indent=2)}
```

[Download extracted_full_text.txt](sandbox:/mnt/data/extracted_full_text.txt)"""

    data, markdown_text = split_json_and_text(content)
    assert data == complex_json
    assert "[Download extracted_full_text.txt]" in markdown_text


def test_unicode_content():
    """Test handling of Unicode content in JSON and markdown."""
    content = """```json
{"title": "Résumé", "content": "café", "emoji": "🚀"}
```

Télécharger: [fichier.txt](sandbox:/mnt/data/fichier.txt)"""

    data, markdown_text = split_json_and_text(content)
    assert data == {"title": "Résumé", "content": "café", "emoji": "🚀"}
    assert "Télécharger" in markdown_text


def test_indented_fenced_blocks():
    """Test handling of indented fenced blocks."""
    content = """    ```json
    {"indented": "json"}
    ```

    Indented markdown text"""

    data, markdown_text = split_json_and_text(content)
    assert data == {"indented": "json"}
    assert "Indented markdown text" in markdown_text


def test_no_markdown_after_json():
    """Test when there's no markdown content after JSON."""
    content = """```json
{"only": "json"}
```"""

    data, markdown_text = split_json_and_text(content)
    assert data == {"only": "json"}
    assert markdown_text == ""


def test_large_json_content():
    """Test with large JSON content."""
    large_data = {
        "items": [{"id": i, "value": f"item_{i}"} for i in range(1000)]
    }
    content = f"""```json
{json.dumps(large_data)}
```

Large data processed successfully"""

    data, markdown_text = split_json_and_text(content)
    assert data == large_data
    assert len(data["items"]) == 1000
    assert markdown_text.strip() == "Large data processed successfully"


@given(st.dictionaries(st.text(min_size=1), st.text(), min_size=1))
def test_json_roundtrip(json_dict):
    """Test JSON extraction with randomly generated data."""
    # Ensure ASCII encoding to avoid JSON serialization issues
    json_str = json.dumps(json_dict, ensure_ascii=True)
    content = f"```json\n{json_str}\n```\n\nMarkdown link here"

    data, markdown_text = split_json_and_text(content)
    assert data == json_dict
    assert markdown_text == "Markdown link here"


@pytest.mark.parametrize("root_path", ["C:\\tmp", "/tmp", "/Users/test"])
def test_windows_path_compatibility(root_path):
    """Test that path handling works across different OS path formats."""
    import os.path

    # Simulate download path construction (as would happen in download helper)
    filename = "test_file.txt"
    download_path = os.path.join(root_path, filename)

    # Verify os.path.join is used correctly for cross-platform compatibility
    if root_path.startswith("C:"):
        # Windows path
        assert "\\" in download_path or "/" in download_path
    else:
        # Unix-like path
        assert "/" in download_path

    # Verify filename is properly joined
    assert filename in download_path
    assert download_path.endswith(filename)


def test_multiple_newlines_in_json():
    """Test JSON with multiple newlines and formatting."""
    content = """```json
{
  "field1": "value1",

  "field2": {
    "nested": "value"
  },


  "field3": "value3"
}
```

Download link follows"""

    data, markdown_text = split_json_and_text(content)
    expected = {
        "field1": "value1",
        "field2": {"nested": "value"},
        "field3": "value3",
    }
    assert data == expected
    assert markdown_text.strip() == "Download link follows"


def test_json_with_arrays():
    """Test JSON containing arrays."""
    content = """```json
{
  "files": ["file1.txt", "file2.txt"],
  "metadata": {
    "count": 2,
    "types": ["text", "document"]
  }
}
```

Files processed: [Download archive.zip](sandbox:/mnt/data/archive.zip)"""

    data, markdown_text = split_json_and_text(content)
    assert data["files"] == ["file1.txt", "file2.txt"]
    assert data["metadata"]["count"] == 2
    assert "Download archive.zip" in markdown_text


def test_edge_case_json_only_whitespace():
    """Test JSON block with only whitespace."""
    content = """```json


```

Some content"""

    with pytest.raises(ValueError, match="Invalid JSON"):
        split_json_and_text(content)


def test_malformed_fenced_block():
    """Test malformed fenced block (missing closing)."""
    content = '''```json
{"incomplete": "block"'''

    with pytest.raises(ValueError, match="No.*json.*block found"):
        split_json_and_text(content)


def test_json_with_special_characters():
    """Test JSON with special characters and escape sequences."""
    content = """```json
{
  "path": "/mnt/data/file.txt",
  "escaped": "Line 1\\nLine 2\\tTabbed",
  "quotes": "He said \\"Hello\\"",
  "backslash": "C:\\\\Users\\\\file.txt"
}
```

Special characters handled correctly"""

    data, markdown_text = split_json_and_text(content)
    assert data["path"] == "/mnt/data/file.txt"
    assert data["escaped"] == "Line 1\nLine 2\tTabbed"
    assert data["quotes"] == 'He said "Hello"'
    assert data["backslash"] == "C:\\Users\\file.txt"
    assert "Special characters handled" in markdown_text
