"""Tests for enhanced symlink depth protection."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import pytest
from ostruct.cli.security.errors import PathSecurityError, SecurityErrorReasons
from ostruct.cli.security.symlink_depth_protection import (
    SymlinkDepthProtector,
    get_symlink_depth_protector,
    reset_symlink_depth_protector,
    symlink_depth_protection_context,
)
from ostruct.cli.security.symlink_resolver import _resolve_symlink
from pyfakefs.fake_filesystem import FakeFilesystem


class TestSymlinkDepthProtector:
    """Test the SymlinkDepthProtector class."""

    def test_basic_depth_validation(self):
        """Test basic depth validation."""
        protector = SymlinkDepthProtector(max_depth=3)

        # Should not raise for valid depths
        assert protector.validate_symlink_depth(Path("/test/path"), 0)
        assert protector.validate_symlink_depth(Path("/test/path"), 1)
        assert protector.validate_symlink_depth(Path("/test/path"), 2)

        # Should raise for invalid depth
        with pytest.raises(PathSecurityError) as exc_info:
            protector.validate_symlink_depth(Path("/test/path"), 4)
        assert "depth exceeded maximum" in str(exc_info.value)

    def test_concurrent_request_limit(self):
        """Test concurrent request limiting."""
        protector = SymlinkDepthProtector(max_concurrent_requests=2)

        # First two requests should succeed
        ctx1 = protector._request_context()
        ctx2 = protector._request_context()

        ctx1.__enter__()
        ctx2.__enter__()

        # Third request should fail
        with pytest.raises(PathSecurityError) as exc_info:
            with protector._request_context():
                pass
        assert "concurrent requests" in str(exc_info.value)

        # Clean up
        ctx1.__exit__(None, None, None)
        ctx2.__exit__(None, None, None)

    def test_processing_time_limit(self):
        """Test processing time limit."""
        protector = SymlinkDepthProtector(max_processing_time=0.1)

        # Test that processing time is checked within a single request
        with protector._request_context():
            # First call should succeed
            protector.validate_depth(0, Path("/test/path"))

            # Wait to exceed time limit
            time.sleep(0.2)

            # Second call should fail due to processing time limit
            with pytest.raises(PathSecurityError) as exc_info:
                protector.validate_depth(1, Path("/test/path"))
            assert "processing time" in str(exc_info.value)

    def test_filesystem_ops_limit(self):
        """Test filesystem operations limit."""
        protector = SymlinkDepthProtector(max_filesystem_ops=3)

        # Test that filesystem ops are checked within a single request
        with protector._request_context():
            # First 3 operations should succeed
            protector.validate_depth(0, Path("/test/path1"))
            protector.validate_depth(1, Path("/test/path2"))
            protector.validate_depth(2, Path("/test/path3"))

            # Fourth operation should fail
            with pytest.raises(PathSecurityError) as exc_info:
                protector.validate_depth(3, Path("/test/path4"))
            assert "Filesystem operations limit exceeded" in str(
                exc_info.value
            )

    def test_timing_protection(self):
        """Test timing attack protection."""
        protector = SymlinkDepthProtector(enable_timing_protection=True)

        start_time = time.time()
        protector.validate_symlink_depth(Path("/test/path"), 0)
        elapsed = time.time() - start_time

        # Should take at least minimum response time
        assert elapsed >= 0.1

    def test_timing_protection_disabled(self):
        """Test timing protection can be disabled."""
        protector = SymlinkDepthProtector(enable_timing_protection=False)

        start_time = time.time()
        protector.validate_symlink_depth(Path("/test/path"), 0)
        elapsed = time.time() - start_time

        # Should be much faster when disabled
        assert elapsed < 0.05

    def test_metrics_tracking(self):
        """Test metrics are tracked correctly."""
        protector = SymlinkDepthProtector()

        # Initial metrics should be zero
        metrics = protector.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["filesystem_ops"] == 0

        # Process some requests
        protector.validate_symlink_depth(Path("/test/path1"), 0)
        protector.validate_symlink_depth(Path("/test/path2"), 1)
        protector.validate_symlink_depth(Path("/test/path3"), 2)

        # Check updated metrics
        metrics = protector.get_metrics()
        assert metrics["total_requests"] == 3
        assert metrics["filesystem_ops"] > 0

    def test_is_symlink_safe(self, fs: FakeFilesystem):
        """Test symlink safety checking."""
        protector = SymlinkDepthProtector(max_concurrent_requests=1)

        # Create test files
        fs.create_file("/test/regular.txt", contents="test")
        fs.create_symlink("/test/link.txt", "/test/regular.txt")

        # Regular file should be safe
        assert protector.is_symlink_safe(Path("/test/regular.txt")) is True

        # Symlink should be safe when under limit
        assert protector.is_symlink_safe(Path("/test/link.txt")) is True

        # Create a protector with very low limits to test failure
        strict_protector = SymlinkDepthProtector(max_depth=0)
        # When depth is 1 (simulating a symlink traversal), it should fail
        try:
            strict_protector.validate_symlink_depth(Path("/test/link.txt"), 1)
            assert False, "Should have raised PathSecurityError"
        except PathSecurityError:
            # This is expected
            pass

    def test_thread_safety(self):
        """Test thread safety of the protector."""
        protector = SymlinkDepthProtector(max_concurrent_requests=5)
        results = []

        def worker(worker_id):
            try:
                protector.validate_symlink_depth(
                    Path(f"/test/path{worker_id}"), 0
                )
                time.sleep(0.1)  # Simulate work
                protector.validate_symlink_depth(
                    Path(f"/test/path{worker_id}"), 1
                )
                return f"success_{worker_id}"
            except Exception as e:
                return f"error_{worker_id}_{type(e).__name__}"

        # Run multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in as_completed(futures):
                results.append(future.result())

        # Should have some successes and some failures due to concurrent limit
        successes = [r for r in results if r.startswith("success")]
        errors = [r for r in results if r.startswith("error")]

        assert len(successes) <= 5  # At most max_concurrent_requests
        assert len(errors) >= 5  # At least some should fail


class TestSymlinkDepthProtectionIntegration:
    """Test integration with symlink resolver."""

    def test_enhanced_protection_in_resolver(self, fs: FakeFilesystem):
        """Test that enhanced protection is used in symlink resolver."""
        # Create a chain of symlinks
        fs.create_file("/test/target.txt", contents="test")
        fs.create_symlink("/test/link1.txt", "/test/target.txt")
        fs.create_symlink("/test/link2.txt", "/test/link1.txt")
        fs.create_symlink("/test/link3.txt", "/test/link2.txt")

        # Reset protector to ensure clean state
        reset_symlink_depth_protector()

        # Should work with normal depth
        result = _resolve_symlink(
            Path("/test/link3.txt"),
            max_depth=10,
            allowed_dirs=[Path("/test")],
        )
        assert result == Path("/test/target.txt")

        # Should fail with low depth limit
        with pytest.raises(PathSecurityError) as exc_info:
            _resolve_symlink(
                Path("/test/link3.txt"),
                max_depth=2,
                allowed_dirs=[Path("/test")],
            )
        assert (
            exc_info.value.context["reason"]
            == SecurityErrorReasons.SYMLINK_MAX_DEPTH
        )

    def test_concurrent_symlink_resolution_protection(
        self, fs: FakeFilesystem
    ):
        """Test protection against concurrent symlink resolution attacks."""
        # Create symlinks
        fs.create_file("/test/target.txt", contents="test")
        fs.create_symlink("/test/link.txt", "/test/target.txt")

        # Set low concurrent limit
        protector = SymlinkDepthProtector(max_concurrent_requests=2)
        reset_symlink_depth_protector()

        # Patch the global protector
        with patch.object(
            sys.modules["ostruct.cli.security.symlink_resolver"],
            "get_symlink_depth_protector",
            return_value=protector,
        ):
            results = []

            def resolve_worker(worker_id):
                try:
                    _resolve_symlink(
                        Path("/test/link.txt"),
                        max_depth=10,
                        allowed_dirs=[Path("/test")],
                    )
                    return f"success_{worker_id}"
                except PathSecurityError as e:
                    if "concurrent requests" in str(e):
                        return f"concurrent_error_{worker_id}"
                    return f"other_error_{worker_id}"
                except Exception as e:
                    return f"unexpected_error_{worker_id}_{type(e).__name__}"

            # Run multiple threads
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(resolve_worker, i) for i in range(5)
                ]
                for future in as_completed(futures):
                    results.append(future.result())

            # Should have some successes and some concurrent errors
            successes = [r for r in results if r.startswith("success")]
            concurrent_errors = [
                r for r in results if r.startswith("concurrent_error")
            ]

            assert len(successes) <= 2  # At most max_concurrent_requests
            assert len(concurrent_errors) >= 3  # At least some should fail

    def test_timing_attack_mitigation(self, fs: FakeFilesystem):
        """Test that timing attacks are mitigated."""
        # Create symlinks of different depths
        fs.create_file("/test/target.txt", contents="test")
        fs.create_symlink("/test/shallow.txt", "/test/target.txt")
        fs.create_symlink("/test/deep1.txt", "/test/target.txt")
        fs.create_symlink("/test/deep2.txt", "/test/deep1.txt")
        fs.create_symlink("/test/deep3.txt", "/test/deep2.txt")

        # Reset protector to ensure clean state
        reset_symlink_depth_protector()

        # Time shallow resolution
        start_time = time.time()
        _resolve_symlink(
            Path("/test/shallow.txt"),
            max_depth=10,
            allowed_dirs=[Path("/test")],
        )
        shallow_time = time.time() - start_time

        # Time deep resolution
        start_time = time.time()
        _resolve_symlink(
            Path("/test/deep3.txt"),
            max_depth=10,
            allowed_dirs=[Path("/test")],
        )
        deep_time = time.time() - start_time

        # Both should take at least minimum response time
        assert shallow_time >= 0.1
        assert deep_time >= 0.1

        # Time difference should be small due to timing protection
        assert abs(shallow_time - deep_time) < 0.1


class TestGlobalProtectorManagement:
    """Test global protector instance management."""

    def test_global_protector_singleton(self):
        """Test that global protector is a singleton."""
        reset_symlink_depth_protector()

        protector1 = get_symlink_depth_protector()
        protector2 = get_symlink_depth_protector()

        assert protector1 is protector2

    def test_global_protector_reset(self):
        """Test resetting global protector."""
        protector1 = get_symlink_depth_protector()
        reset_symlink_depth_protector()
        protector2 = get_symlink_depth_protector()

        assert protector1 is not protector2

    def test_symlink_depth_protection_context(self):
        """Test the context manager function."""
        reset_symlink_depth_protector()
        custom_protector = SymlinkDepthProtector(max_depth=5)

        with symlink_depth_protection_context(custom_protector) as protector:
            assert isinstance(protector, SymlinkDepthProtector)
            assert protector.max_depth == 5
            # Test that the custom protector is being used
            assert protector.validate_symlink_depth(Path("/test/path"), 0)

        # Should work multiple times
        with symlink_depth_protection_context(custom_protector) as protector:
            assert isinstance(protector, SymlinkDepthProtector)
            assert protector.max_depth == 5
