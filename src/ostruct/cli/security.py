"""Security package for file access management.

This module re-exports the public API of the security package.
"""

from .security.allowed_checker import is_path_in_allowed_dirs
from .security.case_manager import CaseManager
from .security.errors import (
    DirectoryNotFoundError,
    PathSecurityError,
    SecurityErrorReasons,
)
from .security.normalization import normalize_path
from .security.safe_joiner import safe_join
from .security.security_manager import SecurityManager
from .security.symlink_resolver import resolve_symlink

__all__ = [
    'normalize_path',
    'safe_join',
    'is_path_in_allowed_dirs',
    'resolve_symlink',
    'CaseManager',
    'PathSecurityError',
    'DirectoryNotFoundError',
    'SecurityErrorReasons',
    'SecurityManager',
] 