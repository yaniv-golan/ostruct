"""Tests for CLI argument validation functions."""

import json
from typing import Any, Dict, List, Literal, Optional, Type, Union, cast

import pytest
from ostruct.cli import (
    validate_path_mapping,
    validate_schema_file,
    validate_task_template,
    validate_variable_mapping,
)
from ostruct.cli.errors import (
    DirectoryNotFoundError,
    InvalidJSONError,
    OstructFileNotFoundError,
    SchemaValidationError,
    TaskTemplateError,
    TaskTemplateSyntaxError,
    TaskTemplateVariableError,
    VariableNameError,
    VariableValueError,
)
from ostruct.cli.schema_validation import validate_openai_schema
from ostruct.cli.template_validation import validate_template_placeholders
from pyfakefs.fake_filesystem import FakeFilesystem


# Variable mapping tests
def test_validate_variable_mapping_basic() -> None:
    """Test basic variable mapping validation."""
    name, value = validate_variable_mapping("foo=bar")
    assert name == "foo"
    assert value == "bar"


@pytest.mark.parametrize(
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


@pytest.mark.parametrize(
    "mapping,is_dir,error_type",
    [
        (
            "test=nonexistent.txt",
            False,
            OstructFileNotFoundError,
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

    with pytest.raises(OstructFileNotFoundError) as exc_file:
        validate_path_mapping("test=test_dir")
    assert "not a file" in str(exc_file.value).lower()


# Task template tests
def test_validate_task_template_string() -> None:
    """Test task template string validation."""
    template = "Hello {{ name }}!"
    result = validate_task_template(template, None)
    assert result == template


def test_validate_task_template_file(fs: FakeFilesystem) -> None:
    """Test task template file validation."""
    template = "Hello {{ name }}!"
    fs.create_file("template.txt", contents=template)
    result = validate_task_template(None, "template.txt")
    assert result == template


def test_validate_task_template_missing_both() -> None:
    """Test error when neither string nor file is provided."""
    with pytest.raises(TaskTemplateVariableError) as exc:
        validate_task_template(None, None)
    assert "Must specify either" in str(exc.value)


def test_validate_task_template_both_provided(fs: FakeFilesystem) -> None:
    """Test error when both string and file are provided."""
    fs.create_file("template.txt", contents="Hello {{ name }}!")
    with pytest.raises(TaskTemplateVariableError) as exc:
        validate_task_template("direct template", "template.txt")
    assert "Cannot specify both" in str(exc.value)


@pytest.mark.parametrize(
    "template,error_type",
    [
        ("Hello {{ name!", TaskTemplateSyntaxError),  # Invalid syntax
        (
            None,
            TaskTemplateVariableError,
        ),  # Non-existent file with task_file="nonexistent.txt"
    ],
)
def test_validate_task_template_errors(
    template: Optional[str], error_type: Type[Exception]
) -> None:
    """Test task template validation errors."""
    with pytest.raises(error_type) as exc:
        if template is None:
            validate_task_template(None, "nonexistent.txt")
        else:
            validate_task_template(template, None)
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


@pytest.mark.parametrize(
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


@pytest.mark.parametrize(
    "template,file_mappings,error_phrase",
    [
        (
            "Hello {{ name }}!",
            cast(Dict[str, Any], {}),
            "missing required template variable(s): name",
        ),  # Missing variable
        (
            "Hello {{ name!",
            cast(Dict[str, Any], {"name": "test"}),
            "syntax",
        ),  # Invalid syntax
        (
            "{% for item in items %}{{ item.undefined }}{% endfor %}",
            cast(Dict[str, Any], {"items": [{"name": "test"}]}),
            "task template uses undefined attribute 'items[0].undefined'",
        ),  # Invalid loop variable
        (
            "{% if condition %}{{ undefined_var }}{% endif %}",
            cast(Dict[str, Any], {"condition": True}),
            "missing required template variable(s): undefined_var",
        ),  # Undefined in conditional
        (
            "{{ undefined_var }}",
            cast(Dict[str, Any], {}),
            "missing required template variable(s): undefined_var",
        ),  # Simple undefined variable
    ],
)
def test_validate_template_placeholders_errors(
    template: str, file_mappings: Dict[str, Any], error_phrase: str
) -> None:
    """Test template validation error cases."""
    with pytest.raises(TaskTemplateError) as exc:
        validate_template_placeholders(template, file_mappings)
    assert error_phrase in str(exc.value).lower()


def test_validate_array_root_schema() -> None:
    """Test that array root schemas are properly rejected."""
    array_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The person's full name",
                },
                "age": {"type": "integer", "description": "The person's age"},
                "occupation": {
                    "type": "string",
                    "description": "The person's job or profession",
                },
            },
            "required": ["name", "age", "occupation"],
        },
    }

    with pytest.raises(SchemaValidationError) as exc:
        validate_openai_schema(array_schema)

    error_msg = str(exc.value)
    assert "Root schema must be type 'object'" in error_msg
    assert "Found: array" in error_msg
    assert "The root of your schema must be an object type" in error_msg
    assert "wrap it in an object property" in error_msg
    assert "Example schema" in error_msg
