"""Models command group for ostruct CLI."""

import json
import sys
from typing import Optional

import click
from openai_model_registry import ModelRegistry
from tabulate import tabulate

from ostruct import __version__

from ..exit_codes import ExitCode


def get_next_minor_version() -> str:
    """Calculate the next minor version for deprecation warnings."""
    try:
        # Parse current version (e.g., "1.4.1" -> [1, 4, 1])
        parts = __version__.split(".")
        if len(parts) >= 2:
            major = int(parts[0])
            minor = int(parts[1])
            return f"{major}.{minor + 1}.0"
        return "next minor version"
    except (ValueError, IndexError):
        return "next minor version"


def _list_models_impl(
    format: str = "table", show_deprecated: bool = False
) -> None:
    """Implementation of list models functionality."""
    try:
        registry = ModelRegistry.get_instance()
        models = registry.models

        # Filter models if not showing deprecated
        if not show_deprecated:
            # Filter out deprecated models (this depends on registry implementation)
            filtered_models = []
            for model_id in models:
                try:
                    capabilities = registry.get_capabilities(model_id)
                    # If we can get capabilities, it's likely not deprecated
                    filtered_models.append(
                        {
                            "id": model_id,
                            "context_window": capabilities.context_window,
                            "max_output": capabilities.max_output_tokens,
                        }
                    )
                except Exception:
                    # Skip models that can't be accessed (likely deprecated)
                    continue
            models_data = filtered_models
        else:
            # Include all models
            models_data = []
            for model_id in models:
                try:
                    capabilities = registry.get_capabilities(model_id)
                    models_data.append(
                        {
                            "id": model_id,
                            "context_window": capabilities.context_window,
                            "max_output": capabilities.max_output_tokens,
                            "status": "active",
                        }
                    )
                except Exception:
                    models_data.append(
                        {
                            "id": model_id,
                            "context_window": "N/A",
                            "max_output": "N/A",
                            "status": "deprecated",
                        }
                    )

        if format == "table":
            # Prepare table data
            table_data = []
            headers = ["Model ID", "Context Window", "Max Output", "Status"]

            for model in models_data:
                status = model.get("status", "active")
                context = (
                    f"{model['context_window']:,}"
                    if isinstance(model["context_window"], int)
                    else model["context_window"]
                )
                output = (
                    f"{model['max_output']:,}"
                    if isinstance(model["max_output"], int)
                    else model["max_output"]
                )

                row = [model["id"], context, output, status]
                table_data.append(row)

            click.echo("Available Models:")
            click.echo(
                tabulate(table_data, headers=headers, tablefmt="simple")
            )
        elif format == "json":
            click.echo(json.dumps(models_data, indent=2))
        else:  # simple
            for model in models_data:
                click.echo(model["id"])

    except Exception as e:
        click.echo(f"❌ Error listing models: {str(e)}")
        sys.exit(ExitCode.API_ERROR.value)


def _update_registry_impl(
    url: Optional[str] = None, force: bool = False
) -> None:
    """Implementation of update registry functionality."""
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


@click.group("models")
def models() -> None:
    """Manage model registry and list available models.

    This command group provides functionality to list available OpenAI models
    and update the local model registry with the latest definitions.
    """
    pass


@models.command("list")
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
def list_models_new(
    format: str = "table", show_deprecated: bool = False
) -> None:
    """List available models from the registry."""
    _list_models_impl(format, show_deprecated)


@models.command("update")
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
def update_registry_new(
    url: Optional[str] = None, force: bool = False
) -> None:
    """Update the model registry with the latest model definitions.

    This command fetches the latest model registry from the official repository
    or a custom URL if provided, and updates the local registry file.

    Example:
        ostruct models update
        ostruct models update --url https://example.com/models.yml
    """
    _update_registry_impl(url, force)
