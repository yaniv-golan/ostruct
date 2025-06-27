#!/usr/bin/env python3
"""Main CLI module for ostruct."""

import os
import sys
from typing import Optional

import rich_click as click
from dotenv import load_dotenv

from .. import __version__
from .commands import create_command_group
from .config import OstructConfig
from .errors import (
    CLIError,
    InvalidJSONError,
    SchemaFileError,
    SchemaValidationError,
    handle_error,
)
from .exit_codes import ExitCode
from .help_json import print_full_cli_help_json as print_full_help_json
from .registry_updates import get_update_notification

# Import rich-click configuration
from .rich_config import *  # noqa: F401,F403
from .unicode_compat import safe_emoji
from .utils import fix_surrogate_escapes

# Load environment variables from .env file
load_dotenv()


def _handle_quick_ref(
    ctx: click.Context, param: click.Parameter, value: bool
) -> None:
    """Handle --quick-ref flag by showing quick reference help and exiting."""
    if not value or ctx.resilient_parsing:
        return

    from .quick_ref_help import show_quick_ref_help

    show_quick_ref_help()
    ctx.exit()


def _handle_version(
    ctx: click.Context, param: click.Parameter, value: bool
) -> None:
    """Handle --version flag by showing version and exiting."""
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"ostruct, version {__version__}")
    ctx.exit()


def fix_argv_encoding() -> None:
    """Fix UTF-8 encoding issues in sys.argv.

    This function addresses the surrogate escape issue where Python's sys.argv
    contains surrogate characters (e.g., a backslash followed by 'udce2')
    when processing command line arguments with non-ASCII characters. This
    commonly happens with filenames containing characters like en dash (–) or
    other Unicode characters.

    The fix detects arguments containing surrogate escapes and converts them
    back to proper UTF-8 strings.
    """
    try:
        fixed_argv = []
        for arg in sys.argv:
            fixed_argv.append(fix_surrogate_escapes(arg))

        # Replace sys.argv with the fixed version
        sys.argv = fixed_argv

    except Exception:
        # If anything goes wrong with the encoding fix, continue with original argv
        # This ensures the CLI doesn't break even if the fix fails
        pass


def create_cli_group() -> click.Group:
    """Create the main CLI group with all commands."""

    @click.group(cls=click.RichGroup)
    @click.option(
        "--version",
        "-V",
        is_flag=True,
        expose_value=False,
        is_eager=True,
        callback=_handle_version,
        help="Show the version and exit.",
    )
    @click.option(
        "--config",
        type=click.Path(exists=True),
        help="Configuration file path (default: ostruct.yaml)",
    )
    @click.option(
        "--quick-ref",
        is_flag=True,
        callback=_handle_quick_ref,
        expose_value=False,
        is_eager=True,
        help=f"{safe_emoji('📖')} Show concise usage examples and patterns",
    )
    @click.option(
        "--help-json",
        is_flag=True,
        callback=print_full_help_json,
        expose_value=False,
        is_eager=True,
        hidden=True,  # Hide from help output - feature not ready for release
        help=f"{safe_emoji('📖')} Output comprehensive help for all commands in JSON format",
    )
    @click.option(
        "--unicode/--no-unicode",
        default=None,
        help="Force enable/disable Unicode emoji display (overrides auto-detection)",
        envvar="OSTRUCT_UNICODE",
    )
    @click.pass_context
    def cli_group(
        ctx: click.Context,
        config: Optional[str] = None,
        unicode: Optional[bool] = None,
    ) -> None:
        """ostruct - AI-powered structured output with multi-tool integration."""
        # Handle Unicode preference
        if unicode is not None:
            os.environ["OSTRUCT_UNICODE"] = "1" if unicode else "0"

        # Load configuration
        try:
            app_config = OstructConfig.load(config)
            ctx.ensure_object(dict)
            ctx.obj["config"] = app_config
        except Exception as e:
            click.secho(
                f"Warning: Failed to load configuration: {e}",
                fg="yellow",
                err=True,
            )
            # Use default configuration
            ctx.ensure_object(dict)
            ctx.obj["config"] = OstructConfig()

        # Check for registry updates in a non-intrusive way
        try:
            update_message = get_update_notification()
            if update_message:
                click.secho(f"Note: {update_message}", fg="blue", err=True)
        except Exception:
            # Ensure any errors don't affect normal operation
            pass

    # Set the docstring dynamically with emoji compatibility
    rocket = safe_emoji("🚀")
    folder = safe_emoji("📁")
    target = safe_emoji("🎯")
    book = safe_emoji("📖")
    lightning = safe_emoji("⚡")
    wrench = safe_emoji("🔧")

    cli_group.__doc__ = f"""ostruct - AI-powered structured output with multi-tool integration.

Transform unstructured inputs into structured JSON using OpenAI APIs, Jinja2 templates, and powerful tool integrations.

{rocket} **QUICK START**

ostruct run template.j2 schema.json --var name=value

{folder} **FILE ATTACHMENT SYSTEM**

--file [targets:]alias path      Attach file with optional target routing

--dir [targets:]alias path       Attach directory with optional target routing

{target} **TARGETS**

prompt (default)                 Template access only

code-interpreter, ci             Code execution & analysis

file-search, fs                  Document search & retrieval

{book} **GETTING HELP**

ostruct --help                   Command overview

ostruct --quick-ref              Usage examples and patterns

ostruct run --help               Detailed options reference

ostruct run --help-debug         Troubleshooting guide

{book} Documentation: https://ostruct.readthedocs.io

{lightning} **EXAMPLES**

# Basic usage
ostruct run template.j2 schema.json --file data file.txt

# Multi-tool routing
ostruct run analysis.j2 schema.json --file ci:data data.csv --file fs:docs manual.pdf

# Combined targets
ostruct run task.j2 schema.json --file ci,fs:shared data.json

# MCP server integration
ostruct run template.j2 schema.json --mcp-server deepwiki@https://mcp.deepwiki.com/sse

{wrench} **ENVIRONMENT VARIABLES**

```text
Core API Configuration:
OPENAI_API_KEY                           OpenAI API authentication key
OPENAI_API_BASE                          Custom OpenAI API base URL

Template Processing Limits:
OSTRUCT_TEMPLATE_FILE_LIMIT              Max individual file size (default: 64KB)
OSTRUCT_TEMPLATE_TOTAL_LIMIT             Max total files size (default: 1MB)
OSTRUCT_TEMPLATE_PREVIEW_LIMIT           Template preview size limit (default: 4096)

System Behavior:
OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS   Disable model registry updates
OSTRUCT_MCP_URL_<name>                   Custom MCP server URLs

Unicode Display Control:
OSTRUCT_UNICODE=auto                     Auto-detect terminal capabilities (default)
OSTRUCT_UNICODE=1/true/yes               Force emoji display (override detection)
OSTRUCT_UNICODE=0/false/no               Force plain text (override detection)
OSTRUCT_UNICODE=debug                    Show detection details and auto-detect
```
"""

    # Add all commands from the command module
    command_group = create_command_group()
    for command in command_group.commands.values():
        cli_group.add_command(command)

    return cli_group


# Create the main cli object using the factory
cli = create_cli_group()


def create_cli() -> click.Command:
    """Create the CLI command.

    Returns:
        click.Command: The CLI command object
    """
    return cli


def main() -> None:
    """Main entry point for the CLI."""
    # Fix UTF-8 encoding issues in command line arguments before processing
    fix_argv_encoding()

    # Load environment variables from .env file
    load_dotenv()

    try:
        cli(standalone_mode=False)
    except (
        CLIError,
        InvalidJSONError,
        SchemaFileError,
        SchemaValidationError,
    ) as e:
        handle_error(e)
        sys.exit(
            e.exit_code if hasattr(e, "exit_code") else ExitCode.INTERNAL_ERROR
        )
    except click.UsageError as e:
        handle_error(e)
        sys.exit(ExitCode.USAGE_ERROR)
    except Exception as e:
        handle_error(e)
        sys.exit(ExitCode.INTERNAL_ERROR)


# Re-export ExitCode for compatibility

# Export public API
__all__ = [
    "ExitCode",
    "main",
    "create_cli",
]


if __name__ == "__main__":
    main()
