"""Test error handling functionality."""

import logging
import os
from typing import Type, TypedDict

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.cli import handle_error
from ostruct.cli.errors import (
    CLIError,
    DirectoryNotFoundError,
    InvalidJSONError,
    OstructFileNotFoundError,
    SchemaError,
    SchemaFileError,
    SchemaValidationError,
    SecurityErrorBase,
    TaskTemplateError,
    TaskTemplateSyntaxError,
    TaskTemplateVariableError,
    VariableError,
    VariableNameError,
    VariableValueError,
)
from ostruct.cli.exit_codes import ExitCode
from ostruct.cli.file_info import FileInfo
from ostruct.cli.file_utils import collect_files_from_directory
from ostruct.cli.path_utils import validate_path_mapping
from ostruct.cli.security.errors import PathSecurityError, SecurityErrorReasons
from tests.conftest import MockSecurityManager


def test_variable_name_error() -> None:
    """Test VariableNameError."""
    error_msg = "test error"
    with pytest.raises(VariableNameError, match=error_msg):
        raise VariableNameError(error_msg)


def test_variable_value_error() -> None:
    """Test VariableValueError."""
    error_msg = "test error"
    with pytest.raises(VariableValueError, match=error_msg):
        raise VariableValueError(error_msg)


def test_json_variable_name_error() -> None:
    """Test JSON variable name error."""
    error_msg = "Empty name in JSON variable mapping"
    with pytest.raises(VariableNameError, match=error_msg):
        raise VariableNameError(error_msg)


def test_json_variable_value_error() -> None:
    """Test JSON variable value error."""
    error_msg = "Invalid JSON value"
    with pytest.raises(ValueError, match=error_msg):
        raise ValueError(error_msg)


def test_path_name_error() -> None:
    """Test path name error."""
    error_msg = "test error"
    with pytest.raises(VariableNameError, match=error_msg):
        raise VariableNameError(error_msg)


def test_file_not_found_error() -> None:
    """Test OstructFileNotFoundError."""
    error_msg = "test error"
    with pytest.raises(OstructFileNotFoundError, match=error_msg):
        raise OstructFileNotFoundError(error_msg)


def test_directory_not_found_error() -> None:
    """Test DirectoryNotFoundError."""
    error_msg = "test error"
    with pytest.raises(DirectoryNotFoundError, match=error_msg):
        raise DirectoryNotFoundError(error_msg)


def test_path_security_error_traversal(fs: FakeFilesystem) -> None:
    """Test path security error for path traversal."""
    error_msg = "Path '../test' is not allowed"
    with pytest.raises(PathSecurityError, match=error_msg):
        raise PathSecurityError(error_msg)


def test_path_security_error_permission(fs: FakeFilesystem) -> None:
    """Test path security error for permission issues."""
    error_msg = "Path '/root/test' is not allowed"
    with pytest.raises(PathSecurityError, match=error_msg):
        raise PathSecurityError(error_msg)


def test_task_template_syntax_error() -> None:
    """Test TaskTemplateSyntaxError."""
    error_msg = "test error"
    with pytest.raises(TaskTemplateSyntaxError, match=error_msg):
        raise TaskTemplateSyntaxError(error_msg)


def test_task_template_file_error() -> None:
    """Test TaskTemplateError."""
    error_msg = "test error"
    with pytest.raises(TaskTemplateError, match=error_msg):
        raise TaskTemplateError(error_msg)


def test_task_template_file_security_error(fs: FakeFilesystem) -> None:
    """Test task template file security error."""
    error_msg = "Path '../template' is not allowed"
    with pytest.raises(PathSecurityError, match=error_msg):
        raise PathSecurityError(error_msg)


def test_schema_file_error() -> None:
    """Test SchemaFileError."""
    error_msg = "test error"
    with pytest.raises(SchemaFileError, match=error_msg):
        raise SchemaFileError(error_msg)


def test_schema_json_error(fs: FakeFilesystem) -> None:
    """Test schema JSON error."""
    error_msg = "Invalid JSON in schema file"
    with pytest.raises(InvalidJSONError, match=error_msg):
        raise InvalidJSONError(error_msg)


def test_schema_validation_error() -> None:
    """Test SchemaValidationError."""
    error_msg = "test error"
    with pytest.raises(SchemaValidationError, match=error_msg):
        raise SchemaValidationError(error_msg)


def test_schema_file_security_error(fs: FakeFilesystem) -> None:
    """Test schema file security error."""
    error_msg = "Path '../schema' is not allowed"
    with pytest.raises(PathSecurityError, match=error_msg):
        raise PathSecurityError(error_msg)


def test_cli_error_str() -> None:
    """Test CLIError string representation."""
    error_msg = "test error"
    error = CLIError(error_msg)
    assert str(error).startswith("[INTERNAL_ERROR] test error")


def test_variable_error_str() -> None:
    """Test VariableError string representation."""
    error_msg = "test error"
    error = VariableError(error_msg)
    assert str(error).startswith("[INTERNAL_ERROR] test error")


def test_variable_name_error_str() -> None:
    """Test VariableNameError string representation."""
    error_msg = "test error"
    error = VariableNameError(error_msg)
    assert str(error).startswith("[INTERNAL_ERROR] test error")


def test_variable_value_error_str() -> None:
    """Test VariableValueError string representation."""
    error_msg = "test error"
    error = VariableValueError(error_msg)
    assert str(error).startswith("[INTERNAL_ERROR] test error")


def test_invalid_json_error() -> None:
    """Test InvalidJSONError."""
    error_msg = "test error"
    with pytest.raises(InvalidJSONError, match=error_msg):
        raise InvalidJSONError(error_msg)


def test_file_not_found_error_str() -> None:
    """Test OstructFileNotFoundError string representation."""
    path = "/test/file.txt"
    error = OstructFileNotFoundError(path)
    error_str = str(error)
    assert error_str.startswith(f"[FILE_ERROR] File not found: {path}")
    assert "Details: " in error_str
    assert "Path: " in error_str
    assert "Troubleshooting:" in error_str


def test_directory_not_found_error_str() -> None:
    """Test DirectoryNotFoundError string representation."""
    path = "/test/dir"
    error = DirectoryNotFoundError(path)
    error_str = str(error)
    assert error_str.startswith(f"[FILE_ERROR] Directory not found: {path}")
    assert "Details: " in error_str
    assert "Path: " in error_str
    assert "Troubleshooting:" in error_str


def test_path_security_error() -> None:
    """Test PathSecurityError."""
    error_msg = "test error"
    with pytest.raises(PathSecurityError, match=error_msg):
        raise PathSecurityError(error_msg)


def test_task_template_error() -> None:
    """Test TaskTemplateError."""
    error_msg = "test error"
    with pytest.raises(TaskTemplateError, match=error_msg):
        raise TaskTemplateError(error_msg)


def test_task_template_variable_error() -> None:
    """Test TaskTemplateVariableError."""
    error_msg = "test error"
    with pytest.raises(TaskTemplateVariableError, match=error_msg):
        raise TaskTemplateVariableError(error_msg)


def test_schema_error() -> None:
    """Test SchemaError."""
    error_msg = "test error"
    with pytest.raises(SchemaError, match=error_msg):
        raise SchemaError(error_msg)


def test_schema_file_error_str() -> None:
    """Test SchemaFileError string representation."""
    error_msg = "test error"
    error = SchemaFileError(error_msg)
    assert str(error).startswith("[SCHEMA_ERROR] test error")


def test_schema_validation_error_str() -> None:
    """Test SchemaValidationError string representation."""
    error_msg = "test error"
    error = SchemaValidationError(error_msg)
    assert str(error).startswith("[SCHEMA_ERROR] test error")


def test_schema_file_error_with_base_dir() -> None:
    """Test SchemaFileError with base directory."""
    error_msg = "test error"
    with pytest.raises(SchemaFileError, match=error_msg):
        raise SchemaFileError(error_msg)


def test_error_context_handling():
    """Test error context handling and formatting."""
    # Test basic context
    error = SchemaFileError(
        "Invalid JSON",
        schema_path="config.json",
    )
    error_str = str(error)
    assert "[SCHEMA_ERROR] Invalid JSON" in error_str
    assert "Source: config.json" in error_str

    # Test schema_path compatibility
    error = SchemaFileError("Schema error", schema_path="schema.json")
    assert error.source == "schema.json"
    assert "Source: schema.json" in str(error)

    # Test source property precedence
    error = SchemaFileError(
        "Schema error",
        schema_path="old.json",
        context={"source": "new.json"},
    )
    assert error.source == "new.json"
    assert "Source: new.json" in str(error)


def test_error_handler_output(caplog):
    """Test error handler output formatting."""
    with caplog.at_level(logging.DEBUG):
        try:
            handle_error(
                SchemaFileError(
                    "Invalid JSON",
                    schema_path="test.json",
                    context={"line": 10, "column": 5},
                )
            )
        except SystemExit:
            pass

    # Check debug log format
    assert "Error details:" in caplog.text
    assert "Type: SchemaFileError" in caplog.text

    # Check context formatting
    log_entry = caplog.records[-1].message
    assert "schema_path: test.json" in log_entry
    assert "line: 10" in log_entry
    assert "column: 5" in log_entry


def test_error_formatting():
    """Test error message formatting."""
    # Test basic error
    error = CLIError("Test error")
    error_str = str(error)
    assert "[INTERNAL_ERROR] Test error" in error_str

    # Test error with details
    error = CLIError(
        "Test error",
        details="Detailed explanation",
        context={"path": "/test/path"},
    )
    error_str = str(error)
    assert "Details: Detailed explanation" in error_str
    assert "Path: /test/path" in error_str

    # Test error with troubleshooting
    error = CLIError(
        "Test error",
        context={"troubleshooting": ["Check A", "Verify B"]},
    )
    error_str = str(error)
    assert "Troubleshooting:" in error_str
    assert "1. Check A" in error_str
    assert "2. Verify B" in error_str


def test_file_not_found_error_formatting():
    """Test OstructFileNotFoundError formatting."""
    error = OstructFileNotFoundError("/test/file.txt")
    error_str = str(error)

    # Check basic message
    assert "[FILE_ERROR] File not found: /test/file.txt" in error_str

    # Check details
    assert "Details: " in error_str
    assert "does not exist or cannot be accessed" in error_str

    # Check troubleshooting
    assert "Troubleshooting:" in error_str
    assert "1. Check if the file exists" in error_str
    assert "2. Verify the path spelling is correct" in error_str
    assert "3. Check file permissions" in error_str
    assert "4. Ensure parent directories exist" in error_str


def test_schema_file_error_formatting():
    """Test SchemaFileError message formatting."""
    error = SchemaFileError("Invalid JSON", schema_path="/test/schema.json")
    error_str = str(error)

    # Check basic message
    assert "[SCHEMA_ERROR] Invalid JSON" in error_str

    # Check source
    assert "Source: /test/schema.json" in error_str

    # Check details and troubleshooting
    assert "Details: " in error_str
    assert "could not be read or contains errors" in error_str
    assert "Troubleshooting:" in error_str
    assert "1. Verify the schema file exists" in error_str
    assert "2. Check if the schema file contains valid JSON" in error_str


def test_path_security_error_formatting():
    """Test PathSecurityError formatting."""
    # Test basic security error
    error = PathSecurityError("Access denied", path="/test/file.txt")
    error_str = str(error)

    # Check basic message
    assert "[SECURITY_ERROR] Access denied" in error_str

    # Check details
    assert "Details: " in error_str
    assert "violates security constraints" in error_str

    # Check troubleshooting
    assert "Troubleshooting:" in error_str
    assert "1. Check if the path is within allowed directories" in error_str

    # Test expanded paths error
    error = PathSecurityError.from_expanded_paths(
        original_path="/test/file.txt",
        expanded_path="/actual/path/file.txt",
        base_dir="/allowed/path",
        allowed_dirs=["/allowed/path", "/other/allowed"],
    )
    error_str = str(error)

    # Check expanded path details
    assert "Original Path: /test/file.txt" in error_str
    assert "Expanded Path: /actual/path/file.txt" in error_str
    assert "Base Directory: /allowed/path" in error_str
    assert (
        "Allowed Directories: ['/allowed/path', '/other/allowed']" in error_str
    )


def test_security_error_base():
    """Test SecurityErrorBase class."""
    error = SecurityErrorBase("Security violation")
    assert error.exit_code == ExitCode.SECURITY_ERROR
    assert error.context["category"] == "security"

    # Test with custom context
    error = SecurityErrorBase(
        "Custom security error", context={"custom_field": "value"}
    )
    assert error.context["custom_field"] == "value"
    assert error.context["category"] == "security"


def test_security_error_formatting():
    """Test security error message formatting."""
    error = PathSecurityError(
        "Access denied",
        path="/secret/file.txt",
        context={"allowed_dirs": ["/safe"], "user": "admin"},
    )
    error_str = str(error)

    # Check basic formatting
    assert "[SECURITY_ERROR] Access denied" in error_str
    assert "Path: /secret/file.txt" in error_str

    # Check context fields
    assert "Allowed Directories: ['/safe']" in error_str
    assert "User: admin" in error_str

    # Check troubleshooting
    assert "Troubleshooting:" in error_str
    assert "1. Check if the path is within allowed directories" in error_str


def test_error_wrapping():
    """Test error wrapping functionality."""
    # Create original error
    original = OstructFileNotFoundError("/missing.txt")

    # Wrap the error
    wrapped = PathSecurityError.wrap_error("Security check failed", original)

    # Check wrapped error
    error_str = str(wrapped)
    assert error_str.startswith("[SECURITY_ERROR] Security check failed")
    assert (
        "Original Message: [FILE_ERROR] File not found: /missing.txt"
        in error_str
    )
    assert "Wrapped Error: OstructFileNotFoundError" in error_str
    assert wrapped.context["wrapped_error"] == "OstructFileNotFoundError"
    assert wrapped.wrapped is True


def test_expanded_paths_error():
    """Test PathSecurityError with expanded paths."""
    error = PathSecurityError.from_expanded_paths(
        original_path="~/file.txt",
        expanded_path="/home/user/file.txt",
        base_dir="/allowed",
        allowed_dirs=["/allowed", "/also-allowed"],
        error_logged=True,
    )

    error_str = str(error)

    # Check basic message
    assert "Access denied" in error_str
    assert "~/file.txt" in error_str
    assert "/home/user/file.txt" in error_str

    # Check context
    assert error.context["original_path"] == "~/file.txt"
    assert error.context["expanded_path"] == "/home/user/file.txt"
    assert error.context["base_dir"] == "/allowed"
    assert error.context["allowed_dirs"] == ["/allowed", "/also-allowed"]
    assert error.context["reason"] == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED

    # Check troubleshooting
    assert "Troubleshooting:" in error_str
    assert "within base directory: /allowed" in error_str
    assert "Current allowed directories: /allowed, /also-allowed" in error_str


def test_cli_error_context():
    """Test CLIError context handling."""
    error = CLIError(
        "Test error",
        context={"custom_field": "value"},
        details="Detailed explanation",
    )

    # Check standard fields
    assert "timestamp" in error.context
    assert "host" in error.context
    assert "version" in error.context
    assert "python_version" in error.context

    # Check custom fields
    assert error.context["custom_field"] == "value"
    assert error.context["details"] == "Detailed explanation"

    # Verify string representation
    error_str = str(error)
    assert "[INTERNAL_ERROR] Test error" in error_str
    assert "Details: Detailed explanation" in error_str
    assert "Custom Field: value" in error_str


def test_security_error_expanded_paths(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test security error with expanded paths in error message."""
    # Create error with expanded paths
    error = PathSecurityError.from_expanded_paths(
        original_path="~/test.txt",
        expanded_path="/home/user/test.txt",
        base_dir="/test_workspace",
        allowed_dirs=["/allowed"],
        error_logged=True,
    )

    error_str = str(error)
    # Check basic message format
    assert error_str.startswith("[SECURITY_ERROR] Access denied")
    # Check path information
    assert "Original Path: ~/test.txt" in error_str
    assert "Expanded Path: /home/user/test.txt" in error_str
    assert "Base Directory: /test_workspace" in error_str
    assert "Allowed Directories: ['/allowed']" in error_str


def test_security_error_format_with_context() -> None:
    """Test formatting security error with additional context."""
    # Create error with context
    error = PathSecurityError(
        "Access denied",
        path="/test.txt",
        context={
            "original_path": "~/test.txt",
            "expanded_path": "/test.txt",
            "base_dir": "/base",
            "allowed_dirs": ["/allowed"],
        },
        error_logged=True,
    )

    error_str = str(error)
    # Check basic message format
    assert error_str.startswith("[SECURITY_ERROR] Access denied")
    # Check context information
    assert "Original Path: ~/test.txt" in error_str
    assert "Expanded Path: /test.txt" in error_str
    assert "Base Directory: /base" in error_str
    assert "Allowed Directories: ['/allowed']" in error_str


def test_security_error_attributes() -> None:
    """Test PathSecurityError attributes and properties."""
    error = PathSecurityError(
        "Access denied", path="/test/path", error_logged=True
    )
    assert error.error_logged
    assert not error.wrapped
    error_str = str(error)
    assert error_str.startswith("[SECURITY_ERROR] Access denied")
    assert "Path: /test/path" in error_str
    assert "Category: security" in error_str


def test_security_error_wrapping() -> None:
    """Test error wrapping with context preservation."""
    original = PathSecurityError("Access denied", error_logged=True)
    wrapped = PathSecurityError.wrap_error("File collection failed", original)
    assert wrapped.error_logged  # Should preserve logged state
    assert wrapped.wrapped  # Should be marked as wrapped


def test_file_info_immutability(
    fs: FakeFilesystem, security_manager: MockSecurityManager
) -> None:
    """Test that FileInfo attributes are immutable."""
    # Create test file
    fs.create_file("/test_workspace/base/test.txt", contents="test")
    os.chdir("/test_workspace/base")  # Change to base directory

    # Create FileInfo instance
    file_info = FileInfo.from_path(
        "test.txt", security_manager=security_manager
    )

    # Attempt to modify private fields should raise AttributeError
    with pytest.raises(AttributeError):
        file_info.__path = "modified.txt"

    with pytest.raises(AttributeError):
        file_info.__content = "modified content"

    with pytest.raises(AttributeError):
        file_info.__security_manager = security_manager


@pytest.mark.error_test
def test_collect_files_security_error_propagates(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test security errors propagate from directory collection."""
    fs.create_file("/test_workspace/base/valid.txt")
    fs.create_symlink("/test_workspace/base/malicious", "../outside.txt")
    os.chdir("/test_workspace/base")

    # Test should now pass with the fixed error propagation
    with pytest.raises(PathSecurityError) as exc_info:
        collect_files_from_directory(".", security_manager=security_manager)

    assert "Symlink security violation:" in str(exc_info.value)
    assert "target not allowed" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )


@pytest.mark.error_test
def test_collect_files_security_violations(
    fs: FakeFilesystem,
    security_manager: MockSecurityManager,
) -> None:
    """Test various security violation scenarios in file collection.

    EXPECTED ERROR: This test verifies that symlink-based security violations
    raise appropriate PathSecurityError with detailed context.
    """
    # Setup
    fs.create_file("/test_workspace/base/valid.txt")
    fs.create_dir("/test_workspace/outside")
    fs.create_file("/test_workspace/outside/target.txt")
    os.chdir("/test_workspace/base")

    # Test 1: Symlink to non-existent file outside allowed dirs
    fs.create_symlink(
        "/test_workspace/base/bad_link1", "../outside/nonexistent.txt"
    )
    with pytest.raises(PathSecurityError) as exc_info:
        collect_files_from_directory(".", security_manager=security_manager)

    assert "Symlink security violation:" in str(exc_info.value)
    assert "target not allowed" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )

    # Test 2: Symlink to existing file outside allowed dirs
    fs.create_symlink(
        "/test_workspace/base/bad_link2", "../outside/target.txt"
    )
    with pytest.raises(PathSecurityError) as exc_info:
        collect_files_from_directory(".", security_manager=security_manager)

    assert "Symlink security violation:" in str(exc_info.value)
    assert "target not allowed" in str(exc_info.value)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )

    # Test 3: Directory traversal attempt
    fs.create_symlink("/test_workspace/base/bad_link3", "../../etc/passwd")
    with pytest.raises(PathSecurityError) as exc_info:
        collect_files_from_directory(".", security_manager=security_manager)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED
    )
    assert "Symlink security violation" in str(exc_info.value)


class PathTestData(TypedDict):
    name: str
    task_file: str
    expected_error: Type[Exception]
    expected_msg: str


@pytest.mark.error_test
def test_template_path_errors(
    fs: FakeFilesystem, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that template path errors surface proper error messages."""
    # Setup test workspace
    fs.create_dir("/test_workspace")
    fs.create_dir("/test_workspace/base")
    fs.create_file("/test_workspace/base/valid.txt", contents="test")
    os.chdir("/test_workspace/base")

    # Create security manager with base directory
    security_manager = MockSecurityManager(base_dir="/test_workspace/base")

    # Test case 1: Non-existent file
    with pytest.raises(OstructFileNotFoundError) as exc_info:
        validate_path_mapping(
            "template=missing.txt", security_manager=security_manager
        )
    error_str = str(exc_info.value)
    assert "[FILE_ERROR] File not found: missing.txt" in error_str
    assert "Details: The specified file does not exist" in error_str
    assert "Troubleshooting:" in error_str
    assert "1. Check if the file exists" in error_str
    assert "2. Verify the path spelling is correct" in error_str
    assert "3. Check file permissions" in error_str
    assert "4. Ensure parent directories exist" in error_str

    # Test case 2: File outside allowed directories
    with pytest.raises(PathSecurityError) as security_exc_info:
        validate_path_mapping(
            "template=/etc/passwd", security_manager=security_manager
        )
    error_str = str(security_exc_info.value)
    assert (
        "[SECURITY_ERROR] Access denied: passwd is outside base directory and not in allowed directories"
        in error_str
    )
    assert "Base Directory:" in error_str
    assert "Allowed Directories:" in error_str
    assert "/etc/passwd" in error_str
    assert "Category: security" in error_str
    assert (
        security_exc_info.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )
