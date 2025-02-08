"""Security type definitions and protocols."""

from contextlib import AbstractContextManager
from pathlib import Path
from typing import List, Protocol, Union


class SecurityManagerProtocol(Protocol):
    """Protocol defining the interface for security management."""

    @property
    def base_dir(self) -> Path:
        """Get the base directory."""
        ...

    @property
    def allowed_dirs(self) -> List[Path]:
        """Get the list of allowed directories."""
        ...

    def add_allowed_directory(self, directory: Union[str, Path]) -> None:
        """Add a directory to the set of allowed directories.

        Args:
            directory: The directory to add.

        Raises:
            DirectoryNotFoundError: If the directory doesn't exist.
        """
        ...

    def is_temp_path(self, path: Union[str, Path]) -> bool:
        """Check if a path is in the system's temporary directory.

        Args:
            path: The path to check.

        Returns:
            True if the path is a temporary path; False otherwise.

        Raises:
            PathSecurityError: If there's an error checking the path.
        """
        ...

    def is_path_allowed(self, path: Union[str, Path]) -> bool:
        """Check if a path is allowed based on security rules.

        Args:
            path: The path to check.

        Returns:
            True if the path is allowed; False otherwise.
        """
        ...

    def validate_path(self, path: Union[str, Path]) -> Path:
        """Validate a path against security rules.

        This method:
        1. Normalizes the path
        2. Checks for directory traversal
        3. Verifies the path is allowed
        4. Resolves symlinks securely if needed

        Args:
            path: The path to validate.

        Returns:
            A validated and (if applicable) resolved Path object.

        Raises:
            PathSecurityError: If the path fails any security check.
        """
        ...

    def resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve a path with security checks.

        This method:
        1. Normalizes the input
        2. Checks for existence
        3. Validates against security rules
        4. Resolves symlinks if needed

        Args:
            path: The path to resolve.

        Returns:
            A validated and resolved Path object.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            PathSecurityError: If the path fails validation.
        """
        ...

    def symlink_context(self) -> AbstractContextManager[None]:
        """Context manager for symlink resolution.

        This context manager ensures that symlink resolution state is properly
        cleaned up, even if an error occurs during resolution.

        Example:
            >>> with security_manager.symlink_context():
            ...     resolved = security_manager.resolve_path("/path/to/symlink")
        """
        ...
