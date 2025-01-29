"""Security type definitions and protocols."""

from pathlib import Path
from typing import List, Protocol


class SecurityManagerProtocol(Protocol):
    """Protocol defining the interface for security managers."""

    @property
    def base_dir(self) -> Path:
        """Get the base directory."""
        ...

    @property
    def allowed_dirs(self) -> List[Path]:
        """Get the list of allowed directories."""
        ...

    def add_allowed_dir(self, directory: str) -> None:
        """Add a directory to the set of allowed directories."""
        ...

    def add_allowed_dirs_from_file(self, file_path: str) -> None:
        """Add allowed directories from a file."""
        ...

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed."""
        ...

    def validate_path(self, path: str, purpose: str = "access") -> Path:
        """Validate and normalize a path."""
        ...

    def is_allowed_file(self, path: str) -> bool:
        """Check if file access is allowed."""
        ...

    def is_allowed_path(self, path_str: str) -> bool:
        """Check if string path is allowed."""
        ...

    def resolve_path(self, path: str) -> Path:
        """Resolve and validate a path.

        This is an alias for validate_path() for backward compatibility.
        """
        ...
