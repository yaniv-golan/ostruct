"""Unattended operation safeguards for CI/CD compatibility."""

import asyncio
import logging
from typing import Any, Callable, List, Optional

from .errors import CLIError, ContainerExpiredError, ExitCode

logger = logging.getLogger(__name__)


class UnattendedOperationTimeoutError(CLIError):
    """Operation timed out during unattended execution."""

    def __init__(
        self,
        message: str,
        timeout_seconds: int,
        exit_code: ExitCode = ExitCode.OPERATION_TIMEOUT,
        context: Optional[dict] = None,
    ):
        """Initialize timeout error with automation guidance.

        Args:
            message: Error message
            timeout_seconds: The timeout that was exceeded
            exit_code: Exit code for automation
            context: Additional context information
        """
        enhanced_message = (
            f"{message}\n\n"
            f"💡 For CI/CD environments:\n"
            f"   • Increase timeout with --timeout {timeout_seconds * 2}\n"
            f"   • Split large operations into smaller chunks\n"
            f"   • Use --dry-run to validate before actual execution\n"
            f"   • Check server/tool availability before running"
        )

        enhanced_context = {
            "timeout_seconds": timeout_seconds,
            "automation_friendly": True,
            **(context or {}),
        }

        super().__init__(
            enhanced_message, exit_code=exit_code, context=enhanced_context
        )


class UnattendedOperationManager:
    """Manager for unattended operations with timeout and error handling."""

    def __init__(self, timeout_seconds: int = 3600):  # 1 hour default
        """Initialize unattended operation manager.

        Args:
            timeout_seconds: Maximum operation timeout in seconds
        """
        self.timeout = timeout_seconds
        logger.debug(
            f"UnattendedOperationManager initialized with {timeout_seconds}s timeout"
        )

    async def execute_with_safeguards(
        self, operation: Callable, operation_name: str = "operation"
    ) -> Any:
        """Execute operation with timeout and error handling.

        Args:
            operation: Async callable to execute
            operation_name: Human-readable name for logging and errors

        Returns:
            Result of the operation

        Raises:
            UnattendedOperationTimeoutError: If operation times out
            ContainerExpiredError: If container expires (fail fast)
            CLIError: For other operation failures
        """
        logger.debug(
            f"Starting unattended {operation_name} with {self.timeout}s timeout"
        )

        try:
            result = await asyncio.wait_for(operation(), timeout=self.timeout)
            logger.debug(f"Unattended {operation_name} completed successfully")
            return result

        except asyncio.TimeoutError:
            error_msg = f"Unattended {operation_name} timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise UnattendedOperationTimeoutError(
                error_msg,
                timeout_seconds=self.timeout,
                context={"operation": operation_name},
            )

        except ContainerExpiredError:
            # Fail fast for container expiration - these are unrecoverable
            logger.error(
                f"Container expired during {operation_name} - failing fast"
            )
            raise

        except CLIError:
            # Re-raise CLI errors as-is (they're already properly formatted)
            raise

        except Exception as e:
            # Wrap unexpected errors for better automation handling
            error_msg = (
                f"Unexpected error during unattended {operation_name}: {e}"
            )
            logger.error(error_msg)
            raise CLIError(
                error_msg,
                exit_code=ExitCode.INTERNAL_ERROR,
                context={
                    "operation": operation_name,
                    "original_error": str(e),
                },
            )

    def set_timeout(self, timeout_seconds: int) -> None:
        """Update operation timeout.

        Args:
            timeout_seconds: New timeout in seconds
        """
        old_timeout = self.timeout
        self.timeout = timeout_seconds
        logger.debug(f"Timeout updated: {old_timeout}s -> {timeout_seconds}s")


class UnattendedCompatibilityValidator:
    """Validator for ensuring operations can run without user interaction."""

    @staticmethod
    def validate_mcp_servers(servers: List[dict]) -> List[str]:
        """Pre-validate MCP servers don't require interaction.

        Args:
            servers: List of MCP server configurations

        Returns:
            List of validation errors, empty if all servers are compatible
        """
        errors = []

        for server in servers:
            server_url = server.get("url", "unknown")

            # Check approval requirement
            require_approval = server.get("require_approval", "user")
            if require_approval != "never":
                errors.append(
                    f"MCP server {server_url} requires approval ('{require_approval}') - "
                    f"incompatible with unattended CLI usage. Set require_approval='never'."
                )

            # Check for interactive features that break automation
            if server.get("interactive_mode", False):
                errors.append(
                    f"MCP server {server_url} has interactive_mode enabled - "
                    f"incompatible with unattended operation"
                )

            # Check for user prompt features
            if server.get("user_prompts", False):
                errors.append(
                    f"MCP server {server_url} enables user_prompts - "
                    f"incompatible with unattended operation"
                )

        return errors

    @staticmethod
    def validate_tool_configurations(tool_configs: List[dict]) -> List[str]:
        """Validate tool configurations for unattended operation.

        Args:
            tool_configs: List of tool configurations

        Returns:
            List of validation errors, empty if all tools are compatible
        """
        errors = []

        for tool_config in tool_configs:
            tool_type = tool_config.get("type", "unknown")

            # Validate MCP tools
            if tool_type == "mcp":
                if tool_config.get("require_approval") != "never":
                    errors.append(
                        f"MCP tool {tool_config.get('server_label', 'unknown')} "
                        f"requires approval - incompatible with unattended operation"
                    )

            # Validate Code Interpreter - should be fine for unattended use
            elif tool_type == "code_interpreter":
                # Code Interpreter is inherently unattended-compatible
                pass

            # Validate File Search - should be fine for unattended use
            elif tool_type == "file_search":
                # File Search is inherently unattended-compatible
                pass

            # Unknown tool types - warn but don't fail
            else:
                logger.warning(
                    f"Unknown tool type '{tool_type}' - cannot validate for unattended operation"
                )

        return errors

    @staticmethod
    def get_automation_recommendations() -> List[str]:
        """Get recommendations for better automation compatibility.

        Returns:
            List of recommendations for CI/CD usage
        """
        return [
            "Use --dry-run to validate configuration before actual execution",
            "Set explicit timeouts with --timeout for long-running operations",
            "Configure MCP servers with require_approval='never'",
            "Use structured logging for better CI/CD integration",
            "Test operations locally before deploying to CI/CD",
            "Monitor container expiration limits (20min runtime, 2min idle)",
            "Use retry logic for transient network failures",
            "Validate API keys and permissions before execution",
        ]


def ensure_unattended_compatibility(
    mcp_servers: Optional[List[dict]] = None,
    tool_configs: Optional[List[dict]] = None,
    timeout_seconds: int = 3600,
) -> tuple[UnattendedOperationManager, List[str]]:
    """Ensure complete unattended operation compatibility.

    Args:
        mcp_servers: Optional list of MCP server configurations
        tool_configs: Optional list of tool configurations
        timeout_seconds: Operation timeout in seconds

    Returns:
        Tuple of (operation_manager, validation_errors)
    """
    validator = UnattendedCompatibilityValidator()
    all_errors = []

    # Validate MCP servers
    if mcp_servers:
        mcp_errors = validator.validate_mcp_servers(mcp_servers)
        all_errors.extend(mcp_errors)

    # Validate tool configurations
    if tool_configs:
        tool_errors = validator.validate_tool_configurations(tool_configs)
        all_errors.extend(tool_errors)

    # Create operation manager
    operation_manager = UnattendedOperationManager(timeout_seconds)

    return operation_manager, all_errors
