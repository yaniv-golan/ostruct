"""Integration tests for SharedUploadManager TTL functionality."""

import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.ostruct.cli.upload_cache import UploadCache
from src.ostruct.cli.upload_manager import SharedUploadManager


@pytest.mark.asyncio
@pytest.mark.no_fs
class TestSharedUploadManagerTTL:
    """Test SharedUploadManager TTL integration."""

    @pytest.fixture
    def mock_client(self):
        """Create mock OpenAI client."""
        client = AsyncMock()
        client.files.delete = AsyncMock()
        return client

    @pytest.fixture
    def temp_cache(self):
        """Create temporary cache for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "test_cache.db"
            cache = UploadCache(cache_path)
            yield cache

    @pytest.fixture
    def upload_manager_with_cache(self, mock_client, temp_cache):
        """Create SharedUploadManager with cache."""
        manager = SharedUploadManager(mock_client, cache=temp_cache)
        return manager

    async def test_cleanup_preserves_cached_files_within_ttl(
        self, upload_manager_with_cache, mock_client
    ):
        """Test that cached files within TTL are preserved during cleanup."""
        manager = upload_manager_with_cache

        # Add file IDs to cleanup list
        file_id_cached = "file-cached-123"
        file_id_uncached = "file-uncached-456"

        manager._all_uploaded_ids.add(file_id_cached)
        manager._all_uploaded_ids.add(file_id_uncached)

        # Cache one file (simulate it was uploaded and cached)
        manager._cache.store("hash123", file_id_cached, 1024, int(time.time()))

        # Run cleanup with 14-day TTL
        await manager.cleanup_uploads(ttl_days=14)

        # Cached file should NOT be deleted
        mock_client.files.delete.assert_called_once_with(file_id_uncached)

        # Verify cached file was not in delete calls
        delete_calls = [
            call.args[0] for call in mock_client.files.delete.call_args_list
        ]
        assert file_id_cached not in delete_calls
        assert file_id_uncached in delete_calls

    async def test_cleanup_deletes_expired_cached_files(
        self, upload_manager_with_cache, mock_client
    ):
        """Test that cached files beyond TTL are deleted."""
        manager = upload_manager_with_cache

        file_id_expired = "file-expired-789"
        manager._all_uploaded_ids.add(file_id_expired)

        # Cache file with old timestamp (30 days ago)
        old_timestamp = int(time.time()) - (30 * 86400)
        with manager._cache._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO files (hash, file_id, algo, size, mtime, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "hashexpired",
                    file_id_expired,
                    "sha256",
                    1024,
                    int(time.time()),
                    old_timestamp,
                ),
            )
            conn.commit()

        # Run cleanup with 14-day TTL
        await manager.cleanup_uploads(ttl_days=14)

        # Expired file should be deleted
        mock_client.files.delete.assert_called_once_with(file_id_expired)

    async def test_cleanup_handles_404_errors(
        self, upload_manager_with_cache, mock_client
    ):
        """Test that 404 errors during cleanup are handled gracefully."""
        manager = upload_manager_with_cache

        file_id_404 = "file-404-missing"
        manager._all_uploaded_ids.add(file_id_404)

        # Cache the file
        manager._cache.store("hash404", file_id_404, 1024, int(time.time()))

        # Mock 404 error
        mock_client.files.delete.side_effect = Exception("404 Not Found")

        # Run cleanup (should not raise exception)
        await manager.cleanup_uploads(ttl_days=0)  # Force deletion attempt

        # Verify cache entry was cleaned up
        assert manager._cache.lookup("hash404") is None

    async def test_cleanup_updates_last_accessed(
        self, upload_manager_with_cache, mock_client
    ):
        """Test that preserved files have their last_accessed updated."""
        manager = upload_manager_with_cache

        file_id = "file-lru-test"
        manager._all_uploaded_ids.add(file_id)

        # Cache the file
        manager._cache.store("hashlru", file_id, 1024, int(time.time()))

        # Record time before cleanup
        before_cleanup = time.time()

        # Run cleanup (should preserve file)
        await manager.cleanup_uploads(ttl_days=14)

        # Record time after cleanup
        after_cleanup = time.time()

        # Verify last_accessed was updated
        with manager._cache._get_connection() as conn:
            result = conn.execute(
                "SELECT last_accessed FROM files WHERE file_id = ?", (file_id,)
            ).fetchone()

            assert result is not None
            last_accessed = result["last_accessed"]
            assert before_cleanup <= last_accessed <= after_cleanup

    async def test_cleanup_with_zero_ttl_deletes_all(
        self, upload_manager_with_cache, mock_client
    ):
        """Test that TTL=0 forces immediate deletion of all files."""
        manager = upload_manager_with_cache

        file_id_cached = "file-cached-immediate"
        manager._all_uploaded_ids.add(file_id_cached)

        # Cache the file (recent)
        manager._cache.store(
            "hashimmediate", file_id_cached, 1024, int(time.time())
        )

        # Run cleanup with TTL=0 (immediate deletion)
        await manager.cleanup_uploads(ttl_days=0)

        # Even cached file should be deleted with TTL=0
        mock_client.files.delete.assert_called_once_with(file_id_cached)

    async def test_cleanup_without_cache_deletes_all(self, mock_client):
        """Test that cleanup without cache deletes all files (legacy behavior)."""
        manager = SharedUploadManager(mock_client)
        # No cache set (manager._cache is None)

        file_id = "file-no-cache"
        manager._all_uploaded_ids.add(file_id)

        # Run cleanup
        await manager.cleanup_uploads(ttl_days=14)

        # File should be deleted (no cache to preserve it)
        mock_client.files.delete.assert_called_once_with(file_id)

    async def test_cleanup_logs_summary(
        self, upload_manager_with_cache, mock_client, caplog
    ):
        """Test that cleanup logs provide clear summary."""
        import logging

        caplog.set_level(logging.DEBUG)

        manager = upload_manager_with_cache

        # Add mixed files
        file_cached = "file-cached-log"
        file_uncached = "file-uncached-log"

        manager._all_uploaded_ids.add(file_cached)
        manager._all_uploaded_ids.add(file_uncached)

        # Cache one file
        manager._cache.store("hashlog", file_cached, 1024, int(time.time()))

        # Run cleanup
        await manager.cleanup_uploads(ttl_days=14)

        # Verify log messages
        log_messages = [record.message for record in caplog.records]

        # Should have preservation and deletion logs
        preserved_logs = [
            msg for msg in log_messages if "Preserving cached file" in msg
        ]
        deleted_logs = [
            msg for msg in log_messages if "Successfully deleted" in msg
        ]
        summary_logs = [
            msg for msg in log_messages if "Cleanup complete" in msg
        ]

        assert len(preserved_logs) >= 1
        assert len(deleted_logs) >= 1
        assert len(summary_logs) >= 1

    async def test_performance_with_large_file_list(
        self, upload_manager_with_cache, mock_client
    ):
        """Test cleanup performance with large number of files."""
        manager = upload_manager_with_cache

        # Add many files (simulate realistic usage)
        num_files = 100
        for i in range(num_files):
            file_id = f"file-perf-{i}"
            manager._all_uploaded_ids.add(file_id)

            # Cache every other file
            if i % 2 == 0:
                manager._cache.store(
                    f"hash{i}", file_id, 1024, int(time.time())
                )

        # Measure cleanup time
        start_time = time.time()
        await manager.cleanup_uploads(ttl_days=14)
        cleanup_time = time.time() - start_time

        # Should complete reasonably quickly (under 1 second for 100 files)
        assert cleanup_time < 1.0

        # Verify correct number of deletions (50 uncached files)
        assert mock_client.files.delete.call_count == 50
