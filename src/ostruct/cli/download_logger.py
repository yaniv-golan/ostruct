"""Specialized logger for file download operations."""

import logging
from datetime import datetime
from typing import Optional

from .download_errors import DownloadErrorType

logger = logging.getLogger(__name__)


class DownloadLogger:
    """Specialized logger for file download operations"""

    def __init__(self) -> None:
        self.logger = logger

    def log_download_attempt(
        self, file_id: str, method: str, container_id: Optional[str] = None
    ) -> None:
        """Log download attempt with context"""
        context = {
            "file_id": file_id,
            "method": method,
            "container_id": container_id,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(f"Attempting download: {method}", extra=context)

    def log_download_success(
        self, file_id: str, size_bytes: int, duration_seconds: float
    ) -> None:
        """Log successful download with metrics"""
        self.logger.info(
            f"Download successful: {file_id} ({size_bytes} bytes in {duration_seconds:.2f}s)"
        )

    def log_download_failure(
        self, file_id: str, error: Exception, error_type: DownloadErrorType
    ) -> None:
        """Log download failure with classification"""
        self.logger.error(
            f"Download failed: {file_id} - {error_type.value}: {error}"
        )

    def log_container_status(
        self, container_id: str, age_minutes: float, is_expired: bool
    ) -> None:
        """Log container status for debugging"""
        status = "EXPIRED" if is_expired else "ACTIVE"
        self.logger.debug(
            f"Container {container_id}: {status} (age: {age_minutes:.1f} minutes)"
        )
