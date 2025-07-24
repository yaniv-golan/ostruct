"""Shared upload manager for multi-tool file sharing.

This module implements a centralized upload management system that ensures files
attached to multiple tools are uploaded only once and shared across all target tools.
This prevents redundant uploads and improves performance for multi-target attachments.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
)

from openai import AsyncOpenAI

from .attachment_processor import AttachmentSpec, ProcessedAttachments

# Centralized constants
from .constants import DefaultConfig
from .errors import CLIError

if TYPE_CHECKING:
    from .upload_cache import UploadCache

logger = logging.getLogger(__name__)


class UploadStatus(Enum):
    """Status of an upload operation."""

    HIT = "hit"  # File was found in cache and reused
    MISS = "miss"  # File was not in cache, had to upload
    FAILED = "failed"  # Upload operation failed


@dataclass
class UploadRecord:
    """Record of a file upload with status tracking."""

    path: Union[
        str, Path
    ]  # Original file path (pathlib.Path or raw URL string)
    upload_id: Optional[str] = None  # OpenAI file ID after upload
    tools_pending: Set[str] = field(
        default_factory=set
    )  # Tools waiting for this file
    tools_completed: Set[str] = field(
        default_factory=set
    )  # Tools that have received this file
    file_size: Optional[int] = None  # File size in bytes
    file_hash: Optional[str] = None  # File content hash for identity
    upload_status: Optional[UploadStatus] = (
        None  # Status of last upload attempt
    )
    is_url: bool = False  # Whether this is a remote URL vs local file


class UploadError(CLIError):
    """Error during file upload operations."""

    def __init__(self, message: str, **kwargs: Any):
        """Initialize upload error with appropriate exit code."""
        from .exit_codes import ExitCode

        super().__init__(message, exit_code=ExitCode.USAGE_ERROR, **kwargs)

    def __str__(self) -> str:
        """Custom string representation without error type prefix."""
        # For upload errors, we want clean user-friendly messages
        # without the [USAGE_ERROR] prefix since our messages are already formatted
        return self.message


class SharedUploadManager:
    """Manages file uploads across multiple tools to avoid duplicates.

    This manager coordinates file uploads between Code Interpreter and File Search
    tools, ensuring that files attached to multiple targets are uploaded only once
    but shared across all requesting tools.
    """

    def __init__(
        self, client: AsyncOpenAI, cache: Optional["UploadCache"] = None
    ):
        """Initialize the shared upload manager.

        Args:
            client: AsyncOpenAI client for file operations
            cache: Optional upload cache for deduplication
        """
        self.client = client

        # Map file identity -> upload record
        self._uploads: Dict[Tuple[int, int], UploadRecord] = {}

        # Queue of files needing upload for each tool
        self._upload_queue: Dict[str, Set[Tuple[int, int]]] = {
            "code-interpreter": set(),
            "file-search": set(),
            "user-data": set(),
        }

        # Track all uploaded file IDs for cleanup
        self._all_uploaded_ids: Set[str] = set()

        # Upload cache for deduplication (None = no caching)
        self._cache = cache

        # Cache statistics
        self._cache_hits: int = 0  # Number of times a cached file was reused
        self._cache_misses: int = (
            0  # Number of times a file had to be uploaded
        )

        # Add per-file upload locks to prevent race conditions
        self._upload_locks: Dict[Tuple[int, int], asyncio.Lock] = {}

        # Lock management settings
        self._max_locks = (
            1000  # Maximum number of locks to prevent memory exhaustion
        )
        self._lock_cleanup_threshold = (
            800  # Trigger cleanup when this many locks exist
        )

        # URL registry for remote files
        self._url_registry: Dict[str, str] = {}  # URL -> unique_id mapping
        self._max_url_registry_size = 10000  # Maximum URL registry entries
        self._url_registry_cleanup_threshold = (
            8000  # Trigger cleanup when this many URLs exist
        )

    def register_attachments(
        self, processed_attachments: ProcessedAttachments
    ) -> None:
        """Register all attachments for upload management.

        Args:
            processed_attachments: Processed attachment specifications
        """
        logger.debug("Registering attachments for upload management")

        # Register all attachment specs
        for spec in processed_attachments.alias_map.values():
            self._register_attachment_spec(spec)

        logger.debug(
            f"Registered {len(self._uploads)} unique files for upload, "
            f"CI queue: {len(self._upload_queue['code-interpreter'])}, "
            f"FS queue: {len(self._upload_queue['file-search'])}, "
            f"UD queue: {len(self._upload_queue['user-data'])}"
        )

    def _register_attachment_spec(self, spec: AttachmentSpec) -> None:
        """Register a single attachment specification.

        Args:
            spec: Attachment specification to register
        """
        # Detect remote URLs and register them separately
        if isinstance(spec.path, str) and str(spec.path).startswith(
            ("http://", "https://")
        ):
            self._register_remote_url(str(spec.path), spec.targets)
            return

        # Get file identity for local files
        file_id = self._get_file_identity(Path(spec.path))

        # Create upload record if it doesn't exist
        if file_id not in self._uploads:
            self._uploads[file_id] = UploadRecord(
                path=Path(spec.path),
                tools_pending=set(),
                tools_completed=set(),
            )

        # Handle directory vs file differently
        if Path(spec.path).is_dir():
            # For directories, we need to expand and register individual files
            self._register_directory_files(spec, file_id)
        else:
            # For individual files, register with target tools
            self._register_file_for_targets(file_id, spec.targets)

    def _register_directory_files(
        self, spec: AttachmentSpec, base_file_id: Tuple[int, int]
    ) -> None:
        """Register individual files from a directory attachment.

        Args:
            spec: Directory attachment specification
            base_file_id: Base file identity for the directory
        """
        path = Path(spec.path)

        # Expand directory to individual files
        files = []
        if spec.recursive:
            if spec.pattern:
                files = list(path.rglob(spec.pattern))
            else:
                files = [f for f in path.rglob("*") if f.is_file()]
        else:
            if spec.pattern:
                files = list(path.glob(spec.pattern))
            else:
                files = [f for f in path.iterdir() if f.is_file()]

        # Register each file individually
        for file_path in files:
            try:
                file_id = self._get_file_identity(file_path)

                if file_id not in self._uploads:
                    self._uploads[file_id] = UploadRecord(
                        path=file_path,
                        tools_pending=set(),
                        tools_completed=set(),
                    )

                self._register_file_for_targets(file_id, spec.targets)

            except Exception as e:
                logger.warning(f"Could not register file {file_path}: {e}")

    def _register_file_for_targets(
        self, file_id: Tuple[int, int], targets: Set[str]
    ) -> None:
        """Register a file for specific target tools.

        Args:
            file_id: File identity tuple
            targets: Set of target tool names
        """
        record = self._uploads[file_id]

        # Add to upload queues for tools that need uploads
        for target in targets:
            if target == "code-interpreter":
                record.tools_pending.add(target)
                self._upload_queue[target].add(file_id)
            elif target == "file-search":
                record.tools_pending.add(target)
                self._upload_queue[target].add(file_id)
            elif target == "user-data":
                record.tools_pending.add(target)
                self._upload_queue[target].add(file_id)
            # "prompt" target doesn't need uploads, just template access

    def _get_file_identity(self, path: Path) -> Tuple[int, int]:
        """Get unique identity for a file based on inode and device.

        This uses the file's inode and device numbers to create a unique
        identity that works across different path representations of the same file.
        Falls back to size+mtime+hash on Windows when inode is unreliable.

        Args:
            path: File path to get identity for

        Returns:
            Tuple of (device, inode) for file identity

        Raises:
            OSError: If file cannot be accessed
        """
        try:
            stat = Path(path).stat()

            # Check if inode is reliable (non-zero on most filesystems)
            if stat.st_ino != 0:
                return (stat.st_dev, stat.st_ino)

            # Fallback for Windows/NTFS: use size + mtime as approximation
            logger.debug(f"Using size+mtime identity for {path} (inode=0)")
            return (stat.st_dev, hash((stat.st_size, int(stat.st_mtime))))

        except OSError as e:
            logger.error(f"Cannot get file identity for {path}: {e}")
            raise

    def _register_remote_url(self, url: str, targets: Set[str]) -> None:
        """Register a remote URL for processing.

        Args:
            url: Remote URL to register
            targets: Set of target tool names that need this URL
        """
        from .url_validation import validate_url_security

        # Validate URL security first
        validate_url_security(url)

        # Create a unique identifier for the URL
        import hashlib

        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        unique_id = f"url_{url_hash}"

        # Store URL mapping
        self._url_registry[url] = unique_id

        # Check if we need to clean up URL registry to prevent memory exhaustion
        if len(self._url_registry) > self._url_registry_cleanup_threshold:
            self._cleanup_url_registry()

        # Create a synthetic file identity for the URL
        # Use hash of URL as both device and inode
        url_identity = (
            hash(url) & 0x7FFFFFFF,
            hash(url + "_inode") & 0x7FFFFFFF,
        )

        # Create upload record for URL – keep raw string to avoid // truncation
        self._uploads[url_identity] = UploadRecord(
            path=url,
            tools_pending=set(),
            tools_completed=set(),
            is_url=True,
        )

        # Register with target tools
        self._register_file_for_targets(url_identity, targets)

        logger.debug(f"Registered remote URL: {url} -> {unique_id}")

    async def upload_for_tool(self, tool: str) -> Dict[str, str]:
        """Upload all queued files for a specific tool.

        Args:
            tool: Tool name ("code-interpreter" or "file-search")

        Returns:
            Dictionary mapping file paths to upload IDs

        Raises:
            UploadError: If any uploads fail
        """
        if tool not in self._upload_queue:
            raise ValueError(f"Unknown tool: {tool}")

        logger.debug(f"Processing uploads for {tool}")
        uploaded = {}
        failed_uploads = []

        for file_id in self._upload_queue[tool]:
            record = self._uploads[file_id]

            try:
                # Ensure we have a lock for this file
                if file_id not in self._upload_locks:
                    self._upload_locks[file_id] = asyncio.Lock()

                # Check if we need to clean up locks to prevent memory exhaustion
                if len(self._upload_locks) > self._lock_cleanup_threshold:
                    await self._cleanup_unused_locks()

                # Use per-file lock to prevent concurrent uploads
                async with self._upload_locks[file_id]:
                    if record.upload_id is None:
                        # Determine purpose based on tool and whether it's user-data
                        purpose: Literal["assistants", "user_data"] = (
                            "user_data"
                            if tool == "user-data"
                            else "assistants"
                        )

                        # First upload for this file
                        record.upload_id = await self._perform_upload(
                            record.path, purpose=purpose
                        )
                        self._all_uploaded_ids.add(record.upload_id)
                        logger.info(
                            f"Uploaded {record.path} -> {record.upload_id}"
                        )
                    else:
                        logger.debug(
                            f"Reusing upload {record.upload_id} for {record.path}"
                        )

                uploaded[str(record.path)] = record.upload_id
                record.tools_completed.add(tool)
                record.tools_pending.discard(tool)

            except UploadError as e:
                # UploadError already has user-friendly message, don't duplicate logging
                failed_uploads.append((record.path, str(e)))
            except Exception as e:
                logger.error(f"Failed to upload {record.path} for {tool}: {e}")
                failed_uploads.append((record.path, str(e)))

        if failed_uploads:
            # If we have user-friendly error messages, present them cleanly
            if len(failed_uploads) == 1:
                # Single file failure - show the detailed error message
                _, error_msg = failed_uploads[0]
                raise UploadError(error_msg)
            else:
                # Multiple file failures - show summary with details
                error_msg = (
                    f"Failed to upload {len(failed_uploads)} files:\n\n"
                )
                for i, (path, error) in enumerate(failed_uploads, 1):
                    error_msg += f"{i}. {error}\n\n"
                raise UploadError(error_msg.rstrip())

        # Perform periodic memory cleanup after completing uploads
        total_memory_usage = (
            len(self._uploads)
            + len(self._upload_locks)
            + len(self._url_registry)
        )
        if total_memory_usage > 5000:  # Cleanup if total memory usage is high
            await self.cleanup_memory()

        logger.debug(f"Completed {len(uploaded)} uploads for {tool}")
        return uploaded

    async def _perform_upload(
        self,
        file_path: Union[str, Path],
        purpose: Literal["assistants", "user_data"] = "assistants",
    ) -> str:
        """Perform actual file upload with error handling.

        Args:
            file_path: Path to file to upload or URL string
            purpose: OpenAI file purpose ("assistants" or "user_data")

        Returns:
            OpenAI file ID

        Raises:
            UploadError: If upload fails
        """
        try:
            # Check if this is a URL
            file_path_str = str(file_path)
            if file_path_str.startswith(("http://", "https://")):
                # Handle URL upload - no local file validation needed
                logger.debug(f"[upload] Processing URL: {file_path_str}")

                # Validate URL security
                from .url_validation import validate_url_security

                validate_url_security(file_path_str)

                # For URLs, we don't upload - we return the URL as a special identifier
                # The actual file_url element will be created in message building
                return f"url:{file_path_str}"

            # Handle local file upload
            if not Path(file_path).exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            file_size = Path(file_path).stat().st_size

            # Validate file size for user_data purpose (512MB limit)
            if (
                purpose == "user_data"
                and file_size > DefaultConfig.USER_DATA_FILE_LIMIT_BYTES
            ):
                raise UploadError(
                    f"File {file_path} ({file_size / (1024 * 1024):.1f}MB) exceeds "
                    f"the {DefaultConfig.USER_DATA_FILE_LIMIT_BYTES / (1024 * 1024):.0f}MB limit for user-data files. Consider using File Search "
                    f"or Code Interpreter for large files."
                )

            # Validate file type for user_data uploads – OpenAI currently supports PDFs only
            if purpose == "user_data":
                allowed_extensions = {".pdf"}
                if Path(file_path).suffix.lower() not in allowed_extensions:
                    raise UploadError(
                        f"User-data attachments currently support PDF files only. "
                        f"Detected '{Path(file_path).suffix}' for {file_path}. "
                        "Please convert the document to PDF or use a different attachment target, "
                        "such as 'code-interpreter' or 'file-search', for non-PDF content."
                    )

            # Warn for large user_data files
            if (
                purpose == "user_data"
                and file_size > DefaultConfig.USER_DATA_LARGE_WARNING_BYTES
            ):
                logger.info(
                    f"Large user-data file: {file_path} ({file_size / (1024 * 1024):.1f}MB). "
                    f"This may impact processing speed and costs."
                )

            file_hash = None  # Compute once and reuse

            # Check cache first if available
            if self._cache:
                try:
                    file_hash = self._cache.compute_file_hash(
                        Path(file_path)
                    )  # Only once
                    cached_file_id = self._cache.lookup_with_validation(
                        Path(file_path), file_hash
                    )
                    if cached_file_id:
                        # Report cache hit to the user via progress reporter
                        try:
                            import click

                            from .progress_reporting import (
                                get_progress_reporter,
                            )

                            reporter = get_progress_reporter()
                            if reporter.should_report:  # pragma: no cover
                                if reporter.detailed:
                                    # Get cache age for detailed reporting
                                    age_str = ""
                                    try:
                                        created_at = (
                                            self._cache.get_created_at(
                                                cached_file_id
                                            )
                                        )
                                        if created_at:
                                            age_days = (
                                                time.time() - created_at
                                            ) / (24 * 3600)
                                            if age_days < 1:
                                                age_str = f", age: {age_days * 24:.1f}h"
                                            else:
                                                age_str = (
                                                    f", age: {age_days:.1f}d"
                                                )
                                    except Exception:
                                        pass

                                    click.echo(
                                        f"♻️  Reusing cached upload for {file_path} ({cached_file_id}{age_str})",
                                        err=True,
                                    )
                                    click.echo(
                                        f"   → Hash: {file_hash[:12]}...",
                                        err=True,
                                    )
                                else:
                                    click.echo(
                                        f"✔ {Path(file_path).name} (cached)",
                                        err=True,
                                    )
                        except Exception:  # pragma: no cover
                            # Never fail upload because of progress reporting
                            pass

                        # Update cache statistics
                        self._cache_hits += 1

                        logger.debug(
                            f"[upload] Using cached file: {file_path} -> {cached_file_id}"
                        )
                        return cached_file_id
                    else:
                        logger.debug(f"[upload] Cache miss for: {file_path}")
                        self._cache_misses += 1
                except Exception as cache_err:
                    logger.debug(f"[upload] Cache lookup failed: {cache_err}")

            logger.debug(f"[upload] Uploading file: {file_path}")

            # Upload file with specified purpose
            with open(file_path, "rb") as f:
                file_obj = await self.client.files.create(
                    file=f, purpose=purpose
                )
                logger.debug(
                    f"[upload] Successfully uploaded {file_path} as {file_obj.id}"
                )

            # Store in cache if available (reuse computed hash)
            if self._cache and file_hash:  # Reuse existing hash
                try:
                    file_stat = Path(file_path).stat()
                    self._cache.store(
                        file_hash,  # Use previously computed hash
                        file_obj.id,
                        file_size,
                        int(file_stat.st_mtime),
                        {"purpose": "assistants"},
                        file_path=str(file_path),  # Pass file path for storage
                    )
                    logger.debug(
                        f"[upload] Stored in cache: {file_path} -> {file_obj.id}"
                    )
                except Exception as cache_err:
                    logger.debug(
                        f"[upload] Failed to store file in cache: {cache_err}"
                    )

            return file_obj.id

        except Exception as e:
            # Parse OpenAI API errors for better user experience
            # Note: We don't log here as the error will be handled at a higher level
            user_friendly_error = self._parse_upload_error(Path(file_path), e)
            raise UploadError(user_friendly_error)

    def _parse_upload_error(self, file_path: Path, error: Exception) -> str:
        """Parse OpenAI upload errors into user-friendly messages.

        Args:
            file_path: Path to the file that failed to upload
            error: The original exception from OpenAI API

        Returns:
            User-friendly error message with actionable suggestions
        """
        error_str = str(error)
        file_ext = file_path.suffix.lower()

        # Check for unsupported file extension error
        if (
            "Invalid extension" in error_str
            and "Supported formats" in error_str
        ):
            return (
                f"❌ Cannot upload {file_path.name} to Code Interpreter/File Search\n"
                f"   File extension '{file_ext}' is not supported by OpenAI's tools.\n"
                f"   See: https://platform.openai.com/docs/assistants/tools/code-interpreter#supported-files\n\n"
                f"💡 Solutions:\n"
                f"   1. Use template-only routing (recommended):\n"
                f"      Change: --dir ci:configs {file_path.parent}\n"
                f"      To:     --dir configs {file_path.parent}\n"
                f'      Your template can still access content with: {{{{ file_ref("configs") }}}}\n\n'
                f"   2. Rename file to add .txt extension:\n"
                f"      {file_path.name} → {file_path.name}.txt\n"
                f"      Then use: --dir ci:configs {file_path.parent}\n"
                f"      (OpenAI will treat it as text but preserve YAML content)"
            )

        # Check for file size errors
        if (
            "file too large" in error_str.lower()
            or "size limit" in error_str.lower()
        ):
            return (
                f"❌ File too large: {file_path.name}\n"
                f"   OpenAI tools have a file size limit (typically 100MB).\n\n"
                f"💡 Solutions:\n"
                f"   1. Use template-only routing: --dir configs {file_path.parent}\n"
                f"   2. Split large files into smaller chunks\n"
                f"   3. Use file summarization before upload"
            )

        # Generic upload error with helpful context
        return (
            f"❌ Failed to upload {file_path.name}\n"
            f"   {error_str}\n\n"
            f"💡 If this is a configuration file, try template-only routing:\n"
            f"   Change: --dir ci:configs {file_path.parent}\n"
            f"   To:     --dir configs {file_path.parent}"
        )

    def get_upload_summary(self) -> Dict[str, Any]:
        """Get summary of upload operations.

        Returns:
            Dictionary with upload statistics and status
        """
        total_files = len(self._uploads)
        uploaded_files = sum(
            1 for record in self._uploads.values() if record.upload_id
        )
        pending_files = total_files - uploaded_files

        ci_files = len(self._upload_queue["code-interpreter"])
        fs_files = len(self._upload_queue["file-search"])

        return {
            "total_files": total_files,
            "uploaded_files": uploaded_files,
            "pending_files": pending_files,
            "code_interpreter_files": ci_files,
            "file_search_files": fs_files,
            "total_upload_ids": len(self._all_uploaded_ids),
            "shared_files": total_files
            - ci_files
            - fs_files
            + len(self._all_uploaded_ids),  # Files used by multiple tools
            # Cache statistics
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
        }

    async def cleanup_uploads(self, ttl_days: Optional[int] = None) -> None:
        """Clean up uploaded files with TTL awareness.

        Args:
            ttl_days: Time-to-live in days for cached files. Files older than this
                     will be deleted. Set to 0 to delete all files immediately.
                     If None, uses configuration or default value.
        """
        if not self._all_uploaded_ids:
            logger.debug("[upload] No uploaded files to clean up")
            return

        # Get TTL from config if not provided
        if ttl_days is None:
            from .cache_config import get_cache_ttl_from_config

            ttl_days = get_cache_ttl_from_config()

        logger.debug(
            f"[upload] Starting cleanup of {len(self._all_uploaded_ids)} files (TTL: {ttl_days}d)"
        )

        preserved_files = set()  # Track files that were preserved

        if not self._cache:
            logger.debug(
                "[upload] No cache available, deleting all files immediately"
            )
            # Fallback to deleting all files if no cache
            for file_id in self._all_uploaded_ids:
                try:
                    logger.debug(f"[upload] Deleting file: {file_id}")
                    await self.client.files.delete(file_id)
                    logger.debug(f"[upload] Successfully deleted: {file_id}")
                except Exception as e:
                    logger.warning(f"[upload] Failed to delete {file_id}: {e}")
        else:
            logger.debug(
                f"[upload] Using cache-aware cleanup with TTL: {ttl_days}d"
            )

            # TTL-aware cleanup with cache
            for file_id in self._all_uploaded_ids:
                try:
                    # Check if file should be preserved
                    if ttl_days > 0 and self._cache.is_file_cached_and_valid(
                        file_id, ttl_days
                    ):
                        logger.debug(
                            f"[upload] Preserving cached file: {file_id}"
                        )
                        preserved_files.add(file_id)
                        # Update last accessed for LRU behavior
                        self._cache.update_last_accessed(file_id)
                        continue

                    # Delete the file
                    logger.debug(f"[upload] Deleting file: {file_id}")
                    await self.client.files.delete(file_id)
                    logger.debug(f"[upload] Successfully deleted: {file_id}")

                except Exception as e:
                    if "404" in str(e) or "not found" in str(e).lower():
                        logger.debug(
                            f"[upload] File {file_id} already gone, cleaning cache"
                        )
                        # Clean up stale cache entry
                        self._cache.invalidate_by_file_id(file_id)
                    else:
                        logger.warning(
                            f"[upload] Failed to delete {file_id}: {e}"
                        )

        # Only clear deleted files, keep preserved ones for future cleanup
        self._all_uploaded_ids = preserved_files

        # Clean up upload locks for files that are no longer tracked
        # This prevents memory leaks in long-running processes
        files_to_remove_locks: List[Tuple[int, int]] = []
        for lock_file_id in list(self._upload_locks.keys()):
            if (
                lock_file_id not in self._uploads
                or self._uploads[lock_file_id].upload_id is None
            ):
                files_to_remove_locks.append(lock_file_id)

        for lock_file_id in files_to_remove_locks:
            del self._upload_locks[lock_file_id]
            logger.debug(f"[upload] Cleaned up lock for file: {lock_file_id}")

        logger.debug(
            f"[upload] Cleanup complete, {len(preserved_files)} files preserved, "
            f"{len(self._all_uploaded_ids)} files remaining in tracking, "
            f"cleaned up {len(files_to_remove_locks)} locks"
        )

    def get_files_for_tool(self, tool: str) -> List[str]:
        """Get list of upload IDs for a specific tool.

        Args:
            tool: Tool name ("code-interpreter" or "file-search")

        Returns:
            List of OpenAI file IDs for the tool
        """
        if tool not in self._upload_queue:
            return []

        file_ids = []
        for file_id in self._upload_queue[tool]:
            record = self._uploads[file_id]
            if record.upload_id:
                file_ids.append(record.upload_id)

        return file_ids

    async def _cleanup_unused_locks(self) -> None:
        """Clean up unused upload locks to prevent memory leaks."""
        logger.debug(
            f"[upload] Cleaning up unused locks, current count: {len(self._upload_locks)}"
        )

        # Find locks for files that are no longer being tracked or have completed upload
        files_to_remove_locks: List[Tuple[int, int]] = []
        for file_id in list(self._upload_locks.keys()):
            if (
                file_id not in self._uploads
                or self._uploads[file_id].upload_id
                is not None  # Upload completed
            ):
                files_to_remove_locks.append(file_id)

        # Remove unused locks
        for file_id in files_to_remove_locks:
            del self._upload_locks[file_id]

        logger.debug(
            f"[upload] Cleaned up {len(files_to_remove_locks)} unused locks, "
            f"remaining: {len(self._upload_locks)}"
        )

        # If we're still over the limit, remove oldest locks (simple FIFO)
        if len(self._upload_locks) > self._max_locks:
            excess_count = len(self._upload_locks) - self._max_locks
            locks_to_remove = list(self._upload_locks.keys())[:excess_count]

            for file_id in locks_to_remove:
                del self._upload_locks[file_id]

            logger.warning(
                f"[upload] Removed {excess_count} locks due to memory limit, "
                f"remaining: {len(self._upload_locks)}"
            )

    def _cleanup_url_registry(self) -> None:
        """Clean up URL registry to prevent memory leaks."""
        logger.debug(
            f"[upload] Cleaning up URL registry, current count: {len(self._url_registry)}"
        )

        # Find URLs that are no longer being tracked or have completed upload
        urls_to_remove: List[str] = []
        for url, unique_id in list(self._url_registry.items()):
            # Create the same synthetic file identity used when storing
            url_identity = (
                hash(url) & 0x7FFFFFFF,
                hash(url + "_inode") & 0x7FFFFFFF,
            )

            # Remove URL if upload record doesn't exist or upload is completed
            if (
                url_identity not in self._uploads
                or self._uploads[url_identity].upload_id is not None
            ):
                urls_to_remove.append(url)

        # Remove unused URL mappings
        for url in urls_to_remove:
            del self._url_registry[url]

        logger.debug(
            f"[upload] Cleaned up {len(urls_to_remove)} URL registry entries, "
            f"remaining: {len(self._url_registry)}"
        )

        # If we're still over the limit, remove oldest entries (simple FIFO)
        if len(self._url_registry) > self._max_url_registry_size:
            excess_count = (
                len(self._url_registry) - self._max_url_registry_size
            )
            urls_to_remove = list(self._url_registry.keys())[:excess_count]

            for url in urls_to_remove:
                del self._url_registry[url]

            logger.warning(
                f"[upload] Removed {excess_count} URL registry entries due to memory limit, "
                f"remaining: {len(self._url_registry)}"
            )

    async def cleanup_memory(self) -> None:
        """Perform comprehensive memory cleanup to prevent leaks."""
        logger.debug("[upload] Performing comprehensive memory cleanup")

        # Clean up upload locks
        await self._cleanup_unused_locks()

        # Clean up URL registry
        self._cleanup_url_registry()

        # Clean up completed uploads that are no longer needed
        uploads_to_remove: List[Tuple[int, int]] = []
        for file_id, record in list(self._uploads.items()):
            # Remove completed uploads that have been processed
            if record.upload_id is not None and record.upload_status in (
                UploadStatus.HIT,
                UploadStatus.MISS,
            ):
                uploads_to_remove.append(file_id)

        for file_id in uploads_to_remove:
            del self._uploads[file_id]
            # Also remove any remaining locks for these files
            if file_id in self._upload_locks:
                del self._upload_locks[file_id]

        logger.debug(
            f"[upload] Memory cleanup completed - removed {len(uploads_to_remove)} upload records"
        )
        logger.debug(
            f"[upload] Current memory usage - uploads: {len(self._uploads)}, "
            f"locks: {len(self._upload_locks)}, urls: {len(self._url_registry)}"
        )

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics if enabled."""
        if self._cache:
            return self._cache.get_stats()
        return None

    def get_cache_summary_for_display(self) -> Optional[Dict[str, Any]]:
        """Get cache summary formatted for end-of-run display."""
        if not self._cache:
            return None

        cache_stats = self._cache.get_stats()
        if not cache_stats:
            return None

        # Calculate space saved (rough estimate)
        space_saved_mb = 0
        if self._cache_hits > 0:
            # Estimate average file size and multiply by hits
            # This is a rough approximation since we don't track exact sizes
            space_saved_mb = (
                self._cache_hits * 5
            )  # Assume 5MB average file size

        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "space_saved_mb": space_saved_mb,
            "cache_path": cache_stats.get("cache_path", ""),
            "total_entries": cache_stats.get("total_entries", 0),
            "db_size_mb": cache_stats.get("size_bytes", 0) / (1024 * 1024),
        }
