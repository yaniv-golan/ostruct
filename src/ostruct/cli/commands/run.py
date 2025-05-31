"""Run command for ostruct CLI."""

import asyncio
import json
import logging
import sys
from typing import Any

import click

from ..click_options import all_options
from ..config import OstructConfig
from ..errors import (
    CLIError,
    InvalidJSONError,
    SchemaFileError,
    SchemaValidationError,
    handle_error,
)
from ..exit_codes import ExitCode
from ..runner import run_cli_async
from ..types import CLIParams

logger = logging.getLogger(__name__)


@click.command()
@click.argument("task_template", type=click.Path(exists=True))
@click.argument("schema_file", type=click.Path(exists=True))
@all_options
@click.pass_context
def run(
    ctx: click.Context,
    task_template: str,
    schema_file: str,
    **kwargs: Any,
) -> None:
    """Run structured output generation with multi-tool integration.

    \b
    📁 FILE ROUTING OPTIONS:

    Template Access Only:
      -ft, --file-for-template FILE     Files available in template only
      -dt, --dir-for-template DIR       Directories for template access

    Code Interpreter (execution & analysis):
      -fc, --file-for-code-interpreter FILE    Upload files for code execution
      -dc, --dir-for-code-interpreter DIR      Upload directories for analysis

    File Search (document retrieval):
      -fs, --file-for-file-search FILE         Upload files for vector search
      -ds, --dir-for-search DIR                Upload directories for search

    Advanced Routing:
      --file-for TOOL PATH              Route files to specific tools
                                        Example: --file-for code-interpreter data.json

    \b
    🔧 TOOL INTEGRATION:

    MCP Servers:
      --mcp-server [LABEL@]URL          Connect to MCP server
                                        Example: --mcp-server deepwiki@https://mcp.deepwiki.com/sse

    \b
    ⚡ EXAMPLES:

    Basic usage:
      ostruct run template.j2 schema.json -V name=value

    Multi-tool explicit routing:
      ostruct run analysis.j2 schema.json -fc data.csv -fs docs.pdf -ft config.yaml

    Legacy compatibility (still works):
      ostruct run template.j2 schema.json -f config main.py -d src ./src

    \b
    Arguments:
      TASK_TEMPLATE  Path to Jinja2 template file
      SCHEMA_FILE    Path to JSON schema file defining output structure
    """
    try:
        # Convert Click parameters to typed dict
        params: CLIParams = {
            "task_file": task_template,
            "task": None,
            "schema_file": schema_file,
        }
        # Add all kwargs to params (type ignore for dynamic key assignment)
        for k, v in kwargs.items():
            params[k] = v  # type: ignore[literal-required]

        # Apply configuration defaults if values not explicitly provided
        # Check for command-level config option first, then group-level
        command_config = kwargs.get("config")
        if command_config:
            config = OstructConfig.load(command_config)
        else:
            config = ctx.obj.get("config") if ctx.obj else OstructConfig()

        if params.get("model") is None:
            params["model"] = config.get_model_default()

        # Run the async function synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            exit_code = loop.run_until_complete(run_cli_async(params))
            sys.exit(int(exit_code))
        except SchemaValidationError as e:
            # Log the error with full context
            logger.error("Schema validation error: %s", str(e))
            if e.context:
                logger.debug(
                    "Error context: %s", json.dumps(e.context, indent=2)
                )
            # Re-raise to preserve error chain and exit code
            raise
        except (CLIError, InvalidJSONError, SchemaFileError) as e:
            handle_error(e)
            sys.exit(
                e.exit_code
                if hasattr(e, "exit_code")
                else ExitCode.INTERNAL_ERROR
            )
        except click.UsageError as e:
            handle_error(e)
            sys.exit(ExitCode.USAGE_ERROR)
        except Exception as e:
            handle_error(e)
            sys.exit(ExitCode.INTERNAL_ERROR)
        finally:
            loop.close()
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        raise
