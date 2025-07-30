"""Update registry command for ostruct CLI."""

from typing import Optional

import click

from .models import _update_registry_impl, get_next_minor_version


@click.command("update-registry", deprecated=True, hidden=True)
@click.option(
    "--url",
    help="URL to fetch the registry from. Defaults to official repository.",
    default=None,
)
@click.option(
    "--force",
    is_flag=True,
    help="Force update even if the registry is already up to date.",
    default=False,
)
def update_registry(url: Optional[str] = None, force: bool = False) -> None:
    """[DEPRECATED] Update the model registry with the latest model definitions. Use 'ostruct models update' instead.

    This command fetches the latest model registry from the official repository
    or a custom URL if provided, and updates the local registry file.

    Example:
        ostruct update-registry
        ostruct update-registry --url https://example.com/models.yml
    """
    # Show deprecation warning
    next_version = get_next_minor_version()
    click.echo(
        f"⚠️ Warning: 'update-registry' is deprecated and will be removed in v{next_version}. "
        "Use 'ostruct models update' instead.",
        err=True,
    )

    # Call the extracted implementation
    _update_registry_impl(url, force)
