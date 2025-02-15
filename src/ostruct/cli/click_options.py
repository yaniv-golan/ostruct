"""Click command and options for the CLI.

This module contains all Click-related code separated from the main CLI logic.
We isolate this code here and provide proper type annotations for Click's
decorator-based API.
"""

from typing import Any, Callable, ParamSpec, TypeVar, Union, cast

import click
from click import Command

from ostruct import __version__
from ostruct.cli.errors import (  # noqa: F401 - Used in error handling
    SystemPromptError,
    TaskTemplateVariableError,
)

P = ParamSpec("P")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])
CommandDecorator = Callable[[F], Command]
DecoratedCommand = Union[Command, Callable[..., Any]]


def validate_task_params(
    ctx: click.Context, param: click.Parameter, value: Any
) -> Any:
    """Validate task-related parameters."""
    if not hasattr(ctx, "params"):
        return value

    # Check for conflicting task parameters
    if (
        param.name == "task_file"
        and value is not None
        and ctx.params.get("task") is not None
    ):
        raise click.UsageError("Cannot specify both --task and --task-file")
    elif (
        param.name == "task"
        and value is not None
        and ctx.params.get("task_file") is not None
    ):
        raise click.UsageError("Cannot specify both --task and --task-file")

    return value


def validate_system_prompt_params(
    ctx: click.Context, param: click.Parameter, value: Any
) -> Any:
    """Validate system prompt parameters."""
    if not hasattr(ctx, "params"):
        return value

    # Check for conflicting system prompt parameters
    if (
        param.name == "system_prompt_file"
        and value is not None
        and ctx.params.get("system_prompt") is not None
    ):
        raise click.UsageError(
            "Cannot specify both --system-prompt and --system-prompt-file"
        )
    elif (
        param.name == "system_prompt"
        and value is not None
        and ctx.params.get("system_prompt_file") is not None
    ):
        raise click.UsageError(
            "Cannot specify both --system-prompt and --system-prompt-file"
        )

    return value


def debug_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add debug-related CLI options."""
    cmd = f if isinstance(f, Command) else cast(Command, f)

    cmd = cast(
        Command,
        click.option(
            "--show-model-schema",
            is_flag=True,
            help="Show generated Pydantic model schema",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--debug-validation",
            is_flag=True,
            help="Show detailed validation errors",
        )(cmd),
    )
    return cmd


def file_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add file-related CLI options."""
    cmd = f if isinstance(f, Command) else cast(Command, f)

    cmd = cast(
        Command,
        click.option(
            "--file", "-f", multiple=True, help="File mapping (name=path)"
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--files",
            multiple=True,
            help="Multiple file mappings from a directory",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--dir", "-d", multiple=True, help="Directory mapping (name=path)"
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--allowed-dir",
            multiple=True,
            help="Additional allowed directory paths",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--base-dir", type=str, help="Base directory for relative paths"
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--allowed-dir-file",
            type=str,
            help="File containing allowed directory paths",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--dir-recursive",
            is_flag=True,
            help="Recursively process directories",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--dir-ext", type=str, help="Filter directory files by extension"
        )(cmd),
    )
    return cmd


def variable_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add variable-related CLI options."""
    cmd = f if isinstance(f, Command) else cast(Command, f)

    cmd = cast(
        Command,
        click.option(
            "--var", "-v", multiple=True, help="Variable mapping (name=value)"
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--json-var",
            "-j",
            multiple=True,
            help="JSON variable mapping (name=json_value)",
        )(cmd),
    )
    return cmd


def model_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add model-related CLI options."""
    cmd = f if isinstance(f, Command) else cast(Command, f)

    cmd = cast(
        Command,
        click.option(
            "--model",
            type=str,
            default="gpt-4o",
            help="The model to use",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--temperature",
            type=float,
            default=None,
            help="The temperature to use (if supported by model)",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--max-output-tokens",
            type=int,
            default=None,
            help="The maximum number of tokens to generate (if supported by model)",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--top-p",
            type=float,
            default=None,
            help="Nucleus sampling threshold (if supported by model)",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--frequency-penalty",
            type=float,
            default=None,
            help="Frequency penalty (if supported by model)",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--presence-penalty",
            type=float,
            default=None,
            help="Presence penalty (if supported by model)",
        )(cmd),
    )
    cmd = cast(
        Command,
        click.option(
            "--reasoning-effort",
            type=click.Choice(["low", "medium", "high"]),
            default=None,
            help="Reasoning effort level (if supported by model)",
        )(cmd),
    )
    return cmd


def create_click_command() -> CommandDecorator:
    """Create the Click command with all options.

    Returns:
        A decorator function that adds all CLI options to the command.
    """

    def decorator(f: F) -> Command:
        # Cast the initial command to ensure type safety
        cmd = cast(Command, click.command()(f))

        # Add all core options with explicit casting
        cmd = cast(
            Command,
            click.option(
                "--task",
                help="Task template string",
                type=str,
                callback=validate_task_params,
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--task-file",
                help="Task template file path",
                type=str,
                callback=validate_task_params,
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--system-prompt",
                help="System prompt string",
                type=str,
                callback=validate_system_prompt_params,
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--system-prompt-file",
                help="System prompt file path",
                type=str,
                callback=validate_system_prompt_params,
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--schema-file",
                required=True,
                help="JSON schema file for response validation",
                type=str,
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--ignore-task-sysprompt",
                is_flag=True,
                help="Ignore system prompt from task template YAML frontmatter",
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--timeout",
                type=float,
                default=60.0,
                help="API timeout in seconds",
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--output-file", help="Write JSON output to file", type=str
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--dry-run",
                is_flag=True,
                help="Simulate API call without making request",
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--no-progress",
                is_flag=True,
                help="Disable progress indicators",
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--progress-level",
                type=click.Choice(["none", "basic", "detailed"]),
                default="basic",
                help="Progress reporting level",
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--api-key",
                help="OpenAI API key (overrides env var)",
                type=str,
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--verbose",
                is_flag=True,
                help="Enable verbose output and detailed logging",
            )(cmd),
        )
        cmd = cast(
            Command,
            click.option(
                "--debug-openai-stream",
                is_flag=True,
                help="Enable low-level debug output for OpenAI streaming",
            )(cmd),
        )

        # Add version option
        cmd = click.version_option(
            __version__,
            "--version",
            "-V",
            message="%(prog)s CLI version %(version)s",
        )(cmd)

        # Add all option groups
        cmd = debug_options(cmd)
        cmd = file_options(cmd)
        cmd = variable_options(cmd)
        cmd = model_options(cmd)

        return cmd

    return decorator
