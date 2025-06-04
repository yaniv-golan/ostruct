"""Tests for universal tool toggle functionality."""

import json
import os
import pytest
from click.testing import CliRunner
from ostruct.cli.cli import create_cli

TEST_BASE_DIR = "/tmp/test_tool_toggles"


def setup_module():
    """Set up test files for all tests."""
    import shutil

    # Clean up any existing test directory
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)

    # Create test directory and files
    os.makedirs(TEST_BASE_DIR, exist_ok=True)

    with open(f"{TEST_BASE_DIR}/template.j2", "w") as f:
        f.write("Test template")

    schema_content = {
        "schema": {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
            "additionalProperties": False,
        }
    }
    with open(f"{TEST_BASE_DIR}/schema.json", "w") as f:
        json.dump(schema_content, f)


class TestToolToggleConflicts:
    """Test conflict detection for tool toggles."""

    @pytest.mark.no_fs
    def test_tool_toggle_conflict_detection(self):
        """Test that conflicts between enable and disable are detected."""
        runner = CliRunner()

        result = runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--enable-tool",
                "web-search",
                "--disable-tool",
                "web-search",
                "--dry-run",
            ],
        )

        assert result.exit_code == 2
        assert (
            "--enable-tool and --disable-tool both specified for"
            in result.output
        )
        assert "web-search" in result.output

    @pytest.mark.no_fs
    def test_no_conflicts_with_different_tools(self):
        """Test that different tools don't cause conflicts."""
        runner = CliRunner()

        result = runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--enable-tool",
                "web-search",
                "--disable-tool",
                "file-search",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert (
            "--enable-tool and --disable-tool both specified for"
            not in result.output
        )


class TestWebSearchToggle:
    """Test web search tool toggle functionality."""

    @pytest.mark.no_fs
    def test_enable_web_search_via_toggle(self):
        """Test enabling web search via --enable-tool."""
        runner = CliRunner()

        result = runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--enable-tool",
                "web-search",
                "--debug",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "web_search_enabled: bool (True)" in result.output

    @pytest.mark.no_fs
    def test_disable_web_search_via_toggle(self):
        """Test disabling web search via --disable-tool."""
        runner = CliRunner()

        result = runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--disable-tool",
                "web-search",
                "--debug",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "web_search_enabled: bool (False)" in result.output

    @pytest.mark.no_fs
    def test_enable_tool_overrides_no_web_search(self):
        """Test that --enable-tool overrides --no-web-search."""
        runner = CliRunner()

        result = runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--enable-tool",
                "web-search",
                "--no-web-search",
                "--debug",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "web_search_enabled: bool (True)" in result.output


class TestCodeInterpreterToggle:
    """Test code interpreter tool toggle functionality."""

    @pytest.mark.no_fs
    def test_enable_code_interpreter_via_toggle(self):
        """Test enabling code interpreter via --enable-tool."""
        runner = CliRunner()

        result = runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--enable-tool",
                "code-interpreter",
                "--debug",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "code_interpreter_enabled: bool (True)" in result.output

    @pytest.mark.no_fs
    def test_disable_code_interpreter_via_toggle(self):
        """Test disabling code interpreter via --disable-tool."""
        runner = CliRunner()

        result = runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--disable-tool",
                "code-interpreter",
                "--debug",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "code_interpreter_enabled: bool (False)" in result.output


class TestMultipleToolToggles:
    """Test multiple tool toggles working together."""

    @pytest.mark.no_fs
    def test_multiple_enables(self):
        """Test enabling multiple tools at once."""
        runner = CliRunner()

        result = runner.invoke(
            create_cli(),
            [
                "run",
                f"{TEST_BASE_DIR}/template.j2",
                f"{TEST_BASE_DIR}/schema.json",
                "--enable-tool",
                "web-search",
                "--enable-tool",
                "code-interpreter",
                "--debug",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "web_search_enabled: bool (True)" in result.output
        assert "code_interpreter_enabled: bool (True)" in result.output


def teardown_module():
    """Clean up test files after all tests."""
    import shutil

    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
