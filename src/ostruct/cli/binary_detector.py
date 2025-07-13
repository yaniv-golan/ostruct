"""Binary file detection using Magika with extension fallback.

This module provides MIME type detection to determine if files should be
routed to the user-data target (for binary files) or prompt target (for text files).
"""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Extension-based fallback for when Magika is unavailable
_EXT_TEXTUAL = {
    ".txt",
    ".md",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".htm",
    ".xml",
    ".css",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".cmd",
    ".log",
    ".csv",
    ".tsv",
    ".env",
    ".gitignore",
    ".gitattributes",
    ".dockerfile",
    ".makefile",
    ".cmake",
    ".gradle",
    ".properties",
    ".plist",
}

# Magika instance (lazy-loaded)
_magika_instance: Optional[Any] = None
_magika_available = True


def _get_magika_instance() -> Optional[Any]:
    """Get or create a Magika instance.

    Returns:
        Magika instance if available, None otherwise
    """
    global _magika_instance, _magika_available

    if not _magika_available:
        return None

    if _magika_instance is None:
        try:
            from magika import Magika

            _magika_instance = Magika()
            logger.debug("Magika initialized successfully")
        except ImportError:
            logger.warning(
                "Magika not available - falling back to extension detection. "
                "Install with: pip install magika"
            )
            _magika_available = False
            return None
        except Exception as e:
            logger.warning(
                f"Failed to initialize Magika: {e} - falling back to extension detection"
            )
            _magika_available = False
            return None

    return _magika_instance


def detect_mime_type(path: str) -> str:
    """Detect MIME type of a file using Magika with extension fallback.

    Args:
        path: Path to the file to analyze

    Returns:
        MIME type string (e.g., "text/plain", "application/pdf")
    """
    magika = _get_magika_instance()

    if magika is not None:
        try:
            result = magika.identify_path(path)
            mime_type = result.output.mime_type
            logger.debug(f"Magika detected MIME type for {path}: {mime_type}")
            return str(mime_type)
        except Exception as e:
            logger.warning(
                f"Magika detection failed for {path}: {e} - falling back to extension detection"
            )

    # Fallback to extension-based detection
    return _detect_mime_by_extension(path)


def _detect_mime_by_extension(path: str) -> str:
    """Detect MIME type based on file extension.

    Args:
        path: Path to the file

    Returns:
        MIME type string
    """
    file_path = Path(path)
    extension = file_path.suffix.lower()

    # Special cases for known extensions
    if extension == ".json":
        return "application/json"
    elif extension in {".yaml", ".yml"}:
        return "application/x-yaml"
    elif extension == ".toml":
        return "application/toml"
    elif extension in {
        ".py",
        ".js",
        ".ts",
        ".html",
        ".htm",
        ".xml",
        ".css",
        ".sql",
    }:
        return "text/plain"
    elif extension in {
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".bat",
        ".cmd",
    }:
        return "text/x-shellscript"
    elif extension in {".csv", ".tsv"}:
        return "text/csv"
    elif extension == ".pdf":
        return "application/pdf"
    elif extension in {".jpg", ".jpeg"}:
        return "image/jpeg"
    elif extension == ".png":
        return "image/png"
    elif extension == ".gif":
        return "image/gif"
    elif extension in {".zip", ".tar", ".gz", ".bz2", ".xz"}:
        return "application/octet-stream"
    elif extension in _EXT_TEXTUAL:
        return "text/plain"
    else:
        # Default to binary for unknown extensions
        logger.debug(
            f"Unknown extension {extension} for {path}, treating as binary"
        )
        return "application/octet-stream"


def is_text_file(path: str) -> bool:
    """Check if a file should be treated as text based on MIME type.

    Args:
        path: Path to the file

    Returns:
        True if file should be treated as text, False for binary
    """
    mime_type = detect_mime_type(path)
    return _is_text_mime_type(mime_type)


def _is_text_mime_type(mime_type: str) -> bool:
    """Check if a MIME type represents text content.

    Args:
        mime_type: MIME type string

    Returns:
        True if MIME type represents text content
    """
    # Text types that should go to prompt target
    if mime_type.startswith("text/"):
        return True

    # Special application types that are text-based
    text_application_types = {
        "application/json",
        "application/x-yaml",
        "application/yaml",
        "application/toml",
        "application/xml",
        "application/javascript",
        "application/x-javascript",
        "application/x-shellscript",
    }

    return mime_type in text_application_types


def should_route_to_user_data(path: str) -> bool:
    """Check if a file should be routed to user-data target.

    Args:
        path: Path to the file

    Returns:
        True if file should go to user-data target, False for prompt target
    """
    return not is_text_file(path)


def get_routing_recommendation(path: str) -> str:
    """Get routing target recommendation for a file.

    Args:
        path: Path to the file

    Returns:
        Recommended target: "prompt" or "user-data"
    """
    if is_text_file(path):
        return "prompt"
    else:
        return "user-data"
