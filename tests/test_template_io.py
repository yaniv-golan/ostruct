"""Test template I/O functionality."""

import logging
import os
from typing import Dict, List, Union

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.file_info import FileInfo
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_io import extract_template_metadata, read_file

# Set up logging for tests
logger = logging.getLogger("ostruct.cli")
logger.setLevel(logging.DEBUG)

# Add console handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@pytest.fixture
def security_manager(fs: FakeFilesystem) -> SecurityManager:
    """Create a security manager for testing."""
    return SecurityManager(base_dir="/test_workspace/base")


def test_read_file_basic(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test basic file reading functionality."""
    # Create a test file in the fake filesystem
    fs.makedirs("/test_workspace/base", exist_ok=True)
    test_file = "/test_workspace/base/test_file.txt"
    fs.create_file(test_file, contents="test content")

    # Read the file
    file_info = read_file(test_file, security_manager=security_manager)

    # Verify the content was read correctly
    assert file_info.content == "test content"
    assert file_info.path == "test_file.txt"  # Path relative to base_dir
    assert file_info.exists
    assert not file_info.is_binary


def test_read_file_with_encoding(
    security_manager: SecurityManager, fs: FakeFilesystem
) -> None:
    """Test file reading with specific encoding."""
    content = "test content with unicode: 🚀"
    fs.makedirs("/test_workspace/base", exist_ok=True)
    test_file = "/test_workspace/base/test_file.txt"
    fs.create_file(test_file, contents=content)

    # Read with UTF-8 encoding
    file_info = read_file(
        test_file, encoding="utf-8", security_manager=security_manager
    )

    # Verify content and encoding
    assert file_info.content == content
    assert file_info.encoding == "utf-8"
    assert file_info.exists
    assert file_info.size == len(content.encode("utf-8"))  # Size in bytes


def test_read_file_content_loading(
    security_manager: SecurityManager, fs: FakeFilesystem
) -> None:
    """Test immediate content loading behavior."""
    # Create a test file in the fake filesystem
    fs.makedirs("/test_workspace/base", exist_ok=True)
    test_file = "/test_workspace/base/test_file.txt"
    test_content = "test content"
    fs.create_file(test_file, contents=test_content)

    # Create FileInfo - content should be loaded immediately
    file_info = read_file(test_file, security_manager=security_manager)

    # Check that content was loaded
    assert file_info.content == test_content
    assert file_info.exists
    assert file_info.size == len(test_content)
    assert str(file_info.abs_path) == test_file

    # Verify metadata
    metadata = file_info.to_dict()
    assert metadata["path"] == "test_file.txt"  # Path relative to base_dir
    assert metadata["abs_path"] == test_file  # Absolute path preserved


def test_read_file_not_found(security_manager: SecurityManager) -> None:
    """Test error handling for non-existent files."""
    with pytest.raises(ValueError) as exc:
        read_file(
            "/test_workspace/base/nonexistent_file.txt",
            security_manager=security_manager,
        )
    assert "File not found" in str(exc.value)


def test_read_file_caching(
    security_manager: SecurityManager, fs: FakeFilesystem
) -> None:
    """Test file content caching."""
    logger.info("Starting file caching test")

    # Create test file
    fs.makedirs("/test_workspace/base", exist_ok=True)
    test_file = "/test_workspace/base/test_file.txt"
    test_content = "test content"
    fs.create_file(test_file, contents=test_content)

    # First read should cache the file
    initial_stats = os.stat(test_file)
    logger.debug(
        "Initial file stats: size=%d, mtime_ns=%d",
        initial_stats.st_size,
        initial_stats.st_mtime_ns,
    )

    file_info1 = read_file(test_file, security_manager=security_manager)
    assert file_info1.content == test_content
    assert file_info1.exists
    assert file_info1.size == len(test_content)

    # Modify file
    new_content = "modified content"
    fs.remove(test_file)  # Remove the file first
    fs.create_file(test_file, contents=new_content)  # Create with new content

    # Second read should detect the change and reload
    file_info2 = read_file(test_file, security_manager=security_manager)
    assert file_info2.content == new_content  # Content should be updated
    assert file_info2.exists
    assert file_info2.size == len(new_content)

    # Verify that the files are different
    assert file_info1.content != file_info2.content
    assert file_info1.size != file_info2.size
    assert file_info1.hash != file_info2.hash


def test_extract_metadata(
    security_manager: SecurityManager, fs: FakeFilesystem
) -> None:
    """Test metadata extraction from FileInfo."""
    fs.makedirs("/test_workspace/base", exist_ok=True)
    test_file = "/test_workspace/base/test_file.txt"
    test_content = "test content"
    fs.create_file(test_file, contents=test_content)

    file_info = read_file(test_file, security_manager=security_manager)

    # Extract metadata
    metadata = file_info.to_dict()

    # Verify basic metadata
    assert metadata["path"] == "test_file.txt"  # Path relative to base_dir
    assert metadata["abs_path"] == test_file  # Absolute path preserved
    assert metadata["exists"] is True
    assert metadata["size"] == len(test_content)
    assert metadata["content"] == test_content

    # Verify timestamps
    assert isinstance(metadata["mtime"], float)
    assert isinstance(metadata["mtime_ns"], int)
    assert metadata["mode"] is not None


def test_extract_template_metadata(
    security_manager: SecurityManager, fs: FakeFilesystem
) -> None:
    """Test metadata extraction from template and context."""
    # Create test file
    fs.makedirs("/test_workspace/base", exist_ok=True)
    test_file = "/test_workspace/base/test_file.txt"
    test_content = "test content"
    fs.create_file(test_file, contents=test_content)

    # Create template context
    template_str = "/test_workspace/base/template.j2"
    context: Dict[str, Union[FileInfo, Dict[str, str], List[str], str]] = {
        "file": read_file(test_file, security_manager=security_manager),
        "config": {"key": "value"},
        "items": ["item1", "item2"],
        "name": "test",
    }

    # Extract metadata
    metadata = extract_template_metadata(template_str, context)

    # Verify metadata
    assert metadata["template"] == {"is_file": True, "path": template_str}
    assert "context" in metadata
    assert sorted(metadata["context"]["variables"]) == [
        "config",
        "file",
        "items",
        "name",
    ]
    assert metadata["context"]["dict_vars"] == ["config"]
    assert metadata["context"]["list_vars"] == ["items"]
    assert metadata["context"]["file_info_vars"] == ["file"]
    assert metadata["context"]["other_vars"] == ["name"]
