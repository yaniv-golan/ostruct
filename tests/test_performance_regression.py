"""Performance and regression testing for CLI v0.9.0.

This module implements T6.2: Performance and Regression Testing from the CLI tasks plan.
Tests performance characteristics and ensures no regression in existing functionality.
"""

import json
import platform
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, NamedTuple

import psutil
import pytest


class BenchmarkResult(NamedTuple):
    """Benchmark result data structure."""

    name: str
    duration: float
    memory_delta: int
    throughput: float
    details: Dict[str, Any]


class ComparisonResult(NamedTuple):
    """Performance comparison result."""

    comparisons: List[Dict[str, Any]]
    summary: Dict[str, Any]


class TestResult(NamedTuple):
    """Test result data structure."""

    name: str
    passed: bool
    details: Dict[str, Any]


class PerformanceBenchmark:
    """Benchmark CLI performance across various scenarios."""

    def __init__(self):
        self.results = {}
        self.test_data_dir = Path(tempfile.mkdtemp(prefix="ostruct_perf_"))
        self._setup_test_files()

    def _setup_test_files(self):
        """Create basic test files."""
        # Template
        (self.test_data_dir / "template.j2").write_text(
            "Files: {% for f in _files %}{{ f.alias }} {% endfor %}"
        )

        # Schema
        schema = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        (self.test_data_dir / "schema.json").write_text(json.dumps(schema))

    def _run_ostruct_cmd(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run ostruct command with timing."""
        cmd = ["poetry", "run", "ostruct"] + args
        project_root = Path(__file__).parent.parent
        return subprocess.run(
            cmd, cwd=project_root, capture_output=True, text=True, timeout=60
        )

    def benchmark_file_processing(
        self, file_count: int, file_size: int
    ) -> BenchmarkResult:
        """Benchmark file processing performance."""
        # Create test files
        test_files = []
        for i in range(file_count):
            file_path = self.test_data_dir / f"perf_test_{i}.txt"
            file_path.write_text("x" * file_size)
            test_files.append(file_path)

        try:
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss

            # Build command args
            cmd_args = [
                "run",
                str(self.test_data_dir / "template.j2"),
                str(self.test_data_dir / "schema.json"),
            ]

            # Add all file attachments
            for i, file_path in enumerate(test_files):
                cmd_args.extend(["--file", f"file_{i}", str(file_path)])

            cmd_args.append("--dry-run")

            # Run ostruct command
            result = self._run_ostruct_cmd(cmd_args)

            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss

            duration = end_time - start_time

            return BenchmarkResult(
                name=f"file_processing_{file_count}x{file_size}",
                duration=duration,
                memory_delta=end_memory - start_memory,
                throughput=file_count / duration if duration > 0 else 0,
                details={
                    "exit_code": result.returncode,
                    "files_processed": file_count,
                    "total_size": file_count * file_size,
                    "command_success": result.returncode == 0,
                },
            )
        finally:
            for file_path in test_files:
                file_path.unlink(missing_ok=True)

    def compare_legacy_performance(self) -> ComparisonResult:
        """Compare new CLI performance across scenarios."""
        test_scenarios = [
            {"files": 1, "size": 1024},  # Small single file
            {"files": 10, "size": 1024},  # Multiple small files
            {"files": 1, "size": 65536},  # Large single file
            {"files": 50, "size": 512},  # Many tiny files
        ]

        comparisons = []
        total_duration = 0

        for scenario in test_scenarios:
            # Benchmark new implementation
            result = self.benchmark_file_processing(
                scenario["files"], scenario["size"]
            )

            total_duration += result.duration

            # Performance expectations (baseline measurements)
            expected_max_duration = {
                (1, 1024): 2.0,  # 1 small file: max 2s
                (10, 1024): 3.0,  # 10 small files: max 3s
                (1, 65536): 2.5,  # 1 large file: max 2.5s
                (50, 512): 5.0,  # 50 tiny files: max 5s
            }

            scenario_key = (scenario["files"], scenario["size"])
            max_expected = expected_max_duration.get(scenario_key, 10.0)

            comparison = {
                "scenario": f"{scenario['files']}x{scenario['size']}",
                "duration": result.duration,
                "max_expected": max_expected,
                "within_expectations": result.duration <= max_expected,
                "throughput": result.throughput,
                "memory_delta": result.memory_delta,
                "command_success": result.details["command_success"],
            }
            comparisons.append(comparison)

        summary = {
            "total_duration": total_duration,
            "all_within_expectations": all(
                c["within_expectations"] for c in comparisons
            ),
            "all_commands_successful": all(
                c["command_success"] for c in comparisons
            ),
            "average_throughput": sum(c["throughput"] for c in comparisons)
            / len(comparisons),
        }

        return ComparisonResult(comparisons, summary)

    def test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage with large file sets."""
        large_files = []
        file_size = 10000  # 10KB each (smaller for testing)
        file_count = 20  # Reduced for CI environments

        for i in range(file_count):
            file_path = self.test_data_dir / f"large_test_{i}.txt"
            file_path.write_text("x" * file_size)
            large_files.append(file_path)

        try:
            initial_memory = psutil.Process().memory_info().rss

            # Build command with many attachments
            cmd_args = [
                "run",
                str(self.test_data_dir / "template.j2"),
                str(self.test_data_dir / "schema.json"),
            ]

            for i, file_path in enumerate(large_files):
                cmd_args.extend(["--file", f"file_{i}", str(file_path)])

            cmd_args.append("--dry-run")

            # Run command
            result = self._run_ostruct_cmd(cmd_args)

            final_memory = psutil.Process().memory_info().rss
            memory_delta = final_memory - initial_memory

            return {
                "files_created": len(large_files),
                "file_size": file_size,
                "initial_memory": initial_memory,
                "final_memory": final_memory,
                "memory_delta": memory_delta,
                "memory_per_file": (
                    memory_delta / file_count if file_count > 0 else 0
                ),
                "command_success": result.returncode == 0,
                "reasonable_memory_usage": memory_delta
                < 50 * 1024 * 1024,  # < 50MB
            }
        finally:
            for file_path in large_files:
                file_path.unlink(missing_ok=True)

    def test_json_output_unified_guidelines(self) -> TestResult:
        """Test JSON output flags per unified guidelines."""
        test_results = {}

        try:
            # Test --help-json (should output to stdout and exit)
            result = self._run_ostruct_cmd(["run", "--help-json"])

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
            test_file = self.test_data_dir / "test.txt"
            test_file.write_text("test content")

            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(self.test_data_dir / "template.j2"),
                    str(self.test_data_dir / "schema.json"),
                    "--file",
                    "data",
                    str(test_file),
                    "--dry-run",
                    "--dry-run-json",
                ]
            )

            test_results["dry_run_json_exit"] = result.returncode == 0
            test_results["dry_run_json_stdout"] = len(result.stdout) > 0

            try:
                plan_data = json.loads(result.stdout)
                test_results["dry_run_json_valid"] = "attachments" in plan_data
            except json.JSONDecodeError:
                test_results["dry_run_json_valid"] = False

            # Test validation: --dry-run-json without --dry-run should fail
            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(self.test_data_dir / "template.j2"),
                    str(self.test_data_dir / "schema.json"),
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
            test_file = self.test_data_dir / "test.txt"
            test_file.write_text("test content")

            # Test dry-run human output goes to stdout
            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(self.test_data_dir / "template.j2"),
                    str(self.test_data_dir / "schema.json"),
                    "--file",
                    "data",
                    str(test_file),
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

    def test_template_compatibility(self) -> TestResult:
        """Ensure templates still work with new attachment system."""
        test_results = {}

        try:
            # Test basic variable access
            template_file = self.test_data_dir / "var_template.j2"
            template_file.write_text("Content: {{ data.content }}")

            data_file = self.test_data_dir / "data.txt"
            data_file.write_text("test content")

            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(template_file),
                    str(self.test_data_dir / "schema.json"),
                    "--file",
                    "data",
                    str(data_file),
                    "--dry-run",
                ]
            )

            test_results["basic_variable_access"] = result.returncode == 0

            # Test multiple file attachments
            template_file2 = self.test_data_dir / "multi_template.j2"
            template_file2.write_text(
                "Files: {% for f in _files %}{{ f.alias }} {% endfor %}"
            )

            file1 = self.test_data_dir / "file1.txt"
            file2 = self.test_data_dir / "file2.txt"
            file1.write_text("content1")
            file2.write_text("content2")

            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(template_file2),
                    str(self.test_data_dir / "schema.json"),
                    "--file",
                    "file1",
                    str(file1),
                    "--file",
                    "file2",
                    str(file2),
                    "--dry-run",
                ]
            )

            test_results["multiple_file_access"] = result.returncode == 0

            return TestResult(
                name="template_compatibility",
                passed=all(test_results.values()),
                details=test_results,
            )

        except Exception as e:
            return TestResult(
                name="template_compatibility",
                passed=False,
                details={"error": str(e)},
            )

    def cleanup(self):
        """Clean up test files."""
        import shutil

        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)


# Pytest integration
@pytest.mark.no_fs
@pytest.mark.live
class TestPerformanceRegression:
    """Pytest class for performance and regression testing."""

    @pytest.fixture(autouse=True)
    def setup_benchmark(self):
        """Setup performance benchmark."""
        self.benchmark = PerformanceBenchmark()
        yield
        self.benchmark.cleanup()

    def test_file_processing_performance(self):
        """Test file processing performance meets expectations."""
        comparison = self.benchmark.compare_legacy_performance()

        assert comparison.summary[
            "all_commands_successful"
        ], "Some commands failed during performance testing"

        assert comparison.summary[
            "all_within_expectations"
        ], f"Performance outside expectations: {comparison.comparisons}"

    def test_memory_usage_reasonable(self):
        """Test memory usage is reasonable for large file sets."""
        memory_result = self.benchmark.test_memory_usage()

        assert memory_result[
            "command_success"
        ], "Memory usage test command failed"

        assert memory_result[
            "reasonable_memory_usage"
        ], f"Memory usage too high: {memory_result['memory_delta']} bytes"

    def test_json_output_guidelines_compliance(self):
        """Test JSON output follows unified guidelines."""
        result = self.benchmark.test_json_output_unified_guidelines()
        assert (
            result.passed
        ), f"JSON output guidelines test failed: {result.details}"

    def test_stream_separation_compliance(self):
        """Test stream separation follows unified guidelines."""
        result = self.benchmark.test_stream_separation_validation()
        assert (
            result.passed
        ), f"Stream separation test failed: {result.details}"

    def test_template_regression(self):
        """Test template compatibility hasn't regressed."""
        result = self.benchmark.test_template_compatibility()
        assert (
            result.passed
        ), f"Template compatibility test failed: {result.details}"


# Standalone runner
def run_performance_tests():
    """Run performance and regression tests."""
    benchmark = PerformanceBenchmark()

    try:
        print(
            f"🚀 Performance & Regression Testing on {platform.system().lower()}"
        )
        print("=" * 60)

        # Performance benchmarks
        print("\n📊 Performance Benchmarks:")
        comparison = benchmark.compare_legacy_performance()

        for comp in comparison.comparisons:
            status = "✅" if comp["within_expectations"] else "⚠️"
            print(
                f"   {status} {comp['scenario']}: {comp['duration']:.2f}s "
                f"(max: {comp['max_expected']:.1f}s)"
            )

        print("\n   📈 Summary:")
        print(
            f"      Total duration: {comparison.summary['total_duration']:.2f}s"
        )
        print(
            f"      Average throughput: {comparison.summary['average_throughput']:.1f} files/s"
        )
        print(
            f"      All within expectations: {comparison.summary['all_within_expectations']}"
        )

        # Memory usage
        print("\n🧠 Memory Usage:")
        memory_result = benchmark.test_memory_usage()
        memory_mb = memory_result["memory_delta"] / (1024 * 1024)
        per_file_kb = memory_result["memory_per_file"] / 1024

        print(f"   Memory delta: {memory_mb:.1f} MB")
        print(f"   Per file: {per_file_kb:.1f} KB")
        print(
            f"   Reasonable usage: {memory_result['reasonable_memory_usage']}"
        )

        # Compliance tests
        print("\n📋 Compliance Tests:")

        json_result = benchmark.test_json_output_unified_guidelines()
        stream_result = benchmark.test_stream_separation_validation()
        template_result = benchmark.test_template_compatibility()

        tests = [json_result, stream_result, template_result]
        passed_count = sum(1 for t in tests if t.passed)

        for test in tests:
            status = "✅ PASS" if test.passed else "❌ FAIL"
            print(f"   {status} {test.name}")

        print("\n🎯 Overall Results:")
        perf_passed = comparison.summary["all_within_expectations"]
        memory_passed = memory_result["reasonable_memory_usage"]
        compliance_passed = passed_count == len(tests)

        all_passed = perf_passed and memory_passed and compliance_passed

        print(f"   Performance: {'✅ PASS' if perf_passed else '❌ FAIL'}")
        print(f"   Memory: {'✅ PASS' if memory_passed else '❌ FAIL'}")
        print(
            f"   Compliance: {'✅ PASS' if compliance_passed else '❌ FAIL'}"
        )

        if all_passed:
            print("\n🎉 All performance and regression tests passed!")
        else:
            print("\n⚠️  Some tests failed - review results above")

        return all_passed

    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    success = run_performance_tests()
    exit(0 if success else 1)
