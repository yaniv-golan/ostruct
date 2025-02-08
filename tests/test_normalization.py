"""Tests for path normalization functionality."""

import os
import unicodedata
from pathlib import Path

import pytest

from ostruct.cli.security import (
    PathSecurityError,
    SecurityErrorReasons,
    normalize_path,
)


def test_normalize_path_basic():
    """Test basic path normalization."""
    # Test with string input
    assert normalize_path("/test/path") == Path("/test/path")

    # Test with Path input
    assert normalize_path(Path("/test/path")) == Path("/test/path")


def test_normalize_path_unicode():
    """Test Unicode normalization."""
    # Test with decomposed form
    decomposed = "/test/pa\u0301th"  # á as 'a' + combining acute accent
    composed = "/test/páth"  # á as single character
    assert normalize_path(decomposed) == normalize_path(composed)


def test_normalize_path_unsafe_unicode():
    """Test detection of unsafe Unicode characters."""
    # Test with control characters
    with pytest.raises(PathSecurityError) as exc_info:
        normalize_path("/test/\x00path")
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.UNSAFE_UNICODE
    )

    # Test with line separators
    with pytest.raises(PathSecurityError) as exc_info:
        normalize_path("/test/\u2028path")
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.UNSAFE_UNICODE
    )


def test_normalize_path_directory_traversal():
    """Test detection of directory traversal attempts."""
    # Test with double dots
    with pytest.raises(PathSecurityError) as exc_info:
        normalize_path("/test/../etc/passwd")
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.PATH_TRAVERSAL
    )

    # Test with multiple slashes - should normalize them
    result = normalize_path("/test//file.txt")
    assert str(result) == os.path.normpath("/test/file.txt")


def test_normalize_path_relative():
    """Test normalization of relative paths."""
    # Test with relative path
    result = normalize_path("test/path")
    assert result.is_absolute()
    assert str(result).endswith("/test/path")


def test_normalize_path_alternative_separators():
    """Test handling of alternative path separators."""
    # Test with alternative separators - should normalize them
    result = normalize_path("/test\\file.txt")
    assert str(result) == os.path.normpath("/test/file.txt")

    # Test with mixed separators
    result = normalize_path("/test\\subdir/file.txt")
    assert str(result) == os.path.normpath("/test/subdir/file.txt")
