import json
from pathlib import Path

from click.testing import CliRunner
from ostruct.cli.cli import create_cli


def _create_files(fs, base_dir: str):
    """Helper to create minimal template and schema files."""
    fs.create_dir(base_dir)
    template_path = Path(base_dir) / "template.j2"
    schema_path = Path(base_dir) / "schema.json"

    fs.create_file(
        str(template_path),
        contents="{}",  # Minimal content, no variables
    )

    fs.create_file(
        str(schema_path),
        contents=json.dumps(
            {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"dummy": {"type": "string"}},
                "required": ["dummy"],
            }
        ),
    )
    return str(template_path), str(schema_path)


class TestToolChoiceCLI:
    """Basic tests for the --tool-choice flag."""

    def test_tool_choice_valid(self, fs):
        base_dir = "/test_workspace/base/tool_choice_valid"
        template_file, schema_file = _create_files(fs, base_dir)

        cli = create_cli()
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run",
                template_file,
                schema_file,
                "--dry-run",
                "--tool-choice",
                "file-search",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_tool_choice_invalid_value(self, fs):
        base_dir = "/test_workspace/base/tool_choice_invalid"
        template_file, schema_file = _create_files(fs, base_dir)

        cli = create_cli()
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run",
                template_file,
                schema_file,
                "--dry-run",
                "--tool-choice",
                "nonexistent",
            ],
        )
        # Click should raise BadParameter and exit code 2
        assert result.exit_code != 0
        assert "Invalid value for '--tool-choice'" in result.output
