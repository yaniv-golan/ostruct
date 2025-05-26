"""Update registry command for ostruct CLI."""

import sys
from typing import Optional

import click
from openai_model_registry import ModelRegistry

from ..exit_codes import ExitCode


@click.command("update-registry")
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
    """Update the model registry with the latest model definitions.

    This command fetches the latest model registry from the official repository
    or a custom URL if provided, and updates the local registry file.

    Example:
        ostruct update-registry
        ostruct update-registry --url https://example.com/models.yml
    """
    try:
        registry = ModelRegistry.get_instance()

        # Show current registry config path
        config_path = registry.config.registry_path
        click.echo(f"Current registry file: {config_path}")

        if force:
            click.echo("🔄 Forcing registry update...")
            refresh_result = registry.refresh_from_remote(url)
            if refresh_result.success:
                click.echo("✅ Registry successfully updated!")
            else:
                click.echo(
                    f"❌ Failed to update registry: {refresh_result.message}"
                )
            return

        click.echo("🔍 Checking for registry updates...")
        update_result = registry.check_for_updates()

        if update_result.status.value == "update_available":
            click.echo(f"📦 Update available: {update_result.message}")
            click.echo("🔄 Updating registry...")
            refresh_result = registry.refresh_from_remote(url)
            if refresh_result.success:
                click.echo("✅ Registry successfully updated!")
            else:
                click.echo(
                    f"❌ Failed to update registry: {refresh_result.message}"
                )
        elif update_result.status.value == "already_current":
            click.echo("✅ Registry is already up to date")
        else:
            click.echo(f"⚠️ Registry check failed: {update_result.message}")
    except Exception as e:
        click.echo(f"❌ Error updating registry: {str(e)}")
        sys.exit(ExitCode.API_ERROR.value)
