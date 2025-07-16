"""Main entry point for python -m ostruct.cli.runx."""

import sys

from .runx_main import runx_main

if __name__ == "__main__":
    sys.exit(runx_main())
