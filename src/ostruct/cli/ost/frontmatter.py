"""Front-matter parsing for OST templates.

This module handles parsing YAML front-matter from .ost template files,
validating the structure, and extracting metadata and body content.
"""

from pathlib import Path
from typing import Any, Dict, Tuple

import yaml


class FrontMatterError(Exception):
    """Raised when front-matter parsing or validation fails."""

    pass


class FrontMatterParser:
    """Parser for OST template front-matter."""

    def __init__(self, content: str) -> None:
        """Initialize parser with template content.

        Args:
            content: Raw template file content
        """
        self.content = content
        self.lines = content.splitlines()

    def parse(self) -> Tuple[Dict[str, Any], int]:
        """Parse front-matter and return metadata with body start position.

        Returns:
            Tuple of (metadata dict, body_start_line_number)

        Raises:
            FrontMatterError: If parsing or validation fails
        """
        # Strip shebang if present
        start_line = 0
        if self.lines and self.lines[0].startswith("#!"):
            start_line = 1

        # Look for front-matter delimiter
        if (
            start_line >= len(self.lines)
            or self.lines[start_line].strip() != "---"
        ):
            raise FrontMatterError(
                "No front-matter delimiter found (expected '---')"
            )

        # Find end delimiter
        end_line = None
        for i in range(start_line + 1, len(self.lines)):
            if self.lines[i].strip() == "---":
                end_line = i
                break

        if end_line is None:
            raise FrontMatterError("No closing front-matter delimiter found")

        # Extract YAML content
        yaml_lines = self.lines[start_line + 1 : end_line]
        yaml_content = "\n".join(yaml_lines)

        # Parse YAML
        try:
            metadata = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise FrontMatterError(f"Invalid YAML in front-matter: {e}")

        if not isinstance(metadata, dict):
            raise FrontMatterError("Front-matter must be a YAML object")

        # Validate structure and warn about format issues
        self._validate_metadata(metadata)

        # Calculate body start position (line after closing delimiter)
        body_start = end_line + 1

        return metadata, body_start

    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """Validate front-matter metadata structure.

        Args:
            metadata: Parsed YAML metadata

        Raises:
            FrontMatterError: If validation fails
        """
        # Required: cli section
        if "cli" not in metadata:
            raise FrontMatterError("Front-matter must contain 'cli' section")

        cli = metadata["cli"]
        if not isinstance(cli, dict):
            raise FrontMatterError("'cli' section must be an object")

        # Required: cli.name
        if "name" not in cli:
            raise FrontMatterError("'cli' section must contain 'name' field")

        if not isinstance(cli["name"], str) or not cli["name"].strip():
            raise FrontMatterError("'cli.name' must be a non-empty string")

        # Required: cli.description
        if "description" not in cli:
            raise FrontMatterError(
                "'cli' section must contain 'description' field"
            )

        if (
            not isinstance(cli["description"], str)
            or not cli["description"].strip()
        ):
            raise FrontMatterError(
                "'cli.description' must be a non-empty string"
            )

        # Required: schema section
        if "schema" not in metadata:
            raise FrontMatterError(
                "Front-matter must contain 'schema' section"
            )

        if (
            not isinstance(metadata["schema"], str)
            or not metadata["schema"].strip()
        ):
            raise FrontMatterError("'schema' must be a non-empty string")

        # Validate documented top-level fields only
        self._validate_top_level_fields(metadata)

        # Validate CLI section structure
        self._validate_cli_structure(cli)

        # Validate other optional sections
        self._validate_optional_sections(metadata)

    def _validate_top_level_fields(self, metadata: Dict[str, Any]) -> None:
        """Validate that only documented top-level fields are present.

        Args:
            metadata: Full parsed metadata
        """
        documented_top_level = {
            "cli",
            "schema",
            "defaults",
            "global_args",
            "global_flags",
        }

        for field in metadata.keys():
            if field not in documented_top_level:
                raise FrontMatterError(
                    f"Unknown top-level field '{field}'. "
                    f"Allowed fields are: {', '.join(sorted(documented_top_level))}"
                )

    def _validate_cli_structure(self, cli: Dict[str, Any]) -> None:
        """Validate CLI section structure.

        Args:
            cli: CLI section of metadata
        """
        # Validate positional args structure
        if "positional" in cli:
            if not isinstance(cli["positional"], list):
                raise FrontMatterError("'cli.positional' must be a list")

            for i, arg in enumerate(cli["positional"]):
                if not isinstance(arg, dict):
                    raise FrontMatterError(
                        f"Positional argument {i} must be an object"
                    )

                if "name" not in arg:
                    raise FrontMatterError(
                        f"Positional argument {i} must have 'name' field"
                    )

                if not isinstance(arg["name"], str) or not arg["name"].strip():
                    raise FrontMatterError(
                        f"Positional argument {i} 'name' must be a non-empty string"
                    )

        # Validate options structure
        if "options" in cli:
            if not isinstance(cli["options"], (dict, list)):
                raise FrontMatterError(
                    "'cli.options' must be an object or list"
                )

        # Validate CLI-level global_args structure
        if "global_args" in cli:
            self._validate_global_args_section(
                cli["global_args"], "'cli.global_args'"
            )

    def _validate_optional_sections(self, metadata: Dict[str, Any]) -> None:
        """Validate optional sections structure.

        Args:
            metadata: Full parsed metadata
        """
        # Validate defaults structure
        if "defaults" in metadata:
            if not isinstance(metadata["defaults"], dict):
                raise FrontMatterError("'defaults' must be an object")

        # Validate global_args structure
        if "global_args" in metadata:
            self._validate_global_args_section(
                metadata["global_args"], "'global_args'"
            )

        # Validate global_flags structure
        if "global_flags" in metadata:
            if not isinstance(metadata["global_flags"], list):
                raise FrontMatterError(
                    "'global_flags' must be a list of strings"
                )

            for i, flag in enumerate(metadata["global_flags"]):
                if not isinstance(flag, str):
                    raise FrontMatterError(
                        f"'global_flags' item {i} must be a string, got {type(flag).__name__}"
                    )

                if not flag.strip():
                    raise FrontMatterError(
                        f"'global_flags' item {i} cannot be empty"
                    )

                # Allow both flags (starting with -) and values (not starting with -)
                # This supports the format: ["--flag", "value", "--other-flag", "other-value"]

    def _validate_global_args_section(
        self, global_args: Any, section_name: str
    ) -> None:
        """Validate global_args section structure.

        Args:
            global_args: The global_args value to validate
            section_name: Human-readable section name for error messages
        """
        if not isinstance(global_args, dict):
            raise FrontMatterError(f"{section_name} must be an object")

        for flag, config in global_args.items():
            # Handle special boolean field
            if flag == "pass_through_global":
                if not isinstance(config, bool):
                    raise FrontMatterError(
                        "'pass_through_global' must be a boolean"
                    )
                continue

            # Handle policy configuration objects
            if not isinstance(config, dict):
                raise FrontMatterError(
                    f"Global arg '{flag}' config must be an object"
                )

            if "mode" not in config:
                raise FrontMatterError(
                    f"Global arg '{flag}' must have 'mode' field"
                )

            mode = config["mode"]
            if mode not in ["fixed", "pass-through", "allowed", "blocked"]:
                raise FrontMatterError(
                    f"Global arg '{flag}' mode must be one of: fixed, pass-through, allowed, blocked"
                )


def parse_frontmatter(file_path: Path) -> Tuple[Dict[str, Any], int]:
    """Parse front-matter from an OST template file.

    Args:
        file_path: Path to the .ost template file

    Returns:
        Tuple of (metadata dict, body_start_line_number)

    Raises:
        FrontMatterError: If parsing or validation fails
        FileNotFoundError: If file doesn't exist
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found: {file_path}")
    except UnicodeDecodeError as e:
        raise FrontMatterError(f"Failed to read template file as UTF-8: {e}")

    parser = FrontMatterParser(content)
    return parser.parse()


def extract_body(file_path: Path, body_start: int) -> str:
    """Extract the Jinja template body from an OST file.

    Args:
        file_path: Path to the .ost template file
        body_start: Line number where template body starts

    Returns:
        The Jinja template body content

    Raises:
        FileNotFoundError: If file doesn't exist
        FrontMatterError: If body extraction fails
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found: {file_path}")
    except UnicodeDecodeError as e:
        raise FrontMatterError(f"Failed to read template file as UTF-8: {e}")

    lines = content.splitlines()

    if body_start >= len(lines):
        return ""  # Empty body

    body_lines = lines[body_start:]
    return "\n".join(body_lines)
