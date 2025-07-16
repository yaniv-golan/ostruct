"""Tests for OST front-matter parsing."""

import tempfile
from pathlib import Path

import pytest
from ostruct.cli.ost.frontmatter import (
    FrontMatterError,
    FrontMatterParser,
    extract_body,
    parse_frontmatter,
)


class TestFrontMatterParser:
    """Tests for FrontMatterParser class."""

    def test_valid_frontmatter(self) -> None:
        """Test parsing valid front-matter."""
        content = """#!/usr/bin/env -S ostruct runx
---
cli:
  name: test_cli
  description: Test CLI description
  positional:
    - name: input_file
      type: path
      help: Input file path
  options:
    --verbose:
      action: store_true
      help: Enable verbose output
  global_args:
    model:
      mode: fixed
      value: gpt-4o
    temperature:
      mode: pass-through
      default: 0.7
schema: |
  {
    "type": "object",
    "properties": {
      "result": {"type": "string"}
    },
    "required": ["result"]
  }
defaults:
  verbose: false
---
Hello {{ input_file }}!
This is the template body.
"""

        parser = FrontMatterParser(content)
        metadata, body_start = parser.parse()

        assert metadata["cli"]["name"] == "test_cli"
        assert metadata["cli"]["description"] == "Test CLI description"
        assert len(metadata["cli"]["positional"]) == 1
        assert metadata["cli"]["positional"][0]["name"] == "input_file"
        assert metadata["cli"]["global_args"]["model"]["mode"] == "fixed"
        assert metadata["cli"]["global_args"]["model"]["value"] == "gpt-4o"
        assert "schema" in metadata
        assert "defaults" in metadata
        assert body_start == 31  # Line after closing ---

    def test_no_shebang(self) -> None:
        """Test parsing without shebang."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        metadata, body_start = parser.parse()

        assert metadata["cli"]["name"] == "test_cli"
        assert body_start == 7

    def test_missing_frontmatter_delimiter(self) -> None:
        """Test error when front-matter delimiter is missing."""
        content = """#!/usr/bin/env -S ostruct runx
cli:
  name: test_cli
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="No front-matter delimiter found"
        ):
            parser.parse()

    def test_missing_closing_delimiter(self) -> None:
        """Test error when closing delimiter is missing."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
schema: |
  {"type": "object"}
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="No closing front-matter delimiter found"
        ):
            parser.parse()

    def test_invalid_yaml(self) -> None:
        """Test error with invalid YAML."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
  invalid: [unclosed list
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="Invalid YAML in front-matter"
        ):
            parser.parse()

    def test_non_dict_frontmatter(self) -> None:
        """Test error when front-matter is not a dict."""
        content = """---
- this is a list
- not a dict
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="Front-matter must be a YAML object"
        ):
            parser.parse()

    def test_missing_cli_section(self) -> None:
        """Test error when cli section is missing."""
        content = """---
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="Front-matter must contain 'cli' section"
        ):
            parser.parse()

    def test_invalid_cli_section(self) -> None:
        """Test error when cli section is not a dict."""
        content = """---
cli: "not a dict"
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="'cli' section must be an object"
        ):
            parser.parse()

    def test_missing_cli_name(self) -> None:
        """Test error when cli.name is missing."""
        content = """---
cli:
  description: Test CLI description
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="'cli' section must contain 'name' field"
        ):
            parser.parse()

    def test_invalid_cli_name(self) -> None:
        """Test error when cli.name is invalid."""
        content = """---
cli:
  name: ""
  description: Test CLI description
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="'cli.name' must be a non-empty string"
        ):
            parser.parse()

    def test_missing_cli_description(self) -> None:
        """Test error when cli.description is missing."""
        content = """---
cli:
  name: test_cli
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError,
            match="'cli' section must contain 'description' field",
        ):
            parser.parse()

    def test_missing_schema(self) -> None:
        """Test error when schema is missing."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError,
            match="Front-matter must contain 'schema' section",
        ):
            parser.parse()

    def test_empty_schema(self) -> None:
        """Test error when schema is empty."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
schema: ""
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="'schema' must be a non-empty string"
        ):
            parser.parse()

    def test_invalid_positional_args(self) -> None:
        """Test error with invalid positional args structure."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
  positional: "not a list"
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="'cli.positional' must be a list"
        ):
            parser.parse()

    def test_invalid_positional_arg_item(self) -> None:
        """Test error with invalid positional arg item."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
  positional:
    - "not a dict"
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="Positional argument 0 must be an object"
        ):
            parser.parse()

    def test_missing_positional_arg_name(self) -> None:
        """Test error when positional arg missing name."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
  positional:
    - type: string
      help: Some help
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError,
            match="Positional argument 0 must have 'name' field",
        ):
            parser.parse()

    def test_invalid_global_args_structure(self) -> None:
        """Test error with invalid global_args structure."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
  global_args: "not a dict"
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="'cli.global_args' must be an object"
        ):
            parser.parse()

    def test_invalid_global_arg_config(self) -> None:
        """Test error with invalid global arg config."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
  global_args:
    model: "not a dict"
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError,
            match="Global arg 'model' config must be an object",
        ):
            parser.parse()

    def test_missing_global_arg_mode(self) -> None:
        """Test error when global arg missing mode."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
  global_args:
    model:
      value: gpt-4o
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="Global arg 'model' must have 'mode' field"
        ):
            parser.parse()

    def test_invalid_global_arg_mode(self) -> None:
        """Test error with invalid global arg mode."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
  global_args:
    model:
      mode: invalid_mode
      value: gpt-4o
schema: |
  {"type": "object"}
---
Template body
"""

        parser = FrontMatterParser(content)
        with pytest.raises(
            FrontMatterError, match="Global arg 'model' mode must be one of"
        ):
            parser.parse()


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parse_valid_file(self) -> None:
        """Test parsing a valid OST file."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
schema: |
  {"type": "object"}
---
Template body
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ost", delete=False
        ) as f:
            f.write(content)
            f.flush()

            try:
                metadata, body_start = parse_frontmatter(Path(f.name))
                assert metadata["cli"]["name"] == "test_cli"
                assert body_start == 7
            finally:
                Path(f.name).unlink()

    def test_file_not_found(self) -> None:
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Template file not found"):
            parse_frontmatter(Path("/nonexistent/file.ost"))

    def test_unicode_decode_error(self) -> None:
        """Test error with invalid UTF-8 file."""
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".ost", delete=False
        ) as f:
            f.write(b"\xff\xfe\x00\x00")  # Invalid UTF-8
            f.flush()

            try:
                with pytest.raises(
                    FrontMatterError,
                    match="Failed to read template file as UTF-8",
                ):
                    parse_frontmatter(Path(f.name))
            finally:
                Path(f.name).unlink()


class TestExtractBody:
    """Tests for extract_body function."""

    def test_extract_body_normal(self) -> None:
        """Test extracting body from normal file."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
schema: |
  {"type": "object"}
---
Hello {{ name }}!
This is the template body.
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ost", delete=False
        ) as f:
            f.write(content)
            f.flush()

            try:
                body = extract_body(Path(f.name), 6)
                expected = "Hello {{ name }}!\nThis is the template body."
                body = extract_body(Path(f.name), 7)
                assert body == expected
            finally:
                Path(f.name).unlink()

    def test_extract_body_empty(self) -> None:
        """Test extracting body when body is empty."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
schema: |
  {"type": "object"}
---
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ost", delete=False
        ) as f:
            f.write(content)
            f.flush()

            try:
                body = extract_body(Path(f.name), 7)
                assert body == ""
            finally:
                Path(f.name).unlink()

    def test_extract_body_beyond_end(self) -> None:
        """Test extracting body when start line is beyond file end."""
        content = """---
cli:
  name: test_cli
  description: Test CLI description
schema: |
  {"type": "object"}
---
Short body
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ost", delete=False
        ) as f:
            f.write(content)
            f.flush()

            try:
                body = extract_body(Path(f.name), 100)
                assert body == ""
            finally:
                Path(f.name).unlink()
