"""Command modules for ostruct CLI."""

import click

from .files import files
from .list_models import list_models
from .run import run
from .runx import runx
from .scaffold import scaffold
from .setup import setup
from .update_registry import update_registry


def create_command_group() -> click.Group:
    """Create and configure the CLI command group with all commands."""
    # Create the main CLI group
    group = click.Group()

    # Add all commands to the group
    group.add_command(run)
    group.add_command(runx)
    group.add_command(scaffold)
    group.add_command(setup)
    group.add_command(update_registry)
    group.add_command(list_models)
    group.add_command(files)

    return group


# Export commands for easy importing
__all__ = [
    "run",
    "runx",
    "scaffold",
    "setup",
    "update_registry",
    "list_models",
    "files",
    "create_command_group",
]
