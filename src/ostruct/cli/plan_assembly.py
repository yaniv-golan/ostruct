"""Plan assembly for execution plans and run summaries.

This module provides the single source of truth for plan data structures
following UNIFIED GUIDELINES to prevent logic drift between JSON and human output.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .attachment_processor import ProcessedAttachments


class PlanAssembler:
    """Single source of truth for execution plan data structure.

    This class ensures consistent plan format across all output types
    (JSON, human-readable, etc.) by providing a single build method.
    """

    @staticmethod
    def validate_download_configuration(
        enabled_tools: Optional[set[str]] = None,
        ci_config: Optional[Dict[str, Any]] = None,
        expected_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate download configuration for dry-run.

        Args:
            enabled_tools: Set of enabled tools
            ci_config: Code Interpreter configuration
            expected_files: List of expected output filenames (optional)

        Returns:
            Dictionary with validation results
        """
        validation: Dict[str, Any] = {
            "enabled": False,
            "directory": None,
            "writable": False,
            "conflicts": [],
            "issues": [],
        }

        # Check if Code Interpreter is enabled
        if not enabled_tools or "code-interpreter" not in enabled_tools:
            return validation

        validation["enabled"] = True

        # Get download directory

        download_dir = "./downloads"  # Default
        if ci_config:
            download_dir = ci_config.get("output_directory", download_dir)

        validation["directory"] = download_dir

        # Check directory permissions
        try:
            download_path = Path(download_dir)
            parent_dir = download_path.parent

            # Check if parent exists and is writable
            if parent_dir.exists():
                # Try to create a test file in parent
                test_file = parent_dir / ".ostruct_write_test"
                try:
                    test_file.touch()
                    test_file.unlink()

                    # If download dir exists, check it specifically
                    if download_path.exists():
                        if not download_path.is_dir():
                            validation["issues"].append(
                                f"Path exists but is not a directory: {download_dir}"
                            )
                        else:
                            # Test write in actual directory
                            test_file = download_path / ".ostruct_write_test"
                            test_file.touch()
                            test_file.unlink()
                            validation["writable"] = True
                    else:
                        # Directory doesn't exist but parent is writable
                        validation["writable"] = True

                except Exception as e:
                    validation["issues"].append(
                        f"Cannot write to directory: {e}"
                    )
            else:
                validation["issues"].append(
                    f"Parent directory does not exist: {parent_dir}"
                )

        except Exception as e:
            validation["issues"].append(f"Error checking directory: {e}")

        # Check for potential conflicts if expected files provided
        if expected_files and validation["writable"]:
            try:
                download_path = Path(download_dir)
                if download_path.exists():
                    existing_files = {
                        f.name for f in download_path.iterdir() if f.is_file()
                    }
                    conflicts = [
                        f for f in expected_files if f in existing_files
                    ]
                    validation["conflicts"] = conflicts
            except Exception:
                pass  # Ignore errors in conflict detection

        return validation

    @staticmethod
    def build_execution_plan(
        processed_attachments: ProcessedAttachments,
        template_path: str,
        schema_path: str,
        variables: Dict[str, Any],
        security_mode: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build execution plan dict with consistent schema.

        Args:
            processed_attachments: Processed attachment specifications
            template_path: Path to template file
            schema_path: Path to schema file
            variables: Template variables
            security_mode: Security mode setting
            model: Model to use for processing
            **kwargs: Additional context (allowed_paths, cost_estimate, template_warning, etc.)

        Returns:
            Execution plan dictionary
        """
        # Handle template warning information
        template_warning = kwargs.get("template_warning")
        original_template_path = kwargs.get("original_template_path")

        # Use original path if available, otherwise use the provided path
        display_path = original_template_path or template_path

        template_info = {
            "path": display_path,
            "exists": (
                Path(display_path).exists() if display_path != "---" else True
            ),
        }

        # Add warning information if present
        if template_warning:
            template_info["warning"] = template_warning

        schema_info = {
            "path": schema_path,
            "exists": Path(schema_path).exists(),
        }

        # Build plan structure
        plan = {
            "schema_version": "1.0",
            "type": "execution_plan",
            "timestamp": datetime.now().isoformat(),
            "template": template_info,
            "schema": schema_info,
            "model": model or "gpt-4o",
            "variables": variables,
            "security_mode": security_mode or "permissive",
            "attachments": PlanAssembler._format_attachments(
                processed_attachments
            ),
        }

        # Add tools section if enabled tools are provided
        enabled_tools = kwargs.get("enabled_tools")
        if enabled_tools:
            tools_dict = {}
            for tool in enabled_tools:
                # Map tool names to boolean values for plan display
                if tool == "code-interpreter":
                    tools_dict["code_interpreter"] = True
                elif tool == "file-search":
                    tools_dict["file_search"] = True
                elif tool == "web-search":
                    tools_dict["web_search"] = True
                elif tool == "mcp":
                    tools_dict["mcp"] = True
                elif (
                    tool != "template"
                ):  # Skip template as it's not an external tool
                    tools_dict[tool] = True

            if tools_dict:
                plan["tools"] = tools_dict

        # Add download validation for Code Interpreter
        if enabled_tools and "code-interpreter" in enabled_tools:
            # Get CI config if available
            ci_config = kwargs.get("ci_config")
            download_validation = (
                PlanAssembler.validate_download_configuration(
                    enabled_tools=enabled_tools,
                    ci_config=ci_config,
                    expected_files=kwargs.get("expected_files"),
                )
            )

            # Add to plan if there are issues or useful info
            if download_validation["enabled"]:
                plan["download_validation"] = download_validation

        # Add optional fields
        if kwargs.get("allowed_paths"):
            plan["allowed_paths"] = kwargs["allowed_paths"]
        if kwargs.get("cost_estimate"):
            plan["cost_estimate"] = kwargs["cost_estimate"]

        return plan

    @staticmethod
    def build_run_summary(
        execution_plan: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build run summary dict from execution plan and results.

        Args:
            execution_plan: Original execution plan
            result: Execution results
            execution_time: Time taken for execution
            **kwargs: Additional summary data

        Returns:
            Dictionary with consistent run summary structure
        """
        summary = {
            "schema_version": "1.0",
            "type": "run_summary",
            "timestamp": time.time(),
            "execution_time": execution_time,
            "success": kwargs.get("success", True),
            "original_plan": execution_plan,
        }

        if result:
            summary["result"] = result

        if "error" in kwargs:
            summary["error"] = kwargs["error"]
            summary["success"] = False

        if "cost_breakdown" in kwargs:
            summary["cost_breakdown"] = kwargs["cost_breakdown"]

        return summary

    @staticmethod
    def _format_attachments(
        processed_attachments: ProcessedAttachments,
    ) -> List[Dict[str, Any]]:
        """Format processed attachments for plan output.

        Args:
            processed_attachments: Processed attachment specifications

        Returns:
            List of formatted attachment dictionaries
        """
        attachments = []

        # Add all attachment types with consistent format
        for alias, spec in processed_attachments.alias_map.items():
            # Determine attachment type based on attachment_type field or path
            if (
                hasattr(spec, "attachment_type")
                and spec.attachment_type == "collection"
            ):
                attachment_type = "collection"
            elif spec.recursive or (
                hasattr(spec, "attachment_type")
                and spec.attachment_type == "dir"
            ):
                attachment_type = "directory"
            else:
                attachment_type = "file"

            attachment = {
                "alias": alias,
                "path": str(spec.path),  # Convert Path to string
                "targets": sorted(
                    list(spec.targets)
                ),  # Ensure consistent ordering
                "type": attachment_type,
                "exists": os.path.exists(
                    str(spec.path)
                ),  # Convert Path to string
                "recursive": spec.recursive,
                "pattern": spec.pattern,
            }

            # Add metadata about where this attachment will be processed
            tool_info = []
            if "prompt" in spec.targets:
                tool_info.append("template")
            if "code-interpreter" in spec.targets or "ci" in spec.targets:
                tool_info.append("code_interpreter")
            if "file-search" in spec.targets or "fs" in spec.targets:
                tool_info.append("file_search")

            attachment["processing"] = tool_info
            attachments.append(attachment)

        return attachments

    @staticmethod
    def validate_plan(plan: Dict[str, Any]) -> bool:
        """Validate plan structure for consistency.

        Args:
            plan: Plan dictionary to validate

        Returns:
            True if plan structure is valid

        Raises:
            ValueError: If plan structure is invalid
        """
        required_fields = ["schema_version", "type", "timestamp"]

        for field in required_fields:
            if field not in plan:
                raise ValueError(f"Missing required field: {field}")

        if plan["type"] not in ["execution_plan", "run_summary"]:
            raise ValueError(f"Invalid plan type: {plan['type']}")

        if plan["schema_version"] != "1.0":
            raise ValueError(
                f"Unsupported schema version: {plan['schema_version']}"
            )

        return True
