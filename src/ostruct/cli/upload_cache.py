"""Upload cache for persistent file upload tracking."""

import hashlib
import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CachedFileInfo:
    """Information about a cached file."""

    file_id: str
    hash: str
    size: int
    path: str
    created_at: int
    metadata: Optional[Dict[str, Any]] = None


def generate_label(file_hash: str, label_style: str = "alpha") -> str:
    """Generate deterministic label for a file hash.

    Args:
        file_hash: SHA-256 hash of file content
        label_style: "alpha" for FILE A/B/C or "filename" for basename

    Returns:
        Deterministic label string
    """
    if label_style == "filename":
        # Will be overridden with actual filename in store()
        return "PLACEHOLDER"

    # Alpha style: FILE A, FILE B, ..., FILE Z, AA, AB, etc.
    index = (
        int(file_hash[:8], 16) % 1000
    )  # Use hash for deterministic ordering
    if index < 26:
        return f"FILE {chr(65 + index)}"
    else:
        first = chr(65 + (index // 26) - 1)
        second = chr(65 + (index % 26))
        return f"FILE {first}{second}"


class UploadCache:
    """Persistent cache for tracking uploaded files by content hash."""

    def __init__(self, cache_path: Path, hash_algo: str = "sha256") -> None:
        """Initialize cache with database path and hash algorithm."""
        self.cache_path = Path(cache_path)
        self.hash_algo = hash_algo
        self._ensure_db_exists()

        # Add thread-safe locking for cache operations
        self._lock = threading.RLock()
        self._file_locks: Dict[str, threading.RLock] = {}

    def _get_file_lock(self, file_hash: str) -> threading.RLock:
        """Get or create a per-file lock to prevent race conditions."""
        with self._lock:
            if file_hash not in self._file_locks:
                self._file_locks[file_hash] = threading.RLock()
            return self._file_locks[file_hash]

    def _ensure_db_exists(self) -> None:
        """Create database and tables if they don't exist."""
        # Ensure parent directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA foreign_keys = ON")

                # Create base table with all columns for new databases
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS files (
                        hash        TEXT PRIMARY KEY,
                        file_id     TEXT NOT NULL,
                        algo        TEXT NOT NULL,
                        size        INTEGER NOT NULL,
                        mtime       INTEGER NOT NULL,
                        created_at  INTEGER NOT NULL,
                        metadata    JSON,
                        last_accessed INTEGER,
                        path        TEXT DEFAULT ''
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

                # Add path column if it doesn't exist (proper migration)
                try:
                    conn.execute(
                        "ALTER TABLE files ADD COLUMN path TEXT DEFAULT ''"
                    )
                    logger.debug("[cache] Added path column to existing table")
                except sqlite3.OperationalError:
                    # Column already exists, which is expected
                    logger.debug("[cache] path column already exists")

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
                            metadata    JSON,
                            path        TEXT DEFAULT ''
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

        # Add new tables for vector store support (automatic migration)
        self._add_vector_store_tables()

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
        file_path: Optional[str] = None,
        label_style: str = "alpha",
    ) -> None:
        """Store file upload record in cache with label generation (thread-safe)."""
        # Use per-file locking to prevent race conditions
        file_lock = self._get_file_lock(file_hash)

        with file_lock:
            try:
                if metadata is None:
                    metadata = {}

                # Normalize file path to absolute path for consistent storage
                normalized_path = ""
                if file_path:
                    try:
                        normalized_path = str(Path(file_path).resolve())
                    except Exception as e:
                        logger.warning(
                            f"Failed to resolve path {file_path}: {e}"
                        )
                        normalized_path = file_path

                # Generate label if not already present
                if "label" not in metadata:
                    if label_style == "filename" and file_path:
                        base_label = Path(file_path).stem
                        # Handle collisions by checking existing labels
                        existing_labels = self._get_existing_labels()
                        final_label = base_label
                        collision_count = 0
                        while final_label in existing_labels:
                            collision_count += 1
                            final_label = f"{base_label}-{collision_count}"
                        metadata["label"] = final_label
                    else:
                        metadata["label"] = generate_label(
                            file_hash, label_style
                        )

                    metadata["label_style"] = label_style

                with self._get_connection() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    current_time = int(time.time())
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO files
                        (hash, file_id, algo, size, mtime, created_at, last_accessed, metadata, path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            normalized_path,  # Store the normalized absolute path
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
        """Look up file_id with size/mtime validation (thread-safe)."""
        # Use per-file locking to prevent race conditions
        file_lock = self._get_file_lock(file_hash)

        with file_lock:
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

                    # Validate file hasn't changed (while holding the lock)
                    if self.is_file_changed(
                        file_path, result["size"], result["mtime"]
                    ):
                        # File changed, invalidate cache entry atomically
                        logger.info(
                            f"[cache] File {file_path} changed, invalidating cache"
                        )
                        # Invalidate within the same transaction to prevent race conditions
                        conn.execute("BEGIN IMMEDIATE")
                        conn.execute(
                            "DELETE FROM files WHERE hash = ?", (file_hash,)
                        )
                        conn.commit()
                        logger.debug(
                            f"[cache] Invalidated: {file_hash[:8]}..."
                        )
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

    def cleanup_file_locks(self) -> None:
        """Clean up unused file locks to prevent memory leaks."""
        with self._lock:
            # Get all current file hashes in the cache
            try:
                with self._get_connection() as conn:
                    result = conn.execute(
                        "SELECT DISTINCT hash FROM files WHERE algo = ?",
                        (self.hash_algo,),
                    ).fetchall()

                    active_hashes = {row["hash"] for row in result}

                    # Remove locks for files no longer in cache
                    locks_to_remove = []
                    for file_hash in self._file_locks:
                        if file_hash not in active_hashes:
                            locks_to_remove.append(file_hash)

                    for file_hash in locks_to_remove:
                        del self._file_locks[file_hash]

                    if locks_to_remove:
                        logger.debug(
                            f"[cache] Cleaned up {len(locks_to_remove)} unused file locks"
                        )

            except Exception as e:
                logger.warning(f"[cache] Failed to cleanup file locks: {e}")

    def _add_vector_store_tables(self) -> None:
        """Add vector store tables for automatic migration."""
        try:
            with self._get_connection() as conn:
                # Create vector_stores table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vector_stores (
                        vector_store_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        last_used INTEGER NOT NULL,
                        metadata JSON
                    )
                    """
                )

                # Create file_vector_store_mappings table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS file_vector_store_mappings (
                        file_hash TEXT NOT NULL,
                        vector_store_id TEXT NOT NULL,
                        added_at INTEGER NOT NULL,
                        PRIMARY KEY (file_hash, vector_store_id),
                        FOREIGN KEY (file_hash) REFERENCES files(hash) ON DELETE CASCADE,
                        FOREIGN KEY (vector_store_id) REFERENCES vector_stores(vector_store_id) ON DELETE CASCADE
                    )
                    """
                )

                # Create indexes (using IF NOT EXISTS for safety)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_vector_stores_name ON vector_stores(name)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_vector_stores_last_used ON vector_stores(last_used)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mappings_file_hash ON file_vector_store_mappings(file_hash)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mappings_vector_store ON file_vector_store_mappings(vector_store_id)"
                )

                # Performance optimization: Index on label extraction for large caches (>50k files)
                # Note: Requires SQLite 3.9+ for json_extract support
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_files_label ON files(json_extract(metadata,'$.label'))"
                )

                logger.debug(
                    "[cache] Vector store tables and indexes created/verified"
                )

        except sqlite3.Error as e:
            logger.warning(
                f"[cache] Failed to create vector store tables: {e}"
            )
            # Continue without vector store support - graceful degradation
            logger.info("[cache] Vector store features will be disabled")

    def _get_existing_labels(self) -> Set[str]:
        """Get all existing labels to detect collisions."""
        try:
            with self._get_connection() as conn:
                results = conn.execute(
                    "SELECT metadata FROM files WHERE metadata IS NOT NULL"
                ).fetchall()

                labels = set()
                for row in results:
                    try:
                        meta = json.loads(row["metadata"])
                        if "label" in meta:
                            labels.add(meta["label"])
                    except (json.JSONDecodeError, KeyError):
                        continue
                return labels
        except Exception as e:
            logger.warning(f"Failed to get existing labels: {e}")
            return set()

    def get_label_and_file_id(
        self, file_hash: str
    ) -> Optional[Tuple[str, str]]:
        """Get label and file_id for a file hash."""
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT file_id, metadata FROM files WHERE hash = ? AND algo = ?",
                    (file_hash, self.hash_algo),
                ).fetchone()

                if not result:
                    return None

                try:
                    metadata = (
                        json.loads(result["metadata"])
                        if result["metadata"]
                        else {}
                    )
                    label = metadata.get("label", "UNKNOWN")
                    return (label, result["file_id"])
                except (json.JSONDecodeError, KeyError):
                    return (f"FILE_{file_hash[:8]}", result["file_id"])

        except Exception as e:
            logger.warning(f"Failed to get label and file_id: {e}")
            return None

    def list_all(self) -> List[CachedFileInfo]:
        """List all cached files."""
        try:
            with self._get_connection() as conn:
                results = conn.execute(
                    "SELECT file_id, hash, size, created_at, metadata, path FROM files WHERE algo = ?",
                    (self.hash_algo,),
                ).fetchall()

                files = []
                for row in results:
                    metadata = None
                    if row["metadata"]:
                        try:
                            metadata = json.loads(row["metadata"])
                        except json.JSONDecodeError:
                            pass

                    files.append(
                        CachedFileInfo(
                            file_id=row["file_id"],
                            hash=row["hash"],
                            size=row["size"],
                            path=row["path"] or "",  # Use stored path
                            created_at=row["created_at"],
                            metadata=metadata,
                        )
                    )

                return files
        except Exception as e:
            logger.warning(f"Failed to list all files: {e}")
            return []

    def get_by_file_id(self, file_id: str) -> Optional[CachedFileInfo]:
        """Get cached file info by file_id."""
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT file_id, hash, size, created_at, metadata, path FROM files WHERE file_id = ?",
                    (file_id,),
                ).fetchone()

                if not result:
                    return None

                metadata = None
                if result["metadata"]:
                    try:
                        metadata = json.loads(result["metadata"])
                    except json.JSONDecodeError:
                        pass

                return CachedFileInfo(
                    file_id=result["file_id"],
                    hash=result["hash"],
                    size=result["size"],
                    path=result["path"] or "",  # Use stored path
                    created_at=result["created_at"],
                    metadata=metadata,
                )
        except Exception as e:
            logger.warning(f"Failed to get file by file_id: {e}")
            return None

    def update_metadata(self, file_id: str, metadata: Dict[str, Any]) -> None:
        """Update metadata for a cached file."""
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "UPDATE files SET metadata = ? WHERE file_id = ?",
                    (json.dumps(metadata), file_id),
                )
                conn.commit()
                logger.debug(f"[cache] Updated metadata for {file_id}")
        except Exception as e:
            logger.warning(
                f"[cache] Failed to update metadata for {file_id}: {e}"
            )

    def register_vector_store(
        self,
        vector_store_id: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a vector store in the cache."""
        try:
            with self._get_connection() as conn:
                current_time = int(time.time())
                conn.execute(
                    """
                    INSERT OR REPLACE INTO vector_stores
                    (vector_store_id, name, created_at, last_used, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        vector_store_id,
                        name,
                        current_time,
                        current_time,
                        json.dumps(metadata) if metadata else None,
                    ),
                )
                conn.commit()
                logger.debug(
                    f"[cache] Registered vector store: {name} -> {vector_store_id}"
                )
        except Exception as e:
            logger.warning(f"[cache] Failed to register vector store: {e}")

    def get_vector_store_by_name(self, name: str) -> Optional[str]:
        """Get vector store ID by name."""
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "SELECT vector_store_id FROM vector_stores WHERE name = ?",
                    (name,),
                ).fetchone()
                return result["vector_store_id"] if result else None
        except Exception as e:
            logger.warning(
                f"[cache] Failed to lookup vector store by name: {e}"
            )
            return None

    def add_file_to_vector_store(
        self, file_hash: str, vector_store_id: str
    ) -> None:
        """Add a file to a vector store mapping."""
        try:
            with self._get_connection() as conn:
                current_time = int(time.time())
                conn.execute(
                    """
                    INSERT OR IGNORE INTO file_vector_store_mappings
                    (file_hash, vector_store_id, added_at)
                    VALUES (?, ?, ?)
                    """,
                    (file_hash, vector_store_id, current_time),
                )
                # Update vector store last_used timestamp
                conn.execute(
                    "UPDATE vector_stores SET last_used = ? WHERE vector_store_id = ?",
                    (current_time, vector_store_id),
                )
                conn.commit()
                logger.debug(
                    f"[cache] Added file {file_hash[:8]}... to vector store {vector_store_id}"
                )
        except Exception as e:
            logger.warning(f"[cache] Failed to add file to vector store: {e}")

    def get_files_in_vector_store(self, vector_store_id: str) -> List[str]:
        """Get all file hashes in a vector store."""
        try:
            with self._get_connection() as conn:
                results = conn.execute(
                    "SELECT file_hash FROM file_vector_store_mappings WHERE vector_store_id = ?",
                    (vector_store_id,),
                ).fetchall()
                return [row["file_hash"] for row in results]
        except Exception as e:
            logger.warning(f"[cache] Failed to get files in vector store: {e}")
            return []

    def list_vector_stores(self) -> List[Dict[str, Any]]:
        """List all vector stores with their metadata."""
        try:
            with self._get_connection() as conn:
                results = conn.execute(
                    """
                    SELECT vs.vector_store_id, vs.name, vs.created_at, vs.last_used, vs.metadata,
                           COUNT(fvs.file_hash) as file_count
                    FROM vector_stores vs
                    LEFT JOIN file_vector_store_mappings fvs ON vs.vector_store_id = fvs.vector_store_id
                    GROUP BY vs.vector_store_id, vs.name, vs.created_at, vs.last_used, vs.metadata
                    ORDER BY vs.last_used DESC
                    """
                ).fetchall()

                vector_stores = []
                for row in results:
                    metadata = (
                        json.loads(row["metadata"]) if row["metadata"] else {}
                    )
                    vector_stores.append(
                        {
                            "vector_store_id": row["vector_store_id"],
                            "name": row["name"],
                            "created_at": row["created_at"],
                            "last_used": row["last_used"],
                            "file_count": row["file_count"],
                            "metadata": metadata,
                        }
                    )
                return vector_stores
        except Exception as e:
            logger.warning(f"[cache] Failed to list vector stores: {e}")
            return []
