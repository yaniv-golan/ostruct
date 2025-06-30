"""Gitignore support for ostruct file collection.

This module provides functionality to respect .gitignore files when collecting
files from directories, helping to automatically exclude unwanted files.
"""

import logging
from pathlib import Path
from typing import Optional

from pathspec import GitIgnoreSpec

logger = logging.getLogger(__name__)


class GitignoreManager:
    """Manages gitignore pattern matching for file collection."""

    def __init__(
        self,
        gitignore_path: Optional[str] = None,
        directory: Optional[str] = None,
    ) -> None:
        """Initialize with optional custom gitignore path or directory.

        Args:
            gitignore_path: Custom path to gitignore file
            directory: Directory to look for .gitignore file in

        Example:
            # Use .gitignore from specific directory
            manager = GitignoreManager(directory="/path/to/project")

            # Use custom gitignore file
            manager = GitignoreManager(gitignore_path="/path/to/.myignore")
        """
        self.spec = self._load_gitignore(gitignore_path, directory)
        self._patterns_loaded = self.spec is not None

    def _load_gitignore(
        self, path: Optional[str], directory: Optional[str]
    ) -> Optional[GitIgnoreSpec]:
        """Load gitignore patterns from file.

        Args:
            path: Custom gitignore file path
            directory: Directory to look for .gitignore in

        Returns:
            GitIgnoreSpec object or None if no patterns loaded
        """
        # Try custom path first
        if path and Path(path).exists():
            logger.debug("Loading gitignore from custom path: %s", path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return GitIgnoreSpec.from_lines(f)
            except (IOError, UnicodeDecodeError) as e:
                logger.warning("Failed to load gitignore from %s: %s", path, e)
                return None

        # Try .gitignore in specified directory
        if directory:
            gitignore_path = Path(directory) / ".gitignore"
            if gitignore_path.exists():
                logger.debug(
                    "Loading gitignore from directory: %s", gitignore_path
                )
                try:
                    with open(gitignore_path, "r", encoding="utf-8") as f:
                        return GitIgnoreSpec.from_lines(f)
                except (IOError, UnicodeDecodeError) as e:
                    logger.warning(
                        "Failed to load gitignore from %s: %s",
                        gitignore_path,
                        e,
                    )
                    return None

        logger.debug("No gitignore file found")
        return None

    def should_ignore(self, file_path: str) -> bool:
        """Check if file should be ignored based on gitignore patterns.

        Args:
            file_path: Relative path to check against patterns

        Returns:
            True if file should be ignored, False otherwise

        Example:
            manager = GitignoreManager(directory="/project")
            if manager.should_ignore("build/output.js"):
                print("File should be excluded")
        """
        if not self.spec:
            return False
        result = self.spec.match_file(file_path)
        if result:
            logger.debug("File ignored by gitignore: %s", file_path)
        return result

    @property
    def has_patterns(self) -> bool:
        """Check if gitignore patterns are loaded.

        Returns:
            True if patterns were successfully loaded, False otherwise
        """
        return self._patterns_loaded

    def get_pattern_count(self) -> int:
        """Get number of loaded patterns for debugging.

        Returns:
            Approximate number of patterns loaded

        Note:
            This is an estimate as pathspec doesn't expose pattern count directly
        """
        if not self.spec:
            return 0
        # pathspec doesn't expose pattern count directly, estimate from string representation
        return len(str(self.spec).split("\n")) if self.spec else 0
