"""Plan printing for human-readable execution plan output.

This module renders execution plans and run summaries for human consumption
using the same data structures as JSON output per UNIFIED GUIDELINES.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional, TextIO

from .unicode_compat import safe_emoji, safe_format


class PlanPrinter:
    """Renders execution plans for human eyes using same dict as JSON output.

    This class ensures consistent rendering logic by operating on the same
    data structures produced by PlanAssembler.
    """

    @staticmethod
    def human(plan: Dict[str, Any], file: Optional[TextIO] = None) -> None:
        """Print human-readable version with colors and formatting.

        Args:
            plan: Plan dictionary from PlanAssembler
            file: Output file (defaults to stdout)
        """
        if file is None:
            file = sys.stdout

        plan_type = plan.get("type", "unknown").replace("_", " ").title()
        emoji = safe_emoji("🔍")
        if emoji:
            print(f"{emoji} {plan_type}\n", file=file)
        else:
            print(f"{plan_type}\n", file=file)

        # Header with timestamp
        timestamp = plan["timestamp"]
        if isinstance(timestamp, str):
            # Handle ISO format timestamp
            try:
                timestamp_dt = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )
            except ValueError:
                # Fallback for other string formats
                timestamp_dt = datetime.now()
        else:
            # Handle numeric timestamp (legacy)
            timestamp_dt = datetime.fromtimestamp(timestamp)

        formatted_time = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")
        print(safe_format("🕐 Generated: {}", formatted_time), file=file)

        # Template and schema
        template = plan.get("template", {})
        schema = plan.get("schema", {})

        template_status = (
            safe_emoji("✅", "[OK]")
            if template.get("exists", False)
            else safe_emoji("❌", "[ERROR]")
        )
        schema_status = (
            safe_emoji("✅", "[OK]")
            if schema.get("exists", False)
            else safe_emoji("❌", "[ERROR]")
        )

        # Show more helpful template warning information
        template_path = template.get("path", "unknown")
        template_warning = template.get("warning")

        if template_warning:
            # Use warning indicator for configuration issues with existing files
            warning_status = (
                safe_emoji("⚠️", "[WARNING]")
                if template.get("exists", False)
                else safe_emoji("❌", "[ERROR]")
            )
            print(
                safe_format(
                    "📄 Template: {} {}", warning_status, template_path
                ),
                file=file,
            )
            print(
                f"   Warning: {template_warning}",
                file=file,
            )
        elif template_path == "---":
            # Special case for YAML frontmatter display issue (legacy)
            print(
                safe_format(
                    "📄 Template: {} {}", template_status, template_path
                ),
                file=file,
            )
            print(
                "   Note: Template content shown below",
                file=file,
            )
        else:
            print(
                safe_format(
                    "📄 Template: {} {}", template_status, template_path
                ),
                file=file,
            )

        print(
            safe_format(
                "📋 Schema: {} {}",
                schema_status,
                schema.get("path", "unknown"),
            ),
            file=file,
        )

        # Model
        if "model" in plan:
            print(safe_format("🤖 Model: {}", plan["model"]), file=file)

        # Security
        security = plan.get("security", {})
        if security:
            print(
                safe_format(
                    "🔒 Security: {}", security.get("mode", "unknown")
                ),
                file=file,
            )
            allowed_paths = security.get("allowed_paths", [])
            if allowed_paths:
                print(
                    f"   Allowed paths: {len(allowed_paths)} configured",
                    file=file,
                )

        # Tools
        tools = plan.get("tools", {})
        if tools:
            enabled_tools = [
                name for name, enabled in tools.items() if enabled
            ]
            if enabled_tools:
                print(
                    safe_format("🛠️  Tools: {}", ", ".join(enabled_tools)),
                    file=file,
                )

        print()  # Blank line before attachments

        # Attachments
        attachments = plan.get("attachments", [])
        print(safe_format("📎 Attachments ({}):", len(attachments)), file=file)

        if not attachments:
            print("   (none)", file=file)
        else:
            for att in attachments:
                exists_status = (
                    safe_emoji("✅", "[OK]")
                    if att.get("exists", False)
                    else safe_emoji("❌", "[ERROR]")
                )
                targets = ", ".join(att.get("targets", []))
                path = att.get("path", "unknown")
                alias = att.get("alias", "unknown")

                print(
                    f"   {exists_status} {alias} → {targets}: {path}",
                    file=file,
                )

                # Show additional details for directories
                if att.get("type") == "directory":
                    details = []
                    if att.get("recursive"):
                        details.append("recursive")
                    if att.get("pattern"):
                        details.append(f"pattern: {att['pattern']}")
                    if details:
                        print(f"      ({', '.join(details)})", file=file)

        # Download validation for Code Interpreter
        download_validation = plan.get("download_validation", {})
        if download_validation.get("enabled"):
            print(safe_format("\n📥 Download Configuration:"), file=file)
            print(
                f"   Directory: {download_validation.get('directory', 'N/A')}",
                file=file,
            )

            # Show writability status
            if download_validation.get("writable"):
                print(
                    safe_format(
                        "   {} Directory writable", safe_emoji("✅", "[OK]")
                    ),
                    file=file,
                )
            else:
                print(
                    safe_format(
                        "   {} Directory not writable",
                        safe_emoji("❌", "[ERROR]"),
                    ),
                    file=file,
                )

            # Show issues if any
            issues = download_validation.get("issues", [])
            if issues:
                print(
                    safe_format(
                        "   {}  Issues:", safe_emoji("⚠️", "[WARNING]")
                    ),
                    file=file,
                )
                for issue in issues:
                    print(f"      - {issue}", file=file)

            # Show potential conflicts
            conflicts = download_validation.get("conflicts", [])
            if conflicts:
                print(
                    safe_format(
                        "   {}  Potential conflicts: {}",
                        safe_emoji("⚠️", "[WARNING]"),
                        ", ".join(conflicts),
                    ),
                    file=file,
                )

        # Variables
        variables = plan.get("variables", {})
        if variables:
            print(
                safe_format("\n📊 Variables ({}):", len(variables)), file=file
            )
            for name, value in variables.items():
                # Truncate long values for readability
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                print(f"   {name}: {value_str}", file=file)

        # Cost estimate
        cost = plan.get("cost_estimate", {})
        if cost and cost.get("approx_usd", 0) > 0:
            estimated_note = " (estimated)" if cost.get("estimated") else ""
            print(
                safe_format(
                    "\n💰 Cost: ~${:.4f}{}",
                    cost.get("approx_usd", 0),
                    estimated_note,
                ),
                file=file,
            )
            if "tokens" in cost:
                print(f"   Tokens: ~{cost['tokens']:,}", file=file)

        # Execution time (for run summaries)
        if plan.get("type") == "run_summary":
            exec_time = plan.get("execution_time")
            success = plan.get("success", True)

            status_icon = (
                safe_emoji("✅", "[OK]")
                if success
                else safe_emoji("❌", "[ERROR]")
            )
            print(
                safe_format(
                    "\n{} Status: {}",
                    status_icon,
                    "Success" if success else "Failed",
                ),
                file=file,
            )

            if exec_time is not None:
                print(
                    safe_format("⏱️  Execution time: {:.2f}s", exec_time),
                    file=file,
                )

            # Show error if present
            if "error" in plan:
                print(
                    safe_format(
                        "{} Error: {}",
                        safe_emoji("❌", "[ERROR]"),
                        plan["error"],
                    ),
                    file=file,
                )

            # Show cost breakdown if present
            if "cost_breakdown" in plan:
                cost_breakdown = plan["cost_breakdown"]
                print(
                    safe_format(
                        "💰 Final cost: ${:.4f}",
                        cost_breakdown.get("total", 0),
                    ),
                    file=file,
                )

    @staticmethod
    def json(
        plan: Dict[str, Any], file: Optional[TextIO] = None, indent: int = 2
    ) -> None:
        """Print JSON version of plan.

        Args:
            plan: Plan dictionary from PlanAssembler
            file: Output file (defaults to stdout)
            indent: JSON indentation level
        """
        if file is None:
            file = sys.stdout

        json.dump(plan, file, indent=indent, default=str)
        file.write("\n")

    @staticmethod
    def summary_line(plan: Dict[str, Any]) -> str:
        """Generate a one-line summary of the plan.

        Args:
            plan: Plan dictionary from PlanAssembler

        Returns:
            Single line summary string
        """
        plan_type = plan.get("type", "unknown")

        if plan_type == "execution_plan":
            attachments = len(plan.get("attachments", []))
            variables = len(plan.get("variables", {}))
            return f"Plan: {attachments} attachments, {variables} variables, model {plan.get('model', 'unknown')}"

        elif plan_type == "run_summary":
            success = plan.get("success", True)
            exec_time = plan.get("execution_time")
            status = "Success" if success else "Failed"
            time_str = f" in {exec_time:.2f}s" if exec_time else ""
            return f"Summary: {status}{time_str}"

        else:
            return f"Plan: {plan_type}"

    @staticmethod
    def validate_and_print(
        plan: Dict[str, Any],
        output_format: str = "human",
        file: Optional[TextIO] = None,
    ) -> None:
        """Validate plan structure and print in specified format.

        Args:
            plan: Plan dictionary from PlanAssembler
            output_format: Output format ("human" or "json")
            file: Output file (defaults to stdout)

        Raises:
            ValueError: If plan structure is invalid or format is unsupported
        """
        from .plan_assembly import PlanAssembler

        # Validate plan structure
        PlanAssembler.validate_plan(plan)

        # Print in requested format
        if output_format == "human":
            PlanPrinter.human(plan, file)
        elif output_format == "json":
            PlanPrinter.json(plan, file)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
