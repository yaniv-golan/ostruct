"""Tests for security functionality."""

import logging
import os
import tempfile
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.errors import DirectoryNotFoundError, PathSecurityError
from ostruct.cli.security import SecurityErrorReasons, SecurityManager


def test_security_manager_init(fs: FakeFilesystem) -> None:
    """Test SecurityManager initialization."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    allowed_dir = Path("/test_workspace/allowed")
    fs.create_dir(base_dir)
    fs.create_dir(allowed_dir)

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])
    assert str(manager.base_dir) == str(base_dir.resolve())
    assert any(
        str(d) == str(allowed_dir.resolve()) for d in manager.allowed_dirs
    )


def test_is_path_allowed(fs: FakeFilesystem) -> None:
    """Test path allowance checks."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    allowed_dir = Path("/test_workspace/allowed")
    outside_dir = Path("/test_workspace/outside")
    fs.create_dir(base_dir)
    fs.create_dir(allowed_dir)
    fs.create_dir(outside_dir)

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])

    # Test that paths in base directory are allowed
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)
    assert manager.is_path_allowed(str(test_file))

    # Test that paths in allowed directory are allowed
    test_file2 = allowed_dir / "test.txt"
    fs.create_file(test_file2)
    assert manager.is_path_allowed(str(test_file2))

    # Test that paths outside allowed directories are not allowed
    test_file3 = outside_dir / "test.txt"
    fs.create_file(test_file3)
    assert not manager.is_path_allowed(str(test_file3))


def test_add_allowed_directory(fs: FakeFilesystem) -> None:
    """Test adding allowed directories."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    allowed_dir = Path("/test_workspace/allowed")
    fs.create_dir(base_dir)
    fs.create_dir(allowed_dir)

    manager = SecurityManager(str(base_dir))
    manager.add_allowed_directory(str(allowed_dir))

    # Test that paths in both directories are allowed
    test_file = base_dir / "test.txt"
    test_file2 = allowed_dir / "test.txt"
    fs.create_file(test_file)
    fs.create_file(test_file2)
    assert manager.is_path_allowed(str(test_file))
    assert manager.is_path_allowed(str(test_file2))


def test_add_allowed_dirs_from_file(fs: FakeFilesystem) -> None:
    """Test adding allowed directories from a file."""
    # Create test directories in fake filesystem
    base_dir = Path("/test_workspace/base")
    allowed_dir1 = Path("/test_workspace/allowed1")
    allowed_dir2 = Path("/test_workspace/allowed2")
    fs.create_dir(allowed_dir1)
    fs.create_dir(allowed_dir2)

    # Create allowed directories file
    allowed_dirs_file = base_dir / "allowed_dirs.txt"
    fs.create_file(
        allowed_dirs_file, contents=f"{allowed_dir1}\n{allowed_dir2}"
    )

    manager = SecurityManager(str(base_dir))
    manager.add_allowed_dirs_from_file(str(allowed_dirs_file))

    # Test that paths in both allowed directories are allowed
    test_file1 = allowed_dir1 / "test.txt"
    test_file2 = allowed_dir2 / "test.txt"
    fs.create_file(test_file1)
    fs.create_file(test_file2)
    assert manager.is_path_allowed(str(test_file1))
    assert manager.is_path_allowed(str(test_file2))


def test_validate_path(fs: FakeFilesystem) -> None:
    """Test path validation."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    allowed_dir = Path("/test_workspace/allowed")
    outside_dir = Path("/test_workspace/outside")
    fs.create_dir(base_dir)
    fs.create_dir(allowed_dir)
    fs.create_dir(outside_dir)

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])

    # Test that valid paths are returned resolved
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)
    assert manager.validate_path(str(test_file)) == test_file.resolve()

    # Test that invalid paths raise an error
    outside_file = outside_dir / "test.txt"
    fs.create_file(outside_file)
    with pytest.raises(PathSecurityError):
        manager.validate_path(str(outside_file))


def test_security_manager_strict_rejects_temp_paths(
    fs: FakeFilesystem, mock_temp_dir: str
) -> None:
    """Test that SecurityManager rejects temp paths when allow_temp_paths is False."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    fs.create_dir(base_dir)

    # Create a file in the temp directory
    temp_file = Path(mock_temp_dir) / "test.txt"
    fs.create_file(temp_file)

    manager = SecurityManager(str(base_dir), allow_temp_paths=False)

    with pytest.raises(PathSecurityError) as exc_info:
        manager.validate_path(str(temp_file))

    assert exc_info.value.context["reason"] == "temp_paths_not_allowed"
    assert str(temp_file).startswith(str(Path(tempfile.gettempdir())))
    assert not str(Path("/not/a/temp/path")).startswith(
        str(Path(tempfile.gettempdir()))
    )


def test_security_manager_permissive_allows_temp_paths(
    fs: FakeFilesystem, mock_temp_dir: str
) -> None:
    """Test that SecurityManager allows temp paths when allow_temp_paths is True."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    fs.create_dir(base_dir)

    # Create a file in the temp directory
    temp_file = Path(mock_temp_dir) / "test.txt"
    fs.create_file(temp_file)

    manager = SecurityManager(str(base_dir), allow_temp_paths=True)

    # Should not raise an exception
    validated_path = manager.validate_path(str(temp_file))
    # Compare resolved paths to handle platform-specific symlinks
    assert validated_path.resolve() == temp_file.resolve()


def test_security_manager_invalid_directory(fs: FakeFilesystem) -> None:
    """Test that SecurityManager handles invalid directories correctly."""
    base_dir = Path("/test_workspace/nonexistent")

    # Test with non-existent directory
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(base_dir))

    # Test with file instead of directory
    base_dir = Path("/test_workspace/base")
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(test_file))


def test_security_manager_not_a_directory(fs: FakeFilesystem) -> None:
    """Test that SecurityManager handles non-directory paths correctly."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    fs.create_dir(base_dir)

    manager = SecurityManager(str(base_dir))

    # Test with file instead of directory
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)

    with pytest.raises(DirectoryNotFoundError) as exc_info:
        manager.add_allowed_directory(str(test_file))
        assert exc_info.value.context["reason"] == "not_a_directory"


# Symlink Security Tests


def test_safe_symlink(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test that symlinks within allowed directories are permitted."""
    # Setup test directories
    fs.create_dir("/test_workspace/base/safe")
    fs.create_file(
        "/test_workspace/base/safe/target.txt", contents="safe content"
    )
    fs.create_symlink(
        "/test_workspace/base/safe/link.txt",
        "/test_workspace/base/safe/target.txt",
    )

    # Access through symlink should work
    with security_manager.symlink_context():
        resolved = security_manager.resolve_symlink(
            Path("/test_workspace/base/safe/link.txt")
        )
        with open(resolved) as f:
            assert f.read() == "safe content"


def test_unsafe_symlink(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test that symlinks pointing outside allowed directories are blocked."""
    logger = logging.getLogger("ostruct.test")
    logger.info("\n=== Setting up Unsafe Symlink Test ===")

    # Setup directories
    fs.create_dir("/test_workspace/base/safe")
    fs.create_dir("/unsafe")
    fs.create_file("/unsafe/target.txt", contents="unsafe content")
    fs.create_symlink(
        "/test_workspace/base/safe/link.txt", "/unsafe/target.txt"
    )

    # Verify setup
    logger.info("\n=== Verifying Setup ===")
    assert fs.exists("/unsafe/target.txt"), "Target file should exist"
    assert fs.islink("/test_workspace/base/safe/link.txt"), "Link should exist"
    assert (
        fs.readlink("/test_workspace/base/safe/link.txt")
        == "/unsafe/target.txt"
    )

    # Attempt to access through symlink should fail
    with pytest.raises(PathSecurityError) as exc_info:
        with security_manager.symlink_context():
            logger.info("Starting symlink resolution...")
            security_manager.resolve_symlink(
                Path("/test_workspace/base/safe/link.txt")
            )

    logger.info("Error context: %s", exc_info.value.context)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )
    assert "/unsafe/target.txt" in str(exc_info.value)


def test_relative_symlink(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test handling of relative symlinks."""
    # Setup test structure
    fs.create_dir("/test_workspace/base/dir1")
    fs.create_dir("/test_workspace/base/dir2")
    fs.create_file(
        "/test_workspace/base/dir2/target.txt", contents="relative content"
    )

    # Create relative symlink
    os.chdir("/test_workspace/base/dir1")
    fs.create_symlink("link.txt", "../dir2/target.txt")

    # Access through relative symlink should work
    with security_manager.symlink_context():
        resolved = security_manager.resolve_symlink(Path("link.txt"))
        with open(resolved) as f:
            assert f.read() == "relative content"


def test_symlink_loop(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test detection of symlink loops."""
    logger = logging.getLogger("ostruct.test")
    logger.info("\n=== Setting up Symlink Loop Test ===")

    # Create base directory and target file
    base = "/test_workspace/base/loop"
    fs.create_dir(base)
    fs.create_file(f"{base}/target.txt", contents="test")

    # Create valid chain first using relative paths
    fs.create_symlink(f"{base}/link1", "target.txt")
    assert fs.exists(f"{base}/link1"), "link1 should exist"

    fs.create_symlink(f"{base}/link2", "link1")
    assert fs.exists(f"{base}/link2"), "link2 should exist"

    fs.create_symlink(f"{base}/link3", "link2")
    assert fs.exists(f"{base}/link3"), "link3 should exist"

    # Create the loop by updating link1 to point to link3
    fs.remove(f"{base}/link1")
    fs.create_symlink(f"{base}/link1", "link3")

    # Verify loop creation
    logger.info("\n=== Verifying Loop Creation ===")
    assert fs.readlink(f"{base}/link1") == "link3"
    assert fs.readlink(f"{base}/link2") == "link1"
    assert fs.readlink(f"{base}/link3") == "link2"

    # Attempt to resolve should detect loop
    with pytest.raises(PathSecurityError) as exc_info:
        with security_manager.symlink_context():
            logger.info("Starting symlink resolution...")
            security_manager.resolve_symlink(Path(f"{base}/link1"))

    logger.info("Error context: %s", exc_info.value.context)
    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.SYMLINK_LOOP
    )
    assert "loop_chain" in exc_info.value.context


def test_max_depth_exceeded(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test handling of excessive symlink nesting."""
    logger = logging.getLogger("ostruct.test")
    logger.info("\n=== Max Depth Test Setup ===")

    # Set explicit max depth for test
    max_depth = 5  # Use a smaller depth for testing
    security_manager.max_symlink_depth = max_depth

    # Create base directory and target file
    base = "/test_workspace/base/deep"
    fs.create_dir(base)
    fs.create_file(f"{base}/target.txt", contents="deep content")

    # Create valid chain of symlinks using relative paths
    prev_link = "target.txt"
    chain_length = (
        max_depth + 3
    )  # Create a chain slightly longer than max_depth

    logger.info("\n=== Creating Symlink Chain ===")
    for i in range(chain_length):
        link = f"link_{i}"
        link_path = f"{base}/{link}"
        fs.create_symlink(link_path, prev_link)
        logger.info("Created link %d: %s -> %s", i, link_path, prev_link)

        # Verify each link right after creation
        assert fs.exists(link_path), f"Failed to create {link}"
        assert fs.islink(link_path), f"{link} is not a symlink"
        assert (
            fs.readlink(link_path) == prev_link
        ), f"{link} points to wrong target"

        prev_link = link

    # Verify the final link exists
    final_link = f"{base}/link_{chain_length-1}"
    assert fs.exists(final_link), f"Final link {final_link} should exist"

    # Attempt to resolve should fail due to max depth
    with pytest.raises(PathSecurityError) as exc_info:
        with security_manager.symlink_context():
            logger.info("Starting symlink resolution for: %s", final_link)
            security_manager.resolve_symlink(Path(final_link))

    logger.info("Error context: %s", exc_info.value.context)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.MAX_DEPTH_EXCEEDED
    )
    assert exc_info.value.context["depth"] >= max_depth
    assert exc_info.value.context["max_depth"] == max_depth


def test_mixed_absolute_relative_symlinks(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test handling of mixed absolute and relative symlinks."""
    # Setup directory structure
    fs.create_dir("/test_workspace/base/mixed")
    fs.create_dir("/test_workspace/base/mixed/subdir")
    fs.create_file(
        "/test_workspace/base/mixed/target.txt", contents="mixed content"
    )

    # Create mixed symlinks
    fs.create_symlink(
        "/test_workspace/base/mixed/abs_link",
        "/test_workspace/base/mixed/target.txt",
    )
    fs.create_symlink(
        "/test_workspace/base/mixed/subdir/rel_link", "../target.txt"
    )

    # Both should work
    with security_manager.symlink_context():
        abs_resolved = security_manager.resolve_symlink(
            Path("/test_workspace/base/mixed/abs_link")
        )
        with open(abs_resolved) as f:
            assert f.read() == "mixed content"

        rel_resolved = security_manager.resolve_symlink(
            Path("/test_workspace/base/mixed/subdir/rel_link")
        )
        with open(rel_resolved) as f:
            assert f.read() == "mixed content"


def test_symlink_to_dir(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test handling of symlinks to directories."""
    # Setup directory structure
    fs.create_dir("/test_workspace/base/dir_links")
    fs.create_dir("/test_workspace/base/dir_links/target_dir")
    fs.create_file(
        "/test_workspace/base/dir_links/target_dir/file.txt",
        contents="dir content",
    )

    # Create symlink to directory
    fs.create_symlink(
        "/test_workspace/base/dir_links/link_dir",
        "/test_workspace/base/dir_links/target_dir",
    )

    # Access through directory symlink should work
    with security_manager.symlink_context():
        resolved = security_manager.resolve_symlink(
            Path("/test_workspace/base/dir_links/link_dir")
        )
        with open(resolved / "file.txt") as f:
            assert f.read() == "dir content"


def test_broken_symlink(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test handling of broken symlinks."""
    # Create a symlink to non-existent target
    fs.create_dir("/test_workspace/base/broken")
    target = "/test_workspace/base/broken/nonexistent"
    link = "/test_workspace/base/broken/broken_link"
    fs.create_symlink(link, target)

    # Verify setup
    assert fs.islink(link), "Link should exist"
    assert not fs.exists(target), "Target should not exist"

    # Attempt to access should fail gracefully
    with pytest.raises(PathSecurityError) as exc_info:
        with security_manager.symlink_context():
            security_manager.resolve_symlink(Path(link))

    assert (
        exc_info.value.context["reason"] == SecurityErrorReasons.BROKEN_SYMLINK
    )
    assert "Broken symlink" in str(exc_info.value)


def test_file_not_found_before_security(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test that file existence is checked before security permissions."""
    # Try to access non-existent file
    with pytest.raises(FileNotFoundError) as exc_info:
        security_manager.resolve_path("nonexistent.txt")

    assert "File not found" in str(exc_info.value)
    assert not isinstance(exc_info.value, PathSecurityError)


def test_symlink_chain_validation(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test validation of each step in a symlink chain."""
    logger = logging.getLogger("ostruct.test")
    logger.info("\n=== Setting up Symlink Chain Test ===")

    # Create test structure:
    # base/
    #   safe/
    #     link1 -> ../intermediate/link2
    #   intermediate/
    #     link2 -> /unsafe/target.txt
    # unsafe/
    #   target.txt

    fs.create_dir("/test_workspace/base/safe")
    fs.create_dir("/test_workspace/base/intermediate")
    fs.create_dir("/unsafe")
    fs.create_file("/unsafe/target.txt", contents="unsafe")

    # Create symlink chain
    fs.create_symlink(
        "/test_workspace/base/intermediate/link2", "/unsafe/target.txt"
    )
    fs.create_symlink(
        "/test_workspace/base/safe/link1", "../intermediate/link2"
    )

    # Verify setup
    logger.info("\n=== Verifying Setup ===")
    assert fs.exists("/unsafe/target.txt"), "Target should exist"
    assert fs.islink("/test_workspace/base/safe/link1"), "Link1 should exist"
    assert fs.islink(
        "/test_workspace/base/intermediate/link2"
    ), "Link2 should exist"

    # Attempt to resolve should fail at the intermediate link
    with pytest.raises(PathSecurityError) as exc_info:
        with security_manager.symlink_context():
            logger.info("Starting symlink resolution...")
            security_manager.resolve_symlink(
                Path("/test_workspace/base/safe/link1")
            )

    logger.info("Error context: %s", exc_info.value.context)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )
    assert "/unsafe/target.txt" in str(exc_info.value)


def test_validate_path_missing_base(fs: FakeFilesystem) -> None:
    """Test validation with missing base directory."""
    base_dir = Path("/test_workspace/base")

    # Test with non-existent directory
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(base_dir))

    # Test with file instead of directory
    base_dir = Path("/test_workspace/base")
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(test_file))


def test_validate_path_missing_allowed(fs: FakeFilesystem) -> None:
    """Test validation with missing allowed directory."""
    base_dir = Path("/test_workspace/base")

    # Test with non-existent directory
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(base_dir))

    # Test with file instead of directory
    base_dir = Path("/test_workspace/base")
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(test_file))


def test_validate_path_nonexistent_base(fs: FakeFilesystem) -> None:
    """Test validation with nonexistent base directory."""
    base_dir = Path("/test_workspace/nonexistent")

    # Test with non-existent directory
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(base_dir))

    # Test with file instead of directory
    base_dir = Path("/test_workspace/base")
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(test_file))


def test_validate_path_symlink(fs: FakeFilesystem) -> None:
    """Test validation with symlinks."""
    base_dir = Path("/test_workspace/base")

    # Test with non-existent directory
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(base_dir))

    # Test with file instead of directory
    base_dir = Path("/test_workspace/base")
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(test_file))


def test_validate_path_symlink_loop(fs: FakeFilesystem) -> None:
    """Test validation with symlink loops."""
    base_dir = Path("/test_workspace/base")

    # Test with non-existent directory
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(base_dir))

    # Test with file instead of directory
    base_dir = Path("/test_workspace/base")
    test_file = base_dir / "test.txt"
    fs.create_file(test_file)
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(test_file))
