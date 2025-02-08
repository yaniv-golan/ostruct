"""Security package for file access management.

This package provides a comprehensive set of security features for file access:
- Path normalization and validation
- Safe path joining
- Directory traversal prevention
- Symlink resolution with security checks
- Case sensitivity handling
- Temporary path management
"""

from .allowed_checker import is_path_in_allowed_dirs
from .case_manager import CaseManager
from .errors import (
    DirectoryNotFoundError,
    PathSecurityError,
    SecurityErrorReasons,
)
from .normalization import normalize_path
from .safe_joiner import safe_join
from .security_manager import SecurityManager

__all__ = [
    "normalize_path",
    "safe_join",
    "is_path_in_allowed_dirs",
    "CaseManager",
    "PathSecurityError",
    "DirectoryNotFoundError",
    "SecurityErrorReasons",
    "SecurityManager",
]
