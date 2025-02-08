"""Tests for internal security primitives.

These tests verify the behavior of internal security functions that are not
part of the public API. They focus on security error classification and
internal error handling.
"""

import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.security import PathSecurityError, SecurityErrorReasons
from ostruct.cli.security.symlink_resolver import _resolve_symlink


def test_internal_broken_symlink(fs: FakeFilesystem) -> None:
    """Verify internal API properly classifies broken symlinks."""
    fs.create_symlink("/test/link.txt", "/test/nonexistent.txt")

    with pytest.raises(PathSecurityError) as exc_info:
        _resolve_symlink(
            Path("/test/link.txt"), max_depth=16, allowed_dirs=[Path("/test")]
        )
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.SYMLINK_BROKEN
    )
    assert "/test/nonexistent.txt" in str(exc_info.value)


def test_internal_symlink_loop(fs: FakeFilesystem) -> None:
    """Verify internal API detects loops before checking existence."""
    fs.create_symlink("/test/link1.txt", "/test/link2.txt")
    fs.create_symlink("/test/link2.txt", "/test/link1.txt")

    with pytest.raises(PathSecurityError) as exc_info:
        _resolve_symlink(
            Path("/test/link1.txt"), max_depth=16, allowed_dirs=[Path("/test")]
        )
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.SYMLINK_LOOP
    )
    assert len(exc_info.value.context["chain"]) > 0


def test_internal_max_depth(fs: FakeFilesystem) -> None:
    """Verify internal API enforces maximum depth."""
    fs.create_file("/test/target.txt", contents="test")
    fs.create_symlink("/test/link1.txt", "/test/target.txt")
    fs.create_symlink("/test/link2.txt", "/test/link1.txt")

    with pytest.raises(PathSecurityError) as exc_info:
        _resolve_symlink(
            Path("/test/link2.txt"), max_depth=1, allowed_dirs=[Path("/test")]
        )
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_MAX_DEPTH
    )
    assert exc_info.value.context["depth"] == 1


def test_internal_target_not_allowed(fs: FakeFilesystem) -> None:
    """Verify internal API enforces allowed directory restrictions."""
    fs.create_file("/outside/target.txt", contents="test")
    fs.create_symlink("/test/link.txt", "/outside/target.txt")

    with pytest.raises(PathSecurityError) as exc_info:
        _resolve_symlink(
            Path("/test/link.txt"), max_depth=16, allowed_dirs=[Path("/test")]
        )
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )
