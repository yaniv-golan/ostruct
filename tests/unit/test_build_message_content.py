from typing import Any, Dict, List

from ostruct.cli.runner import _build_message_content


class _FakeUploadManagerDict:  # noqa: D101 naming
    """Fake upload manager returning legacy dict mapping."""

    def __init__(self, mapping: Dict[str, str]):
        self._mapping = mapping

    def get_files_for_tool(self, tool: str) -> Dict[str, str]:  # noqa: D401
        assert tool == "user-data"
        return self._mapping


class _FakeUploadManagerList:  # noqa: D101 naming
    """Fake upload manager returning new list of IDs or url-prefixed strings."""

    def __init__(self, uploads: List[str]):
        self._uploads = uploads

    def get_files_for_tool(self, tool: str) -> List[str]:  # noqa: D401
        assert tool == "user-data"
        return self._uploads


def _assert_structured_response(msg: Any, expected_file_count: int) -> None:
    """Ensure returned message has expected Responses API structure."""
    assert isinstance(
        msg, list
    ), "Message should be a list with a single entry"
    assert msg and msg[0]["role"] == "user"
    content = msg[0]["content"]
    # There should be one input_text plus N input_file elements
    assert len(content) == 1 + expected_file_count
    assert content[0]["type"] == "input_text"
    file_elems = content[1:]
    for elem in file_elems:
        assert elem["type"] == "input_file"
        # Either file_id or file_url must exist (exclusive)
        has_id = "file_id" in elem
        has_url = "file_url" in elem
        assert has_id ^ has_url, "Exactly one of file_id or file_url expected"


def test_build_message_content_with_dict() -> None:
    """Legacy dict mapping should be handled correctly without errors."""
    manager = _FakeUploadManagerDict(
        {"foo.txt": "file-123", "bar.txt": "file-456"}
    )
    msg = _build_message_content("SYS", "USER", shared_upload_manager=manager)
    _assert_structured_response(msg, expected_file_count=2)


def test_build_message_content_with_list_ids() -> None:
    """New list of file IDs should be handled correctly."""
    manager = _FakeUploadManagerList(["file-abc", "file-def"])
    msg = _build_message_content("SYS", "USER", shared_upload_manager=manager)
    _assert_structured_response(msg, expected_file_count=2)


def test_build_message_content_with_list_urls() -> None:
    """List containing url-prefixed entries should produce file_url elements."""
    manager = _FakeUploadManagerList(["url:https://example.com/foo.pdf"])
    msg = _build_message_content("SYS", "USER", shared_upload_manager=manager)
    _assert_structured_response(msg, expected_file_count=1)
