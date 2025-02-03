"""Click command and options for the CLI.

This module contains all Click-related code separated from the main CLI logic.
We isolate this code here and disable mypy type checking for the entire module
because Click's decorator-based API is not easily type-checkable, leading to
many type: ignore comments in the main code.
"""

# mypy: ignore-errors
# ^ This tells mypy to ignore type checking for this entire file

from typing import Any, Callable

import click

from ostruct import __version__
from ostruct.cli.errors import (  # noqa: F401 - Used in error handling
    SystemPromptError,
    TaskTemplateVariableError,
)


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


def create_click_command() -> Callable:
    """Create the Click command with all options."""

    def decorator(f: Callable) -> Callable:
        f = click.command(help="Make structured OpenAI API calls.")(f)
        f = click.option(
            "--task",
            help="Task template string",
            type=str,
            callback=validate_task_params,
        )(f)
        f = click.option(
            "--task-file",
            help="Task template file path",
            type=str,
            callback=validate_task_params,
        )(f)
        f = click.option(
            "--system-prompt",
            help="System prompt string",
            type=str,
            callback=validate_system_prompt_params,
        )(f)
        f = click.option(
            "--system-prompt-file",
            help="System prompt file path",
            type=str,
            callback=validate_system_prompt_params,
        )(f)
        f = click.option(
            "--schema-file",
            required=True,
            help="JSON schema file for response validation",
            type=str,
        )(f)
        f = click.option(
            "--ignore-task-sysprompt",
            is_flag=True,
            help="Ignore system prompt from task template YAML frontmatter",
        )(f)
        f = click.option(
            "--timeout",
            type=float,
            default=60.0,
            help="API timeout in seconds",
        )(f)
        f = click.option(
            "--output-file", help="Write JSON output to file", type=str
        )(f)
        f = click.option(
            "--dry-run",
            is_flag=True,
            help="Simulate API call without making request",
        )(f)
        f = click.option(
            "--no-progress", is_flag=True, help="Disable progress indicators"
        )(f)
        f = click.option(
            "--progress-level",
            type=click.Choice(["none", "basic", "detailed"]),
            default="basic",
            help="Progress reporting level",
        )(f)
        f = click.option(
            "--api-key", help="OpenAI API key (overrides env var)", type=str
        )(f)
        f = click.option(
            "--verbose",
            is_flag=True,
            help="Enable verbose output and detailed logging",
        )(f)
        f = click.option(
            "--debug-openai-stream",
            is_flag=True,
            help="Enable low-level debug output for OpenAI streaming",
        )(f)
        f = debug_options(f)
        f = file_options(f)
        f = variable_options(f)
        f = model_options(f)
        f = click.version_option(version=__version__)(f)
        return f

    return decorator
