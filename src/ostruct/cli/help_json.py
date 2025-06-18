"""Unified JSON help system for ostruct CLI."""

import json
from typing import Any, Dict, List

import click

from .. import __version__


def generate_attachment_system_info() -> Dict[str, Any]:
    """Generate structured attachment system information from codebase constants."""
    from .params import TARGET_NORMALISE

    # Build structured target information
    canonical_targets = set(TARGET_NORMALISE.values())
    aliases: Dict[str, List[str]] = {}

    for alias, canonical in TARGET_NORMALISE.items():
        if alias != canonical:  # Only include actual aliases
            if canonical not in aliases:
                aliases[canonical] = []
            aliases[canonical].append(alias)

    targets = {}
    for canonical in sorted(canonical_targets):
        targets[canonical] = {
            "canonical_name": canonical,
            "aliases": sorted(aliases.get(canonical, [])),
            "description": _get_target_description(canonical),
            "type": "file_routing_target",
        }

    return {
        "format_spec": "[targets:]alias path",
        "targets": targets,
        "examples": [
            {
                "syntax": "--file data file.txt",
                "targets": ["prompt"],
                "description": "Template access only (default target)",
            },
            {
                "syntax": "--file ci:analysis data.csv",
                "targets": ["code-interpreter"],
                "description": "Code execution & analysis",
            },
            {
                "syntax": "--dir fs:docs ./documentation",
                "targets": ["file-search"],
                "description": "Document search & retrieval",
            },
            {
                "syntax": "--file ci,fs:shared data.json",
                "targets": ["code-interpreter", "file-search"],
                "description": "Multi-target routing",
            },
        ],
    }


def _get_target_description(target: str) -> str:
    """Get description for a target."""
    descriptions = {
        "prompt": "Template access only (default)",
        "code-interpreter": "Code execution & analysis",
        "file-search": "Document search & retrieval",
    }
    return descriptions.get(target, f"Unknown target: {target}")


def generate_json_output_modes() -> Dict[str, Any]:
    """Generate structured JSON output mode information."""
    return {
        "help_json": {
            "description": "Output command help in JSON format",
            "output_destination": "stdout",
            "exit_behavior": "exits_after_output",
            "scope": "single_command_or_full_cli",
        },
        "dry_run_json": {
            "description": "Output execution plan as JSON with --dry-run",
            "output_destination": "stdout",
            "requires": ["--dry-run"],
            "exit_behavior": "exits_after_output",
            "scope": "execution_plan",
        },
        "run_summary_json": {
            "description": "Output run summary as JSON to stderr after execution",
            "output_destination": "stderr",
            "requires": [],
            "conflicts_with": ["--dry-run"],
            "exit_behavior": "continues_execution",
            "scope": "execution_summary",
        },
    }


def enhance_param_info(
    param_info: Dict[str, Any], param: click.Parameter
) -> Dict[str, Any]:
    """Enhance parameter info with dynamic data."""
    # Import here to avoid circular imports
    try:
        from .click_options import ModelChoice

        model_choice_class = ModelChoice
    except ImportError:
        model_choice_class = None

    # For model parameter, add dynamic choices metadata
    if (
        param.name == "model"
        and model_choice_class is not None
        and isinstance(param.type, model_choice_class)
    ):
        param_info["dynamic_choices"] = True
        param_info["choices_source"] = "openai_model_registry"

        # Add registry metadata if available
        try:
            from openai_model_registry import ModelRegistry

            registry = ModelRegistry.get_instance()
            choices_list = list(param.type.choices)
            param_info["registry_metadata"] = {
                "total_models": len(list(registry.models)),
                "structured_output_models": len(choices_list),
                "registry_path": str(
                    getattr(registry.config, "registry_path", "unknown")
                ),
            }
        except Exception:
            param_info["registry_metadata"] = {"status": "unavailable"}

    return param_info


def generate_usage_patterns_from_commands(
    commands: Dict[str, Any],
) -> Dict[str, str]:
    """Generate usage patterns from actual command definitions instead of hardcoding."""
    # This would ideally inspect the actual commands and generate examples
    # For now, we'll keep the patterns but mark them as generated
    patterns = {}

    if "run" in commands:
        patterns.update(
            {
                "basic_template": "ostruct run TEMPLATE.j2 SCHEMA.json -V name=value",
                "file_attachment": "ostruct run TEMPLATE.j2 SCHEMA.json --file ci:data DATA.csv --file fs:docs DOCS.pdf",
                "mcp_integration": "ostruct run TEMPLATE.j2 SCHEMA.json --mcp-server label@https://server.com/sse",
                "dry_run": "ostruct run TEMPLATE.j2 SCHEMA.json --dry-run",
                "json_output": "ostruct run TEMPLATE.j2 SCHEMA.json --dry-run-json",
            }
        )

    return patterns


def print_command_help_json(
    ctx: click.Context, param: click.Parameter, value: Any
) -> None:
    """Print single command help in JSON format."""
    if not value or ctx.resilient_parsing:
        return

    # Use Click's built-in to_info_dict() method
    help_data = ctx.to_info_dict()  # type: ignore[attr-defined]

    # Enhance parameter info with dynamic data
    if "command" in help_data and "params" in help_data["command"]:
        for param_info in help_data["command"]["params"]:
            # Find the corresponding Click parameter
            param_name = param_info.get("name")
            if param_name:
                for click_param in ctx.command.params:
                    if click_param.name == param_name:
                        enhance_param_info(param_info, click_param)
                        break

    # Add ostruct-specific metadata
    help_data.update(
        {
            "ostruct_version": __version__,
            "help_type": "single_command",
            "attachment_system": generate_attachment_system_info(),
            "json_output_modes": generate_json_output_modes(),
        }
    )

    click.echo(json.dumps(help_data, indent=2))
    ctx.exit(0)


def print_full_cli_help_json(
    ctx: click.Context, param: click.Parameter, value: Any
) -> None:
    """Print comprehensive help for all commands in JSON format."""
    if not value or ctx.resilient_parsing:
        return

    # Get main group help
    main_help = ctx.to_info_dict()  # type: ignore[attr-defined]

    # Get all commands help
    commands_help = {}
    if hasattr(ctx.command, "commands"):
        for cmd_name, cmd in ctx.command.commands.items():
            try:
                cmd_ctx = cmd.make_context(
                    cmd_name, [], parent=ctx, resilient_parsing=True
                )
                commands_help[cmd_name] = cmd_ctx.to_info_dict()
            except Exception as e:
                commands_help[cmd_name] = {
                    "name": cmd_name,
                    "help": getattr(cmd, "help", None)
                    or getattr(cmd, "short_help", None),
                    "error": f"Could not generate full help: {str(e)}",
                }

    # Build comprehensive help structure
    full_help = {
        "ostruct_version": __version__,
        "help_type": "full_cli",
        "main_command": main_help,
        "commands": commands_help,
        "usage_patterns": generate_usage_patterns_from_commands(commands_help),
        "attachment_system": generate_attachment_system_info(),
        "json_output_modes": generate_json_output_modes(),
    }

    click.echo(json.dumps(full_help, indent=2))
    ctx.exit(0)
