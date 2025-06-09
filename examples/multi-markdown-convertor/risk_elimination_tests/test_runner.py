#!/usr/bin/env python3
"""
Comprehensive Test Runner for Multi-Markdown Converter Risk Elimination Tests

This script executes all 30 tests in isolated environment with proper:
- Error handling and timeouts
- Resource cleanup
- Result collection and reporting
- Categorized execution (dry-run vs live)
"""

import json
import sys
import subprocess
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
import shutil
import signal


@dataclass
class TestResult:
    """Container for individual test results."""

    test_id: str
    test_name: str
    success: bool
    duration: float
    error: Optional[str] = None
    results_file: Optional[Path] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class TestRunner:
    """Main test runner class."""

    def __init__(
        self, tests_dir: Path, dry_run: bool = True, timeout: int = 300
    ):
        self.tests_dir = tests_dir
        self.dry_run = dry_run
        self.timeout = timeout
        self.results: List[TestResult] = []

        # Test categories
        self.pdf_processing_tests = ["01", "02", "03"]
        self.document_conversion_tests = [
            "04",
            "05",
            "06",
            "07",
            "08",
            "09",
            "10",
        ]
        self.llm_integration_tests = [
            "11",
            "12",
            "13",
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
            "20",
            "21",
            "22",
        ]
        self.performance_tests = [
            "23",
            "24",
            "25",
            "26",
            "27",
            "28",
            "29",
            "30",
        ]

    def find_test_directories(self) -> List[Path]:
        """Find all test directories."""
        test_dirs = []
        for i in range(1, 31):
            test_id = f"{i:02d}"
            test_dir = self.tests_dir / f"test_{test_id}_*"
            matching_dirs = list(self.tests_dir.glob(f"test_{test_id}_*"))
            if matching_dirs:
                test_dirs.extend(matching_dirs)
        return sorted(test_dirs)

    def run_single_test(self, test_dir: Path) -> TestResult:
        """Execute a single test with timeout and error handling."""
        test_id = test_dir.name.split("_")[1]
        test_script = test_dir / f"test_{test_id}.py"

        result = TestResult(
            test_id=test_id,
            test_name=test_dir.name,
            success=False,
            duration=0.0,
        )

        if not test_script.exists():
            result.error = f"Test script not found: {test_script}"
            return result

        print(f"Running Test {test_id}: {test_dir.name}")

        start_time = time.time()

        try:
            # Run test in virtual environment
            cmd = [
                "bash",
                "-c",
                f"source test_env/bin/activate && cd {test_dir} && python {test_script.name}",
            ]

            process = subprocess.run(
                cmd,
                cwd=self.tests_dir.parent,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            result.duration = time.time() - start_time
            result.stdout = process.stdout
            result.stderr = process.stderr

            # Check for results.json file
            results_file = test_dir / "results.json"
            if results_file.exists():
                result.results_file = results_file
                try:
                    with open(results_file, "r") as f:
                        test_data = json.load(f)
                        result.success = test_data.get("success", False)
                except json.JSONDecodeError as e:
                    result.error = f"Invalid JSON in results file: {e}"
            else:
                # Fallback: check return code
                result.success = process.returncode == 0
                if not result.success:
                    result.error = (
                        f"Test failed with return code {process.returncode}"
                    )

            if process.returncode != 0 and not result.error:
                result.error = f"Process failed: {process.stderr[:200]}..."

        except subprocess.TimeoutExpired:
            result.error = f"Test timed out after {self.timeout} seconds"
            result.duration = self.timeout

        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
            result.duration = time.time() - start_time

        # Clean up any temporary files created by the test
        self.cleanup_test_artifacts(test_dir)

        return result

    def cleanup_test_artifacts(self, test_dir: Path) -> None:
        """Clean up temporary files created by tests."""
        cleanup_patterns = [
            "*.tmp",
            "*.temp",
            "temp_*",
            "test_output_*",
            "*.log",
            "generated_*",
            "temp_dir_*",
        ]

        for pattern in cleanup_patterns:
            for temp_file in test_dir.glob(pattern):
                try:
                    if temp_file.is_file():
                        temp_file.unlink()
                    elif temp_file.is_dir():
                        shutil.rmtree(temp_file)
                except Exception:
                    pass  # Ignore cleanup errors

    def run_tests_by_category(self, category: str) -> None:
        """Run tests by category."""
        category_map = {
            "pdf": self.pdf_processing_tests,
            "document": self.document_conversion_tests,
            "llm": self.llm_integration_tests,
            "performance": self.performance_tests,
        }

        if category not in category_map:
            print(f"Unknown category: {category}")
            return

        test_ids = category_map[category]
        test_dirs = [
            d
            for d in self.find_test_directories()
            if d.name.split("_")[1] in test_ids
        ]

        print(f"\nRunning {category.upper()} tests ({len(test_dirs)} tests):")
        print("=" * 50)

        for test_dir in test_dirs:
            result = self.run_single_test(test_dir)
            self.results.append(result)
            self.print_test_result(result)

    def run_all_tests(self, parallel: bool = False) -> None:
        """Run all 30 tests."""
        test_dirs = self.find_test_directories()
        print(f"\nFound {len(test_dirs)} tests to run")
        print("=" * 50)

        if parallel and not self.dry_run:
            # Only run in parallel for non-API tests to avoid rate limits
            safe_parallel_tests = [
                d
                for d in test_dirs
                if d.name.split("_")[1]
                in self.pdf_processing_tests + self.document_conversion_tests
            ]
            sequential_tests = [
                d for d in test_dirs if d not in safe_parallel_tests
            ]

            # Run safe tests in parallel
            if safe_parallel_tests:
                print(
                    f"Running {len(safe_parallel_tests)} tests in parallel..."
                )
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=4
                ) as executor:
                    future_to_test = {
                        executor.submit(
                            self.run_single_test, test_dir
                        ): test_dir
                        for test_dir in safe_parallel_tests
                    }

                    for future in concurrent.futures.as_completed(
                        future_to_test
                    ):
                        result = future.result()
                        self.results.append(result)
                        self.print_test_result(result)

            # Run API tests sequentially
            if sequential_tests:
                print(
                    f"Running {len(sequential_tests)} API tests sequentially..."
                )
                for test_dir in sequential_tests:
                    result = self.run_single_test(test_dir)
                    self.results.append(result)
                    self.print_test_result(result)
        else:
            # Run all tests sequentially
            for test_dir in test_dirs:
                result = self.run_single_test(test_dir)
                self.results.append(result)
                self.print_test_result(result)

    def print_test_result(self, result: TestResult) -> None:
        """Print formatted test result."""
        status = "✅ PASS" if result.success else "❌ FAIL"
        duration_str = f"{result.duration:.2f}s"

        print(f"Test {result.test_id}: {status} ({duration_str})")

        if result.error:
            print(f"  Error: {result.error}")

        if result.results_file and result.results_file.exists():
            print(f"  Results: {result.results_file}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        total_duration = sum(r.duration for r in self.results)

        report = {
            "execution_info": {
                "timestamp": datetime.now().isoformat(),
                "dry_run": self.dry_run,
                "timeout": self.timeout,
                "total_duration": round(total_duration, 2),
            },
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": round(passed_tests / total_tests * 100, 1)
                if total_tests > 0
                else 0,
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": round(r.duration, 2),
                    "error": r.error,
                    "has_results_file": r.results_file is not None
                    and r.results_file.exists(),
                }
                for r in self.results
            ],
            "failed_tests": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "error": r.error,
                    "stderr": r.stderr[:500] if r.stderr else None,
                }
                for r in self.results
                if not r.success
            ],
        }

        return report

    def save_report(self, output_file: Path) -> None:
        """Save test report to file."""
        report = self.generate_report()

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nTest report saved to: {output_file}")

    def print_summary(self) -> None:
        """Print test execution summary."""
        report = self.generate_report()
        summary = report["summary"]

        print("\n" + "=" * 60)
        print("TEST EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} (✅)")
        print(f"Failed: {summary['failed']} (❌)")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Total Duration: {report['execution_info']['total_duration']}s")

        if report["failed_tests"]:
            print(f"\nFailed Tests:")
            for failed in report["failed_tests"]:
                print(f"  • Test {failed['test_id']}: {failed['error']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run multi-markdown converter tests"
    )
    parser.add_argument(
        "--category",
        choices=["pdf", "document", "llm", "performance", "all"],
        default="all",
        help="Test category to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode (no API calls)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run with live API calls (costs money)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Test timeout in seconds"
    )
    parser.add_argument(
        "--parallel", action="store_true", help="Run safe tests in parallel"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="test_report.json",
        help="Output file for test report",
    )

    args = parser.parse_args()

    # Set dry_run based on flags
    dry_run = not args.live

    tests_dir = Path(__file__).parent / "tests"
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
        sys.exit(1)

    runner = TestRunner(tests_dir, dry_run=dry_run, timeout=args.timeout)

    print("Multi-Markdown Converter Test Runner")
    print("=" * 40)
    print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE (API calls)'}")
    print(f"Timeout: {args.timeout}s per test")
    print(f"Category: {args.category}")

    try:
        if args.category == "all":
            runner.run_all_tests(parallel=args.parallel)
        else:
            runner.run_tests_by_category(args.category)

        runner.print_summary()
        runner.save_report(Path(args.output))

        # Exit with error code if any tests failed
        failed_count = sum(1 for r in runner.results if not r.success)
        sys.exit(1 if failed_count > 0 else 0)

    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        runner.print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
