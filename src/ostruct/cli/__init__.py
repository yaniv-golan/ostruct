"""Command-line interface for making structured OpenAI API calls."""

from .cli import (
    ExitCode,
    _main,
    validate_schema_file,
    validate_task_template,
    validate_variable_mapping,
)
from .path_utils import validate_path_mapping

__all__ = [
    "ExitCode",
    "_main",
    "validate_path_mapping",
    "validate_schema_file",
    "validate_task_template",
    "validate_variable_mapping",
]
