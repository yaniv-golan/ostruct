"""Centralized constants for ostruct CLI."""

from typing import Any, Dict


class DefaultPaths:
    """Default paths and directories for ostruct."""

    # Code Interpreter defaults
    CODE_INTERPRETER_OUTPUT_DIR = "./downloads"

    # Configuration file paths
    CONFIG_FILE_NAME = "ostruct.yaml"
    HOME_CONFIG_DIR = ".ostruct"
    HOME_CONFIG_FILE = "config.yaml"


class DefaultConfig:
    """Default configuration values for ostruct."""

    # Model defaults
    DEFAULT_MODEL: str = "gpt-4.1"

    # Code Interpreter defaults
    CODE_INTERPRETER: Dict[str, Any] = {
        "auto_download": True,
        "output_directory": DefaultPaths.CODE_INTERPRETER_OUTPUT_DIR,
        "download_strategy": "single_pass",
    }

    # File Search defaults
    FILE_SEARCH: Dict[str, Any] = {
        "max_results": 10,
    }

    # Web Search defaults
    WEB_SEARCH: Dict[str, Any] = {
        "enable_by_default": False,
        "search_context_size": None,
        "user_location": None,
    }

    # Operation defaults - individual values for direct access
    OPERATION_TIMEOUT_MINUTES: int = 60
    OPERATION_RETRY_ATTEMPTS: int = 3
    OPERATION_REQUIRE_APPROVAL: str = "never"

    # Limits defaults - individual values for direct access
    LIMITS_MAX_COST_PER_RUN: float = 10.00
    LIMITS_WARN_EXPENSIVE_OPERATIONS: bool = True

    # Template processing defaults
    TEMPLATE: Dict[str, Any] = {
        "system_prompt": "You are a helpful assistant.",
        "file_limit": 65536,  # 64KB
        "total_limit": 1048576,  # 1MB
        "preview_limit": 4096,  # 4KB
    }


class DefaultTimeouts:
    """Default timeout values."""

    API_TIMEOUT = 60.0
    MAX_API_TIMEOUT = 300.0  # 5 minutes cap


class DefaultSecurity:
    """Default security settings."""

    PATH_SECURITY_MODE = "permissive"
    VALID_SECURITY_MODES = ["permissive", "warn", "strict"]
    VALID_APPROVAL_SETTINGS = ["never", "always", "expensive"]


# Environment variable names (for consistency)
class EnvVars:
    """Environment variable names."""

    OPENAI_API_KEY = "OPENAI_API_KEY"
    OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS = (
        "OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS"
    )
    OSTRUCT_TEMPLATE_FILE_LIMIT = "OSTRUCT_TEMPLATE_FILE_LIMIT"
    OSTRUCT_TEMPLATE_TOTAL_LIMIT = "OSTRUCT_TEMPLATE_TOTAL_LIMIT"
    OSTRUCT_TEMPLATE_PREVIEW_LIMIT = "OSTRUCT_TEMPLATE_PREVIEW_LIMIT"

    # MCP URL pattern: OSTRUCT_MCP_URL_<name>
    MCP_URL_PREFIX = "OSTRUCT_MCP_URL_"
