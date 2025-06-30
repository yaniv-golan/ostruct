"""Attachment processing system for the new CLI interface.

This module processes the new target/alias attachment system and converts it to
the existing file routing structure for backward compatibility.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from .explicit_file_processor import ExplicitRouting, ProcessingResult
from .security import SecurityManager
from .types import CLIParams

logger = logging.getLogger(__name__)


@dataclass
class AttachmentSpec:
    """Specification for a single attachment with target and alias."""

    alias: str  # User-provided alias for the attachment
    path: Union[str, Path]  # File or directory path
    targets: Set[
        str
    ]  # Target tools: {"prompt", "code-interpreter", "file-search"}
    recursive: bool = False  # For directory attachments
    pattern: Optional[str] = None  # Glob pattern for directory attachments
    from_collection: bool = (
        False  # Whether this came from a --collect filelist
    )
    collection_base_alias: Optional[str] = (
        None  # Original collection alias for TSES
    )
    attachment_type: str = (
        "file"  # Original attachment type: "file", "dir", or "collection"
    )
    # Gitignore settings for directory expansion
    ignore_gitignore: bool = False  # Whether to ignore gitignore patterns
    gitignore_file: Optional[str] = None  # Custom gitignore file path


@dataclass
class ProcessedAttachments:
    """Processed attachments organized by target tool."""

    # Files/dirs for template access (prompt target)
    template_files: List[AttachmentSpec] = field(default_factory=list)
    template_dirs: List[AttachmentSpec] = field(default_factory=list)

    # Files/dirs for code interpreter uploads
    ci_files: List[AttachmentSpec] = field(default_factory=list)
    ci_dirs: List[AttachmentSpec] = field(default_factory=list)

    # Files/dirs for file search uploads
    fs_files: List[AttachmentSpec] = field(default_factory=list)
    fs_dirs: List[AttachmentSpec] = field(default_factory=list)

    # Mapping of aliases to their specs for template context
    alias_map: Dict[str, AttachmentSpec] = field(default_factory=dict)


class AttachmentProcessor:
    """Processes new attachment specifications into existing file routing."""

    def __init__(self, security_manager: SecurityManager):
        """Initialize the attachment processor.

        Args:
            security_manager: Security manager for file validation
        """
        self.security_manager = security_manager

    def process_attachments(
        self, attachments: List[Dict[str, Any]]
    ) -> ProcessedAttachments:
        """Process attachment specifications into organized structure.

        Args:
            attachments: List of attachment dictionaries from CLI parsing

        Returns:
            ProcessedAttachments with files organized by target tool

        Raises:
            ValueError: If attachment specifications are invalid
        """
        logger.debug("Processing %d attachments", len(attachments))
        processed = ProcessedAttachments()

        for attachment_dict in attachments:
            # Handle filelist syntax: path can be ("@", "filelist.txt") tuple
            path_value = attachment_dict["path"]
            if (
                isinstance(path_value, tuple)
                and len(path_value) == 2
                and path_value[0] == "@"
            ):
                # Process filelist collection
                filelist_specs = self._process_filelist(
                    path_value[1], attachment_dict
                )
                for spec in filelist_specs:
                    processed.alias_map[spec.alias] = spec
                    self._route_attachment(spec, processed)
            else:
                # Regular file/directory attachment
                spec = AttachmentSpec(
                    alias=attachment_dict["alias"],
                    path=Path(path_value),
                    targets=set(attachment_dict["targets"]),
                    recursive=attachment_dict.get("recursive", False),
                    pattern=attachment_dict.get("pattern"),
                    attachment_type=attachment_dict.get(
                        "attachment_type", "file"
                    ),
                    ignore_gitignore=attachment_dict.get(
                        "ignore_gitignore", False
                    ),
                    gitignore_file=attachment_dict.get("gitignore_file"),
                )

                # Validate file/directory with security manager
                validated_path = self.security_manager.validate_file_access(
                    spec.path, context=f"attachment {spec.alias}"
                )
                spec.path = validated_path

                # Add to alias map
                processed.alias_map[spec.alias] = spec

                # Route to appropriate target collections
                self._route_attachment(spec, processed)

        logger.debug(
            "Processed attachments: %d template files, %d template dirs, "
            "%d CI files, %d CI dirs, %d FS files, %d FS dirs",
            len(processed.template_files),
            len(processed.template_dirs),
            len(processed.ci_files),
            len(processed.ci_dirs),
            len(processed.fs_files),
            len(processed.fs_dirs),
        )

        return processed

    def _route_attachment(
        self, spec: AttachmentSpec, processed: ProcessedAttachments
    ) -> None:
        """Route a single attachment to appropriate target collections.

        Args:
            spec: Attachment specification to route
            processed: ProcessedAttachments to update
        """
        is_dir = Path(spec.path).is_dir()

        for target in spec.targets:
            if target == "prompt":
                if is_dir:
                    processed.template_dirs.append(spec)
                else:
                    processed.template_files.append(spec)
            elif target == "code-interpreter":
                if is_dir:
                    processed.ci_dirs.append(spec)
                else:
                    processed.ci_files.append(spec)
            elif target == "file-search":
                if is_dir:
                    processed.fs_dirs.append(spec)
                else:
                    processed.fs_files.append(spec)
            else:
                logger.warning(
                    "Unknown target '%s' for attachment %s", target, spec.alias
                )

    def _process_filelist(
        self, filelist_path: str, attachment_dict: Dict[str, Any]
    ) -> List[AttachmentSpec]:
        """Process @filelist.txt syntax for file collections.

        Args:
            filelist_path: Path to the filelist file
            attachment_dict: Original attachment specification

        Returns:
            List of AttachmentSpec objects for each file in the list

        Raises:
            ValueError: If filelist file is invalid or files cannot be processed
        """
        logger.debug("Processing filelist: %s", filelist_path)

        # Validate filelist file itself
        list_file = Path(filelist_path)
        validated_list_file = self.security_manager.validate_file_access(
            list_file, context=f"filelist for {attachment_dict['alias']}"
        )

        specs = []
        base_alias = attachment_dict["alias"]
        targets = set(attachment_dict["targets"])

        try:
            with open(validated_list_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    try:
                        # Resolve relative paths relative to filelist directory
                        file_path = Path(line)
                        if not file_path.is_absolute():
                            file_path = validated_list_file.parent / file_path

                        # Validate each file through security manager
                        validated_file = (
                            self.security_manager.validate_file_access(
                                file_path,
                                context=f"filelist {filelist_path}:{line_num}",
                            )
                        )

                        # Create unique alias for each file in collection
                        # Use base_alias with file index or filename
                        file_alias = f"{base_alias}_{line_num}"

                        # Create AttachmentSpec for each file
                        spec = AttachmentSpec(
                            alias=file_alias,
                            path=validated_file,
                            targets=targets,
                            recursive=False,  # Files from list are individual files
                            pattern=None,
                            from_collection=True,  # Mark as from collection
                            collection_base_alias=base_alias,  # Store original alias
                            attachment_type="collection",  # From --collect
                            ignore_gitignore=attachment_dict.get(
                                "ignore_gitignore", False
                            ),
                            gitignore_file=attachment_dict.get(
                                "gitignore_file"
                            ),
                        )

                        specs.append(spec)
                        logger.debug(
                            "Added file from filelist: %s -> %s",
                            validated_file,
                            file_alias,
                        )

                    except Exception as e:
                        logger.warning(
                            "Filelist %s:%d: Failed to process '%s': %s",
                            filelist_path,
                            line_num,
                            line,
                            e,
                        )
                        # Continue processing other files in permissive modes
                        if hasattr(self.security_manager, "security_mode"):
                            from .security.types import PathSecurity

                            if (
                                getattr(
                                    self.security_manager,
                                    "security_mode",
                                    None,
                                )
                                == PathSecurity.STRICT
                            ):
                                raise ValueError(
                                    f"Filelist processing failed at line {line_num}: {e}"
                                )

        except IOError as e:
            logger.error("Failed to read filelist %s: %s", filelist_path, e)
            raise ValueError(f"Cannot read filelist {filelist_path}: {e}")

        logger.debug(
            "Processed filelist %s: %d files loaded", filelist_path, len(specs)
        )

        return specs

    def convert_to_explicit_routing(
        self, processed: ProcessedAttachments
    ) -> ExplicitRouting:
        """Convert ProcessedAttachments to legacy ExplicitRouting format.

        Args:
            processed: ProcessedAttachments to convert

        Returns:
            ExplicitRouting compatible with existing file processor
        """
        routing = ExplicitRouting()

        # Convert template attachments
        routing.template_files = [
            str(spec.path) for spec in processed.template_files
        ]
        routing.template_dirs = [
            str(spec.path) for spec in processed.template_dirs
        ]
        routing.template_dir_aliases = [
            (spec.alias, str(spec.path)) for spec in processed.template_dirs
        ]

        # Convert code interpreter attachments
        routing.code_interpreter_files = [
            str(spec.path) for spec in processed.ci_files
        ]
        routing.code_interpreter_dirs = [
            str(spec.path) for spec in processed.ci_dirs
        ]
        routing.code_interpreter_dir_aliases = [
            (spec.alias, str(spec.path)) for spec in processed.ci_dirs
        ]

        # Convert file search attachments
        routing.file_search_files = [
            str(spec.path) for spec in processed.fs_files
        ]
        routing.file_search_dirs = [
            str(spec.path) for spec in processed.fs_dirs
        ]
        routing.file_search_dir_aliases = [
            (spec.alias, str(spec.path)) for spec in processed.fs_dirs
        ]

        return routing

    def create_processing_result(
        self, processed: ProcessedAttachments
    ) -> ProcessingResult:
        """Create ProcessingResult from ProcessedAttachments.

        Args:
            processed: ProcessedAttachments to convert

        Returns:
            ProcessingResult compatible with existing pipeline
        """
        routing = self.convert_to_explicit_routing(processed)

        # Determine enabled tools
        enabled_tools = set()
        if processed.template_files or processed.template_dirs:
            enabled_tools.add("template")
        if processed.ci_files or processed.ci_dirs:
            enabled_tools.add("code-interpreter")
        if processed.fs_files or processed.fs_dirs:
            enabled_tools.add("file-search")

        # Create validated files mapping
        validated_files = {
            "template": routing.template_files + routing.template_dirs,
            "code-interpreter": routing.code_interpreter_files
            + routing.code_interpreter_dirs,
            "file-search": routing.file_search_files
            + routing.file_search_dirs,
        }

        return ProcessingResult(
            routing=routing,
            enabled_tools=enabled_tools,
            validated_files=validated_files,
            auto_enabled_feedback=None,  # New system doesn't auto-enable
        )


def process_new_attachments(
    args: CLIParams, security_manager: SecurityManager
) -> Optional[ProcessingResult]:
    """Process new-style attachment arguments into file routing.

    This function checks for new attachment syntax in CLI args and processes
    them into the existing file routing system for backward compatibility.

    Args:
        args: CLI parameters (may contain new attachment syntax)
        security_manager: Security manager for file validation

    Returns:
        ProcessingResult if new attachments found, None otherwise
    """
    # Check if args contain new attachment syntax
    if not _has_new_attachment_syntax(args):
        return None

    logger.debug("Detected new attachment syntax, processing...")
    processor = AttachmentProcessor(security_manager)

    # Extract attachment specifications from args
    attachments = _extract_attachments_from_args(args)

    # Process attachments
    processed = processor.process_attachments(attachments)

    # Convert to processing result
    result = processor.create_processing_result(processed)

    logger.debug("New attachment processing complete")
    return result


def _has_new_attachment_syntax(args: CLIParams) -> bool:
    """Check if CLI args contain new attachment syntax.

    Args:
        args: CLI parameters to check

    Returns:
        True if new attachment syntax is present
    """
    # Check for new attachment-related keys
    new_syntax_keys = ["attaches", "dirs", "collects"]
    return any(args.get(key) for key in new_syntax_keys)


def _extract_attachments_from_args(args: CLIParams) -> List[Dict[str, Any]]:
    """Extract attachment specifications from CLI args.

    Args:
        args: CLI parameters containing attachment specifications

    Returns:
        List of attachment dictionaries with attachment_type added
    """
    attachments: List[Dict[str, Any]] = []

    # Get global flags that apply to ALL applicable attachments
    recursive_flag = args.get("recursive", False)
    pattern_flag = args.get("pattern", None)

    # Get gitignore settings from CLI args
    ignore_gitignore = args.get("ignore_gitignore", False)
    gitignore_file = args.get("gitignore_file")

    # Extract --attach specifications (file attachments)
    attaches = args.get("attaches", [])
    if attaches:
        for attach in attaches:
            attach_with_type = dict(attach)
            attach_with_type["attachment_type"] = "file"
            # Files don't support recursive/pattern flags, but add gitignore settings
            attach_with_type["ignore_gitignore"] = ignore_gitignore
            attach_with_type["gitignore_file"] = gitignore_file
            attachments.append(attach_with_type)

    # Extract --dir specifications (directory attachments)
    dirs = args.get("dirs", [])
    if dirs:
        for dir_spec in dirs:
            dir_with_type = dict(dir_spec)
            dir_with_type["attachment_type"] = "dir"

            # Apply global flags to ALL directories
            if recursive_flag:
                dir_with_type["recursive"] = True
            if pattern_flag:
                dir_with_type["pattern"] = pattern_flag

            # Add gitignore settings
            dir_with_type["ignore_gitignore"] = ignore_gitignore
            dir_with_type["gitignore_file"] = gitignore_file

            attachments.append(dir_with_type)

    # Extract --collect specifications (collection attachments)
    collects = args.get("collects", [])
    if collects:
        for collect in collects:
            collect_with_type = dict(collect)
            collect_with_type["attachment_type"] = "collection"

            # Apply global flags to ALL collections
            if recursive_flag:
                collect_with_type["recursive"] = True
            if pattern_flag:
                collect_with_type["pattern"] = pattern_flag

            # Add gitignore settings
            collect_with_type["ignore_gitignore"] = ignore_gitignore
            collect_with_type["gitignore_file"] = gitignore_file

            attachments.append(collect_with_type)

    logger.debug(
        "Extracted %d attachment specifications from args", len(attachments)
    )
    return attachments
