"""
Test suite for ostruct examples.

This module automatically discovers and tests all examples in the /examples directory
following the EXAMPLES_STANDARD.md specification.

Test Modes:
- test_example_dry_run: Fast validation with --test-dry-run (no API calls)
- test_example_live: Live API testing with --test-live (marked as @pytest.mark.live)
"""

import subprocess
from pathlib import Path
from typing import List

import pytest


def find_example_scripts() -> List[Path]:
    """
    Discover all run.sh scripts in the examples directory.

    Returns:
        List of Path objects pointing to run.sh scripts
    """
    examples_dir = Path(__file__).parent.parent / "examples"
    if not examples_dir.exists():
        return []

    scripts = []
    for script_path in examples_dir.rglob("run.sh"):
        if (
            script_path.is_file() and script_path.stat().st_mode & 0o111
        ):  # executable
            scripts.append(script_path)

    return sorted(scripts)


def script_id_func(script_path: Path) -> str:
    """
    Generate test ID from script path.

    Args:
        script_path: Path to the run.sh script

    Returns:
        Human-readable test ID (e.g., "tools/code-interpreter-basics")
    """
    examples_dir = Path(__file__).parent.parent / "examples"
    relative_path = script_path.parent.relative_to(examples_dir)
    return str(relative_path)


def is_debugging_example(script_path: Path) -> bool:
    """
    Check if this is a debugging/troubleshooting example that intentionally contains broken code.

    Args:
        script_path: Path to the run.sh script

    Returns:
        True if this is a debugging example
    """
    script_id = script_id_func(script_path)
    return script_id.startswith("debugging/")


# Discover all example scripts
RUN_SCRIPTS = find_example_scripts()


@pytest.mark.no_fs
@pytest.mark.parametrize("script", RUN_SCRIPTS, ids=script_id_func)
def test_example_dry_run(script: Path) -> None:
    """
    Test example dry-run validation (no API calls).

    This test validates:
    - Template syntax and schema compliance
    - File processing and routing
    - Configuration validation
    - Input validation
    - Token counting and cost estimation

    Does NOT test:
    - Live OpenAI API calls
    - API authentication
    - Actual structured output generation

    Note: Debugging examples are handled specially since they intentionally contain broken code.

    Args:
        script: Path to the example's run.sh script
    """
    script_name = script_id_func(script)
    print(f"\n🧪 Testing dry-run validation for {script_name}")

    # Change to the script's directory
    script_dir = script.parent

    # Run the dry-run test
    proc = subprocess.run(
        ["bash", str(script), "--test-dry-run"],
        cwd=script_dir,
        capture_output=True,
        text=True,
        timeout=60,  # 1 minute timeout for dry-run tests
    )

    # Special handling for debugging examples
    if is_debugging_example(script):
        # Debugging examples are expected to show both failures and successes
        # We just check that the script itself runs without crashing
        if proc.returncode not in [
            0,
            1,
        ]:  # Allow exit code 1 for expected failures
            print(
                f"❌ Debugging example test failed unexpectedly for {script_name}"
            )
            print(f"STDOUT:\n{proc.stdout}")
            print(f"STDERR:\n{proc.stderr}")
            pytest.fail(
                f"Debugging example test failed unexpectedly for {script_name}\n"
                f"Exit code: {proc.returncode} (expected 0 or 1)\n"
                f"STDERR: {proc.stderr}\n"
                f"STDOUT: {proc.stdout}"
            )
        print(f"✅ Debugging example validation completed for {script_name}")
    else:
        # Regular examples should pass completely
        if proc.returncode != 0:
            print(f"❌ Dry-run test failed for {script_name}")
            print(f"STDOUT:\n{proc.stdout}")
            print(f"STDERR:\n{proc.stderr}")
            pytest.fail(
                f"Dry-run test failed for {script_name}\n"
                f"Exit code: {proc.returncode}\n"
                f"STDERR: {proc.stderr}\n"
                f"STDOUT: {proc.stdout}"
            )
        print(f"✅ Dry-run validation passed for {script_name}")


@pytest.mark.no_fs
@pytest.mark.live
@pytest.mark.parametrize("script", RUN_SCRIPTS, ids=script_id_func)
def test_example_live(script: Path) -> None:
    """
    Test example with live API calls.

    This test validates:
    - Live OpenAI API connectivity
    - API authentication (API key validation)
    - Model availability and compatibility
    - Actual structured output generation
    - API error handling
    - Rate limiting behavior

    Note: This test makes real API calls and incurs costs.
    It is marked with @pytest.mark.live and skipped by default.

    Note: Debugging examples are handled specially since they intentionally contain broken code.

    Args:
        script: Path to the example's run.sh script
    """
    script_name = script_id_func(script)
    print(f"\n🌐 Testing live API call for {script_name}")

    # Change to the script's directory
    script_dir = script.parent

    # Run the live test
    proc = subprocess.run(
        ["bash", str(script), "--test-live"],
        cwd=script_dir,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout for live tests
    )

    # Special handling for debugging examples
    if is_debugging_example(script):
        # Debugging examples are expected to show both failures and successes
        # We just check that the script itself runs without crashing
        if proc.returncode not in [
            0,
            1,
        ]:  # Allow exit code 1 for expected failures
            print(
                f"❌ Debugging example live test failed unexpectedly for {script_name}"
            )
            print(f"STDOUT:\n{proc.stdout}")
            print(f"STDERR:\n{proc.stderr}")
            pytest.fail(
                f"Debugging example live test failed unexpectedly for {script_name}\n"
                f"Exit code: {proc.returncode} (expected 0 or 1)\n"
                f"STDERR: {proc.stderr}\n"
                f"STDOUT: {proc.stdout}"
            )
        print(f"✅ Debugging example live test completed for {script_name}")
    else:
        # Regular examples should pass completely
        if proc.returncode != 0:
            print(f"❌ Live test failed for {script_name}")
            print(f"STDOUT:\n{proc.stdout}")
            print(f"STDERR:\n{proc.stderr}")
            pytest.fail(
                f"Live test failed for {script_name}\n"
                f"Exit code: {proc.returncode}\n"
                f"STDERR: {proc.stderr}\n"
                f"STDOUT: {proc.stdout}"
            )
        print(f"✅ Live API test passed for {script_name}")


@pytest.mark.no_fs
def test_examples_discovery() -> None:
    """
    Test that we can discover example scripts.

    This is a sanity check to ensure the discovery mechanism works
    and that we have examples to test.
    """
    scripts = find_example_scripts()

    # We should have at least some examples
    assert len(scripts) > 0, "No example scripts found in /examples directory"

    # All discovered scripts should be executable
    for script in scripts:
        assert script.exists(), f"Script does not exist: {script}"
        assert script.is_file(), f"Script is not a file: {script}"
        assert (
            script.stat().st_mode & 0o111
        ), f"Script is not executable: {script}"

    print(f"✅ Discovered {len(scripts)} example scripts")
    for script in scripts:
        script_name = script_id_func(script)
        if is_debugging_example(script):
            print(f"  - {script_name} (debugging example)")
        else:
            print(f"  - {script_name}")


@pytest.mark.no_fs
def test_examples_follow_standard() -> None:
    """
    Test that examples follow the EXAMPLES_STANDARD.md structure.

    This validates:
    - Required files exist (README.md, templates/, schemas/)
    - run.sh follows the standard interface
    - Special handling for debugging examples
    """
    scripts = find_example_scripts()

    for script in scripts:
        example_dir = script.parent
        script_name = script_id_func(script)

        # Check required files/directories exist
        required_paths = [
            example_dir / "README.md",
            example_dir / "templates",
            example_dir / "schemas",
        ]

        for required_path in required_paths:
            assert (
                required_path.exists()
            ), f"Example {script_name} missing required path: {required_path.name}"

        # Check run.sh uses standard_runner.sh
        script_content = script.read_text()
        assert (
            "standard_runner.sh" in script_content
        ), f"Example {script_name} does not use standard_runner.sh"

        # Check run.sh defines run_example function
        assert (
            "run_example()" in script_content
        ), f"Example {script_name} does not define run_example() function"

        # Special validation for debugging vs regular examples
        if is_debugging_example(script):
            # Debugging examples have intentionally broken templates
            # Just check that schemas directory exists and has at least one schema
            schemas_dir = example_dir / "schemas"
            schema_files = list(schemas_dir.glob("*.json"))
            assert (
                len(schema_files) > 0
            ), f"Debugging example {script_name} has no schema files"
            print(f"✅ Debugging example {script_name} structure validated")
        else:
            # Regular examples should have main.j2 and main.json
            templates_dir = example_dir / "templates"
            main_template = templates_dir / "main.j2"
            assert (
                main_template.exists()
            ), f"Example {script_name} missing main template: templates/main.j2"

            schemas_dir = example_dir / "schemas"
            main_schema = schemas_dir / "main.json"
            assert (
                main_schema.exists()
            ), f"Example {script_name} missing main schema: schemas/main.json"

    print(f"✅ All {len(scripts)} examples follow the standard structure")


if __name__ == "__main__":
    # Allow running this module directly for debugging
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--discover":
        # Just show discovered examples
        scripts = find_example_scripts()
        print(f"Discovered {len(scripts)} example scripts:")
        for script in scripts:
            script_name = script_id_func(script)
            if is_debugging_example(script):
                print(f"  - {script_name} (debugging example)")
            else:
                print(f"  - {script_name}")
    else:
        # Run basic discovery test
        test_examples_discovery()
        test_examples_follow_standard()
        print("✅ All discovery and structure tests passed")
