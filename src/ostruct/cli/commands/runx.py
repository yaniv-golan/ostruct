"""The runx command for executing OST files (self-executing ostruct prompts)."""

import sys

import rich_click as click

from ..runx.runx_main import runx_main


@click.command(
    name="runx",
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
    },
)
@click.argument("template_file", type=click.Path(exists=True))
@click.argument("args", nargs=-1)
@click.help_option("--help", "-h")
def runx(template_file: str, args: tuple[str, ...]) -> None:
    """Execute an OST file (self-executing ostruct prompt).

    This command executes .ost files that contain embedded schemas
    and CLI metadata in their YAML front-matter. Each OST file acts as a
    self-contained tool with its own argument parsing, help system, and policy enforcement.

    TEMPLATE_FILE: Path to the .ost file (self-executing ostruct prompt) to execute
    ARGS: Arguments to pass to the OST file

    Examples:
      ostruct runx hello.ost --name "World"
      ostruct runx analysis.ost data.csv --format json
    """
    # Construct argv for runx_main: [template_file, *args]
    argv = [template_file] + list(args)

    # Call runx_main and exit with its return code
    exit_code = runx_main(argv)
    sys.exit(exit_code)
