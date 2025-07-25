"""Shared utility modules for CLI commands."""

from .attachment_utils import AttachmentProcessor
from .common_utils import fix_surrogate_escapes
from .error_utils import ErrorCollector
from .json_output import JSONOutputHandler
from .progress_utils import BatchPhaseContext, ProgressHandler

__all__ = [
    "AttachmentProcessor",
    "ErrorCollector",
    "JSONOutputHandler",
    "ProgressHandler",
    "BatchPhaseContext",
    "fix_surrogate_escapes",
]
