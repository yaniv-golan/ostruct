"""Raw HTTP downloader for OpenAI container files.

This module provides functionality to download files from OpenAI Code Interpreter
containers using raw HTTP requests, working around SDK limitations.
"""

import logging

import httpx

from .errors import ContainerExpiredError, DownloadError
from .progress_reporting import get_progress_reporter
from .security.credential_sanitizer import CredentialSanitizer

logger = logging.getLogger(__name__)

# Maximum download size to prevent memory exhaustion during CI file downloads (100MB)
# Separate from template max_file_size which applies to user input files
MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024


class ContainerFileDownloader:
    """Raw HTTP downloader for OpenAI container files"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def download_container_file(
        self, file_id: str, container_id: str
    ) -> bytes:
        """Download file from container using raw HTTP

        Args:
            file_id: OpenAI file ID
            container_id: Container ID
        """

        # Use the correct OpenAI API endpoint
        url = f"https://api.openai.com/v1/containers/{container_id}/files/{file_id}/content"

        try:
            # First, check file size to prevent memory exhaustion
            head_response = await self.client.head(url)
            if head_response.status_code == 429:
                raise httpx.HTTPStatusError(
                    "Rate limited",
                    request=head_response.request,
                    response=head_response,
                )

            content_length = head_response.headers.get("content-length")
            file_size = int(content_length) if content_length else None

            if file_size and file_size > MAX_DOWNLOAD_SIZE:
                raise DownloadError(
                    f"File too large: {file_size} bytes (max: {MAX_DOWNLOAD_SIZE})"
                )

            # Use existing progress system
            progress_reporter = get_progress_reporter()
            size_str = f" ({file_size} bytes)" if file_size else ""
            progress_reporter.report_phase(
                f"📥 Downloading {file_id}{size_str}", ""
            )

            # Now download the actual content
            response = await self.client.get(url)

            if response.status_code == 404:
                raise ContainerExpiredError(
                    f"Container {container_id} expired or file {file_id} not found"
                )
            elif response.status_code == 429:
                raise httpx.HTTPStatusError(
                    "Rate limited", request=response.request, response=response
                )
            elif response.status_code != 200:
                # Use credential sanitizer for error messages
                sanitized_text = CredentialSanitizer.sanitize_string(
                    response.text
                )
                raise DownloadError(
                    f"Download failed: {response.status_code} - {sanitized_text}"
                )

            return response.content

        except httpx.TimeoutException:
            raise DownloadError("Download timed out after 30 seconds")
        except httpx.RequestError as e:
            # Sanitize network errors that might contain credentials
            sanitized_error = CredentialSanitizer.sanitize_exception(e)
            raise DownloadError(f"Network error: {sanitized_error}")

    async def close(self) -> None:
        await self.client.aclose()
