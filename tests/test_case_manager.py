"""Tests for case management functionality."""

import threading
from pathlib import Path

import pytest
from ostruct.cli.security import CaseManager


def test_case_manager_basic() -> None:
    """Test basic case management functionality."""
    # Set original case
    CaseManager.set_original_case(Path("/tmp/file.txt"), "/TMP/File.txt")

    # Get original case
    result = CaseManager.get_original_case(Path("/tmp/file.txt"))
    assert result == "/TMP/File.txt"

    # Clear case mappings
    CaseManager.clear()
    result = CaseManager.get_original_case(Path("/tmp/file.txt"))
    assert result == str(Path("/tmp/file.txt"))


def test_case_manager_missing_path() -> None:
    """Test behavior with missing paths."""
    # Get case for unmapped path
    result = CaseManager.get_original_case(Path("/unknown/path.txt"))
    assert result == str(Path("/unknown/path.txt"))


def test_case_manager_thread_safety() -> None:
    """Test thread safety of case management."""

    def worker(path: Path, original: str) -> None:
        """Worker function for thread testing."""
        CaseManager.set_original_case(path, original)
        assert CaseManager.get_original_case(path) == original

    # Create multiple threads
    threads = []
    for i in range(10):
        path = Path(f"/tmp/file{i}.txt")
        original = f"/TMP/File{i}.txt"
        thread = threading.Thread(target=worker, args=(path, original))
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify all mappings
    for i in range(10):
        path = Path(f"/tmp/file{i}.txt")
        expected = f"/TMP/File{i}.txt"
        assert CaseManager.get_original_case(path) == expected


def test_case_manager_overwrite() -> None:
    """Test overwriting existing case mappings."""
    path = Path("/tmp/file.txt")

    # Set initial case
    CaseManager.set_original_case(path, "/TMP/File.txt")
    assert CaseManager.get_original_case(path) == "/TMP/File.txt"

    # Overwrite case
    CaseManager.set_original_case(path, "/TMP/FILE.TXT")
    assert CaseManager.get_original_case(path) == "/TMP/FILE.TXT"


def test_case_manager_clear() -> None:
    """Test clearing case mappings."""
    # Set multiple mappings
    CaseManager.set_original_case(Path("/tmp/file1.txt"), "/TMP/File1.txt")
    CaseManager.set_original_case(Path("/tmp/file2.txt"), "/TMP/File2.txt")

    # Clear mappings
    CaseManager.clear()

    # Verify mappings are cleared
    assert CaseManager.get_original_case(Path("/tmp/file1.txt")) == str(
        Path("/tmp/file1.txt")
    )
    assert CaseManager.get_original_case(Path("/tmp/file2.txt")) == str(
        Path("/tmp/file2.txt")
    )


def test_case_manager_invalid_input() -> None:
    """Test handling of invalid input."""
    # Test with None path
    with pytest.raises(TypeError):
        CaseManager.set_original_case(Path(None), "/TMP/File.txt")  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        CaseManager.get_original_case(Path(None))  # type: ignore[arg-type]

    # Test with empty string case
    CaseManager.set_original_case(Path("/tmp/file.txt"), "")
    assert CaseManager.get_original_case(Path("/tmp/file.txt")) == ""
