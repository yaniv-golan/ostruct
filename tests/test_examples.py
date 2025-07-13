"""
Test suite for ostruct examples.

This module automatically discovers and tests all examples in the /examples directory
following the Examples Standard (docs/source/contribute/examples_standard.rst).

Test Modes:
- test_example_dry_run: Fast validation with `make test-dry` (no API calls)
- test_example_live: Live API testing with `make test-live` (marked as @pytest.mark.live)
"""

import subprocess
from pathlib import Path
from typing import List

import pytest


def find_examples() -> List[Path]:
    """
    Discover all examples in the examples directory by finding Makefile files.

    Excludes the 'agent' example as it's not ready for release.

    Returns:
        List of Path objects pointing to example directories containing Makefiles
    """
    examples_dir = Path(__file__).parent.parent / "examples"
    if not examples_dir.exists():
        return []

    examples = []
    for makefile_path in examples_dir.rglob("Makefile"):
        if makefile_path.is_file():
            example_dir = makefile_path.parent
            # Skip the agent example - not ready for release
            if example_dir.name == "agent":
                continue
            examples.append(example_dir)

    return sorted(examples)


def example_id_func(example_path: Path) -> str:
    """
    Generate test ID from example path.

    Args:
        example_path: Path to the example directory

    Returns:
        Human-readable test ID (e.g., "tools/code-interpreter-basics")
    """
    examples_dir = Path(__file__).parent.parent / "examples"
    relative_path = example_path.relative_to(examples_dir)
    return str(relative_path)


def is_debugging_example(example_path: Path) -> bool:
    """
    Check if this is a debugging/troubleshooting example that intentionally contains broken code.

    Args:
        example_path: Path to the example directory

    Returns:
        True if this is a debugging example
    """
    example_id = example_id_func(example_path)
    return example_id.startswith("debugging/")


def check_makefile_targets(
    makefile_path: Path, required_targets: List[str]
) -> List[str]:
    """
    Check if a Makefile contains the required targets.

    Args:
        makefile_path: Path to the Makefile
        required_targets: List of target names to check for

    Returns:
        List of missing targets
    """
    try:
        content = makefile_path.read_text()
        missing_targets = []

        for target in required_targets:
            # Look for target definition (target: or target followed by whitespace)
            if f"{target}:" not in content and not any(
                line.strip().startswith(f"{target}\t")
                or line.strip().startswith(f"{target} ")
                for line in content.split("\n")
            ):
                missing_targets.append(target)

        return missing_targets
    except Exception:
        return required_targets  # If we can't read the file, assume all targets are missing


# Discover all examples
EXAMPLES = find_examples()


@pytest.mark.no_fs
@pytest.mark.parametrize("example", EXAMPLES, ids=example_id_func)
def test_example_dry_run(example: Path) -> None:
    """
    Test example dry-run validation using `make test-dry` (no API calls).

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
        example: Path to the example directory
    """
    example_name = example_id_func(example)
    print(f"\n🧪 Testing dry-run validation for {example_name}")

    # Check if this is a debugging example
    if is_debugging_example(example):
        print(
            f"⚠️  Skipping dry-run test for debugging example: {example_name}"
        )
        pytest.skip("Debugging examples intentionally contain broken code")

    # Run make test-dry
    try:
        result = subprocess.run(
            ["make", "test-dry"],
            cwd=example,
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute timeout for dry-run
        )

        if result.returncode != 0:
            print(f"❌ Dry-run failed for {example_name}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            pytest.fail(
                f"Example {example_name} dry-run failed with exit code {result.returncode}\n"
                f"STDERR: {result.stderr}\n"
                f"STDOUT: {result.stdout}"
            )
        else:
            print(f"✅ Dry-run validation passed for {example_name}")

    except subprocess.TimeoutExpired:
        pytest.fail(
            f"Example {example_name} dry-run timed out after 60 seconds"
        )
    except FileNotFoundError:
        pytest.fail(f"Example {example_name} missing make command or Makefile")


@pytest.mark.no_fs
@pytest.mark.live
@pytest.mark.parametrize("example", EXAMPLES, ids=example_id_func)
def test_example_live(example: Path) -> None:
    """
    Test example live validation using `make test-live` (minimal API calls).

    This test performs minimal live API testing to verify:
    - API connectivity and authentication
    - Basic template processing with live API
    - Structured output generation
    - Error handling for API issues

    Args:
        example: Path to the example directory
    """
    example_name = example_id_func(example)
    print(f"\n🔴 Testing live API for {example_name}")

    # Check if this is a debugging example
    if is_debugging_example(example):
        print(f"⚠️  Skipping live test for debugging example: {example_name}")
        pytest.skip("Debugging examples intentionally contain broken code")

    # Run make test-live
    try:
        result = subprocess.run(
            ["make", "test-live"],
            cwd=example,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout for live test
        )

        if result.returncode != 0:
            print(f"❌ Live test failed for {example_name}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")

            # Check for common API issues
            stderr_lower = result.stderr.lower()
            if "api" in stderr_lower and (
                "key" in stderr_lower or "auth" in stderr_lower
            ):
                pytest.skip(
                    f"API authentication issue for {example_name} - this is expected in CI"
                )
            elif "rate limit" in stderr_lower or "quota" in stderr_lower:
                pytest.skip(
                    f"API rate limit hit for {example_name} - this is expected under load"
                )
            else:
                pytest.fail(
                    f"Example {example_name} live test failed with exit code {result.returncode}\n"
                    f"STDERR: {result.stderr}\n"
                    f"STDOUT: {result.stdout}"
                )
        else:
            print(f"✅ Live test passed for {example_name}")

    except subprocess.TimeoutExpired:
        pytest.fail(
            f"Example {example_name} live test timed out after 120 seconds"
        )
    except FileNotFoundError:
        pytest.fail(f"Example {example_name} missing make command or Makefile")


@pytest.mark.no_fs
def test_examples_discovery() -> None:
    """
    Test that example discovery works correctly.

    This validates:
    - Examples directory exists
    - At least some examples are discovered
    - All discovered examples have valid Makefiles
    """
    examples = find_examples()

    # Should find at least some examples
    assert len(examples) > 0, "No examples discovered in /examples directory"

    # All discovered paths should be directories with Makefiles
    for example in examples:
        assert example.is_dir(), f"Example path is not a directory: {example}"
        makefile = example / "Makefile"
        assert makefile.exists(), f"Example missing Makefile: {example}"

    print(f"✅ Discovered {len(examples)} examples with Makefiles")


@pytest.mark.no_fs
def test_examples_follow_standard() -> None:
    """
    Test that examples follow the Examples Standard.

    This validates:
    - Required Makefile targets exist (test-dry, test-live, run, clean, help)
    - Makefiles are properly structured
    - Special handling for debugging examples
    """
    examples = find_examples()
    required_targets = ["test-dry", "test-live", "run", "clean", "help"]

    for example in examples:
        example_name = example_id_func(example)
        makefile = example / "Makefile"

        # Check required targets exist
        missing_targets = check_makefile_targets(makefile, required_targets)

        if missing_targets:
            pytest.fail(
                f"Example {example_name} missing required Makefile targets: {', '.join(missing_targets)}"
            )

        # Special validation for debugging vs regular examples
        if is_debugging_example(example):
            print(
                f"✅ Debugging example {example_name} Makefile structure validated"
            )
        else:
            # For regular examples, test that help target works
            try:
                result = subprocess.run(
                    ["make", "help"],
                    cwd=example,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    pytest.fail(
                        f"Example {example_name} 'make help' failed with exit code {result.returncode}"
                    )

                # Help output should mention the available targets
                help_output = result.stdout.lower()
                if not any(
                    target in help_output
                    for target in ["test-dry", "test-live", "run"]
                ):
                    pytest.fail(
                        f"Example {example_name} 'make help' output doesn't mention key targets"
                    )

            except subprocess.TimeoutExpired:
                pytest.fail(f"Example {example_name} 'make help' timed out")
            except FileNotFoundError:
                pytest.fail(f"Example {example_name} missing make command")

            print(f"✅ Example {example_name} Makefile structure validated")

    print(f"✅ All {len(examples)} examples follow the standard structure")


if __name__ == "__main__":
    # Allow running this module directly for debugging
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--discover":
        # Just show discovered examples
        examples = find_examples()
        print(f"Discovered {len(examples)} examples:")
        for example in examples:
            example_name = example_id_func(example)
            if is_debugging_example(example):
                print(f"  - {example_name} (debugging example)")
            else:
                print(f"  - {example_name}")
    else:
        # Run basic discovery test
        test_examples_discovery()
        test_examples_follow_standard()
        print("✅ All discovery and structure tests passed")
