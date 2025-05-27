"""Tests for correct classification of symlink-related security errors.

This test suite focuses specifically on verifying that different symlink
scenarios are correctly classified with the appropriate error types:
- SYMLINK_LOOP for any form of cyclic references
- SYMLINK_BROKEN for true broken links
- Proper error precedence when multiple conditions exist
"""

from pathlib import Path

import pytest
from ostruct.cli.security import PathSecurityError, SecurityErrorReasons
from ostruct.cli.security.symlink_resolver import (
    _resolve_symlink as resolve_symlink,
)
from pyfakefs.fake_filesystem import FakeFilesystem


def verify_error_type(
    path: Path, expected_error: str, fs: FakeFilesystem
) -> None:
    """Helper to verify the error type raised by resolve_symlink."""
    with pytest.raises(PathSecurityError) as exc_info:
        resolve_symlink(
            path, max_depth=16, allowed_dirs=[Path("/test_workspace/base")]
        )
    assert (
        exc_info.value.context["reason"] == expected_error
    ), f"Expected {expected_error}, got {exc_info.value.context['reason']}"


def test_direct_loop(fs: FakeFilesystem) -> None:
    """Test classification of direct symlink loops (A -> B -> A)."""
    # Create a simple loop
    fs.create_symlink(
        "/test_workspace/base/link1.txt", "/test_workspace/base/link2.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link1.txt"
    )

    verify_error_type(
        Path("/test_workspace/base/link1.txt"),
        SecurityErrorReasons.SYMLINK_LOOP,
        fs,
    )


def test_broken_symlink(fs: FakeFilesystem) -> None:
    """Test classification of truly broken symlinks."""
    # Create a symlink to nonexistent file
    fs.create_symlink(
        "/test_workspace/base/broken.txt",
        "/test_workspace/base/nonexistent.txt",
    )

    verify_error_type(
        Path("/test_workspace/base/broken.txt"),
        SecurityErrorReasons.SYMLINK_BROKEN,
        fs,
    )


def test_chain_to_loop(fs: FakeFilesystem) -> None:
    """Test classification of chains that eventually lead to a loop.

    Example: C -> B -> (A -> A) should be classified as a loop.
    """
    # Create a self-referential loop at the end
    fs.create_symlink(
        "/test_workspace/base/loop.txt", "/test_workspace/base/loop.txt"
    )
    # Create a chain leading to it
    fs.create_symlink(
        "/test_workspace/base/chain1.txt", "/test_workspace/base/loop.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/chain2.txt", "/test_workspace/base/chain1.txt"
    )

    verify_error_type(
        Path("/test_workspace/base/chain2.txt"),
        SecurityErrorReasons.SYMLINK_LOOP,
        fs,
    )


def test_chain_to_broken(fs: FakeFilesystem) -> None:
    """Test classification of chains that lead to a broken link.

    Example: C -> B -> A -> nonexistent should be classified as broken.
    """
    # Create chain ending in broken link
    fs.create_symlink(
        "/test_workspace/base/link1.txt",
        "/test_workspace/base/nonexistent.txt",
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link1.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link3.txt", "/test_workspace/base/link2.txt"
    )

    verify_error_type(
        Path("/test_workspace/base/link3.txt"),
        SecurityErrorReasons.SYMLINK_BROKEN,
        fs,
    )


def test_loop_with_valid_branch(fs: FakeFilesystem) -> None:
    """Test classification when a loop exists alongside valid paths.

    Example: A -> B -> A, but B also -> valid_file
    Should still be classified as a loop.
    """
    # Create a valid file
    fs.create_file("/test_workspace/base/real.txt", contents="real")
    # Create a loop
    fs.create_symlink(
        "/test_workspace/base/link1.txt", "/test_workspace/base/link2.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link1.txt"
    )
    # Create valid symlink from one of the loop members
    fs.create_symlink(
        "/test_workspace/base/valid.txt", "/test_workspace/base/real.txt"
    )

    verify_error_type(
        Path("/test_workspace/base/link1.txt"),
        SecurityErrorReasons.SYMLINK_LOOP,
        fs,
    )


def test_complex_loop(fs: FakeFilesystem) -> None:
    """Test classification of more complex loop patterns.

    Example: A -> B -> C -> D -> B (creates a loop in the middle)
    Should be classified as a loop.
    """
    # Create a complex loop pattern
    fs.create_symlink(
        "/test_workspace/base/link1.txt", "/test_workspace/base/link2.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link3.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link3.txt", "/test_workspace/base/link4.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link4.txt", "/test_workspace/base/link2.txt"
    )

    verify_error_type(
        Path("/test_workspace/base/link1.txt"),
        SecurityErrorReasons.SYMLINK_LOOP,
        fs,
    )


def test_nested_valid_symlinks(fs: FakeFilesystem) -> None:
    """Test that valid nested symlinks are not misclassified.

    This is a control test to ensure we don't over-eagerly classify
    as loops or broken links.
    """
    # Create a valid file and chain of symlinks to it
    fs.create_file("/test_workspace/base/real.txt", contents="real")
    fs.create_symlink(
        "/test_workspace/base/link1.txt", "/test_workspace/base/real.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link1.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link3.txt", "/test_workspace/base/link2.txt"
    )

    # Should not raise any error
    result = resolve_symlink(
        Path("/test_workspace/base/link3.txt"),
        max_depth=16,
        allowed_dirs=[Path("/test_workspace/base")],
    )
    assert result == Path("/test_workspace/base/real.txt").resolve()


def test_loop_precedence_over_broken(fs: FakeFilesystem) -> None:
    """Test that loop detection takes precedence over broken link detection.

    If a path is both part of a loop and would lead to a broken link,
    it should be classified as a loop.
    """
    # Create a loop where one link also points to nonexistent file
    fs.create_symlink(
        "/test_workspace/base/link1.txt", "/test_workspace/base/link2.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2.txt", "/test_workspace/base/link1.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/link2_to_nowhere.txt",
        "/test_workspace/base/nonexistent.txt",
    )

    verify_error_type(
        Path("/test_workspace/base/link1.txt"),
        SecurityErrorReasons.SYMLINK_LOOP,
        fs,
    )
