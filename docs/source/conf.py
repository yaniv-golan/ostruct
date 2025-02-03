# Configuration file for the Sphinx documentation builder.
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("../../src"))

# Read version from pyproject.toml
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore  # Python <3.11

# Get the project root directory
root_dir = Path(__file__).parent.parent.parent
pyproject_path = root_dir / "pyproject.toml"

with open(pyproject_path, "rb") as f:
    pyproject_data = tomllib.load(f)
    version = pyproject_data["tool"]["poetry"]["version"]

project = "ostruct-cli"
copyright = "2025, Yaniv Golan"
author = "Yaniv Golan"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
    "myst_parser",
]

html_theme = "sphinx_rtd_theme"
# html_static_path = ["_static"]

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
