#!/usr/bin/env python3
"""
Main implementation for OST (Self-Executing Templates) runx command.

This module provides the core logic for executing .ost templates as standalone
scripts with embedded schemas and argument policies.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..ost.arg_policy import GlobalArgsPolicyEnforcer
from ..ost.frontmatter import FrontMatterError, FrontMatterParser
from ..ost.schema_export import export_inline_schema


def build_template_parser(cli_meta: Dict[str, Any]) -> argparse.ArgumentParser:
    """
    Build an argparse parser for the template-specific arguments.

    Args:
        cli_meta: The 'cli' section from the front-matter

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog=cli_meta.get("name", "template"),
        description=cli_meta.get("description", ""),
        add_help=False,  # We'll handle --help manually
    )

    # Add manual --help flag
    parser.add_argument(
        "--help",
        "-h",
        action="store_true",
        help="Show this help message and exit",
    )

    # Add positional arguments if specified
    if "positional" in cli_meta:
        for pos_arg in cli_meta["positional"]:
            if isinstance(pos_arg, str):
                parser.add_argument(pos_arg)
            elif isinstance(pos_arg, dict):
                name = pos_arg.get("name")
                if name:
                    kwargs = {k: v for k, v in pos_arg.items() if k != "name"}
                    parser.add_argument(name, **kwargs)

    # Add optional arguments if specified
    if "options" in cli_meta:
        options = cli_meta["options"]
        if isinstance(options, dict):
            # Options is a dict with option names as keys
            for opt_name, opt_config in options.items():
                if isinstance(opt_config, dict):
                    names = opt_config.get("names", [])
                    if names:
                        kwargs = {
                            k: v
                            for k, v in opt_config.items()
                            if k not in ["names", "target"]
                        }
                        # Handle type field - convert string type names to actual types
                        if "type" in kwargs:
                            type_val = kwargs["type"]
                            if isinstance(type_val, str):
                                if type_val == "str":
                                    kwargs["type"] = str
                                elif type_val == "int":
                                    kwargs["type"] = int
                                elif type_val == "float":
                                    kwargs["type"] = float
                                elif type_val == "bool":
                                    kwargs["type"] = bool
                                elif type_val in [
                                    "file",
                                    "directory",
                                    "collection",
                                ]:
                                    # These are ostruct-specific types, treat as string for argparse
                                    kwargs["type"] = str
                                else:
                                    # Remove unknown type to avoid errors
                                    del kwargs["type"]
                        parser.add_argument(*names, **kwargs)
        else:
            raise ValueError(
                "options must be a dictionary with option names as keys"
            )

    return parser


def print_custom_help(
    parser: argparse.ArgumentParser,
    cli_meta: Dict[str, Any],
    global_args: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Print custom help message combining template help with global policy info.

    Args:
        parser: The template argument parser
        cli_meta: The 'cli' section from front-matter
        global_args: The 'global_args' section from front-matter
    """
    # Print template-specific help
    parser.print_help()

    # Add global policy information if available
    if global_args:
        print("\nGlobal ostruct flags policy:")

        pass_through_global = global_args.get("pass_through_global", True)
        if pass_through_global:
            print("  Unknown flags: passed through to ostruct run")
        else:
            print("  Unknown flags: rejected (error)")

        # Show specific policies
        for flag, policy in global_args.items():
            if flag == "pass_through_global":
                continue
            if isinstance(policy, dict):
                mode = policy.get("mode", "pass_through")
                print(f"  {flag}: {mode}")
                if mode == "fixed" and "value" in policy:
                    print(f"    Fixed value: {policy['value']}")
                elif mode == "allowed" and "values" in policy:
                    print(f"    Allowed values: {policy['values']}")

    # Add tail of ostruct run --help
    print("\nFor full ostruct run options, use: ostruct run --help")


def map_template_vars_to_ostruct_flags(
    t_ns: argparse.Namespace, meta: Dict[str, Any]
) -> List[str]:
    """
    Map template variables to ostruct run flags using current syntax.

    Args:
        t_ns: Parsed template arguments namespace
        meta: Full front-matter metadata

    Returns:
        List of ostruct run flag arguments
    """
    flags = []

    # Get defaults from front-matter
    defaults = meta.get("defaults", {})

    # Build a map of argument names to their types from CLI metadata
    arg_types = {}
    arg_targets = {}  # Map argument names to their routing targets
    cli_meta = meta.get("cli", {})
    options = cli_meta.get("options", {})

    if isinstance(options, dict):
        for opt_name, opt_config in options.items():
            if isinstance(opt_config, dict):
                arg_type = opt_config.get("type")
                target = opt_config.get(
                    "target", "prompt"
                )  # Default to prompt target
                if arg_type:
                    arg_types[opt_name] = arg_type
                    arg_targets[opt_name] = target

    # Process each argument from the namespace
    all_keys = set(vars(t_ns).keys()) | set(defaults.keys())

    for key in all_keys:
        if key == "help":
            continue

        # Get value from namespace or defaults
        ns_value = vars(t_ns).get(key)
        default_value = defaults.get(key)

        # Skip if no value available
        if ns_value is None and default_value is None:
            continue

        # Use provided value or default
        final_value = ns_value if ns_value is not None else default_value

        # Special handling for known ostruct flags
        if key == "dry_run" and final_value:
            flags.append("--dry-run")
            continue

        # Check if this argument has a specific type that should be mapped to file flags
        arg_type = arg_types.get(key)
        arg_target = arg_targets.get(key, "prompt")

        if arg_type == "file":
            # Map file type to --file flag with routing target
            if arg_target == "ci" or arg_target == "code-interpreter":
                flags.extend(["--file", f"ci:{key}:{final_value}"])
            elif arg_target == "fs" or arg_target == "file-search":
                flags.extend(["--file", f"fs:{key}:{final_value}"])
            elif arg_target == "ud" or arg_target == "user-data":
                flags.extend(["--file", f"ud:{key}:{final_value}"])
            elif arg_target == "auto":
                flags.extend(["--file", f"auto:{key}:{final_value}"])
            else:  # prompt or default
                flags.extend(["--file", f"{key}:{final_value}"])
        elif arg_type == "directory":
            # Map directory type to --dir flag with routing target
            if arg_target == "ci" or arg_target == "code-interpreter":
                flags.extend(["--dir", f"ci:{key}:{final_value}"])
            elif arg_target == "fs" or arg_target == "file-search":
                flags.extend(["--dir", f"fs:{key}:{final_value}"])
            elif arg_target == "ud" or arg_target == "user-data":
                flags.extend(["--dir", f"ud:{key}:{final_value}"])
            elif arg_target == "auto":
                flags.extend(["--dir", f"auto:{key}:{final_value}"])
            else:  # prompt or default
                flags.extend(["--dir", f"{key}:{final_value}"])
        elif arg_type == "collection":
            # Map collection type to --collect flag with routing target
            if arg_target == "ci" or arg_target == "code-interpreter":
                flags.extend(["--collect", f"ci:{key}:@{final_value}"])
            elif arg_target == "fs" or arg_target == "file-search":
                flags.extend(["--collect", f"fs:{key}:@{final_value}"])
            elif arg_target == "ud" or arg_target == "user-data":
                flags.extend(["--collect", f"ud:{key}:@{final_value}"])
            elif arg_target == "auto":
                flags.extend(["--collect", f"auto:{key}:@{final_value}"])
            else:  # prompt or default
                flags.extend(["--collect", f"{key}:@{final_value}"])
        elif isinstance(final_value, bool):
            flags.extend(["--var", f"{key}={str(final_value).lower()}"])
        elif isinstance(final_value, (str, int, float)):
            flags.extend(["--var", f"{key}={final_value}"])
        elif isinstance(final_value, list):
            # Handle list values by repeating the flag
            for item in final_value:
                flags.extend(["--var", f"{key}={item}"])
        elif isinstance(final_value, Path):
            # Handle file/directory paths (fallback)
            flags.extend(["--file", f"{key}:{final_value}"])
        else:
            # Convert to string for other types
            flags.extend(["--var", f"{key}={final_value}"])

    return flags


def enforce_global_policy(
    leftover_args: List[str], global_args: Optional[Dict[str, Any]]
) -> List[str]:
    """
    Enforce global argument policy and return sanitized arguments.

    Args:
        leftover_args: Arguments not consumed by template parser
        global_args: Global arguments policy from front-matter

    Returns:
        Sanitized arguments that passed policy enforcement

    Raises:
        SystemExit: With code 2 if policy violations are found
    """
    if not global_args:
        return leftover_args

    enforcer = GlobalArgsPolicyEnforcer(global_args)

    # Extract pass_through_global setting (default True)
    pass_through_global = global_args.get("pass_through_global", True)

    try:
        sanitized, unknown = enforcer.enforce_policies(
            leftover_args, pass_through_global
        )
        return sanitized
    except ValueError as e:
        print(f"Policy violation: {e}", file=sys.stderr)
        sys.exit(2)


def extract_template_body(file_path: Path, body_start: int) -> str:
    """
    Extract the Jinja template body from the OST file.

    Args:
        file_path: Path to the OST file
        body_start: Line number where template body starts (1-indexed)

    Returns:
        Template body content
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # body_start is 1-indexed, convert to 0-indexed
    if body_start > len(lines):
        return ""

    return "".join(lines[body_start - 1 :])


def resolve_overrides(
    baseline_args: List[str],
    user_args: List[str],
    global_args: Optional[Dict[str, Any]],
) -> List[str]:
    """
    Resolve conflicts between template-set baseline flags and user-provided flags.

    Template-set flags (from global_flags) are always applied. User flags are
    checked against policy:
    - FIXED mode: Reject if user tries to override with different value
    - BLOCKED mode: Reject if user tries to use the flag at all
    - ALLOWED mode: Allow if value is in allowed list
    - PASS_THROUGH mode: Allow through

    Args:
        baseline_args: Template-set flags from global_flags
        user_args: User-provided flags
        global_args: Policy configuration from global_args section

    Returns:
        Combined list of resolved flags

    Raises:
        SystemExit: If policy violation detected
    """
    if not global_args:
        global_args = {}

    # Parse baseline args into flag->value mapping
    baseline_flags: Dict[str, Any] = {}
    i = 0
    while i < len(baseline_args):
        arg = baseline_args[i]
        if "=" in arg:
            # --flag=value format
            flag, value = arg.split("=", 1)
            baseline_flags[flag] = value
            i += 1
        elif (
            arg.startswith("-")
            and i + 1 < len(baseline_args)
            and not baseline_args[i + 1].startswith("-")
        ):
            # --flag value format
            flag = arg
            value = baseline_args[i + 1]
            baseline_flags[flag] = value
            i += 2
        else:
            # Boolean flag or standalone
            baseline_flags[arg] = True
            i += 1

    # Parse user args and check for conflicts
    allowed_user_args = []
    i = 0
    while i < len(user_args):
        arg = user_args[i]

        if "=" in arg:
            # --flag=value format
            flag, value = arg.split("=", 1)
            user_value: Any = value
            increment = 1
        elif (
            arg.startswith("-")
            and i + 1 < len(user_args)
            and not user_args[i + 1].startswith("-")
        ):
            # --flag value format
            flag = arg
            user_value = user_args[i + 1]
            increment = 2
        else:
            # Boolean flag or standalone
            flag = arg
            user_value = True
            increment = 1

        # Check if this flag has a policy
        # Convert command line flag to global_args key format
        # e.g., "--model" -> "model"
        global_args_key = flag[2:] if flag.startswith("--") else flag
        policy_config = global_args.get(global_args_key)

        if policy_config:
            mode = policy_config.get("mode")

            if mode == "blocked":
                print(
                    f"Error: Flag {flag} is blocked by template policy",
                    file=sys.stderr,
                )
                sys.exit(2)
            elif mode == "fixed":
                # Check if user is trying to override template-set value
                if flag in baseline_flags:
                    fixed_value = baseline_flags[flag]
                    if user_value != fixed_value:
                        print(
                            f"Error: Cannot override template-set flag {flag}={fixed_value} with {user_value}",
                            file=sys.stderr,
                        )
                        sys.exit(2)
                else:
                    # User providing fixed flag that template didn't set
                    fixed_value = policy_config.get("value")
                    if fixed_value is not None and user_value != fixed_value:
                        print(
                            f"Error: Flag {flag} is fixed to {fixed_value}, cannot set to {user_value}",
                            file=sys.stderr,
                        )
                        sys.exit(2)
            elif mode == "allowed":
                allowed_values = policy_config.get("allowed", [])
                if user_value not in allowed_values:
                    print(
                        f"Error: Flag {flag} value {user_value} not in allowed list: {allowed_values}",
                        file=sys.stderr,
                    )
                    sys.exit(2)
            # pass-through mode allows everything

        # If we get here, the user flag is allowed
        if increment == 1:
            allowed_user_args.append(arg)
        else:
            allowed_user_args.extend([arg, user_args[i + 1]])

        i += increment

    # Build final args: baseline args first, then user args
    # But if user provides a flag that's also in baseline, user wins for allowed/pass-through modes
    final_args = []
    user_flags = set()

    # Extract user flag names for override detection
    i = 0
    while i < len(allowed_user_args):
        arg = allowed_user_args[i]
        if "=" in arg:
            flag, _ = arg.split("=", 1)
            user_flags.add(flag)
            i += 1
        elif (
            arg.startswith("-")
            and i + 1 < len(allowed_user_args)
            and not allowed_user_args[i + 1].startswith("-")
        ):
            user_flags.add(arg)
            i += 2
        else:
            if arg.startswith("-"):
                user_flags.add(arg)
            i += 1

    # Add baseline args, skipping those that user is overriding in allowed/pass-through modes
    i = 0
    while i < len(baseline_args):
        arg = baseline_args[i]
        if "=" in arg:
            flag, _ = arg.split("=", 1)
            increment = 1
        elif (
            arg.startswith("-")
            and i + 1 < len(baseline_args)
            and not baseline_args[i + 1].startswith("-")
        ):
            flag = arg
            increment = 2
        else:
            flag = arg
            increment = 1

        # Check if user is overriding this flag
        if flag in user_flags:
            policy_config = global_args.get(flag, {})
            mode = policy_config.get("mode", "pass-through")

            # In fixed mode, user can't override (already checked above)
            # In allowed/pass-through modes, user can override
            if mode in ["allowed", "pass-through"]:
                # Skip baseline flag, user version will be used
                i += increment
                continue

        # Add baseline flag
        if increment == 1:
            final_args.append(arg)
        else:
            final_args.extend([arg, baseline_args[i + 1]])

        i += increment

    # Add all user args
    final_args.extend(allowed_user_args)

    return final_args


def _preprocess_args_for_flag_value_pairs(args: List[str]) -> List[str]:
    """
    Preprocess arguments to convert --flag value pairs to --flag=value format
    only when necessary to prevent positional argument consumption issues.

    This helps argparse.parse_known_args() better handle unknown flags that take values
    when positional arguments are also present.

    Args:
        args: Raw command line arguments

    Returns:
        Processed arguments with some flag-value pairs converted to --flag=value format
    """
    processed_args = []
    i = 0

    # Check if there are any non-flag arguments (potential positionals)
    has_positionals = any(not arg.startswith("-") for arg in args)

    while i < len(args):
        arg = args[i]

        # Only convert flag-value pairs if there are positional arguments
        # that could be consumed by the flag
        if (
            has_positionals
            and arg.startswith("--")
            and i + 1 < len(args)
            and not args[i + 1].startswith("-")
            and i + 2
            < len(
                args
            )  # There's at least one more argument after the flag value
            and not args[i + 2].startswith(
                "-"
            )  # And that argument doesn't start with -
        ):
            # Convert --flag value to --flag=value to prevent consuming the next positional
            processed_args.append(f"{arg}={args[i + 1]}")
            i += 2
        else:
            # Keep argument as-is
            processed_args.append(arg)
            i += 1

    return processed_args


def runx_main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the runx command.

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if argv is None:
        argv = sys.argv

    if len(argv) < 1:
        print("Error: No template file specified", file=sys.stderr)
        return 1

    # Resolve template path
    tpl_path = Path(argv[0]).resolve()

    if not tpl_path.exists():
        print(f"Error: Template file not found: {tpl_path}", file=sys.stderr)
        return 1

    try:
        # Parse front-matter
        content = tpl_path.read_text(encoding="utf-8")
        parser = FrontMatterParser(content)
        meta, body_start = parser.parse()

        # Extract global_flags as baseline args
        baseline_args = meta.get("global_flags", [])

        # Build template parser
        cli_meta = meta["cli"]
        tparser = build_template_parser(cli_meta)

        # Check for --help before parsing to avoid required argument errors
        if "--help" in argv[1:] or "-h" in argv[1:]:
            print_custom_help(tparser, cli_meta, meta.get("global_args"))
            return 0

        # Parse template and global arguments
        try:
            # Pre-process arguments to better handle flag-value associations
            processed_args = _preprocess_args_for_flag_value_pairs(argv[1:])

            # Use parse_known_args() for non-intermixed parsing
            # This requires flags before positionals, matching user expectations
            # and reducing ambiguity with unknown flags
            t_ns, leftover = tparser.parse_known_args(processed_args)
        except SystemExit:
            # argparse called sys.exit, likely due to error
            return 2

        # Export schema to temporary file
        schema_path = export_inline_schema(meta["schema"])

        # Map template variables to ostruct flags
        template_flags = map_template_vars_to_ostruct_flags(t_ns, meta)

        # Resolve conflicts between template-set baseline flags and user flags
        global_args = meta.get("global_args")
        final_flags = resolve_overrides(baseline_args, leftover, global_args)

        # Add template-generated flags (these are always allowed)
        final_flags.extend(template_flags)

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

        # Add final sanitized flags
        run_cmd.extend(final_flags)

        # Execute ostruct run via execvp
        # Note: Don't clean up temp files here since execvp replaces the process
        try:
            os.execvp("ostruct", run_cmd)
        except OSError as e:
            print(f"Error executing ostruct: {e}", file=sys.stderr)
            # Clean up on error
            try:
                os.unlink(tmp_template_path)
            except OSError:
                pass
            return 1

    except FrontMatterError as e:
        print(f"Front-matter error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    return 0  # Should not reach here due to execvp


if __name__ == "__main__":
    sys.exit(runx_main())
