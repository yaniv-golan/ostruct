"""Tests for task template utilities."""

import os
from typing import Any, Dict, Generator, List, TypedDict, Union, cast

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_filesystem_unittest import Patcher

from ostruct.cli.errors import TemplateValidationError
from ostruct.cli.file_utils import FileInfo
from ostruct.cli.security import SecurityManager
from ostruct.cli.template_utils import render_template
from ostruct.cli.template_validation import validate_template_placeholders


class ConfigDict(TypedDict, total=False):
    debug: bool
    settings: Dict[str, str]
    exclude: Dict[str, str]


class FileMapping(TypedDict, total=False):
    name: str
    config: ConfigDict
    file: FileInfo
    source_files: List[FileInfo]
    items: List[Dict[str, str]]
    condition: bool
    defined_var: str
    text: str
    data: Dict[str, Union[str, int]]


def test_render_task_template_basic() -> None:
    """Test basic task template rendering."""
    template = "Hello {{ name }}!"
    context: Dict[str, str] = {"name": "World"}
    result = render_template(template, context)
    assert result == "Hello World!"


def test_render_task_template_missing_var() -> None:
    """Test task template rendering with missing variable."""
    template = "Hello {{ name }}!"
    context: Dict[str, Any] = {}
    with pytest.raises(TemplateValidationError) as exc:
        render_template(template, context)
    assert "'name' is undefined" in str(exc.value)


def test_validate_task_template_basic() -> None:
    """Test basic task template validation."""
    template = "Hello {{ name }}!"
    file_mappings: Dict[str, Any] = {"name": "test"}  # Simple value
    validate_template_placeholders(template, file_mappings)


def test_validate_task_template_missing_var() -> None:
    """Test task template validation with missing variable."""
    template = "Hello {{ name }}!"
    file_mappings: Dict[str, Any] = {}  # Empty dict instead of set()
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_placeholders(template, file_mappings)
    assert "undefined variable" in str(exc.value)


def test_validate_task_template_invalid_syntax() -> None:
    """Test task template validation with invalid syntax."""
    template = "Hello {{ name!"  # Missing closing brace
    file_mappings: Dict[str, Any] = {"name": "test"}
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_placeholders(template, file_mappings)
    assert "Invalid task template syntax" in str(exc.value)


@pytest.fixture  # type: ignore[misc]
def fs() -> Generator[FakeFilesystem, None, None]:
    """Fixture to set up fake filesystem."""
    with Patcher() as patcher:
        fs = patcher.fs
        assert fs is not None  # Type assertion for mypy
        # Create test files and directories
        fs.create_file("/path/to/file.txt", contents="Test file content")
        fs.create_file(
            "/absolute/path/to/file.txt", contents="Test file content"
        )
        yield fs


@pytest.fixture  # type: ignore[misc]
def security_manager() -> SecurityManager:
    """Create a security manager for testing."""
    return SecurityManager(base_dir=os.getcwd())


def test_validate_fileinfo_attributes(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test validation of FileInfo attribute access."""
    fs.create_dir("/test1")
    fs.create_file("/test1/file.txt", contents="test content")
    template = "Content: {{ file.content }}, Path: {{ file.abs_path }}"
    file_info = FileInfo.from_path(
        path="/test1/file.txt", security_manager=security_manager
    )
    file_mappings = {"file": file_info}
    validate_template_placeholders(template, file_mappings)
    assert file_info.content == "test content"
    assert os.path.basename(file_info.abs_path) == "file.txt"


def test_validate_fileinfo_invalid_attribute(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test validation with invalid FileInfo attribute."""
    fs.create_dir("/test2")
    fs.create_file("/test2/file.txt", contents="test content")
    template = "{{ file.invalid_attr }}"
    file_info = FileInfo.from_path(
        path="/test2/file.txt", security_manager=security_manager
    )
    file_mappings = {"file": file_info}
    with pytest.raises(TemplateValidationError):
        validate_template_placeholders(template, file_mappings)
    assert file_info.content == "test content"


def test_validate_nested_json_access() -> None:
    """Test validation of nested JSON dictionary access."""
    template = "{{ config['debug'] }}, {{ config['settings']['mode'] }}"
    file_mappings = cast(
        Dict[str, Any],
        {"config": {"debug": True, "settings": {"mode": "test"}}},
    )
    validate_template_placeholders(template, file_mappings)


def test_validate_nested_json_invalid_key() -> None:
    """Test validation with invalid nested JSON key."""
    template = "{{ config['invalid_key'] }}"
    file_mappings = cast(Dict[str, Any], {"config": {"debug": True}})
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_placeholders(template, file_mappings)
    assert "undefined" in str(exc.value)


def test_validate_complex_template(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test validation of complex template with multiple features."""
    # Set up test files
    fs.create_file("/test/file1.txt", contents="File 1 content")
    fs.create_file("/test/file2.txt", contents="File 2 content")

    template = """
    {% for file in source_files %}
        File: {{ file.abs_path }}
        Content: {{ file.content }}
        {% if file.name in config.exclude %}
            Excluded: {{ config.exclude[file.name] }}
        {% endif %}
    {% endfor %}

    Settings:
    {% for key, value in config.settings.items() %}
        {{ key }}: {{ value }}
    {% endfor %}
    """
    file_mappings = cast(
        Dict[str, Any],
        {
            "source_files": [
                FileInfo.from_path(
                    path="/test/file1.txt", security_manager=security_manager
                ),
                FileInfo.from_path(
                    path="/test/file2.txt", security_manager=security_manager
                ),
            ],
            "config": {
                "exclude": {"file1.txt": "reason1"},
                "settings": {"mode": "test"},
            },
        },
    )
    validate_template_placeholders(template, file_mappings)
    assert file_mappings["source_files"][0].content == "File 1 content"
    assert file_mappings["source_files"][1].content == "File 2 content"


def test_validate_template_with_filters(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test validation of template using built-in filters and functions."""
    fs.create_file("/test/data.txt", contents="Test data content")

    template = """
    {% set content = file.content|trim %}
    {{ content|wordcount }}
    {{ content|extract_field("status")|frequency|dict_to_table }}
    """
    file_mappings = {
        "file": FileInfo.from_path(
            path="/test/data.txt", security_manager=security_manager
        )
    }
    validate_template_placeholders(template, file_mappings)
    assert file_mappings["file"].content == "Test data content"


def test_validate_template_undefined_in_loop() -> None:
    """Test validation catches undefined variables in loops."""
    template = """
    {% for item in items %}
        {{ item.undefined_var }}
    {% endfor %}
    """
    file_mappings: Dict[str, Any] = cast(
        Dict[str, Any], {"items": [{"name": "item1"}, {"name": "item2"}]}
    )
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_placeholders(template, file_mappings)
    assert "undefined" in str(exc.value)


def test_validate_template_conditional_vars() -> None:
    """Test validation with variables in conditional blocks."""
    template = """
    {% if condition %}
        {{ defined_var }}
    {% else %}
        {{ undefined_var }}
    {% endif %}
    """
    file_mappings: Dict[str, Any] = cast(
        Dict[str, Any], {"condition": True, "defined_var": "test"}
    )
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_placeholders(template, file_mappings)
    assert "undefined" in str(exc.value)


def test_validate_template_builtin_functions() -> None:
    """Test validation allows built-in Jinja2 functions and filters."""
    template = """
    {% set items = range(5) %}
    {% for i in items %}
        {{ loop.index }}: {{ i }}
    {% endfor %}
    {{ "text"|upper }}
    {{ lipsum(2) }}
    """
    file_mappings: Dict[str, Any] = {}  # No variables needed
    validate_template_placeholders(template, file_mappings)


def test_validate_template_custom_functions(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test validation allows custom template functions."""
    fs.create_file("/test/file.txt", contents="Test file content")
    fs.create_file("/test/data.json", contents='{"status": "active"}')

    template = """
    {{ file.content|extract_field("status") }}
    {{ data|pivot_table("category", "value", "mean") }}
    {{ text|format_code("python") }}
    """
    file_mappings: Dict[str, Any] = cast(
        Dict[str, Any],
        {
            "file": FileInfo.from_path(
                path="/test/file.txt", security_manager=security_manager
            ),
            "data": {"category": "test", "value": 1},
            "text": "print('hello')",
        },
    )
    validate_template_placeholders(template, file_mappings)
    assert file_mappings["file"].content == "Test file content"


def test_render_template_with_file_content(
    fs: FakeFilesystem, security_manager: SecurityManager
) -> None:
    """Test rendering template with actual file content."""
    fs.create_file("/test/input.txt", contents="Hello from file!")

    template = "Content: {{ file.content }}"
    file_info = FileInfo.from_path(
        path="/test/input.txt", security_manager=security_manager
    )
    result = render_template(template, {"file": file_info})
    assert result == "Content: Hello from file!"
    assert file_info.content == "Hello from file!"


def test_validate_json_variable_access() -> None:
    """Test validation of JSON variable access using both dot notation and dictionary syntax."""
    template = """
    Dot notation: {{ config.debug }}, {{ config.settings.mode }}
    Dict access: {{ config['debug'] }}, {{ config['settings']['mode'] }}
    Mixed: {{ config.settings['mode'] }}, {{ config['settings'].mode }}
    """
    file_mappings: Dict[str, Any] = cast(
        Dict[str, Any],
        {"config": {"debug": True, "settings": {"mode": "test"}}},
    )
    validate_template_placeholders(template, file_mappings)


def test_render_json_variable_access() -> None:
    """Test rendering with JSON variables using both access methods."""
    config: ConfigDict = {"debug": True, "settings": {"mode": "test"}}

    template = """
    Dot notation: {{ config.debug }}, {{ config.settings.mode }}
    Dict access: {{ config['debug'] }}, {{ config['settings']['mode'] }}
    Mixed: {{ config.settings['mode'] }}, {{ config['settings'].mode }}
    """

    result = render_template(template, {"config": config})
    assert "Dot notation: True, test" in result


def test_invalid_json_variable_access() -> None:
    """Test validation catches invalid JSON variable access."""
    template = "{{ config.invalid }}"
    file_mappings: Dict[str, ConfigDict] = {
        "config": {"debug": True, "settings": {"mode": "test"}}
    }
    with pytest.raises(TemplateValidationError) as exc:
        validate_template_placeholders(template, file_mappings)
    assert "undefined" in str(exc.value)
