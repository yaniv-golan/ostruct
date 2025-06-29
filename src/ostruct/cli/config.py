"""Configuration management for ostruct CLI."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from .constants import DefaultConfig, DefaultSecurity

logger = logging.getLogger(__name__)


class WebSearchUserLocationConfig(BaseModel):
    """Configuration for web search user location."""

    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None


class WebSearchToolConfig(BaseModel):
    """Configuration for web search tool settings."""

    enable_by_default: bool = False
    user_location: Optional[WebSearchUserLocationConfig] = None
    search_context_size: Optional[str] = Field(default=None)

    @field_validator("search_context_size")
    @classmethod
    def validate_search_context_size(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["low", "medium", "high"]:
            raise ValueError(
                "search_context_size must be one of: low, medium, high"
            )
        return v


class FileCollectionConfig(BaseModel):
    """Configuration for file collection behavior."""

    ignore_gitignore: bool = False
    gitignore_file: Optional[str] = None
    gitignore_patterns: list[str] = Field(default_factory=list)

    @field_validator("gitignore_file")
    @classmethod
    def validate_gitignore_file(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not Path(v).exists():
            logger.warning(f"Gitignore file not found: {v}")
        return v


class ToolsConfig(BaseModel):
    """Configuration for tool-specific settings."""

    code_interpreter: Dict[str, Any] = Field(
        default_factory=lambda: DefaultConfig.CODE_INTERPRETER.copy()
    )
    file_search: Dict[str, Any] = Field(
        default_factory=lambda: DefaultConfig.FILE_SEARCH.copy()
    )
    web_search: WebSearchToolConfig = Field(
        default_factory=WebSearchToolConfig
    )


class ModelsConfig(BaseModel):
    """Configuration for model settings."""

    default: str = DefaultConfig.DEFAULT_MODEL


class OperationConfig(BaseModel):
    """Configuration for operation settings."""

    timeout_minutes: int = DefaultConfig.OPERATION_TIMEOUT_MINUTES
    retry_attempts: int = DefaultConfig.OPERATION_RETRY_ATTEMPTS
    require_approval: str = DefaultConfig.OPERATION_REQUIRE_APPROVAL

    @field_validator("require_approval")
    @classmethod
    def validate_approval_setting(cls, v: str) -> str:
        if v not in DefaultSecurity.VALID_APPROVAL_SETTINGS:
            raise ValueError(
                f"require_approval must be one of {DefaultSecurity.VALID_APPROVAL_SETTINGS}"
            )
        return v


class LimitsConfig(BaseModel):
    """Configuration for cost and operation limits."""

    max_cost_per_run: float = DefaultConfig.LIMITS_MAX_COST_PER_RUN
    warn_expensive_operations: bool = (
        DefaultConfig.LIMITS_WARN_EXPENSIVE_OPERATIONS
    )


class OstructConfig(BaseModel):
    """Main configuration class for ostruct."""

    models: ModelsConfig = Field(default_factory=ModelsConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    file_collection: FileCollectionConfig = Field(
        default_factory=FileCollectionConfig
    )
    mcp: Dict[str, str] = Field(default_factory=dict)
    operation: OperationConfig = Field(default_factory=OperationConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)

    @model_validator(mode="before")
    @classmethod
    def _validate_download_strategy(cls, values: Any) -> Any:
        """Validate download_strategy in code_interpreter config."""
        if isinstance(values, dict):
            tools_config = values.get("tools", {})
            if isinstance(tools_config, dict):
                ci_config = tools_config.get("code_interpreter", {})
                if isinstance(ci_config, dict):
                    strategy = ci_config.get(
                        "download_strategy", "single_pass"
                    )
                    if strategy not in {"single_pass", "two_pass_sentinel"}:
                        raise ValueError(
                            "download_strategy must be 'single_pass' or 'two_pass_sentinel'"
                        )
        return values

    @classmethod
    def load(
        cls, config_path: Optional[Union[str, Path]] = None
    ) -> "OstructConfig":
        """Load configuration from YAML file with smart defaults.

        Args:
            config_path: Path to configuration file. If None, looks for ostruct.yaml
                        in current directory, then user's home directory.

        Returns:
            OstructConfig instance with loaded settings and defaults.
        """
        config_data: Dict[str, Any] = {}

        # Determine config file path
        if config_path is None:
            # Look for ostruct.yaml in current directory first
            current_config = Path("ostruct.yaml")
            home_config = Path.home() / ".ostruct" / "config.yaml"

            if current_config.exists():
                config_path = current_config
            elif home_config.exists():
                config_path = home_config
            else:
                # No config file found, use defaults
                logger.info("No configuration file found, using defaults")
                return cls()
        else:
            config_path = Path(config_path)

        # Load configuration file if it exists
        if config_path and config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to load configuration from {config_path}: {e}"
                )
                logger.info("Using default configuration")
                config_data = {}

        # Apply environment variable overrides for secrets
        config_data = cls._apply_env_overrides(config_data)

        return cls(**config_data)

    @staticmethod
    def _apply_env_overrides(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides for sensitive settings."""

        # Model configuration from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            # Environment variable exists, configuration valid
            pass

        # MCP server URLs from environment
        mcp_config = config_data.setdefault("mcp", {})

        # Look for OSTRUCT_MCP_URL_* environment variables
        for key, value in os.environ.items():
            if key.startswith("OSTRUCT_MCP_URL_"):
                server_name = key[
                    16:
                ].lower()  # Remove OSTRUCT_MCP_URL_ prefix
                mcp_config[server_name] = value

        # File collection environment variables
        file_collection_config = config_data.setdefault("file_collection", {})

        # OSTRUCT_IGNORE_GITIGNORE environment variable
        ignore_gitignore_env = os.getenv("OSTRUCT_IGNORE_GITIGNORE")
        if ignore_gitignore_env is not None:
            file_collection_config["ignore_gitignore"] = (
                ignore_gitignore_env.lower() in ("true", "1", "yes")
            )

        # OSTRUCT_GITIGNORE_FILE environment variable
        gitignore_file_env = os.getenv("OSTRUCT_GITIGNORE_FILE")
        if gitignore_file_env:
            file_collection_config["gitignore_file"] = gitignore_file_env

        # Built-in MCP server shortcuts
        builtin_servers = {
            "stripe": "https://mcp.stripe.com",
            "shopify": "https://mcp.shopify.com",
        }

        for name, url in builtin_servers.items():
            if name not in mcp_config:
                env_key = f"OSTRUCT_MCP_URL_{name}"
                if os.getenv(env_key):
                    mcp_config[name] = os.getenv(env_key)

        return config_data

    def get_model_default(self) -> str:
        """Get the default model to use."""
        return self.models.default

    def get_mcp_servers(self) -> Dict[str, str]:
        """Get configured MCP servers."""
        return self.mcp

    def get_code_interpreter_config(self) -> Dict[str, Any]:
        """Get code interpreter configuration."""
        return self.tools.code_interpreter

    def get_file_search_config(self) -> Dict[str, Any]:
        """Get file search configuration."""
        return self.tools.file_search

    def get_web_search_config(self) -> WebSearchToolConfig:
        """Get web search configuration."""
        return self.tools.web_search

    def get_file_collection_config(self) -> FileCollectionConfig:
        """Get file collection configuration."""
        return self.file_collection

    def should_require_approval(self, cost_estimate: float = 0.0) -> bool:
        """Determine if approval should be required for an operation."""
        if self.operation.require_approval == "always":
            return True
        elif self.operation.require_approval == "never":
            return False
        elif self.operation.require_approval == "expensive":
            return cost_estimate > self.limits.max_cost_per_run * 0.5
        return False

    def is_within_cost_limits(self, cost_estimate: float) -> bool:
        """Check if operation is within configured cost limits."""
        return cost_estimate <= self.limits.max_cost_per_run

    def should_warn_expensive(self, cost_estimate: float) -> bool:
        """Check if expensive operation warning should be shown."""
        return (
            self.limits.warn_expensive_operations
            and cost_estimate > self.limits.max_cost_per_run * 0.3
        )


def create_example_config() -> str:
    """Create example configuration YAML content."""
    return """# ostruct Configuration File
# This file configures default behavior for the ostruct CLI tool.
# All settings are optional - ostruct works with smart defaults.

# Model configuration
models:
  default: gpt-4o  # Default model to use

# Tool-specific settings
tools:
  code_interpreter:
    auto_download: true
    output_directory: "./downloads"

  file_search:
    max_results: 10

  web_search:
    enable_by_default: false  # Whether to enable web search by default
    search_context_size: medium  # Options: low, medium, high
    user_location:
      country: US  # Optional: country for geographically relevant results
      city: San Francisco  # Optional: city for local context
      region: California  # Optional: region/state for regional relevance

# MCP (Model Context Protocol) server configurations
# You can define shortcuts to commonly used MCP servers
mcp:
  # Built-in server shortcuts (uncomment to use)
  # stripe: "https://mcp.stripe.com"
  # shopify: "https://mcp.shopify.com"

  # Custom servers
  # my_server: "https://my-mcp-server.com"

# Operation settings
operation:
  timeout_minutes: 60
  retry_attempts: 3
  require_approval: never  # Options: never, always, expensive

# Cost and safety limits
limits:
  max_cost_per_run: 10.00
  warn_expensive_operations: true

# Environment Variables for Secrets:
# OPENAI_API_KEY - Your OpenAI API key
# OSTRUCT_MCP_URL_<name> - URL for custom MCP servers (e.g., OSTRUCT_MCP_URL_stripe)
"""


def get_config() -> OstructConfig:
    """Get the global configuration instance."""
    return OstructConfig.load()
