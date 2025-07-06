"""Tests for security context management."""

import pytest

from src.ostruct.cli.security.context import (
    get_current_security_manager,
    is_security_context_initialized,
    reset_security_context,
    set_current_security_manager,
)
from src.ostruct.cli.security.security_manager import SecurityManager
from src.ostruct.cli.security.types import PathSecurity


@pytest.mark.no_fs
class TestSecurityContext:
    """Test security context management."""

    def setup_method(self):
        """Reset security context before each test."""
        reset_security_context()

    def teardown_method(self):
        """Reset security context after each test."""
        reset_security_context()

    def test_context_not_initialized_initially(self):
        """Test that context is not initialized initially."""
        assert not is_security_context_initialized()

    def test_get_security_manager_before_init_raises_error(self):
        """Test that getting security manager before initialization raises error."""
        with pytest.raises(
            RuntimeError, match="SecurityManager not initialized"
        ):
            get_current_security_manager()

    def test_set_and_get_security_manager(self, tmp_path):
        """Test setting and getting security manager."""
        sm = SecurityManager(str(tmp_path), security_mode=PathSecurity.WARN)

        set_current_security_manager(sm)

        assert is_security_context_initialized()
        retrieved_sm = get_current_security_manager()
        assert retrieved_sm is sm
        assert retrieved_sm.base_dir == tmp_path

    def test_reset_security_context(self, tmp_path):
        """Test resetting security context."""
        sm = SecurityManager(str(tmp_path), security_mode=PathSecurity.WARN)
        set_current_security_manager(sm)

        assert is_security_context_initialized()

        reset_security_context()

        assert not is_security_context_initialized()
        with pytest.raises(RuntimeError):
            get_current_security_manager()
