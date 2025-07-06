"""Tests for upload cache functionality."""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.ostruct.cli.upload_cache import UploadCache


@pytest.mark.no_fs
class TestUploadCache:
    """Test UploadCache functionality."""

    @pytest.fixture
    def temp_cache(self):
        """Create temporary cache for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "test_cache.db"
            cache = UploadCache(cache_path)
            yield cache

    def test_basic_store_and_lookup(self, temp_cache):
        """Test basic store and lookup operations."""
        file_hash = "abc123"
        file_id = "file-123"

        # Store
        temp_cache.store(file_hash, file_id, 1024, int(time.time()))

        # Lookup
        result = temp_cache.lookup(file_hash)
        assert result == file_id

    def test_cache_miss(self, temp_cache):
        """Test lookup for non-existent hash."""
        result = temp_cache.lookup("nonexistent")
        assert result is None

    def test_file_validation(self, temp_cache):
        """Test file change detection."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            file_path = Path(f.name)

        try:
            # Get initial stats
            stat = file_path.stat()
            size = stat.st_size
            mtime = int(stat.st_mtime)

            # Test no change
            assert not temp_cache.is_file_changed(file_path, size, mtime)

            # Modify file
            time.sleep(0.1)  # Ensure mtime changes
            file_path.write_text("modified content")

            # Test change detected
            assert temp_cache.is_file_changed(file_path, size, mtime)
        finally:
            file_path.unlink()

    def test_hash_computation(self, temp_cache):
        """Test file hash computation."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            content = b"test content for hashing"
            f.write(content)
            file_path = Path(f.name)

        try:
            hash1 = temp_cache.compute_file_hash(file_path)

            # Hash should be consistent
            hash2 = temp_cache.compute_file_hash(file_path)
            assert hash1 == hash2

            # Hash should be hex string
            assert all(c in "0123456789abcdef" for c in hash1)

            # SHA256 should be 64 chars
            assert len(hash1) == 64
        finally:
            file_path.unlink()

    def test_concurrent_access(self, temp_cache):
        """Test thread-safe concurrent access."""

        def store_entry(i):
            temp_cache.store(f"hash{i}", f"file{i}", 1024, int(time.time()))

        threads = []
        for i in range(10):
            t = threading.Thread(target=store_entry, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All entries should be stored
        for i in range(10):
            assert temp_cache.lookup(f"hash{i}") == f"file{i}"

    def test_cache_stats(self, temp_cache):
        """Test cache statistics."""
        # Empty cache
        stats = temp_cache.get_stats()
        assert stats["entries"] == 0

        # Add entries
        for i in range(5):
            temp_cache.store(f"hash{i}", f"file{i}", 1024, int(time.time()))

        stats = temp_cache.get_stats()
        assert stats["entries"] == 5
        assert stats["hash_algorithm"] == "sha256"
        assert "path" in stats

    def test_lookup_with_validation(self, temp_cache):
        """Test lookup with file validation."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            file_path = Path(f.name)

        try:
            # Store in cache
            file_hash = temp_cache.compute_file_hash(file_path)
            stat = file_path.stat()
            temp_cache.store(
                file_hash, "file-123", stat.st_size, int(stat.st_mtime)
            )

            # Should find cached entry
            result = temp_cache.lookup_with_validation(file_path, file_hash)
            assert result == "file-123"

            # Modify file
            time.sleep(0.1)
            file_path.write_text("modified")

            # Should not find cached entry (file changed)
            result = temp_cache.lookup_with_validation(file_path, file_hash)
            assert result is None
        finally:
            file_path.unlink()

    def test_invalidate(self, temp_cache):
        """Test cache invalidation."""
        file_hash = "test_hash"
        temp_cache.store(file_hash, "file-123", 1024, int(time.time()))

        # Verify stored
        assert temp_cache.lookup(file_hash) == "file-123"

        # Invalidate
        temp_cache.invalidate(file_hash)

        # Should be gone
        assert temp_cache.lookup(file_hash) is None

    def test_metadata_storage(self, temp_cache):
        """Test storing metadata with cache entries."""
        file_hash = "test_hash"
        metadata = {"purpose": "assistants", "tool": "code_interpreter"}

        temp_cache.store(
            file_hash, "file-123", 1024, int(time.time()), metadata
        )

        # Should still lookup correctly
        assert temp_cache.lookup(file_hash) == "file-123"

    def test_different_hash_algorithms(self):
        """Test different hash algorithms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "test_cache_md5.db"

            # Test MD5
            cache_md5 = UploadCache(cache_path, "md5")

            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(b"test content")
                file_path = Path(f.name)

            try:
                hash_md5 = cache_md5.compute_file_hash(file_path)
                assert len(hash_md5) == 32  # MD5 is 32 chars

                # Store and retrieve
                cache_md5.store(hash_md5, "file-md5", 1024, int(time.time()))
                assert cache_md5.lookup(hash_md5) == "file-md5"
            finally:
                file_path.unlink()

    def test_ttl_preservation(self, temp_cache):
        """Test files within TTL are preserved."""
        file_id = "file-123"

        # Store entry (created_at = now)
        temp_cache.store("hash123", file_id, 1024, int(time.time()))

        # Test within TTL (14 days)
        assert temp_cache.is_file_cached_and_valid(file_id, 14) is True

        # Test within shorter TTL (1 day)
        assert temp_cache.is_file_cached_and_valid(file_id, 1) is True

        # Test with very short TTL but still valid
        assert (
            temp_cache.is_file_cached_and_valid(file_id, 0) is False
        )  # 0 days = immediate expiration

    def test_ttl_expiration(self, temp_cache):
        """Test files beyond TTL are expired."""
        file_id = "file-456"

        # Store entry with old timestamp (simulate 30 days ago)
        old_timestamp = int(time.time()) - (30 * 86400)  # 30 days ago

        # Manually insert with old timestamp
        with temp_cache._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO files (hash, file_id, algo, size, mtime, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "hash456",
                    file_id,
                    "sha256",
                    1024,
                    int(time.time()),
                    old_timestamp,
                ),
            )
            conn.commit()

        # Test beyond TTL (14 days)
        assert temp_cache.is_file_cached_and_valid(file_id, 14) is False

        # Test with longer TTL (should still be valid)
        assert temp_cache.is_file_cached_and_valid(file_id, 45) is True

    def test_404_cache_cleanup(self, temp_cache):
        """Test cache cleanup when files already deleted."""
        file_id = "file-404"

        # Store entry
        temp_cache.store("hash404", file_id, 1024, int(time.time()))

        # Verify it exists
        assert temp_cache.lookup("hash404") == file_id

        # Clean up by file_id (simulates 404 cleanup)
        temp_cache.invalidate_by_file_id(file_id)

        # Should be gone
        assert temp_cache.lookup("hash404") is None

        # Second cleanup should be safe (no error)
        temp_cache.invalidate_by_file_id(file_id)

    def test_last_accessed_update(self, temp_cache):
        """Test last_accessed timestamp update for LRU-like behavior."""
        file_id = "file-lru"

        # Store entry
        temp_cache.store("hashlru", file_id, 1024, int(time.time()))

        # Update last_accessed
        before_update = time.time()
        temp_cache.update_last_accessed(file_id)
        after_update = time.time()

        # Verify last_accessed was updated
        with temp_cache._get_connection() as conn:
            result = conn.execute(
                "SELECT last_accessed FROM files WHERE file_id = ?", (file_id,)
            ).fetchone()

            assert result is not None
            last_accessed = result["last_accessed"]
            assert before_update <= last_accessed <= after_update

    def test_get_created_at(self, temp_cache):
        """Test retrieving creation timestamp."""
        file_id = "file-created"
        created_time = int(time.time())

        # Store entry
        temp_cache.store("hashcreated", file_id, 1024, created_time)

        # Get created_at timestamp
        retrieved_time = temp_cache.get_created_at(file_id)
        assert retrieved_time == created_time

        # Test non-existent file
        assert temp_cache.get_created_at("nonexistent") is None

    def test_concurrent_cache_access(self, temp_cache):
        """Test two processes accessing same cache simultaneously."""
        results = []

        def cache_worker(worker_id):
            """Worker function that stores and retrieves cache entries."""
            try:
                # Store entry
                file_id = f"file-{worker_id}"
                file_hash = f"hash-{worker_id}"
                temp_cache.store(file_hash, file_id, 1024, int(time.time()))

                # Retrieve entry
                retrieved = temp_cache.lookup(file_hash)
                results.append((worker_id, retrieved == file_id))

                # Test TTL validation
                valid = temp_cache.is_file_cached_and_valid(file_id, 14)
                results.append((f"{worker_id}-ttl", valid))

            except Exception as e:
                results.append((worker_id, f"ERROR: {e}"))

        # Run multiple workers concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=cache_worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify all operations succeeded
        for worker_id, success in results:
            assert success is True, f"Worker {worker_id} failed"

    def test_cache_corruption_handling(self, temp_cache):
        """Test handling of database corruption."""
        # This is hard to test directly, but we can test error handling
        with patch.object(temp_cache, "_get_connection") as mock_conn:
            mock_conn.side_effect = Exception("Database corrupted")

            # Should not raise exception, just return None
            result = temp_cache.lookup("any_hash")
            assert result is None
