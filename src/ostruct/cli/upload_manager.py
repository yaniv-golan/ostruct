"""Shared upload manager for multi-tool file sharing.

This module implements a centralized upload management system that ensures files
attached to multiple tools are uploaded only once and shared across all target tools.
This prevents redundant uploads and improves performance for multi-target attachments.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from openai import AsyncOpenAI

from .attachment_processor import AttachmentSpec, ProcessedAttachments
from .errors import CLIError

logger = logging.getLogger(__name__)


@dataclass
class UploadRecord:
    """Record of a file upload with status tracking."""

    path: Path  # Original file path
    upload_id: Optional[str] = None  # OpenAI file ID after upload
    tools_pending: Set[str] = field(
        default_factory=set
    )  # Tools waiting for this file
    tools_completed: Set[str] = field(
        default_factory=set
    )  # Tools that have received this file
    file_size: Optional[int] = None  # File size in bytes
    file_hash: Optional[str] = None  # File content hash for identity


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

    def __init__(self, client: AsyncOpenAI):
        """Initialize the shared upload manager.

        Args:
            client: AsyncOpenAI client for file operations
        """
        self.client = client

        # Map file identity -> upload record
        self._uploads: Dict[Tuple[int, int], UploadRecord] = {}

        # Queue of files needing upload for each tool
        self._upload_queue: Dict[str, Set[Tuple[int, int]]] = {
            "code-interpreter": set(),
            "file-search": set(),
        }

        # Track all uploaded file IDs for cleanup
        self._all_uploaded_ids: Set[str] = set()

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
            f"FS queue: {len(self._upload_queue['file-search'])}"
        )

    def _register_attachment_spec(self, spec: AttachmentSpec) -> None:
        """Register a single attachment specification.

        Args:
            spec: Attachment specification to register
        """
        # Get file identity
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
            # "prompt" target doesn't need uploads, just template access

    def _get_file_identity(self, path: Path) -> Tuple[int, int]:
        """Get unique identity for a file based on inode and device.

        This uses the file's inode and device numbers to create a unique
        identity that works across different path representations of the same file.

        Args:
            path: File path to get identity for

        Returns:
            Tuple of (device, inode) for file identity

        Raises:
            OSError: If file cannot be accessed
        """
        try:
            stat = Path(path).stat()
            return (stat.st_dev, stat.st_ino)
        except OSError as e:
            logger.error(f"Cannot get file identity for {path}: {e}")
            raise

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
                if record.upload_id is None:
                    # First upload for this file
                    record.upload_id = await self._perform_upload(record.path)
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

        logger.debug(f"Completed {len(uploaded)} uploads for {tool}")
        return uploaded

    async def _perform_upload(self, file_path: Path) -> str:
        """Perform actual file upload with error handling.

        Args:
            file_path: Path to file to upload

        Returns:
            OpenAI file ID

        Raises:
            UploadError: If upload fails
        """
        try:
            # Validate file exists and get info
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            file_size = file_path.stat().st_size
            logger.debug(f"Uploading {file_path} ({file_size} bytes)")

            # Perform upload
            with open(file_path, "rb") as f:
                upload_response = await self.client.files.create(
                    file=f,
                    purpose="assistants",  # Standard purpose for both CI and FS
                )

            logger.debug(
                f"Successfully uploaded {file_path} as {upload_response.id}"
            )
            return upload_response.id

        except Exception as e:
            # Parse OpenAI API errors for better user experience
            # Note: We don't log here as the error will be handled at a higher level
            user_friendly_error = self._parse_upload_error(file_path, e)
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
        }

    async def cleanup_uploads(self) -> None:
        """Clean up all uploaded files.

        This method deletes all files that were uploaded during this session.
        Should be called when the operation is complete to avoid leaving
        temporary files in OpenAI storage.
        """
        if not self._all_uploaded_ids:
            logger.debug("No uploaded files to clean up")
            return

        logger.debug(
            f"Cleaning up {len(self._all_uploaded_ids)} uploaded files"
        )
        cleanup_errors = []

        for file_id in self._all_uploaded_ids:
            try:
                await self.client.files.delete(file_id)
                logger.debug(f"Deleted uploaded file: {file_id}")
            except Exception as e:
                logger.warning(
                    f"Failed to delete uploaded file {file_id}: {e}"
                )
                cleanup_errors.append((file_id, str(e)))

        if cleanup_errors:
            logger.error(f"Failed to clean up {len(cleanup_errors)} files")
        else:
            logger.debug("Successfully cleaned up all uploaded files")

        # Clear tracking
        self._all_uploaded_ids.clear()

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
