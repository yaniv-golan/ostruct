"""Test suite for attachment processor functionality."""

import tempfile
from pathlib import Path

from ostruct.cli.attachment_processor import (
    AttachmentProcessor,
    AttachmentSpec,
    process_new_attachments,
)
from ostruct.cli.security import PathSecurity, SecurityManager


def test_attachment_spec_creation():
    """Test AttachmentSpec creation and attributes."""
    spec = AttachmentSpec(
        alias="test_data",
        path="/tmp/test.txt",
        targets={"prompt", "code-interpreter"},
        recursive=False,
        pattern=None,
    )

    assert spec.alias == "test_data"
    assert spec.path == "/tmp/test.txt"
    assert spec.targets == {"prompt", "code-interpreter"}
    assert spec.recursive is False
    assert spec.pattern is None


def test_attachment_processor_basic():
    """Test basic attachment processing functionality."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        processor = AttachmentProcessor(manager)

        # Test processing single attachment
        attachments = [
            {
                "alias": "data",
                "path": str(test_file),
                "targets": ["prompt"],
                "recursive": False,
                "pattern": None,
            }
        ]

        processed = processor.process_attachments(attachments)

        # Verify results
        assert len(processed.template_files) == 1
        assert processed.template_files[0].alias == "data"
        assert "data" in processed.alias_map
        assert len(processed.ci_files) == 0
        assert len(processed.fs_files) == 0


def test_attachment_processor_multi_target():
    """Test attachment with multiple targets."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        processor = AttachmentProcessor(manager)

        # Test processing attachment with multiple targets
        attachments = [
            {
                "alias": "data",
                "path": str(test_file),
                "targets": ["prompt", "code-interpreter"],
                "recursive": False,
                "pattern": None,
            }
        ]

        processed = processor.process_attachments(attachments)

        # Verify it appears in both target collections
        assert len(processed.template_files) == 1
        assert len(processed.ci_files) == 1
        assert processed.template_files[0].alias == "data"
        assert processed.ci_files[0].alias == "data"


def test_attachment_processor_directory():
    """Test directory attachment processing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test directory
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        processor = AttachmentProcessor(manager)

        # Test processing directory attachment
        attachments = [
            {
                "alias": "docs",
                "path": str(test_dir),
                "targets": ["file-search"],
                "recursive": True,
                "pattern": "*.txt",
            }
        ]

        processed = processor.process_attachments(attachments)

        # Verify directory routing
        assert len(processed.fs_dirs) == 1
        assert processed.fs_dirs[0].alias == "docs"
        assert processed.fs_dirs[0].recursive is True
        assert processed.fs_dirs[0].pattern == "*.txt"


def test_convert_to_explicit_routing():
    """Test conversion to legacy ExplicitRouting format."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        dir1 = tmp_path / "dir1"
        file1.write_text("content1")
        file2.write_text("content2")
        dir1.mkdir()

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        processor = AttachmentProcessor(manager)

        # Process multiple attachments
        attachments = [
            {
                "alias": "data1",
                "path": str(file1),
                "targets": ["prompt"],
                "recursive": False,
                "pattern": None,
            },
            {
                "alias": "data2",
                "path": str(file2),
                "targets": ["code-interpreter"],
                "recursive": False,
                "pattern": None,
            },
            {
                "alias": "docs",
                "path": str(dir1),
                "targets": ["file-search"],
                "recursive": True,
                "pattern": None,
            },
        ]

        processed = processor.process_attachments(attachments)
        routing = processor.convert_to_explicit_routing(processed)

        # Verify conversion (paths will be resolved by security manager)
        assert len(routing.template_files) == 1
        assert (
            file1.name in routing.template_files[0]
        )  # Check filename is in path
        assert len(routing.code_interpreter_files) == 1
        assert (
            file2.name in routing.code_interpreter_files[0]
        )  # Check filename is in path
        assert len(routing.file_search_dirs) == 1
        assert (
            dir1.name in routing.file_search_dirs[0]
        )  # Check dirname is in path
        # Check alias mapping exists
        assert len(routing.file_search_dir_aliases) == 1
        assert routing.file_search_dir_aliases[0][0] == "docs"


def test_process_new_attachments_integration():
    """Test integration function for processing new attachments."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        # Test with new attachment syntax
        args = {
            "attaches": [
                {
                    "alias": "data",
                    "path": str(test_file),
                    "targets": ["prompt"],
                    "recursive": False,
                    "pattern": None,
                }
            ]
        }

        result = process_new_attachments(args, manager)

        # Verify result (paths will be resolved by security manager)
        assert result is not None
        assert "template" in result.enabled_tools
        assert len(result.validated_files["template"]) == 1
        assert (
            test_file.name in result.validated_files["template"][0]
        )  # Check filename is in path


def test_process_new_attachments_no_syntax():
    """Test that function returns None when no new syntax is present."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        # Test with no new attachment syntax
        args = {"legacy_files": ["file1.txt"]}

        result = process_new_attachments(args, manager)

        # Should return None for legacy syntax
        assert result is None
