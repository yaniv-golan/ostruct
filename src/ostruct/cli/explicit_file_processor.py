"""Explicit File Routing System for ostruct CLI.

This module implements the explicit file routing system with tool-specific file handling.
Following the design philosophy "Explicit is better than implicit" - zero magic behavior.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .security.security_manager import SecurityManager

logger = logging.getLogger(__name__)


@dataclass
class FileForSpec:
    """Specification for files routed to specific tools."""

    tools: List[str]  # ["code-interpreter", "file-search", "template"]
    files: List[str]  # ["data.csv", "analysis.py"]


@dataclass
class ExplicitRouting:
    """Explicit routing configuration for files to tools."""

    template_files: List[str] = field(
        default_factory=list
    )  # Template access only
    code_interpreter_files: List[str] = field(
        default_factory=list
    )  # Code Interpreter uploads
    file_search_files: List[str] = field(
        default_factory=list
    )  # File Search uploads
    template_dirs: List[str] = field(
        default_factory=list
    )  # Template directory access
    code_interpreter_dirs: List[str] = field(
        default_factory=list
    )  # Code Interpreter directory uploads
    file_search_dirs: List[str] = field(
        default_factory=list
    )  # File Search directory uploads

    # Directory aliases for stable template variable names
    template_dir_aliases: List[tuple[str, str]] = field(
        default_factory=list
    )  # (alias_name, dir_path) for template access
    code_interpreter_dir_aliases: List[tuple[str, str]] = field(
        default_factory=list
    )  # (alias_name, dir_path) for code interpreter
    file_search_dir_aliases: List[tuple[str, str]] = field(
        default_factory=list
    )  # (alias_name, dir_path) for file search


@dataclass
class ProcessingResult:
    """Result of file routing processing."""

    routing: ExplicitRouting
    enabled_tools: Set[str]
    validated_files: Dict[str, List[str]]  # tool -> file paths
    auto_enabled_feedback: Optional[str] = None


class ExplicitFileProcessor:
    """Processor for explicit file routing with tool-specific handling."""

    def __init__(self, security_manager: SecurityManager):
        """Initialize the explicit file processor.

        Args:
            security_manager: Security manager for file validation
        """
        self.security_manager = security_manager

    async def process_file_routing(
        self, args: Dict[str, Any], explicit_tools: Optional[List[str]] = None
    ) -> ProcessingResult:
        """Process files with explicit tool routing.

        Args:
            args: CLI arguments containing file routing specifications
            explicit_tools: Explicitly specified tools to enable

        Returns:
            ProcessingResult with routing configuration and enabled tools

        Raises:
            ValueError: If routing configuration is invalid
        """
        logger.debug("=== Explicit File Routing Processing ===")

        # Phase 1: Parse file routing from CLI arguments
        routing = self._parse_file_routing_from_args(args)

        # Phase 2: Auto-detect and enable tools based on file routing
        enabled_tools, auto_feedback = self._resolve_tools(
            routing, explicit_tools
        )

        # Phase 3: Security validation for all files
        validated_routing = await self._validate_routing_security(routing)

        # Phase 4: Create validated file mappings
        validated_files = self._create_validated_file_mappings(
            validated_routing
        )

        logger.debug(
            f"File routing processed: {len(enabled_tools)} tools enabled"
        )

        return ProcessingResult(
            routing=validated_routing,
            enabled_tools=enabled_tools,
            validated_files=validated_files,
            auto_enabled_feedback=auto_feedback,
        )

    def _parse_file_routing_from_args(
        self, args: Dict[str, Any]
    ) -> ExplicitRouting:
        """Parse file routing specifications from CLI arguments.

        Args:
            args: CLI arguments

        Returns:
            ExplicitRouting configuration
        """
        routing = ExplicitRouting()

        # Legacy options (-f, -d) are handled separately in create_template_context_from_routing
        # to preserve their custom variable naming semantics
        legacy_files = args.get("files", [])
        legacy_dirs = args.get("dir", [])

        if legacy_files:
            logger.debug(
                f"Legacy -f flag detected: {len(legacy_files)} files (handled separately)"
            )

        if legacy_dirs:
            logger.debug(
                f"Legacy -d flag detected: {len(legacy_dirs)} dirs (handled separately)"
            )

        # Handle explicit tool routing - file options now have different formats

        # Template files (from -ft) - now single-argument auto-naming
        template_file_paths = args.get("template_files", [])
        for file_path in template_file_paths:
            if isinstance(file_path, str):
                routing.template_files.append(file_path)
            else:
                # Fallback for old format (shouldn't happen with new implementation)
                routing.template_files.append(str(file_path))

        # Template file aliases (from --fta) - two-argument explicit naming
        template_file_aliases = args.get("template_file_aliases", [])
        for name_path_tuple in template_file_aliases:
            if isinstance(name_path_tuple, tuple):
                name, path = name_path_tuple
                routing.template_files.append(str(path))
            else:
                routing.template_files.append(str(name_path_tuple))

        # Code Interpreter files (from -fc) - now single-argument auto-naming
        code_interpreter_file_paths = args.get("code_interpreter_files", [])
        for file_path in code_interpreter_file_paths:
            if isinstance(file_path, str):
                routing.code_interpreter_files.append(file_path)
            else:
                # Fallback for old format (shouldn't happen with new implementation)
                routing.code_interpreter_files.append(str(file_path))

        # Code interpreter file aliases (from --fca) - two-argument explicit naming
        code_interpreter_file_aliases = args.get(
            "code_interpreter_file_aliases", []
        )
        for name_path_tuple in code_interpreter_file_aliases:
            if isinstance(name_path_tuple, tuple):
                name, path = name_path_tuple
                routing.code_interpreter_files.append(str(path))
            else:
                routing.code_interpreter_files.append(str(name_path_tuple))

        # File Search files (from -fs) - now single-argument auto-naming
        file_search_file_paths = args.get("file_search_files", [])
        for file_path in file_search_file_paths:
            if isinstance(file_path, str):
                routing.file_search_files.append(file_path)
            else:
                # Fallback for old format (shouldn't happen with new implementation)
                routing.file_search_files.append(str(file_path))

        # File search file aliases (from --fsa) - two-argument explicit naming
        file_search_file_aliases = args.get("file_search_file_aliases", [])
        for name_path_tuple in file_search_file_aliases:
            if isinstance(name_path_tuple, tuple):
                name, path = name_path_tuple
                routing.file_search_files.append(str(path))
            else:
                routing.file_search_files.append(str(name_path_tuple))

        # Directory options - auto-naming (existing behavior)
        routing.template_dirs.extend(args.get("template_dirs", []))
        routing.code_interpreter_dirs.extend(
            args.get("code_interpreter_dirs", [])
        )
        routing.file_search_dirs.extend(args.get("file_search_dirs", []))

        # Directory aliases - custom naming for stable template variables
        template_dir_aliases = args.get("template_dir_aliases", [])
        for alias_name, dir_path in template_dir_aliases:
            routing.template_dir_aliases.append((alias_name, str(dir_path)))

        code_interpreter_dir_aliases = args.get(
            "code_interpreter_dir_aliases", []
        )
        for alias_name, dir_path in code_interpreter_dir_aliases:
            routing.code_interpreter_dir_aliases.append(
                (alias_name, str(dir_path))
            )

        file_search_dir_aliases = args.get("file_search_dir_aliases", [])
        for alias_name, dir_path in file_search_dir_aliases:
            routing.file_search_dir_aliases.append((alias_name, str(dir_path)))

        # Handle tool-specific file routing
        # New --file-for syntax: --file-for TOOL PATH
        tool_files = args.get("tool_files", [])
        valid_tools = {"code-interpreter", "file-search", "template"}

        for tool, file_path in tool_files:
            if tool not in valid_tools:
                raise ValueError(
                    f"Invalid tool '{tool}' in --file-for. "
                    f"Valid tools: {', '.join(sorted(valid_tools))}"
                )

            if tool == "code-interpreter":
                routing.code_interpreter_files.append(file_path)
            elif tool == "file-search":
                routing.file_search_files.append(file_path)
            elif tool == "template":
                routing.template_files.append(file_path)

        return routing

    def _resolve_tools(
        self,
        routing: ExplicitRouting,
        explicit_tools: Optional[List[str]] = None,
    ) -> tuple[Set[str], Optional[str]]:
        """Resolve which tools should be enabled based on file routing.

        Args:
            routing: File routing configuration
            explicit_tools: Explicitly specified tools

        Returns:
            Tuple of (enabled_tools_set, auto_enablement_feedback_message)
        """
        enabled_tools = set(explicit_tools or [])
        auto_enabled = set()

        # Auto-enable tools based on file routing
        if (
            routing.code_interpreter_files
            or routing.code_interpreter_dirs
            or routing.code_interpreter_dir_aliases
        ):
            if "code-interpreter" not in enabled_tools:
                auto_enabled.add("code-interpreter")
                enabled_tools.add("code-interpreter")

        if (
            routing.file_search_files
            or routing.file_search_dirs
            or routing.file_search_dir_aliases
        ):
            if "file-search" not in enabled_tools:
                auto_enabled.add("file-search")
                enabled_tools.add("file-search")

        # Generate feedback message for auto-enabled tools
        auto_feedback = None
        if auto_enabled:
            auto_feedback = f"ℹ️  Based on explicit routing, auto-enabled tools: {', '.join(sorted(auto_enabled))}"
            logger.info(auto_feedback)

        return enabled_tools, auto_feedback

    async def _validate_routing_security(
        self, routing: ExplicitRouting
    ) -> ExplicitRouting:
        """Validate file routing through security manager.

        Args:
            routing: File routing configuration

        Returns:
            Validated routing configuration

        Raises:
            SecurityError: If any files fail security validation
        """
        logger.debug("Validating file routing security")

        # Collect all files for validation
        all_files = []
        all_files.extend(routing.template_files)
        all_files.extend(routing.code_interpreter_files)
        all_files.extend(routing.file_search_files)

        # Collect all directories for validation
        all_dirs = []
        all_dirs.extend(routing.template_dirs)
        all_dirs.extend(routing.code_interpreter_dirs)
        all_dirs.extend(routing.file_search_dirs)

        # Add directory aliases (extract paths from tuples)
        all_dirs.extend(
            [dir_path for _, dir_path in routing.template_dir_aliases]
        )
        all_dirs.extend(
            [dir_path for _, dir_path in routing.code_interpreter_dir_aliases]
        )
        all_dirs.extend(
            [dir_path for _, dir_path in routing.file_search_dir_aliases]
        )

        # Validate files through security manager
        for file_path in all_files:
            try:
                # Use security manager's validation methods
                validated_path = self.security_manager.validate_path(file_path)
                # Check if it's actually a file
                if not validated_path.is_file():
                    raise ValueError(f"Path is not a file: {file_path}")
            except Exception as e:
                logger.error(
                    f"Security validation failed for file {file_path}: {e}"
                )
                raise

        # Validate directories through security manager
        for dir_path in all_dirs:
            try:
                validated_path = self.security_manager.validate_path(dir_path)
                # Check if it's actually a directory
                if not validated_path.is_dir():
                    raise ValueError(f"Path is not a directory: {dir_path}")
            except Exception as e:
                logger.error(
                    f"Security validation failed for directory {dir_path}: {e}"
                )
                raise

        logger.debug(
            f"Security validation passed for {len(all_files)} files and {len(all_dirs)} directories"
        )
        return routing

    def _create_validated_file_mappings(
        self, routing: ExplicitRouting
    ) -> Dict[str, List[str]]:
        """Create validated file mappings for each tool.

        Args:
            routing: Validated routing configuration

        Returns:
            Dictionary mapping tool names to file paths
        """
        validated_files: Dict[str, List[str]] = {
            "template": [],
            "code-interpreter": [],
            "file-search": [],
        }

        # Add files for each tool
        validated_files["template"].extend(routing.template_files)
        validated_files["code-interpreter"].extend(
            routing.code_interpreter_files
        )
        validated_files["file-search"].extend(routing.file_search_files)

        # Expand directories to individual files
        for dir_path in routing.template_dirs:
            validated_files["template"].extend(
                self._expand_directory(dir_path)
            )

        for dir_path in routing.code_interpreter_dirs:
            validated_files["code-interpreter"].extend(
                self._expand_directory(dir_path)
            )

        for dir_path in routing.file_search_dirs:
            validated_files["file-search"].extend(
                self._expand_directory(dir_path)
            )

        # Expand directory aliases to individual files
        for alias_name, dir_path in routing.template_dir_aliases:
            validated_files["template"].extend(
                self._expand_directory(dir_path)
            )

        for alias_name, dir_path in routing.code_interpreter_dir_aliases:
            validated_files["code-interpreter"].extend(
                self._expand_directory(dir_path)
            )

        for alias_name, dir_path in routing.file_search_dir_aliases:
            validated_files["file-search"].extend(
                self._expand_directory(dir_path)
            )

        # Remove duplicates while preserving order
        for tool in validated_files:
            validated_files[tool] = list(dict.fromkeys(validated_files[tool]))

        return validated_files

    def _expand_directory(self, dir_path: str) -> List[str]:
        """Expand directory to list of individual file paths.

        Args:
            dir_path: Directory path to expand

        Returns:
            List of file paths within the directory
        """
        try:
            path = Path(dir_path)
            if not path.exists() or not path.is_dir():
                logger.warning(
                    f"Directory not found or not a directory: {dir_path}"
                )
                return []

            files = []
            for file_path in path.iterdir():
                if file_path.is_file():
                    files.append(str(file_path))

            logger.debug(
                f"Expanded directory {dir_path} to {len(files)} files"
            )
            return files

        except Exception as e:
            logger.error(f"Failed to expand directory {dir_path}: {e}")
            return []

    def get_routing_summary(self, result: ProcessingResult) -> Dict[str, Any]:
        """Get a summary of the file routing configuration.

        Args:
            result: Processing result to summarize

        Returns:
            Dictionary with routing summary information
        """
        routing = result.routing

        summary = {
            "enabled_tools": list(result.enabled_tools),
            "file_counts": {
                "template": len(routing.template_files),
                "code_interpreter": len(routing.code_interpreter_files),
                "file_search": len(routing.file_search_files),
            },
            "directory_counts": {
                "template": len(routing.template_dirs),
                "code_interpreter": len(routing.code_interpreter_dirs),
                "file_search": len(routing.file_search_dirs),
            },
            "total_files": sum(
                len(files) for files in result.validated_files.values()
            ),
            "auto_enabled_feedback": result.auto_enabled_feedback,
        }

        return summary

    def validate_routing_consistency(
        self, routing: ExplicitRouting
    ) -> List[str]:
        """Validate routing configuration for consistency issues.

        Args:
            routing: Routing configuration to validate

        Returns:
            List of validation warnings/errors
        """
        issues = []

        # Check for files that don't exist
        all_files = (
            routing.template_files
            + routing.code_interpreter_files
            + routing.file_search_files
        )

        for file_path in all_files:
            if not Path(file_path).exists():
                issues.append(f"File not found: {file_path}")

        # Check for directories that don't exist
        all_dirs = (
            routing.template_dirs
            + routing.code_interpreter_dirs
            + routing.file_search_dirs
        )

        for dir_path in all_dirs:
            path = Path(dir_path)
            if not path.exists():
                issues.append(f"Directory not found: {dir_path}")
            elif not path.is_dir():
                issues.append(f"Path is not a directory: {dir_path}")

        # Check for duplicate files across different tools
        file_tool_mapping: Dict[str, str] = {}
        for tool, files in [
            ("template", routing.template_files),
            ("code-interpreter", routing.code_interpreter_files),
            ("file-search", routing.file_search_files),
        ]:
            for file_path in files:
                if file_path in file_tool_mapping:
                    issues.append(
                        f"File {file_path} is routed to multiple tools: {file_tool_mapping[file_path]} and {tool}"
                    )
                else:
                    file_tool_mapping[file_path] = tool

        return issues
