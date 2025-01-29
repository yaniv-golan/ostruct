"""Tests for cache manager implementation."""

import dataclasses
import os
import time
from typing import Generator

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_filesystem_unittest import Patcher
from typing_extensions import TypeAlias

from ostruct.cli.cache_manager import CacheEntry, FileCache

# Type alias for the fixture
FSFixture: TypeAlias = Generator[FakeFilesystem, None, None]


@pytest.fixture  # type: ignore[misc] # Decorator is typed in pytest's stub
def fs() -> FSFixture:
    """Fixture to set up fake filesystem."""
    with Patcher() as patcher:
        fs = patcher.fs
        assert fs is not None  # Type assertion for mypy
        yield fs


def test_cache_entry_immutability() -> None:
    """Test that CacheEntry is immutable."""
    entry = CacheEntry(
        content="test",
        encoding="utf-8",
        hash_value="hash",
        mtime_ns=123_000_000_000,  # nanoseconds
        size=4,
    )

    # Verify we can't modify attributes
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.content = "new"  # type: ignore
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.encoding = "ascii"  # type: ignore
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.hash_value = "new_hash"  # type: ignore


def test_cache_basic_operations(fs: FakeFilesystem) -> None:
    """Test basic cache operations."""
    cache = FileCache(max_size_bytes=1024)  # Small cache for testing

    # Create test file
    content = "test content"
    fs.create_file("/test.txt", contents=content)
    stats = os.stat("/test.txt")

    # Test cache miss
    assert cache.get("/test.txt", stats.st_mtime_ns, stats.st_size) is None

    # Test cache put and hit
    cache.put(
        "/test.txt", content, "utf-8", "hash", stats.st_mtime_ns, stats.st_size
    )
    entry = cache.get("/test.txt", stats.st_mtime_ns, stats.st_size)
    assert entry is not None
    assert entry.content == content
    assert entry.encoding == "utf-8"
    assert entry.hash_value == "hash"
    assert entry.mtime_ns == stats.st_mtime_ns
    assert entry.size == stats.st_size


def test_cache_size_limit(fs: FakeFilesystem) -> None:
    """Test cache size limiting."""
    # Create cache with 100 byte limit
    cache = FileCache(max_size_bytes=100)

    # Create test files
    fs.create_file("/small.txt", contents="small")
    fs.create_file("/large.txt", contents="x" * 200)  # Exceeds cache size

    small_stats = os.stat("/small.txt")
    large_stats = os.stat("/large.txt")

    # Small file should be cached
    cache.put(
        "/small.txt",
        "small",
        "utf-8",
        "hash",
        small_stats.st_mtime_ns,
        small_stats.st_size,
    )
    assert (
        cache.get("/small.txt", small_stats.st_mtime_ns, small_stats.st_size)
        is not None
    )

    # Large file should be rejected
    large_content = "x" * 200
    cache.put(
        "/large.txt",
        large_content,
        "utf-8",
        "hash",
        large_stats.st_mtime_ns,
        large_stats.st_size,
    )
    assert (
        cache.get("/large.txt", large_stats.st_mtime_ns, large_stats.st_size)
        is None
    )


def test_cache_lru_eviction(fs: FakeFilesystem) -> None:
    """Test LRU eviction behavior."""
    # Create cache with size limit that can hold 2 small files
    # Each file is ~8 bytes (content1, content2, content3)
    cache = FileCache(max_size_bytes=16)  # Only fits 2 files

    # Create test files
    files = ["/file1.txt", "/file2.txt", "/file3.txt"]
    stats_list = []

    for i, path in enumerate(files, 1):
        content = f"content{i}"
        fs.create_file(path, contents=content)
        stats = os.stat(path)
        stats_list.append(stats)
        cache.put(
            path,
            content,
            "utf-8",
            f"hash{i}",
            stats.st_mtime_ns,
            stats.st_size,
        )
        time.sleep(0.01)  # Ensure different mtimes

    # First file should be evicted due to size limit
    assert (
        cache.get(files[0], stats_list[0].st_mtime_ns, stats_list[0].st_size)
        is None
    )
    # Later files should still be cached
    assert (
        cache.get(files[1], stats_list[1].st_mtime_ns, stats_list[1].st_size)
        is not None
    )
    assert (
        cache.get(files[2], stats_list[2].st_mtime_ns, stats_list[2].st_size)
        is not None
    )


def test_cache_modification_detection(fs: FakeFilesystem) -> None:
    """Test detection of file modifications."""
    cache = FileCache()

    # Create and cache file
    original_content = "original"
    fs.create_file("/test.txt", contents=original_content)
    original_stats = os.stat("/test.txt")
    cache.put(
        "/test.txt",
        original_content,
        "utf-8",
        "hash1",
        original_stats.st_mtime_ns,
        original_stats.st_size,
    )

    # Modify file
    time.sleep(0.01)  # Ensure different mtime
    fs.remove("/test.txt")  # Remove first
    modified_content = "modified"
    fs.create_file("/test.txt", contents=modified_content)  # Then create new
    new_stats = os.stat("/test.txt")

    # Cache should detect modification
    assert original_stats.st_mtime_ns != new_stats.st_mtime_ns
    assert (
        cache.get("/test.txt", new_stats.st_mtime_ns, new_stats.st_size)
        is None
    )


def test_cache_concurrent_access() -> None:
    """Test concurrent cache access."""
    import random
    import threading

    cache = FileCache(max_size_bytes=1000)
    errors: list[Exception] = []

    def cache_operation(thread_id: int) -> None:
        """Perform random cache operations."""
        try:
            for _ in range(100):
                path = f"/file{random.randint(1, 5)}.txt"
                mtime_ns = (
                    random.randint(1, 1000) * 1_000_000_000
                )  # Convert to ns
                size = random.randint(10, 100)  # Random file size

                if random.random() < 0.5:
                    # Read operation
                    cache.get(path, mtime_ns, size)
                else:
                    # Write operation
                    content = f"content{thread_id}"
                    cache.put(
                        path,
                        content,
                        "utf-8",
                        f"hash{thread_id}",
                        mtime_ns,
                        len(content.encode("utf-8")),  # Actual content size
                    )
        except Exception as e:
            errors.append(e)

    # Create and start threads
    threads = [
        threading.Thread(target=cache_operation, args=(i,)) for i in range(10)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Check for errors
    assert not errors, f"Encountered errors during concurrent access: {errors}"


def test_cache_key_collisions() -> None:
    """Test handling of potential key collisions."""
    cache = FileCache()
    mtime_ns = int(time.time() * 1_000_000_000)  # Convert to nanoseconds

    # Test paths that might hash similarly
    paths = [
        "/test/path/file.txt",
        "/test/path/file.txt/",  # Trailing slash
        "//test/path/file.txt",  # Double slash
        "/test//path/file.txt",
        "/test/./path/file.txt",
        "/test/path/../path/file.txt",
    ]

    # Add each path to cache
    for i, path in enumerate(paths):
        content = f"content{i}"
        size = len(content.encode("utf-8"))
        cache.put(path, content, "utf-8", f"hash{i}", mtime_ns, size)

    # Verify each path has correct content
    for i, path in enumerate(paths):
        content = f"content{i}"
        size = len(content.encode("utf-8"))
        entry = cache.get(path, mtime_ns, size)
        assert entry is not None
        assert entry.content == content
