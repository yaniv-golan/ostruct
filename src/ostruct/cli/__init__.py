"""Command-line interface for making structured OpenAI API calls."""

from .cli import (
    ExitCode,
    main,
    validate_schema_file,
    validate_task_template,
    validate_variable_mapping,
)
from .path_utils import validate_path_mapping
from .registry_updates import get_update_notification

__all__ = [
    "ExitCode",
    "main",
    "validate_path_mapping",
    "validate_schema_file",
    "validate_task_template",
    "validate_variable_mapping",
    "get_update_notification",
]
