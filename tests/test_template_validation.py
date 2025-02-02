"""Test template validation functionality."""

import os
import tempfile
from typing import Any, Dict, List, Set, TypedDict, Union, cast

import jinja2
import pytest
from jinja2 import Environment
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.errors import TemplateValidationError
from ostruct.cli.file_utils import FileInfo
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_rendering import render_template
from ostruct.cli.template_validation import (
    SafeUndefined,
    validate_template_placeholders,
)


@pytest.fixture  # type: ignore[misc]
def security_manager() -> SecurityManager:
    """Create a security manager for testing."""
    manager = SecurityManager()
    manager.add_allowed_directory(tempfile.gettempdir())
    return manager


class FileMapping(TypedDict, total=False):
    name: str
    dict: Dict[str, str]
    deep: Dict[str, Dict[str, Dict[str, str]]]
    content: str
    items: List[Dict[str, str]]
    condition: bool
    config: Dict[str, Union[Dict[str, str], Dict[str, Dict[str, str]]]]
    source_files: List[FileInfo]


@pytest.mark.parametrize(  # type: ignore[misc]
    "template,available_vars",
    [
        ("{{ any_dict.any_key }}", {"any_dict"}),  # Basic undefined access
        ("{{ nested.deep.key }}", {"nested"}),  # Nested key access
    ],
)
def test_safe_undefined(template: str, available_vars: Set[str]) -> None:
    """Test SafeUndefined behavior for various access patterns."""
    env = Environment(undefined=SafeUndefined)
    temp = env.from_string(template)
    with pytest.raises(jinja2.UndefinedError):
        temp.render()


@pytest.mark.parametrize(  # type: ignore[misc]
    "template,file_mappings,should_pass",
    [
        (
            "Hello {{ name }}!",
            cast(Dict[str, Any], {"name": "test"}),
            True,
        ),  # Basic variable
        (
            "{{ dict.key }}",
            cast(Dict[str, Any], {"dict": {"key": "value"}}),
            True,
        ),  # Nested access
        (
            "{{ deep.nested.key }}",
            cast(Dict[str, Any], {"deep": {"nested": {"key": "value"}}}),
            True,
        ),  # Deep nested access
        (
            "{{ content | trim | upper }}",
            cast(Dict[str, Any], {"content": "test"}),
            True,
        ),  # Multiple filters
        (
            "{% for item in items %}{{ item.name }}{% endfor %}",
            cast(Dict[str, Any], {"items": [{"name": "test"}]}),
            True,
        ),  # Loop variable
    ],
)
def test_validate_template_success(
    template: str, file_mappings: Dict[str, Any], should_pass: bool
) -> None:
    """Test successful template validation cases."""
    validate_template_placeholders(template, file_mappings)


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
def test_validate_template_errors(
    template: str, file_mappings: Dict[str, Any], error_phrase: str
) -> None:
    """Test template validation error cases."""
    with pytest.raises(TemplateValidationError) as excinfo:
        validate_template_placeholders(template, file_mappings)
    assert error_phrase in str(excinfo.value).lower()


def test_validate_with_filters() -> None:
    """Test validation with template filters."""
    template = """
    {{ content | trim | upper }}
    {{ data | extract_field("status") | frequency | dict_to_table }}
    """
    file_mappings: Dict[str, Any] = {
        "content": "test",
        "data": [{"status": "active"}],
    }
    validate_template_placeholders(template, file_mappings)


def test_validate_fileinfo_attributes(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test validation of FileInfo attribute access."""
    # Create test file in fake filesystem
    fs.create_file("/test_workspace/test_file.txt", contents="test content")

    template = "Content: {{ file.content }}, Path: {{ file.abs_path }}"
    file_info = FileInfo.from_path(
        path="/test_workspace/test_file.txt", security_manager=security_manager
    )
    file_mappings: Dict[str, Any] = {"file": file_info}
    validate_template_placeholders(template, file_mappings)


def create_test_file(
    fs: FakeFilesystem, filename: str, security_manager: SecurityManager
) -> FileInfo:
    """Create a test file and return FileInfo instance."""
    full_path = os.path.join("/test_workspace", filename)
    fs.create_file(full_path, contents="test content")
    return FileInfo.from_path(path=full_path, security_manager=security_manager)


@pytest.mark.parametrize(  # type: ignore[misc]
    "template,context_setup",
    [
        (
            "{{ file.invalid_attr }}",
            lambda fs, sm: {"file": create_test_file(fs, "test.txt", sm)},
        ),  # Invalid FileInfo attribute
        (
            "{{ config['invalid'] }}",
            lambda _, __: {"config": {}},
        ),  # Invalid dict key
        (
            "{{ config.settings.invalid }}",
            lambda _, __: {"config": {"settings": {}}},
        ),  # Invalid nested dict key
    ],
)
def test_validate_invalid_access(
    template: str,
    context_setup: Any,
    fs: FakeFilesystem,
    security_manager: SecurityManager,
) -> None:
    """Test validation with invalid attribute/key access."""
    file_mappings = context_setup(fs, security_manager)
    with pytest.raises(TemplateValidationError):
        validate_template_placeholders(template, file_mappings)


def test_validate_complex_template(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test validation of complex template with multiple features."""
    # Set up fake filesystem
    fs.create_file("/test_workspace/file1.txt", contents="content1")
    fs.create_file("/test_workspace/file2.txt", contents="content2")

    template = """
    {% for file in source_files %}
        File: {{ file.abs_path }}
        Content: {{ file.content }}
        {% if file.name in config['exclude'] %}
            Excluded: {{ config['exclude'][file.name] }}
        {% endif %}
    {% endfor %}

    Settings:
    {% for key, value in config['settings'].items() %}
        {{ key }}: {{ value }}
    {% endfor %}
    """
    file_mappings: Dict[str, Any] = {
        "source_files": [
            FileInfo.from_path(
                path="/test_workspace/file1.txt", security_manager=security_manager
            ),
            FileInfo.from_path(
                path="/test_workspace/file2.txt", security_manager=security_manager
            ),
        ],
        "config": {
            "exclude": {"file1.txt": "reason1"},
            "settings": {"mode": "test"},
        },
    }
    validate_template_placeholders(template, file_mappings)


def test_validate_template_placeholders_invalid_json() -> None:
    """Test that validate_template_placeholders raises TemplateValidationError for invalid JSON access."""
    with pytest.raises(TemplateValidationError) as excinfo:
        validate_template_placeholders(
            "{{ invalid_json.some_key }}", {"invalid_json": "not json"}
        )
    assert "undefined" in str(excinfo.value).lower()


def test_comment_block_variables_ignored() -> None:
    """Test that variables inside comment blocks are ignored during validation and rendering."""
    # Template with variables inside a comment block
    template = """
    {% comment %}
    This template uses these variables:
    - {{ undefined_var }}
    - {{ another_missing_var.attribute }}
    {% endcomment %}

    Actual content: {{ real_var }}
    """

    # Context only has the variables used outside comments
    context = {"real_var": "Hello World"}

    # Should not raise any validation errors for undefined variables in comments
    validate_template_placeholders(template, context)

    # Should render without errors, stripping the comment
    result = render_template(template, context)

    # Check that the comment is removed and only real content remains
    assert "undefined_var" not in result
    assert "another_missing_var" not in result
    assert "Actual content: Hello World" in result.strip()


def test_comment_block_with_real_undefined_vars() -> None:
    """Test that we catch undefined variables outside comments while ignoring those inside comments."""
    # Template with variables both inside comments and outside
    template = """
    {% comment %}
    This template uses these variables:
    - {{ commented_undefined_var }}
    - {{ another_commented_var.attribute }}
    {% endcomment %}

    Real content with {{ real_var }} and {{ undefined_real_var }}
    """

    # Context only has some of the real variables
    context = {"real_var": "Hello World"}

    # Should raise validation error only for undefined_real_var
    with pytest.raises(TemplateValidationError) as excinfo:
        validate_template_placeholders(template, context)

    # Error should mention the real undefined variable but not the commented ones
    assert "undefined_real_var" in str(excinfo.value)
    assert "commented_undefined_var" not in str(excinfo.value)
    assert "another_commented_var" not in str(excinfo.value)


def test_validate_template_placeholders_with_invalid_placeholders() -> None:
    """Test that validate_template_placeholders raises TemplateValidationError for invalid placeholders."""
    with pytest.raises(TemplateValidationError):
        validate_template_placeholders("{{ undefined_var }}")


def test_validate_template_placeholders_with_valid_placeholders() -> None:
    """Test that validate_template_placeholders accepts valid placeholders."""
    validate_template_placeholders("{{ name }}", {"name": "test"})


def test_validate_template_errors_with_placeholders() -> None:
    """Test validation of template placeholders with various error conditions."""
    with pytest.raises(TemplateValidationError):
        validate_template_placeholders("{{ undefined_var }}")
