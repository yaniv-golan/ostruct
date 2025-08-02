"""Centralized constants for ostruct CLI."""

from typing import Any, Dict


class DefaultPaths:
    """Default paths and directories for ostruct."""

    # Code Interpreter defaults
    CODE_INTERPRETER_OUTPUT_DIR = "./downloads"

    # User-data upload limits
    USER_DATA_FILE_LIMIT_BYTES = 512 * 1024 * 1024  # 512 MB
    USER_DATA_LARGE_WARNING_BYTES = 50 * 1024 * 1024  # 50 MB

    # Configuration file paths
    CONFIG_FILE_NAME = "ostruct.yaml"
    HOME_CONFIG_DIR = ".ostruct"
    HOME_CONFIG_FILE = "config.yaml"


class DefaultConfig:
    """Default configuration values for ostruct."""

    # Model defaults
    DEFAULT_MODEL: str = "gpt-4.1"

    # JSON parsing defaults
    JSON_PARSING_STRATEGY: str = (
        "robust"  # Enable duplication handling by default
    )

    # Code Interpreter defaults
    CODE_INTERPRETER: Dict[str, Any] = {
        "auto_download": False,  # Changed from True - new default optimizes for computation over file downloads
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

    # User-data upload limits (surfaced for other modules)
    USER_DATA_FILE_LIMIT_BYTES: int = DefaultPaths.USER_DATA_FILE_LIMIT_BYTES
    USER_DATA_LARGE_WARNING_BYTES: int = (
        DefaultPaths.USER_DATA_LARGE_WARNING_BYTES
    )

    # Template processing defaults
    TEMPLATE: Dict[str, Any] = {
        "system_prompt": "You are a helpful assistant.",
        "max_file_size": 100 * 1024 * 1024,  # 100MB default limit (was None)
        "max_total_size": 500 * 1024 * 1024,  # 500MB total limit (was None)
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
    OSTRUCT_JSON_PARSING_STRATEGY = "OSTRUCT_JSON_PARSING_STRATEGY"

    # MCP URL pattern: OSTRUCT_MCP_URL_<name>
    MCP_URL_PREFIX = "OSTRUCT_MCP_URL_"
