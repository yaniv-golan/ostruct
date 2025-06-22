"""Tests for Template Structure Enhancement System (TSES) v2.0 core functionality."""

from typing import Optional

import pytest
from jinja2 import Environment
from ostruct.cli.template_filters import (
    AliasManager,
    TemplateStructureError,
    XMLAppendixBuilder,
    file_ref,
    format_tses_error,
    register_tses_filters,
)


class MockFileInfo:
    """Mock FileInfo for testing."""

    def __init__(
        self,
        path: str,
        content: str = "test content",
        parent_alias: Optional[str] = None,
        relative_path: Optional[str] = None,
        base_path: Optional[str] = None,
        from_collection: bool = False,
        attachment_type: str = "file",
    ):
        self.path = path
        self.content = content
        self.parent_alias = parent_alias
        self.relative_path = relative_path or path.split("/")[-1]
        self.base_path = base_path or "/".join(path.split("/")[:-1])
        self.from_collection = from_collection
        self.attachment_type = attachment_type
        self.name = path.split("/")[-1]


class TestTemplateStructureError:
    """Test TSES error handling."""

    def test_error_creation(self):
        """Test creating TemplateStructureError with suggestions."""
        error = TemplateStructureError(
            "Test error message", ["Suggestion 1", "Suggestion 2"]
        )
        assert str(error) == "Test error message"
        assert error.suggestions == ["Suggestion 1", "Suggestion 2"]

    def test_error_without_suggestions(self):
        """Test creating TemplateStructureError without suggestions."""
        error = TemplateStructureError("Test error message")
        assert str(error) == "Test error message"
        assert error.suggestions == []

    def test_format_tses_error(self):
        """Test formatting TSES errors with suggestions."""
        error = TemplateStructureError(
            "Unknown alias 'missing'",
            ["Check your --dir attachments", "Use --file for single files"],
        )
        formatted = format_tses_error(error)
        expected = (
            "Template Structure Error: Unknown alias 'missing'\n"
            "Suggestions:\n"
            "  • Check your --dir attachments\n"
            "  • Use --file for single files"
        )
        assert formatted == expected

    def test_format_tses_error_no_suggestions(self):
        """Test formatting TSES errors without suggestions."""
        error = TemplateStructureError("Simple error")
        formatted = format_tses_error(error)
        assert formatted == "Template Structure Error: Simple error"


class TestAliasManager:
    """Test the AliasManager component."""

    def test_register_single_file(self):
        """Test registering a single file attachment."""
        manager = AliasManager()
        file_info = MockFileInfo("test.py", "print('hello')")

        manager.register_attachment("source", "/path/test.py", [file_info])

        assert "source" in manager.aliases
        assert manager.aliases["source"]["type"] == "file"
        assert manager.aliases["source"]["path"] == "/path/test.py"
        assert len(manager.aliases["source"]["files"]) == 1

    def test_register_directory(self):
        """Test registering a directory attachment."""
        manager = AliasManager()
        files = [
            MockFileInfo("file1.py", "content1", attachment_type="dir"),
            MockFileInfo("file2.py", "content2", attachment_type="dir"),
        ]

        manager.register_attachment("source", "/path/to/src", files)

        assert "source" in manager.aliases
        assert manager.aliases["source"]["type"] == "dir"
        assert manager.aliases["source"]["path"] == "/path/to/src"
        assert len(manager.aliases["source"]["files"]) == 2

    def test_register_collection(self):
        """Test registering a file collection."""
        manager = AliasManager()
        files = [
            MockFileInfo("data1.csv", "csv content"),
            MockFileInfo("data2.json", "json content"),
        ]

        manager.register_attachment(
            "data", "/path/to/data", files, is_collection=True
        )

        assert "data" in manager.aliases
        assert manager.aliases["data"]["type"] == "collection"
        assert manager.aliases["data"]["path"] == "/path/to/data"
        assert len(manager.aliases["data"]["files"]) == 2

    def test_reference_valid_alias(self):
        """Test referencing a valid alias."""
        manager = AliasManager()
        files = [MockFileInfo("test.py")]
        manager.register_attachment("source", "/path", files)

        manager.reference_alias("source")

        assert "source" in manager.referenced
        referenced = manager.get_referenced_aliases()
        assert "source" in referenced

    def test_reference_invalid_alias(self):
        """Test referencing an invalid alias raises error."""
        manager = AliasManager()
        manager.register_attachment(
            "valid", "/path", [MockFileInfo("test.py")]
        )

        with pytest.raises(TemplateStructureError) as exc_info:
            manager.reference_alias("missing")

        error = exc_info.value
        assert "Unknown alias 'missing'" in str(error)
        assert "Available aliases: valid" in error.suggestions[0]
        assert (
            "Check your --dir and --file attachments" in error.suggestions[1]
        )

    def test_get_referenced_aliases_empty(self):
        """Test getting referenced aliases when none are referenced."""
        manager = AliasManager()
        manager.register_attachment(
            "source", "/path", [MockFileInfo("test.py")]
        )

        referenced = manager.get_referenced_aliases()
        assert referenced == {}

    def test_get_referenced_aliases_multiple(self):
        """Test getting multiple referenced aliases."""
        manager = AliasManager()
        manager.register_attachment(
            "source", "/path", [MockFileInfo("test.py")]
        )
        manager.register_attachment(
            "config", "/config", [MockFileInfo("config.yaml")]
        )

        manager.reference_alias("source")
        manager.reference_alias("config")

        referenced = manager.get_referenced_aliases()
        assert len(referenced) == 2
        assert "source" in referenced
        assert "config" in referenced


class TestXMLAppendixBuilder:
    """Test the XMLAppendixBuilder component."""

    def test_build_empty_appendix(self):
        """Test building appendix with no referenced aliases."""
        manager = AliasManager()
        builder = XMLAppendixBuilder(manager)

        appendix = builder.build_appendix()
        assert appendix == ""

    def test_build_single_file_appendix(self):
        """Test building appendix with a single file."""
        manager = AliasManager()
        file_info = MockFileInfo("config.yaml", "debug: true\nmode: test")

        manager.register_attachment("config", "/path/config.yaml", [file_info])
        manager.reference_alias("config")

        builder = XMLAppendixBuilder(manager)
        appendix = builder.build_appendix()

        expected_lines = [
            "<files>",
            '  <file alias="config" path="/path/config.yaml">',
            "    <content><![CDATA[debug: true\nmode: test]]></content>",
            "  </file>",
            "</files>",
        ]
        assert appendix == "\n".join(expected_lines)

    def test_build_directory_appendix(self):
        """Test building appendix with a directory."""
        manager = AliasManager()
        files = [
            MockFileInfo(
                "src/main.py",
                "def main(): pass",
                relative_path="main.py",
                attachment_type="dir",
            ),
            MockFileInfo(
                "src/utils.py",
                "def helper(): pass",
                relative_path="utils.py",
                attachment_type="dir",
            ),
        ]

        manager.register_attachment("source", "/path/src", files)
        manager.reference_alias("source")

        builder = XMLAppendixBuilder(manager)
        appendix = builder.build_appendix()

        assert "<files>" in appendix
        assert '<dir alias="source" path="/path/src">' in appendix
        assert "def main(): pass" in appendix
        assert "def helper(): pass" in appendix
        assert 'path="main.py"' in appendix
        assert 'path="utils.py"' in appendix

    def test_build_collection_appendix(self):
        """Test building appendix with a collection."""
        manager = AliasManager()
        files = [
            MockFileInfo(
                "data1.csv", "col1,col2\nval1,val2", relative_path="data1.csv"
            ),
            MockFileInfo(
                "data2.json", '{"key": "value"}', relative_path="data2.json"
            ),
        ]

        manager.register_attachment(
            "datasets", "/path/data", files, is_collection=True
        )
        manager.reference_alias("datasets")

        builder = XMLAppendixBuilder(manager)
        appendix = builder.build_appendix()

        assert "<files>" in appendix
        assert '<collection alias="datasets" path="/path/data">' in appendix
        assert '<file path="data1.csv">' in appendix
        assert '<file path="data2.json">' in appendix
        assert "col1,col2\nval1,val2" in appendix
        assert '{"key": "value"}' in appendix
        assert "</collection>" in appendix
        assert "</files>" in appendix

    def test_build_mixed_appendix(self):
        """Test building appendix with mixed attachment types."""
        manager = AliasManager()

        # Single file
        config_file = MockFileInfo(
            "config.yaml", "debug: true", attachment_type="file"
        )
        manager.register_attachment("config", "/config.yaml", [config_file])

        # Directory (multiple files)
        source_files = [
            MockFileInfo(
                "src/main.py",
                "def main(): pass",
                relative_path="main.py",
                attachment_type="dir",
            ),
            MockFileInfo(
                "src/utils.py",
                "def helper(): pass",
                relative_path="utils.py",
                attachment_type="dir",
            ),
        ]
        manager.register_attachment("source", "/src", source_files)

        # Reference both
        manager.reference_alias("config")
        manager.reference_alias("source")

        builder = XMLAppendixBuilder(manager)
        appendix = builder.build_appendix()

        # Should contain both file and dir sections
        assert '<file alias="config"' in appendix
        assert '<dir alias="source"' in appendix
        assert "debug: true" in appendix
        assert "def main(): pass" in appendix


class TestFileRefFunction:
    """Test the file_ref() template function."""

    def test_file_ref_valid_alias(self):
        """Test file_ref with a valid alias."""
        manager = AliasManager()
        files = [MockFileInfo("test.py")]
        manager.register_attachment("source", "/path", files)

        # Set global alias manager
        import ostruct.cli.template_filters as tf

        tf._alias_manager = manager

        result = file_ref("source")
        assert result == "<source>"
        assert "source" in manager.referenced

    def test_file_ref_invalid_alias(self):
        """Test file_ref with an invalid alias."""
        manager = AliasManager()

        # Set global alias manager
        import ostruct.cli.template_filters as tf

        tf._alias_manager = manager

        with pytest.raises(TemplateStructureError) as exc_info:
            file_ref("missing")

        assert "Unknown alias 'missing'" in str(exc_info.value)

    def test_file_ref_no_manager(self):
        """Test file_ref when no alias manager is set."""
        # Clear global alias manager
        import ostruct.cli.template_filters as tf

        tf._alias_manager = None

        with pytest.raises(TemplateStructureError) as exc_info:
            file_ref("any_alias")

        assert "File references not initialized" in str(exc_info.value)


class TestTSESIntegration:
    """Test TSES integration with Jinja2 environment."""

    def test_register_tses_filters(self):
        """Test registering TSES filters in Jinja2 environment."""
        env = Environment()
        manager = AliasManager()

        # Register files
        files = [MockFileInfo("test.py", attachment_type="file")]
        manager.register_attachment("source", "/path", files)

        # Register TSES filters
        register_tses_filters(env, manager)

        # Should have file_ref function available
        assert "file_ref" in env.globals

        # Should be able to call file_ref
        file_ref_func = env.globals["file_ref"]
        result = file_ref_func("source")
        assert result == "<source>"
        assert "source" in manager.referenced

    def test_template_rendering_with_file_ref(self):
        """Test template rendering with file_ref function."""
        env = Environment()
        manager = AliasManager()

        # Register files
        files = [
            MockFileInfo("config.yaml", "debug: true", attachment_type="file")
        ]
        manager.register_attachment("config", "/path", files)

        # Register TSES filters
        register_tses_filters(env, manager)

        # Create template with file_ref
        template_content = (
            "Please analyze {{ file_ref('config') }} for issues."
        )
        template = env.from_string(template_content)

        # Render template
        result = template.render()
        assert result == "Please analyze <config> for issues."
        assert "config" in manager.referenced
