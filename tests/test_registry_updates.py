"""Tests for registry update functionality."""

import os
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from ostruct.cli.registry_updates import (
    UPDATE_CHECK_ENV_VAR,
    UPDATE_CHECK_INTERVAL_SECONDS,
    check_for_registry_updates,
    get_update_notification,
    should_check_for_updates,
)


# Mock classes that match the real openai-model-registry API
class MockRegistryUpdateStatus:
    def __init__(self, value: str):
        self.value = value


class RegistryUpdateResult:
    def __init__(self, status: str, message: str, success: bool = True):
        self.status = MockRegistryUpdateStatus(status)
        self.message = message
        self.success = success


class ModelRegistry:
    def check_for_updates(self) -> Any:
        return RegistryUpdateResult(
            status="ALREADY_CURRENT", message="Registry is up to date"
        )


class RegistryUpdateStatus:
    UPDATE_AVAILABLE = "update_available"
    ALREADY_CURRENT = "already_current"


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / "ostruct_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    with patch(
        "ostruct.cli.registry_updates._get_cache_dir"
    ) as mock_get_cache_dir:
        mock_get_cache_dir.return_value = cache_dir
        yield cache_dir


def test_should_check_for_updates_env_var():
    """Test that update checks can be disabled via environment variable."""
    with patch.dict(os.environ, {UPDATE_CHECK_ENV_VAR: "1"}):
        assert not should_check_for_updates()

    with patch.dict(os.environ, {UPDATE_CHECK_ENV_VAR: "true"}):
        assert not should_check_for_updates()

    with patch.dict(os.environ, {UPDATE_CHECK_ENV_VAR: "yes"}):
        assert not should_check_for_updates()

    with patch.dict(os.environ, {UPDATE_CHECK_ENV_VAR: ""}):
        # This would normally return True, but we need to mock the last check time
        with patch(
            "ostruct.cli.registry_updates._get_last_check_time"
        ) as mock_get_last_check_time:
            mock_get_last_check_time.return_value = None
            assert should_check_for_updates()


def test_should_check_for_updates_throttling():
    """Test that update checks are throttled based on the last check time."""
    # No previous check
    with patch(
        "ostruct.cli.registry_updates._get_last_check_time"
    ) as mock_get_last_check_time:
        mock_get_last_check_time.return_value = None
        assert should_check_for_updates()

    # Recent check
    with patch(
        "ostruct.cli.registry_updates._get_last_check_time"
    ) as mock_get_last_check_time:
        mock_get_last_check_time.return_value = time.time()
        assert not should_check_for_updates()

    # Old check
    with patch(
        "ostruct.cli.registry_updates._get_last_check_time"
    ) as mock_get_last_check_time:
        mock_get_last_check_time.return_value = (
            time.time() - UPDATE_CHECK_INTERVAL_SECONDS - 1
        )
        assert should_check_for_updates()


def test_check_for_registry_updates():
    """Test checking for registry updates."""
    # Mock should_check_for_updates to return False
    with patch(
        "ostruct.cli.registry_updates.should_check_for_updates"
    ) as mock_should_check:
        mock_should_check.return_value = False
        update_available, message = check_for_registry_updates()
        assert not update_available
        assert message is None

    # Mock should_check_for_updates to return True and registry.check_for_updates to return UPDATE_AVAILABLE
    with patch(
        "ostruct.cli.registry_updates.should_check_for_updates"
    ) as mock_should_check:
        mock_should_check.return_value = True
        with patch(
            "ostruct.cli.registry_updates._save_last_check_time"
        ) as mock_save:
            with patch(
                "ostruct.cli.registry_updates.ModelRegistry.get_instance"
            ) as mock_get_instance:
                mock_registry = MagicMock()
                mock_registry.check_for_updates.return_value = (
                    RegistryUpdateResult(
                        status=RegistryUpdateStatus.UPDATE_AVAILABLE,
                        message="Update available",
                        success=True,
                    )
                )
                mock_get_instance.return_value = mock_registry

                update_available, message = check_for_registry_updates()
                assert update_available
                assert message is not None
                assert "new model registry is available" in message
                mock_save.assert_called_once()

    # Mock should_check_for_updates to return True and registry.check_for_updates to return ALREADY_CURRENT
    with patch(
        "ostruct.cli.registry_updates.should_check_for_updates"
    ) as mock_should_check:
        mock_should_check.return_value = True
        with patch(
            "ostruct.cli.registry_updates._save_last_check_time"
        ) as mock_save:
            with patch(
                "ostruct.cli.registry_updates.ModelRegistry.get_instance"
            ) as mock_get_instance:
                mock_registry = MagicMock()
                mock_registry.check_for_updates.return_value = (
                    RegistryUpdateResult(
                        status=RegistryUpdateStatus.ALREADY_CURRENT,
                        message="Up to date",
                        success=True,
                    )
                )
                mock_get_instance.return_value = mock_registry

                update_available, message = check_for_registry_updates()
                assert not update_available
                assert message is None
                mock_save.assert_called_once()

    # Test exception handling
    with patch(
        "ostruct.cli.registry_updates.should_check_for_updates"
    ) as mock_should_check:
        mock_should_check.return_value = True
        with patch(
            "ostruct.cli.registry_updates.ModelRegistry.get_instance"
        ) as mock_get_instance:
            mock_get_instance.side_effect = Exception("Test error")
            update_available, message = check_for_registry_updates()
            assert not update_available
            assert message is None


def test_get_update_notification():
    """Test getting update notifications."""
    # No update available
    with patch(
        "ostruct.cli.registry_updates.check_for_registry_updates"
    ) as mock_check:
        mock_check.return_value = (False, None)
        assert get_update_notification() is None

    # Update available
    with patch(
        "ostruct.cli.registry_updates.check_for_registry_updates"
    ) as mock_check:
        mock_check.return_value = (True, "Test message")
        assert get_update_notification() == "Test message"

    # Exception handling
    with patch(
        "ostruct.cli.registry_updates.check_for_registry_updates"
    ) as mock_check:
        mock_check.side_effect = Exception("Test error")
        assert get_update_notification() is None
