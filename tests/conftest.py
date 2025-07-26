"""Global pytest configuration and hooks.

Ensures that the parent directory used by pytest's tmpdir / tmp_path fixtures
exists on all operating systems.  macOS sometimes sets TMPDIR to a per-user
path like ``/var/folders/.../T/`` and pytest appends ``test`` – if that
sub-directory is missing the tmp fixture crashes before a test even begins.

Creating it once here guarantees robustness without touching individual tests.
"""

import errno
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Union

import pytest
import tiktoken
from _pytest.config import Config
from _pytest.terminal import TerminalReporter
from dotenv import load_dotenv
from ostruct.cli.base_errors import OstructFileNotFoundError
from ostruct.cli.errors import PathSecurityError
from ostruct.cli.security import SecurityManager
from pyfakefs.fake_filesystem import FakeFilesystem

# Create <TMPDIR>/test if missing (idempotent, works on all OSes)
for base in {os.getenv("TMPDIR"), tempfile.gettempdir()}:
    if base:
        try:
            Path(base).joinpath("test").mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Non-critical – fall back to pytest's normal behaviour
            pass

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
        "error_test: mark test as one that expects an error to be raised",
    )
    config.addinivalue_line(
        "markers",
        "no_fs: mark test to not use pyfakefs",
    )
    config.addinivalue_line(
        "markers",
        "mock_openai: mark test to use mock OpenAI client",
    )

    # Register the custom marker with pytest
    config.addinivalue_line(
        "markers",
        "error_test: mark test functions that are designed to verify error conditions",
    )


def pytest_collection_modifyitems(items):
    """Automatically mark tests using tmp_path with no_fs to prevent conflicts.

    Tests that use pytest's real tmp_path fixture are incompatible with our
    autouse setup_test_fs fixture that enables pyfakefs. This hook automatically
    adds the no_fs marker to any test that uses tmp_path to prevent the
    FileNotFoundError issues that occur when pyfakefs patches tempfile.gettempdir()
    while pytest tries to create real temporary directories.
    """
    for item in items:
        if "tmp_path" in item.fixturenames:
            item.add_marker("no_fs")


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
    # Set up model registry config paths FIRST before anything else
    try:
        import openai_model_registry

        registry_path = Path(openai_model_registry.__file__).parent
        config_dir = registry_path / "config"

        if config_dir.exists():
            models_yml = config_dir / "models.yml"
            constraints_yml = config_dir / "parameter_constraints.yml"

            if models_yml.exists():
                monkeypatch.setenv("MODEL_REGISTRY_PATH", str(models_yml))
            if constraints_yml.exists():
                monkeypatch.setenv(
                    "PARAMETER_CONSTRAINTS_PATH", str(constraints_yml)
                )
    except Exception:
        pass

    # Always try to load .env file first to get real API key
    load_dotenv()

    # Check if we have a real API key
    real_api_key = os.environ.get("OPENAI_API_KEY")
    has_real_key = (
        real_api_key
        and not real_api_key.startswith("test-")
        and len(real_api_key) > 10
    )

    if "live" in request.keywords:
        # Live tests require a real API key
        if not has_real_key:
            pytest.skip("No valid OpenAI API key found for live test")
    elif "requires_openai" in request.keywords:
        # Don't set test key for these tests - use real key if available
        if not has_real_key:
            pytest.skip("OpenAI API key required but not found")
    else:
        # For CLI execution tests, use real API key if available, otherwise use test key
        if not has_real_key:
            monkeypatch.setenv("OPENAI_API_KEY", "test-key")


@pytest.fixture
def fs(
    fs: FakeFilesystem, request: pytest.FixtureRequest
) -> Generator[FakeFilesystem, None, None]:
    """Create a fake filesystem for testing.

    This fixture is automatically used by tests that have an fs parameter.
    It provides a clean filesystem for each test, preventing interference
    between tests.

    Args:
        fs: The pyfakefs fixture
        request: The pytest request object

    Returns:
        The pyfakefs FakeFilesystem object
    """
    # Skip if test is marked with no_fs
    marker = request.node.get_closest_marker("no_fs")
    if marker is not None:
        pytest.skip("Test marked with no_fs")

    # pyfakefs already sets up common system paths
    # We can add any additional setup here if needed in the future
    yield fs


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
    base_dir = "/test_workspace/test_files"
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
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Set up test filesystem and patch temp directory.

    This fixture:
    1. Creates common test directories only when needed by fixtures
    2. Patches the system temp directory to use a controlled location
    3. Adds model registry files to the fake filesystem

    Note: These directories are created automatically only when needed:
    - /test_workspace/
    - /test_workspace/base/
    - /test_workspace/allowed/
    - /tmp/test/

    Tests that need to test directory creation/missing directories
    should NOT use the security_manager fixture.

    Note on tiktoken:
    ---------------
    We previously attempted to add tiktoken's directory to the fake filesystem,
    but this didn't work because tiktoken uses C/Rust bindings that bypass
    pyfakefs's file system mocking. Instead, we now pause pyfakefs during
    tiktoken operations. See tests/test_tokens.py for more details.
    """
    # Skip if test is marked with no_fs
    marker = request.node.get_closest_marker("no_fs")
    if marker is not None:
        return

    # Get the fs fixture only if we need it
    fs = request.getfixturevalue("fs")

    # Model registry configuration is handled in env_setup fixture
    # No additional setup needed here

    # Only create directories if the test uses fixtures that need them
    needs_dirs = any(
        name in request.fixturenames
        for name in [
            "security_manager",
            "strict_security_manager",
            "cli_runner",
        ]
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

    def __init__(self, base_dir: str = "/test_workspace/base") -> None:
        """Initialize mock security manager.

        Args:
            base_dir: Base directory for path resolution
        """
        super().__init__(base_dir)
        # Add parent directory as an allowed directory for testing
        parent_dir = os.path.dirname(base_dir)
        if parent_dir:
            self.add_allowed_directory(parent_dir)
        self._symlink_tracker = SymlinkResolutionTracker()
        self._patch_file_operations()

    def _patch_file_operations(self) -> None:
        """Patch file operations to enforce security checks."""
        import builtins
        from functools import wraps
        from typing import IO, Any, Callable, Optional, TypeVar, Union, cast

        T = TypeVar("T", bound=IO[Any])
        # Use type alias syntax that works with mypy
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
            # If `file` is a low-level fd (int) or some non-pathlike object (e.g. when
            # subprocess pipes are created), delegate directly to the real open().
            if not isinstance(file, (str, Path, bytes, os.PathLike)):
                # If it's an integer file descriptor, use os.fdopen to bypass pyfakefs.
                if isinstance(file, int):
                    import io

                    # Use a raw FileIO object to avoid pyfakefs tracking; wrap in TextIOWrapper for text mode.
                    raw = io.FileIO(file, mode="r" if "r" in mode else "w")
                    if "b" in mode:
                        return raw  # type: ignore[return-value]
                    return io.TextIOWrapper(
                        raw, encoding=encoding or "utf-8", newline=newline
                    )
                # For any other non-pathlike, fall back to original open (safe).
                return original_open(
                    file,  # type: ignore[arg-type]
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
                    # File not found should use OstructFileNotFoundError
                    raise OstructFileNotFoundError(str(file))
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
    """Create a security manager for testing using global context pattern.

    Args:
        fs: The pyfakefs fixture

    Returns:
        A SecurityManager instance configured for testing
    """
    from ostruct.cli.security.context import (
        get_current_security_manager,
        reset_security_context,
        set_current_security_manager,
    )

    # Reset context to ensure clean state
    reset_security_context()

    # Create and configure the security manager
    mock_sm = MockSecurityManager()

    # Set it as the global context
    set_current_security_manager(mock_sm)

    # Return the global instance
    return get_current_security_manager()


@pytest.fixture
def strict_security_manager(fs: FakeFilesystem) -> SecurityManager:
    """Create a security manager for testing with STRICT mode using global context pattern.

    Args:
        fs: The pyfakefs fixture

    Returns:
        A SecurityManager instance configured for testing with STRICT security mode
    """
    from ostruct.cli.security.context import (
        get_current_security_manager,
        reset_security_context,
        set_current_security_manager,
    )
    from ostruct.cli.security.types import PathSecurity

    # Reset context to ensure clean state
    reset_security_context()

    # Create and configure the security manager
    mock_sm = MockSecurityManager()
    mock_sm.security_mode = PathSecurity.STRICT

    # Set it as the global context
    set_current_security_manager(mock_sm)

    # Return the global instance
    return get_current_security_manager()


@pytest.fixture(autouse=True)
def setup_global_security_context(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Generator[None, None, None]:
    """Set up global security context for tests and ensure clean teardown.

    This fixture ensures that the global security context is properly reset
    between tests and that the deprecation warning is not triggered during
    legitimate test operations.

    Args:
        monkeypatch: The pytest monkeypatch fixture
        request: The pytest request fixture
    """
    from ostruct.cli.security.context import reset_security_context

    # Reset context before each test
    reset_security_context()

    # Yield to run the test
    yield

    # Reset context after each test to ensure clean state
    reset_security_context()


@pytest.fixture(autouse=True)
def patch_security_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the SecurityManager class to use the mock version.

    This fixture is now simplified since we're using the global context pattern.
    It only patches the SecurityManager constructor to use test-friendly defaults
    when SecurityManager is instantiated directly (which should be rare).

    Args:
        monkeypatch: The pytest monkeypatch fixture
    """
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
            base_dir = "/test_workspace/base"

        # Temporarily suppress the deprecation warning during tests
        # since tests legitimately create SecurityManager instances for mocking
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            original_init(self, base_dir, *args, **kwargs)

    monkeypatch.setattr(SecurityManager, "__init__", patched_init)


def pytest_runtest_call(item: pytest.Item) -> None:
    """Modify test execution behavior."""
    marker = item.get_closest_marker("error_test")
    if marker:
        # Store that this is an error test for use in reporting
        item.user_properties.append(("is_error_test", True))


def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo
) -> None:
    """Modify test reports for error_test marked tests."""
    if "error_test" in item.keywords:
        if call.excinfo is not None:
            # Check if the error was expected (caught by pytest.raises)
            if call.excinfo.type == pytest.fail.Exception:
                return
            # Mark the test as passed if it raised an expected exception
            if call.when == "call":
                call.excinfo = None


def pytest_terminal_summary(
    terminalreporter: TerminalReporter, exitstatus: int, config: Config
) -> None:
    """Customize the terminal summary for error tests."""
    error_tests = []
    for report in terminalreporter.getreports(""):
        if hasattr(report, "when") and report.when == "call":
            if hasattr(report, "keywords") and "error_test" in report.keywords:
                error_tests.append(report)

    if error_tests:
        terminalreporter.write_sep("=", "Error Test Summary")
        terminalreporter.write_line(
            "The following tests PASSED by raising expected errors:"
        )
        for report in error_tests:
            terminalreporter.write_line(f"  {report.nodeid}")


class MockResponsesAPI:
    """Mock for OpenAI Responses API."""

    async def create(self, **kwargs):
        """Mock the responses.create method."""

        # Return an async iterator that yields mock response chunks
        async def mock_stream():
            yield {
                "choices": [
                    {"delta": {"content": '{"result": "Mock response"}'}}
                ]
            }

        return mock_stream()


class MockClient:
    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        # Accept any API key for testing
        self.api_key = api_key or "test-key"
        self.responses = MockResponsesAPI()

    async def chat_completions_create(self, **kwargs):
        """Simple mock that returns a basic response."""
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"result": "Mock response"}',
                        "role": "assistant",
                    }
                }
            ]
        }

    async def close(self) -> None:
        """Close the client."""
        pass


@pytest.fixture(autouse=True)
def mock_model_support(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock OpenAI API client for testing."""
    monkeypatch.setattr("openai.AsyncOpenAI", MockClient)
    monkeypatch.setattr("openai.OpenAI", MockClient)


class DummyEncoder:
    def encode(self, text: str) -> list[int]:
        # Simple approximation: each character is a token
        # This is not accurate but sufficient for testing
        return [1] * len(str(text))


@pytest.fixture(autouse=True)
def mock_tiktoken(monkeypatch):
    """Mock tiktoken to avoid filesystem/network access."""

    def mock_get_encoding(name: str) -> DummyEncoder:
        return DummyEncoder()

    monkeypatch.setattr(tiktoken, "get_encoding", mock_get_encoding)


@pytest.fixture(autouse=True)
def mock_model_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the ModelRegistry to provide consistent test data."""
    from openai_model_registry import ModelRegistry  # noqa: F401
    from openai_model_registry.registry import ModelCapabilities  # noqa: F401

    class MockModelRegistry:
        _instance: Optional["MockModelRegistry"] = None

        def __init__(self):
            self._capabilities = {
                "gpt-4o": self._create_mock_capabilities(
                    "gpt-4o", 128000, 16384
                ),
                "gpt-4o-mini": self._create_mock_capabilities(
                    "gpt-4o-mini", 128000, 16384
                ),
                "o1": self._create_mock_capabilities("o1", 200000, 100000),
                "o3-mini": self._create_mock_capabilities(
                    "o3-mini", 200000, 65536
                ),
                "gpt-4o-2024-05-13": self._create_mock_capabilities(
                    "gpt-4o-2024-05-13", 128000, 16384
                ),
            }

        @property
        def models(self):
            """Return list of available model names."""
            return list(self._capabilities.keys())

        @property
        def config(self):
            """Return mock config object with registry_path."""

            class MockConfig:
                registry_path = "/test/mock/registry/path/models.yml"

            return MockConfig()

        def _create_mock_capabilities(
            self, model_name: str, context_window: int, max_output_tokens: int
        ) -> Any:
            """Create a mock ModelCapabilities object."""

            class MockCapabilities:
                def __init__(
                    self,
                    model_name: str,
                    context_window: int,
                    max_output_tokens: int,
                ):
                    self.model_name = model_name
                    self.openai_model_name = model_name
                    self.context_window = context_window
                    self.max_output_tokens = max_output_tokens
                    self.supports_structured = True
                    self.supports_structured_output = True
                    self.supports_streaming = True
                    self.supports_vision = False
                    self.supports_functions = True
                    self.supported_parameters = [
                        "temperature",
                        "max_output_tokens",
                        "top_p",
                        "frequency_penalty",
                        "presence_penalty",
                    ]

                def validate_parameter(
                    self, param_name: str, value: Any
                ) -> None:
                    """Mock parameter validation."""
                    pass

            return MockCapabilities(
                model_name, context_window, max_output_tokens
            )

        def get_capabilities(self, model: str) -> Any:
            """Get model capabilities."""
            if model in self._capabilities:
                return self._capabilities[model]
            # For unknown models, raise the same error as the real registry
            from openai_model_registry.errors import ModelNotSupportedError

            raise ModelNotSupportedError(
                f"Model '{model}' not found. Available base models: {', '.join(sorted(self._capabilities.keys()))}",
                model=model,
                available_models=list(self._capabilities.keys()),
            )

        def check_for_updates(self) -> Any:
            """Mock check for updates method."""
            # Import the real types to match the API
            try:
                from openai_model_registry.registry import (
                    RefreshResult,
                    RefreshStatus,
                )

                # Return a successful "already current" result by default
                return RefreshResult(
                    success=True,
                    status=RefreshStatus.ALREADY_CURRENT,
                    message="Registry is up to date",
                )
            except ImportError:
                # Fallback if the real types aren't available
                class MockStatus:
                    def __init__(self, value: str):
                        self.value = value

                class MockResult:
                    def __init__(
                        self, status: str, message: str, success: bool = True
                    ):
                        self.status = MockStatus(status)
                        self.message = message
                        self.success = success

                return MockResult(
                    status="already_current",
                    message="Registry is up to date",
                    success=True,
                )

        @classmethod
        def get_instance(cls):
            """Get singleton instance."""
            if not hasattr(cls, "_instance"):
                cls._instance = cls()
            return cls._instance

    # Replace the ModelRegistry class with our mock
    # Patch the original module
    monkeypatch.setattr(
        "openai_model_registry.ModelRegistry", MockModelRegistry
    )

    # Patch all the local references where ModelRegistry is imported with 'from'
    # These are the actual module paths, not the command objects
    try:
        monkeypatch.setattr(
            "ostruct.cli.registry_updates.ModelRegistry", MockModelRegistry
        )
    except AttributeError:
        pass  # Module might not be imported yet

    try:
        monkeypatch.setattr(
            "ostruct.cli.cost_estimation.ModelRegistry", MockModelRegistry
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "ostruct.cli.commands.list_models.ModelRegistry", MockModelRegistry
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "ostruct.cli.commands.update_registry.ModelRegistry",
            MockModelRegistry,
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "ostruct.cli.schema_utils.ModelRegistry", MockModelRegistry
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "ostruct.cli.runner.ModelRegistry", MockModelRegistry
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "ostruct.cli.model_validation.ModelRegistry", MockModelRegistry
        )
    except AttributeError:
        pass

    # Patch the direct import used in help_json.py
    try:
        monkeypatch.setattr(
            "openai_model_registry.ModelRegistry", MockModelRegistry
        )
    except AttributeError:
        pass
