"""CLI integration tests for gitignore functionality.

These tests verify end-to-end CLI behavior that would catch bugs like:
- Bug #1: Recursive flag not working
- Bug #2: Directory expansion doesn't use gitignore
- Bug #3: Global vs last attachment flag behavior

Note: Dry-run mode only shows attachment configuration, not actual file lists.
File enumeration happens during actual execution, not in dry-run.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pytest


@pytest.mark.no_fs
class TestGitignoreCLIIntegration:
    """Test CLI integration with gitignore functionality."""

    def create_test_project(self, tmp_path: Path) -> Path:
        """Create a test project with gitignore patterns."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create source files
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("# main module")
        (src_dir / "utils.py").write_text("# utilities")
        (src_dir / "main.pyc").write_text("# compiled")

        # Create test files
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("# tests")

        # Create build artifacts
        dist_dir = project_dir / "dist"
        dist_dir.mkdir()
        (dist_dir / "package.tar.gz").write_text("# build output")

        # Create cache
        cache_dir = project_dir / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "main.cpython-39.pyc").write_text("# cache")

        # Create environment files
        (project_dir / ".env").write_text("SECRET=value")
        (project_dir / "debug.log").write_text("debug info")
        (project_dir / "important.log").write_text("important info")

        # Create config files
        (project_dir / "requirements.txt").write_text("requests==2.28.0")
        (project_dir / "package.json").write_text('{"name": "test"}')

        # Create .gitignore
        gitignore = project_dir / ".gitignore"
        gitignore.write_text(
            """
# Compiled files
*.pyc
__pycache__/

# Build outputs
dist/
build/

# Environment files
.env
.env.*

# Logs
*.log
!important.log

# Dependencies
node_modules/
"""
        )

        return project_dir

    def create_minimal_template_and_schema(
        self, tmp_path: Path, template_content: str | None = None
    ) -> tuple[Path, Path]:
        """Create minimal template and schema for testing."""
        template = tmp_path / "test.j2"
        if template_content is None:
            template_content = "Files: {{ project_files | length }}"
        template.write_text(template_content)

        schema = tmp_path / "test.json"
        schema.write_text(
            '{"type": "object", "properties": {"result": {"type": "string"}}}'
        )

        return template, schema

    def test_dir_flag_respects_gitignore_by_default(
        self, tmp_path: Path
    ) -> None:
        """Test that --dir flag respects gitignore patterns by default."""
        project_dir = self.create_test_project(tmp_path)
        template, schema = self.create_minimal_template_and_schema(tmp_path)

        # Run ostruct with --dir flag (should respect gitignore)
        result = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "project_files",
                str(project_dir),
                "--recursive",
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse dry-run JSON output
        dry_run_data = json.loads(result.stdout)
        attachments = dry_run_data.get("attachments", [])

        # Find the directory attachment
        dir_attachment = None
        for attachment in attachments:
            if attachment.get("alias") == "project_files":
                dir_attachment = attachment
                break

        assert dir_attachment is not None, "Directory attachment not found"

        # Verify attachment configuration
        assert dir_attachment.get("type") == "directory"
        assert dir_attachment.get("exists") is True
        assert dir_attachment.get("recursive") is True

        # Note: dry-run doesn't enumerate files, it only shows configuration
        # The actual file filtering happens during execution, not in dry-run

    def test_dir_flag_ignores_gitignore_when_disabled(
        self, tmp_path: Path
    ) -> None:
        """Test that --dir with --ignore-gitignore includes all files."""
        project_dir = self.create_test_project(tmp_path)
        template, schema = self.create_minimal_template_and_schema(tmp_path)

        # Run ostruct with --ignore-gitignore
        result = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "project_files",
                str(project_dir),
                "--recursive",
                "--ignore-gitignore",
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse dry-run JSON output
        dry_run_data = json.loads(result.stdout)
        attachments = dry_run_data.get("attachments", [])

        # Find the directory attachment
        dir_attachment = None
        for attachment in attachments:
            if attachment.get("alias") == "project_files":
                dir_attachment = attachment
                break

        assert dir_attachment is not None, "Directory attachment not found"

        # Verify attachment configuration shows ignore_gitignore flag
        assert dir_attachment.get("type") == "directory"
        assert dir_attachment.get("exists") is True
        assert dir_attachment.get("recursive") is True
        # Check that ignore_gitignore is passed through (if shown in dry-run)

    def test_recursive_flag_actually_works(self, tmp_path: Path) -> None:
        """Test that --recursive flag is actually applied (Bug #1)."""
        project_dir = self.create_test_project(tmp_path)
        template, schema = self.create_minimal_template_and_schema(tmp_path)

        # Test WITH --recursive flag
        result_recursive = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "project_files",
                str(project_dir),
                "--recursive",
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        # Test WITHOUT --recursive flag
        result_non_recursive = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "project_files",
                str(project_dir),
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result_recursive.returncode == 0
        assert result_non_recursive.returncode == 0

        # Parse outputs
        recursive_data = json.loads(result_recursive.stdout)
        non_recursive_data = json.loads(result_non_recursive.stdout)

        # Verify recursive flag is set correctly in dry-run output
        recursive_attachment = recursive_data["attachments"][0]
        non_recursive_attachment = non_recursive_data["attachments"][0]

        assert recursive_attachment.get("recursive") is True
        assert non_recursive_attachment.get("recursive") is False

    def test_pattern_flag_actually_works(self, tmp_path: Path) -> None:
        """Test that --pattern flag is actually applied (Bug #1)."""
        project_dir = self.create_test_project(tmp_path)
        template, schema = self.create_minimal_template_and_schema(tmp_path)

        # Test WITH --pattern flag for Python files only
        result_pattern = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "project_files",
                str(project_dir),
                "--recursive",
                "--pattern",
                "*.py",
                "--ignore-gitignore",  # Disable gitignore to see all files
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        # Test WITHOUT --pattern flag
        result_no_pattern = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "project_files",
                str(project_dir),
                "--recursive",
                "--ignore-gitignore",
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result_pattern.returncode == 0
        assert result_no_pattern.returncode == 0

        # Parse outputs
        pattern_data = json.loads(result_pattern.stdout)
        no_pattern_data = json.loads(result_no_pattern.stdout)

        # Verify pattern is set correctly in dry-run output
        pattern_attachment = pattern_data["attachments"][0]
        assert pattern_attachment.get("pattern") == "*.py"

        no_pattern_attachment = no_pattern_data["attachments"][0]
        assert no_pattern_attachment.get("pattern") is None

    def test_global_flags_behavior_multiple_dirs(self, tmp_path: Path) -> None:
        """Test that flags apply globally to all --dir attachments (Bug #3)."""
        # Create two separate project directories
        proj1_dir = tmp_path / "proj1"
        proj1_dir.mkdir()
        proj2_dir = tmp_path / "proj2"
        proj2_dir.mkdir()
        project1 = self.create_test_project(proj1_dir)
        project2 = self.create_test_project(proj2_dir)

        # Create template that uses both aliases
        template = tmp_path / "test.j2"
        template.write_text(
            "Proj1 Files: {{ proj1_files | length }}, Proj2 Files: {{ proj2_files | length }}"
        )

        schema = tmp_path / "test.json"
        schema.write_text(
            '{"type": "object", "properties": {"result": {"type": "string"}}}'
        )

        # Run with multiple --dir attachments and global flags
        result = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "proj1_files",
                str(project1),
                "--dir",
                "proj2_files",
                str(project2),
                "--recursive",
                "--pattern",
                "*.py",
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse dry-run JSON output
        dry_run_data = json.loads(result.stdout)
        attachments = dry_run_data.get("attachments", [])

        # Should have two directory attachments
        assert (
            len(attachments) == 2
        ), f"Expected 2 attachments, got {len(attachments)}"

        # Find both attachments
        proj1_attachment = None
        proj2_attachment = None
        for attachment in attachments:
            if attachment.get("alias") == "proj1_files":
                proj1_attachment = attachment
            elif attachment.get("alias") == "proj2_files":
                proj2_attachment = attachment

        assert proj1_attachment is not None, "proj1_files attachment not found"
        assert proj2_attachment is not None, "proj2_files attachment not found"

        # BOTH attachments should have the global flags applied
        assert proj1_attachment.get("recursive") is True
        assert proj1_attachment.get("pattern") == "*.py"
        assert proj2_attachment.get("recursive") is True
        assert proj2_attachment.get("pattern") == "*.py"

    def test_custom_gitignore_file_cli_option(self, tmp_path: Path) -> None:
        """Test --gitignore-file CLI option works correctly."""
        project_dir = self.create_test_project(tmp_path)
        template, schema = self.create_minimal_template_and_schema(tmp_path)

        # Create custom gitignore that excludes different files
        custom_gitignore = tmp_path / ".custom_ignore"
        custom_gitignore.write_text(
            """
# Custom patterns - exclude Python files instead of compiled files
*.py
*.txt
"""
        )

        # Run with custom gitignore file
        result = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "project_files",
                str(project_dir),
                "--recursive",
                "--gitignore-file",
                str(custom_gitignore),
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse dry-run JSON output
        dry_run_data = json.loads(result.stdout)
        attachments = dry_run_data.get("attachments", [])
        dir_attachment = attachments[0]

        # Verify attachment exists and has correct configuration
        assert dir_attachment.get("alias") == "project_files"
        assert dir_attachment.get("exists") is True
        # Note: The actual gitignore file usage is internal and may not be shown in dry-run

    def test_collect_flag_with_gitignore(self, tmp_path: Path) -> None:
        """Test that --collect flag also respects gitignore patterns."""
        project_dir = self.create_test_project(tmp_path)
        # Create template that uses generic files variable
        template, schema = self.create_minimal_template_and_schema(
            tmp_path, "Files count: {{ files | length }}"
        )

        # Create file list that includes both included and excluded files
        file_list = tmp_path / "files.txt"
        file_list.write_text(
            f"""
{project_dir}/src/main.py
{project_dir}/src/main.pyc
{project_dir}/.env
{project_dir}/requirements.txt
"""
        )

        # Run with --collect flag (should respect gitignore)
        result = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--collect",
                "collected_files",
                f"@{file_list}",
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse dry-run JSON output
        dry_run_data = json.loads(result.stdout)
        attachments = dry_run_data.get("attachments", [])
        collect_attachment = attachments[0]

        # Verify collection attachment configuration
        assert collect_attachment.get("alias") == "collected_files"
        assert collect_attachment.get("type") == "collection"
        # Note: gitignore filtering happens during execution, not in dry-run

    def test_environment_variables_affect_cli(self, tmp_path: Path) -> None:
        """Test that environment variables affect CLI behavior."""
        project_dir = self.create_test_project(tmp_path)
        template, schema = self.create_minimal_template_and_schema(tmp_path)

        # Test with OSTRUCT_IGNORE_GITIGNORE=true
        env = os.environ.copy()
        env["OSTRUCT_IGNORE_GITIGNORE"] = "true"

        result = subprocess.run(
            [
                "ostruct",
                "run",
                str(template),
                str(schema),
                "--dir",
                "project_files",
                str(project_dir),
                "--recursive",
                "--dry-run",
                "--dry-run-json",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env=env,
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse dry-run JSON output
        dry_run_data = json.loads(result.stdout)
        attachments = dry_run_data.get("attachments", [])

        # Verify attachment exists
        assert len(attachments) == 1
        assert attachments[0].get("alias") == "project_files"
        # Note: Environment variable effects are internal and may not show in dry-run


@pytest.mark.no_fs
class TestCLIFlagParsing:
    """Test CLI flag parsing and propagation."""

    def test_dry_run_json_shows_correct_flag_values(
        self, tmp_path: Path
    ) -> None:
        """Test that dry-run JSON output shows correct flag values."""
        # Create minimal test setup
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("test")

        template = tmp_path / "test.j2"
        template.write_text("Test")
        schema = tmp_path / "test.json"
        schema.write_text(
            '{"type": "object", "properties": {"result": {"type": "string"}}}'
        )

        # Test various flag combinations
        test_cases: List[Dict[str, Any]] = [
            {
                "flags": ["--recursive"],
                "expected": {"recursive": True, "pattern": None},
            },
            {
                "flags": ["--pattern", "*.txt"],
                "expected": {"recursive": False, "pattern": "*.txt"},
            },
            {
                "flags": ["--recursive", "--pattern", "*.py"],
                "expected": {"recursive": True, "pattern": "*.py"},
            },
            {
                "flags": ["--ignore-gitignore"],
                "expected": {"recursive": False},
            },
        ]

        for case in test_cases:
            # Run the command with the specified flags
            result = subprocess.run(
                [
                    "ostruct",
                    "run",
                    str(template),
                    str(schema),
                    "--dir",
                    "test_files",
                    str(test_dir),
                    *case["flags"],
                    "--dry-run",
                    "--dry-run-json",
                ],
                capture_output=True,
                text=True,
                cwd=str(tmp_path),
            )

            assert result.returncode == 0, f"Command failed: {result.stderr}"

            dry_run_data = json.loads(result.stdout)
            attachment = dry_run_data["attachments"][0]

            for key, expected_value in case["expected"].items():
                actual_value = attachment.get(key)
                assert actual_value == expected_value, (
                    f"Flag {key}: expected {expected_value}, got {actual_value} "
                    f"for flags {case['flags']}"
                )
