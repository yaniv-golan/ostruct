"""ostruct-cli package."""

from importlib.metadata import version

try:
    __version__ = version("ostruct-cli")
except Exception:
    __version__ = "unknown"

__all__ = ["__version__"]
