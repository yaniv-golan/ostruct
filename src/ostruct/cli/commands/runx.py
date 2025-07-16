"""The runx command for executing OST (Self-Executing Templates) files."""

import sys

import rich_click as click

from ..runx.runx_main import runx_main


@click.command(name="runx")
@click.argument("template_file", type=click.Path(exists=True))
@click.argument("args", nargs=-1)
@click.help_option("--help", "-h")
def runx(template_file: str, args: tuple[str, ...]) -> None:
    """Execute an OST (Self-Executing Template) file.

    This command executes .ost template files that contain embedded schemas
    and CLI metadata in their YAML front-matter. The template acts as a
    self-contained mini-CLI with its own argument parsing and policy enforcement.

    TEMPLATE_FILE: Path to the .ost template file to execute
    ARGS: Arguments to pass to the template

    Examples:
      ostruct runx hello.ost --name "World"
      ostruct runx analysis.ost data.csv --format json
    """
    # Construct argv for runx_main: [template_file, *args]
    argv = [template_file] + list(args)

    # Call runx_main and exit with its return code
    exit_code = runx_main(argv)
    sys.exit(exit_code)
