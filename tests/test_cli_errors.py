"""Tests for CLI error handling."""

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.errors import (
    CLIError,
    DirectoryNotFoundError,
    FileNotFoundError,
    InvalidJSONError,
    PathSecurityError,
    SchemaError,
    SchemaFileError,
    SchemaValidationError,
    TaskTemplateError,
    TaskTemplateSyntaxError,
    TaskTemplateVariableError,
    VariableError,
    VariableNameError,
    VariableValueError,
)


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
    """Test FileNotFoundError."""
    error_msg = "test error"
    with pytest.raises(FileNotFoundError, match=error_msg):
        raise FileNotFoundError(error_msg)


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
    assert str(error) == error_msg


def test_variable_error_str() -> None:
    """Test VariableError string representation."""
    error_msg = "test error"
    error = VariableError(error_msg)
    assert str(error) == error_msg


def test_variable_name_error_str() -> None:
    """Test VariableNameError string representation."""
    error_msg = "test error"
    error = VariableNameError(error_msg)
    assert str(error) == error_msg


def test_variable_value_error_str() -> None:
    """Test VariableValueError string representation."""
    error_msg = "test error"
    error = VariableValueError(error_msg)
    assert str(error) == error_msg


def test_invalid_json_error() -> None:
    """Test InvalidJSONError."""
    error_msg = "test error"
    with pytest.raises(InvalidJSONError, match=error_msg):
        raise InvalidJSONError(error_msg)


def test_file_not_found_error_str() -> None:
    """Test FileNotFoundError string representation."""
    error_msg = "test error"
    error = FileNotFoundError(error_msg)
    assert str(error) == error_msg


def test_directory_not_found_error_str() -> None:
    """Test DirectoryNotFoundError string representation."""
    error_msg = "test error"
    error = DirectoryNotFoundError(error_msg)
    assert str(error) == error_msg


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
    assert str(error) == error_msg


def test_schema_validation_error_str() -> None:
    """Test SchemaValidationError string representation."""
    error_msg = "test error"
    error = SchemaValidationError(error_msg)
    assert str(error) == error_msg


def test_schema_file_error_with_base_dir() -> None:
    """Test SchemaFileError with base directory."""
    error_msg = "test error"
    with pytest.raises(SchemaFileError, match=error_msg):
        raise SchemaFileError(error_msg)
