"""Tests for OpenAI Responses API Code Interpreter annotation behavior.

This test suite verifies backend facts about how the Responses API handles
Code Interpreter file annotations. It documents current v0.8.3 behavior
without making any production code changes.
"""

import pytest
from openai import OpenAI

# shared inside each test file
MODELS = ["gpt-4o", "gpt-4.1"]


def _ci_call(prompt: str, model: str, client):
    """Make a Code Interpreter call via Responses API."""
    # ↘ REQUIRED container field for Code-Interpreter in Responses-API
    return client.responses.create(
        model=model,
        input=prompt,
        tools=[
            {
                "type": "code_interpreter",
                "container": {"type": "auto", "file_ids": []},
            }
        ],
        stream=False,
    )


def _annotations(resp):
    """Return all content-level annotations (any block, any index)."""
    ann: list = []
    for item in resp.output:  # list of tool call + message
        if getattr(item, "type", None) == "message":
            for blk in item.content or []:
                if hasattr(blk, "annotations"):
                    ann.extend(blk.annotations or [])
    return ann


# --- R-01  markdown-FREE => NO annotation ----------------------------
@pytest.mark.live
@pytest.mark.parametrize("model", MODELS)
def test_no_markdown_no_annotation(model, requires_openai):
    """Test that without markdown links, no annotations are created."""
    client = OpenAI()
    resp = _ci_call(
        "Write 'hi' to hello.txt via Python; do NOT mention file.",
        model,
        client,
    )
    assert not _annotations(resp)


# --- R-02  markdown link => annotation PRESENT -----------------------
@pytest.mark.live
@pytest.mark.parametrize("model", MODELS)
def test_markdown_triggers_annotation(model, requires_openai):
    """Test that markdown links trigger file citation annotations."""
    client = OpenAI()
    prompt = (
        "Write 'hi' to hello.txt and then output this exact markdown link: "
        "[Download hello.txt](sandbox:/mnt/data/hello.txt)"
    )
    resp = _ci_call(prompt, model, client)
    anns = [a for a in _annotations(resp) if "file_citation" in a.type]

    # Note: GPT-4.1 inconsistency is now covered by statistical compliance test

    assert anns, "Markdown link failed to create annotation"


# --- R-03  message.file_ids is empty (deprecated) --------------------
@pytest.mark.live
@pytest.mark.parametrize("model", MODELS)
def test_file_ids_deprecated(model, requires_openai):
    """Test that message.file_ids field is empty in Responses API."""
    client = OpenAI()
    resp = _ci_call("Make a linked hello.txt", model, client)
    assert not getattr(resp, "file_ids", []), ".file_ids unexpectedly set"
