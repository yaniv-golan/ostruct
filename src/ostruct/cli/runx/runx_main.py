#!/usr/bin/env python3
"""
Click-based implementation for OST (Self-Executing Templates) runx command.

This module provides the core logic for executing .ost templates as standalone
scripts with embedded schemas and argument policies using Click for argument parsing.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import rich_click as click

from ..ost.arg_policy import GlobalArgsPolicyEnforcer
from ..ost.frontmatter import FrontMatterError, FrontMatterParser
from ..ost.schema_export import export_inline_schema


class OSTFileType(click.ParamType):
    """Enhanced file type with routing target support."""

    def __init__(self, target: str = "prompt", **kwargs: Any) -> None:
        self.target = target
        self.name = "file"

    def convert(self, value: Any, param: Any, ctx: Any) -> str:
        # Just return the string path - let ostruct run handle validation
        return str(value)


class OSTDirectoryType(click.ParamType):
    """Enhanced directory type with routing target support."""

    def __init__(self, target: str = "prompt", **kwargs: Any) -> None:
        self.target = target
        self.name = "directory"

    def convert(self, value: Any, param: Any, ctx: Any) -> str:
        # Just return the string path - let ostruct run handle validation
        return str(value)


class OSTCollectionType(click.ParamType):
    """Collection type for glob patterns with routing target support."""

    def __init__(self, target: str = "prompt") -> None:
        self.target = target
        self.name = "collection"

    def convert(self, value: Any, param: Any, ctx: Any) -> str:
        return str(value)


class OSTPolicyError(click.ClickException):
    """Policy violation error with enhanced messaging."""

    def __init__(self, message: str, policy_mode: str, flag: str):
        self.policy_mode = policy_mode
        self.flag = flag
        super().__init__(message)

    def format_message(self) -> str:
        return click.style(f"Policy Error: {self.message}", fg="red")


def create_click_option(
    opt_name: str, opt_config: Dict[str, Any]
) -> Callable[..., Any]:
    """Create a Click option decorator from OST option configuration."""

    # Get basic option properties
    names = opt_config.get("names", [f"--{opt_name.replace('_', '-')}"])
    help_text = opt_config.get("help", "")
    default = opt_config.get("default")
    type_spec = opt_config.get("type", "str")
    action = opt_config.get("action", "store")
    choices = opt_config.get("choices")
    target = opt_config.get("target", "prompt")

    # Map OST types to Click types
    click_type: Union[click.ParamType, type]
    if type_spec == "file":
        click_type = OSTFileType(target=target)
    elif type_spec == "directory":
        click_type = OSTDirectoryType(target=target)
    elif type_spec == "collection":
        click_type = OSTCollectionType(target=target)
    elif type_spec == "int":
        click_type = int
    elif type_spec == "float":
        click_type = float
    elif type_spec == "bool":
        click_type = bool
    else:
        click_type = str

    # Handle choices
    if choices:
        click_type = click.Choice(choices)

    # Build Click option parameters
    option_kwargs = {
        "help": help_text,
        "default": default,
        "type": click_type,
    }

    # Handle different actions
    if action == "store_true":
        option_kwargs["is_flag"] = True
        option_kwargs["default"] = False
        option_kwargs.pop("type", None)  # Remove type for flags
    elif action == "store_false":
        option_kwargs["is_flag"] = True
        option_kwargs["flag_value"] = False
        option_kwargs["default"] = True
        option_kwargs.pop("type", None)  # Remove type for flags
    elif action == "append":
        option_kwargs["multiple"] = True
    elif action == "count":
        option_kwargs["count"] = True
        option_kwargs.pop("type", None)  # Remove type for count

    return click.option(*names, **option_kwargs)


def create_click_command(cli_meta: Dict[str, Any]) -> click.Command:
    """Create a Click command from OST front-matter CLI metadata."""

    # Create base command
    @click.command(
        name=cli_meta.get("name", "template"),
        help=cli_meta.get("description", "OST template"),
        context_settings={
            "allow_extra_args": True,
            "allow_interspersed_args": True,
            "ignore_unknown_options": True,
            "help_option_names": ["--help", "-h"],
        },
    )
    @click.pass_context
    def template_command(ctx: click.Context, **kwargs: Any) -> Dict[str, Any]:
        """OST template command."""
        # Store parsed parameters in context for later processing
        ctx.ensure_object(dict)
        ctx.obj["parsed_params"] = kwargs
        ctx.obj["extra_args"] = ctx.args.copy()
        return ctx.obj  # type: ignore[no-any-return]

    # Add positional arguments
    for pos_arg in reversed(cli_meta.get("positional", [])):
        arg_name = pos_arg.get("name")
        default = pos_arg.get("default")

        if default is not None:
            # Optional argument with default
            template_command = click.argument(
                arg_name, required=False, default=default
            )(template_command)
        else:
            # Required argument
            template_command = click.argument(arg_name)(template_command)

    # Add optional arguments
    options = cli_meta.get("options", {})
    if isinstance(options, list):
        # Handle list format (legacy)
        for opt_config in options:
            if isinstance(opt_config, dict) and "name" in opt_config:
                opt_name = opt_config["name"]
                option_decorator = create_click_option(opt_name, opt_config)
                template_command = option_decorator(template_command)
    else:
        # Handle dictionary format
        for opt_name, opt_config in options.items():
            if isinstance(opt_config, dict):
                option_decorator = create_click_option(opt_name, opt_config)
                template_command = option_decorator(template_command)

    return template_command


def apply_global_policies(
    extra_args: List[str], global_args: Dict[str, Any]
) -> List[str]:
    """Apply global argument policies to extra arguments."""

    if not global_args:
        return extra_args

    # Use existing policy enforcer
    enforcer = GlobalArgsPolicyEnforcer(global_args)

    # Extract pass_through_global setting (default True)
    pass_through_global = global_args.get("pass_through_global", True)

    try:
        sanitized, unknown = enforcer.enforce_policies(
            extra_args, pass_through_global
        )
        return sanitized
    except ValueError as e:
        raise OSTPolicyError(str(e), "policy_violation", "unknown")


def process_template_arguments(
    parsed_params: Dict[str, Any],
    extra_args: List[str],
    command: click.Command,
    defaults: Dict[str, Any],
) -> List[str]:
    """Convert Click parameters to ostruct run flags."""

    flags = []

    # First, process defaults that aren't in command parameters
    processed_defaults = set()
    for default_name, default_value in defaults.items():
        if default_name not in parsed_params:
            processed_defaults.add(default_name)
            # Special handling for known ostruct flags
            if default_name == "dry_run" and default_value:
                flags.append("--dry-run")
                continue
            elif default_value is not None:
                flags.extend(["--var", f"{default_name}={default_value}"])

    # Process template parameters
    for param in command.params:
        param_name = param.name
        value = parsed_params.get(param_name)

        # Skip if value is None and no default
        if value is None and param_name not in defaults:
            continue

        # Use provided value or default
        final_value = value if value is not None else defaults.get(param_name)

        # Special handling for known ostruct flags
        if param_name == "dry_run" and final_value:
            flags.append("--dry-run")
            continue

        # Handle different parameter types
        if isinstance(param.type, OSTFileType):
            if param.type.target == "ci":
                flags.extend(["--file", f"ci:{param_name}:{final_value}"])
            elif param.type.target == "fs":
                flags.extend(["--file", f"fs:{param_name}:{final_value}"])
            elif param.type.target in ("ud", "user-data"):
                flags.extend(["--file", f"ud:{param_name}:{final_value}"])
            elif param.type.target == "auto":
                flags.extend(["--file", f"auto:{param_name}:{final_value}"])
            else:  # prompt or default
                flags.extend(["--file", f"{param_name}:{final_value}"])
        elif (
            param.type is str
            and hasattr(param, "_ost_type")
            and param._ost_type == "file"
        ):
            # Handle file type that wasn't converted to OSTFileType
            flags.extend(["--file", f"{param_name}:{final_value}"])

        elif isinstance(param.type, OSTDirectoryType):
            if param.type.target == "ci":
                flags.extend(["--dir", f"ci:{param_name}:{final_value}"])
            elif param.type.target == "fs":
                flags.extend(["--dir", f"fs:{param_name}:{final_value}"])
            elif param.type.target in ("ud", "user-data"):
                flags.extend(["--dir", f"ud:{param_name}:{final_value}"])
            elif param.type.target == "auto":
                flags.extend(["--dir", f"auto:{param_name}:{final_value}"])
            else:  # prompt or default
                flags.extend(["--dir", f"{param_name}:{final_value}"])

        elif isinstance(param.type, OSTCollectionType):
            if param.type.target == "ci":
                flags.extend(["--collect", f"ci:{param_name}:@{final_value}"])
            elif param.type.target == "fs":
                flags.extend(["--collect", f"fs:{param_name}:@{final_value}"])
            elif param.type.target in ("ud", "user-data"):
                flags.extend(["--collect", f"ud:{param_name}:@{final_value}"])
            elif param.type.target == "auto":
                flags.extend(
                    ["--collect", f"auto:{param_name}:@{final_value}"]
                )
            else:  # prompt or default
                flags.extend(["--collect", f"{param_name}:@{final_value}"])

        elif isinstance(final_value, bool):
            flags.extend(["--var", f"{param_name}={str(final_value).lower()}"])
        elif isinstance(final_value, (list, tuple)):
            # Handle multiple values
            for item in final_value:
                flags.extend(["--var", f"{param_name}={item}"])
        elif final_value is not None:
            # Check if this was supposed to be a file/directory but didn't get handled above
            if hasattr(param, "_click_type_str") and param._click_type_str in (
                "file",
                "directory",
            ):
                if param._click_type_str == "file":
                    flags.extend(["--file", f"{param_name}:{final_value}"])
                else:
                    flags.extend(["--dir", f"{param_name}:{final_value}"])
            else:
                flags.extend(["--var", f"{param_name}={final_value}"])

    # Add extra arguments (unknown flags that passed policy enforcement)
    flags.extend(extra_args)

    return flags


def extract_template_body(file_path: Path, body_start: int) -> str:
    """Extract the Jinja template body from the OST file."""

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # body_start is the line number where template body starts (0-indexed)
    if body_start >= len(lines):
        return ""

    return "".join(lines[body_start:])


def preprocess_arguments(
    args: List[str], cli_meta: Dict[str, Any], global_args: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    """
    Preprocess arguments to separate template args from global args.

    This function identifies which arguments belong to the template vs. global flags
    to avoid the argument consumption issues we had with argparse.
    """
    # Get known template option names
    template_option_names = set()
    options = cli_meta.get("options", {})
    if isinstance(options, list):
        # Handle list format (legacy)
        for opt_config in options:
            if isinstance(opt_config, dict) and "name" in opt_config:
                opt_name = opt_config["name"]
                names = opt_config.get(
                    "names", [f"--{opt_name.replace('_', '-')}"]
                )
                template_option_names.update(names)
    else:
        # Handle dictionary format
        for opt_name, opt_config in options.items():
            if isinstance(opt_config, dict):
                names = opt_config.get(
                    "names", [f"--{opt_name.replace('_', '-')}"]
                )
                template_option_names.update(names)

    # Get known global flag names (convert from global_args format to CLI format)
    global_flag_names = set()
    for flag_name in global_args.keys():
        if flag_name == "pass_through_global":
            continue
        cli_flag = (
            f"--{flag_name}" if not flag_name.startswith("-") else flag_name
        )
        global_flag_names.add(cli_flag)

    template_args = []
    global_args_raw = []
    i = 0

    while i < len(args):
        arg = args[i]

        if arg in template_option_names:
            # This is a known template option
            template_args.append(arg)
            # Check if it takes a value
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                template_args.append(args[i + 1])
                i += 2
            else:
                i += 1
        elif arg in global_flag_names or (
            arg.startswith("--") and arg not in template_option_names
        ):
            # This is a global flag (known or unknown)
            global_args_raw.append(arg)

            # Check if this is a known boolean flag that doesn't take a value
            is_boolean_flag = False
            if arg in global_flag_names:
                # Convert CLI flag to global_args key format for lookup
                global_args_key = (
                    arg[2:].replace("-", "_") if arg.startswith("--") else arg
                )
                flag_config = global_args.get(global_args_key, {})
                # --dry-run is always a boolean flag regardless of policy mode
                is_boolean_flag = (
                    arg == "--dry-run"
                    or flag_config.get("mode") == "store_true"
                )
            else:
                # For unknown global flags, assume --dry-run is boolean
                is_boolean_flag = arg == "--dry-run"

            # Check if it takes a value (and the next arg doesn't start with -)
            if (
                not is_boolean_flag
                and i + 1 < len(args)
                and not args[i + 1].startswith("-")
            ):
                global_args_raw.append(args[i + 1])
                i += 2
            else:
                i += 1
        else:
            # This is a positional argument or unknown value
            template_args.append(arg)
            i += 1

    return template_args, global_args_raw


def format_ost_help(
    command: click.Command,
    cli_meta: Dict[str, Any],
    global_args: Dict[str, Any],
) -> str:
    """Enhanced help formatting with policy information."""

    # Get basic Click help
    try:
        ctx = click.Context(command)
        help_text = command.get_help(ctx)
    except Exception:
        # Fallback to manual help if Click help fails
        help_lines = [
            f"Usage: {command.name} [OPTIONS]",
            "",
            command.help or "OST template",
            "",
            "Options:",
        ]

        # Add options from command
        for param in command.params:
            if hasattr(param, "opts") and param.opts:
                opt_names = ", ".join(param.opts)
                help_desc = getattr(param, "help", "") or ""
                help_lines.append(f"  {opt_names:<20} {help_desc}")

        help_text = "\n".join(help_lines)

    # Add policy information if available
    if global_args:
        help_text += "\n\nGlobal ostruct flags policy:\n"

        pass_through_global = global_args.get("pass_through_global", True)
        if pass_through_global:
            help_text += "  Unknown flags: passed through to ostruct run\n"
        else:
            help_text += "  Unknown flags: rejected (error)\n"

        # Show specific policies
        for flag, policy in global_args.items():
            if flag == "pass_through_global":
                continue
            if isinstance(policy, dict):
                mode = policy.get("mode", "pass-through")
                help_text += f"  {flag}: {mode}\n"
                if mode == "fixed" and "value" in policy:
                    help_text += f"    Fixed value: {policy['value']}\n"
                elif mode == "allowed" and "allowed" in policy:
                    help_text += f"    Allowed values: {policy['allowed']}\n"

    # Add ostruct run reference
    help_text += "\nFor full ostruct run options, use: ostruct run --help\n"

    return help_text


def runx_main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the Click-based runx command.

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if argv is None:
        argv = sys.argv

    if len(argv) < 1:
        click.echo("Error: No template file specified", err=True)
        sys.exit(1)

    # Resolve template path
    tpl_path = Path(argv[0]).resolve()

    if not tpl_path.exists():
        click.echo(f"Error: Template file not found: {tpl_path}", err=True)
        sys.exit(1)

    try:
        # Parse front-matter
        content = tpl_path.read_text(encoding="utf-8")
        parser = FrontMatterParser(content)
        meta, body_start = parser.parse()

        # Extract configuration
        cli_meta = meta["cli"]
        defaults = meta.get("defaults", {})
        global_args = meta.get("global_args", {})
        baseline_args = meta.get("global_flags", [])

        # Create Click command dynamically
        click_cmd = create_click_command(cli_meta)

        # Check for help before parsing
        if "--help" in argv[1:] or "-h" in argv[1:]:
            help_text = format_ost_help(click_cmd, cli_meta, global_args)
            click.echo(help_text)
            return 0

        # Parse arguments using Click with custom preprocessing
        try:
            # Preprocess arguments to separate known template args from unknown global args
            template_args, global_args_raw = preprocess_arguments(
                argv[1:], cli_meta, global_args
            )

            ctx = click_cmd.make_context("template", template_args)
            try:
                result = click_cmd.invoke(ctx)

                parsed_params = result["parsed_params"]
                extra_args = result["extra_args"] + global_args_raw
            finally:
                if hasattr(ctx, "close"):
                    ctx.close()

        except click.ClickException as e:
            e.show()
            sys.exit(2)
        except SystemExit:
            # Click may raise SystemExit on validation errors - re-raise it
            raise

        # Remove baseline flags that are overridden by user for allowed/pass-through modes
        filtered_baseline_args = []
        user_flags = set()

        # Extract user flag names
        i = 0
        while i < len(extra_args):
            arg = extra_args[i]
            if arg.startswith("--"):
                user_flags.add(arg)
            i += 1

        # Filter baseline args - remove those that user is overriding with allowed policy
        i = 0
        while i < len(baseline_args):
            arg = baseline_args[i]
            if arg.startswith("--") and arg in user_flags:
                # Check if this flag has an allowed or pass-through policy
                flag_policy = global_args.get(arg.replace("--", ""), {})
                policy_mode = flag_policy.get("mode", "pass-through")
                if policy_mode in ("allowed", "pass-through"):
                    # Skip baseline value - user override will be used
                    if i + 1 < len(baseline_args) and not baseline_args[
                        i + 1
                    ].startswith("-"):
                        i += 2  # Skip flag and value
                    else:
                        i += 1  # Skip just the flag
                    continue
            filtered_baseline_args.append(arg)
            i += 1

        # Apply global policies to extra arguments
        try:
            sanitized_extra_args = apply_global_policies(
                extra_args, global_args
            )
        except OSTPolicyError as e:
            e.show()
            sys.exit(2)

        # Export schema to temporary file
        schema_path = export_inline_schema(meta["schema"])

        # Map template variables to ostruct flags
        template_flags = process_template_arguments(
            parsed_params, sanitized_extra_args, click_cmd, defaults
        )

        # Combine filtered baseline with template flags
        final_flags = filtered_baseline_args + template_flags

        # Create temporary file for template body
        template_body = extract_template_body(tpl_path, body_start)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".j2", delete=False
        ) as tmp_template:
            tmp_template.write(template_body)
            tmp_template_path = tmp_template.name

        # Build ostruct run command
        run_cmd: List[str] = [
            "ostruct",
            "run",
            tmp_template_path,
            str(schema_path),
        ]

        # Add default --progress none for OST files (cleaner UX for standalone tools)
        # unless user or template explicitly sets progress mode
        has_progress_flag = any(
            arg.startswith("--progress") for arg in final_flags
        )
        if not has_progress_flag:
            run_cmd.extend(["--progress", "none"])

        # Add final flags
        run_cmd.extend(final_flags)

        # Execute ostruct run via execvp
        try:
            os.execvp("ostruct", run_cmd)
        except OSError as e:
            click.echo(f"Error executing ostruct: {e}", err=True)
            # Clean up on error
            try:
                os.unlink(tmp_template_path)
            except OSError:
                pass
            sys.exit(1)

    except FrontMatterError as e:
        click.echo(f"Front-matter error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)

    return 0  # Should not reach here due to execvp


if __name__ == "__main__":
    sys.exit(runx_main())
