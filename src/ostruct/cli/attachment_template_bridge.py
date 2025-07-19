"""Bridge between new attachment system and template processing.

This module converts processed attachments into template context variables
while maintaining compatibility with existing template patterns.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .attachment_processor import AttachmentSpec, ProcessedAttachments
from .file_info import FileInfo, FileRoutingIntent, LazyLoadError
from .file_list import FileInfoList
from .file_utils import collect_files_from_directory
from .security import SecurityManager
from .template_schema import DotDict

logger = logging.getLogger(__name__)

# Template variable name constants
UTILITY_VARIABLES = {
    "files",
    "file_count",
    "has_files",
}

SYSTEM_CONFIG_VARIABLES = {
    "current_model",
    "stdin",
    "web_search_enabled",
    "code_interpreter_enabled",
    "auto_download_enabled",
    "code_interpreter_config",
}


class ValidationResult:
    """Result of file size validation with errors and warnings."""

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.total_size: int = 0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0

    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return not self.has_errors()


class FileSizeValidator:
    """Validates file sizes before processing to prevent memory exhaustion."""

    def __init__(
        self,
        max_individual: Optional[int] = None,
        max_total: Optional[int] = None,
    ):
        """Initialize file size validator.

        Args:
            max_individual: Maximum size per individual file in bytes (None for no limit)
            max_total: Maximum total size for all files in bytes (None for no limit)
        """
        # Use the same logic as FileInfo for consistency
        if max_individual is None:
            from .file_info import FileInfo

            max_individual = FileInfo._get_default_max_size()
        if max_total is None:
            max_total = self._get_default_total_size()

        self.max_individual = max_individual
        self.max_total = max_total

    @staticmethod
    def _get_default_total_size() -> Optional[int]:
        """Get default total size limit from environment.

        Returns:
            Default maximum total file size in bytes, or None for no limit
        """
        import os

        from .constants import DefaultConfig

        total_limit_env = os.getenv("OSTRUCT_TEMPLATE_TOTAL_LIMIT")
        if total_limit_env is not None:
            if total_limit_env.lower() in ("none", "unlimited", ""):
                return None
            try:
                return int(total_limit_env)
            except ValueError:
                logger.warning(
                    f"Invalid OSTRUCT_TEMPLATE_TOTAL_LIMIT value '{total_limit_env}', using default limit"
                )
                # Fall through to default

        # Default: 500MB total limit for DoS protection
        default_total = DefaultConfig.TEMPLATE["max_total_size"]
        return int(default_total) if default_total is not None else None

    def validate_file_list(self, files: List[Path]) -> ValidationResult:
        """Validate list of files against size limits.

        Args:
            files: List of file paths to validate

        Returns:
            ValidationResult with errors, warnings, and total size
        """
        results = ValidationResult()
        total_size = 0

        for file_path in files:
            try:
                size = file_path.stat().st_size
                total_size += size

                # Check individual file size limit (if set)
                if (
                    self.max_individual is not None
                    and size > self.max_individual
                ):
                    results.add_warning(
                        f"File {file_path} ({size:,} bytes) exceeds individual limit "
                        f"({self.max_individual:,} bytes) - will use lazy loading"
                    )

                # Check total size limit (if set)
                if self.max_total is not None and total_size > self.max_total:
                    results.add_error(
                        f"Total file size ({total_size:,} bytes) exceeds limit "
                        f"({self.max_total:,} bytes) after processing {file_path}"
                    )
                    break

            except OSError as e:
                results.add_error(f"Cannot access {file_path}: {e}")

        results.total_size = total_size
        return results

    def validate_single_file(self, file_path: Path) -> ValidationResult:
        """Validate a single file against size limits.

        Args:
            file_path: Path to file to validate

        Returns:
            ValidationResult for the single file
        """
        return self.validate_file_list([file_path])


class ProgressiveLoader:
    """Loads files progressively based on size and usage priority."""

    def __init__(self, validator: FileSizeValidator):
        """Initialize progressive loader.

        Args:
            validator: File size validator to use
        """
        self.validator = validator
        self._load_queue: List[Tuple[int, FileInfo]] = []
        self._loaded_count = 0

    def create_lazy_content(
        self, file_info: FileInfo, priority: int = 0, strict_mode: bool = False
    ) -> FileInfo:
        """Create lazy content with loading priority.

        Args:
            file_info: FileInfo for the file
            priority: Loading priority (higher = loaded first)
            strict_mode: If True, raise exceptions instead of returning fallback content

        Returns:
            FileInfo instance with lazy loading enabled
        """
        lazy_content = file_info.enable_lazy_loading(
            max_size=self.validator.max_individual,
            strict_mode=strict_mode,
        )

        # Pre-check size and determine loading strategy
        try:
            if lazy_content.check_size():
                # Small file - can load immediately if requested
                self._load_queue.append((priority, lazy_content))
                logger.debug(
                    f"Added {file_info.path} to load queue (priority {priority})"
                )
            else:
                # Large file - will always use lazy loading
                logger.info(
                    f"Large file {file_info.path} will use lazy loading"
                )
        except LazyLoadError as e:
            logger.warning(f"Cannot check size of {file_info.path}: {e}")

        return lazy_content

    def preload_high_priority(self, max_files: int = 5) -> int:
        """Preload high-priority small files.

        Args:
            max_files: Maximum number of files to preload

        Returns:
            Number of files successfully preloaded
        """
        # Sort by priority (highest first)
        self._load_queue.sort(key=lambda x: x[0], reverse=True)

        preloaded = 0
        for i, (priority, lazy_content) in enumerate(
            self._load_queue[:max_files]
        ):
            try:
                # In strict mode, don't preload content - it will be loaded on demand
                # This prevents dry-run from failing when only metadata is accessed
                if getattr(lazy_content, "_FileInfo__strict_mode", False):
                    logger.debug(
                        f"Skipping preload for {lazy_content.path} (strict mode)"
                    )
                    continue

                # Trigger loading by accessing content safely
                _ = lazy_content.load_safe()
                if getattr(lazy_content, "_FileInfo__loaded", False):
                    preloaded += 1
                    logger.debug(f"Preloaded {lazy_content.path}")
            except Exception as e:
                logger.debug(f"Failed to preload {lazy_content.path}: {e}")

        self._loaded_count = preloaded
        return preloaded

    def get_load_summary(self) -> Dict[str, Any]:
        """Get summary of loading operations.

        Returns:
            Dictionary with loading statistics
        """
        return {
            "total_queued": len(self._load_queue),
            "preloaded": self._loaded_count,
            "pending": len(self._load_queue) - self._loaded_count,
            "max_individual_size": self.validator.max_individual,
            "max_total_size": self.validator.max_total,
        }


class AttachmentTemplateContext:
    """Helper class for building template context from attachments."""

    size_validator: Optional[FileSizeValidator]
    progressive_loader: Optional[ProgressiveLoader]

    def __init__(
        self,
        security_manager: SecurityManager,
        use_progressive_loading: bool = True,
        max_file_size: Optional[int] = None,
    ):
        """Initialize context builder.

        Args:
            security_manager: Security manager for file validation
            use_progressive_loading: Enable progressive loading with size validation
            max_file_size: Maximum individual file size for template access (None for no limit)
        """
        self.security_manager = security_manager
        self.use_progressive_loading = use_progressive_loading
        self.max_file_size = max_file_size

        # Initialize size validator and progressive loader if enabled
        if self.use_progressive_loading:
            self.size_validator = FileSizeValidator(
                max_individual=max_file_size
            )
            self.progressive_loader = ProgressiveLoader(self.size_validator)
        else:
            self.size_validator = None
            self.progressive_loader = None

    def build_template_context(
        self,
        processed_attachments: ProcessedAttachments,
        base_context: Optional[Dict[str, Any]] = None,
        strict_mode: bool = False,
    ) -> Dict[str, Any]:
        """Build template context from processed attachments.

        Args:
            processed_attachments: Processed attachment specifications
            base_context: Existing context to extend (optional)
            strict_mode: If True, raise exceptions for file loading errors

        Returns:
            Template context dictionary with attachment-derived variables
        """
        logger.debug("Building template context from attachments")

        context = base_context.copy() if base_context else {}

        # Add individual alias-based variables
        for alias, spec in processed_attachments.alias_map.items():
            context[alias] = self._create_attachment_variable(
                spec, strict_mode=strict_mode
            )

        # Add utility variables for template iteration
        all_files = self._collect_all_files(processed_attachments)

        context["files"] = all_files
        context["file_count"] = len(all_files)
        context["has_files"] = len(all_files) > 0

        # Note: Legacy compatibility removed per CLI redesign plan (breaking change)

        # Perform file size validation if progressive loading is enabled
        validation_result = None
        if self.use_progressive_loading and self.size_validator:
            # Collect all file paths for validation
            all_file_paths = []
            for file_info in all_files:
                all_file_paths.append(Path(file_info.abs_path))

            validation_result = self.size_validator.validate_file_list(
                all_file_paths
            )

            # Log validation results
            if validation_result.has_errors():
                for error in validation_result.errors:
                    logger.error(f"File size validation error: {error}")

            if validation_result.has_warnings():
                for warning in validation_result.warnings:
                    logger.warning(f"File size validation warning: {warning}")

            # Perform progressive loading for high-priority files
            if self.progressive_loader:
                preloaded_count = (
                    self.progressive_loader.preload_high_priority()
                )
                logger.debug(
                    f"Preloaded {preloaded_count} high-priority files"
                )

        # Add attachment metadata
        metadata = {
            "aliases": list(processed_attachments.alias_map.keys()),
            "template_file_count": len(processed_attachments.template_files),
            "template_dir_count": len(processed_attachments.template_dirs),
            "ci_file_count": len(processed_attachments.ci_files),
            "ci_dir_count": len(processed_attachments.ci_dirs),
            "fs_file_count": len(processed_attachments.fs_files),
            "fs_dir_count": len(processed_attachments.fs_dirs),
            "progressive_loading_enabled": self.use_progressive_loading,
        }

        # Add size validation metadata if available
        if validation_result:
            metadata.update(
                {
                    "total_file_size": validation_result.total_size,
                    "size_validation_errors": validation_result.errors,
                    "size_validation_warnings": validation_result.warnings,
                    "size_validation_passed": validation_result.is_valid(),
                }
            )

        # Add progressive loading summary if available
        if self.progressive_loader:
            metadata.update(
                {"loading_summary": self.progressive_loader.get_load_summary()}
            )

        context["_attachments"] = metadata

        logger.debug(
            f"Built template context with {len(processed_attachments.alias_map)} aliases, "
            f"{len(all_files)} total files, progressive loading: {self.use_progressive_loading}"
        )

        return context

    def debug_attachment_context(
        self,
        context: Dict[str, Any],
        processed_attachments: ProcessedAttachments,
        show_detailed: bool = False,
    ) -> None:
        """Debug template context created from attachments.

        Args:
            context: Template context to debug
            processed_attachments: Source attachment specifications
            show_detailed: Whether to show detailed debugging output
        """
        import click

        click.echo("🔗 Attachment-Based Template Context Debug:", err=True)
        click.echo("=" * 60, err=True)

        # Show attachment summary
        click.echo("📎 Attachment Summary:", err=True)
        for alias, spec in processed_attachments.alias_map.items():
            targets_str = ", ".join(sorted(spec.targets))
            path_type = "directory" if Path(spec.path).is_dir() else "file"
            click.echo(f"  {alias}: {path_type} → {targets_str}", err=True)
            if show_detailed:
                click.echo(f"    Path: {spec.path}", err=True)
                if spec.recursive:
                    click.echo(f"    Recursive: {spec.recursive}", err=True)
                if spec.pattern:
                    click.echo(f"    Pattern: {spec.pattern}", err=True)

        # Show template variable mapping
        click.echo("\n📝 Template Variables Created:", err=True)
        attachment_vars = []
        utility_vars = []
        user_defined_vars = []
        system_config_vars = []

        for key, value in context.items():
            if key in processed_attachments.alias_map:
                attachment_vars.append(key)
            elif key.startswith("_") or key in UTILITY_VARIABLES:
                utility_vars.append(key)
            elif key in SYSTEM_CONFIG_VARIABLES:
                system_config_vars.append(key)
            elif isinstance(value, FileInfo) and getattr(
                value, "_FileInfo__lazy_loading", False
            ):
                user_defined_vars.append(key)
            else:
                user_defined_vars.append(key)

        if attachment_vars:
            click.echo("  Attachment aliases:", err=True)
            for var in sorted(attachment_vars):
                value = context[var]
                if isinstance(value, FileInfo) and getattr(
                    value, "_FileInfo__lazy_loading", False
                ):
                    # Show user-friendly file information instead of class name
                    try:
                        file_size = value.actual_size or 0
                        if file_size > 0:
                            size_str = f"{file_size:,} bytes"
                        else:
                            size_str = "unknown size"
                        click.echo(
                            f"    {var}: file {value.name} ({size_str})",
                            err=True,
                        )
                    except Exception:
                        click.echo(
                            f"    {var}: file {getattr(value, 'name', 'unknown')}",
                            err=True,
                        )
                elif hasattr(value, "__len__"):
                    # FileInfoList or similar collections
                    try:
                        count = len(value)
                        if count == 1:
                            click.echo(f"    {var}: 1 file", err=True)
                        else:
                            click.echo(f"    {var}: {count} files", err=True)
                    except Exception:
                        click.echo(f"    {var}: file collection", err=True)
                else:
                    # Fallback to type name for other cases
                    var_type = type(value).__name__
                    click.echo(f"    {var}: {var_type}", err=True)

        if user_defined_vars:
            click.echo("  User-defined variables:", err=True)
            for var in sorted(user_defined_vars):
                if not var.startswith("_"):  # Skip internal variables
                    if isinstance(context[var], (int, bool)):
                        click.echo(f"    {var}: {context[var]}", err=True)
                    else:
                        var_type = type(context[var]).__name__
                        click.echo(f"    {var}: {var_type}", err=True)

        if utility_vars:
            click.echo("  Utility variables:", err=True)
            for var in sorted(utility_vars):
                if isinstance(context[var], (int, bool)):
                    click.echo(f"    {var}: {context[var]}", err=True)
                else:
                    var_type = type(context[var]).__name__
                    click.echo(f"    {var}: {var_type}", err=True)

        if system_config_vars:
            click.echo("  System configuration variables:", err=True)
            for var in sorted(system_config_vars):
                if isinstance(context[var], (int, bool)):
                    click.echo(f"    {var}: {context[var]}", err=True)
                else:
                    var_type = type(context[var]).__name__
                    click.echo(f"    {var}: {var_type}", err=True)

        # Show file statistics
        total_files = context.get("file_count", 0)
        click.echo("\n📊 File Statistics:", err=True)
        click.echo(f"  Total files: {total_files}", err=True)
        click.echo(
            f"  Template files: {context.get('template_file_count', 0)}",
            err=True,
        )
        click.echo(
            f"  Code interpreter files: {context.get('ci_file_count', 0)}",
            err=True,
        )
        click.echo(
            f"  File search files: {context.get('fs_file_count', 0)}", err=True
        )

        if show_detailed and total_files > 0:
            click.echo("\n📄 File Details:", err=True)
            files_list = context.get("files", [])
            for i, file_info in enumerate(
                files_list[:10]
            ):  # Show first 10 files
                click.echo(
                    f"  {i + 1}. {file_info.path} ({file_info.routing_intent.value})",
                    err=True,
                )
            if len(files_list) > 10:
                click.echo(
                    f"  ... and {len(files_list) - 10} more files", err=True
                )

        click.echo("=" * 60, err=True)

    def _create_attachment_variable(
        self, spec: AttachmentSpec, strict_mode: bool = False
    ) -> Union[FileInfo, FileInfoList, DotDict]:
        """Create template variable for a single attachment.

        Args:
            spec: Attachment specification
            strict_mode: If True, raise exceptions for file loading errors

        Returns:
            Template variable (file content, file list, or directory info)
        """
        # Detect remote URL attachments (http/https) – treat as virtual file
        if isinstance(spec.path, str) and str(spec.path).startswith(
            ("http://", "https://")
        ):
            routing_type = (
                "user-data" if "user-data" in spec.targets else "template"
            )
            routing_intent = (
                FileRoutingIntent.USER_DATA
                if "user-data" in spec.targets
                else FileRoutingIntent.TEMPLATE_ONLY
            )

            file_info = FileInfo.from_path(
                spec.path,
                self.security_manager,
                routing_type=routing_type,
                routing_intent=routing_intent,
                parent_alias=spec.alias,
                relative_path=os.path.basename(spec.path),
                base_path="",
                from_collection=False,
                attachment_type=spec.attachment_type,
            )

            return file_info.enable_lazy_loading(
                max_size=self.max_file_size,
                strict_mode=True,
            )

        path = Path(spec.path)

        if path.is_file():
            """Create variable for a single file attachment.

            For files that are *only* targeted at Code Interpreter (i.e., not
            also routed to the prompt), we avoid eager content loading and set
            the routing metadata appropriately to prevent template-only
            warnings.
            """

            # Decide routing metadata based on attachment targets
            if (
                "code-interpreter" in spec.targets
                and "prompt" not in spec.targets
            ):
                routing_type = "code-interpreter"
                routing_intent = FileRoutingIntent.CODE_INTERPRETER
                # Avoid pre-loading large CI files into the prompt
                lazy_strict_mode = True
                # Priority value is irrelevant because strict_mode=True below
                # guarantees the file will be skipped by the pre-loader.
                preload_priority = 5
            elif (
                "file-search" in spec.targets and "prompt" not in spec.targets
            ):
                routing_type = "file-search"
                routing_intent = FileRoutingIntent.FILE_SEARCH
                # File Search files don't need content loaded into prompt
                lazy_strict_mode = True
                preload_priority = 3  # Medium priority for file search files
            elif "user-data" in spec.targets and "prompt" not in spec.targets:
                routing_type = "user-data"
                routing_intent = FileRoutingIntent.USER_DATA
                # User-data files don't need content loaded into prompt (will raise error)
                lazy_strict_mode = True
                preload_priority = 4  # Medium-low priority for user-data files
            else:
                routing_type = "template"
                routing_intent = FileRoutingIntent.TEMPLATE_ONLY
                lazy_strict_mode = strict_mode
                preload_priority = 1  # High priority for template files

            file_info = FileInfo.from_path(
                str(path),
                self.security_manager,
                routing_type=routing_type,
                routing_intent=routing_intent,
                parent_alias=spec.alias,
                relative_path=path.name,
                base_path=str(path.parent),
                from_collection=False,
                attachment_type=spec.attachment_type,
            )

            # Use progressive loader if available, otherwise create LazyFileContent directly
            if self.progressive_loader:
                return self.progressive_loader.create_lazy_content(
                    file_info,
                    priority=preload_priority,
                    strict_mode=lazy_strict_mode,
                )
            else:
                return file_info.enable_lazy_loading(
                    max_size=self.max_file_size,
                    strict_mode=lazy_strict_mode,
                )

        elif path.is_dir():
            # Directory - create FileInfoList with file expansion
            files = self._expand_directory(spec)
            return FileInfoList(files)

        else:
            logger.warning(
                f"Attachment path {spec.path} is neither file nor directory"
            )
            # Return empty DotDict for invalid paths
            return DotDict(
                {
                    "path": str(spec.path),
                    "error": f"Invalid path: {spec.path}",
                    "content": f"[Invalid path: {spec.path}]",
                }
            )

    def _expand_directory(self, spec: AttachmentSpec) -> List[FileInfo]:
        """Expand directory attachment into list of files.

        Args:
            spec: Directory attachment specification

        Returns:
            List of FileInfo objects for files in directory
        """
        try:
            # Use the gitignore-aware file collection function
            files = collect_files_from_directory(
                directory=str(spec.path),
                security_manager=self.security_manager,
                recursive=spec.recursive,
                allowed_extensions=None,  # No extension filtering for directory attachments
                routing_type="template",
                routing_intent=FileRoutingIntent.TEMPLATE_ONLY,
                ignore_gitignore=spec.ignore_gitignore,
                gitignore_file=spec.gitignore_file,
                parent_alias=spec.alias,
                base_path=str(spec.path),
                from_collection=False,
                attachment_type=spec.attachment_type,
            )

            # Apply pattern filtering if specified (after gitignore filtering)
            if spec.pattern:
                from fnmatch import fnmatch

                filtered_files = []
                for file_info in files:
                    # Check pattern against the relative path from the directory
                    rel_path = file_info.relative_path or file_info.name
                    if fnmatch(rel_path, spec.pattern):
                        filtered_files.append(file_info)
                files = filtered_files

            logger.debug(
                f"Expanded directory {spec.path} to {len(files)} files "
                f"(recursive={spec.recursive}, pattern={spec.pattern}, "
                f"ignore_gitignore={spec.ignore_gitignore})"
            )

        except Exception as e:
            logger.error(f"Error expanding directory {spec.path}: {e}")
            files = []

        return files

    def _collect_all_files(
        self, processed_attachments: ProcessedAttachments
    ) -> FileInfoList:
        """Collect all file attachments into a single list.

        Args:
            processed_attachments: Processed attachment specifications

        Returns:
            FileInfoList containing all files from all attachments
        """
        all_files = []

        # Collect files from all attachment types
        for spec in processed_attachments.template_files:
            if Path(spec.path).is_file():
                try:
                    file_info = FileInfo.from_path(
                        str(spec.path),
                        self.security_manager,
                        routing_type="template",
                        routing_intent=FileRoutingIntent.TEMPLATE_ONLY,
                        parent_alias=spec.collection_base_alias or spec.alias,
                        relative_path=Path(spec.path).name,
                        base_path=str(Path(spec.path).parent),
                        from_collection=spec.from_collection,
                        attachment_type=spec.attachment_type,
                    )
                    all_files.append(file_info)
                except Exception as e:
                    logger.warning(f"Could not add file {spec.path}: {e}")

        # Expand directories and add their files
        for spec in processed_attachments.template_dirs:
            dir_files = self._expand_directory(spec)
            all_files.extend(dir_files)

        # Include CI and FS files for template access as well (metadata only)
        for spec in processed_attachments.ci_files:
            if Path(spec.path).is_file():
                try:
                    file_info = FileInfo.from_path(
                        str(spec.path),
                        self.security_manager,
                        routing_type="code-interpreter",
                        routing_intent=FileRoutingIntent.CODE_INTERPRETER,
                        parent_alias=spec.collection_base_alias or spec.alias,
                        relative_path=Path(spec.path).name,
                        base_path=str(Path(spec.path).parent),
                        from_collection=spec.from_collection,
                        attachment_type=spec.attachment_type,
                    )
                    all_files.append(file_info)
                except Exception as e:
                    logger.warning(f"Could not add file {spec.path}: {e}")

        for spec in processed_attachments.fs_files:
            if Path(spec.path).is_file():
                try:
                    file_info = FileInfo.from_path(
                        str(spec.path),
                        self.security_manager,
                        routing_type="file-search",
                        routing_intent=FileRoutingIntent.FILE_SEARCH,
                        parent_alias=spec.collection_base_alias or spec.alias,
                        relative_path=Path(spec.path).name,
                        base_path=str(Path(spec.path).parent),
                        from_collection=spec.from_collection,
                        attachment_type=spec.attachment_type,
                    )
                    all_files.append(file_info)
                except Exception as e:
                    logger.warning(f"Could not add FS file {spec.path}: {e}")

        # Include user-data files for template access (metadata only, content blocked)
        for spec in processed_attachments.ud_files:
            if Path(spec.path).is_file():
                try:
                    file_info = FileInfo.from_path(
                        str(spec.path),
                        self.security_manager,
                        routing_type="user-data",
                        routing_intent=FileRoutingIntent.USER_DATA,
                        parent_alias=spec.collection_base_alias or spec.alias,
                        relative_path=Path(spec.path).name,
                        base_path=str(Path(spec.path).parent),
                        from_collection=spec.from_collection,
                        attachment_type=spec.attachment_type,
                    )
                    all_files.append(file_info)
                except Exception as e:
                    logger.warning(f"Could not add UD file {spec.path}: {e}")

        return FileInfoList(all_files)


def build_template_context_from_attachments(
    processed_attachments: ProcessedAttachments,
    security_manager: SecurityManager,
    base_context: Optional[Dict[str, Any]] = None,
    strict_mode: bool = False,
    max_file_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Build template context from processed attachments.

    This is the main entry point for converting attachment specifications
    into template context variables.

    Args:
        processed_attachments: Processed attachment specifications
        security_manager: Security manager for file validation
        base_context: Existing context to extend (optional)
        strict_mode: If True, raise exceptions for file loading errors
        max_file_size: Maximum individual file size for template access (None for no limit)

    Returns:
        Template context dictionary
    """
    context_builder = AttachmentTemplateContext(
        security_manager, max_file_size=max_file_size
    )
    return context_builder.build_template_context(
        processed_attachments, base_context, strict_mode=strict_mode
    )
