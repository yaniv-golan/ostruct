#!/usr/bin/env python3
"""
Build script to generate the macOS installation script with the current version.

This script:
1. Reads the version from pyproject.toml
2. Takes the template script (install-macos.sh.template)
3. Replaces the {{OSTRUCT_VERSION}} placeholder with the actual version
4. Writes the final script to install-macos.sh
"""

import re
import sys
from pathlib import Path


def extract_version_from_pyproject(pyproject_path: Path) -> str:
    """Extract version from pyproject.toml file."""
    try:
        content = pyproject_path.read_text(encoding="utf-8")

        # Look for version = "x.y.z" in the [project] section
        version_match = re.search(
            r'version\s*=\s*["\']([^"\']+)["\']', content
        )

        if not version_match:
            raise ValueError("Could not find version in pyproject.toml")

        version = version_match.group(1)
        print(f"Found version: {version}")
        return version

    except Exception as e:
        print(f"Error reading pyproject.toml: {e}", file=sys.stderr)
        sys.exit(1)


def generate_install_script(
    template_path: Path, output_path: Path, version: str
) -> None:
    """Generate the final installation script from template."""
    try:
        # Read template
        template_content = template_path.read_text(encoding="utf-8")

        # Replace placeholder with actual version
        final_content = template_content.replace(
            "{{OSTRUCT_VERSION}}", version
        )

        # Write final script
        output_path.write_text(final_content, encoding="utf-8")

        # Make executable
        output_path.chmod(0o755)

        print(f"Generated {output_path} with version {version}")

    except Exception as e:
        print(f"Error generating install script: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function."""
    # Get script directory and project root
    script_dir = Path(__file__).parent
    scripts_root = script_dir.parent
    project_root = scripts_root.parent

    # Define paths
    pyproject_path = project_root / "pyproject.toml"
    template_path = scripts_root / "install" / "macos" / "install.sh.template"
    output_path = scripts_root / "generated" / "install-macos.sh"

    # Validate paths exist
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found", file=sys.stderr)
        sys.exit(1)

    if not template_path.exists():
        print(f"Error: {template_path} not found", file=sys.stderr)
        sys.exit(1)

    # Extract version and generate script
    version = extract_version_from_pyproject(pyproject_path)
    generate_install_script(template_path, output_path, version)

    print("✅ Installation script build complete!")


if __name__ == "__main__":
    main()
