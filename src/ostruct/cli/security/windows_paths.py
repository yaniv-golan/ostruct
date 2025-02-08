"""Windows path handling and validation.

This module provides functions for handling Windows-specific path features:
- Device paths (r"\\\\?\\", r"\\\\.")
- Drive-relative paths (C:folder)
- Reserved names (CON, PRN, etc.)
- UNC paths (r"\\\\server\\share")
- Alternate Data Streams (file.txt:stream)

Security Design Choices:
1. Device Paths:
   - Explicitly blocked for security
   - No support for extended-length paths
   - No direct device access allowed

2. Drive Paths:
   - Drive-relative paths must include separator
   - Drive absolute paths are allowed
   - Drive letters must be A-Z (case insensitive)

3. Reserved Names:
   - All Windows reserved names blocked
   - Case-insensitive matching
   - Blocked with or without extensions

4. UNC Paths:
   - Must be complete (server and share)
   - No device paths in UNC format
   - Normalized to forward slashes

5. Alternate Data Streams:
   - All ADS access is blocked
   - No exceptions for Zone.Identifier
   - Blocks both read and write

Known Limitations:
1. Path Length:
   - No extended-length path support
   - Standard Windows MAX_PATH limits
   - No workarounds for long paths

2. Network:
   - No special handling for DFS
   - No support for administrative shares
   - Basic UNC validation only

3. Security:
   - Some rare path formats may bypass checks
   - Complex NTFS features not handled
   - Limited reparse point support
"""

import logging
import os
import re
from pathlib import Path, WindowsPath
from typing import Optional, Union

from .errors import PathSecurityError, SecurityErrorReasons

logger = logging.getLogger(__name__)

# Windows path length limits
MAX_PATH = 260
EXTENDED_MAX_PATH = 32767

# Regex patterns for Windows path features
_WINDOWS_DEVICE_PATH = re.compile(
    r"^(?:\\\\|//)[?.](?:\\|/)(?!UNC(?:\\|/))",  # Match device paths but exclude UNC
    flags=re.IGNORECASE,
)

_WINDOWS_DRIVE_RELATIVE = re.compile(
    r"(?:^|[/\\])[A-Za-z]:(?![/\\])|"  # C:folder or \C:folder but not C:\folder
    r"^/[A-Za-z]:(?![/\\])"  # /C:folder variants
)

_WINDOWS_RESERVED_NAMES = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])"  # Base names
    r"(\.[^\\/:*?\"<>|]*)?$",  # Optional extension
    re.IGNORECASE,
)

_WINDOWS_UNC = re.compile(
    r"^\\\\[^?.\\/][^\\/]*\\[^\\/]+(?:\\.*)?|"  # \\server\share[\anything]
    r"^//[^?./][^/]*/[^/]+(?:/.*)?$"  # //server/share[/anything]
)

_WINDOWS_INCOMPLETE_UNC = re.compile(
    r"^\\\\[^?.\\/][^\\/]*(?:\\[^\\/]+)?$|"  # \\server or \\server\incomplete
    r"^//[^?./][^/]*(?:/[^/]+)?$"  # //server or //server/incomplete variants
)

_WINDOWS_ADS = re.compile(
    r":[^/\\<>:\"|?*]+$|"  # Basic ADS
    r":Zone\.Identifier$|"  # Zone.Identifier
    r":[^/\\<>:\"|?*]+:[^/\\]+$"  # Multiple stream segments
)

_WINDOWS_INVALID_CHARS = re.compile(
    r'[<>"|?*]|'  # Standard invalid chars except colon
    r"(?<!^[A-Za-z]):|"  # Colon except after drive letter at start
    r"[\x00-\x1F]"  # Control chars
)

_WINDOWS_TRAILING = re.compile(r"[. ]+$")  # Trailing dots/spaces


def is_windows_path(path: Union[str, Path]) -> bool:
    """Check if path uses Windows-specific features.

    Security Note:
    - Detects device paths (r"\\?\\" and r"\\.\\") in both slash formats
    - Case insensitive to handle drive letters
    """
    path_str = str(path)

    # Normalize slashes for consistent matching
    normalized_path = path_str.replace("\\", "/")

    # Check for device paths first before any processing
    if _WINDOWS_DEVICE_PATH.match(path_str) or _WINDOWS_DEVICE_PATH.match(
        normalized_path
    ):
        logger.debug("Windows device path detected: %r", path_str)
        return True

    # Rest of the function remains unchanged
    basename = os.path.basename(path_str)
    is_drive_relative = bool(_WINDOWS_DRIVE_RELATIVE.search(path_str))
    is_unc = bool(_WINDOWS_UNC.search(path_str))
    is_ads = bool(_WINDOWS_ADS.search(path_str))
    is_reserved = bool(_WINDOWS_RESERVED_NAMES.match(basename))

    logger.debug(
        "Windows path check for %r: drive_relative=%s, unc=%s, ads=%s, reserved=%s",
        path_str,
        is_drive_relative,
        is_unc,
        is_ads,
        is_reserved,
    )

    return bool(is_drive_relative or is_unc or is_ads or is_reserved)


def normalize_windows_path(path: Union[str, Path]) -> Path:
    """Normalize a path using Windows-specific rules.

    This function:
    1. Converts to Path with Windows semantics
    2. Resolves to absolute path
    3. Normalizes separators and case
    4. Removes redundant separators and dots

    Args:
        path: Path to normalize

    Returns:
        Normalized Path

    Raises:
        PathSecurityError: If path cannot be normalized
    """
    try:
        logger.debug("Normalizing Windows path: %r", path)

        # Convert to string and normalize all slashes to forward slashes first
        path_str = str(path)
        # Replace all backslashes with forward slashes for consistent handling
        path_str = path_str.replace("\\", "/")
        # Collapse multiple slashes to single slash, except for UNC prefixes
        path_str = re.sub(r"(?<!^)//+", "/", path_str)
        logger.debug("Normalized slashes: %r", path_str)

        # Use regular Path on non-Windows systems
        path_cls = WindowsPath if os.name == "nt" else Path

        # Convert back to backslashes for Windows path handling
        if os.name == "nt":
            path_str = path_str.replace("/", "\\")
            # Preserve UNC path double backslashes
            if path_str.startswith("\\") and not path_str.startswith("\\\\"):
                path_str = "\\" + path_str

        normalized = path_cls(path_str)
        logger.debug(
            "Created path object: %r (class=%s)", normalized, path_cls.__name__
        )

        if os.name == "nt":
            # Check if resolve() would exceed MAX_PATH
            resolved = normalized.resolve()
            resolved_str = str(resolved)
            # If resolve() added \\?\ prefix or path is too long, reject it
            if (
                resolved_str.startswith("\\\\?\\")
                or len(resolved_str) > MAX_PATH
            ):
                raise PathSecurityError(
                    f"Path would exceed maximum length of {MAX_PATH} characters after resolution",
                    path=str(path),
                    context={
                        "reason": SecurityErrorReasons.NORMALIZATION_ERROR
                    },
                )
            normalized = resolved
            logger.debug("Resolved on Windows: %r", normalized)
        else:
            # On non-Windows, just normalize the path
            normalized = Path(os.path.normpath(path_str))
            logger.debug("Normalized on non-Windows: %r", normalized)

        return normalized
    except PathSecurityError:
        raise
    except Exception as e:
        logger.error(
            "Failed to normalize Windows path %r: %s", path, e, exc_info=True
        )
        raise PathSecurityError(
            f"Failed to normalize Windows path: {e}",
            path=str(path),
            context={"reason": SecurityErrorReasons.NORMALIZATION_ERROR},
        )


def validate_windows_path(path: Union[str, Path]) -> Optional[str]:
    """Validate a path for Windows-specific security issues.

    Performs checks in order:
    1. Device paths (blocked)
    2. Path normalization
    3. Other Windows-specific checks

    Returns an error message if the path:
    - Uses device paths (r"\\\\?\\", r"\\\\.")
    - Uses drive-relative paths (C:folder)
    - Contains reserved names (CON, PRN, etc.)
    - Uses UNC paths (r"\\\\server\\share")
    - Contains Alternate Data Streams (file.txt:stream)
    - Exceeds maximum path length
    - Contains invalid characters
    - Has trailing dots or spaces

    Returns None if the path is valid.
    """
    logger.debug("Validating Windows path: %r", path)

    # Initial checks on raw path string
    path_str = str(path)

    # Normalize slashes for consistent matching
    normalized_path = path_str.replace("\\", "/")

    # Check for device paths before any processing
    if _WINDOWS_DEVICE_PATH.match(path_str) or _WINDOWS_DEVICE_PATH.match(
        normalized_path
    ):
        logger.debug("Device path detected in original path: %r", path_str)
        return "Device paths not allowed"

    # Check for incomplete UNC paths before normalization
    if _WINDOWS_INCOMPLETE_UNC.search(path_str):
        logger.debug("Incomplete UNC path detected: %r", path_str)
        return "Incomplete UNC path"

    # Then normalize the path for other checks
    try:
        normalized_str = str(normalize_windows_path(path))
        logger.debug("Normalized path: %r", normalized_str)

        # Check for device paths again after normalization
        if _WINDOWS_DEVICE_PATH.match(normalized_str):
            logger.debug(
                "Device path detected after normalization: %r", normalized_str
            )
            return "Device paths not allowed"

    except PathSecurityError as e:
        logger.debug("Path normalization failed: %s", e)
        return str(e)

    # Check path length
    if len(normalized_str) > MAX_PATH:
        msg = f"Path exceeds maximum length of {MAX_PATH} characters"
        logger.debug("Path too long: %s", msg)
        return msg

    if _WINDOWS_DRIVE_RELATIVE.search(normalized_str):
        logger.debug("Drive-relative path detected: %r", normalized_str)
        return "Drive-relative paths must include separator"

    # Check for complete UNC paths
    if _WINDOWS_UNC.search(normalized_str):
        logger.debug("UNC path detected: %r", normalized_str)
        return "UNC paths not allowed"

    if _WINDOWS_ADS.search(normalized_str):
        logger.debug("Alternate Data Stream detected: %r", normalized_str)
        return "Alternate Data Streams not allowed"

    # Check each path component
    try:
        parts = (
            Path(normalized_str).parts
            if os.name != "nt"
            else WindowsPath(normalized_str).parts
        )
        logger.debug("Path components: %r", parts)

        for part in parts:
            # Check for reserved names
            if _WINDOWS_RESERVED_NAMES.match(part):
                logger.debug("Reserved name detected: %r", part)
                return "Windows reserved names not allowed"

            # Check for invalid characters
            if _WINDOWS_INVALID_CHARS.search(part):
                msg = f"Invalid characters in path component '{part}'"
                logger.debug("Invalid characters: %s", msg)
                return msg

            # Check for trailing dots/spaces
            if _WINDOWS_TRAILING.search(part):
                msg = f"Trailing dots or spaces not allowed in '{part}'"
                logger.debug("Trailing dots/spaces: %s", msg)
                return msg
    except Exception as e:
        logger.error("Failed to check path components: %s", e, exc_info=True)
        return f"Failed to validate path components: {e}"

    logger.debug("Path validation successful: %r", normalized_str)
    return None


def resolve_windows_symlink(path: Path) -> Optional[Path]:
    """Resolve a Windows symlink or reparse point.

    This is a Windows-specific helper for symlink resolution that handles:
    - NTFS symbolic links
    - NTFS junction points
    - NTFS mount points
    - Other reparse points

    Args:
        path: The path to resolve.

    Returns:
        Resolved Path if successful, None if not a Windows symlink.

    Note:
        This function requires Windows and elevated privileges for some
        reparse point operations.

    Security Note:
        By default, this function only handles regular symlinks.
        For security reasons, other reparse points (junctions, mount points)
        are not resolved by default as they can bypass directory restrictions.
        If you need to handle these, implement proper security checks in the
        calling code.
    """
    if os.name != "nt":
        return None

    try:
        # Try to resolve as a regular symlink first
        if path.is_symlink():
            target = Path(os.readlink(path))
            logger.debug("Resolved symlink %r to %r", path, target)
            return target

        # Check if it's a reparse point but not a symlink
        # This requires using Windows APIs, so we just warn about it
        if hasattr(path, "is_mount") and path.is_mount():
            logger.warning(
                "Path %r is a mount point/junction - not resolving for security",
                path,
            )
            return None

        # For any other reparse points, log a warning
        try:
            import ctypes

            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))  # type: ignore[attr-defined]
            is_reparse = bool(
                attrs != -1 and attrs & 0x400
            )  # FILE_ATTRIBUTE_REPARSE_POINT
            if is_reparse:
                logger.warning(
                    "Path %r is a reparse point - not resolving for security",
                    path,
                )
                return None
        except Exception:
            # If we can't check reparse attributes, assume it's not a reparse point
            pass

        return None

    except OSError as e:
        logger.debug("Failed to resolve Windows symlink %r: %s", path, e)
        return None
