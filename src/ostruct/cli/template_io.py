"""File I/O operations for template processing.

This module provides functionality for file operations related to template processing:
1. Reading files with encoding detection and caching
2. Extracting metadata from files and templates
3. Managing file content caching and eviction
4. Progress tracking for file operations

Key Components:
    - read_file: Main function for reading files
    - extract_metadata: Extract metadata from files
    - extract_template_metadata: Extract metadata from templates
    - Cache management for file content

Examples:
    Basic file reading:
    >>> file_info = read_file('example.txt')
    >>> print(file_info.name)  # 'example.txt'
    >>> print(file_info.content)  # File contents
    >>> print(file_info.encoding)  # Detected encoding

    Lazy loading:
    >>> file_info = read_file('large_file.txt', lazy=True)
    >>> # Content not loaded yet
    >>> print(file_info.content)  # Now content is loaded
    >>> print(file_info.size)  # File size in bytes

    Metadata extraction:
    >>> metadata = extract_metadata(file_info)
    >>> print(metadata['size'])  # File size
    >>> print(metadata['encoding'])  # File encoding
    >>> print(metadata['mtime'])  # Last modified time

    Template metadata:
    >>> template = "Hello {{ name }}, files: {% for f in files %}{{ f.name }}{% endfor %}"
    >>> metadata = extract_template_metadata(template)
    >>> print(metadata['variables'])  # ['name', 'files']
    >>> print(metadata['has_loops'])  # True
    >>> print(metadata['filters'])  # []

    Cache management:
    >>> # Files are automatically cached
    >>> file_info1 = read_file('example.txt')
    >>> file_info2 = read_file('example.txt')  # Uses cached content
    >>> # Cache is invalidated if file changes
    >>> # Large files evicted from cache based on size

Notes:
    - Automatically detects file encoding
    - Caches file content for performance
    - Tracks file modifications
    - Provides progress updates for large files
    - Handles various error conditions gracefully
"""

import logging
import os
from typing import Any, Dict, Optional

from jinja2 import Environment

from .cache_manager import FileCache
from .file_utils import FileInfo
from .progress import ProgressContext
from .security import SecurityManager

logger = logging.getLogger(__name__)

# Global cache instance
_file_cache = FileCache()


def read_file(
    file_path: str,
    security_manager: Optional["SecurityManager"] = None,
    encoding: Optional[str] = None,
    progress_enabled: bool = True,
    chunk_size: int = 1024 * 1024,  # 1MB chunks
) -> FileInfo:
    """Read file with caching and progress tracking.

    Args:
        file_path: Path to file to read
        security_manager: Optional security manager for path validation
        encoding: Optional encoding to use for reading file
        progress_enabled: Whether to show progress bar
        chunk_size: Size of chunks to read in bytes

    Returns:
        FileInfo object with file metadata and content

    Raises:
        ValueError: If file not found or cannot be read
        PathSecurityError: If path is not allowed
    """
    # Create security manager if not provided
    if security_manager is None:
        from .security import SecurityManager

        security_manager = SecurityManager(base_dir=os.getcwd())
        logger.debug(
            "Created default SecurityManager with base_dir=%s", os.getcwd()
        )

    # Create progress context
    with ProgressContext(
        level="basic" if progress_enabled else "none"
    ) as progress:
        try:
            # Get absolute path and check file exists
            abs_path = os.path.abspath(file_path)
            logger.debug(
                "Reading file: path=%s, abs_path=%s", file_path, abs_path
            )

            if not os.path.isfile(abs_path):
                logger.error("File not found: %s", abs_path)
                raise ValueError(f"File not found: {file_path}")

            # Get file stats for cache validation
            try:
                stats = os.stat(abs_path)
                logger.debug(
                    "File stats: size=%d, mtime=%d, mtime_ns=%d, mode=%o",
                    stats.st_size,
                    stats.st_mtime,
                    stats.st_mtime_ns,
                    stats.st_mode,
                )
            except OSError as e:
                logger.error("Failed to get file stats: %s", e)
                raise ValueError(f"Cannot read file stats: {e}")

            mtime_ns = stats.st_mtime_ns
            size = stats.st_size

            # Check if file is in cache and up to date
            cache_entry = _file_cache.get(abs_path, mtime_ns, size)

            if cache_entry is not None:
                logger.debug(
                    "Using cached content for %s: encoding=%s, hash=%s",
                    abs_path,
                    cache_entry.encoding,
                    cache_entry.hash_value,
                )
                if progress.enabled:
                    progress.update(1)
                # Create FileInfo and update from cache
                file_info = FileInfo.from_path(
                    path=file_path, security_manager=security_manager
                )
                file_info.update_cache(
                    content=cache_entry.content,
                    encoding=cache_entry.encoding,
                    hash_value=cache_entry.hash_value,
                )
                return file_info

            # Create new FileInfo - content will be loaded immediately
            logger.debug("Reading fresh content for %s", abs_path)
            file_info = FileInfo.from_path(
                path=file_path, security_manager=security_manager
            )

            # Update cache with loaded content
            logger.debug(
                "Caching new content: path=%s, size=%d, encoding=%s, hash=%s",
                abs_path,
                size,
                file_info.encoding,
                file_info.hash,
            )
            _file_cache.put(
                abs_path,
                file_info.content,
                file_info.encoding,
                file_info.hash,
                mtime_ns,
                size,
            )

            if progress.enabled:
                progress.update(1)

            return file_info

        except Exception as e:
            logger.error(
                "Error reading file %s: %s (%s)",
                file_path,
                str(e),
                type(e).__name__,
                exc_info=True,
            )
            raise


def extract_metadata(file_info: FileInfo) -> Dict[str, Any]:
    """Extract metadata from a FileInfo object.

    This function respects lazy loading - it will not force content loading
    if the content hasn't been loaded yet.
    """
    metadata: Dict[str, Any] = {
        "name": os.path.basename(file_info.path),
        "path": file_info.path,
        "abs_path": os.path.realpath(file_info.path),
        "mtime": file_info.mtime,
    }

    # Only include content-related fields if content has been explicitly accessed
    if (
        hasattr(file_info, "_FileInfo__content")
        and file_info.content is not None
    ):
        metadata["content"] = file_info.content
        metadata["size"] = file_info.size

    return metadata


def extract_template_metadata(
    template_str: str,
    context: Dict[str, Any],
    jinja_env: Optional[Environment] = None,
    progress_enabled: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """Extract metadata about a template string."""
    metadata: Dict[str, Dict[str, Any]] = {
        "template": {"is_file": True, "path": template_str},
        "context": {
            "variables": sorted(context.keys()),
            "dict_vars": [],
            "list_vars": [],
            "file_info_vars": [],
            "other_vars": [],
        },
    }

    with ProgressContext(
        description="Analyzing template",
        level="basic" if progress_enabled else "none",
    ) as progress:
        # Categorize variables by type
        for key, value in context.items():
            if isinstance(value, dict):
                metadata["context"]["dict_vars"].append(key)
            elif isinstance(value, list):
                metadata["context"]["list_vars"].append(key)
            elif isinstance(value, FileInfo):
                metadata["context"]["file_info_vars"].append(key)
            else:
                metadata["context"]["other_vars"].append(key)

        # Sort lists for consistent output
        for key in ["dict_vars", "list_vars", "file_info_vars", "other_vars"]:
            metadata["context"][key].sort()

        if progress.enabled:
            progress.current = 1

        return metadata
