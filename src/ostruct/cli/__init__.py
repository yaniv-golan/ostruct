"""Command-line interface for making structured OpenAI API calls."""

# Import modules for test mocking support
from . import (
    config,
    mcp_integration,
    model_validation,
    runner,
)
from .cli import (
    ExitCode,
    create_cli,
    main,
)
from .path_utils import validate_path_mapping
from .registry_updates import get_update_notification
from .runner import OstructRunner
from .template_processor import validate_task_template
from .validators import (
    validate_schema_file,
    validate_variable_mapping,
)

__all__ = [
    "ExitCode",
    "main",
    "create_cli",
    "validate_path_mapping",
    "validate_schema_file",
    "validate_task_template",
    "validate_variable_mapping",
    "get_update_notification",
    "OstructRunner",
    # Modules for test mocking
    "config",
    "mcp_integration",
    "model_validation",
    "runner",
]
