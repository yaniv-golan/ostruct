"""Click command and options for the CLI.

This module contains all Click-related code separated from the main CLI logic.
We isolate this code here and provide proper type annotations for Click's
decorator-based API.
"""

from typing import Any, Callable, TypeVar, Union, cast

import click
from click import Command
from typing_extensions import ParamSpec

from ostruct import __version__
from ostruct.cli.errors import (  # noqa: F401 - Used in error handling
    SystemPromptError,
    TaskTemplateVariableError,
)
from ostruct.cli.validators import (
    validate_json_variable,
    validate_name_path_pair,
    validate_variable,
)

P = ParamSpec("P")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])
CommandDecorator = Callable[[F], Command]
DecoratedCommand = Union[Command, Callable[..., Any]]


def debug_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add debug-related CLI options."""
    # Initial conversion to Command if needed
    cmd: Any = f if isinstance(f, Command) else f

    # Add options without redundant casts
    cmd = click.option(
        "--show-model-schema",
        is_flag=True,
        help="Show generated Pydantic model schema",
    )(cmd)

    cmd = click.option(
        "--debug-validation",
        is_flag=True,
        help="Show detailed validation errors",
    )(cmd)

    # Final cast to Command for return type
    return cast(Command, cmd)


def file_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add file-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "-f",
        "--file",
        "files",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATH>",
        callback=validate_name_path_pair,
        help="""Associate a file with a variable name. The file will be available in
        your template as the specified variable. You can specify this option multiple times.
        Example: -f code main.py -f test test_main.py""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "-d",
        "--dir",
        "dir",
        multiple=True,
        nargs=2,
        metavar="<NAME> <DIR>",
        callback=validate_name_path_pair,
        help="""Associate a directory with a variable name. All files in the directory
        will be available in your template. Use -R for recursive scanning.
        Example: -d src ./src""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "-p",
        "--pattern",
        "patterns",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATTERN>",
        help="""Associate a glob pattern with a variable name. Matching files will be
        available in your template. Use -R for recursive matching.
        Example: -p logs '*.log'""",
    )(cmd)

    cmd = click.option(
        "-R",
        "--recursive",
        is_flag=True,
        help="Process directories and patterns recursively",
    )(cmd)

    cmd = click.option(
        "--base-dir",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="""Base directory for resolving relative paths. All file operations will be
        relative to this directory. Defaults to current directory.""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "-A",
        "--allow",
        "allowed_dirs",
        multiple=True,
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="""Add an allowed directory for security. Files must be within allowed
        directories. Can be specified multiple times.""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "--allowed-dir-file",
        type=click.Path(exists=True, file_okay=True, dir_okay=False),
        help="""File containing allowed directory paths, one per line. Lines starting
        with # are treated as comments.""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    return cast(Command, cmd)


def variable_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add variable-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "-V",
        "--var",
        "var",
        multiple=True,
        metavar="name=value",
        callback=validate_variable,
        help="""Define a simple string variable. Format: name=value
        Example: -V debug=true -V env=prod""",
    )(cmd)

    cmd = click.option(
        "-J",
        "--json-var",
        "json_var",
        multiple=True,
        metavar='name=\'{"json":"value"}\'',
        callback=validate_json_variable,
        help="""Define a JSON variable. Format: name='{"key":"value"}'
        Example: -J config='{"env":"prod","debug":true}'""",
    )(cmd)

    return cast(Command, cmd)


def model_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add model-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "-m",
        "--model",
        default="gpt-4o",
        show_default=True,
        help="""OpenAI model to use. Must support structured output.
        Supported models:
        - gpt-4o (128k context window)
        - o1 (200k context window)
        - o3-mini (200k context window)""",
    )(cmd)

    cmd = click.option(
        "--temperature",
        type=click.FloatRange(0.0, 2.0),
        help="""Sampling temperature. Controls randomness in the output.
        Range: 0.0 to 2.0. Lower values are more focused.""",
    )(cmd)

    cmd = click.option(
        "--max-output-tokens",
        type=click.IntRange(1, None),
        help="""Maximum number of tokens in the output.
        Higher values allow longer responses but cost more.""",
    )(cmd)

    cmd = click.option(
        "--top-p",
        type=click.FloatRange(0.0, 1.0),
        help="""Top-p (nucleus) sampling parameter. Controls diversity.
        Range: 0.0 to 1.0. Lower values are more focused.""",
    )(cmd)

    cmd = click.option(
        "--frequency-penalty",
        type=click.FloatRange(-2.0, 2.0),
        help="""Frequency penalty for text generation.
        Range: -2.0 to 2.0. Positive values reduce repetition.""",
    )(cmd)

    cmd = click.option(
        "--presence-penalty",
        type=click.FloatRange(-2.0, 2.0),
        help="""Presence penalty for text generation.
        Range: -2.0 to 2.0. Positive values encourage new topics.""",
    )(cmd)

    cmd = click.option(
        "--reasoning-effort",
        type=click.Choice(["low", "medium", "high"]),
        help="""Control reasoning effort (if supported by model).
        Higher values may improve output quality but take longer.""",
    )(cmd)

    return cast(Command, cmd)


def system_prompt_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add system prompt related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--sys-prompt",
        "system_prompt",
        help="""Provide system prompt directly. This sets the initial context
        for the model. Example: --sys-prompt "You are a code reviewer." """,
    )(cmd)

    cmd = click.option(
        "--sys-file",
        "system_prompt_file",
        type=click.Path(exists=True, dir_okay=False),
        help="""Load system prompt from file. The file should contain the prompt text.
        Example: --sys-file prompts/code_review.txt""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "--ignore-task-sysprompt",
        is_flag=True,
        help="""Ignore system prompt in task template. By default, system prompts
        in template frontmatter are used.""",
    )(cmd)

    return cast(Command, cmd)


def output_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add output-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--output-file",
        type=click.Path(dir_okay=False),
        help="""Write output to file instead of stdout.
        Example: --output-file result.json""",
        shell_complete=click.Path(file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "--dry-run",
        is_flag=True,
        help="""Validate and render but skip API call. Useful for testing
        template rendering and validation.""",
    )(cmd)

    return cast(Command, cmd)


def api_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add API-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--api-key",
        help="""OpenAI API key. If not provided, uses OPENAI_API_KEY
        environment variable.""",
    )(cmd)

    cmd = click.option(
        "--timeout",
        type=click.FloatRange(1.0, None),
        default=60.0,
        show_default=True,
        help="API timeout in seconds.",
    )(cmd)

    return cast(Command, cmd)


def debug_progress_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add debugging and progress CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--no-progress", is_flag=True, help="Disable progress indicators"
    )(cmd)

    cmd = click.option(
        "--progress-level",
        type=click.Choice(["none", "basic", "detailed"]),
        default="basic",
        show_default=True,
        help="""Control progress verbosity. 'none' shows no progress,
        'basic' shows key steps, 'detailed' shows all steps.""",
    )(cmd)

    cmd = click.option(
        "--verbose", is_flag=True, help="Enable verbose logging"
    )(cmd)

    cmd = click.option(
        "--debug-openai-stream",
        is_flag=True,
        help="Debug OpenAI streaming process",
    )(cmd)

    return cast(Command, cmd)


def all_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add all CLI options.

    Args:
        f: Function to decorate

    Returns:
        Decorated function
    """
    decorators = [
        model_options,  # Model selection and parameters first
        system_prompt_options,  # System prompt configuration
        file_options,  # File and directory handling
        variable_options,  # Variable definitions
        output_options,  # Output control
        api_options,  # API configuration
        debug_options,  # Debug settings
        debug_progress_options,  # Progress and logging
    ]

    for decorator in decorators:
        f = decorator(f)

    return cast(Command, f)


def create_click_command() -> CommandDecorator:
    """Create the Click command with all options.

    Returns:
        A decorator function that adds all CLI options to the command.
    """

    def decorator(f: F) -> Command:
        # Initial command creation
        cmd: Any = click.command()(f)

        # Add version option
        cmd = click.version_option(
            __version__,
            "--version",
            "-V",
            message="%(prog)s CLI version %(version)s",
        )(cmd)

        return cast(Command, cmd)

    return decorator
