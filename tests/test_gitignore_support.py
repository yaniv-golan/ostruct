"""Tests for gitignore support functionality."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from ostruct.cli.gitignore_support import GitignoreManager


class TestGitignoreManager:
    """Test GitignoreManager class functionality."""

    def test_basic_patterns(self) -> None:
        """Test basic gitignore pattern matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.pyc\n__pycache__/\n.env\n")

            manager = GitignoreManager(directory=tmpdir)

            assert manager.should_ignore("test.pyc")
            assert manager.should_ignore("__pycache__/test.py")
            assert manager.should_ignore(".env")
            assert not manager.should_ignore("test.py")
            assert manager.has_patterns
            assert manager.get_pattern_count() > 0

    def test_no_gitignore_file(self) -> None:
        """Test behavior when no gitignore file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GitignoreManager(directory=tmpdir)
            assert not manager.has_patterns
            assert not manager.should_ignore("any_file.txt")
            assert manager.get_pattern_count() == 0

    def test_custom_gitignore_path(self) -> None:
        """Test using custom gitignore file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_ignore = Path(tmpdir) / ".custom_ignore"
            custom_ignore.write_text("*.tmp\n")

            manager = GitignoreManager(gitignore_path=str(custom_ignore))
            assert manager.has_patterns
            assert manager.should_ignore("test.tmp")
            assert not manager.should_ignore("test.txt")

    def test_complex_patterns(self) -> None:
        """Test complex gitignore patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text(
                """
# Comments should be ignored
*.log
!important.log
temp/
/root_only.txt
**/nested.txt
"""
            )

            manager = GitignoreManager(directory=tmpdir)

            # Basic pattern
            assert manager.should_ignore("debug.log")
            # Negation pattern
            assert not manager.should_ignore("important.log")
            # Directory pattern
            assert manager.should_ignore("temp/file.txt")
            # Root-only pattern
            assert manager.should_ignore("root_only.txt")
            assert not manager.should_ignore("subdir/root_only.txt")
            # Nested pattern
            assert manager.should_ignore("any/path/nested.txt")

    def test_invalid_gitignore_file(self) -> None:
        """Test handling of invalid gitignore files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test non-existent custom file
            manager = GitignoreManager(gitignore_path="/non/existent/file")
            assert not manager.has_patterns
            assert not manager.should_ignore("any_file.txt")

            # Test permission denied (simulate by creating directory instead of file)
            invalid_path = Path(tmpdir) / "invalid"
            invalid_path.mkdir()

            with patch(
                "builtins.open",
                side_effect=PermissionError("Permission denied"),
            ):
                manager = GitignoreManager(gitignore_path=str(invalid_path))
                assert not manager.has_patterns

    def test_unicode_filenames(self) -> None:
        """Test with Unicode filenames and patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.测试\n🎉*.txt\n")

            manager = GitignoreManager(directory=tmpdir)

            assert manager.should_ignore("file.测试")
            assert manager.should_ignore("🎉celebration.txt")
            assert not manager.should_ignore("normal.txt")

    def test_encoding_errors(self) -> None:
        """Test handling of files with invalid encoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            # Write binary data that's not valid UTF-8
            gitignore.write_bytes(b"\xff\xfe*.pyc\n")

            manager = GitignoreManager(directory=tmpdir)
            # Should handle encoding error gracefully
            assert not manager.has_patterns

    def test_empty_gitignore(self) -> None:
        """Test with empty gitignore file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("")

            manager = GitignoreManager(directory=tmpdir)
            # Empty file should still be considered as having patterns loaded
            assert manager.has_patterns
            assert not manager.should_ignore("any_file.txt")

    def test_gitignore_with_only_comments(self) -> None:
        """Test gitignore file with only comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("# This is a comment\n# Another comment\n")

            manager = GitignoreManager(directory=tmpdir)
            assert manager.has_patterns
            assert not manager.should_ignore("any_file.txt")

    def test_path_normalization(self) -> None:
        """Test that paths are normalized correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.pyc\n")

            manager = GitignoreManager(directory=tmpdir)

            # Test various path formats
            assert manager.should_ignore("file.pyc")
            assert manager.should_ignore("./file.pyc")
            assert manager.should_ignore("subdir/file.pyc")
            assert manager.should_ignore("./subdir/file.pyc")

    def test_performance_large_patterns(self) -> None:
        """Test performance with many gitignore patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"

            # Create 100 patterns
            patterns = [f"*.{i:03d}" for i in range(100)]
            gitignore.write_text("\n".join(patterns))

            manager = GitignoreManager(directory=tmpdir)

            start = time.time()
            # Test 1000 file checks
            for i in range(1000):
                manager.should_ignore(f"file_{i % 50}.{i % 100:03d}")
            duration = time.time() - start

            # Should process 1000 files in under 0.1 seconds
            assert duration < 0.1

    def test_performance_large_directory(self) -> None:
        """Test performance with large number of files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.pyc\n__pycache__/\n*.log\n")

            manager = GitignoreManager(directory=tmpdir)

            start = time.time()
            # Test checking 1000 different files
            for i in range(1000):
                manager.should_ignore(f"file_{i}.py")
                manager.should_ignore(f"file_{i}.pyc")
                manager.should_ignore(f"__pycache__/file_{i}.py")
            duration = time.time() - start

            # Should process 3000 file checks in under 0.1 seconds
            assert duration < 0.1

    def test_concurrent_access(self) -> None:
        """Test thread safety and concurrent access."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.pyc\n*.log\n")

            manager = GitignoreManager(directory=tmpdir)
            results = []
            errors = []

            def worker(worker_id: int) -> None:
                try:
                    for i in range(100):
                        result = manager.should_ignore(
                            f"worker_{worker_id}_file_{i}.pyc"
                        )
                        results.append(result)
                except Exception as e:
                    errors.append(e)

            # Create 5 threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Should have no errors and all results should be True (*.pyc matches)
            assert not errors
            assert len(results) == 500
            assert all(results)

    def test_directory_parameter_precedence(self) -> None:
        """Test that custom gitignore_path takes precedence over directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .gitignore in directory
            dir_gitignore = Path(tmpdir) / ".gitignore"
            dir_gitignore.write_text("*.dir\n")

            # Create custom gitignore file
            custom_gitignore = Path(tmpdir) / ".custom"
            custom_gitignore.write_text("*.custom\n")

            manager = GitignoreManager(
                gitignore_path=str(custom_gitignore), directory=tmpdir
            )

            # Should use custom file, not directory file
            assert manager.should_ignore("test.custom")
            assert not manager.should_ignore("test.dir")

    def test_relative_vs_absolute_paths(self) -> None:
        """Test behavior with relative vs absolute gitignore paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.test\n")

            # Test with absolute path
            manager_abs = GitignoreManager(
                gitignore_path=str(gitignore.absolute())
            )
            assert manager_abs.has_patterns
            assert manager_abs.should_ignore("file.test")

            # Change to the temp directory and test with relative path
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                manager_rel = GitignoreManager(gitignore_path=".gitignore")
                assert manager_rel.has_patterns
                assert manager_rel.should_ignore("file.test")
            finally:
                os.chdir(original_cwd)

    def test_logging_behavior(self) -> None:
        """Test that logging works correctly."""

        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.log\n")

            # Mock the logger
            with patch("ostruct.cli.gitignore_support.logger") as mock_logger:
                manager = GitignoreManager(directory=tmpdir)

                # Test debug logging for pattern loading
                mock_logger.debug.assert_called()

                # Test debug logging for file matching
                manager.should_ignore("test.log")
                mock_logger.debug.assert_called_with(
                    "File ignored by gitignore: %s", "test.log"
                )

    def test_edge_case_patterns(self) -> None:
        """Test edge case gitignore patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text(
                """
# Test various edge cases
*
!*.py
!*.md
**/*
!README.md
"""
            )

            manager = GitignoreManager(directory=tmpdir)

            # Pattern order matters: '**/*' overrides earlier negations
            # Only README.md is not ignored because its negation comes after **/*
            assert manager.should_ignore("file.txt")
            assert manager.should_ignore("file.js")
            assert manager.should_ignore(
                "file.py"
            )  # Ignored due to **/* pattern
            assert manager.should_ignore(
                "file.md"
            )  # Ignored due to **/* pattern
            assert not manager.should_ignore(
                "README.md"
            )  # Not ignored due to final negation


class TestGitignoreManagerIntegration:
    """Integration tests for GitignoreManager with file system operations."""

    def test_real_gitignore_patterns(self) -> None:
        """Test with real-world gitignore patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text(
                """
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""
            )

            manager = GitignoreManager(directory=tmpdir)

            # Test Python patterns
            assert manager.should_ignore("__pycache__/module.py")
            assert manager.should_ignore("file.pyc")
            assert manager.should_ignore("file.pyo")
            assert manager.should_ignore("file.pyd")

            # Test build patterns
            assert manager.should_ignore("build/output.js")
            assert manager.should_ignore("dist/package.tar.gz")
            assert manager.should_ignore("*.egg-info/PKG-INFO")

            # Test environment patterns
            assert manager.should_ignore(".env")
            assert manager.should_ignore("venv/bin/python")

            # Test IDE patterns
            assert manager.should_ignore(".vscode/settings.json")
            assert manager.should_ignore(".idea/workspace.xml")

            # Test OS patterns
            assert manager.should_ignore(".DS_Store")
            assert manager.should_ignore("Thumbs.db")

            # Test that normal Python files are not ignored
            assert not manager.should_ignore("main.py")
            assert not manager.should_ignore("src/module.py")
            assert not manager.should_ignore("tests/test_something.py")

    def test_nested_directory_patterns(self) -> None:
        """Test gitignore patterns with nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text(
                """
logs/
temp/
**/node_modules/
**/target/
src/**/generated/
"""
            )

            manager = GitignoreManager(directory=tmpdir)

            # Test directory patterns
            assert manager.should_ignore("logs/app.log")
            assert manager.should_ignore("temp/cache.tmp")

            # Test wildcard directory patterns
            assert manager.should_ignore("node_modules/package/index.js")
            assert manager.should_ignore("frontend/node_modules/lib/util.js")
            assert manager.should_ignore("backend/target/classes/Main.class")

            # Test specific nested patterns
            assert manager.should_ignore("src/main/generated/Parser.java")
            assert manager.should_ignore("src/test/generated/Lexer.java")
            assert not manager.should_ignore("src/main/java/Main.java")
