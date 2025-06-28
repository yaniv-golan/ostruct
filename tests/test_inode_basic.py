"""Basic test for inode functionality."""

import os
import tempfile
from pathlib import Path

from ostruct.cli.security import PathSecurity, SecurityManager


def test_basic_inode_functionality():
    """Test basic inode pinning and validation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Create SecurityManager in strict mode
        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Pin the file by inode
        assert manager.pin_file_by_inode(test_file) is True

        # Verify file is allowed by inode
        assert manager.is_file_allowed_by_inode(test_file) is True

        # Test file identity generation
        st = os.stat(test_file, follow_symlinks=False)
        identity = manager._get_file_identity(st)
        assert isinstance(identity, tuple)
        assert len(identity) == 2


def test_inode_persistence():
    """Test that inode tracking survives file moves."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Pin the file
        manager.pin_file_by_inode(test_file)

        # Move file and verify it's still allowed
        moved_file = tmp_path / "moved.txt"
        test_file.rename(moved_file)
        assert manager.is_file_allowed_by_inode(moved_file) is True

        # Create new file with original name - should not be allowed
        new_file = tmp_path / "test.txt"
        new_file.write_text("different content")
        assert manager.is_file_allowed_by_inode(new_file) is False


def test_configure_with_allow_files():
    """Test configure_security_mode with allow_files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Configure with allow_files
        manager.configure_security_mode(
            mode=PathSecurity.STRICT, allow_files=[str(file1), str(file2)]
        )

        # Both files should be allowed
        assert manager.is_file_allowed_by_inode(file1) is True
        assert manager.is_file_allowed_by_inode(file2) is True

        # Other files should not be allowed
        file3 = tmp_path / "file3.txt"
        file3.write_text("content3")
        assert manager.is_file_allowed_by_inode(file3) is False
