"""File utilities for the CLI.

This module provides utilities for file operations with security controls:

1. File Information:
   - FileInfo class for safe file access and metadata
   - Support for file content caching
   - Automatic encoding detection

2. Path Handling:
   - Supports ~ expansion for home directory
   - Supports environment variable expansion
   - Security checks for file access
   - Requires explicit allowed directories for access outside CWD

3. Security Features:
   - Directory traversal prevention
   - Explicit allowed directory configuration
   - Temporary file access controls
   - Path validation and normalization

Usage Examples:
    Basic file access (from current directory):
    >>> info = FileInfo.from_path("var_name", "local_file.txt")
    >>> content = info.content

    Access home directory files (requires --allowed-dir):
    >>> info = FileInfo.from_path("var_name", "~/file.txt", allowed_dirs=["~/"])
    >>> content = info.content

    Multiple file collection:
    >>> files = collect_files(
    ...     file_args=["var=path.txt"],
    ...     allowed_dirs=["/allowed/path"],
    ...     recursive=True
    ... )

Security Notes:
    - Files must be in current directory or explicitly allowed directories
    - Use --allowed-dir to access files outside current directory
    - Home directory (~) is not automatically allowed
    - Environment variables are expanded in paths
"""

import codecs
import glob
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import chardet

from .errors import (
    DirectoryNotFoundError,
    OstructFileNotFoundError,
    PathSecurityError,
)
from .file_info import FileInfo
from .file_list import FileInfoList
from .security import SecurityManager
from .security.types import SecurityManagerProtocol

__all__ = [
    "FileInfo",  # Re-exported from file_info
    "SecurityManager",  # Re-exported from security
    "FileInfoList",  # Re-exported from file_list
    "collect_files",
    "collect_files_from_pattern",
    "collect_files_from_directory",
    "detect_encoding",
    "expand_path",
    "read_allowed_dirs_from_file",
]

logger = logging.getLogger(__name__)

# Type for values in template context
TemplateValue = Union[str, List[str], Dict[str, str]]


def _get_security_manager() -> Type[SecurityManagerProtocol]:
    """Get the SecurityManager class.

    Returns:
        The SecurityManager class type
    """
    return SecurityManager


def expand_path(path: str, force_absolute: bool = False) -> str:
    """Expand user home directory and environment variables in path.

    Args:
        path: Path that may contain ~ or environment variables
        force_absolute: Whether to force conversion to absolute path

    Returns:
        Expanded path, maintaining relative paths unless force_absolute=True
        or the path contains ~ or environment variables
    """
    # First expand user and environment variables
    expanded = os.path.expanduser(os.path.expandvars(path))

    # If the path hasn't changed and we're not forcing absolute, keep it relative
    if expanded == path and not force_absolute:
        return path

    # Otherwise return absolute path
    return os.path.abspath(expanded)


def collect_files_from_pattern(
    pattern: str,
    security_manager: SecurityManager,
) -> List[FileInfo]:
    """Collect files matching a glob pattern or exact file path.

    Args:
        pattern: Glob pattern or file path to match
        security_manager: Security manager for path validation

    Returns:
        List of FileInfo objects for matched files

    Raises:
        PathSecurityError: If any matched file is outside base directory
    """
    # First check if it's an exact file path
    if os.path.isfile(pattern):
        try:
            file_info = FileInfo.from_path(pattern, security_manager)
            return [file_info]
        except PathSecurityError:
            raise
        except Exception as e:
            logger.warning("Could not process file %s: %s", pattern, str(e))
            return []

    # If not an exact file, try glob pattern
    matched_paths = glob.glob(pattern, recursive=True)
    if not matched_paths:
        logger.debug("No files matched pattern: %s", pattern)
        return []

    # Create FileInfo objects
    files: List[FileInfo] = []
    for path in matched_paths:
        try:
            file_info = FileInfo.from_path(path, security_manager)
            files.append(file_info)
        except PathSecurityError:
            # Let security errors propagate
            raise
        except Exception as e:
            logger.warning("Could not process file %s: %s", path, str(e))

    return files


def collect_files_from_directory(
    directory: str,
    security_manager: SecurityManager,
    recursive: bool = False,
    allowed_extensions: Optional[List[str]] = None,
    **kwargs: Any,
) -> List[FileInfo]:
    """Collect files from a directory.

    Args:
        directory: Directory to collect files from
        security_manager: Security manager for path validation
        recursive: Whether to process subdirectories
        allowed_extensions: List of allowed file extensions (without dot)
        **kwargs: Additional arguments passed to FileInfo.from_path

    Returns:
        List of FileInfo objects

    Raises:
        DirectoryNotFoundError: If directory does not exist
        PathSecurityError: If directory or any file path is not allowed
    """
    logger.debug(
        "Collecting files from directory: %s (recursive=%s, extensions=%s)",
        directory,
        recursive,
        allowed_extensions,
    )

    # First validate and resolve the directory path
    try:
        abs_dir = str(security_manager.resolve_path(directory))
        logger.debug("Resolved directory path: %s", abs_dir)
    except PathSecurityError as e:
        logger.error(
            "Security violation in directory path: %s (%s)", directory, str(e)
        )
        raise

    if not os.path.isdir(abs_dir):
        logger.error("Path is not a directory: %s", abs_dir)
        raise DirectoryNotFoundError(f"Path is not a directory: {directory}")

    files: List[FileInfo] = []

    try:
        for root, dirs, filenames in os.walk(abs_dir):
            logger.debug("Walking directory: %s", root)
            logger.debug("Found subdirectories: %s", dirs)
            logger.debug("Found files: %s", filenames)

            # Validate current directory
            try:
                security_manager.validate_path(root)
            except PathSecurityError as e:
                logger.error(
                    "Security violation in subdirectory: %s (%s)", root, str(e)
                )
                raise

            if not recursive and root != abs_dir:
                logger.debug(
                    "Skipping subdirectory (non-recursive mode): %s", root
                )
                continue

            logger.debug("Scanning directory: %s", root)
            logger.debug("Current files collected: %d", len(files))

            for filename in filenames:
                # Get relative path from base directory
                abs_path = os.path.join(root, filename)
                try:
                    rel_path = os.path.relpath(
                        abs_path, security_manager.base_dir
                    )
                    logger.debug(
                        "Processing file: %s -> %s", abs_path, rel_path
                    )
                except ValueError as e:
                    logger.warning(
                        "Skipping file that can't be made relative: %s (error: %s)",
                        abs_path,
                        str(e),
                    )
                    continue

                # Check extension if filter is specified
                if allowed_extensions is not None:
                    ext = os.path.splitext(filename)[1].lstrip(".")
                    if ext not in allowed_extensions:
                        logger.debug(
                            "Skipping file with disallowed extension: %s",
                            filename,
                        )
                        continue

                # Validate file path before creating FileInfo
                try:
                    security_manager.validate_path(abs_path)
                except PathSecurityError as e:
                    logger.error(
                        "Security violation for file: %s (%s)",
                        abs_path,
                        str(e),
                    )
                    raise

                try:
                    # Use absolute path when creating FileInfo
                    file_info = FileInfo.from_path(
                        abs_path, security_manager=security_manager, **kwargs
                    )
                    files.append(file_info)
                    logger.debug("Added file to list: %s", abs_path)
                except PathSecurityError as e:
                    # Log and re-raise security errors immediately
                    logger.error(
                        "Security violation processing file: %s (%s)",
                        abs_path,
                        str(e),
                    )
                    raise
                except (OstructFileNotFoundError, PermissionError) as e:
                    # Skip legitimate file access errors
                    logger.warning(
                        "Skipping inaccessible file: %s (error: %s)",
                        rel_path,
                        str(e),
                    )

    except PathSecurityError:
        # Re-raise security errors without wrapping
        raise
    except Exception as e:
        logger.error("Error collecting files: %s", str(e))
        raise

    logger.debug("Collected %d files from directory %s", len(files), directory)
    return files


def _validate_and_split_mapping(
    mapping: tuple[str, Union[str, Path]], mapping_type: str
) -> tuple[str, str]:
    """Validate a name/path tuple mapping.

    Args:
        mapping: The mapping tuple (name, path)
        mapping_type: Type of mapping for error messages ("file", "pattern", or "directory")

    Returns:
        The same tuple of (name, path)

    Raises:
        ValueError: If mapping format is invalid
    """
    name, value = mapping

    if not name:
        raise ValueError(f"Empty name in {mapping_type} mapping")
    if not value:
        raise ValueError(f"Empty value in {mapping_type} mapping")

    return name, str(value)  # Convert Path to str if needed


def collect_files(
    file_mappings: Optional[List[Tuple[str, Union[str, Path]]]] = None,
    pattern_mappings: Optional[List[Tuple[str, Union[str, Path]]]] = None,
    dir_mappings: Optional[List[Tuple[str, Union[str, Path]]]] = None,
    dir_recursive: bool = False,
    dir_extensions: Optional[List[str]] = None,
    security_manager: Optional[SecurityManager] = None,
    **kwargs: Any,
) -> Dict[str, FileInfoList]:
    """Collect files from multiple sources.

    Args:
        file_mappings: List of file mappings as (name, path) tuples
        pattern_mappings: List of pattern mappings as (name, pattern) tuples
        dir_mappings: List of directory mappings as (name, directory) tuples
        dir_recursive: Whether to process directories recursively
        dir_extensions: List of file extensions to include in directory processing
        security_manager: Security manager instance
        **kwargs: Additional arguments passed to FileInfo.from_path

    Returns:
        Dictionary mapping variable names to FileInfoList instances

    Raises:
        ValueError: If no files are found or if there are duplicate mappings
        PathSecurityError: If a path is outside the base directory
        DirectoryNotFoundError: If a directory is not found
    """
    logger.debug(
        "Collecting files (recursive=%s, extensions=%s):\n  files=%s\n  patterns=%s\n  dirs=%s",
        dir_recursive,
        dir_extensions,
        file_mappings,
        pattern_mappings,
        dir_mappings,
    )

    if security_manager is None:
        security_manager = SecurityManager(base_dir=os.getcwd())
        logger.debug(
            "Created default security manager with base_dir=%s", os.getcwd()
        )
    else:
        logger.debug(
            "Using provided security manager with base_dir=%s and allowed_dirs=%s",
            security_manager.base_dir,
            security_manager.allowed_dirs,
        )

    # Normalize extensions by removing leading dots
    if dir_extensions:
        dir_extensions = [ext.lstrip(".") for ext in dir_extensions]
        logger.debug("Normalized extensions: %s", dir_extensions)

    files: Dict[str, FileInfoList] = {}

    # Process file mappings
    if file_mappings:
        for mapping in file_mappings:
            logger.debug("Processing file mapping: %s", mapping)
            name, path = _validate_and_split_mapping(mapping, "file")
            if name in files:
                raise ValueError(f"Duplicate file mapping: {name}")

            file_info = FileInfo.from_path(
                str(path), security_manager=security_manager, **kwargs
            )
            files[name] = FileInfoList([file_info], from_dir=False)
            logger.debug("Added single file mapping: %s -> %s", name, path)

    # Process pattern mappings
    if pattern_mappings:
        for mapping in pattern_mappings:
            logger.debug("Processing pattern mapping: %s", mapping)
            name, pattern = _validate_and_split_mapping(mapping, "pattern")
            if name in files:
                raise ValueError(f"Duplicate pattern mapping: {name}")

            try:
                matched_files = collect_files_from_pattern(
                    str(pattern), security_manager=security_manager, **kwargs
                )
            except PathSecurityError as e:
                logger.debug("Security error in pattern mapping: %s", str(e))
                raise PathSecurityError(
                    "Pattern mapping error: Access denied: "
                    f"{pattern} is outside base directory and not in allowed directories"
                ) from e

            if not matched_files:
                logger.warning("No files matched pattern: %s", pattern)
                continue

            files[name] = FileInfoList(matched_files, from_dir=False)
            logger.debug(
                "Added pattern mapping: %s -> %s (%d files)",
                name,
                pattern,
                len(matched_files),
            )

    # Process directory mappings
    if dir_mappings:
        for mapping in dir_mappings:
            logger.debug("Processing directory mapping: %s", mapping)
            name, directory = _validate_and_split_mapping(mapping, "directory")
            if name in files:
                raise ValueError(f"Duplicate directory mapping: {name}")

            logger.debug(
                "Processing directory mapping: %s -> %s", name, directory
            )
            try:
                dir_files = collect_files_from_directory(
                    directory=directory,
                    security_manager=security_manager,
                    recursive=dir_recursive,
                    allowed_extensions=dir_extensions,
                    **kwargs,
                )
            except PathSecurityError as e:
                logger.debug("Security error in directory mapping: %s", str(e))
                raise PathSecurityError(
                    "Directory mapping error: Access denied: "
                    f"{directory} is outside base directory and not in allowed directories",
                    path=directory,
                ) from e
            except DirectoryNotFoundError as e:
                logger.debug("Directory not found: %s", str(e))
                raise DirectoryNotFoundError(
                    f"Directory not found: {directory}"
                )

            if not dir_files:
                logger.warning("No files found in directory: %s", directory)
                files[name] = FileInfoList([], from_dir=True)
            else:
                files[name] = FileInfoList(dir_files, from_dir=True)
                logger.debug(
                    "Added directory mapping: %s -> %s (%d files)",
                    name,
                    directory,
                    len(dir_files),
                )

    if not files:
        logger.debug("No files found in any mappings")
        return files

    logger.debug("Collected files total mappings: %d", len(files))
    return files


def detect_encoding(file_path: str) -> str:
    """Detect the encoding of a file.

    Args:
        file_path: Path to the file to check

    Returns:
        str: The detected encoding (e.g. 'utf-8', 'utf-16', etc.)

    Raises:
        OSError: If there is an error reading the file
        ValueError: If the encoding cannot be detected
    """
    logger = logging.getLogger(__name__)
    logger.debug("Detecting encoding for file: %s", file_path)

    try:
        with open(file_path, "rb") as f:
            # Check for BOM markers first
            raw_data = f.read(4)
            if not raw_data:
                logger.debug("Empty file")
                return "utf-8"

            # Check for common BOMs
            if raw_data.startswith(codecs.BOM_UTF8):
                logger.debug("UTF-8 BOM detected")
                return "utf-8"
            elif raw_data.startswith(codecs.BOM_UTF16_LE):
                logger.debug("UTF-16 LE BOM detected")
                return "utf-16-le"
            elif raw_data.startswith(codecs.BOM_UTF16_BE):
                logger.debug("UTF-16 BE BOM detected")
                return "utf-16-be"
            elif raw_data.startswith(codecs.BOM_UTF32_LE):
                logger.debug("UTF-32 LE BOM detected")
                return "utf-32-le"
            elif raw_data.startswith(codecs.BOM_UTF32_BE):
                logger.debug("UTF-32 BE BOM detected")
                return "utf-32-be"

            # Read more data for chardet (up to 1MB)
            f.seek(0)
            raw_data = f.read(
                1024 * 1024
            )  # Read up to 1MB for better detection

            # Try chardet detection
            result = chardet.detect(raw_data)
            logger.debug("Chardet detection result: %s", result)

            if result and isinstance(result, dict) and result.get("encoding"):
                detected = str(result["encoding"]).lower()
                confidence = float(result.get("confidence", 0.0))

                # Handle ASCII detection
                if detected == "ascii":
                    logger.debug(
                        "ASCII detected, converting to UTF-8 (confidence: %f)",
                        confidence,
                    )
                    return "utf-8"

                # High confidence detection
                if confidence > 0.9:
                    logger.debug(
                        "High confidence encoding detected: %s (confidence: %f)",
                        detected,
                        confidence,
                    )
                    return detected

                # Medium confidence - validate with UTF-8 attempt
                if confidence > 0.6:
                    logger.debug(
                        "Medium confidence for %s (confidence: %f), validating",
                        detected,
                        confidence,
                    )
                    try:
                        raw_data.decode("utf-8")
                        logger.debug("Successfully validated as UTF-8")
                        return "utf-8"
                    except UnicodeDecodeError:
                        logger.debug(
                            "UTF-8 validation failed, using detected encoding: %s",
                            detected,
                        )
                        return detected

            # Low confidence or no detection - try UTF-8
            try:
                raw_data.decode("utf-8")
                logger.debug(
                    "No confident detection, but UTF-8 decode successful"
                )
                return "utf-8"
            except UnicodeDecodeError:
                if (
                    result
                    and isinstance(result, dict)
                    and result.get("encoding")
                ):
                    detected_encoding = str(result["encoding"]).lower()
                    logger.debug(
                        "Falling back to detected encoding with low confidence: %s",
                        detected_encoding,
                    )
                    return detected_encoding

                logger.warning(
                    "Could not confidently detect encoding for %s, defaulting to UTF-8",
                    file_path,
                )
                return "utf-8"

    except OSError as e:
        logger.error("Error reading file %s: %s", file_path, e)
        raise
    except Exception as e:
        logger.error(
            "Unexpected error detecting encoding for %s: %s",
            file_path,
            e,
        )
        raise ValueError(f"Failed to detect encoding: {e}")


def read_allowed_dirs_from_file(filepath: str) -> List[str]:
    """Reads a list of allowed directories from a file.

    Args:
        filepath: The path to the file.

    Returns:
        A list of allowed directories as absolute paths.

    Raises:
        OstructFileNotFoundError: If the file does not exist.
        ValueError: If the file contains invalid data.
    """
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except OSError as e:
        raise OstructFileNotFoundError(
            f"Error reading allowed directories from file: {filepath}: {e}"
        )

    allowed_dirs = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith(
            "#"
        ):  # Ignore empty lines and comments
            abs_path = os.path.abspath(line)
            if not os.path.isdir(abs_path):
                raise ValueError(
                    f"Invalid directory in allowed directories file '{filepath}': "
                    f"'{line}' is not a directory or does not exist."
                )
            allowed_dirs.append(abs_path)
    return allowed_dirs
