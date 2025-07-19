"""Main entry point for python -m ostruct.cli.runx."""

import sys

from .runx_main import runx_main

if __name__ == "__main__":
    # When called via 'python -m ostruct.cli.runx', sys.argv[0] is the module path
    # We need to skip it and pass only the template file and arguments
    argv = sys.argv[1:] if len(sys.argv) > 1 else []
    sys.exit(runx_main(argv))
