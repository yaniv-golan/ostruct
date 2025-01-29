"""Cache management for file content.

This module provides a thread-safe cache manager for file content
with LRU eviction and automatic invalidation on file changes.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from cachetools import LRUCache
from cachetools.keys import hashkey

logger = logging.getLogger(__name__)

# Type alias for cache keys
CacheKey = Tuple[Any, ...]


@dataclass(frozen=True)
class CacheEntry:
    """Represents a cached file entry.

    Note: This class is immutable (frozen) to ensure thread safety
    when used as a cache value.
    """

    content: str
    encoding: Optional[str]
    hash_value: Optional[str]
    mtime_ns: int  # Nanosecond precision mtime
    size: int  # Actual file size from stat


class FileCache:
    """Thread-safe LRU cache for file content with size limit."""

    def __init__(self, max_size_bytes: int = 50 * 1024 * 1024):  # 50MB default
        """Initialize cache with maximum size in bytes.

        Args:
            max_size_bytes: Maximum cache size in bytes
        """
        self._max_size = max_size_bytes
        self._current_size = 0
        self._cache: LRUCache[CacheKey, CacheEntry] = LRUCache(maxsize=1024)
        logger.debug(
            "Initialized FileCache with max_size=%d bytes, maxsize=%d entries",
            max_size_bytes,
            1024,
        )

    def _remove_entry(self, key: CacheKey) -> None:
        """Remove entry from cache and update size.

        Args:
            key: Cache key to remove
        """
        entry = self._cache.get(key)
        if entry is not None:
            self._current_size -= entry.size
            logger.debug(
                "Removed cache entry: key=%s, size=%d, new_total_size=%d",
                key,
                entry.size,
                self._current_size,
            )
        self._cache.pop(key, None)

    def get(
        self, path: str, current_mtime_ns: int, current_size: int
    ) -> Optional[CacheEntry]:
        """Get cache entry if it exists and is valid.

        Args:
            path: Absolute path to the file
            current_mtime_ns: Current modification time in nanoseconds
            current_size: Current file size in bytes

        Returns:
            CacheEntry if valid cache exists, None otherwise
        """
        key = hashkey(path)
        entry = self._cache.get(key)

        if entry is None:
            logger.debug("Cache miss for %s: no entry found", path)
            return None

        # Check if file has been modified using both mtime and size
        if entry.mtime_ns != current_mtime_ns or entry.size != current_size:
            logger.info(
                "Cache invalidated for %s: mtime_ns=%d->%d (%s), size=%d->%d (%s)",
                path,
                entry.mtime_ns,
                current_mtime_ns,
                "changed" if entry.mtime_ns != current_mtime_ns else "same",
                entry.size,
                current_size,
                "changed" if entry.size != current_size else "same",
            )
            self._remove_entry(key)
            return None

        logger.debug(
            "Cache hit for %s: mtime_ns=%d, size=%d",
            path,
            entry.mtime_ns,
            entry.size,
        )
        return entry

    def put(
        self,
        path: str,
        content: str,
        encoding: Optional[str],
        hash_value: Optional[str],
        mtime_ns: int,
        size: int,
    ) -> None:
        """Add or update cache entry.

        Args:
            path: Absolute path to the file
            content: File content
            encoding: File encoding
            hash_value: Content hash
            mtime_ns: File modification time in nanoseconds
            size: File size in bytes from stat
        """
        if size > self._max_size:
            logger.warning(
                "File %s size (%d bytes) exceeds cache max size (%d bytes)",
                path,
                size,
                self._max_size,
            )
            return

        key = hashkey(path)
        self._remove_entry(key)

        entry = CacheEntry(content, encoding, hash_value, mtime_ns, size)

        # Evict entries if needed
        evicted_count = 0
        while self._current_size + size > self._max_size and self._cache:
            evicted_key, evicted = self._cache.popitem()
            self._current_size -= evicted.size
            evicted_count += 1
            logger.debug(
                "Evicted cache entry: key=%s, size=%d, new_total_size=%d",
                evicted_key,
                evicted.size,
                self._current_size,
            )

        if evicted_count > 0:
            logger.info(
                "Evicted %d entries to make room for %s (size=%d)",
                evicted_count,
                path,
                size,
            )

        self._cache[key] = entry
        self._current_size += size
        logger.debug(
            "Added cache entry: path=%s, size=%d, total_size=%d/%d",
            path,
            size,
            self._current_size,
            self._max_size,
        )
