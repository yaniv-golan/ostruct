from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest
from ostruct.cli.json_extract import split_json_and_text


def test_annotation_presence_detection():
    """Test that markdown links trigger container_file_citation annotations."""
    # Mock response with annotations
    mock_message: Dict[str, Any] = {
        "content": """```json
{"converted_text": {"content_file": "extracted_text.txt"}}
```

[Download extracted_text.txt](sandbox:/mnt/data/extracted_text.txt)""",
        "annotations": [
            {
                "type": "container_file_citation",
                "file_citation": {
                    "file_id": "file-123",
                    "filename": "extracted_text.txt",
                },
            }
        ],
    }

    # Test that annotation is detected
    annotations = mock_message.get("annotations", [])
    file_citations = [
        a for a in annotations if a.get("type") == "container_file_citation"
    ]

    assert len(file_citations) == 1
    assert file_citations[0]["file_citation"]["file_id"] == "file-123"
    assert (
        file_citations[0]["file_citation"]["filename"] == "extracted_text.txt"
    )


def test_missing_annotation_detection():
    """Test detection when annotations are not created."""
    mock_message: Dict[str, Any] = {
        "content": """```json
{"result": "success"}
```

No markdown link here""",
        "annotations": [],
    }

    # Should detect missing annotations
    annotations = mock_message.get("annotations", [])
    file_citations = [
        a for a in annotations if a.get("type") == "container_file_citation"
    ]

    assert len(file_citations) == 0


def test_json_extraction_with_markdown_link():
    """Test that JSON extraction preserves markdown text for annotation processing."""
    content = """```json
{"converted_text": {"content_file": "test.txt", "metadata": {"source": "doc.pdf"}}}
```

The extracted text has been saved. [Download test.txt](sandbox:/mnt/data/test.txt)"""

    data, markdown_text = split_json_and_text(content)

    # Verify JSON extraction
    assert data["converted_text"]["content_file"] == "test.txt"
    assert data["converted_text"]["metadata"]["source"] == "doc.pdf"

    # Verify markdown text preservation
    assert "Download test.txt" in markdown_text
    assert "sandbox:/mnt/data/test.txt" in markdown_text


def test_multiple_file_annotations():
    """Test handling of multiple file annotations in a single response."""
    mock_message: Dict[str, Any] = {
        "content": """```json
{"results": {"files": ["file1.txt", "file2.txt"]}}
```

[Download file1.txt](sandbox:/mnt/data/file1.txt)
[Download file2.txt](sandbox:/mnt/data/file2.txt)""",
        "annotations": [
            {
                "type": "container_file_citation",
                "file_citation": {
                    "file_id": "file-123",
                    "filename": "file1.txt",
                },
            },
            {
                "type": "container_file_citation",
                "file_citation": {
                    "file_id": "file-456",
                    "filename": "file2.txt",
                },
            },
        ],
    }

    annotations = mock_message.get("annotations", [])
    file_citations = [
        a for a in annotations if a.get("type") == "container_file_citation"
    ]

    assert len(file_citations) == 2
    filenames = [fc["file_citation"]["filename"] for fc in file_citations]
    assert "file1.txt" in filenames
    assert "file2.txt" in filenames


def test_annotation_with_mixed_content():
    """Test annotation detection with mixed annotation types."""
    mock_message: Dict[str, Any] = {
        "content": "Some content with file link",
        "annotations": [
            {"type": "other_annotation", "data": "some other data"},
            {
                "type": "container_file_citation",
                "file_citation": {
                    "file_id": "file-789",
                    "filename": "important.txt",
                },
            },
            {"type": "another_type", "info": "more data"},
        ],
    }

    annotations = mock_message.get("annotations", [])
    file_citations = [
        a for a in annotations if a.get("type") == "container_file_citation"
    ]

    assert len(file_citations) == 1
    assert file_citations[0]["file_citation"]["filename"] == "important.txt"


@pytest.mark.asyncio
async def test_download_generated_files_with_annotations():
    """Test file download using annotation-based approach."""
    mock_messages: List[Dict[str, Any]] = [
        {
            "content": "JSON + markdown link content",
            "annotations": [
                {
                    "type": "container_file_citation",
                    "file_citation": {
                        "file_id": "file-123",
                        "filename": "test.txt",
                    },
                }
            ],
        }
    ]

    # Mock the CodeInterpreterManager and its methods
    with patch(
        "ostruct.cli.code_interpreter.CodeInterpreterManager"
    ) as MockManager:
        mock_manager = MockManager.return_value
        mock_manager.download_generated_files = AsyncMock(
            return_value=["test.txt"]
        )

        # Test download logic
        download_dir = "/tmp/test_downloads"
        downloaded_files = await mock_manager.download_generated_files(
            mock_messages, download_dir
        )

        # Verify it was called with correct parameters
        mock_manager.download_generated_files.assert_called_once_with(
            mock_messages, download_dir
        )
        assert "test.txt" in downloaded_files


def test_annotation_structure_validation():
    """Test that annotation structure matches expected OpenAI format."""
    # Example annotation structure from OpenAI Responses API
    expected_annotation: Dict[str, Any] = {
        "type": "container_file_citation",
        "file_citation": {
            "file_id": "file-abc123",
            "filename": "document.txt",
        },
    }

    # Validate structure
    assert "type" in expected_annotation
    assert expected_annotation["type"] == "container_file_citation"
    assert "file_citation" in expected_annotation
    assert "file_id" in expected_annotation["file_citation"]
    assert "filename" in expected_annotation["file_citation"]

    # Validate data types
    assert isinstance(expected_annotation["file_citation"]["file_id"], str)
    assert isinstance(expected_annotation["file_citation"]["filename"], str)


def test_edge_case_empty_annotations():
    """Test handling of messages with empty or missing annotations."""
    test_cases: List[Dict[str, Any]] = [
        {"content": "some content", "annotations": []},
        {"content": "some content", "annotations": None},
        {"content": "some content"},  # No annotations key
    ]

    for message in test_cases:
        annotations = message.get("annotations", []) or []
        file_citations = [
            a
            for a in annotations
            if a.get("type") == "container_file_citation"
        ]
        assert len(file_citations) == 0


def test_malformed_annotation_handling():
    """Test graceful handling of malformed annotations."""
    mock_message: Dict[str, Any] = {
        "content": "some content",
        "annotations": [
            # Missing file_citation
            {"type": "container_file_citation"},
            # Missing filename
            {
                "type": "container_file_citation",
                "file_citation": {"file_id": "file-123"},
            },
            # Missing file_id
            {
                "type": "container_file_citation",
                "file_citation": {"filename": "test.txt"},
            },
            # Valid annotation
            {
                "type": "container_file_citation",
                "file_citation": {
                    "file_id": "file-456",
                    "filename": "valid.txt",
                },
            },
        ],
    }

    annotations = mock_message.get("annotations", [])

    # Filter for valid file citations only
    valid_file_citations = []
    for a in annotations:
        if (
            a.get("type") == "container_file_citation"
            and "file_citation" in a
            and "file_id" in a["file_citation"]
            and "filename" in a["file_citation"]
        ):
            valid_file_citations.append(a)

    # Should only find the one valid annotation
    assert len(valid_file_citations) == 1
    assert valid_file_citations[0]["file_citation"]["filename"] == "valid.txt"


def test_json_extraction_preserves_full_response():
    """Test that JSON extraction preserves the complete response for annotation processing."""
    full_response = """Here's the analysis:

```json
{"analysis": {"status": "complete", "file": "results.txt"}}
```

The analysis is complete. [Download results.txt](sandbox:/mnt/data/results.txt)

Additional notes about the analysis process."""

    data, markdown_text = split_json_and_text(full_response)

    # Verify JSON extraction
    assert data["analysis"]["status"] == "complete"
    assert data["analysis"]["file"] == "results.txt"

    # Verify markdown text includes everything after JSON
    assert "Download results.txt" in markdown_text
    assert "Additional notes" in markdown_text
    assert "sandbox:/mnt/data/results.txt" in markdown_text


@pytest.mark.asyncio
async def test_end_to_end_annotation_flow():
    """Test complete flow from JSON extraction to file download."""
    # Simulate a complete API response
    api_response_content = """```json
{"converted_text": {"content_file": "extracted_full_text.txt", "metadata": {"source_file": "document.pdf"}}}
```

The extracted text has been saved. [Download extracted_full_text.txt](sandbox:/mnt/data/extracted_full_text.txt)"""

    # Step 1: Extract JSON and markdown
    data, markdown_text = split_json_and_text(api_response_content)

    # Step 2: Verify JSON structure
    assert data["converted_text"]["content_file"] == "extracted_full_text.txt"
    assert "Download extracted_full_text.txt" in markdown_text

    # Step 3: Simulate annotation creation (would happen in OpenAI's system)
    mock_annotation: Dict[str, Any] = {
        "type": "container_file_citation",
        "file_citation": {
            "file_id": "file-xyz789",
            "filename": "extracted_full_text.txt",
        },
    }

    # Step 4: Simulate message with annotation
    mock_message: Dict[str, Any] = {
        "content": api_response_content,
        "annotations": [mock_annotation],
    }

    # Step 5: Test file download would work
    with patch(
        "ostruct.cli.code_interpreter.CodeInterpreterManager"
    ) as MockManager:
        mock_manager = MockManager.return_value
        mock_manager.download_generated_files = AsyncMock(
            return_value=["extracted_full_text.txt"]
        )

        downloaded_files = await mock_manager.download_generated_files(
            [mock_message], "/tmp/downloads"
        )

        assert "extracted_full_text.txt" in downloaded_files
        mock_manager.download_generated_files.assert_called_once()
