"""Shared file attachment and upload processing utilities."""

import fnmatch
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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
                try:
                    for matched_file in parent.glob(pattern_name):
                        if matched_file.is_file():
                            resolved_path = matched_file.resolve()
                            if resolved_path not in processed_paths:
                                all_files.append(resolved_path)
                                processed_paths.add(resolved_path)
                except Exception:
                    # If glob fails, treat as literal path
                    if path.exists() and path.is_file():
                        resolved_path = path.resolve()
                        if resolved_path not in processed_paths:
                            all_files.append(resolved_path)
                            processed_paths.add(resolved_path)
            else:
                # Regular file path
                if path.exists() and path.is_file():
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

            if dir_path.exists() and dir_path.is_dir():
                # Recursively collect files from directory
                try:
                    for file_path in dir_path.rglob("*"):
                        if file_path.is_file():
                            resolved_path = file_path.resolve()
                            if resolved_path not in processed_paths:
                                all_files.append(resolved_path)
                                processed_paths.add(resolved_path)
                except Exception:
                    # Skip directories that can't be read
                    continue

        # Process collections (@filelist.txt format)
        for collection_str in collections:
            if self.support_aliases and ":" in collection_str:
                # Parse alias:@filelist for RUN command
                alias, path_str = collection_str.split(":", 1)
                collection_path = Path(path_str.lstrip("@"))
            else:
                # Remove @ prefix for FILES command
                collection_path = Path(collection_str.lstrip("@"))

            if collection_path.exists() and collection_path.is_file():
                try:
                    with open(collection_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                file_path = Path(line)
                                if file_path.exists() and file_path.is_file():
                                    resolved_path = file_path.resolve()
                                    if resolved_path not in processed_paths:
                                        all_files.append(resolved_path)
                                        processed_paths.add(resolved_path)
                except Exception:
                    # Skip collections that can't be read
                    continue

        # Apply pattern filter if specified
        if pattern:
            filtered_files = []
            for file_path in all_files:
                if fnmatch.fnmatch(file_path.name, pattern):
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
