"""Cache path management utilities."""

import os
import stat
import sys
from pathlib import Path


def get_default_cache_dir() -> Path:
    """Get platform-specific cache directory."""
    if "OSTRUCT_CACHE_DIR" in os.environ:
        return Path(os.environ["OSTRUCT_CACHE_DIR"])

    if sys.platform == "darwin":  # macOS
        base = Path.home() / "Library" / "Caches"
    elif sys.platform == "win32":  # Windows
        base = Path.home() / "AppData" / "Local"
    else:  # Linux and others
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

    return base / "ostruct"


def get_default_cache_path() -> Path:
    """Get default path for upload cache database."""
    return get_default_cache_dir() / "upload_cache.sqlite"


def ensure_cache_dir_exists(cache_dir: Path) -> None:
    """Ensure cache directory exists with proper permissions."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Set restrictive permissions on Unix-like systems
    if sys.platform != "win32":
        cache_dir.chmod(stat.S_IRWXU)  # 700 permissions
