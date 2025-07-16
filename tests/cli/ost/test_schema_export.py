"""Tests for OST schema export functionality."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from ostruct.cli.ost.schema_export import (
    SchemaExporter,
    SchemaExportError,
    export_inline_schema,
    get_schema_exporter,
)


class TestSchemaExporter:
    """Tests for SchemaExporter class."""

    def test_export_valid_schema(self) -> None:
        """Test exporting a valid JSON schema."""
        schema_content = """
        {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
                "score": {"type": "number"}
            },
            "required": ["result"]
        }
        """

        exporter = SchemaExporter()
        schema_path = exporter.export_inline_schema(schema_content)

        assert schema_path.exists()
        assert schema_path.suffix == ".json"
        assert schema_path.name.startswith("ost_schema_")

        # Verify content
        with open(schema_path, "r") as f:
            exported_schema = json.load(f)

        assert exported_schema["type"] == "object"
        assert "result" in exported_schema["properties"]
        assert "score" in exported_schema["properties"]
        assert exported_schema["required"] == ["result"]

        # Cleanup
        schema_path.unlink()

    def test_export_empty_schema(self) -> None:
        """Test error when schema content is empty."""
        exporter = SchemaExporter()

        with pytest.raises(
            SchemaExportError, match="Schema content is empty or missing"
        ):
            exporter.export_inline_schema("")

        with pytest.raises(
            SchemaExportError, match="Schema content is empty or missing"
        ):
            exporter.export_inline_schema("   ")

    def test_export_invalid_json(self) -> None:
        """Test error when schema content is invalid JSON."""
        exporter = SchemaExporter()
        invalid_json = '{"type": "object", "properties": {'

        with pytest.raises(SchemaExportError, match="Invalid JSON schema"):
            exporter.export_inline_schema(invalid_json)

    def test_export_non_object_schema(self) -> None:
        """Test error when schema is not a JSON object."""
        exporter = SchemaExporter()

        # Array schema
        array_schema = '["not", "an", "object"]'
        with pytest.raises(
            SchemaExportError, match="Schema must be a JSON object"
        ):
            exporter.export_inline_schema(array_schema)

        # String schema
        string_schema = '"not an object"'
        with pytest.raises(
            SchemaExportError, match="Schema must be a JSON object"
        ):
            exporter.export_inline_schema(string_schema)

    def test_export_uses_xdg_runtime_dir(self) -> None:
        """Test that export uses XDG_RUNTIME_DIR when available."""
        schema_content = '{"type": "object"}'

        with patch.dict("os.environ", {"XDG_RUNTIME_DIR": "/custom/runtime"}):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_file = mock_temp.return_value.__enter__.return_value
                mock_file.name = "/custom/runtime/ost_schema_test.json"
                mock_file.flush.return_value = None

                exporter = SchemaExporter()
                exporter.export_inline_schema(schema_content)

                # Verify tempfile was called with custom directory
                mock_temp.assert_called_once()
                call_kwargs = mock_temp.call_args[1]
                assert call_kwargs["dir"] == "/custom/runtime"

    def test_export_file_creation_error(self) -> None:
        """Test error handling when file creation fails."""
        schema_content = '{"type": "object"}'

        with patch(
            "tempfile.NamedTemporaryFile",
            side_effect=OSError("Permission denied"),
        ):
            exporter = SchemaExporter()
            with pytest.raises(
                SchemaExportError,
                match="Failed to create temporary schema file",
            ):
                exporter.export_inline_schema(schema_content)

    def test_cleanup_temp_files(self) -> None:
        """Test cleanup of temporary files."""
        schema_content = '{"type": "object"}'

        exporter = SchemaExporter()

        # Create multiple temp files
        path1 = exporter.export_inline_schema(schema_content)
        path2 = exporter.export_inline_schema(schema_content)

        assert path1.exists()
        assert path2.exists()
        assert len(exporter._temp_files) == 2

        # Cleanup
        exporter._cleanup_temp_files()

        assert not path1.exists()
        assert not path2.exists()
        assert len(exporter._temp_files) == 0

    def test_cleanup_ignores_missing_files(self) -> None:
        """Test cleanup handles missing files gracefully."""
        exporter = SchemaExporter()

        # Add a non-existent file to temp files list
        fake_path = Path("/nonexistent/file.json")
        exporter._temp_files.append(fake_path)

        # Should not raise an error
        exporter._cleanup_temp_files()
        assert len(exporter._temp_files) == 0

    def test_cleanup_ignores_permission_errors(self) -> None:
        """Test cleanup handles permission errors gracefully."""
        schema_content = '{"type": "object"}'

        exporter = SchemaExporter()
        _path = exporter.export_inline_schema(schema_content)

        # Mock unlink to raise OSError
        with patch.object(
            Path, "unlink", side_effect=OSError("Permission denied")
        ):
            # Should not raise an error
            exporter._cleanup_temp_files()

        # File should still be in the list but cleanup should have completed
        assert len(exporter._temp_files) == 0

    def test_atexit_registration(self) -> None:
        """Test that cleanup is registered with atexit."""
        with patch("atexit.register") as mock_register:
            exporter = SchemaExporter()
            mock_register.assert_called_once_with(exporter._cleanup_temp_files)

    def test_multiple_exports_track_files(self) -> None:
        """Test that multiple exports track all temporary files."""
        schema_content = '{"type": "object"}'

        exporter = SchemaExporter()

        path1 = exporter.export_inline_schema(schema_content)
        path2 = exporter.export_inline_schema(schema_content)
        path3 = exporter.export_inline_schema(schema_content)

        assert len(exporter._temp_files) == 3
        assert path1 in exporter._temp_files
        assert path2 in exporter._temp_files
        assert path3 in exporter._temp_files

        # Cleanup
        for path in [path1, path2, path3]:
            if path.exists():
                path.unlink()


class TestGetSchemaExporter:
    """Tests for get_schema_exporter function."""

    def test_get_singleton_exporter(self) -> None:
        """Test that get_schema_exporter returns a singleton."""
        exporter1 = get_schema_exporter()
        exporter2 = get_schema_exporter()

        assert exporter1 is exporter2
        assert isinstance(exporter1, SchemaExporter)

    def test_get_exporter_after_reset(self) -> None:
        """Test getting exporter after resetting global state."""
        # Get initial exporter
        exporter1 = get_schema_exporter()

        # Reset global state
        import ostruct.cli.ost.schema_export

        ostruct.cli.ost.schema_export._exporter = None

        # Get new exporter
        exporter2 = get_schema_exporter()

        assert exporter1 is not exporter2
        assert isinstance(exporter2, SchemaExporter)


class TestExportInlineSchema:
    """Tests for export_inline_schema convenience function."""

    def test_export_convenience_function(self) -> None:
        """Test the convenience function works correctly."""
        schema_content = (
            '{"type": "object", "properties": {"test": {"type": "string"}}}'
        )

        schema_path = export_inline_schema(schema_content)

        assert schema_path.exists()
        assert schema_path.suffix == ".json"

        # Verify content
        with open(schema_path, "r") as f:
            exported_schema = json.load(f)

        assert exported_schema["type"] == "object"
        assert "test" in exported_schema["properties"]

        # Cleanup
        schema_path.unlink()

    def test_export_convenience_function_error(self) -> None:
        """Test the convenience function propagates errors."""
        invalid_schema = '{"invalid": json}'

        with pytest.raises(SchemaExportError, match="Invalid JSON schema"):
            export_inline_schema(invalid_schema)

    def test_export_uses_global_exporter(self) -> None:
        """Test that convenience function uses global exporter."""
        schema_content = '{"type": "object"}'

        # Get the global exporter
        global_exporter = get_schema_exporter()

        # Export using convenience function
        with patch.object(
            global_exporter, "export_inline_schema"
        ) as mock_export:
            mock_export.return_value = Path("/tmp/test.json")

            result = export_inline_schema(schema_content)

            mock_export.assert_called_once_with(schema_content)
            assert result == Path("/tmp/test.json")


class TestSchemaExportIntegration:
    """Integration tests for schema export functionality."""

    def test_export_and_load_roundtrip(self) -> None:
        """Test complete export and load roundtrip."""
        original_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
                "active": {"type": "boolean"},
            },
            "required": ["name", "age"],
            "additionalProperties": False,
        }

        schema_content = json.dumps(original_schema, indent=2)

        # Export schema
        schema_path = export_inline_schema(schema_content)

        try:
            # Load and verify
            with open(schema_path, "r") as f:
                loaded_schema = json.load(f)

            assert loaded_schema == original_schema

        finally:
            # Cleanup
            if schema_path.exists():
                schema_path.unlink()

    def test_export_with_unicode_content(self) -> None:
        """Test exporting schema with unicode content."""
        schema_with_unicode = {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "A message with unicode: 你好世界 🌍",
                }
            },
        }

        schema_content = json.dumps(schema_with_unicode, ensure_ascii=False)

        # Export schema
        schema_path = export_inline_schema(schema_content)

        try:
            # Load and verify unicode is preserved
            with open(schema_path, "r", encoding="utf-8") as f:
                loaded_schema = json.load(f)

            assert (
                "你好世界 🌍"
                in loaded_schema["properties"]["message"]["description"]
            )

        finally:
            # Cleanup
            if schema_path.exists():
                schema_path.unlink()
