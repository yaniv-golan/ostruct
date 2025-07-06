"""Upload cache for persistent file upload tracking."""

import hashlib
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class UploadCache:
    """Persistent cache for tracking uploaded files by content hash."""

    def __init__(self, cache_path: Path, hash_algo: str = "sha256") -> None:
        """Initialize cache with database path and hash algorithm."""
        self.cache_path = Path(cache_path)
        self.hash_algo = hash_algo
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Create database and tables if they don't exist."""
        # Ensure parent directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA foreign_keys = ON")

                # Create base table without last_accessed (for migration compatibility)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS files (
                        hash        TEXT PRIMARY KEY,
                        file_id     TEXT NOT NULL,
                        algo        TEXT NOT NULL,
                        size        INTEGER NOT NULL,
                        mtime       INTEGER NOT NULL,
                        created_at  INTEGER NOT NULL,
                        metadata    JSON
                    )
                """
                )

                # Add last_accessed column if it doesn't exist (proper migration)
                try:
                    conn.execute(
                        "ALTER TABLE files ADD COLUMN last_accessed INTEGER"
                    )
                    logger.debug(
                        "[cache] Added last_accessed column to existing table"
                    )
                except sqlite3.OperationalError:
                    # Column already exists, which is expected
                    logger.debug("[cache] last_accessed column already exists")

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_files_created
                    ON files(created_at)
                """
                )
        except sqlite3.DatabaseError as e:
            # Handle actual database corruption (not just missing files)
            if self.cache_path.exists():
                logger.warning(f"[cache] Database corruption detected: {e}")
                logger.info("[cache] Recreating corrupted database")

                # Remove corrupted database file
                self.cache_path.unlink()

                # Recreate database
                with self._get_connection() as conn:
                    conn.execute("PRAGMA journal_mode = WAL")
                    conn.execute("PRAGMA foreign_keys = ON")

                    conn.execute(
                        """
                        CREATE TABLE files (
                            hash        TEXT PRIMARY KEY,
                            file_id     TEXT NOT NULL,
                            algo        TEXT NOT NULL,
                            size        INTEGER NOT NULL,
                            mtime       INTEGER NOT NULL,
                            created_at  INTEGER NOT NULL,
                            last_accessed INTEGER,
                            metadata    JSON
                        )
                    """
                    )

                    conn.execute(
                        """
                        CREATE INDEX idx_files_created
                        ON files(created_at)
                    """
                    )

                    logger.info("[cache] Database recreated successfully")
            else:
                # File doesn't exist, this is a normal case - re-raise
                raise

    @contextmanager
    def _get_connection(self) -> Any:
        """Get database connection with proper transaction handling."""
        conn = sqlite3.connect(str(self.cache_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute hash of file contents with optimized buffering."""
        hasher = hashlib.new(self.hash_algo)

        # Use larger buffer for better I/O performance
        buffer_size = 1024 * 1024  # 1MB buffer
        buffer = bytearray(buffer_size)

        with open(file_path, "rb") as f:
            while True:
                bytes_read = f.readinto(buffer)
                if not bytes_read:
                    break
                hasher.update(buffer[:bytes_read])

        return hasher.hexdigest()

    def lookup(self, file_hash: str) -> Optional[str]:
        """Look up file_id by hash. Returns None if not found."""
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT file_id FROM files WHERE hash = ? AND algo = ?",
                    (file_hash, self.hash_algo),
                ).fetchone()

                if result:
                    file_id = str(result["file_id"])
                    logger.debug(
                        f"[cache] Cache hit: {file_hash[:8]}... -> {file_id}"
                    )
                    return file_id

                logger.debug(f"[cache] Cache miss: {file_hash[:8]}...")
                return None
        except Exception as e:
            logger.warning(f"[cache] Cache lookup failed: {e}")
            return None

    def store(
        self,
        file_hash: str,
        file_id: str,
        size: int,
        mtime: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store file upload record in cache."""
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                current_time = int(time.time())
                conn.execute(
                    """
                    INSERT OR REPLACE INTO files
                    (hash, file_id, algo, size, mtime, created_at, last_accessed, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        file_hash,
                        file_id,
                        self.hash_algo,
                        size,
                        mtime,
                        current_time,
                        current_time,  # Set last_accessed to creation time
                        json.dumps(metadata) if metadata else None,
                    ),
                )
                conn.commit()
                logger.debug(
                    f"[cache] Stored: {file_hash[:8]}... -> {file_id}"
                )
        except Exception as e:
            logger.warning(f"[cache] Failed to store cache entry: {e}")

    def is_file_changed(
        self, file_path: Path, cached_size: int, cached_mtime: int
    ) -> bool:
        """Check if file has changed since caching."""
        try:
            stat = file_path.stat()
            current_size = stat.st_size
            current_mtime = int(stat.st_mtime)

            # If size or mtime differs, file has changed
            if current_size != cached_size or current_mtime != cached_mtime:
                logger.debug(
                    f"[cache] File changed: {file_path} "
                    f"(size: {cached_size} -> {current_size}, "
                    f"mtime: {cached_mtime} -> {current_mtime})"
                )
                return True

            # If size and mtime are the same, the file likely hasn't changed
            # but we could add additional checks here if needed
            return False
        except OSError as e:
            logger.warning(f"[cache] Cannot stat file {file_path}: {e}")
            return True  # Assume changed if we can't check

    def lookup_with_validation(
        self, file_path: Path, file_hash: str
    ) -> Optional[str]:
        """Look up file_id with size/mtime validation."""
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT file_id, size, mtime FROM files WHERE hash = ? AND algo = ?",
                    (file_hash, self.hash_algo),
                ).fetchone()

                if not result:
                    logger.debug(
                        f"[cache] No cache entry for {file_hash[:8]}..."
                    )
                    return None

                # Validate file hasn't changed
                if self.is_file_changed(
                    file_path, result["size"], result["mtime"]
                ):
                    # File changed, invalidate cache entry
                    logger.info(
                        f"[cache] File {file_path} changed, invalidating cache"
                    )
                    self.invalidate(file_hash)
                    return None

                file_id = str(result["file_id"])
                logger.debug(
                    f"[cache] Validated hit: {file_hash[:8]}... -> {file_id}"
                )
                return file_id
        except Exception as e:
            logger.warning(f"[cache] Cache validation lookup failed: {e}")
            return None

    def invalidate(self, file_hash: str) -> None:
        """Remove entry from cache."""
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM files WHERE hash = ?", (file_hash,))
                conn.commit()
                logger.debug(f"[cache] Invalidated: {file_hash[:8]}...")
        except Exception as e:
            logger.warning(f"[cache] Failed to invalidate cache entry: {e}")

    def get_created_at(self, file_id: str) -> Optional[int]:
        """Get creation timestamp for a file_id."""
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT created_at FROM files WHERE file_id = ?",
                    (file_id,),
                ).fetchone()
                if result:
                    created_at = int(result["created_at"])
                    logger.debug(
                        f"[cache] Found creation time for {file_id}: {created_at}"
                    )
                    return created_at
                logger.debug(f"[cache] No creation time found for {file_id}")
                return None
        except Exception as e:
            logger.warning(f"[cache] Failed to get creation time: {e}")
            return None

    def is_file_cached_and_valid(self, file_id: str, ttl_days: int) -> bool:
        """Check if file is cached and within TTL."""
        try:
            created_at = self.get_created_at(file_id)
            if created_at is None:
                logger.debug(f"[cache] File {file_id} not in cache")
                return False

            if ttl_days <= 0:
                logger.debug(
                    f"[cache] TTL disabled (0 days), file {file_id} not valid for preservation"
                )
                return False

            age_seconds = time.time() - created_at
            age_days = age_seconds / (24 * 3600)
            ttl_exceeded = age_days > ttl_days

            logger.debug(
                f"[cache] File {file_id} age: {age_days:.1f}d, TTL: {ttl_days}d, expired: {ttl_exceeded}"
            )

            # Don't automatically delete expired entries here - just return status
            # Deletion should be done explicitly by cleanup operations
            return not ttl_exceeded
        except Exception as e:
            logger.warning(f"[cache] Failed to check TTL for {file_id}: {e}")
            return False

    def invalidate_by_file_id(self, file_id: str) -> None:
        """Remove entry from cache by file_id."""
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                result = conn.execute(
                    "SELECT hash FROM files WHERE file_id = ?", (file_id,)
                ).fetchone()
                if result:
                    file_hash = result["hash"]
                    conn.execute(
                        "DELETE FROM files WHERE file_id = ?", (file_id,)
                    )
                    conn.commit()
                    logger.debug(
                        f"[cache] Invalidated by file_id: {file_id} ({file_hash[:8]}...)"
                    )
                else:
                    logger.debug(
                        f"[cache] File {file_id} not found for invalidation"
                    )
        except Exception as e:
            logger.warning(
                f"[cache] Failed to invalidate by file_id {file_id}: {e}"
            )

    def update_last_accessed(self, file_id: str) -> None:
        """Update last accessed timestamp for LRU behavior."""
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                # Use higher precision timestamp to avoid test timing issues
                current_timestamp = time.time()
                conn.execute(
                    "UPDATE files SET last_accessed = ? WHERE file_id = ?",
                    (current_timestamp, file_id),
                )
                conn.commit()
                logger.debug(f"[cache] Updated last_accessed for {file_id}")
        except Exception as e:
            logger.warning(
                f"[cache] Failed to update last_accessed for {file_id}: {e}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics including TTL information."""
        try:
            with self._get_connection() as conn:
                # Basic stats
                result = conn.execute(
                    "SELECT COUNT(*) as count FROM files"
                ).fetchone()
                total_files = result["count"] if result else 0

                # Age distribution stats
                current_time = int(time.time())
                age_stats = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        AVG(? - created_at) / 86400.0 as avg_age_days,
                        MIN(? - created_at) / 86400.0 as min_age_days,
                        MAX(? - created_at) / 86400.0 as max_age_days,
                        COUNT(CASE WHEN last_accessed IS NULL THEN 1 END) as never_accessed
                    FROM files
                """,
                    (current_time, current_time, current_time),
                ).fetchone()

                # TTL expiry stats (using default 14 days)
                from .cache_config import DEFAULT_CACHE_TTL_DAYS

                ttl_seconds = DEFAULT_CACHE_TTL_DAYS * 24 * 3600
                expired_count = conn.execute(
                    """
                    SELECT COUNT(*) as count FROM files
                    WHERE (? - created_at) > ?
                """,
                    (current_time, ttl_seconds),
                ).fetchone()

                # Get size on disk
                db_size = (
                    self.cache_path.stat().st_size
                    if self.cache_path.exists()
                    else 0
                )

                return {
                    # Backward compatibility - keep both keys
                    "entries": total_files,
                    "total_entries": total_files,
                    "path": str(self.cache_path),  # Backward compatibility
                    "cache_path": str(self.cache_path),
                    "hash_algorithm": self.hash_algo,
                    "size_bytes": db_size,
                    "age_stats": {
                        "average_age_days": (
                            float(age_stats["avg_age_days"])
                            if age_stats["avg_age_days"]
                            else 0
                        ),
                        "min_age_days": (
                            float(age_stats["min_age_days"])
                            if age_stats["min_age_days"]
                            else 0
                        ),
                        "max_age_days": (
                            float(age_stats["max_age_days"])
                            if age_stats["max_age_days"]
                            else 0
                        ),
                        "never_accessed_count": age_stats["never_accessed"]
                        or 0,
                    },
                    "ttl_stats": {
                        "default_ttl_days": DEFAULT_CACHE_TTL_DAYS,
                        "expired_entries": (
                            expired_count["count"] if expired_count else 0
                        ),
                        "active_entries": total_files
                        - (expired_count["count"] if expired_count else 0),
                    },
                }
        except Exception as e:
            logger.warning(f"[cache] Failed to get cache stats: {e}")
            return {"error": str(e), "entries": 0, "total_entries": 0}
