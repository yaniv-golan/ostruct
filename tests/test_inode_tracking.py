"""Test suite for inode-based file tracking in SecurityManager."""

import os
from unittest.mock import patch

import pytest
from ostruct.cli.security import PathSecurity, SecurityManager
from ostruct.cli.security.errors import PathSecurityError


@pytest.mark.no_fs
class TestInodeTracking:
    """Test inode-based file allowlist functionality."""

    def test_pin_file_by_inode_unix(self, tmp_path):
        """Test file pinning by inode on Unix-like systems."""
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

        # Move file and verify it's still allowed
        moved_file = tmp_path / "moved.txt"
        test_file.rename(moved_file)
        assert manager.is_file_allowed_by_inode(moved_file) is True

        # Create new file with original name - should not be allowed
        new_file = tmp_path / "test.txt"
        new_file.write_text("different content")
        assert manager.is_file_allowed_by_inode(new_file) is False

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_pin_file_by_inode_windows(self, tmp_path):
        """Test file pinning behavior on Windows."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Create SecurityManager
        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Pin the file
        assert manager.pin_file_by_inode(test_file) is True

        # Verify file can be accessed after pinning
        assert manager.is_file_allowed_by_inode(test_file) is True

        # Verify Windows-specific file identity is used
        stat_result = os.stat(test_file)
        file_id = manager._get_file_identity(stat_result)
        assert isinstance(file_id, tuple)
        assert len(file_id) == 2
        # First element should be device
        assert file_id[0] == stat_result.st_dev
        # Second element should be an integer (hashed extended_id on Windows)
        assert isinstance(file_id[1], int)

    def test_inode_persistence_across_operations(self, tmp_path):
        """Test that inode tracking survives various file operations."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Pin the file
        manager.pin_file_by_inode(test_file)

        # Test 1: Move file
        moved_file = tmp_path / "moved.txt"
        test_file.rename(moved_file)
        assert manager.is_file_allowed_by_inode(moved_file) is True

        # Test 2: Copy file back (different inode)
        copied_file = tmp_path / "copied.txt"
        copied_file.write_text(moved_file.read_text())
        assert manager.is_file_allowed_by_inode(copied_file) is False

        # Test 3: Symlink to moved file
        if os.name != "nt":  # Unix-like systems support symlinks
            symlink_file = tmp_path / "symlink.txt"
            symlink_file.symlink_to(moved_file)
            # Symlink itself should not be allowed unless explicitly pinned
            assert manager.is_file_allowed_by_inode(symlink_file) is False
            # But target should still be allowed
            assert manager.is_file_allowed_by_inode(moved_file) is True

    def test_symlink_target_validation(self, tmp_path):
        """Test symlink target validation with different security modes."""
        if os.name == "nt":
            pytest.skip("Symlink tests not supported on Windows")

        # Create allowed file in base directory
        allowed_file = tmp_path / "allowed.txt"
        allowed_file.write_text("allowed")

        # Create disallowed file outside base directory to test pure inode behavior
        disallowed_dir = tmp_path.parent / "disallowed_dir"
        disallowed_dir.mkdir(exist_ok=True)
        disallowed_file = disallowed_dir / "disallowed.txt"
        disallowed_file.write_text("disallowed")

        # Create symlinks
        allowed_symlink = tmp_path / "allowed_link.txt"
        disallowed_symlink = tmp_path / "disallowed_link.txt"
        allowed_symlink.symlink_to(allowed_file)
        disallowed_symlink.symlink_to(disallowed_file)

        # Test STRICT mode
        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )
        manager.pin_file_by_inode(allowed_file)

        # Allowed symlink should pass
        assert manager.validate_symlink_target(allowed_symlink) is True

        # Disallowed symlink should raise in STRICT mode
        with pytest.raises(PathSecurityError, match="Path not in allowlist"):
            manager.validate_symlink_target(disallowed_symlink)

        # Test WARN mode
        manager.security_mode = PathSecurity.WARN
        # Should return True but log warning
        assert manager.validate_symlink_target(disallowed_symlink) is True

        # Test PERMISSIVE mode
        manager.security_mode = PathSecurity.PERMISSIVE
        assert manager.validate_symlink_target(disallowed_symlink) is True

    def test_broken_symlink_handling(self, tmp_path):
        """Test handling of broken symlinks."""
        if os.name == "nt":
            pytest.skip("Symlink tests not supported on Windows")

        # Create symlink to non-existent file
        broken_symlink = tmp_path / "broken_link.txt"
        broken_symlink.symlink_to("nonexistent.txt")

        # Test STRICT mode
        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Broken symlinks within base directory should be allowed in directory-based validation
        # The symlink resolves to tmp_path/nonexistent.txt which is within the base directory
        assert manager.validate_symlink_target(broken_symlink) is True

        # Test WARN mode
        manager.security_mode = PathSecurity.WARN
        assert manager.validate_symlink_target(broken_symlink) is True

        # Test PERMISSIVE mode
        manager.security_mode = PathSecurity.PERMISSIVE
        assert manager.validate_symlink_target(broken_symlink) is True

    def test_o_nofollow_security(self, tmp_path):
        """Test O_NOFOLLOW security on Unix systems."""
        if os.name == "nt":
            pytest.skip("O_NOFOLLOW not available on Windows")

        # Create test file and symlink
        real_file = tmp_path / "real.txt"
        real_file.write_text("real content")

        symlink_file = tmp_path / "symlink.txt"
        symlink_file.symlink_to(real_file)

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Pin real file
        assert manager.pin_file_by_inode(real_file) is True

        # Try to pin symlink - should detect it and pin the target
        with patch(
            "os.open", side_effect=OSError(20, "Not a directory")
        ):  # ENOTDIR
            # This simulates O_NOFOLLOW detecting a symlink
            assert manager.pin_file_by_inode(symlink_file) is False

    def test_configure_security_mode_with_allow_files(self, tmp_path):
        """Test configure_security_mode with allow_files parameter."""
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

    def test_allow_list_file_loading(self, tmp_path):
        """Test loading files from allow-list files."""
        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        dir1 = tmp_path / "dir1"
        file1.write_text("content1")
        file2.write_text("content2")
        dir1.mkdir()

        # Create allow-list file
        allow_list = tmp_path / "allow.txt"
        allow_list.write_text(
            f"""# Allow list
{file1}
{file2}
{dir1}
# Comment line
"""
        )

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Configure with allow-list
        manager.configure_security_mode(
            mode=PathSecurity.STRICT, allow_lists=[str(allow_list)]
        )

        # Files should be allowed by inode
        assert manager.is_file_allowed_by_inode(file1) is True
        assert manager.is_file_allowed_by_inode(file2) is True

        # Directory should be in allowed dirs
        assert dir1 in manager.allowed_dirs

    def test_cross_platform_file_identity(self, tmp_path):
        """Test cross-platform file identity generation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        manager = SecurityManager(base_dir=tmp_path)
        st = os.stat(test_file, follow_symlinks=False)

        # Test Unix-like behavior
        with patch("os.name", "posix"):
            identity_unix = manager._get_file_identity(st)
            assert identity_unix == (st.st_dev, st.st_ino)

        # Test Windows behavior
        with patch("os.name", "nt"):
            identity_windows = manager._get_file_identity(st)
            assert identity_windows[0] == st.st_dev
            assert isinstance(identity_windows[1], int)
            # Should be different from Unix due to hashing
            assert identity_windows != identity_unix
