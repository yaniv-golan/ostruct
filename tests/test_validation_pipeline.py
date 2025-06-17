"""Test suite for security validation pipeline functionality."""

import tempfile
from pathlib import Path

import pytest
from ostruct.cli.errors import OstructFileNotFoundError
from ostruct.cli.security import PathSecurity, SecurityManager
from ostruct.cli.security.errors import PathSecurityError


def test_validate_file_access_basic():
    """Test basic file access validation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        # Should succeed
        result = manager.validate_file_access(test_file, "test context")
        assert result == test_file.resolve()


def test_validate_file_access_not_found():
    """Test file access validation with non-existent file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        # Should raise OstructFileNotFoundError
        with pytest.raises(OstructFileNotFoundError, match="File not found"):
            manager.validate_file_access(tmp_path / "nonexistent.txt")


def test_validate_file_access_strict_mode():
    """Test file access validation in strict mode."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create file outside base directory
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "outside.txt"
        outside_file.write_text("outside content")

        try:
            manager = SecurityManager(
                base_dir=tmp_path, security_mode=PathSecurity.STRICT
            )

            # Should raise PathSecurityError in strict mode
            with pytest.raises(
                PathSecurityError, match="Path not in allowlist"
            ):
                manager.validate_file_access(outside_file, "test context")

        finally:
            outside_file.unlink(missing_ok=True)
            outside_dir.rmdir()


def test_validate_batch_access():
    """Test batch file access validation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.WARN
        )

        # Should validate both files
        results = manager.validate_batch_access([file1, file2], "batch test")
        assert len(results) == 2
        assert file1.resolve() in results
        assert file2.resolve() in results


def test_validate_batch_access_mixed_results():
    """Test batch validation with mix of valid and invalid files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create one valid file
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("valid content")

        # One invalid (non-existent) file
        invalid_file = tmp_path / "invalid.txt"

        manager = SecurityManager(
            base_dir=tmp_path,
            security_mode=PathSecurity.WARN,  # Should continue with warnings
        )

        # Should validate only the valid file
        results = manager.validate_batch_access(
            [valid_file, invalid_file], "mixed batch test"
        )
        assert len(results) == 1
        assert valid_file.resolve() in results


def test_validate_batch_access_strict_mode():
    """Test batch validation in strict mode."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create one valid file
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("valid content")

        # One invalid (non-existent) file
        invalid_file = tmp_path / "invalid.txt"

        manager = SecurityManager(
            base_dir=tmp_path,
            security_mode=PathSecurity.STRICT,  # Should fail on any error
        )

        # Should raise PathSecurityError for the batch
        with pytest.raises(PathSecurityError, match="Batch validation failed"):
            manager.validate_batch_access(
                [valid_file, invalid_file], "strict batch test"
            )


def test_security_context_manager():
    """Test temporary security context manager."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create file outside base directory
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "outside.txt"
        outside_file.write_text("outside content")

        try:
            manager = SecurityManager(
                base_dir=tmp_path, security_mode=PathSecurity.STRICT
            )

            # Should fail in normal strict mode
            with pytest.raises(PathSecurityError):
                manager.validate_file_access(outside_file)

            # Should succeed in permissive context
            with manager.security_context(PathSecurity.PERMISSIVE):
                result = manager.validate_file_access(
                    outside_file, "context test"
                )
                assert result == outside_file.resolve()

            # Should fail again after context exits
            with pytest.raises(PathSecurityError):
                manager.validate_file_access(outside_file)

        finally:
            outside_file.unlink(missing_ok=True)
            outside_dir.rmdir()


def test_security_context_with_additional_allows():
    """Test security context with additional allowed directories."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create additional directory
        extra_dir = tmp_path.parent / "extra"
        extra_dir.mkdir(exist_ok=True)
        extra_file = extra_dir / "extra.txt"
        extra_file.write_text("extra content")

        try:
            manager = SecurityManager(
                base_dir=tmp_path, security_mode=PathSecurity.STRICT
            )

            # Should fail normally
            with pytest.raises(PathSecurityError):
                manager.validate_file_access(extra_file)

            # Should succeed with additional allows
            with manager.security_context(
                PathSecurity.STRICT, additional_allows=[str(extra_dir)]
            ):
                result = manager.validate_file_access(
                    extra_file, "additional test"
                )
                assert result == extra_file.resolve()

        finally:
            extra_file.unlink(missing_ok=True)
            extra_dir.rmdir()


def test_security_context_state_restoration():
    """Test that security context properly restores state."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        manager = SecurityManager(
            base_dir=tmp_path, security_mode=PathSecurity.STRICT
        )

        # Save original state
        original_mode = manager.security_mode
        original_dirs = manager.allowed_dirs.copy()

        # Modify state within context
        with manager.security_context(
            PathSecurity.PERMISSIVE, additional_allows=["/tmp"]
        ):
            # State should be modified
            assert manager.security_mode == PathSecurity.PERMISSIVE
            assert len(manager.allowed_dirs) > len(original_dirs)

        # State should be restored
        assert manager.security_mode == original_mode
        assert manager.allowed_dirs == original_dirs
