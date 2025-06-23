"""Command modules for ostruct CLI."""

import click

from .list_models import list_models
from .run import run
from .update_registry import update_registry


def create_command_group() -> click.Group:
    """Create and configure the CLI command group with all commands."""
    # Create the main CLI group
    group = click.Group()

    # Add all commands to the group
    group.add_command(run)
    group.add_command(update_registry)
    group.add_command(list_models)

    return group


# Export commands for easy importing
__all__ = [
    "run",
    "update_registry",
    "list_models",
    "create_command_group",
]
