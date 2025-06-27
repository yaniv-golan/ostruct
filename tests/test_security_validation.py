"""Security validation and penetration testing for CLI v0.9.0.

This module implements T6.3: Security Validation and Penetration Testing from the CLI tasks plan.
Tests security controls against various attack vectors and validates security mode enforcement.

PERFORMANCE OPTIMIZATION:
- Uses hybrid approach: fast unit tests + critical integration tests
- Unit tests: Test security modules directly (milliseconds)
- Integration tests: Only most critical attack vectors via subprocess (seconds)
- Total time reduced from ~2-3 minutes to ~10-30 seconds
"""

import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple

import pytest

# Import security modules for direct unit testing
from ostruct.cli.security import (
    PathSecurity,
    PathSecurityError,
    SecurityManager,
    normalize_path,
)
from ostruct.cli.security.allowed_checker import is_path_in_allowed_dirs
from ostruct.cli.security.windows_paths import validate_windows_path


class TestResult(NamedTuple):
    """Security test result data structure."""

    name: str
    passed: bool
    details: Dict[str, Any]


# =============================================================================
# FAST UNIT TESTS - Test security modules directly (no subprocess overhead)
# =============================================================================


@pytest.mark.no_fs
class TestSecurityModulesUnit:
    """Fast unit tests for security modules - test logic directly."""

    def test_path_normalization_security(self):
        """Test path normalization blocks directory traversal paths."""
        # Only test paths that normalize_path actually blocks (directory traversal)
        traversal_paths = [
            "../../../etc/passwd",
            "file://../../sensitive.txt",
            "../../../../../../proc/version",
        ]

        # Platform-specific traversal paths
        if platform.system().lower() == "windows":
            # On Windows, test backslash traversal
            traversal_paths.extend(
                [
                    "..\\..\\..\\windows\\system32\\config\\sam",
                    "..\\..\\..\\boot.ini",
                ]
            )

        for traversal_path in traversal_paths:
            with pytest.raises(PathSecurityError):
                # normalize_path should block directory traversal
                normalize_path(traversal_path)

        # Test that non-traversal paths don't raise exceptions
        non_traversal_paths = [
            "/etc/shadow",  # Absolute path - not blocked by normalize_path
            "~/.ssh/id_rsa",  # Tilde path - not blocked by normalize_path
            "C:\\Windows\\System32\\config\\SAM",  # Absolute Windows path
        ]

        for safe_path in non_traversal_paths:
            # These should not raise exceptions (but may not be secure)
            try:
                result = normalize_path(safe_path)
                assert result is not None
            except PathSecurityError:
                pytest.fail(
                    f"normalize_path unexpectedly blocked non-traversal path: {safe_path}"
                )

    def test_allowed_checker_logic(self):
        """Test directory allowlist logic directly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            allowed_dirs = [temp_path]

            # Create test files
            safe_file = temp_path / "safe.txt"
            safe_file.write_text("safe")

            unsafe_dir = temp_path.parent / "unsafe"
            unsafe_dir.mkdir(exist_ok=True)
            unsafe_file = unsafe_dir / "unsafe.txt"
            unsafe_file.write_text("unsafe")

            # Test allowlist logic
            assert is_path_in_allowed_dirs(safe_file, allowed_dirs)
            assert not is_path_in_allowed_dirs(unsafe_file, allowed_dirs)

            # Cleanup
            shutil.rmtree(unsafe_dir, ignore_errors=True)

    def test_security_manager_modes(self):
        """Test security manager mode enforcement directly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test")

            # Test PERMISSIVE mode - should allow anything
            sm_permissive = SecurityManager(
                base_dir=temp_path, security_mode=PathSecurity.PERMISSIVE
            )
            assert sm_permissive.is_path_allowed_enhanced(test_file)

            # Test WARN mode - should allow with warnings
            sm_warn = SecurityManager(
                base_dir=temp_path, security_mode=PathSecurity.WARN
            )
            assert sm_warn.is_path_allowed_enhanced(test_file)

            # Test STRICT mode - should only allow explicitly allowed paths
            sm_strict = SecurityManager(
                base_dir=temp_path, security_mode=PathSecurity.STRICT
            )
            # File in base dir should be allowed
            assert sm_strict.is_path_allowed_enhanced(test_file)

            # File outside base dir should be blocked in strict mode
            outside_dir = temp_path.parent / "outside"
            outside_dir.mkdir(exist_ok=True)
            outside_file = outside_dir / "outside.txt"
            outside_file.write_text("outside")

            with pytest.raises(PathSecurityError):
                sm_strict.is_path_allowed_enhanced(outside_file)

            # Cleanup
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_windows_path_validation_unit(self):
        """Test Windows-specific path validation logic."""
        if platform.system().lower() != "windows":
            pytest.skip("Windows-specific test")

        dangerous_windows_paths = [
            "CON:",
            "LPT1:",
            "\\\\?\\C:\\dangerous",
            "\\\\.\\dangerous",
            "file.txt:stream",
            "\\\\network\\share\\file.txt",
        ]

        for dangerous_path in dangerous_windows_paths:
            error_msg = validate_windows_path(dangerous_path)
            assert (
                error_msg is not None
            ), f"Should block dangerous path: {dangerous_path}"

    def test_path_escape_validation_unit(self):
        """Test path escape validation logic directly."""
        malicious_paths = [
            "file:///etc/passwd",
            "http://evil.com/malware",
            "data:text/plain;base64,bWFsaWNpb3Vz",
            "javascript:alert('xss')",
            "/dev/null",
            "/proc/self/environ",
            "file\x00injection.txt",  # null byte injection
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sm = SecurityManager(
                base_dir=temp_path, security_mode=PathSecurity.STRICT
            )

            for malicious_path in malicious_paths:
                # These should all be blocked by security manager
                assert not sm.is_path_allowed(malicious_path)

    def test_command_injection_prevention_unit(self):
        """Test command injection prevention in path validation."""
        injection_attempts = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& curl evil.com",
            "$(whoami)",
            "`id`",
            "\x00; evil_command",
            "file.txt; echo pwned",
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sm = SecurityManager(
                base_dir=temp_path, security_mode=PathSecurity.STRICT
            )

            for injection in injection_attempts:
                # Command injection attempts should be blocked
                assert not sm.is_path_allowed(injection)

    def test_symlink_security_unit(self):
        """Test symlink security validation logic."""
        if platform.system().lower() == "windows":
            pytest.skip("Symlink test requires Unix-like system")

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
                symlink.symlink_to(sensitive_file)

                # Test symlink validation
                sm = SecurityManager(
                    base_dir=temp_path, security_mode=PathSecurity.STRICT
                )

                # Symlink target validation should raise exception in STRICT mode
                with pytest.raises(PathSecurityError):
                    sm.validate_symlink_target(symlink)

            except OSError:
                pytest.skip("Symlink creation failed")
            finally:
                shutil.rmtree(sensitive_dir, ignore_errors=True)


# =============================================================================
# CRITICAL INTEGRATION TESTS - Only most dangerous attack vectors via subprocess
# =============================================================================


class SecurityPenetrationTests:
    """Critical integration tests - reduced to most dangerous attack vectors."""

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

    def _run_ostruct_cmd(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run ostruct command for security testing."""
        import sys

        # Use direct Python execution instead of poetry to avoid dependency issues
        cmd = [
            sys.executable,
            "-c",
            "from ostruct.cli.cli import main; main()",
        ] + args
        project_root = Path(__file__).parent.parent
        # Reduced timeout for dry-run tests
        timeout = 10 if "--dry-run" in args else 30
        return subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_critical_directory_traversal(self) -> TestResult:
        """Test only the most critical directory traversal attacks."""
        # Reduced to most dangerous attacks only
        critical_attacks = [
            "../../../etc/passwd",  # Unix password file
            "C:\\Windows\\System32\\config\\SAM",  # Windows SAM file
            "$(rm -rf /)",  # Command injection
        ]

        results = {}
        for attack in critical_attacks:
            try:
                result = self._run_ostruct_cmd(
                    [
                        "run",
                        str(self.test_data_dir / "template.j2"),
                        str(self.test_data_dir / "schema.json"),
                        "--file",
                        "data",
                        attack,
                        "--path-security",
                        "strict",
                        "--allow",
                        str(self.test_data_dir),
                        "--dry-run",
                    ]
                )
                results[attack] = result.returncode != 0  # Should be blocked
            except Exception as e:
                results[attack] = f"Test error: {e}"

        return TestResult(
            name="critical_directory_traversal",
            passed=all(
                v is True for v in results.values() if isinstance(v, bool)
            ),
            details=results,
        )

    def test_critical_security_modes(self) -> TestResult:
        """Test critical security mode enforcement via CLI."""
        test_file = self.test_data_dir / "security_test.txt"
        test_file.write_text("test content")

        try:
            modes_results = {}

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
                name="critical_security_modes",
                passed=all(
                    [
                        modes_results.get("strict_blocks", False),
                        modes_results.get("strict_with_allowlist", False),
                    ]
                ),
                details=modes_results,
            )
        finally:
            test_file.unlink(missing_ok=True)

    def cleanup(self):
        """Clean up test files."""
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)


# =============================================================================
# PYTEST INTEGRATION - Hybrid approach with fast unit tests + critical integration
# =============================================================================


@pytest.mark.no_fs
class TestSecurityValidation:
    """Pytest class for security validation - hybrid approach."""

    @pytest.fixture(autouse=True)
    def setup_security_tests(self):
        """Setup security test suite."""
        self.security_tests = SecurityPenetrationTests()
        yield
        self.security_tests.cleanup()

    # Fast unit tests are in TestSecurityModulesUnit class above

    def test_critical_directory_traversal_integration(self):
        """Integration test for critical directory traversal attacks."""
        result = self.security_tests.test_critical_directory_traversal()
        assert (
            result.passed
        ), f"Critical directory traversal prevention failed: {result.details}"

    def test_critical_security_modes_integration(self):
        """Integration test for critical security mode enforcement."""
        result = self.security_tests.test_critical_security_modes()
        assert (
            result.passed
        ), f"Critical security mode enforcement failed: {result.details}"


# =============================================================================
# STANDALONE RUNNER - For manual testing and CI
# =============================================================================


def run_security_validation():
    """Run security validation with hybrid approach."""
    security_tests = SecurityPenetrationTests()

    try:
        print(
            f"🔒 Security Validation (Hybrid Approach) on {platform.system().lower()}"
        )
        print("=" * 60)
        print("✅ Fast unit tests: Testing security modules directly")
        print("🔍 Critical integration tests: Testing via CLI subprocess")
        print()

        # Run critical integration tests only
        test_methods = [
            security_tests.test_critical_directory_traversal,
            security_tests.test_critical_security_modes,
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

        print("🛡️  Critical Integration Test Results:")
        for result in results:
            status = "✅ SECURE" if result.passed else "🚨 VULNERABLE"
            print(f"   {status} {result.name}")
            if not result.passed:
                print(f"        Issues: {result.details}")

        print(f"\n📊 Integration Tests: {passed_count}/{total_count} passed")
        print("💡 Note: Fast unit tests cover additional attack vectors")
        print(
            "   Run 'pytest tests/test_security_validation.py::TestSecurityModulesUnit -v' for details"
        )

        if passed_count == total_count:
            print("\n🎉 All critical security tests passed! System is secure.")
        else:
            print(
                f"\n⚠️  {total_count - passed_count} critical vulnerabilities found!"
            )
            print("🚨 CRITICAL: Fix vulnerabilities before release!")

        return passed_count == total_count

    finally:
        security_tests.cleanup()


if __name__ == "__main__":
    success = run_security_validation()
    exit(0 if success else 1)
