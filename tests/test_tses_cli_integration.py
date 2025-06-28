"""Tests for TSES v2.0 CLI integration."""

import os
import tempfile
from pathlib import Path

import pytest
from ostruct.cli.attachment_processor import (
    AttachmentProcessor,
    AttachmentSpec,
)
from ostruct.cli.file_info import FileInfo
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_filters import TemplateStructureError, file_ref


class TestTSESAttachmentIntegration:
    """Test TSES integration with attachment processing."""

    def test_attachment_spec_tses_fields(self):
        """Test AttachmentSpec includes TSES fields."""
        spec = AttachmentSpec(
            alias="test",
            path="/path/test.txt",
            targets={"prompt"},
            from_collection=True,
            collection_base_alias="original",
        )

        assert spec.from_collection is True
        assert spec.collection_base_alias == "original"

    def test_file_info_tses_fields(self):
        """Test FileInfo includes TSES fields."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            security_manager = SecurityManager(base_dir=".")
            file_info = FileInfo.from_path(
                temp_path,
                security_manager,
                parent_alias="test_alias",
                relative_path="test.txt",
                base_path="/base/path",
                from_collection=True,
            )

            assert file_info.parent_alias == "test_alias"
            assert file_info.relative_path == "test.txt"
            assert file_info.base_path == "/base/path"
            assert file_info.from_collection is True
        finally:
            os.unlink(temp_path)

    def test_collection_processing_sets_tses_fields(self):
        """Test that collection processing sets TSES fields correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            file1 = Path(temp_dir) / "file1.txt"
            file2 = Path(temp_dir) / "file2.txt"
            filelist = Path(temp_dir) / "filelist.txt"

            file1.write_text("content1")
            file2.write_text("content2")
            filelist.write_text(f"{file1}\n{file2}\n")

            # Create attachment for collection
            attachment = {
                "alias": "test_collection",
                "path": ("@", str(filelist)),
                "targets": {"prompt"},
                "recursive": False,
                "pattern": None,
            }

            security_manager = SecurityManager(base_dir=".")
            processor = AttachmentProcessor(security_manager)

            # Process filelist
            specs = processor._process_filelist(str(filelist), attachment)

            # Check TSES fields are set
            assert len(specs) == 2
            for spec in specs:
                assert spec.from_collection is True
                assert spec.collection_base_alias == "test_collection"
                assert spec.alias.startswith("test_collection_")


class TestTSESTemplateProcessing:
    """Test TSES integration with template processing through normal CLI flow."""

    def test_file_reference_integration_with_template_env(self):
        """Test that file references work with the integrated template environment."""
        from ostruct.cli.template_env import create_jinja_env
        from ostruct.cli.template_filters import AliasManager

        # Mock FileInfo objects with TSES fields
        class MockFileInfo:
            def __init__(
                self,
                path,
                parent_alias=None,
                relative_path=None,
                base_path=None,
                from_collection=False,
                attachment_type="file",
            ):
                self.path = path
                self.content = f"Content of {path}"
                self.parent_alias = parent_alias
                self.relative_path = relative_path or os.path.basename(path)
                self.base_path = base_path or os.path.dirname(path)
                self.from_collection = from_collection
                self.attachment_type = attachment_type
                self.name = os.path.basename(path)

        # Create files with TSES metadata
        files = [
            MockFileInfo(
                "src/main.py",
                parent_alias="source",
                relative_path="main.py",
                base_path="/project/src",
                attachment_type="dir",
            ),
            MockFileInfo(
                "config.yaml",
                parent_alias="config",
                relative_path="config.yaml",
                base_path="/project",
                attachment_type="file",
            ),
        ]

        # Create environment with file reference support
        env, alias_manager = create_jinja_env(files=files)

        # Verify environment setup
        assert "file_ref" in env.globals
        assert isinstance(alias_manager, AliasManager)
        assert len(alias_manager.aliases) == 2
        assert "source" in alias_manager.aliases
        assert "config" in alias_manager.aliases

        # Verify alias types
        assert alias_manager.aliases["source"]["type"] == "dir"
        assert alias_manager.aliases["config"]["type"] == "file"

    def test_template_rendering_with_integrated_file_ref(self):
        """Test template rendering with file_ref function through integrated approach."""
        from ostruct.cli.template_env import create_jinja_env

        # Mock FileInfo
        class MockFileInfo:
            def __init__(
                self, path, content, parent_alias=None, attachment_type="file"
            ):
                self.path = path
                self.content = content
                self.parent_alias = parent_alias
                self.relative_path = os.path.basename(path)
                self.base_path = os.path.dirname(path)
                self.from_collection = False
                self.attachment_type = attachment_type
                self.name = os.path.basename(path)

        # Create test files
        files = [
            MockFileInfo("config.yaml", "debug: true", parent_alias="config"),
            MockFileInfo(
                "src/main.py",
                "def main(): pass",
                parent_alias="source",
                attachment_type="dir",
            ),
        ]

        # Create environment with file reference support
        env, alias_manager = create_jinja_env(files=files)

        # Test template with file_ref
        template_str = """
Configuration: {{ file_ref("config") }}
Source code: {{ file_ref("source") }}
        """.strip()

        template = env.from_string(template_str)
        result = template.render()

        # Check that file_ref calls work
        assert "<config>" in result
        assert "<source>" in result

        # Check that aliases were referenced
        assert "config" in alias_manager.referenced
        assert "source" in alias_manager.referenced

    def test_xml_appendix_generation_integrated(self):
        """Test XML appendix generation with integrated approach."""
        from ostruct.cli.template_env import create_jinja_env
        from ostruct.cli.template_filters import XMLAppendixBuilder

        # Mock FileInfo
        class MockFileInfo:
            def __init__(
                self, path, content, parent_alias=None, attachment_type="file"
            ):
                self.path = path
                self.content = content
                self.parent_alias = parent_alias
                self.relative_path = os.path.basename(path)
                self.base_path = os.path.dirname(path)
                self.from_collection = False
                self.attachment_type = attachment_type
                self.name = os.path.basename(path)

        # Create test files
        files = [
            MockFileInfo(
                "config.yaml", "debug: true\nmode: test", parent_alias="config"
            )
        ]

        # Create environment and render template
        env, alias_manager = create_jinja_env(files=files)

        template_str = "Check the configuration in {{ file_ref('config') }}."
        template = env.from_string(template_str)
        rendered = template.render()

        # Generate appendix
        builder = XMLAppendixBuilder(alias_manager)
        appendix = builder.build_appendix()

        # Verify appendix content
        assert "<files>" in appendix
        assert '<file alias="config"' in appendix
        assert "debug: true\nmode: test" in appendix
        assert "</files>" in appendix

        # Verify complete output
        complete_output = rendered + "\n\n" + appendix
        assert "Check the configuration in <config>." in complete_output
        assert "<files>" in complete_output

    def test_no_appendix_when_no_references_integrated(self):
        """Test that no appendix is generated when no file_ref calls are made."""
        from ostruct.cli.template_env import create_jinja_env
        from ostruct.cli.template_filters import XMLAppendixBuilder

        # Mock FileInfo
        class MockFileInfo:
            def __init__(
                self, path, content, parent_alias=None, attachment_type="file"
            ):
                self.path = path
                self.content = content
                self.parent_alias = parent_alias
                self.relative_path = os.path.basename(path)
                self.base_path = os.path.dirname(path)
                self.from_collection = False
                self.attachment_type = attachment_type
                self.name = os.path.basename(path)

        # Create test files
        files = [
            MockFileInfo("config.yaml", "debug: true", parent_alias="config")
        ]

        # Create environment and render template without file_ref
        env, alias_manager = create_jinja_env(files=files)

        template_str = "This template doesn't reference any files."
        template = env.from_string(template_str)
        template.render()  # Render but don't store result

        # Generate appendix
        builder = XMLAppendixBuilder(alias_manager)
        appendix = builder.build_appendix()

        # Should be empty since no references were made
        assert appendix == ""


class TestTSESErrorHandling:
    """Test TSES error handling in CLI integration."""

    def test_unknown_alias_error_in_template(self):
        """Test error handling for unknown alias in template."""
        from ostruct.cli.template_env import create_jinja_env
        from ostruct.cli.template_filters import TemplateStructureError

        # Create environment with no files - should still return tuple with empty alias manager
        env, alias_manager = create_jinja_env(files=[])

        template_str = "Reference: {{ file_ref('missing_alias') }}"
        template = env.from_string(template_str)

        # Should raise TemplateStructureError
        with pytest.raises(TemplateStructureError) as exc_info:
            template.render()

        error = exc_info.value
        assert "Unknown alias 'missing_alias'" in str(error)
        assert "Available aliases:" in error.suggestions[0]

    def test_tses_not_initialized_error(self):
        """Test error when file references are not initialized."""
        import ostruct.cli.template_filters as tf
        from ostruct.cli.template_filters import (
            TemplateStructureError,
            file_ref,
        )

        # Clear global alias manager
        original_manager = getattr(tf, "_alias_manager", None)
        tf._alias_manager = None

        try:
            with pytest.raises(TemplateStructureError) as exc_info:
                file_ref("any_alias")

            error = exc_info.value
            assert "File references not initialized" in str(error)
            assert "Check template processing pipeline" in error.suggestions[0]
        finally:
            # Restore original manager
            tf._alias_manager = original_manager

    def test_file_reference_error_suggestions(self):
        """Test that file reference errors include helpful suggestions."""
        with pytest.raises(TemplateStructureError) as exc_info:
            file_ref("nonexistent")

        error = exc_info.value
        assert "Unknown alias 'nonexistent'" in str(error)
        assert "Available aliases: none" in error.suggestions[0]


class TestTSESEndToEnd:
    """End-to-end tests for TSES functionality."""

    def test_complete_tses_workflow(self):
        """Test complete TSES workflow from files to appendix."""
        from ostruct.cli.template_env import create_jinja_env
        from ostruct.cli.template_filters import XMLAppendixBuilder

        # Mock FileInfo objects representing real CLI attachments
        class MockFileInfo:
            def __init__(
                self,
                path,
                content,
                parent_alias=None,
                relative_path=None,
                base_path=None,
                from_collection=False,
                attachment_type="file",
            ):
                self.path = path
                self.content = content
                self.parent_alias = parent_alias
                self.relative_path = relative_path or os.path.basename(path)
                self.base_path = base_path or os.path.dirname(path)
                self.from_collection = from_collection
                self.attachment_type = attachment_type
                self.name = os.path.basename(path)

        # Simulate files from different attachment types
        files = [
            # Single file: --file config config.yaml
            MockFileInfo(
                "config.yaml",
                "debug: true\nmode: production",
                parent_alias="config",
                relative_path="config.yaml",
                base_path="/project",
                attachment_type="file",  # From --file
            ),
            # Directory: --dir source src/
            MockFileInfo(
                "src/main.py",
                "def main():\n    print('Hello')",
                parent_alias="source",
                relative_path="main.py",
                base_path="/project/src",
                attachment_type="dir",  # From --dir
            ),
            MockFileInfo(
                "src/utils.py",
                "def helper():\n    return 42",
                parent_alias="source",
                relative_path="utils.py",
                base_path="/project/src",
                attachment_type="dir",  # From --dir
            ),
            # Collection: --collect data @files.txt
            MockFileInfo(
                "data1.csv",
                "name,value\ntest,123",
                parent_alias="data",
                relative_path="data1.csv",
                from_collection=True,
                attachment_type="collection",  # From --collect
            ),
            MockFileInfo(
                "data2.json",
                '{"key": "value"}',
                parent_alias="data",
                relative_path="data2.json",
                from_collection=True,
                attachment_type="collection",  # From --collect
            ),
        ]

        # Step 1: Create environment with file reference support
        env, alias_manager = create_jinja_env(files=files)

        # Step 2: Render template with file references
        template_str = """
# Security Audit Report

## Configuration Analysis
Review the configuration in {{ file_ref("config") }}.

## Source Code Review
Analyze the source code in {{ file_ref("source") }}.

## Data Analysis
Check the data files in {{ file_ref("data") }}.
        """.strip()

        template = env.from_string(template_str)
        rendered = template.render()

        # Step 3: Generate XML appendix
        builder = XMLAppendixBuilder(alias_manager)
        appendix = builder.build_appendix()

        # Step 4: Combine output
        complete_output = rendered + "\n\n" + appendix

        # Verify the complete workflow
        # Check template rendering
        assert "Review the configuration in <config>." in complete_output
        assert "Analyze the source code in <source>." in complete_output
        assert "Check the data files in <data>." in complete_output

        # Check XML appendix structure
        assert "<files>" in complete_output

        # Single file
        assert '<file alias="config" path="/project">' in complete_output
        assert "debug: true\nmode: production" in complete_output

        # Directory
        assert '<dir alias="source" path="/project/src">' in complete_output
        assert '<file path="main.py">' in complete_output
        assert '<file path="utils.py">' in complete_output
        assert "def main():" in complete_output
        assert "def helper():" in complete_output

        # Collection
        assert '<collection alias="data"' in complete_output
        assert '<file path="data1.csv">' in complete_output
        assert '<file path="data2.json">' in complete_output
        assert "name,value\ntest,123" in complete_output
        assert '{"key": "value"}' in complete_output

        assert "</files>" in complete_output

        # Verify all aliases were referenced
        assert len(alias_manager.referenced) == 3
        assert "config" in alias_manager.referenced
        assert "source" in alias_manager.referenced
        assert "data" in alias_manager.referenced
