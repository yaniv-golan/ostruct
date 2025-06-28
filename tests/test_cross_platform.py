"""Cross-platform testing matrix for CLI v0.9.0 functionality.

This module implements T6.1: Cross-Platform Testing Matrix from the CLI tasks plan.
Tests the new attachment system, JSON output, security modes, and platform-specific behaviors.
"""

import json
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple

import pytest


class TestResult(NamedTuple):
    """Test result data structure."""

    name: str
    passed: bool
    details: Dict[str, Any]
    platform: str = platform.system().lower()


class CrossPlatformTester:
    """Cross-platform CLI testing framework for ostruct v0.9.0."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.current_platform = platform.system().lower()
        self.test_data_dir = Path(tempfile.mkdtemp(prefix="ostruct_test_"))
        self._setup_test_files()

    def _setup_test_files(self):
        """Create test files for cross-platform testing."""
        # Create basic test template
        (self.test_data_dir / "test_template.j2").write_text(
            "Analyze: {{ data.content if data is defined else 'No data' }}"
        )

        # Create basic schema
        schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string", "description": "Analysis result"}
            },
            "required": ["result"],
        }
        (self.test_data_dir / "test_schema.json").write_text(
            json.dumps(schema, indent=2)
        )

        # Create test data file
        (self.test_data_dir / "test_data.txt").write_text(
            "Sample test data for analysis"
        )

        # Create test directory with files
        test_dir = self.test_data_dir / "test_directory"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("Content of file 1")
        (test_dir / "file2.txt").write_text("Content of file 2")

        # Create file collection list
        (self.test_data_dir / "file_list.txt").write_text(
            str(self.test_data_dir / "test_data.txt") + "\n"
        )

    def _run_ostruct_command(
        self, args: List[str], cwd: Path = None
    ) -> subprocess.CompletedProcess:
        """Run ostruct command and capture output."""
        cmd = ["poetry", "run", "ostruct"] + args
        # Always run from project root to ensure poetry works correctly
        project_root = Path(__file__).parent.parent
        return subprocess.run(
            cmd, cwd=project_root, capture_output=True, text=True, timeout=30
        )

    def _get_test_args(self, *additional_args):
        """Get standard test arguments with absolute paths."""
        base_args = [
            "run",
            str(self.test_data_dir / "test_template.j2"),
            str(self.test_data_dir / "test_schema.json"),
        ]
        return base_args + list(additional_args)

    def test_basic_attachment(self) -> TestResult:
        """Test basic file attachment functionality."""
        test_results = {}

        try:
            # Test basic file attachment with prompt target (default)
            result = self._run_ostruct_command(
                self._get_test_args(
                    "--file",
                    "data",
                    str(self.test_data_dir / "test_data.txt"),
                    "--dry-run",
                )
            )

            test_results["basic_attachment_exit"] = result.returncode == 0
            test_results["basic_attachment_output"] = len(result.stdout) > 0
            test_results["contains_attachment_info"] = (
                "data" in result.stdout.lower()
            )

            # Test explicit target specification
            result = self._run_ostruct_command(
                self._get_test_args(
                    "--file",
                    "ci:analysis",
                    str(self.test_data_dir / "test_data.txt"),
                    "--dry-run",
                )
            )

            test_results["explicit_target_exit"] = result.returncode == 0
            test_results["explicit_target_contains_ci"] = (
                "code-interpreter" in result.stdout.lower()
            )

            return TestResult(
                name="basic_attachment",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="basic_attachment",
                passed=False,
                details={"error": str(e)},
            )

    def test_multi_tool_routing(self) -> TestResult:
        """Test multi-tool attachment routing."""
        test_results = {}

        try:
            # Test multi-tool attachment (ci,fs:shared)
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--file",
                    "ci,fs:shared",
                    "test_data.txt",
                    "--dry-run",
                ]
            )

            test_results["multi_tool_exit"] = result.returncode == 0
            test_results["contains_code_interpreter"] = (
                "code-interpreter" in result.stdout.lower()
            )
            test_results["contains_file_search"] = (
                "file-search" in result.stdout.lower()
            )

            # Test directory attachment to specific tool
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--dir",
                    "fs:docs",
                    "test_directory",
                    "--dry-run",
                ]
            )

            test_results["dir_tool_routing_exit"] = result.returncode == 0
            test_results["dir_contains_fs"] = (
                "file-search" in result.stdout.lower()
            )

            return TestResult(
                name="multi_tool_routing",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="multi_tool_routing",
                passed=False,
                details={"error": str(e)},
            )

    def test_security_modes(self) -> TestResult:
        """Test path security modes."""
        test_results = {}

        try:
            # Test permissive mode (default)
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--file",
                    "data",
                    "test_data.txt",
                    "--path-security",
                    "permissive",
                    "--dry-run",
                ]
            )

            test_results["permissive_mode_exit"] = result.returncode == 0

            # Test with explicit allow directory
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--file",
                    "data",
                    "test_data.txt",
                    "--path-security",
                    "strict",
                    "--allow",
                    str(self.test_data_dir),
                    "--dry-run",
                ]
            )

            test_results["strict_mode_with_allow_exit"] = (
                result.returncode == 0
            )

            return TestResult(
                name="security_modes",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="security_modes", passed=False, details={"error": str(e)}
            )

    def test_directory_processing(self) -> TestResult:
        """Test directory attachment and processing."""
        test_results = {}

        try:
            # Test basic directory attachment
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--dir",
                    "docs",
                    "test_directory",
                    "--dry-run",
                ]
            )

            test_results["dir_attachment_exit"] = result.returncode == 0
            test_results["dir_contains_files"] = (
                "file1.txt" in result.stdout or "file2.txt" in result.stdout
            )

            # Test directory with pattern
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--dir",
                    "docs",
                    "test_directory",
                    "--pattern",
                    "*.txt",
                    "--dry-run",
                ]
            )

            test_results["dir_pattern_exit"] = result.returncode == 0

            # Test recursive directory processing
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--dir",
                    "docs",
                    "test_directory",
                    "--recursive",
                    "--dry-run",
                ]
            )

            test_results["dir_recursive_exit"] = result.returncode == 0

            return TestResult(
                name="directory_processing",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="directory_processing",
                passed=False,
                details={"error": str(e)},
            )

    def test_collection_processing(self) -> TestResult:
        """Test file collection processing."""
        test_results = {}

        try:
            # Test file collection from list
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--collect",
                    "files",
                    "@file_list.txt",
                    "--dry-run",
                ]
            )

            test_results["collection_exit"] = result.returncode == 0
            test_results["collection_contains_data"] = (
                "test_data.txt" in result.stdout
            )

            return TestResult(
                name="collection_processing",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="collection_processing",
                passed=False,
                details={"error": str(e)},
            )

    def test_json_output_unified_guidelines(self) -> TestResult:
        """Test JSON output flags per unified guidelines."""
        test_results = {}

        try:
            # Test --help-json (should output to stdout and exit)
            result = self._run_ostruct_command(["run", "--help-json"])

            test_results["help_json_exit"] = result.returncode == 0
            test_results["help_json_stdout"] = len(result.stdout) > 0
            test_results["help_json_stderr_empty"] = len(result.stderr) == 0

            try:
                help_data = json.loads(result.stdout)
                test_results["help_json_valid"] = (
                    "ostruct_version" in help_data
                )
            except json.JSONDecodeError:
                test_results["help_json_valid"] = False

            # Test --dry-run --dry-run-json (plan JSON to stdout)
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--file",
                    "data",
                    "test_data.txt",
                    "--dry-run",
                    "--dry-run-json",
                ]
            )

            test_results["dry_run_json_exit"] = result.returncode == 0
            test_results["dry_run_json_stdout"] = len(result.stdout) > 0

            try:
                plan_data = json.loads(result.stdout)
                test_results["dry_run_json_valid"] = (
                    plan_data.get("type") == "execution_plan"
                )
            except json.JSONDecodeError:
                test_results["dry_run_json_valid"] = False

            # Test validation: --dry-run-json without --dry-run should fail
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--dry-run-json",
                ]
            )

            test_results["validation_dry_run_json"] = result.returncode != 0

            return TestResult(
                name="json_output_unified_guidelines",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="json_output_unified_guidelines",
                passed=False,
                details={"error": str(e)},
            )

    def test_stream_separation_validation(self) -> TestResult:
        """Test stdout/stderr separation per unified guidelines."""
        test_results = {}

        try:
            # Test dry-run human output goes to stdout
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--file",
                    "data",
                    "test_data.txt",
                    "--dry-run",
                ]
            )

            test_results["dry_run_human_stdout"] = (
                "execution plan" in result.stdout.lower()
            )
            test_results["dry_run_human_stderr_minimal"] = len(
                result.stderr
            ) < len(result.stdout)

            return TestResult(
                name="stream_separation_validation",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="stream_separation_validation",
                passed=False,
                details={"error": str(e)},
            )

    def test_error_handling(self) -> TestResult:
        """Test error handling and validation."""
        test_results = {}

        try:
            # Test invalid target
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--file",
                    "invalid-target:data",
                    "test_data.txt",
                    "--dry-run",
                ]
            )

            test_results["invalid_target_fails"] = result.returncode != 0
            test_results["invalid_target_message"] = (
                "unknown target" in result.stderr.lower()
            )

            # Test missing file
            result = self._run_ostruct_command(
                [
                    "run",
                    "test_template.j2",
                    "test_schema.json",
                    "--file",
                    "data",
                    "nonexistent_file.txt",
                    "--dry-run",
                ]
            )

            test_results["missing_file_fails"] = result.returncode != 0

            return TestResult(
                name="error_handling",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="error_handling", passed=False, details={"error": str(e)}
            )

    def run_all_tests(self) -> List[TestResult]:
        """Run all cross-platform tests."""
        test_methods = [
            self.test_basic_attachment,
            self.test_multi_tool_routing,
            self.test_security_modes,
            self.test_directory_processing,
            self.test_collection_processing,
            self.test_json_output_unified_guidelines,
            self.test_stream_separation_validation,
            self.test_error_handling,
        ]

        results = []
        for test_method in test_methods:
            try:
                result = test_method()
                results.append(result)
            except Exception as e:
                results.append(
                    TestResult(
                        name=test_method.__name__,
                        passed=False,
                        details={"error": f"Test execution failed: {e}"},
                    )
                )

        self.results = results
        return results

    def cleanup(self):
        """Clean up test files."""
        import shutil

        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)


# Pytest integration
@pytest.mark.no_fs
@pytest.mark.live
class TestCrossPlatformCLI:
    """Pytest class for cross-platform CLI testing."""

    @pytest.fixture(autouse=True)
    def setup_tester(self):
        """Setup cross-platform tester."""
        self.tester = CrossPlatformTester()
        yield
        self.tester.cleanup()

    def test_basic_attachment_functionality(self):
        """Test basic file attachment works cross-platform."""
        result = self.tester.test_basic_attachment()
        assert result.passed, f"Basic attachment test failed: {result.details}"

    def test_multi_tool_routing_functionality(self):
        """Test multi-tool routing works cross-platform."""
        result = self.tester.test_multi_tool_routing()
        assert (
            result.passed
        ), f"Multi-tool routing test failed: {result.details}"

    def test_security_modes_functionality(self):
        """Test security modes work cross-platform."""
        result = self.tester.test_security_modes()
        assert result.passed, f"Security modes test failed: {result.details}"

    def test_directory_processing_functionality(self):
        """Test directory processing works cross-platform."""
        result = self.tester.test_directory_processing()
        assert (
            result.passed
        ), f"Directory processing test failed: {result.details}"

    def test_collection_processing_functionality(self):
        """Test collection processing works cross-platform."""
        result = self.tester.test_collection_processing()
        assert (
            result.passed
        ), f"Collection processing test failed: {result.details}"

    def test_json_output_unified_guidelines_functionality(self):
        """Test JSON output per unified guidelines works cross-platform."""
        result = self.tester.test_json_output_unified_guidelines()
        assert result.passed, f"JSON output test failed: {result.details}"

    def test_stream_separation_functionality(self):
        """Test stream separation works cross-platform."""
        result = self.tester.test_stream_separation_validation()
        assert (
            result.passed
        ), f"Stream separation test failed: {result.details}"

    def test_error_handling_functionality(self):
        """Test error handling works cross-platform."""
        result = self.tester.test_error_handling()
        assert result.passed, f"Error handling test failed: {result.details}"


# Standalone test runner for manual execution
def run_cross_platform_tests():
    """Run cross-platform tests and generate report."""
    tester = CrossPlatformTester()

    try:
        print(
            f"🔍 Running Cross-Platform CLI Tests on {tester.current_platform}"
        )
        print("=" * 60)

        results = tester.run_all_tests()

        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)

        print("\n📊 Test Results Summary:")
        print(f"   Platform: {tester.current_platform}")
        print(f"   Passed: {passed_count}/{total_count}")
        print(f"   Success Rate: {passed_count/total_count*100:.1f}%")

        print("\n📋 Detailed Results:")
        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"   {status} {result.name}")
            if not result.passed:
                print(f"        Details: {result.details}")

        if passed_count == total_count:
            print(f"\n🎉 All tests passed on {tester.current_platform}!")
        else:
            print(
                f"\n⚠️  {total_count - passed_count} tests failed on {tester.current_platform}"
            )

        return results

    finally:
        tester.cleanup()


if __name__ == "__main__":
    run_cross_platform_tests()
