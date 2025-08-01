"""Enhanced error classification for download operations."""

from enum import Enum
from typing import Any, Dict, List, Optional

from .errors import DownloadError


class DownloadErrorType(Enum):
    CONTAINER_EXPIRED = "container_expired"
    SDK_LIMITATION = "sdk_limitation"
    NETWORK_TIMEOUT = "network_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    FILE_NOT_FOUND = "file_not_found"
    ANNOTATION_MISSING = "annotation_missing"
    UNKNOWN = "unknown"


class EnhancedDownloadError(DownloadError):
    """Enhanced download error with classification and user guidance"""

    def __init__(
        self,
        message: str,
        error_type: DownloadErrorType,
        file_id: Optional[str] = None,
        container_id: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context=context)
        self.error_type = error_type
        self.file_id = file_id
        self.container_id = container_id
        self.suggestions = suggestions or []

    def get_user_message(self) -> str:
        """Get user-friendly error message with suggestions"""

        base_messages = {
            DownloadErrorType.CONTAINER_EXPIRED: (
                "The Code Interpreter session expired (20-minute limit). "
                "Files created more than 20 minutes ago cannot be downloaded."
            ),
            DownloadErrorType.SDK_LIMITATION: (
                "Using fallback download method due to OpenAI SDK limitations."
            ),
            DownloadErrorType.NETWORK_TIMEOUT: (
                "Download timed out. This may be due to large file size or network issues."
            ),
            DownloadErrorType.API_RATE_LIMIT: (
                "API rate limit reached. Retrying with exponential backoff."
            ),
            DownloadErrorType.FILE_NOT_FOUND: (
                "File was not created or has been deleted from the container."
            ),
            DownloadErrorType.ANNOTATION_MISSING: (
                "File download link not found in AI response. "
                "The AI may not have included proper download links."
            ),
        }

        message = base_messages.get(self.error_type, str(self))

        if self.suggestions:
            message += "\n\nSuggestions:\n"
            for i, suggestion in enumerate(self.suggestions, 1):
                message += f"{i}. {suggestion}\n"

        return message
