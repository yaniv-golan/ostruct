"""Test configuration and fixtures."""

import json
import os
from typing import Dict, Generator

import pytest
from dotenv import load_dotenv
from openai import OpenAI
from pyfakefs.fake_filesystem import FakeFilesystem

pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line(
        "markers",
        "no_collect: mark class to not be collected by pytest",
    )
    config.addinivalue_line(
        "markers",
        "live: mark test as a live test that should use real API key",
    )


@pytest.fixture  # type: ignore[misc]
def requires_openai() -> None:
    """Skip tests that require OpenAI API access if no valid API key is found."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "test-key":
        pytest.skip("OpenAI API key not found or is test key")


@pytest.fixture(autouse=True)  # type: ignore[misc]
def env_setup(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Set up environment variables for testing."""
    # Load .env file for live tests
    if "live" in request.keywords:
        load_dotenv()
    # For tests that require OpenAI, ensure no test key is set
    elif "requires_openai" in request.keywords:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # For all other tests, set test key
    else:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")


@pytest.fixture  # type: ignore[misc]
def fs(fs: FakeFilesystem) -> Generator[FakeFilesystem, None, None]:
    """Create a fake filesystem for testing.

    This fixture is automatically used by tests that have an fs parameter.
    It provides a clean filesystem for each test, preventing interference
    between tests.

    Args:
        fs: The pyfakefs fixture

    Returns:
        The pyfakefs FakeFilesystem object
    """
    # pyfakefs already sets up common system paths
    # We can add any additional setup here if needed in the future
    yield fs


@pytest.fixture  # type: ignore[misc]
def mock_openai_client() -> OpenAI:
    """Create a mock OpenAI client for testing."""
    return OpenAI(api_key="test-key", base_url="http://localhost:8000")


@pytest.fixture  # type: ignore[misc]
def test_files(fs: FakeFilesystem) -> Dict[str, str]:
    """Create test files for testing.

    This fixture creates a set of test files in a temporary directory
    and returns their paths.

    Args:
        fs: The pyfakefs fixture

    Returns:
        A dictionary mapping file names to their paths
    """
    base_dir = "/Users/yaniv/Documents/code/openai-structured/tests/test_files"
    fs.create_dir(base_dir)

    # Create test files
    files = {
        "base_dir": base_dir,
        "input": f"{base_dir}/input.txt",
        "template": f"{base_dir}/template.txt",
        "template_no_prompt": f"{base_dir}/template_no_prompt.txt",
        "schema": f"{base_dir}/schema.json",
        "system_prompt": f"{base_dir}/system.txt",
    }

    # Create input file
    fs.create_file(files["input"], contents="Test input file")

    # Create template with YAML frontmatter
    fs.create_file(
        files["template"],
        contents=(
            "---\n"
            "system_prompt: You are a test assistant using YAML frontmatter.\n"
            "---\n"
            "Process input: {{ input }}"
        ),
    )

    # Create template without YAML frontmatter
    fs.create_file(
        files["template_no_prompt"], contents="Process input: {{ input }}"
    )

    # Create schema file
    schema_content = {
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "status": {"type": "string"},
        },
        "required": ["result", "status"],
    }
    fs.create_file(files["schema"], contents=json.dumps(schema_content))

    # Create system prompt file
    fs.create_file(
        files["system_prompt"],
        contents="You are a test assistant from a file.",
    )

    return files
