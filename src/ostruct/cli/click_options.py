"""Click command and options for the CLI.

This module contains all Click-related code separated from the main CLI logic.
We isolate this code here and provide proper type annotations for Click's
decorator-based API.
"""

from typing import Any, Callable, TypeVar, Union, cast

import click
from click import Command

from ostruct import __version__
from ostruct.cli.errors import (  # noqa: F401 - Used in error handling
    SystemPromptError,
    TaskTemplateVariableError,
)

F = TypeVar("F", bound=Callable[..., Any])
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


def debug_options(f: Callable) -> Callable:
    """Add debug-related CLI options."""
    f = click.option(
        "--show-model-schema",
        is_flag=True,
        help="Show generated Pydantic model schema",
    )(f)
    f = click.option(
        "--debug-validation",
        is_flag=True,
        help="Show detailed validation errors",
    )(f)
    return f


def file_options(f: Callable) -> Callable:
    """Add file-related CLI options."""
    f = click.option(
        "--file", "-f", multiple=True, help="File mapping (name=path)"
    )(f)
    f = click.option(
        "--files",
        multiple=True,
        help="Multiple file mappings from a directory",
    )(f)
    f = click.option(
        "--dir", "-d", multiple=True, help="Directory mapping (name=path)"
    )(f)
    f = click.option(
        "--allowed-dir",
        multiple=True,
        help="Additional allowed directory paths",
    )(f)
    f = click.option(
        "--base-dir", type=str, help="Base directory for relative paths"
    )(f)
    f = click.option(
        "--allowed-dir-file",
        type=str,
        help="File containing allowed directory paths",
    )(f)
    f = click.option(
        "--dir-recursive", is_flag=True, help="Recursively process directories"
    )(f)
    f = click.option(
        "--dir-ext", type=str, help="Filter directory files by extension"
    )(f)
    return f


def variable_options(f: Callable) -> Callable:
    """Add variable-related CLI options."""
    f = click.option(
        "--var", "-v", multiple=True, help="Variable mapping (name=value)"
    )(f)
    f = click.option(
        "--json-var",
        "-j",
        multiple=True,
        help="JSON variable mapping (name=json_value)",
    )(f)
    return f


def model_options(f: Callable) -> Callable:
    """Add model-related CLI options."""
    f = click.option(
        "--model", type=str, default="gpt-4o", help="OpenAI model to use"
    )(f)
    f = click.option(
        "--temperature", type=float, default=0.0, help="Sampling temperature"
    )(f)
    f = click.option(
        "--max-tokens", type=int, help="Maximum tokens in response"
    )(f)
    f = click.option(
        "--top-p", type=float, default=1.0, help="Nucleus sampling threshold"
    )(f)
    f = click.option(
        "--frequency-penalty",
        type=float,
        default=0.0,
        help="Frequency penalty",
    )(f)
    f = click.option(
        "--presence-penalty", type=float, default=0.0, help="Presence penalty"
    )(f)
    return f


def create_click_command() -> Callable[[F], Command]:
    """Create the Click command with all options.

    Returns:
        A decorator function that adds all CLI options to the command.
    """

    def decorator(f: F) -> Command:
        # Start with the base command
        cmd: DecoratedCommand = click.command(
            help="Make structured OpenAI API calls."
        )(f)

        # Add all options
        cmd = click.option(
            "--task",
            help="Task template string",
            type=str,
            callback=validate_task_params,
        )(cmd)
        cmd = click.option(
            "--task-file",
            help="Task template file path",
            type=str,
            callback=validate_task_params,
        )(cmd)
        cmd = click.option(
            "--system-prompt",
            help="System prompt string",
            type=str,
            callback=validate_system_prompt_params,
        )(cmd)
        cmd = click.option(
            "--system-prompt-file",
            help="System prompt file path",
            type=str,
            callback=validate_system_prompt_params,
        )(cmd)
        cmd = click.option(
            "--schema-file",
            required=True,
            help="JSON schema file for response validation",
            type=str,
        )(cmd)
        cmd = click.option(
            "--ignore-task-sysprompt",
            is_flag=True,
            help="Ignore system prompt from task template YAML frontmatter",
        )(cmd)
        cmd = click.option(
            "--timeout",
            type=float,
            default=60.0,
            help="API timeout in seconds",
        )(cmd)
        cmd = click.option(
            "--output-file", help="Write JSON output to file", type=str
        )(cmd)
        cmd = click.option(
            "--dry-run",
            is_flag=True,
            help="Simulate API call without making request",
        )(cmd)
        cmd = click.option(
            "--no-progress", is_flag=True, help="Disable progress indicators"
        )(cmd)
        cmd = click.option(
            "--progress-level",
            type=click.Choice(["none", "basic", "detailed"]),
            default="basic",
            help="Progress reporting level",
        )(cmd)
        cmd = click.option(
            "--api-key", help="OpenAI API key (overrides env var)", type=str
        )(cmd)
        cmd = click.option(
            "--verbose",
            is_flag=True,
            help="Enable verbose output and detailed logging",
        )(cmd)
        cmd = click.option(
            "--debug-openai-stream",
            is_flag=True,
            help="Enable low-level debug output for OpenAI streaming",
        )(cmd)
        cmd = debug_options(cmd)
        cmd = file_options(cmd)
        cmd = variable_options(cmd)
        cmd = model_options(cmd)
        cmd = click.version_option(version=__version__)(cmd)
        return cast(Command, cmd)

    return decorator
