"""Test progress reporting functionality."""

from io import StringIO
from unittest.mock import patch

from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.progress import ProgressContext


def test_stdout_output() -> None:
    """Test direct output to stdout."""
    with patch("sys.stdout", new=StringIO()) as fake_out:
        with ProgressContext() as progress:
            progress.print_output("test message")
        assert fake_out.getvalue() == "test message\n"


def test_file_output(fs: FakeFilesystem) -> None:
    """Test output to file."""
    with ProgressContext(output_file="test.txt") as progress:
        progress.print_output("test message")

    with open("test.txt", "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "test message\n"


def test_compatibility_methods() -> None:
    """Test that compatibility methods don't raise errors."""
    with ProgressContext() as progress:
        # These should be no-ops but shouldn't raise errors
        progress.update()
        with progress.step("test"):
            pass
