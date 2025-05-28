"""File Search integration for ostruct CLI.

This module provides support for uploading files to OpenAI's File Search
(vector store) and integrating retrieval capabilities with the OpenAI Responses API.
Includes retry logic for reliability improvements.
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class FileSearchManager:
    """Manager for File Search vector store operations with retry logic."""

    def __init__(self, client: AsyncOpenAI):
        """Initialize File Search manager.

        Args:
            client: AsyncOpenAI client instance
        """
        self.client = client
        self.uploaded_file_ids: List[str] = []
        self.created_vector_stores: List[str] = []

    async def create_vector_store_with_retry(
        self,
        name: str = "ostruct_vector_store",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> str:
        """Create a vector store with retry logic for reliability.

        Args:
            name: Name for the vector store
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            Vector store ID

        Raises:
            Exception: If creation fails after all retries
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    f"Creating vector store '{name}' (attempt {attempt + 1}/{max_retries + 1})"
                )

                vector_store = await self.client.vector_stores.create(
                    name=name,
                    expires_after={
                        "anchor": "last_active_at",
                        "days": 7,  # Automatically expire after 7 days of inactivity
                    },
                )

                self.created_vector_stores.append(vector_store.id)
                logger.debug(
                    f"Successfully created vector store: {vector_store.id}"
                )
                return vector_store.id

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Vector store creation attempt {attempt + 1} failed: {e}"
                )

                if attempt < max_retries:
                    delay = retry_delay * (2**attempt)  # Exponential backoff
                    logger.debug(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Vector store creation failed after {max_retries + 1} attempts"
                    )

        raise Exception(
            f"Failed to create vector store after {max_retries + 1} attempts: {last_exception}"
        )

    async def upload_files_to_vector_store(
        self,
        vector_store_id: str,
        files: List[str],
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> List[str]:
        """Upload files to vector store with retry logic.

        Args:
            vector_store_id: ID of the vector store
            files: List of file paths to upload
            max_retries: Maximum number of retry attempts per file
            retry_delay: Initial delay between retries

        Returns:
            List of successfully uploaded file IDs

        Raises:
            Exception: If upload fails for any file after all retries
        """
        file_ids = []

        for file_path in files:
            try:
                # Validate file exists
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")

                # Upload file with retry logic
                file_id = await self._upload_single_file_with_retry(
                    file_path, max_retries, retry_delay
                )
                file_ids.append(file_id)

            except Exception as e:
                logger.error(f"Failed to upload file {file_path}: {e}")
                # Clean up any successfully uploaded files on error
                await self._cleanup_uploaded_files(file_ids)
                raise

        # Add files to vector store with retry logic
        try:
            await self._add_files_to_vector_store_with_retry(
                vector_store_id, file_ids, max_retries, retry_delay
            )
        except Exception as e:
            logger.error(f"Failed to add files to vector store: {e}")
            await self._cleanup_uploaded_files(file_ids)
            raise

        # Store for potential cleanup
        self.uploaded_file_ids.extend(file_ids)
        return file_ids

    async def _upload_single_file_with_retry(
        self, file_path: str, max_retries: int, retry_delay: float
    ) -> str:
        """Upload a single file with retry logic.

        Args:
            file_path: Path to the file to upload
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries

        Returns:
            File ID of uploaded file

        Raises:
            Exception: If upload fails after all retries
        """
        last_exception = None
        file_size = os.path.getsize(file_path)

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    f"Uploading {file_path} ({file_size} bytes) - attempt {attempt + 1}/{max_retries + 1}"
                )

                with open(file_path, "rb") as f:
                    file_obj = await self.client.files.create(
                        file=f,
                        purpose="assistants",  # Required for File Search
                    )

                logger.debug(
                    f"Successfully uploaded {file_path} with ID: {file_obj.id}"
                )
                return file_obj.id

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"File upload attempt {attempt + 1} failed for {file_path}: {e}"
                )

                if attempt < max_retries:
                    delay = retry_delay * (2**attempt)
                    logger.debug(f"Retrying upload in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"File upload failed after {max_retries + 1} attempts: {file_path}"
                    )

        raise Exception(
            f"Failed to upload {file_path} after {max_retries + 1} attempts: {last_exception}"
        )

    async def _add_files_to_vector_store_with_retry(
        self,
        vector_store_id: str,
        file_ids: List[str],
        max_retries: int,
        retry_delay: float,
    ) -> None:
        """Add files to vector store with retry logic.

        Args:
            vector_store_id: ID of the vector store
            file_ids: List of file IDs to add
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries

        Raises:
            Exception: If adding files fails after all retries
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    f"Adding {len(file_ids)} files to vector store - attempt {attempt + 1}/{max_retries + 1}"
                )

                await self.client.vector_stores.file_batches.create(
                    vector_store_id=vector_store_id, file_ids=file_ids
                )

                logger.debug(
                    f"Successfully added files to vector store: {vector_store_id}"
                )
                return

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Adding files to vector store attempt {attempt + 1} failed: {e}"
                )

                if attempt < max_retries:
                    delay = retry_delay * (2**attempt)
                    logger.debug(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Adding files to vector store failed after {max_retries + 1} attempts"
                    )

        raise Exception(
            f"Failed to add files to vector store after {max_retries + 1} attempts: {last_exception}"
        )

    async def wait_for_vector_store_ready(
        self,
        vector_store_id: str,
        timeout: float = 60.0,
        poll_interval: float = 2.0,
    ) -> bool:
        """Wait for vector store to be ready for search.

        Based on probe tests, indexing is typically instant (0.0s average),
        but we include polling for reliability.

        Args:
            vector_store_id: ID of the vector store
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds

        Returns:
            True if vector store is ready, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                vector_store = await self.client.vector_stores.retrieve(
                    vector_store_id
                )

                if vector_store.status == "completed":
                    logger.debug(f"Vector store {vector_store_id} is ready")
                    return True
                elif vector_store.status == "failed":
                    logger.error(
                        f"Vector store {vector_store_id} failed to index"
                    )
                    return False

                logger.debug(
                    f"Vector store {vector_store_id} status: {vector_store.status}"
                )
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.warning(f"Error checking vector store status: {e}")
                await asyncio.sleep(poll_interval)

        logger.warning(
            f"Vector store {vector_store_id} not ready after {timeout}s timeout"
        )
        return False

    def build_tool_config(self, vector_store_id: str) -> dict:
        """Build File Search tool configuration.

        Creates a tool configuration compatible with the OpenAI Responses API
        for File Search functionality.

        Args:
            vector_store_id: ID of the vector store to search

        Returns:
            Tool configuration dict for Responses API
        """
        return {
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
        }

    async def cleanup_resources(self) -> None:
        """Clean up uploaded files and created vector stores.

        This method removes files and vector stores that were created during
        the session to avoid accumulating resources in the user's OpenAI account.
        """
        # Clean up uploaded files
        await self._cleanup_uploaded_files(self.uploaded_file_ids)
        self.uploaded_file_ids.clear()

        # Clean up vector stores
        await self._cleanup_vector_stores(self.created_vector_stores)
        self.created_vector_stores.clear()

    async def _cleanup_uploaded_files(self, file_ids: List[str]) -> None:
        """Internal method to clean up specific file IDs.

        Args:
            file_ids: List of file IDs to delete
        """
        for file_id in file_ids:
            try:
                await self.client.files.delete(file_id)
                logger.debug(f"Cleaned up uploaded file: {file_id}")
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_id}: {e}")

    async def _cleanup_vector_stores(
        self, vector_store_ids: List[str]
    ) -> None:
        """Internal method to clean up specific vector store IDs.

        Args:
            vector_store_ids: List of vector store IDs to delete
        """
        for vs_id in vector_store_ids:
            try:
                await self.client.vector_stores.delete(vs_id)
                logger.debug(f"Cleaned up vector store: {vs_id}")
            except Exception as e:
                logger.warning(f"Failed to clean up vector store {vs_id}: {e}")

    def validate_files_for_file_search(self, files: List[str]) -> List[str]:
        """Validate files are suitable for File Search upload.

        Args:
            files: List of file paths to validate

        Returns:
            List of validation error messages, empty if all files are valid
        """
        errors = []

        # File types commonly supported by File Search
        supported_extensions = {
            ".txt",
            ".md",
            ".pdf",
            ".docx",
            ".doc",
            ".rtf",
            ".html",
            ".xml",
            ".csv",
            ".json",
            ".jsonl",
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".sql",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".log",
        }

        # Size limits for File Search (approximate)
        max_file_size = 100 * 1024 * 1024  # 100MB

        for file_path in files:
            try:
                if not os.path.exists(file_path):
                    errors.append(f"File not found: {file_path}")
                    continue

                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size > max_file_size:
                    errors.append(
                        f"File too large: {file_path} ({file_size / 1024 / 1024:.1f}MB > 100MB)"
                    )

                # Check file extension
                file_ext = Path(file_path).suffix.lower()
                if file_ext not in supported_extensions:
                    logger.warning(
                        f"File extension {file_ext} may not be optimal for File Search: {file_path}"
                    )

                # Check if file is empty
                if file_size == 0:
                    errors.append(f"File is empty: {file_path}")

            except Exception as e:
                errors.append(f"Error validating file {file_path}: {e}")

        return errors

    def get_performance_info(self) -> Dict[str, Any]:
        """Get information about File Search performance characteristics.

        Returns:
            Dictionary with performance information
        """
        return {
            "indexing_time": "typically instant (0.0s average based on probe tests)",
            "reliability_note": "File Search can be intermittent - retry logic is essential",
            "max_file_size_mb": 100,
            "supported_formats": [
                "PDF",
                "text files",
                "documents",
                "code files",
            ],
            "vector_store_expiry": "7 days of inactivity",
            "retry_strategy": "exponential backoff with 3 retries by default",
        }
