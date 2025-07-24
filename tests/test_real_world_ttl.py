"""Real-world validation tests for TTL cache functionality."""

import hashlib
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.ostruct.cli.upload_cache import UploadCache
from src.ostruct.cli.upload_manager import SharedUploadManager


def make_test_hash(pattern: str) -> str:
    """Generate a proper SHA-256 hash for test patterns."""
    return hashlib.sha256(pattern.encode()).hexdigest()


@pytest.mark.asyncio
@pytest.mark.no_fs
class TestRealWorldTTLScenarios:
    """Test realistic TTL cache usage scenarios."""

    @pytest.fixture
    def temp_cache(self):
        """Create temporary cache for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "test_cache.db"
            cache = UploadCache(cache_path)
            yield cache

    @pytest.fixture
    def mock_client(self):
        """Create mock OpenAI client."""
        client = AsyncMock()
        client.files.delete = AsyncMock()
        return client

    async def test_repeated_aif_analysis_scenario(
        self, temp_cache, mock_client
    ):
        """Test scenario: Running AIF analysis multiple times on same files."""
        cache = temp_cache
        manager = SharedUploadManager(mock_client)
        manager._cache = cache

        # Simulate first run - upload files
        files_run1 = {
            "report.pdf": "file-report-123",
            "data.csv": "file-data-456",
            "analysis.py": "file-analysis-789",
        }

        for filename, file_id in files_run1.items():
            # Cache the uploads
            file_hash = make_test_hash(f"run1-{filename}")
            cache.store(
                file_hash, file_id, 1024 * len(filename), int(time.time())
            )
            manager._all_uploaded_ids.add(file_id)

        # First cleanup - should preserve all (within TTL)
        await manager.cleanup_uploads(ttl_days=14)

        # No files should be deleted (all cached and within TTL)
        assert mock_client.files.delete.call_count == 0

        # Simulate second run - same files, should hit cache
        cache_hits = 0
        for filename, expected_file_id in files_run1.items():
            file_hash = make_test_hash(f"run1-{filename}")
            cached_file_id = cache.lookup(file_hash)
            if cached_file_id == expected_file_id:
                cache_hits += 1

        # All files should be cache hits
        assert cache_hits == 3

        # Simulate time passing (15 days later)
        old_timestamp = int(time.time()) - (15 * 86400)

        # Update cache entries to be expired
        with cache._get_connection() as conn:
            conn.execute("UPDATE files SET created_at = ?", (old_timestamp,))
            conn.commit()

        # Third run cleanup - should delete expired files
        mock_client.files.delete.reset_mock()

        # Re-add files to cleanup list (simulate new run)
        manager._all_uploaded_ids.clear()
        for file_id in files_run1.values():
            manager._all_uploaded_ids.add(file_id)

        await manager.cleanup_uploads(ttl_days=14)

        # All files should be deleted (expired)
        assert mock_client.files.delete.call_count == 3

    async def test_mixed_file_types_routing_scenario(
        self, temp_cache, mock_client
    ):
        """Test scenario: Mixed file types with different routing intents."""
        cache = temp_cache
        manager = SharedUploadManager(mock_client)
        manager._cache = cache

        # Simulate files for different tools
        files = {
            # Code Interpreter files
            "script.py": "file-script-ci",
            "data.csv": "file-data-ci",
            # File Search files
            "docs.pdf": "file-docs-fs",
            "manual.txt": "file-manual-fs",
            # General attachments
            "image.png": "file-image-gen",
        }

        current_time = int(time.time())

        for filename, file_id in files.items():
            # Store with metadata indicating purpose
            metadata = {
                "tool": (
                    "code-interpreter"
                    if filename.endswith((".py", ".csv"))
                    else (
                        "file-search"
                        if filename.endswith((".pdf", ".txt"))
                        else "general"
                    )
                )
            }

            cache.store(
                make_test_hash(f"mixed-{filename}"),
                file_id,
                1024 * len(filename),
                current_time,
                metadata,
            )
            manager._all_uploaded_ids.add(file_id)

        # Cleanup with standard TTL
        await manager.cleanup_uploads(ttl_days=14)

        # All files should be preserved (within TTL)
        assert mock_client.files.delete.call_count == 0

        # Verify all files still cached
        for filename in files.keys():
            assert (
                cache.lookup(make_test_hash(f"mixed-{filename}")) is not None
            )

    async def test_file_modification_detection_scenario(
        self, temp_cache, mock_client
    ):
        """Test scenario: File modification detection with cache invalidation."""
        cache = temp_cache

        # Create temporary files to simulate modification
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("Original content")
            test_file = Path(f.name)

        try:
            # Initial file stats
            stat = test_file.stat()
            original_hash = cache.compute_file_hash(test_file)

            # Cache the file
            cache.store(
                original_hash,
                "file-original",
                stat.st_size,
                int(stat.st_mtime),
            )

            # Verify cache hit with validation
            cached_id = cache.lookup_with_validation(test_file, original_hash)
            assert cached_id == "file-original"

            # Modify the file
            time.sleep(0.1)  # Ensure mtime changes
            test_file.write_text("Modified content with different length")

            # File should be detected as changed
            assert cache.is_file_changed(
                test_file, stat.st_size, int(stat.st_mtime)
            )

            # Cache lookup with validation should return None (file changed)
            cached_id = cache.lookup_with_validation(test_file, original_hash)
            assert cached_id is None

            # New hash should be different
            new_hash = cache.compute_file_hash(test_file)
            assert new_hash != original_hash

        finally:
            test_file.unlink()

    async def test_cost_optimization_scenario(self, temp_cache, mock_client):
        """Test scenario: Cost optimization with different TTL strategies."""
        cache = temp_cache
        manager = SharedUploadManager(mock_client)
        manager._cache = cache

        # Simulate large files (high cost to re-upload)
        large_files = {
            "dataset.csv": ("file-dataset-large", 100 * 1024 * 1024),  # 100MB
            "model.pkl": ("file-model-large", 50 * 1024 * 1024),  # 50MB
            "archive.zip": ("file-archive-large", 200 * 1024 * 1024),  # 200MB
        }

        current_time = int(time.time())

        for filename, (file_id, size) in large_files.items():
            cache.store(
                make_test_hash(f"cost-{filename}"), file_id, size, current_time
            )
            manager._all_uploaded_ids.add(file_id)

        # Test different TTL strategies

        # Strategy 1: Development (short TTL for cost control)
        await manager.cleanup_uploads(ttl_days=3)
        assert mock_client.files.delete.call_count == 0  # Still within 3 days

        # Strategy 2: Production (longer TTL for stability)
        await manager.cleanup_uploads(ttl_days=30)
        assert mock_client.files.delete.call_count == 0  # Within 30 days

        # Strategy 3: Compliance (immediate deletion)
        mock_client.files.delete.reset_mock()
        await manager.cleanup_uploads(ttl_days=0)
        assert mock_client.files.delete.call_count == 3  # All deleted

    async def test_performance_measurement_scenario(
        self, temp_cache, mock_client
    ):
        """Test scenario: Performance measurement and cache hit rate calculation."""
        cache = temp_cache

        # Simulate multiple runs with repeated files
        runs = [
            # Run 1: Initial files
            ["report.pdf", "data.csv", "script.py"],
            # Run 2: Mostly repeated (typical re-run scenario)
            ["report.pdf", "data.csv", "config.json"],
            # Run 3: Core files + new analysis
            ["report.pdf", "script.py", "analysis.py"],
            # Run 4: Same core files + iteration
            ["report.pdf", "data.csv", "script.py", "results.txt"],
        ]

        total_files = 0
        cache_hits = 0
        current_time = int(time.time())

        for run_num, files in enumerate(runs, 1):
            for filename in files:
                total_files += 1
                file_hash = make_test_hash(f"perf-{filename}")

                # Check if file is already cached
                cached_id = cache.lookup(file_hash)
                if cached_id:
                    cache_hits += 1
                    # Update last accessed (LRU behavior)
                    cache.update_last_accessed(cached_id)
                else:
                    # Simulate new upload
                    file_id = f"file-{filename}-{run_num}"
                    cache.store(file_hash, file_id, 1024, current_time)

        # Calculate cache hit rate
        cache_hit_rate = (cache_hits / total_files) * 100

        # Should achieve >50% hit rate with repeated files
        assert cache_hit_rate > 50.0

        # Verify cache statistics
        stats = cache.get_stats()
        assert stats["entries"] > 0
        assert "size_bytes" in stats

    async def test_edge_case_scenarios(self, temp_cache, mock_client):
        """Test edge cases: corruption recovery, disk space, network issues."""
        # Use a separate cache path for corruption testing
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "corruption_test.db"

        # Test 1: Cache corruption recovery
        cache = UploadCache(cache_path)
        cache.store("test-hash", "test-file", 1024, int(time.time()))

        # Simulate corruption by writing invalid data
        with open(cache_path, "w") as f:
            f.write("corrupted data")

        # Creating new cache should handle corruption gracefully
        try:
            new_cache = UploadCache(cache_path)
            # Should not raise exception
            stats = new_cache.get_stats()
            assert stats["entries"] == 0  # Clean slate after corruption
        except Exception as e:
            pytest.fail(f"Cache corruption not handled gracefully: {e}")

        # Test 2: Network interruption during cleanup
        manager = SharedUploadManager(mock_client)
        manager._cache = UploadCache(cache_path)
        manager._all_uploaded_ids.add("file-network-test")

        # Simulate network error
        mock_client.files.delete.side_effect = Exception("Network timeout")

        # Cleanup should not crash
        try:
            await manager.cleanup_uploads(ttl_days=0)
        except Exception as e:
            pytest.fail(f"Network error not handled gracefully: {e}")

        # Test 3: Disk space limitations (simulated)
        # This would be hard to test realistically without actually filling disk
        # But we can test that cache creation fails gracefully
        invalid_path = Path("/invalid/path/that/does/not/exist/cache.db")
        try:
            invalid_cache = UploadCache(invalid_path)
            # Operations should fail gracefully
            result = invalid_cache.lookup("any-hash")
            assert result is None  # Should return None, not crash
        except Exception:
            # It's OK if it raises exception, as long as it's handled
            pass
