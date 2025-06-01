"""Minimal CLI entry point for ostruct."""

import sys
from typing import Optional

import click

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
from .registry_updates import get_update_notification


def create_cli_group() -> click.Group:
    """Create the main CLI group with all commands."""

    @click.group()
    @click.version_option(version=__version__)
    @click.option(
        "--config",
        type=click.Path(exists=True),
        help="Configuration file path (default: ostruct.yaml)",
    )
    @click.pass_context
    def cli_group(ctx: click.Context, config: Optional[str] = None) -> None:
        """ostruct - AI-powered structured output with multi-tool integration.

        ostruct transforms unstructured inputs into structured JSON using OpenAI APIs,
        Jinja2 templates, and powerful tool integrations including Code Interpreter,
        File Search, Web Search, and MCP servers.

        🚀 QUICK START:
            ostruct run template.j2 schema.json -V name=value

        📁 FILE ROUTING (explicit tool assignment):
            -ft/--file-for-template          Template access only
            -fc/--file-for-code-interpreter  Code execution & analysis
            -fs/--file-for-file-search       Document search & retrieval

        ⚡ EXAMPLES:
            # Basic usage (unchanged)
            ostruct run template.j2 schema.json -f config.yaml

            # Multi-tool explicit routing
            ostruct run analysis.j2 schema.json -fc data.csv -fs docs.pdf -ft config.yaml

            # Advanced routing with --file-for
            ostruct run task.j2 schema.json --file-for code-interpreter shared.json --file-for file-search shared.json

            # MCP server integration
            ostruct run template.j2 schema.json --mcp-server deepwiki@https://mcp.deepwiki.com/sse

        📖 For detailed documentation: https://ostruct.readthedocs.io
        """
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
