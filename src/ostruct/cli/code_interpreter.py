"""Code Interpreter integration for ostruct CLI.

This module provides support for uploading files to OpenAI's Code Interpreter
and integrating code execution capabilities with the OpenAI Responses API.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class CodeInterpreterManager:
    """Manager for Code Interpreter file uploads and tool integration."""

    def __init__(
        self, client: AsyncOpenAI, config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Code Interpreter manager.

        Args:
            client: AsyncOpenAI client instance
            config: Code interpreter configuration dict
        """
        self.client = client
        self.uploaded_file_ids: List[str] = []
        self.config = config or {}

    async def upload_files_for_code_interpreter(
        self, files: List[str]
    ) -> List[str]:
        """Upload files for Code Interpreter (validated working pattern).

        This method uploads files to OpenAI's file storage with the correct
        purpose for Code Interpreter usage.

        Args:
            files: List of file paths to upload

        Returns:
            List of file IDs from successful uploads

        Raises:
            FileNotFoundError: If a file doesn't exist
            Exception: If upload fails
        """
        file_ids = []

        for file_path in files:
            try:
                # Validate file exists
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")

                # Get file info
                file_size = os.path.getsize(file_path)
                logger.debug(
                    f"Uploading file: {file_path} ({file_size} bytes)"
                )

                # Upload with correct purpose for Code Interpreter
                with open(file_path, "rb") as f:
                    file_obj = await self.client.files.create(
                        file=f,
                        purpose="assistants",  # Validated correct purpose
                    )
                    file_ids.append(file_obj.id)
                    logger.debug(
                        f"Successfully uploaded {file_path} with ID: {file_obj.id}"
                    )

            except Exception as e:
                logger.error(f"Failed to upload file {file_path}: {e}")
                # Clean up any successfully uploaded files on error
                await self._cleanup_uploaded_files(file_ids)
                raise

        # Store for potential cleanup
        self.uploaded_file_ids.extend(file_ids)
        return file_ids

    def build_tool_config(self, file_ids: List[str]) -> dict:
        """Build Code Interpreter tool configuration.

        Creates a tool configuration compatible with the OpenAI Responses API
        for Code Interpreter functionality.

        Args:
            file_ids: List of uploaded file IDs

        Returns:
            Tool configuration dict for Responses API
        """
        return {
            "type": "code_interpreter",
            "container": {"type": "auto", "file_ids": file_ids},
        }

    def _collect_file_annotations(self, resp: Any) -> List[Dict[str, Any]]:
        """Collect file annotations from Responses API output.

        Based on IMPLEMENTATION_NOTES.md findings:
        - resp.output is a list of ResponseCodeInterpreterToolCall and ResponseOutputMessage
        - Annotations can be in ResponseOutputMessage.content[].annotations
        - Also check ResponseCodeInterpreterToolCall for file outputs
        - Look for container_file_citation type

        Returns:
            List of annotation dicts with file_id, container_id, filename
        """
        annotations = []

        for item in resp.output:
            # Check messages for annotations
            if getattr(item, "type", None) == "message":
                for blk in item.content or []:
                    if hasattr(blk, "annotations"):
                        for ann in blk.annotations or []:
                            # Look specifically for container_file_citation type
                            if (
                                getattr(ann, "type", None)
                                == "container_file_citation"
                            ):
                                annotations.append(
                                    {
                                        "file_id": ann.file_id,
                                        "container_id": getattr(
                                            ann, "container_id", None
                                        ),
                                        "filename": getattr(
                                            ann, "filename", None
                                        ),
                                        "type": ann.type,
                                    }
                                )

            # Check code interpreter tool calls for file outputs
            elif getattr(item, "type", None) == "code_interpreter_call":
                # Check if the tool call has outputs with files
                if hasattr(item, "outputs"):
                    for output in item.outputs or []:
                        # Look for file outputs
                        if hasattr(output, "type") and output.type == "file":
                            file_id = getattr(output, "file_id", None)
                            filename = getattr(output, "filename", None)
                            if file_id:
                                annotations.append(
                                    {
                                        "file_id": file_id,
                                        "container_id": None,
                                        "filename": filename or file_id,
                                        "type": "code_interpreter_file",
                                    }
                                )

        return annotations

    async def download_generated_files(
        self, response: Any, output_dir: str = "."
    ) -> List[str]:
        """Download files generated by Code Interpreter using annotations.

        Updated to use container_file_citation annotations instead of
        deprecated message.file_ids field.

        Args:
            response: Response from client.responses.create()
            output_dir: Directory to save downloaded files

        Returns:
            List of local file paths where files were saved

        Raises:
            Exception: If download fails
        """
        if not response:
            return []

        # Check if auto_download is enabled
        if not self.config.get("auto_download", True):
            logger.debug("Auto-download disabled in configuration")
            return []

        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Collect file annotations using new method
        annotations = self._collect_file_annotations(response)
        logger.debug(
            f"Found {len(annotations)} file annotations: {annotations}"
        )

        if not annotations:
            logger.debug("No file annotations found in response")
            return []

        downloaded_paths = []

        for ann in annotations:
            try:
                file_id = ann["file_id"]
                container_id = ann.get("container_id")
                filename = ann.get("filename") or file_id

                # Use container-specific API for cfile_* IDs
                if file_id.startswith("cfile_") and container_id:
                    logger.debug(
                        f"Using container API for {file_id} in container {container_id}"
                    )

                    # Try different approaches to access the Container Files API
                    file_content = None

                    # Approach 1: Direct method call (should work in v1.84.0+)
                    try:
                        logger.debug(
                            "Attempting direct containers.files.content() call"
                        )
                        # Note: type: ignore[operator] is needed due to mypy false positive
                        # The OpenAI SDK's type annotations incorrectly suggest AsyncContent is not callable
                        # but the method works correctly at runtime and returns an object with .content property
                        result = await self.client.containers.files.content(  # type: ignore[operator]
                            file_id, container_id=container_id
                        )

                        # Based on expert guidance: in v1.83.0+, result should have .content property
                        if hasattr(result, "content"):
                            file_content = result.content
                            logger.debug(
                                f"✓ Got content via result.content: {len(file_content)} bytes"
                            )
                        elif hasattr(result, "response") and hasattr(
                            result.response, "content"
                        ):
                            file_content = result.response.content
                            logger.debug(
                                f"✓ Got content via result.response.content: {len(file_content)} bytes"
                            )
                        else:
                            logger.debug(
                                f"Result type: {type(result)}, available attrs: {[a for a in dir(result) if not a.startswith('_')]}"
                            )

                    except Exception as e:
                        logger.debug(f"Direct method call failed: {e}")

                    # Approach 2: Try using the raw HTTP client if direct method fails
                    if file_content is None:
                        try:
                            logger.debug(
                                "Attempting raw HTTP request to container files endpoint"
                            )
                            import httpx

                            # Construct the URL manually
                            base_url = str(self.client.base_url).rstrip("/")
                            url = f"{base_url}/containers/{container_id}/files/{file_id}/content"

                            # Use the client's HTTP client with auth headers
                            headers = {
                                "Authorization": f"Bearer {self.client.api_key}",
                                "User-Agent": "ostruct/container-files-client",
                            }

                            async with httpx.AsyncClient() as http_client:
                                response = await http_client.get(
                                    url, headers=headers
                                )
                                response.raise_for_status()
                                file_content = response.content
                                logger.debug(
                                    f"✓ Got content via raw HTTP: {len(file_content)} bytes"
                                )

                        except Exception as e:
                            logger.debug(f"Raw HTTP request failed: {e}")

                    if file_content is None:
                        raise Exception(
                            f"Failed to download container file {file_id} using both direct API and raw HTTP methods"
                        )
                else:
                    logger.debug(f"Using standard Files API for {file_id}")
                    # Use standard Files API for regular uploaded files
                    file_content_resp = await self.client.files.content(
                        file_id
                    )
                    file_content = file_content_resp.read()

                # Save to local file
                local_path = output_path / filename
                with open(local_path, "wb") as f:
                    f.write(file_content)

                downloaded_paths.append(str(local_path))
                logger.info(f"Downloaded generated file: {local_path}")

            except Exception as e:
                logger.error(f"Failed to download file {file_id}: {e}")
                # Continue with other files instead of raising
                continue

        return downloaded_paths

    def _extract_filename_from_message(self, msg: Any) -> str:
        """Extract filename from message content if available.

        Args:
            msg: Message object that might contain filename references

        Returns:
            Extracted filename or empty string if not found
        """
        try:
            # Try to extract filename from markdown links in message content
            if hasattr(msg, "content") and msg.content:
                import re

                # Look for patterns like [filename.ext](sandbox:/mnt/data/filename.ext)
                content_str = str(msg.content)
                match = re.search(
                    r"\[([^\]]+\.[a-zA-Z0-9]+)\]\(sandbox:/mnt/data/[^)]+\)",
                    content_str,
                )
                if match:
                    return match.group(1)
        except Exception:
            pass
        return ""

    async def cleanup_uploaded_files(self) -> None:
        """Clean up uploaded files from OpenAI storage.

        This method removes files that were uploaded during the session
        to avoid accumulating files in the user's OpenAI storage.
        """
        await self._cleanup_uploaded_files(self.uploaded_file_ids)
        self.uploaded_file_ids.clear()

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

    def validate_files_for_upload(self, files: List[str]) -> List[str]:
        """Validate files are suitable for Code Interpreter upload.

        Args:
            files: List of file paths to validate

        Returns:
            List of validation error messages, empty if all files are valid
        """
        errors = []

        # Common file types supported by Code Interpreter
        supported_extensions = {
            ".py",
            ".txt",
            ".csv",
            ".json",
            ".xlsx",
            ".xls",
            ".pdf",
            ".docx",
            ".md",
            ".xml",
            ".html",
            ".js",
            ".sql",
            ".log",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
        }

        # Size limits (approximate - OpenAI has file size limits)
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
                        f"File extension {file_ext} may not be supported by Code Interpreter: {file_path}"
                    )

            except Exception as e:
                errors.append(f"Error validating file {file_path}: {e}")

        return errors

    def get_container_limits_info(self) -> Dict[str, Any]:
        """Get information about Code Interpreter container limits.

        Returns:
            Dictionary with container limit information
        """
        return {
            "max_runtime_minutes": 20,
            "idle_timeout_minutes": 2,
            "max_file_size_mb": 100,
            "supported_languages": ["python"],
            "note": "Container expires after 20 minutes of runtime or 2 minutes of inactivity",
        }
