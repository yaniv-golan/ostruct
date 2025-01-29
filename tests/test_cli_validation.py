"""Tests for CLI argument validation functions."""

import json
import os
from typing import Any, Dict, List, Literal, Type, Union, cast

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli import (
    validate_path_mapping,
    validate_schema_file,
    validate_task_template,
    validate_variable_mapping,
)
from ostruct.cli.errors import (
    DirectoryNotFoundError,
    FileNotFoundError,
    InvalidJSONError,
    PathSecurityError,
    TaskTemplateSyntaxError,
    TaskTemplateVariableError,
    VariableNameError,
    VariableValueError,
)
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_validation import (
    TemplateValidationError,
    validate_template_placeholders,
)


# Variable mapping tests
def test_validate_variable_mapping_basic() -> None:
    """Test basic variable mapping validation."""
    name, value = validate_variable_mapping("foo=bar")
    assert name == "foo"
    assert value == "bar"


@pytest.mark.parametrize(  # type: ignore[misc]
    "mapping,is_json,error_type",
    [
        ("=value", False, VariableNameError),  # Empty name
        ("invalid", False, VariableValueError),  # No equals sign
        ("=", True, VariableNameError),  # Empty name with JSON
        ("key={invalid}", True, InvalidJSONError),  # Invalid JSON
    ],
)
def test_validate_variable_mapping_errors(
    mapping: str, is_json: bool, error_type: Type[Exception]
) -> None:
    """Test various error cases for variable mapping."""
    with pytest.raises(error_type) as exc:
        validate_variable_mapping(mapping, is_json=is_json)
    # Only check that error message exists and is non-empty
    assert str(exc.value)


def test_validate_variable_mapping_json_basic() -> None:
    """Test basic JSON variable mapping."""
    name, value = validate_variable_mapping(
        'config={"debug": true}', is_json=True
    )
    assert name == "config"
    assert value == {"debug": True}


# Path mapping tests
def test_validate_path_mapping_file(fs: FakeFilesystem) -> None:
    """Test file path mapping validation."""
    fs.create_file("test.txt", contents="test")
    name, path = validate_path_mapping("test=test.txt")
    assert name == "test"
    assert path == "test.txt"


def test_validate_path_mapping_dir(fs: FakeFilesystem) -> None:
    """Test directory path mapping validation."""
    fs.create_dir("test_dir")
    name, path = validate_path_mapping("test=test_dir", is_dir=True)
    assert name == "test"
    assert path == "test_dir"


@pytest.mark.parametrize(  # type: ignore[misc]
    "mapping,is_dir,error_type",
    [
        (
            "test=nonexistent.txt",
            False,
            FileNotFoundError,
        ),  # Non-existent file
        (
            "test=nonexistent",
            True,
            DirectoryNotFoundError,
        ),  # Non-existent directory
    ],
)
def test_validate_path_mapping_not_found(
    mapping: str,
    is_dir: Union[Literal[True], Literal[False]],
    error_type: Type[Exception],
) -> None:
    """Test path mapping with non-existent paths."""
    with pytest.raises(error_type) as exc:
        validate_path_mapping(mapping, is_dir=is_dir)
    # Check that error message contains 'not found'
    assert "not found" in str(exc.value).lower()


def test_validate_path_mapping_wrong_type(fs: FakeFilesystem) -> None:
    """Test path mapping with wrong type (file vs directory)."""
    fs.create_file("test.txt", contents="test")
    fs.create_dir("test_dir")

    with pytest.raises(DirectoryNotFoundError) as exc:
        validate_path_mapping("test=test.txt", is_dir=True)
    assert "not a directory" in str(exc.value).lower()

    with pytest.raises(FileNotFoundError) as exc_file:
        validate_path_mapping("test=test_dir")
    assert "not a file" in str(exc_file.value).lower()


def test_validate_path_mapping_outside_base(fs: FakeFilesystem) -> None:
    """Test path mapping with path outside base directory."""
    fs.create_dir("/base")
    fs.create_file("/base/test.txt", contents="test")
    os.chdir("/base")
    fs.create_file("/outside.txt", contents="test")

    security_manager = SecurityManager(base_dir="/base")
    with pytest.raises(PathSecurityError) as exc:
        validate_path_mapping(
            "file=/outside.txt", security_manager=security_manager
        )
    assert "outside" in str(exc.value).lower()
    assert "base directory" in str(exc.value).lower()


# Task template tests
def test_validate_task_template_string() -> None:
    """Test task template string validation."""
    template = "Hello {{ name }}!"
    result = validate_task_template(template)
    assert result == template


def test_validate_task_template_file(fs: FakeFilesystem) -> None:
    """Test task template file validation."""
    template = "Hello {{ name }}!"
    fs.create_file("template.txt", contents=template)
    result = validate_task_template("@template.txt")
    assert result == template


@pytest.mark.parametrize(  # type: ignore[misc]
    "template,error_type",
    [
        ("Hello {{ name!", TaskTemplateSyntaxError),  # Invalid syntax
        ("@nonexistent.txt", TaskTemplateVariableError),  # Non-existent file
    ],
)
def test_validate_task_template_errors(
    template: str, error_type: Type[Exception]
) -> None:
    """Test task template validation errors."""
    with pytest.raises(error_type) as exc:
        validate_task_template(template)
    assert str(exc.value)  # Just verify error message exists


# Schema file tests
def test_validate_schema_file_basic(fs: FakeFilesystem) -> None:
    """Test basic schema file validation."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"],
    }
    fs.create_file("schema.json", contents=json.dumps(schema))
    result = validate_schema_file("schema.json")
    # Check essential properties instead of exact equality
    assert result["type"] == schema["type"]
    assert set(result["required"]) == set(schema["required"])
    assert "name" in result["properties"]
    assert "age" in result["properties"]


@pytest.mark.parametrize(  # type: ignore[misc]
    "content,error_type,error_parts",
    [
        # For JSON parsing errors, check for key error indicators
        (
            "{not valid json}",
            InvalidJSONError,
            ["property name", "double quotes"],
        ),
    ],
)
def test_validate_schema_file_errors(
    fs: FakeFilesystem,
    content: str,
    error_type: Type[Exception],
    error_parts: List[str],
) -> None:
    """Test schema file validation errors."""
    fs.create_file("schema.json", contents=content)
    with pytest.raises(error_type) as exc:
        validate_schema_file("schema.json")
    error_msg = str(exc.value).lower()
    for part in error_parts:
        assert (
            part.lower() in error_msg
        ), f"Expected '{part}' in error message: {error_msg}"


@pytest.mark.parametrize(  # type: ignore[misc]
    "template,file_mappings,error_phrase",
    [
        (
            "Hello {{ name }}!",
            cast(Dict[str, Any], {}),
            "undefined variables",
        ),  # Missing variable
        (
            "Hello {{ name!",
            cast(Dict[str, Any], {"name": "test"}),
            "syntax",
        ),  # Invalid syntax
        (
            "{% for item in items %}{{ item.undefined }}{% endfor %}",
            cast(Dict[str, Any], {"items": [{"name": "test"}]}),
            "items",
        ),  # Invalid loop variable
        (
            "{% if condition %}{{ undefined_var }}{% endif %}",
            cast(Dict[str, Any], {"condition": True}),
            "undefined variable",
        ),  # Undefined in conditional
        (
            "{{ undefined_var }}",
            cast(Dict[str, Any], {}),
            "undefined variable",
        ),  # Simple undefined variable
    ],
)
def test_validate_template_placeholders_errors(
    template: str, file_mappings: Dict[str, Any], error_phrase: str
) -> None:
    """Test validation error cases for template placeholders."""
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_placeholders(template, file_mappings)
    assert error_phrase in str(exc.value).lower()
