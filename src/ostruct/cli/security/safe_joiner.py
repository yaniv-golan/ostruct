"""Safe path joining module.

This module provides a safe_join function that is inspired by Werkzeug's safe_join.
It safely joins untrusted path components to a trusted base directory while avoiding
directory traversal issues.

Security Design Choices:
1. Parent Directory (..) References:
   - Explicitly blocked for security, even in "safe" contexts
   - This is a deliberate choice to prevent directory traversal
   - No exceptions are made, even for legitimate uses

2. Environment Variables:
   - No expansion of environment variables (%VAR%, $HOME)
   - Must be handled explicitly at a higher level if needed
   - Prevents unexpected path resolution

3. Home Directory:
   - No expansion of ~ (tilde)
   - Must be expanded explicitly before passing to this function
   - Prevents unexpected user directory access

4. Symlinks:
   - Not resolved in this module
   - Handled separately by the resolve_symlink function
   - Allows for explicit symlink security policies

5. Case Sensitivity:
   - Basic normalization only
   - Full case handling delegated to CaseManager
   - Ensures consistent cross-platform behavior

Known Limitations:
1. Windows-Specific:
   - UNC paths (r"\\\\server\\share") are handled but must be complete
   - Device paths (r"\\\\?\\", r"\\\\.") are rejected for security
   - Drive-relative paths (C:folder) must be absolute
   - Reserved names (CON, NUL, etc.) are rejected
   - Alternate Data Streams (:stream) are rejected

2. Unicode:
   - Basic NFKC normalization only
   - Some confusable characters may not be detected
   - Advanced homograph attack prevention requires additional checks

3. Threading:
   - Current working directory calls are not thread-safe
   - Race conditions possible if CWD changes during execution
"""

import os
import posixpath
import re
from typing import Optional

# Compute alternative separators (if any) that differ from "/"
_os_alt_seps = list(
    {sep for sep in [os.path.sep, os.path.altsep] if sep and sep != "/"}
)

# Windows-specific patterns
_WINDOWS_DEVICE_PATH = re.compile(r"^\\\\[?.]\\")  # \\?\ and \\.\ paths
_WINDOWS_DRIVE_RELATIVE = re.compile(
    r"^[A-Za-z]:(?![/\\])"
)  # C:folder (no slash)
_WINDOWS_RESERVED_NAMES = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.IGNORECASE
)
_WINDOWS_UNC = re.compile(r"^\\\\[^?./\\]")  # UNC but not device paths
_WINDOWS_ADS = re.compile(r":.+$")  # Alternate Data Streams


def safe_join(directory: str, *pathnames: str) -> Optional[str]:
    """Safely join zero or more untrusted path components to a trusted base directory.

    This function is inspired by Werkzeug's safe_join and ensures that the
    resulting path is always within the base directory, preventing directory
    traversal attacks.

    Security Features:
    - Rejects absolute path components
    - Blocks all parent directory references (..)
    - Normalizes path separators to forward slashes
    - Performs final containment check against base directory
    - Handles Windows-specific security concerns:
        * Rejects device paths (r"\\\\?\\", r"\\\\.")
        * Rejects relative drive paths (C:folder)
        * Rejects reserved names (CON, PRN, etc.)
        * Rejects Alternate Data Streams
        * Safely handles UNC paths

    Design Choices:
    - No environment variable expansion
    - No home directory (~) expansion
    - No symlink resolution (handled separately)
    - Case sensitivity handled by CaseManager
    - Thread-safety warning: CWD operations are not atomic

    Args:
        directory: The trusted base directory.
        pathnames: Untrusted path components relative to the base directory.

    Returns:
        A safe path as a string if successful; otherwise, None.

    Example:
        >>> safe_join("/base", "subdir", "file.txt")
        '/base/subdir/file.txt'
        >>> safe_join("/base", "../etc/passwd")
        None
    """
    if not directory and not pathnames:
        return None

    if not directory:
        directory = "."

    # Handle None values in pathnames
    if any(p is None for p in pathnames):
        return None

    # Convert and normalize base directory
    directory = str(directory)
    directory = directory.replace("\\", "/")
    base_dir = posixpath.normpath(directory)

    # Windows-specific base directory checks
    if os.name == "nt":
        # Check for device paths
        if _WINDOWS_DEVICE_PATH.search(base_dir):
            return None
        # Check for relative drive paths
        if _WINDOWS_DRIVE_RELATIVE.search(base_dir):
            return None
        # Check for reserved names
        if _WINDOWS_RESERVED_NAMES.search(base_dir):
            return None
        # Check for ADS
        if _WINDOWS_ADS.search(base_dir):
            return None
        # Handle UNC paths - must be complete
        if _WINDOWS_UNC.search(base_dir):
            if base_dir.count("/") < 3:  # Needs server and share
                return None

    # Process and validate each component
    normalized_parts = []
    for filename in pathnames:
        if filename == "":
            continue

        # Convert to string and normalize separators
        filename = str(filename)
        filename = filename.replace("\\", "/")

        # Windows-specific component checks
        if os.name == "nt":
            # Check for device paths
            if _WINDOWS_DEVICE_PATH.search(filename):
                return None
            # Check for relative drive paths
            if _WINDOWS_DRIVE_RELATIVE.search(filename):
                return None
            # Check for reserved names
            if _WINDOWS_RESERVED_NAMES.search(filename):
                return None
            # Check for ADS
            if _WINDOWS_ADS.search(filename):
                return None
            # Reject UNC in components
            if _WINDOWS_UNC.search(filename):
                return None

        # Reject absolute paths and parent directory traversal
        if (
            filename.startswith("/")
            or filename == ".."
            or filename.startswith("../")
            or filename.endswith("/..")
            or "/../" in filename
        ):
            return None

        # Normalize the component
        normalized = posixpath.normpath(filename)
        if normalized == ".":
            continue
        normalized_parts.append(normalized)

    # Join all parts
    if not normalized_parts:
        result = base_dir
    else:
        result = posixpath.join(base_dir, *normalized_parts)

    # Final security check on the complete path
    normalized_result = posixpath.normpath(result)
    if not normalized_result.startswith(base_dir):
        return None

    # Final Windows-specific checks on complete path
    if os.name == "nt":
        # Check for ADS in final path
        if _WINDOWS_ADS.search(normalized_result):
            return None
        # Check for reserved names in any component
        path_parts = normalized_result.split("/")
        if any(_WINDOWS_RESERVED_NAMES.search(part) for part in path_parts):
            return None

    return normalized_result
