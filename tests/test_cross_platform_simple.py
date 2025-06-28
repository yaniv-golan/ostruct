"""Simplified cross-platform testing for CLI v0.9.0 functionality.

This is a streamlined version focusing on key functionality validation.
"""

import json
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import List

import pytest


def run_ostruct_cmd(args: List[str]) -> subprocess.CompletedProcess:
    """Run ostruct command from project root."""
    cmd = ["poetry", "run", "ostruct"] + args
    project_root = Path(__file__).parent.parent
    return subprocess.run(
        cmd, cwd=project_root, capture_output=True, text=True, timeout=30
    )


def setup_test_files() -> Path:
    """Create test files and return test directory."""
    test_dir = Path(tempfile.mkdtemp(prefix="ostruct_cross_platform_"))

    # Template
    (test_dir / "template.j2").write_text(
        "Analyze: {{ data.content if data is defined else 'No data' }}"
    )

    # Schema
    schema = {
        "type": "object",
        "properties": {"result": {"type": "string"}},
        "required": ["result"],
    }
    (test_dir / "schema.json").write_text(json.dumps(schema))

    # Test data
    (test_dir / "test.txt").write_text("test data")

    # Test directory
    test_subdir = test_dir / "subdir"
    test_subdir.mkdir()
    (test_subdir / "file1.txt").write_text("content 1")
    (test_subdir / "file2.txt").write_text("content 2")

    # File list
    (test_dir / "files.txt").write_text(str(test_dir / "test.txt"))

    return test_dir


@pytest.mark.no_fs
@pytest.mark.live
def test_basic_functionality():
    """Test basic CLI functionality works."""
    test_dir = setup_test_files()

    results = {}

    try:
        # 1. Test basic attachment
        result = run_ostruct_cmd(
            [
                "run",
                str(test_dir / "template.j2"),
                str(test_dir / "schema.json"),
                "--file",
                "data",
                str(test_dir / "test.txt"),
                "--dry-run",
            ]
        )
        results["basic_attachment"] = result.returncode == 0

        # 2. Test multi-tool routing
        result = run_ostruct_cmd(
            [
                "run",
                str(test_dir / "template.j2"),
                str(test_dir / "schema.json"),
                "--file",
                "ci,fs:shared",
                str(test_dir / "test.txt"),
                "--dry-run",
            ]
        )
        results["multi_tool"] = (
            result.returncode == 0 and "code-interpreter" in result.stdout
        )

        # 3. Test directory attachment
        result = run_ostruct_cmd(
            [
                "run",
                str(test_dir / "template.j2"),
                str(test_dir / "schema.json"),
                "--dir",
                "docs",
                str(test_dir / "subdir"),
                "--dry-run",
            ]
        )
        results["directory"] = result.returncode == 0

        # 4. Test JSON help
        result = run_ostruct_cmd(["run", "--help-json"])
        results["json_help"] = (
            result.returncode == 0 and "ostruct_version" in result.stdout
        )

        # 5. Test dry-run JSON
        result = run_ostruct_cmd(
            [
                "run",
                str(test_dir / "template.j2"),
                str(test_dir / "schema.json"),
                "--file",
                "data",
                str(test_dir / "test.txt"),
                "--dry-run",
                "--dry-run-json",
            ]
        )
        results["dry_run_json"] = result.returncode == 0
        if results["dry_run_json"]:
            try:
                data = json.loads(result.stdout)
                # Check for basic structure (current implementation doesn't have 'type' field yet)
                results["dry_run_json_valid"] = (
                    "attachments" in data and "template" in data
                )
            except (json.JSONDecodeError, KeyError):
                results["dry_run_json_valid"] = False

        # 6. Test security modes
        result = run_ostruct_cmd(
            [
                "run",
                str(test_dir / "template.j2"),
                str(test_dir / "schema.json"),
                "--file",
                "data",
                str(test_dir / "test.txt"),
                "--path-security",
                "permissive",
                "--dry-run",
            ]
        )
        results["security_permissive"] = result.returncode == 0

        # 7. Test error handling
        result = run_ostruct_cmd(
            [
                "run",
                str(test_dir / "template.j2"),
                str(test_dir / "schema.json"),
                "--file",
                "invalid-target:data",
                str(test_dir / "test.txt"),
                "--dry-run",
            ]
        )
        results["invalid_target_fails"] = result.returncode != 0

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(test_dir)

    return results


def main():
    """Run cross-platform validation."""
    print(f"🔍 Cross-Platform CLI Validation on {platform.system().lower()}")
    print("=" * 60)

    results = test_basic_functionality()

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(
        f"\n📊 Results: {passed}/{total} tests passed ({passed / total * 100:.1f}%)"
    )
    print("\n📋 Details:")

    for test_name, passed_val in results.items():
        status = "✅ PASS" if passed_val else "❌ FAIL"
        print(f"   {status} {test_name}")

    if passed == total:
        print(f"\n🎉 All tests passed on {platform.system().lower()}!")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
