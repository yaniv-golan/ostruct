# Configuration file for the Sphinx documentation builder.
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("../../src"))


# Read version - handle dynamic versioning
def get_version():
    """Get version from installed package or fallback to development version."""
    try:
        # Try to get version from installed package
        from importlib.metadata import version as get_installed_version

        return get_installed_version("ostruct-cli")
    except Exception:
        # Fallback for development/build environment
        try:
            # Try to get version from git tags using poetry-dynamic-versioning
            import subprocess

            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                git_version = result.stdout.strip()
                # Remove 'v' prefix if present
                return git_version.lstrip("v")
        except Exception:
            pass

        # Final fallback
        return "1.0.0-dev"


version = get_version()

project = "ostruct-cli"
copyright = "2025, Yaniv Golan"
author = "Yaniv Golan"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_design",
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
