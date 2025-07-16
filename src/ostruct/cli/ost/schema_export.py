"""Schema export functionality for OST templates.

This module handles exporting inline schemas from OST front-matter to
temporary files for use with the ostruct run command.
"""

import atexit
import json
import os
import tempfile
from pathlib import Path
from typing import Optional


class SchemaExportError(Exception):
    """Raised when schema export fails."""

    pass


class SchemaExporter:
    """Handles exporting inline schemas to temporary files."""

    def __init__(self) -> None:
        """Initialize schema exporter."""
        self._temp_files: list[Path] = []

        # Register cleanup function
        atexit.register(self._cleanup_temp_files)

    def export_inline_schema(self, schema_content: str) -> Path:
        """Export inline schema to a temporary file.

        Args:
            schema_content: JSON schema content as string

        Returns:
            Path to the temporary schema file

        Raises:
            SchemaExportError: If export fails
        """
        if not schema_content or not schema_content.strip():
            raise SchemaExportError("Schema content is empty or missing")

        # Validate JSON format
        try:
            parsed_schema = json.loads(schema_content)
        except json.JSONDecodeError as e:
            raise SchemaExportError(f"Invalid JSON schema: {e}")

        # Ensure it's a valid schema object
        if not isinstance(parsed_schema, dict):
            raise SchemaExportError("Schema must be a JSON object")

        # Create temporary file
        try:
            # Use system temp directory or XDG_RUNTIME_DIR if available
            temp_dir = (
                os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
            )

            # Create named temporary file
            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                prefix="ost_schema_",
                dir=temp_dir,
                delete=False,
                encoding="utf-8",
            )

            # Write schema content
            json.dump(parsed_schema, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()

            temp_path = Path(temp_file.name)
            temp_file.close()

            # Track for cleanup
            self._temp_files.append(temp_path)

            return temp_path

        except (OSError, IOError) as e:
            raise SchemaExportError(
                f"Failed to create temporary schema file: {e}"
            )

    def _cleanup_temp_files(self) -> None:
        """Clean up temporary schema files."""
        for temp_path in self._temp_files:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                # Ignore cleanup errors
                pass

        self._temp_files.clear()


# Global exporter instance
_exporter: Optional[SchemaExporter] = None


def get_schema_exporter() -> SchemaExporter:
    """Get the global schema exporter instance.

    Returns:
        SchemaExporter instance
    """
    global _exporter
    if _exporter is None:
        _exporter = SchemaExporter()
    return _exporter


def export_inline_schema(schema_content: str) -> Path:
    """Export inline schema to a temporary file.

    This is a convenience function that uses the global exporter instance.

    Args:
        schema_content: JSON schema content as string

    Returns:
        Path to the temporary schema file

    Raises:
        SchemaExportError: If export fails
    """
    exporter = get_schema_exporter()
    return exporter.export_inline_schema(schema_content)
