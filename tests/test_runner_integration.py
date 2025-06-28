"""Test runner integration with new attachment system."""

from ostruct.cli.runner import OstructRunner
from ostruct.cli.types import CLIParams


def test_runner_attachment_detection():
    """Test that OstructRunner detects new attachment syntax."""
    # Test with new attachment syntax
    new_args: CLIParams = {
        "attaches": [
            {
                "alias": "data",
                "path": "test.txt",
                "targets": ["prompt"],
                "recursive": False,
                "pattern": None,
            }
        ],
        "model": "gpt-4",
        "schema_file": "schema.json",
    }

    runner = OstructRunner(new_args)
    assert runner._has_new_attachment_syntax() is True

    # Test with legacy syntax (no new keys)
    legacy_args: CLIParams = {
        "model": "gpt-4",
        "schema_file": "schema.json",
        "files": [("data", "test.txt")],  # legacy format
    }

    runner = OstructRunner(legacy_args)
    assert runner._has_new_attachment_syntax() is False


def test_runner_attachment_summary():
    """Test attachment summary generation."""
    args: CLIParams = {
        "attaches": [
            {
                "alias": "data1",
                "path": "test1.txt",
                "targets": ["prompt"],
                "recursive": False,
                "pattern": None,
            }
        ],
        "dirs": [
            {
                "alias": "docs",
                "path": "documentation/",
                "targets": ["file-search", "code-interpreter"],
                "recursive": True,
                "pattern": "*.md",
            }
        ],
        "model": "gpt-4",
        "schema_file": "schema.json",
    }

    runner = OstructRunner(args)
    summary = runner._get_attachment_summary()

    assert summary["total_attachments"] == 2
    assert summary["attach_count"] == 1
    assert summary["dir_count"] == 1
    assert summary["collect_count"] == 0
    assert set(summary["targets_used"]) == {
        "prompt",
        "file-search",
        "code-interpreter",
    }


def test_runner_configuration_summary():
    """Test configuration summary with new attachments."""
    # Test with new attachments
    new_args: CLIParams = {
        "attaches": [
            {
                "alias": "data",
                "path": "test.txt",
                "targets": ["prompt"],
                "recursive": False,
                "pattern": None,
            }
        ],
        "model": "gpt-4",
        "schema_file": "schema.json",
        "dry_run": True,
        "verbose": False,
        "mcp_servers": ["server1", "server2"],
        "task": "Test task",
    }

    runner = OstructRunner(new_args)
    config = runner.get_configuration_summary()

    assert config["attachment_system"] == "new"
    assert config["attachments"]["total_attachments"] == 1
    assert config["model"] == "gpt-4"
    assert config["dry_run"] is True
    assert config["mcp_servers"] == 2  # This returns the count, not the list

    # Test with legacy format
    legacy_args: CLIParams = {
        "model": "gpt-4",
        "schema_file": "schema.json",
        "code_interpreter_files": [("data", "test.txt")],
        "dry_run": False,
        "verbose": True,
        "mcp_servers": [],
        "task": "Legacy task",
    }

    runner = OstructRunner(legacy_args)
    config = runner.get_configuration_summary()

    assert config["attachment_system"] == "legacy"
    assert config["code_interpreter_enabled"] is True
    assert config["file_search_enabled"] is False
    assert config["dry_run"] is False
    assert config["verbose"] is True
