"""Tests for binary file lazy loading behavior."""

import json
import os

from click.testing import CliRunner
from ostruct.cli.cli import create_cli
from pyfakefs.fake_filesystem import FakeFilesystem


class TestBinaryLazyLoading:
    """Test binary file handling with lazy loading."""

    def test_binary_metadata_access_dry_run(self, fs: FakeFilesystem) -> None:
        """Binary file metadata access should work in dry run without content loading."""
        # Create binary test file
        binary_content = b"\x00\x01\x02\x03\xff\xfe\xfd"
        fs.create_file("/tmp/test.bin", contents=binary_content)

        # Create minimal schema
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file("/tmp/schema.json", contents=json.dumps(schema_content))

        # Create template that only accesses metadata (not content)
        # Note: --file ci:test_bin test.bin creates variable "test_bin" as LazyFileContent
        # For single files, we can access .name directly
        template_content = "Binary file: {{ test_bin.name }}"
        fs.create_file("/tmp/template.j2", contents=template_content)

        # Change to temp directory
        os.chdir("/tmp")

        runner = CliRunner()
        result = runner.invoke(
            create_cli(),
            [
                "run",
                "template.j2",
                "schema.json",
                "--file",
                "ci:test_bin",
                "test.bin",
                "--dry-run",
            ],
        )

        # Should succeed
        assert (
            result.exit_code == 0
        ), f"Expected success but got: {result.output}"
        # In dry run mode, template doesn't render output, just validates
        assert "Dry run completed successfully" in result.output

    def test_binary_content_access_fails_gracefully(
        self, fs: FakeFilesystem
    ) -> None:
        """Binary file content access should fail gracefully with clear error."""
        # Create binary test file
        binary_content = b"\x00\x01\x02\x03\xff\xfe\xfd"
        fs.create_file("/tmp/test.bin", contents=binary_content)

        # Create minimal schema
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file("/tmp/schema.json", contents=json.dumps(schema_content))

        # Create template that tries to access content
        template_content = "Binary content: {{ test_bin.content }}"
        fs.create_file("/tmp/template.j2", contents=template_content)

        # Change to temp directory
        os.chdir("/tmp")

        runner = CliRunner()
        result = runner.invoke(
            create_cli(),
            [
                "run",
                "template.j2",
                "schema.json",
                "--file",
                "ci:test_bin",
                "test.bin",
                "--dry-run",
            ],
        )

        # Should fail with appropriate error
        assert result.exit_code != 0
        # Check for FileReadError or UnicodeDecodeError in output
        error_output = result.output.lower()
        assert any(
            error_type in error_output
            for error_type in [
                "fileread",
                "unicode",
                "decode",
                "binary",
                "failed to load content",
            ]
        ), f"Expected file read error but got: {result.output}"

    def test_text_file_still_works(self, fs: FakeFilesystem) -> None:
        """Text files should continue to work normally."""
        # Create text file
        fs.create_file("/tmp/test.txt", contents="Hello, world!")

        # Create minimal schema
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file("/tmp/schema.json", contents=json.dumps(schema_content))

        # Create template that accesses content
        # Note: test.txt becomes test_txt variable as LazyFileContent
        template_content = "Text content: {{ test_txt.content }}"
        fs.create_file("/tmp/template.j2", contents=template_content)

        # Change to temp directory
        os.chdir("/tmp")

        runner = CliRunner()
        result = runner.invoke(
            create_cli(),
            [
                "run",
                "template.j2",
                "schema.json",
                "--file",
                "ci:test_txt",
                "test.txt",
                "--dry-run",
            ],
        )

        # Should succeed
        assert (
            result.exit_code == 0
        ), f"Expected success but got: {result.output}"
        # In dry run mode, template doesn't render output, just validates
        assert "Dry run completed successfully" in result.output

    def test_mixed_file_types(self, fs: FakeFilesystem) -> None:
        """Mixed binary and text files should work when only metadata accessed."""
        # Create files
        fs.create_file("/tmp/binary.bin", contents=b"\x00\x01\x02\x03")
        fs.create_file("/tmp/text.txt", contents="Hello!")

        # Create minimal schema
        schema_content = {
            "schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
                "additionalProperties": False,
            }
        }
        fs.create_file("/tmp/schema.json", contents=json.dumps(schema_content))

        # Create template that only accesses metadata
        # Note: binary.bin becomes binary_bin, text.txt becomes text_txt as LazyFileContent
        template_content = "Files: {{ binary_bin.name }}, {{ text_txt.name }}"
        fs.create_file("/tmp/template.j2", contents=template_content)

        # Change to temp directory
        os.chdir("/tmp")

        runner = CliRunner()
        result = runner.invoke(
            create_cli(),
            [
                "run",
                "template.j2",
                "schema.json",
                "--file",
                "ci:binary_bin",
                "binary.bin",
                "--file",
                "ci:text_txt",
                "text.txt",
                "--dry-run",
            ],
        )

        # Should succeed
        assert (
            result.exit_code == 0
        ), f"Expected success but got: {result.output}"
        # In dry run mode, template doesn't render output, just validates
        assert "Dry run completed successfully" in result.output
