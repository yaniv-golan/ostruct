"""Tests for template I/O operations."""

import logging
import os
import tempfile
import time
from typing import Dict, List, Union

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.file_info import FileInfo
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_io import (
    extract_metadata,
    extract_template_metadata,
    read_file,
)

# Set up logging for tests
logger = logging.getLogger("openai_structured.cli")
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


@pytest.fixture  # type: ignore[misc]
def security_manager() -> SecurityManager:
    """Create a security manager for testing."""
    manager = SecurityManager(base_dir=os.getcwd())
    manager.add_allowed_dir(tempfile.gettempdir())
    return manager


def test_read_file_basic(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test basic file reading."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        f.flush()
        file_path = f.name
    try:
        # Read file
        file_info = read_file(file_path, security_manager=security_manager)
        # Verify content
        assert file_info.content == "test content"
        assert file_info.encoding is not None
        assert file_info.hash is not None
    finally:
        os.unlink(file_path)


def test_read_file_with_encoding(security_manager: SecurityManager) -> None:
    """Test file reading with specific encoding."""
    content = "test content with unicode: 🚀"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(content)
        f.flush()
        file_path = f.name
    try:
        file_info = read_file(
            file_path, encoding="utf-8", security_manager=security_manager
        )
        assert file_info.content == content
        assert file_info.encoding == "utf-8"
    finally:
        os.unlink(file_path)


def test_read_file_content_loading(security_manager: SecurityManager) -> None:
    """Test immediate content loading behavior."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        f.flush()
        file_path = f.name
    try:
        # Create FileInfo - content should be loaded immediately
        file_info = read_file(file_path, security_manager=security_manager)
        # Content should be available immediately
        assert file_info.content == "test content"
        # Internal state should show content is loaded
        assert getattr(file_info, "_FileInfo__content") == "test content"
    finally:
        os.unlink(file_path)


def test_read_file_not_found(security_manager: SecurityManager) -> None:
    """Test error handling for non-existent files."""
    with pytest.raises(ValueError) as exc:
        read_file("nonexistent_file.txt", security_manager=security_manager)
    assert "File not found" in str(exc.value)


def test_read_file_caching(security_manager: SecurityManager) -> None:
    """Test file content caching."""
    logger.info("Starting file caching test")

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        f.flush()
        os.fsync(f.fileno())  # Force flush to disk
        file_path = f.name
        logger.debug("Created test file: %s", file_path)

    try:
        # First read should cache the file
        initial_stats = os.stat(file_path)
        logger.debug(
            "Initial file stats: size=%d, mtime_ns=%d",
            initial_stats.st_size,
            initial_stats.st_mtime_ns,
        )

        file_info1 = read_file(file_path, security_manager=security_manager)
        initial_content = file_info1.content
        logger.debug("First read complete: content=%r", initial_content)

        # Second read should use cached content
        file_info2 = read_file(file_path, security_manager=security_manager)
        assert file_info2.content == initial_content
        logger.debug("Second read verified from cache")

        # Modify file
        logger.debug("Modifying file content")
        with open(file_path, "w") as f:
            f.write("new content")
            f.flush()
            os.fsync(f.fileno())  # Force flush to disk

        # Wait until file stats actually change
        max_retries = 20  # Increased for CI environments
        for retry in range(max_retries):
            current_stats = os.stat(file_path)
            logger.debug(
                "Retry %d/%d - Current stats: mtime_ns=%d, size=%d",
                retry + 1,
                max_retries,
                current_stats.st_mtime_ns,
                current_stats.st_size,
            )

            if (
                current_stats.st_mtime_ns != initial_stats.st_mtime_ns
                or current_stats.st_size != initial_stats.st_size
            ):
                logger.info(
                    "File stats changed after %d retries: mtime_ns_diff=%d, size_diff=%d",
                    retry + 1,
                    current_stats.st_mtime_ns - initial_stats.st_mtime_ns,
                    current_stats.st_size - initial_stats.st_size,
                )
                break
            time.sleep(0.1)
            if retry == max_retries - 1:
                raise RuntimeError(
                    f"File stats did not update after {max_retries} retries. "
                    f"Initial: mtime_ns={initial_stats.st_mtime_ns}, size={initial_stats.st_size}. "
                    f"Current: mtime_ns={current_stats.st_mtime_ns}, size={current_stats.st_size}"
                )

        # Third read should detect file change and update cache
        logger.debug("Attempting third read after modification")
        file_info3 = read_file(file_path, security_manager=security_manager)
        assert file_info3.content == "new content", (
            f"File content not updated. Stats: initial_mtime_ns={initial_stats.st_mtime_ns}, "
            f"current_mtime_ns={current_stats.st_mtime_ns}, "
            f"size_diff={current_stats.st_size - initial_stats.st_size}"
        )
        logger.info("Cache test completed successfully")
    finally:
        os.unlink(file_path)
        logger.debug("Test file cleaned up: %s", file_path)


def test_extract_metadata(security_manager: SecurityManager) -> None:
    """Test metadata extraction from FileInfo."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        f.flush()
        file_path = f.name

    try:
        file_info = read_file(file_path, security_manager=security_manager)
        metadata = extract_metadata(file_info)

        # Test basic metadata
        assert metadata["name"] == os.path.basename(file_path)
        assert metadata["path"] == file_path
        assert metadata["abs_path"] == os.path.realpath(file_path)
        assert isinstance(metadata["mtime"], float)

        # Test optional metadata
        assert "encoding" not in metadata
        assert "mime_type" not in metadata
    finally:
        os.unlink(file_path)


def test_extract_template_metadata(security_manager: SecurityManager) -> None:
    """Test metadata extraction from template and context."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        f.flush()
        file_path = f.name

    try:
        template_str = "template.j2"
        context: Dict[str, Union[FileInfo, Dict[str, str], List[str], str]] = {
            "file": read_file(file_path, security_manager=security_manager),
            "config": {"key": "value"},
            "items": ["item1", "item2"],
            "name": "test",
        }

        metadata = extract_template_metadata(template_str, context)

        # Test template metadata
        assert metadata["template"]["path"] == "template.j2"

        # Test context metadata
        assert metadata["context"]["file_info_vars"] == ["file"]
        assert metadata["context"]["dict_vars"] == ["config"]
        assert metadata["context"]["list_vars"] == ["items"]
    finally:
        os.unlink(file_path)
