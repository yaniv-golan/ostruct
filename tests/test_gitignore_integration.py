"""Integration tests for gitignore functionality with ostruct file collection."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from ostruct.cli.config import FileCollectionConfig, OstructConfig
from ostruct.cli.file_utils import collect_files_from_directory
from ostruct.cli.security.security_manager import SecurityManager


class TestGitignoreFileCollection:
    """Test gitignore integration with file collection utilities."""

    def test_collect_files_with_gitignore_enabled(self) -> None:
        """Test file collection with gitignore enabled (default behavior)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "include.py").write_text("# include this file")
            (test_dir / "exclude.pyc").write_text("# exclude this file")
            (test_dir / "important.log").write_text("# important log")
            (test_dir / "debug.log").write_text("# debug log")

            # Create subdirectory with files
            subdir = test_dir / "subdir"
            subdir.mkdir()
            (subdir / "module.py").write_text("# python module")
            (subdir / "cache.pyc").write_text("# cached file")

            # Create .gitignore
            gitignore = test_dir / ".gitignore"
            gitignore.write_text("*.pyc\n*.log\n!important.log\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test with gitignore enabled (default)
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,  # Default behavior
            )

            file_names = [f.name for f in files]

            # Should include .py files and important.log (negation pattern)
            assert "include.py" in file_names
            assert "module.py" in file_names
            assert "important.log" in file_names

            # Should exclude .pyc files and other .log files
            assert "exclude.pyc" not in file_names
            assert "cache.pyc" not in file_names
            assert "debug.log" not in file_names

    def test_collect_files_with_gitignore_disabled(self) -> None:
        """Test file collection with gitignore disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "include.py").write_text("# include this file")
            (test_dir / "exclude.pyc").write_text("# exclude this file")
            (test_dir / "debug.log").write_text("# debug log")

            # Create .gitignore
            gitignore = test_dir / ".gitignore"
            gitignore.write_text("*.pyc\n*.log\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test with gitignore disabled
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=True,  # Disable gitignore
            )

            file_names = [f.name for f in files]

            # Should include all files when gitignore is disabled
            assert "include.py" in file_names
            assert "exclude.pyc" in file_names
            assert "debug.log" in file_names

    def test_collect_files_with_custom_gitignore_file(self) -> None:
        """Test file collection with custom gitignore file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "keep.py").write_text("# keep this file")
            (test_dir / "remove.tmp").write_text("# remove this file")
            (test_dir / "normal.txt").write_text("# normal file")

            # Create default .gitignore (should be ignored)
            default_gitignore = test_dir / ".gitignore"
            default_gitignore.write_text("*.py\n")

            # Create custom gitignore file
            custom_gitignore = test_dir / ".custom_ignore"
            custom_gitignore.write_text("*.tmp\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test with custom gitignore file
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,
                gitignore_file=str(custom_gitignore),
            )

            file_names = [f.name for f in files]

            # Should use custom gitignore (exclude .tmp, include .py)
            assert "keep.py" in file_names
            assert "normal.txt" in file_names
            assert "remove.tmp" not in file_names

    def test_collect_files_no_gitignore_file(self) -> None:
        """Test file collection when no gitignore file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files without .gitignore
            test_dir = Path(tmpdir)
            (test_dir / "file1.py").write_text("# file 1")
            (test_dir / "file2.pyc").write_text("# file 2")
            (test_dir / "file3.log").write_text("# file 3")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test without gitignore file
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,
            )

            file_names = [f.name for f in files]

            # Should include all files when no gitignore exists
            assert "file1.py" in file_names
            assert "file2.pyc" in file_names
            assert "file3.log" in file_names

    def test_collect_files_with_logging(self) -> None:
        """Test that appropriate logging messages are generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "keep.py").write_text("# keep")
            (test_dir / "exclude1.pyc").write_text("# exclude 1")
            (test_dir / "exclude2.pyc").write_text("# exclude 2")

            # Create .gitignore
            gitignore = test_dir / ".gitignore"
            gitignore.write_text("*.pyc\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Mock the logger to capture log messages
            with patch("ostruct.cli.file_utils.logger") as mock_logger:
                _ = collect_files_from_directory(
                    directory=str(test_dir),
                    security_manager=security_manager,
                    recursive=True,
                    ignore_gitignore=False,
                )

                # Verify logging calls
                mock_logger.info.assert_any_call(
                    "Applying .gitignore patterns from directory: %s",
                    str(test_dir),
                )
                mock_logger.info.assert_any_call(
                    "Excluded %d files based on .gitignore patterns", 2
                )
                mock_logger.info.assert_any_call(
                    "Use --ignore-gitignore to include ignored files"
                )

    def test_collect_files_performance_with_many_files(self) -> None:
        """Test performance with many files and gitignore patterns."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)

            # Create many files
            for i in range(100):
                (test_dir / f"file_{i}.py").write_text(f"# file {i}")
                (test_dir / f"file_{i}.pyc").write_text(f"# compiled {i}")
                (test_dir / f"file_{i}.log").write_text(f"# log {i}")

            # Create .gitignore with multiple patterns
            gitignore = test_dir / ".gitignore"
            gitignore.write_text("*.pyc\n*.log\n*.tmp\n*.bak\n*.cache\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            start = time.time()
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,
            )
            duration = time.time() - start

            # Should complete quickly (under 1 second for 300 files)
            assert duration < 1.0

            # Should only include .py files (and possibly .gitignore)
            py_files = [f for f in files if f.name.endswith(".py")]
            assert len(py_files) == 100

            # All non-.gitignore files should be .py files
            for file_info in files:
                assert (
                    file_info.name.endswith(".py")
                    or file_info.name == ".gitignore"
                )


class TestGitignoreConfiguration:
    """Test gitignore configuration support."""

    def test_file_collection_config_defaults(self) -> None:
        """Test FileCollectionConfig default values."""
        config = FileCollectionConfig()

        assert config.ignore_gitignore is False
        assert config.gitignore_file is None

    def test_file_collection_config_custom_values(self) -> None:
        """Test FileCollectionConfig with custom values."""
        config = FileCollectionConfig(
            ignore_gitignore=True, gitignore_file="/custom/path/.gitignore"
        )

        assert config.ignore_gitignore is True
        assert config.gitignore_file == "/custom/path/.gitignore"

    def test_gitignore_file_validation(self) -> None:
        """Test gitignore_file path validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_file = Path(tmpdir) / ".gitignore"
            valid_file.write_text("*.pyc\n")

            # Valid file should pass validation
            config = FileCollectionConfig(gitignore_file=str(valid_file))
            assert config.gitignore_file == str(valid_file)

            # Non-existent file should pass validation (warning only)
            config = FileCollectionConfig(gitignore_file="/non/existent/file")
            assert config.gitignore_file == "/non/existent/file"

    def test_environment_variable_integration(self) -> None:
        """Test environment variable integration."""
        with patch.dict(
            os.environ,
            {
                "OSTRUCT_IGNORE_GITIGNORE": "true",
                "OSTRUCT_GITIGNORE_FILE": "/custom/.gitignore",
            },
        ):
            # Environment variables should be applied
            config = OstructConfig._apply_env_overrides({})
            file_config = config.get("file_collection", {})

            assert file_config.get("ignore_gitignore") is True
            assert file_config.get("gitignore_file") == "/custom/.gitignore"

    def test_environment_variable_boolean_parsing(self) -> None:
        """Test boolean environment variable parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("invalid", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(
                os.environ, {"OSTRUCT_IGNORE_GITIGNORE": env_value}
            ):
                config = OstructConfig._apply_env_overrides({})
                file_config = config.get("file_collection", {})
                assert file_config.get("ignore_gitignore") is expected


class TestGitignoreCLIIntegration:
    """Test CLI integration with gitignore functionality."""

    def test_cli_parameters_passed_to_file_collection(self) -> None:
        """Test that CLI parameters are correctly passed to file collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "keep.py").write_text("# keep")
            (test_dir / "exclude.pyc").write_text("# exclude")

            # Create .gitignore
            gitignore = test_dir / ".gitignore"
            gitignore.write_text("*.pyc\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test that parameters are passed correctly
            files_with_gitignore = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,
                gitignore_file=None,
            )

            files_without_gitignore = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=True,
                gitignore_file=None,
            )

            # Results should be different
            with_names = [f.name for f in files_with_gitignore]
            without_names = [f.name for f in files_without_gitignore]

            # With gitignore: should include .py file but not .pyc
            assert "keep.py" in with_names
            assert "exclude.pyc" not in with_names

            # Without gitignore: should include all files
            assert "keep.py" in without_names
            assert "exclude.pyc" in without_names

            # Without gitignore should have more files than with gitignore
            assert len(files_without_gitignore) > len(files_with_gitignore)

    def test_custom_gitignore_file_parameter(self) -> None:
        """Test custom gitignore file parameter functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "file.py").write_text("# python")
            (test_dir / "file.js").write_text("# javascript")
            (test_dir / "file.tmp").write_text("# temporary")

            # Create custom gitignore
            custom_gitignore = test_dir / ".custom"
            custom_gitignore.write_text("*.js\n*.tmp\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test with custom gitignore file
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,
                gitignore_file=str(custom_gitignore),
            )

            file_names = [f.name for f in files]

            # Should only include .py file
            assert "file.py" in file_names
            assert "file.js" not in file_names
            assert "file.tmp" not in file_names

    def test_recursive_directory_collection(self) -> None:
        """Test gitignore with recursive directory collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            test_dir = Path(tmpdir)

            # Root level
            (test_dir / "root.py").write_text("# root")
            (test_dir / "root.pyc").write_text("# root compiled")

            # Subdirectory
            subdir = test_dir / "subdir"
            subdir.mkdir()
            (subdir / "sub.py").write_text("# sub")
            (subdir / "sub.pyc").write_text("# sub compiled")

            # Nested subdirectory
            nested = subdir / "nested"
            nested.mkdir()
            (nested / "nested.py").write_text("# nested")
            (nested / "nested.pyc").write_text("# nested compiled")

            # Create .gitignore in root
            gitignore = test_dir / ".gitignore"
            gitignore.write_text("*.pyc\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test recursive collection with gitignore
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,
            )

            file_names = [f.name for f in files]

            # Should include all .py files but no .pyc files
            assert "root.py" in file_names
            assert "sub.py" in file_names
            assert "nested.py" in file_names
            assert "root.pyc" not in file_names
            assert "sub.pyc" not in file_names
            assert "nested.pyc" not in file_names

    def test_error_handling_with_invalid_gitignore_file(self) -> None:
        """Test error handling when gitignore file is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "file.py").write_text("# test")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test with non-existent gitignore file
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,
                gitignore_file="/non/existent/file",
            )

            # Should still work and include all files
            assert len(files) == 1
            assert files[0].name == "file.py"

    def test_gitignore_with_allowed_extensions_filter(self) -> None:
        """Test gitignore interaction with allowed_extensions filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_dir = Path(tmpdir)
            (test_dir / "script.py").write_text("# python script")
            (test_dir / "script.pyc").write_text("# compiled python")
            (test_dir / "data.json").write_text("# json data")
            (test_dir / "readme.txt").write_text("# readme")

            # Create .gitignore
            gitignore = test_dir / ".gitignore"
            gitignore.write_text("*.pyc\n*.txt\n")

            security_manager = SecurityManager(base_dir=str(test_dir))

            # Test with both gitignore and allowed_extensions
            files = collect_files_from_directory(
                directory=str(test_dir),
                security_manager=security_manager,
                recursive=True,
                ignore_gitignore=False,
                allowed_extensions=["py", "json"],  # Extensions without dots
            )

            file_names = [f.name for f in files]

            # Should include .py and .json files, but exclude .pyc (gitignore) and .txt (gitignore)
            assert "script.py" in file_names
            assert "data.json" in file_names
            assert "script.pyc" not in file_names
            assert "readme.txt" not in file_names
