"""Cache configuration utilities for ostruct.

Provides centralized configuration management for cache settings including TTL,
path resolution, and environment variable handling.
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default cache TTL in days
DEFAULT_CACHE_TTL_DAYS = 14


def get_cache_ttl_from_config(config: Optional[Dict[str, Any]] = None) -> int:
    """Get cache TTL from configuration with fallback to default.

    Priority order:
    1. config["cache"]["ttl_days"] if provided
    2. OSTRUCT_CACHE_TTL_DAYS environment variable
    3. DEFAULT_CACHE_TTL_DAYS constant

    Args:
        config: Optional configuration dictionary

    Returns:
        TTL in days as integer
    """
    # Check config dictionary first
    if config and "cache" in config and "ttl_days" in config["cache"]:
        try:
            ttl = int(config["cache"]["ttl_days"])
            logger.debug(f"[cache] Using TTL from config: {ttl} days")
            return ttl
        except (ValueError, TypeError) as e:
            logger.warning(
                f"[cache] Invalid TTL in config: {e}, using fallback"
            )

    # Check environment variable
    env_ttl = os.getenv("OSTRUCT_CACHE_TTL_DAYS")
    if env_ttl:
        try:
            ttl = int(env_ttl)
            logger.debug(f"[cache] Using TTL from environment: {ttl} days")
            return ttl
        except ValueError:
            logger.warning(
                f"[cache] Invalid OSTRUCT_CACHE_TTL_DAYS: {env_ttl}, using default"
            )

    # Use default
    logger.debug(f"[cache] Using default TTL: {DEFAULT_CACHE_TTL_DAYS} days")
    return DEFAULT_CACHE_TTL_DAYS


def get_cache_config_from_dict(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Extract complete cache configuration from config dictionary.

    Args:
        config: Optional configuration dictionary

    Returns:
        Dictionary with cache configuration including ttl_days, enabled, etc.
    """
    cache_config = {
        "ttl_days": get_cache_ttl_from_config(config),
        "enabled": True,  # Cache enabled by default
    }

    # Override with config values if present
    if config and "cache" in config:
        cache_dict = config["cache"]
        if "enabled" in cache_dict:
            cache_config["enabled"] = bool(cache_dict["enabled"])
        # ttl_days already handled by get_cache_ttl_from_config

    return cache_config
