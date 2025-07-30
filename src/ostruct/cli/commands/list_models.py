"""List models command for ostruct CLI."""

import click

from .models import _list_models_impl, get_next_minor_version


@click.command("list-models", deprecated=True, hidden=True)
@click.option(
    "--format",
    type=click.Choice(["table", "json", "simple"]),
    default="table",
    help="Output format for model list",
)
@click.option(
    "--show-deprecated",
    is_flag=True,
    help="Include deprecated models in output",
)
def list_models(format: str = "table", show_deprecated: bool = False) -> None:
    """[DEPRECATED] List available models from the registry. Use 'ostruct models list' instead."""
    # Show deprecation warning
    next_version = get_next_minor_version()
    click.echo(
        f"⚠️ Warning: 'list-models' is deprecated and will be removed in v{next_version}. "
        "Use 'ostruct models list' instead.",
        err=True,
    )

    # Call the extracted implementation
    _list_models_impl(format, show_deprecated)
