"""Security context management for ostruct CLI.

This module provides a global security context that eliminates the need for
multiple SecurityManager instances throughout the codebase. The context is
initialized once during CLI bootstrap and then accessed everywhere else.
"""

import warnings
from typing import Optional

from .security_manager import SecurityManager

# Global security context
_SECURITY_CTX: Optional[SecurityManager] = None
_CONTEXT_INITIALIZED: bool = False


def set_current_security_manager(sm: SecurityManager) -> None:
    """Set the current security manager for the global context.

    This should only be called once during CLI initialization.

    Args:
        sm: The configured SecurityManager instance
    """
    global _SECURITY_CTX, _CONTEXT_INITIALIZED
    _SECURITY_CTX = sm
    _CONTEXT_INITIALIZED = True


def get_current_security_manager() -> SecurityManager:
    """Get the current security manager from the global context.

    Returns:
        The configured SecurityManager instance

    Raises:
        RuntimeError: If SecurityManager has not been initialized
    """
    if _SECURITY_CTX is None:
        raise RuntimeError(
            "SecurityManager not initialized. This usually indicates a bug "
            "where security validation is attempted before CLI bootstrap."
        )
    return _SECURITY_CTX


def is_security_context_initialized() -> bool:
    """Check if the security context has been initialized.

    Returns:
        True if security context is ready, False otherwise
    """
    return _CONTEXT_INITIALIZED


def reset_security_context() -> None:
    """Reset the security context.

    This is primarily for testing purposes to ensure clean state
    between test runs.
    """
    global _SECURITY_CTX, _CONTEXT_INITIALIZED
    _SECURITY_CTX = None
    _CONTEXT_INITIALIZED = False


def warn_if_creating_security_manager_after_init() -> None:
    """Warn if SecurityManager is being created after context initialization.

    This helps identify places where ad-hoc SecurityManager instances
    are created instead of using the global context.
    """
    if _CONTEXT_INITIALIZED:
        warnings.warn(
            "Creating SecurityManager after global context initialization. "
            "Consider using get_current_security_manager() instead. "
            "This pattern will be deprecated in v1.0.",
            DeprecationWarning,
            stacklevel=3,
        )
