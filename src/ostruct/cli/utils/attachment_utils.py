"""Shared file attachment and upload processing utilities."""

import fnmatch
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
    """Unified processor for file collection and batch processing.

    This class handles the common patterns of collecting files from various sources
    (individual files, directories, collections) and processing them in batches,
    with support for aliases (in RUN command) vs. no aliases (in FILES command).

    Usage:
        # For FILES command (no aliases)
        processor = AttachmentProcessor(support_aliases=False, progress_handler=handler)
        files = await processor.collect_files(files, dirs, collections, pattern)
        results = await processor.process_batch(files, upload_func, tools)

        # For RUN command (with aliases)
        processor = AttachmentProcessor(support_aliases=True, progress_handler=handler)
        files = await processor.collect_files(files, dirs, collections, pattern)
        results = await processor.process_batch(files, attach_func, tools)
    """

    def __init__(
        self,
        support_aliases: bool = False,
        progress_handler: Optional[ProgressHandler] = None,
    ) -> None:
        """Initialize the attachment processor.

        Args:
            support_aliases: True for RUN command (parse alias:path), False for FILES command
            progress_handler: Optional progress handler for batch operations
        """
        self.support_aliases = support_aliases
        self.progress_handler = progress_handler

    async def collect_files(
        self,
        files: Tuple[str, ...],
        directories: Tuple[str, ...],
        collections: Tuple[str, ...],
        pattern: Optional[str] = None,
    ) -> List[Path]:
        """Collect files from various sources with deduplication.

        Args:
            files: Individual file paths or patterns (may include aliases if supported)
            directories: Directory paths to scan recursively
            collections: Collection files (@filelist.txt format)
            pattern: Optional glob pattern to filter collected files

        Returns:
            List of unique file paths
        """
        all_files = []
        processed_paths = set()  # For deduplication

        # Process individual files
        for file_str in files:
            if self.support_aliases and ":" in file_str:
                # Parse alias:path for RUN command
                alias, path_str = file_str.split(":", 1)
                # Store alias for later use if needed
                # For now, just process the path
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
                            # Validate each matched file
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
                # Regular file path - validate existence before adding
                validate_file_exists(path)
                resolved_path = path.resolve()
                if resolved_path not in processed_paths:
                    all_files.append(resolved_path)
                    processed_paths.add(resolved_path)

        # Process directories recursively
        for dir_str in directories:
            if self.support_aliases and ":" in dir_str:
                # Parse alias:path for RUN command
                alias, path_str = dir_str.split(":", 1)
                dir_path = Path(path_str)
            else:
                # No alias for FILES command
                dir_path = Path(dir_str)

            # Validate directory exists and is accessible
            validate_directory_exists(dir_path)

            # Recursively collect files from directory
            dir_files = []
            try:
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        # Validate each file in directory
                        validate_file_exists(file_path)
                        resolved_path = file_path.resolve()
                        if resolved_path not in processed_paths:
                            dir_files.append(resolved_path)
                            processed_paths.add(resolved_path)
            except Exception as e:
                # Re-raise validation errors, but allow other directory errors
                if hasattr(e, "exit_code"):
                    raise e
                # For other errors (permission issues, etc.), continue processing
                pass

            # Note: Empty directories are allowed (warning case, not error)

        # Process collections (@filelist.txt format)
        for collection_str in collections:
            if self.support_aliases and ":" in collection_str:
                # Parse alias:@filelist for RUN command
                alias, path_str = collection_str.split(":", 1)
                collection_path = Path(path_str.lstrip("@"))
            else:
                # Remove @ prefix for FILES command
                collection_path = Path(collection_str.lstrip("@"))

            # Validate collection file exists
            validate_collection_file_exists(collection_path)

            try:
                with open(collection_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            file_path = Path(line)
                            # Validate each file in collection
                            try:
                                validate_file_exists(file_path)
                            except Exception as e:
                                # Convert to collection-specific error
                                raise FileFromCollectionNotFoundError(
                                    str(file_path), str(collection_path)
                                ) from e

                            resolved_path = file_path.resolve()
                            if resolved_path not in processed_paths:
                                all_files.append(resolved_path)
                                processed_paths.add(resolved_path)
            except FileFromCollectionNotFoundError:
                # Re-raise collection-specific errors
                raise
            except Exception as e:
                # For other errors (encoding, permission), convert to file error
                if hasattr(e, "exit_code"):
                    raise e
                # For IO errors, this becomes a permission error on the collection file
                raise CollectionFileNotFoundError(str(collection_path)) from e

        # Apply pattern filter if specified
        if pattern:
            # Check if pattern is being used as primary input method
            is_pattern_primary = not (files or directories or collections)

            if is_pattern_primary:
                # Pattern is primary input - collect files from current directory
                cwd = Path.cwd()
                pattern_files = []
                for file_path in cwd.rglob("*"):
                    if file_path.is_file() and fnmatch.fnmatch(
                        file_path.name, pattern
                    ):
                        validate_file_exists(file_path)
                        resolved_path = file_path.resolve()
                        if resolved_path not in processed_paths:
                            pattern_files.append(resolved_path)
                            processed_paths.add(resolved_path)

                if not pattern_files:
                    raise NoFilesMatchPatternError(pattern)

                all_files.extend(pattern_files)
            else:
                # Pattern is a filter on collected files
                filtered_files = []
                for file_path in all_files:
                    if fnmatch.fnmatch(file_path.name, pattern):
                        filtered_files.append(file_path)
                all_files = filtered_files
                # Note: Empty result after filtering is a warning, not an error

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
