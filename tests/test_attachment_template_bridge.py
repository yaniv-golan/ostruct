"""Test attachment template bridge functionality."""

import tempfile
from pathlib import Path

import pytest
from ostruct.cli.attachment_processor import (
    AttachmentSpec,
    ProcessedAttachments,
)
from ostruct.cli.attachment_template_bridge import (
    AttachmentTemplateContext,
    LazyFileContent,
    build_template_context_from_attachments,
)
from ostruct.cli.file_info import FileInfo, FileRoutingIntent
from ostruct.cli.security import SecurityManager


@pytest.fixture
def security_manager():
    """Create security manager for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Resolve symlinks to ensure consistent path resolution
        resolved_tmp_dir = Path(tmp_dir).resolve()
        yield SecurityManager(resolved_tmp_dir)


@pytest.fixture
def test_files(security_manager):
    """Create test files for attachment processing."""
    base_path = Path(security_manager.base_dir)

    # Create test files
    test_file = base_path / "test.txt"
    test_file.write_text("Test file content")

    large_file = base_path / "large.txt"
    large_file.write_text("x" * 100000)  # 100KB file

    # Create test directory with files
    test_dir = base_path / "testdir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("File 1 content")
    (test_dir / "file2.txt").write_text("File 2 content")
    (test_dir / "nested.md").write_text("# Nested markdown")

    return {
        "test_file": test_file,
        "large_file": large_file,
        "test_dir": test_dir,
    }


def test_lazy_file_content_basic(security_manager, test_files):
    """Test basic lazy file content functionality."""
    file_info = FileInfo.from_path(
        str(test_files["test_file"]),
        security_manager,
        routing_type="template",
        routing_intent=FileRoutingIntent.TEMPLATE_ONLY,
    )

    lazy_content = LazyFileContent(file_info)

    # Content should not be loaded initially
    assert not lazy_content._loaded

    # Access content should trigger loading
    content = str(lazy_content)
    assert content == "Test file content"
    assert lazy_content._loaded


def test_lazy_file_content_size_check(security_manager, test_files):
    """Test size checking functionality."""
    file_info = FileInfo.from_path(
        str(test_files["large_file"]),
        security_manager,
        routing_type="template",
        routing_intent=FileRoutingIntent.TEMPLATE_ONLY,
    )

    # Small size limit should fail
    lazy_content = LazyFileContent(file_info, max_size=1000)
    assert not lazy_content.check_size()

    # Large size limit should pass
    lazy_content = LazyFileContent(file_info, max_size=200000)
    assert lazy_content.check_size()


def test_lazy_file_content_size_limit_handling(security_manager, test_files):
    """Test that large files are handled gracefully."""
    file_info = FileInfo.from_path(
        str(test_files["large_file"]),
        security_manager,
        routing_type="template",
        routing_intent=FileRoutingIntent.TEMPLATE_ONLY,
    )

    lazy_content = LazyFileContent(file_info, max_size=1000)
    content = str(lazy_content)

    assert "File too large" in content
    assert "100,000 bytes > 1,000 bytes" in content


def test_attachment_template_context_single_file(security_manager, test_files):
    """Test template context creation for single file attachment."""
    processed_attachments = ProcessedAttachments()

    # Add a template file attachment
    spec = AttachmentSpec(
        alias="data", path=test_files["test_file"], targets={"prompt"}
    )
    processed_attachments.template_files.append(spec)
    processed_attachments.alias_map["data"] = spec

    context_builder = AttachmentTemplateContext(security_manager)
    context = context_builder.build_template_context(processed_attachments)

    # Check that alias variable exists and is LazyFileContent
    assert "data" in context
    assert isinstance(context["data"], LazyFileContent)

    # Check content can be accessed
    assert str(context["data"]) == "Test file content"

    # Check utility variables (preserved from template engine)
    assert "files" in context
    assert "file_count" in context
    assert context["file_count"] == 1
    assert context["has_files"] is True

    # Verify no legacy auto-generated variable names (breaking change)
    assert (
        "test_txt" not in context
    )  # Would be auto-generated in legacy system


def test_attachment_template_context_directory(security_manager, test_files):
    """Test template context creation for directory attachment."""
    processed_attachments = ProcessedAttachments()

    # Add a template directory attachment
    spec = AttachmentSpec(
        alias="docs",
        path=test_files["test_dir"],
        targets={"prompt"},
        recursive=False,
        pattern="*.txt",
    )
    processed_attachments.template_dirs.append(spec)
    processed_attachments.alias_map["docs"] = spec

    context_builder = AttachmentTemplateContext(security_manager)
    context = context_builder.build_template_context(processed_attachments)

    # Check that alias variable exists and is FileInfoList
    assert "docs" in context
    from ostruct.cli.file_list import FileInfoList

    assert isinstance(context["docs"], FileInfoList)

    # Should have 2 .txt files (file1.txt and file2.txt)
    assert len(context["docs"]) == 2

    # Check utility variables
    assert context["file_count"] >= 2  # At least the directory files


def test_attachment_template_context_multi_target(
    security_manager, test_files
):
    """Test template context with multi-target attachments."""
    processed_attachments = ProcessedAttachments()

    # Add attachment that targets both prompt and code-interpreter
    spec = AttachmentSpec(
        alias="shared_data",
        path=test_files["test_file"],
        targets={"prompt", "code-interpreter"},
    )
    processed_attachments.template_files.append(spec)
    processed_attachments.ci_files.append(spec)
    processed_attachments.alias_map["shared_data"] = spec

    context_builder = AttachmentTemplateContext(security_manager)
    context = context_builder.build_template_context(processed_attachments)

    # Check that alias variable exists
    assert "shared_data" in context
    assert str(context["shared_data"]) == "Test file content"

    # Check attachment metadata
    assert context["_attachments"]["template_file_count"] == 1
    assert context["_attachments"]["ci_file_count"] == 1


def test_build_template_context_from_attachments_integration(
    security_manager, test_files
):
    """Test full integration through main entry point."""
    processed_attachments = ProcessedAttachments()

    # Add multiple attachments
    file_spec = AttachmentSpec(
        alias="config", path=test_files["test_file"], targets={"prompt"}
    )
    dir_spec = AttachmentSpec(
        alias="source",
        path=test_files["test_dir"],
        targets={"prompt", "file-search"},
        recursive=True,
    )

    processed_attachments.template_files.append(file_spec)
    processed_attachments.template_dirs.append(dir_spec)
    processed_attachments.fs_dirs.append(dir_spec)
    processed_attachments.alias_map["config"] = file_spec
    processed_attachments.alias_map["source"] = dir_spec

    base_context = {"custom_var": "custom_value"}

    context = build_template_context_from_attachments(
        processed_attachments, security_manager, base_context
    )

    # Check base context is preserved
    assert context["custom_var"] == "custom_value"

    # Check attachment variables exist
    assert "config" in context
    assert "source" in context

    # Check utility variables
    assert "files" in context
    assert "file_count" in context
    assert "has_files" in context
    assert "_attachments" in context

    # Check content access works
    assert str(context["config"]) == "Test file content"
