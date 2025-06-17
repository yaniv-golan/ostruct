"""Plan assembly for execution plans and run summaries.

This module provides the single source of truth for plan data structures
following UNIFIED GUIDELINES to prevent logic drift between JSON and human output.
"""

import os
import time
from typing import Any, Dict, List, Optional

from .attachment_processor import ProcessedAttachments


class PlanAssembler:
    """Single source of truth for execution plan data structure.

    This class ensures consistent plan format across all output types
    (JSON, human-readable, etc.) by providing a single build method.
    """

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
            **kwargs: Additional context (allowed_paths, cost_estimate, etc.)

        Returns:
            Dictionary with consistent execution plan structure
        """
        return {
            "schema_version": "1.0",
            "type": "execution_plan",
            "timestamp": time.time(),
            "template": {
                "path": template_path,
                "exists": os.path.exists(template_path),
            },
            "schema": {
                "path": schema_path,
                "exists": os.path.exists(schema_path),
            },
            "model": model or "gpt-4o",
            "security": {
                "mode": str(security_mode) if security_mode else "permissive",
                "allowed_paths": kwargs.get("allowed_paths", []),
            },
            "attachments": PlanAssembler._format_attachments(
                processed_attachments
            ),
            "variables": dict(variables),
            "cost_estimate": kwargs.get(
                "cost_estimate",
                {"approx_usd": 0.0, "tokens": 0, "estimated": True},
            ),
            "tools": {
                "code_interpreter": len(
                    processed_attachments.ci_files
                    + processed_attachments.ci_dirs
                )
                > 0,
                "file_search": len(
                    processed_attachments.fs_files
                    + processed_attachments.fs_dirs
                )
                > 0,
                "web_search": kwargs.get("web_search_enabled", False),
            },
        }

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
            attachment = {
                "alias": alias,
                "path": spec.path,
                "targets": sorted(
                    list(spec.targets)
                ),  # Ensure consistent ordering
                "type": "file" if not spec.recursive else "directory",
                "exists": os.path.exists(spec.path),
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
