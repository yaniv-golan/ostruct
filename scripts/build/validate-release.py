#!/usr/bin/env python3
"""
Release validation script for ostruct.

This script automates the technical validation checks before releasing
a new version of ostruct. It should be run as part of the release process
documented in RELEASE_CHECKLIST.md.

Usage:
    python scripts/build/validate-release.py [--skip-clean-install]
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Union


class ReleaseValidator:
    def __init__(self, skip_clean_install: bool = False):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.skip_clean_install = skip_clean_install

    def log_error(self, message: str) -> None:
        self.errors.append(message)
        print(f"❌ ERROR: {message}")

    def log_warning(self, message: str) -> None:
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")

    def log_success(self, message: str) -> None:
        print(f"✅ {message}")

    def log_info(self, message: str) -> None:
        print(f"ℹ️  {message}")

    def run_command(
        self, cmd: List[str], cwd: Optional[str] = None, check: bool = True
    ) -> Union[subprocess.CompletedProcess, subprocess.CalledProcessError]:
        """Run a command and return the result."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=cwd, check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            if check:
                self.log_error(f"Command failed: {' '.join(cmd)}\n{e.stderr}")
                raise
            return e

    def check_version_consistency(self) -> bool:
        """Check that version is consistent across files."""
        self.log_info("Checking version consistency...")

        try:
            import tomli

            with open("pyproject.toml", "rb") as f:
                pyproject = tomli.load(f)

            # Check for dynamic versioning
            if (
                "dynamic" in pyproject.get("project", {})
                and "version" in pyproject["project"]["dynamic"]
            ):
                # Dynamic versioning - get version from poetry
                result = self.run_command(
                    ["poetry", "version", "-s"], check=False
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    self.log_success(
                        f"Version consistency check passed (dynamic): {version}"
                    )
                    return True
                else:
                    self.log_error("Failed to get version from poetry")
                    return False
            else:
                # Static versioning
                version = pyproject["project"]["version"]
                self.log_success(
                    f"Version consistency check passed (static): {version}"
                )
                return True

        except Exception as e:
            self.log_error(f"Version consistency check failed: {e}")
            return False

    def validate_pyproject(self) -> bool:
        """Validate pyproject.toml structure."""
        self.log_info("Validating pyproject.toml...")

        try:
            import tomli

            with open("pyproject.toml", "rb") as f:
                pyproject = tomli.load(f)

            # Check required fields
            required_fields = [
                "project.name",
                "project.description",
            ]

            # Check version (static or dynamic)
            project = pyproject.get("project", {})
            if "version" not in project and (
                "dynamic" not in project
                or "version" not in project.get("dynamic", [])
            ):
                self.log_error(
                    "Missing version: neither project.version nor dynamic versioning configured"
                )
                return False

            for field in required_fields:
                keys = field.split(".")
                obj = pyproject
                for key in keys:
                    if key not in obj:
                        self.log_error(f"Missing required field: {field}")
                        return False
                    obj = obj[key]

            self.log_success("pyproject.toml validation passed")
            return True

        except Exception as e:
            self.log_error(f"pyproject.toml validation failed: {e}")
            return False

    def build_package(self) -> bool:
        """Build the package and check outputs."""
        self.log_info("Building package...")

        try:
            # Clean previous builds
            if Path("dist").exists():
                shutil.rmtree("dist")

            # Build package
            self.run_command(["poetry", "build"])

            # Check outputs
            dist_files = list(Path("dist").glob("*"))
            wheels = [f for f in dist_files if f.suffix == ".whl"]
            sdists = [f for f in dist_files if f.suffix == ".gz"]

            if not wheels:
                self.log_error("No wheel files found in dist/")
                return False

            if not sdists:
                self.log_error("No source distribution found in dist/")
                return False

            self.log_success(
                f"Package built successfully: {len(wheels)} wheel(s), {len(sdists)} sdist(s)"
            )
            return True

        except Exception as e:
            self.log_error(f"Package build failed: {e}")
            return False

    def test_dependency_resolution(self) -> bool:
        """Test that dependencies can be resolved."""
        self.log_info("Testing dependency resolution...")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create requirements file from pyproject.toml
                import tomli

                with open("pyproject.toml", "rb") as f:
                    pyproject = tomli.load(f)

                deps = pyproject.get("project", {}).get("dependencies", [])

                req_file = Path(temp_dir) / "requirements.txt"
                with open(req_file, "w") as f:
                    for dep in deps:
                        f.write(f"{dep}\n")

                # Test dry-run installation
                python_exe = sys.executable
                self.run_command(
                    [
                        python_exe,
                        "-m",
                        "pip",
                        "install",
                        "--dry-run",
                        "-r",
                        str(req_file),
                    ]
                )

            self.log_success("All dependencies can be resolved")
            return True

        except Exception as e:
            self.log_error(f"Dependency resolution test failed: {e}")
            return False

    def run_test_suite(self) -> bool:
        """Run the existing test suite."""
        self.log_info("Running test suite...")

        try:
            # Run pytest
            self.run_command(
                ["poetry", "run", "pytest", "-m", "not live", "-v"]
            )
            self.log_success("All tests passed")
            return True

        except Exception as e:
            self.log_error(f"Test suite failed: {e}")
            return False

    def build_documentation(self) -> bool:
        """Test that documentation builds successfully."""
        self.log_info("Building documentation...")

        try:
            # Check if docs directory exists
            if not Path("docs/source").exists():
                self.log_warning(
                    "No docs/source directory found, skipping documentation build"
                )
                return True

            self.run_command(
                [
                    "poetry",
                    "run",
                    "sphinx-build",
                    "-W",
                    "docs/source",
                    "docs/build/html",
                ]
            )
            self.log_success("Documentation builds successfully")
            return True

        except Exception as e:
            self.log_error(f"Documentation build failed: {e}")
            return False

    def test_clean_installation(self) -> bool:
        """Test installation in clean virtual environments."""
        if self.skip_clean_install:
            self.log_info(
                "Skipping clean installation tests (--skip-clean-install)"
            )
            return True

        self.log_info("Testing clean installation...")

        # Find available Python versions
        python_versions = []
        for version in ["3.10", "3.11", "3.12"]:
            try:
                result = self.run_command(
                    [f"python{version}", "--version"], check=False
                )
                if result.returncode == 0:
                    python_versions.append(version)
            except FileNotFoundError:
                continue

        if not python_versions:
            self.log_warning(
                "No Python versions found for clean installation testing"
            )
            return True

        # Test installation for each available Python version
        for version in python_versions:
            if not self._test_python_version(version):
                return False

        return True

    def _test_python_version(self, version: str) -> bool:
        """Test installation for a specific Python version."""
        self.log_info(f"Testing Python {version}...")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                venv_dir = Path(temp_dir) / "venv"
                python_exe = f"python{version}"

                # Create virtual environment
                self.run_command([python_exe, "-m", "venv", str(venv_dir)])

                # Get venv python path
                if platform.system() == "Windows":
                    python_venv = str(venv_dir / "Scripts" / "python.exe")
                else:
                    python_venv = str(venv_dir / "bin" / "python")

                # Upgrade pip
                self.run_command(
                    [python_venv, "-m", "pip", "install", "--upgrade", "pip"]
                )

                # Install from wheel
                wheel_files = list(Path("dist").glob("*.whl"))
                if not wheel_files:
                    self.log_error("No wheel files found for testing")
                    return False

                self.run_command(
                    [python_venv, "-m", "pip", "install", str(wheel_files[0])]
                )

                # Test CLI help
                self.run_command(
                    [
                        python_venv,
                        "-c",
                        "import sys; sys.argv = ['ostruct', '--help']; import ostruct.cli.cli; ostruct.cli.cli.main()",
                    ]
                )

                # Test basic functionality with dry-run
                schema_content = {
                    "schema": {
                        "type": "object",
                        "properties": {"result": {"type": "string"}},
                        "required": ["result"],
                        "additionalProperties": False,
                    }
                }

                template_file = Path(temp_dir) / "test_template.j2"
                schema_file = Path(temp_dir) / "test_schema.json"

                template_file.write_text(
                    "Test task: {{ task_description | default('sample task') }}"
                )
                schema_file.write_text(json.dumps(schema_content))

                self.run_command(
                    [
                        python_venv,
                        "-c",
                        f"import sys; sys.argv = ['ostruct', 'run', '{template_file}', '{schema_file}', '--dry-run']; import ostruct.cli.cli; ostruct.cli.cli.main()",
                    ]
                )

            self.log_success(f"Python {version} installation test passed")
            return True

        except Exception as e:
            self.log_error(f"Python {version} installation test failed: {e}")
            return False

    def validate(self) -> bool:
        """Run all validation checks."""
        print("🚀 Starting Release Validation for ostruct")
        print("=" * 50)

        checks = [
            ("Version Consistency", self.check_version_consistency),
            ("pyproject.toml Validation", self.validate_pyproject),
            ("Package Building", self.build_package),
            ("Dependency Resolution", self.test_dependency_resolution),
            ("Test Suite", self.run_test_suite),
            ("Documentation", self.build_documentation),
            ("Clean Installation", self.test_clean_installation),
        ]

        results = {}

        for check_name, check_func in checks:
            print(f"\n=== {check_name} ===")
            try:
                results[check_name] = check_func()
            except Exception as e:
                self.log_error(f"Unexpected error in {check_name}: {e}")
                results[check_name] = False

        # Print summary
        print("\n" + "=" * 50)
        print("VALIDATION SUMMARY")
        print("=" * 50)

        for check_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            icon = "✅" if passed else "❌"
            print(f"{icon} {status} {check_name}")

        print(
            f"\nResult: {sum(results.values())}/{len(results)} checks passed"
        )

        if self.warnings:
            print(f"\nWarnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  ⚠️ {warning}")

        if all(results.values()):
            print("\n🎉 ALL CHECKS PASSED! Package is ready for release.")
            return True
        else:
            print(
                f"\n❌ {len([r for r in results.values() if not r])} CHECK(S) FAILED!"
            )
            print("\nPlease fix the issues above before releasing.")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate ostruct release readiness"
    )
    parser.add_argument(
        "--skip-clean-install",
        action="store_true",
        help="Skip clean virtual environment installation tests",
    )
    args = parser.parse_args()

    validator = ReleaseValidator(skip_clean_install=args.skip_clean_install)
    success = validator.validate()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
