"""Utilities for processing file attachments."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .file_errors import (
    CollectionFileNotFoundError,
    FileFromCollectionNotFoundError,
    NoFilesMatchPatternError,
    validate_collection_file_exists,
    validate_directory_exists,
    validate_file_exists,
)
from .progress_utils import ProgressHandler


class AttachmentProcessor:
    """Process file attachments with support for aliases and progress tracking."""

    def __init__(
        self,
        support_aliases: bool = False,
        progress_handler: Optional[ProgressHandler] = None,
        validate_files: bool = False,
    ):
        """Initialize the attachment processor.

        Args:
            support_aliases: Whether to support alias parsing (alias:path format)
            progress_handler: Optional progress handler for reporting progress
            validate_files: Whether to validate file existence and permissions
        """
        self.support_aliases = support_aliases
        self.progress_handler = progress_handler
        self.validate_files = validate_files

    async def collect_files(
        self,
        files: Tuple[str, ...],
        directories: Tuple[str, ...],
        collections: Tuple[str, ...],
        pattern: Optional[str],
    ) -> List[Path]:
        """Collect files from various input sources.

        Args:
            files: Individual file paths (may include globs)
            directories: Directory paths
            collections: Collection file paths (prefixed with @)
            pattern: Optional global pattern filter

        Returns:
            List of resolved file paths

        Raises:
            FileNotFoundError: If any explicitly specified file doesn't exist
            DirectoryNotFoundError: If any directory doesn't exist
            CollectionFileNotFoundError: If any collection file doesn't exist
            NoFilesMatchPatternError: If glob patterns match no files
        """
        all_files: List[Path] = []
        processed_paths: set[Path] = set()

        # Process individual files
        for file_str in files:
            if self.support_aliases and ":" in file_str:
                # Extract alias and path
                alias, path_str = file_str.split(":", 1)
                path = Path(path_str)
            else:
                # No alias for FILES command
                path = Path(file_str)

            # Handle glob patterns
            if "*" in str(path) or "?" in str(path):
                # Expand glob pattern
                parent = (
                    path.parent if path.parent != Path(".") else Path.cwd()
                )
                pattern_name = path.name
                matched_files = []
                try:
                    for matched_file in parent.glob(pattern_name):
                        if matched_file.is_file():
                            # Validate each matched file only if validation is enabled
                            if self.validate_files:
                                validate_file_exists(matched_file)
                            resolved_path = matched_file.resolve()
                            if resolved_path not in processed_paths:
                                matched_files.append(resolved_path)
                                processed_paths.add(resolved_path)
                except Exception as e:
                    # If glob expansion fails, this is an error
                    # Don't fall back to treating as literal path
                    raise e

                # Check if glob pattern matched any files
                if not matched_files:
                    raise NoFilesMatchPatternError(str(path))

                all_files.extend(matched_files)
            else:
                # Regular file path - validate existence before adding only if validation is enabled
                if self.validate_files:
                    validate_file_exists(path)
                resolved_path = path.resolve()
                if resolved_path not in processed_paths:
                    all_files.append(resolved_path)
                    processed_paths.add(resolved_path)

        # Process directories recursively
        for dir_str in directories:
            if self.support_aliases and ":" in dir_str:
                # Extract alias and path
                alias, path_str = dir_str.split(":", 1)
                dir_path = Path(path_str)
            else:
                # No alias for FILES command
                dir_path = Path(dir_str)

            # Validate directory exists only if validation is enabled
            if self.validate_files:
                validate_directory_exists(dir_path)

            # Collect files from directory
            if dir_path.exists() and dir_path.is_dir():
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        resolved_path = file_path.resolve()
                        if resolved_path not in processed_paths:
                            all_files.append(resolved_path)
                            processed_paths.add(resolved_path)

        # Process collections
        for collection_str in collections:
            if collection_str.startswith("@"):
                collection_path = Path(collection_str[1:])
            else:
                # Handle alias:@file format
                if self.support_aliases and ":" in collection_str:
                    alias, file_part = collection_str.split(":", 1)
                    if file_part.startswith("@"):
                        collection_path = Path(file_part[1:])
                    else:
                        raise ValueError(
                            f"Collection must start with @: {collection_str}"
                        )
                else:
                    raise ValueError(
                        f"Collection must start with @: {collection_str}"
                    )

            # Validate collection file exists only if validation is enabled
            if self.validate_files:
                validate_collection_file_exists(collection_path)

            # Read and process collection file
            if collection_path.exists():
                try:
                    with open(collection_path, "r") as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if line and not line.startswith("#"):
                                file_path = Path(line)
                                # Validate files from collection only if validation is enabled
                                if self.validate_files:
                                    if not file_path.exists():
                                        raise FileFromCollectionNotFoundError(
                                            str(file_path),
                                            str(collection_path),
                                        )
                                resolved_path = file_path.resolve()
                                if resolved_path not in processed_paths:
                                    all_files.append(resolved_path)
                                    processed_paths.add(resolved_path)
                except Exception as e:
                    if self.validate_files and isinstance(
                        e, FileFromCollectionNotFoundError
                    ):
                        raise
                    # For other errors, re-raise as collection file error
                    raise CollectionFileNotFoundError(str(collection_path))

        # Apply global pattern filter if specified
        if pattern:
            filtered_files = []
            for file_path in all_files:
                if file_path.match(pattern):
                    filtered_files.append(file_path)
            all_files = filtered_files

        return all_files

    def collect_files_sync(
        self,
        files: Tuple[str, ...],
        directories: Tuple[str, ...],
        collections: Tuple[str, ...],
        pattern: Optional[str],
    ) -> List[Path]:
        """Synchronous version of collect_files for dry-run mode.

        This is identical to collect_files but without async/await to avoid
        Click context issues in dry-run mode.

        Args:
            files: Individual file paths (may include globs)
            directories: Directory paths
            collections: Collection file paths (prefixed with @)
            pattern: Optional global pattern filter

        Returns:
            List of resolved file paths

        Raises:
            FileNotFoundError: If any explicitly specified file doesn't exist
            DirectoryNotFoundError: If any directory doesn't exist
            CollectionFileNotFoundError: If any collection file doesn't exist
            NoFilesMatchPatternError: If glob patterns match no files
        """
        all_files: List[Path] = []
        processed_paths: set[Path] = set()

        # Process individual files
        for file_str in files:
            if self.support_aliases and ":" in file_str:
                # Extract alias and path
                alias, path_str = file_str.split(":", 1)
                path = Path(path_str)
            else:
                # No alias for FILES command
                path = Path(file_str)

            # Handle glob patterns
            if "*" in str(path) or "?" in str(path):
                # Expand glob pattern
                parent = (
                    path.parent if path.parent != Path(".") else Path.cwd()
                )
                pattern_name = path.name
                matched_files = []
                try:
                    for matched_file in parent.glob(pattern_name):
                        if matched_file.is_file():
                            # Validate each matched file only if validation is enabled
                            if self.validate_files:
                                validate_file_exists(matched_file)
                            resolved_path = matched_file.resolve()
                            if resolved_path not in processed_paths:
                                matched_files.append(resolved_path)
                                processed_paths.add(resolved_path)
                except Exception as e:
                    # If glob expansion fails, this is an error
                    # Don't fall back to treating as literal path
                    raise e

                # Check if glob pattern matched any files
                if not matched_files:
                    raise NoFilesMatchPatternError(str(path))

                all_files.extend(matched_files)
            else:
                # Regular file path - validate existence before adding only if validation is enabled
                if self.validate_files:
                    validate_file_exists(path)
                resolved_path = path.resolve()
                if resolved_path not in processed_paths:
                    all_files.append(resolved_path)
                    processed_paths.add(resolved_path)

        # Process directories recursively
        for dir_str in directories:
            if self.support_aliases and ":" in dir_str:
                # Extract alias and path
                alias, path_str = dir_str.split(":", 1)
                dir_path = Path(path_str)
            else:
                # No alias for FILES command
                dir_path = Path(dir_str)

            # Validate directory exists only if validation is enabled
            if self.validate_files:
                validate_directory_exists(dir_path)

            # Collect files from directory
            if dir_path.exists() and dir_path.is_dir():
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        resolved_path = file_path.resolve()
                        if resolved_path not in processed_paths:
                            all_files.append(resolved_path)
                            processed_paths.add(resolved_path)

        # Process collections
        for collection_str in collections:
            if collection_str.startswith("@"):
                collection_path = Path(collection_str[1:])
            else:
                # Handle alias:@file format
                if self.support_aliases and ":" in collection_str:
                    alias, file_part = collection_str.split(":", 1)
                    if file_part.startswith("@"):
                        collection_path = Path(file_part[1:])
                    else:
                        raise ValueError(
                            f"Collection must start with @: {collection_str}"
                        )
                else:
                    raise ValueError(
                        f"Collection must start with @: {collection_str}"
                    )

            # Validate collection file exists only if validation is enabled
            if self.validate_files:
                validate_collection_file_exists(collection_path)

            # Read and process collection file
            if collection_path.exists():
                try:
                    with open(collection_path, "r") as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if line and not line.startswith("#"):
                                file_path = Path(line)
                                # Validate files from collection only if validation is enabled
                                if self.validate_files:
                                    if not file_path.exists():
                                        raise FileFromCollectionNotFoundError(
                                            str(file_path),
                                            str(collection_path),
                                        )
                                resolved_path = file_path.resolve()
                                if resolved_path not in processed_paths:
                                    all_files.append(resolved_path)
                                    processed_paths.add(resolved_path)
                except Exception as e:
                    if self.validate_files and isinstance(
                        e, FileFromCollectionNotFoundError
                    ):
                        raise
                    # For other errors, re-raise as collection file error
                    raise CollectionFileNotFoundError(str(collection_path))

        # Apply global pattern filter if specified
        if pattern:
            filtered_files = []
            for file_path in all_files:
                if file_path.match(pattern):
                    filtered_files.append(file_path)
            all_files = filtered_files

        return all_files

    async def process_batch(
        self,
        files: List[Path],
        process_func: Callable,
        tools: Optional[Tuple[str, ...]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Process files in batch with progress tracking.

        Args:
            files: List of file paths to process
            process_func: Async function to process each file (upload, attach, etc.)
            tools: Optional tools parameter to pass to process_func
            dry_run: If True, skip actual processing

        Returns:
            Dictionary with results and errors
        """
        results = []
        errors = []

        if dry_run:
            # In dry-run mode, just return file info without processing
            return {
                "results": [{"path": str(f), "dry_run": True} for f in files],
                "errors": [],
                "summary": {
                    "total": len(files),
                    "processed": len(files),
                    "errors": 0,
                },
            }

        # Use progress handler if available
        if self.progress_handler:
            with self.progress_handler.batch_phase(
                "Processing files", "📂", len(files)
            ) as phase:
                for file_path in files:
                    try:
                        # Call the processing function
                        if tools:
                            result = await process_func(file_path, tools)
                        else:
                            result = await process_func(file_path)
                        results.append(result)

                        # Update progress
                        if self.progress_handler.detailed:
                            phase.advance(msg=f"Processed {file_path.name}")
                        else:
                            phase.advance()

                    except Exception as e:
                        error_msg = f"{file_path}: {str(e)}"
                        errors.append(error_msg)

                        # Update progress even on error
                        if self.progress_handler.detailed:
                            phase.advance(msg=f"Error with {file_path.name}")
                        else:
                            phase.advance()
        else:
            # No progress tracking - process files directly
            for file_path in files:
                try:
                    if tools:
                        result = await process_func(file_path, tools)
                    else:
                        result = await process_func(file_path)
                    results.append(result)
                except Exception as e:
                    error_msg = f"{file_path}: {str(e)}"
                    errors.append(error_msg)

        return {
            "results": results,
            "errors": errors,
            "summary": {
                "total": len(files),
                "processed": len(results),
                "errors": len(errors),
            },
        }
