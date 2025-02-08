"""Test configuration and fixtures.

Test File Structure Rules:
-------------------------
1. Base Directory:
   - All tests use /test_workspace/base as their base directory
   - The security_manager fixture enforces this
   - Most test files should be created within this directory
   - These directories are automatically created by setup_test_fs:
     - /test_workspace/
     - /test_workspace/base/
     - /test_workspace/allowed/

2. File Creation:
   - Use fs.create_file("/test_workspace/base/...") for test files
   - Always change to base directory: os.chdir("/test_workspace/base")
   - Only create files outside base when testing security boundaries

3. Directory Structure:
   - /test_workspace/base: Main test directory (secure)
   - /test_workspace/allowed: Explicitly allowed directory
   - /test_workspace/outside: Used for testing security boundaries
   - /tmp: Temporary directory (allowed)

4. Security Testing:
   - Use ../outside/... paths to test directory traversal
   - Use absolute paths when testing explicit security boundaries
   - Security errors should be caught and verified
"""

import errno
import json
import os
import tempfile
from pathlib import Path
from typing import IO, Any, Dict, Generator, List, Optional, Set, Union

import pytest
from dotenv import load_dotenv
from openai import OpenAI
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.errors import PathSecurityError
from ostruct.cli.security import SecurityManager

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
    config.addinivalue_line(
        "markers",
        "error_test: mark test as one that expects an error to be raised"
    )

    # Register the custom marker with pytest
    config.addinivalue_line(
        "markers",
        "error_test: mark test functions that are designed to verify error conditions",
    )


@pytest.fixture
def requires_openai() -> None:
    """Skip tests that require OpenAI API access if no valid API key is found."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "test-key":
        pytest.skip("OpenAI API key not found or is test key")


@pytest.fixture(autouse=True)
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


@pytest.fixture
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


@pytest.fixture
def mock_openai_client() -> OpenAI:
    """Create a mock OpenAI client for testing."""
    return OpenAI(api_key="test-key", base_url="http://localhost:8000")


@pytest.fixture
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


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(autouse=True, scope="function")
def setup_test_fs(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Set up test filesystem and patch temp directory.

    This fixture:
    1. Creates common test directories only when needed by fixtures
    2. Patches the system temp directory to use a controlled location

    Note: These directories are created automatically only when needed:
    - /test_workspace/
    - /test_workspace/base/
    - /test_workspace/allowed/
    - /tmp/test/

    Tests that need to test directory creation/missing directories
    should NOT use the security_manager fixture.
    """
    # Only create directories if the test uses fixtures that need them
    needs_dirs = any(
        name in request.fixturenames
        for name in ["security_manager", "cli_runner"]
    )

    if needs_dirs:
        test_dirs = [
            "/test_workspace",
            "/test_workspace/base",
            "/test_workspace/allowed",
        ]

        # Create directories only if needed by fixtures
        for dir_path in test_dirs:
            try:
                fs.create_dir(dir_path)
            except FileExistsError:
                # Ignore if directory already exists
                pass

    # Always create the test temp directory and its subdirectories
    test_temp_dir = "/tmp/test"
    fs.create_dir(test_temp_dir)
    
    # Create pytest-specific temp directories
    pytest_temp = f"{test_temp_dir}/pytest-of-yaniv"
    fs.create_dir(pytest_temp)
    
    # Patch tempfile to use our test directory
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(test_temp_dir))
    
    # Also patch tempfile.tempdir to handle direct access
    monkeypatch.setattr(tempfile, "tempdir", str(test_temp_dir))


@pytest.fixture
def mock_temp_dir(monkeypatch: pytest.MonkeyPatch, fs: FakeFilesystem) -> str:
    """Mock the system temp directory."""
    test_temp_dir = "/tmp/test"
    if not fs.exists(test_temp_dir):
        fs.create_dir(test_temp_dir)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(test_temp_dir))
    return test_temp_dir


def clean_path_str(path_str: str) -> str:
    """Clean pyfakefs metadata while preserving symlink information."""
    # Handle symlink notation (path->target)
    if "->" in path_str:
        link_path, target_path = path_str.split("->")
        return f"{_clean_single_path(link_path)}->{_clean_single_path(target_path)}"
    return _clean_single_path(path_str)


def _clean_single_path(p: str) -> str:
    """Clean a single path component of metadata."""
    if "'/" in p:
        parts = p.split("'/")
        return "/" + parts[-1].strip()
    return p.strip()


class SymlinkResolutionTracker:
    """Track symlink resolution to detect loops."""

    def __init__(self, max_depth: int = 40):
        self.seen_paths: Dict[str, int] = {}  # path -> depth first seen
        self.resolution_chain: List[str] = []
        self.max_depth = max_depth
        self.resolved_targets: Set[str] = (
            set()
        )  # Successfully resolved final targets

    def add_path(self, path: str, is_final: bool = False) -> None:
        """Track path resolution with enhanced loop detection."""
        clean_path = clean_path_str(str(path))
        current_depth = len(self.resolution_chain)

        # If we've seen this path before
        if clean_path in self.seen_paths:
            # If it's a final target we've resolved before, it's not a loop
            if clean_path in self.resolved_targets:
                return

            # Find the loop
            loop_start = self.resolution_chain.index(clean_path)
            loop = self.resolution_chain[loop_start:] + [clean_path]

            raise PathSecurityError(
                "Symlink loop detected",
                path=path,
                context={
                    "reason": "symlink_loop",
                    "loop_chain": loop,
                    "resolution_depth": current_depth,
                    "loop_start_depth": self.seen_paths[clean_path],
                },
                error_logged=True,
            )

        # Check max depth
        if current_depth >= self.max_depth:
            raise PathSecurityError(
                "Maximum symlink resolution depth exceeded",
                path=path,
                context={
                    "reason": "max_depth_exceeded",
                    "max_depth": self.max_depth,
                    "resolution_chain": self.resolution_chain,
                },
                error_logged=True,
            )

        # Track the path
        self.seen_paths[clean_path] = current_depth
        self.resolution_chain.append(clean_path)

        # If this is a final target, record it
        if is_final:
            self.resolved_targets.add(clean_path)


class MockSecurityManager(SecurityManager):
    """Mock security manager for testing.

    This class provides a mock implementation of the SecurityManager
    that works with the fake filesystem and enforces security checks
    in a test environment.
    """

    def __init__(self, base_dir: str = "/test_workspace") -> None:
        """Initialize mock security manager.

        Args:
            base_dir: Base directory for path resolution
        """
        super().__init__(base_dir)
        self._symlink_tracker = SymlinkResolutionTracker()
        self._patch_file_operations()

    def _patch_file_operations(self) -> None:
        """Patch file operations to enforce security checks."""
        import builtins
        from functools import wraps
        from typing import Callable, Optional, TypeVar, Union, cast

        T = TypeVar("T", bound=IO[Any])
        OpenFunc = Callable[..., T]
        original_open: OpenFunc = builtins.open

        @wraps(original_open)
        def secure_open(
            file: Union[str, Path],
            mode: str = "r",
            buffering: int = -1,
            encoding: Optional[str] = None,
            errors: Optional[str] = None,
            newline: Optional[str] = None,
            closefd: bool = True,
            opener: Optional[Callable[[str, int], int]] = None,
            *args: Any,
            **kwargs: Any,
        ) -> IO[Any]:
            try:
                # First resolve relative paths against cwd
                p = Path(file)
                if not p.is_absolute():
                    p = Path.cwd() / p

                # Now resolve and validate path using our security checks
                resolved = self.resolve_path(p)
                result = original_open(
                    resolved,
                    mode=mode,
                    buffering=buffering,
                    encoding=encoding,
                    errors=errors,
                    newline=newline,
                    closefd=closefd,
                    opener=opener,
                    *args,
                    **kwargs,
                )
                # Check if result has required file interface methods instead of strict IO inheritance
                if not hasattr(result, "read") or not hasattr(result, "close"):
                    raise TypeError("Expected file-like object from open")
                return cast(
                    IO[Any], result
                )  # Cast the result to IO[Any] since we verified it has the required methods
            except PathSecurityError:
                # Re-raise security errors as is
                raise
            except OSError as e:
                if e.errno == errno.ELOOP:
                    # Symlink loops are a security issue
                    raise PathSecurityError(
                        "Symlink loop detected",
                        path=str(file),
                        context={"reason": "symlink_loop", "error": str(e)},
                        error_logged=True,
                    )
                elif e.errno == errno.ENOENT:
                    # File not found should use simplified message
                    raise FileNotFoundError(
                        f"File not found: {os.path.basename(str(file))}"
                    )
                # Other OS errors should be raised as is
                raise

        builtins.open = secure_open  # type: ignore[assignment]

    def resolve_path(
        self, path: Union[str, Path], strict: bool = False
    ) -> Path:
        """Resolve and validate a path.

        Args:
            path: Path to resolve
            strict: Whether to require the path to exist

        Returns:
            Resolved Path object

        Raises:
            PathSecurityError: If path is not allowed
        """
        # Convert to Path object
        p = Path(path)

        # If path is not absolute, resolve it against current directory
        if not p.is_absolute():
            p = Path.cwd() / p

        # Normalize the path to handle .. components
        p = p.resolve()

        # Now validate using base class implementation and convert result back to Path
        return Path(super().resolve_path(str(p)))

    def _resolve_with_tracking(self, path: Path) -> Path:
        """Resolve a path with symlink loop detection."""
        try:
            clean_path = clean_path_str(str(path))
            if path.is_symlink():
                # Add to tracker as symlink
                self._symlink_tracker.add_path(clean_path)

                # Read and resolve the target
                target = path.readlink()
                if not target.is_absolute():
                    target = path.parent / target
                return self._resolve_with_tracking(target)
            else:
                # Add to tracker as final target
                self._symlink_tracker.add_path(clean_path, is_final=True)
                return path

        except OSError as e:
            if e.errno == errno.ELOOP:
                raise PathSecurityError(
                    "Symlink loop detected",
                    path=str(path),
                    context={"reason": "symlink_loop", "error": str(e)},
                    error_logged=True,
                )
            raise PathSecurityError(
                f"Error resolving symlink: {e}",
                path=str(path),
                context={"reason": "symlink_error"},
                error_logged=True,
            )


@pytest.fixture
def security_manager(fs: FakeFilesystem) -> SecurityManager:
    """Create a security manager for testing."""
    # Create test workspace structure if it doesn't exist
    workspace = "/test_workspace"
    base_dir = (
        "/test_workspace/base"  # This is the actual base directory for tests
    )
    allowed_dir = (
        "/test_workspace/allowed"  # This is an explicitly allowed directory
    )

    # Create required directories
    for d in [workspace, base_dir, allowed_dir]:
        try:
            fs.create_dir(d)
        except FileExistsError:
            pass

    # Create a temp directory
    temp_dir = "/tmp"
    try:
        fs.create_dir(temp_dir)
    except FileExistsError:
        pass

    # Use our test-specific security manager with the base directory
    manager = MockSecurityManager(base_dir=base_dir)

    # Add allowed directories
    manager.add_allowed_directory(
        allowed_dir
    )  # Only allow the explicitly allowed directory
    manager.add_allowed_directory(temp_dir)  # And the temp directory

    # Change to the base directory by default
    os.chdir(base_dir)

    return manager


@pytest.fixture(autouse=True)
def mock_model_support(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock model support check to allow any model in tests."""

    def mock_supports_structured_output(model: str) -> bool:
        return True

    monkeypatch.setattr(
        "openai_structured.client.supports_structured_output",
        mock_supports_structured_output,
    )


@pytest.fixture(autouse=True)
def mock_api_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock OpenAI API client for tests."""

    class MockResponse:
        def __iter__(self) -> Generator[dict[str, Any], None, None]:
            yield {"choices": [{"delta": {"content": "test"}}]}

    class MockClient:
        async def chat_completions_create(
            self, *args: Any, **kwargs: Any
        ) -> MockResponse:
            return MockResponse()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("openai.AsyncOpenAI", lambda **kwargs: MockClient())


@pytest.fixture(autouse=True)
def patch_security_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch SecurityManager to use /test_workspace as default base directory in tests."""
    from ostruct.cli.security import SecurityManager

    original_init = SecurityManager.__init__

    def patched_init(
        self: SecurityManager,
        base_dir: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Patch the SecurityManager init to use a fixed base directory."""
        if base_dir is None:
            base_dir = "/test_workspace"
        original_init(self, base_dir, *args, **kwargs)

    monkeypatch.setattr(SecurityManager, "__init__", patched_init)


def pytest_runtest_call(item: pytest.Item) -> None:
    """Modify test execution behavior."""
    marker = item.get_closest_marker("error_test")
    if marker:
        # Store that this is an error test for use in reporting
        item.user_properties.append(("is_error_test", True))


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """Modify test reports for error_test marked tests."""
    if "error_test" in item.keywords:
        if call.excinfo is not None:
            # Check if the error was expected (caught by pytest.raises)
            if call.excinfo.type == pytest.fail.Exception:
                return
            # Mark the test as passed if it raised an expected exception
            if call.when == "call":
                call.excinfo = None


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Customize the terminal summary for error tests."""
    error_tests = []
    for report in terminalreporter.getreports(''):
        if hasattr(report, 'when') and report.when == 'call':
            if hasattr(report, 'keywords') and 'error_test' in report.keywords:
                error_tests.append(report)
    
    if error_tests:
        terminalreporter.write_sep("=", "Error Test Summary")
        terminalreporter.write_line(
            "The following tests PASSED by raising expected errors:"
        )
        for report in error_tests:
            terminalreporter.write_line(f"  {report.nodeid}")
