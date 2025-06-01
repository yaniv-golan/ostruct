"""Registry update checks for ostruct CLI.

This module provides functionality to check for updates to the model registry
and notify users when updates are available.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple

# Model Registry Integration - Using external openai-model-registry library
from openai_model_registry import ModelRegistry


# For compatibility with existing code
class RegistryUpdateStatus:
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    ALREADY_CURRENT = "ALREADY_CURRENT"


logger = logging.getLogger(__name__)

# Constants
UPDATE_CHECK_ENV_VAR = "OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS"
UPDATE_CHECK_INTERVAL_SECONDS = (
    86400  # Check for updates once per day (24 hours)
)
LAST_CHECK_CACHE_FILE = ".ostruct_registry_check"


def _get_cache_dir() -> Path:
    """Get the cache directory for ostruct.

    Returns:
        Path: Path to the cache directory
    """
    # Use XDG_CACHE_HOME if available, otherwise use ~/.cache
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        base_dir = Path(xdg_cache_home)
    else:
        base_dir = Path.home() / ".cache"

    cache_dir = base_dir / "ostruct"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_last_check_time() -> Optional[float]:
    """Get the timestamp of the last update check.

    Returns:
        Optional[float]: Timestamp of the last check, or None if never checked
    """
    cache_file = _get_cache_dir() / LAST_CHECK_CACHE_FILE

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r") as f:
            data = json.load(f)
            last_check_time = data.get("last_check_time")
            return (
                float(last_check_time) if last_check_time is not None else None
            )
    except (json.JSONDecodeError, IOError, OSError):
        return None


def _save_last_check_time() -> None:
    """Save the current time as the last update check time."""
    cache_file = _get_cache_dir() / LAST_CHECK_CACHE_FILE

    try:
        data = {"last_check_time": time.time()}
        with open(cache_file, "w") as f:
            json.dump(data, f)
    except (IOError, OSError) as e:
        logger.debug(f"Failed to save last check time: {e}")


def should_check_for_updates() -> bool:
    """Determine if we should check for registry updates.

    Returns:
        bool: True if update checks are enabled, False otherwise
    """
    # Allow users to disable update checks via environment variable
    if os.environ.get(UPDATE_CHECK_ENV_VAR, "").lower() in (
        "1",
        "true",
        "yes",
    ):
        logger.debug(
            "Registry update checks disabled via environment variable"
        )
        return False

    # Check if we've checked recently
    last_check_time = _get_last_check_time()
    if last_check_time is not None:
        time_since_last_check = time.time() - last_check_time
        if time_since_last_check < UPDATE_CHECK_INTERVAL_SECONDS:
            logger.debug(
                f"Skipping update check, last check was {time_since_last_check:.1f} seconds ago"
            )
            return False

    return True


def check_for_registry_updates() -> Tuple[bool, Optional[str]]:
    """Check if there are updates available for the model registry.

    This function is designed to be non-intrusive and fail gracefully.

    Returns:
        Tuple[bool, Optional[str]]: (update_available, message)
            - update_available: True if an update is available
            - message: A message to display to the user, or None if no update is available
    """
    if not should_check_for_updates():
        return False, None

    try:
        registry = ModelRegistry.get_instance()
        result = registry.check_for_updates()

        # Save the check time regardless of the result
        _save_last_check_time()

        if result.status.value == "update_available":
            return True, (
                "A new model registry is available. "
                "This may include support for new models or features. "
                "Run 'ostruct update-registry' to update."
            )

        return False, None
    except Exception as e:
        # Ensure any errors don't affect normal operation
        logger.debug(f"Error checking for registry updates: {e}")
        return False, None


def get_update_notification() -> Optional[str]:
    """Get a notification message if registry updates are available.

    This function is designed to be called from the CLI to provide
    a non-intrusive notification to users.

    Returns:
        Optional[str]: A notification message, or None if no notification is needed
    """
    try:
        update_available, message = check_for_registry_updates()
        if update_available and message:
            return str(message)  # Explicit cast to ensure str type
        return None
    except Exception as e:
        # Ensure any errors don't affect normal operation
        logger.debug(f"Error getting update notification: {e}")
        return None
