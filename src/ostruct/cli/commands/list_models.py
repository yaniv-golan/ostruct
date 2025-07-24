"""List models command for ostruct CLI."""

import json
import sys

import click
from openai_model_registry import ModelRegistry
from tabulate import tabulate

from ..exit_codes import ExitCode


@click.command("list-models")
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
    """List available models from the registry."""
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
