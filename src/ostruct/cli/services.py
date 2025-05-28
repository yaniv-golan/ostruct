"""Service container for ostruct CLI tool managers."""

import logging
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .types import CLIParams

logger = logging.getLogger(__name__)

# Type alias for CLI parameters
# CLIParams imported from types module


class ServiceStatus(Enum):
    """Service health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Service health information."""

    status: ServiceStatus
    message: str
    details: Optional[Dict[str, Any]] = None


class ServiceConfigurationBase(BaseModel):
    """Base configuration for all services."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow additional fields for service-specific config

    enabled: bool = Field(
        default=True, description="Whether the service is enabled"
    )
    timeout: Optional[float] = Field(
        default=None, description="Service timeout in seconds"
    )
    retry_attempts: int = Field(
        default=3, description="Number of retry attempts"
    )


class MCPServiceConfiguration(ServiceConfigurationBase):
    """Configuration for MCP service."""

    servers: List[Dict[str, Any]] = Field(
        default_factory=list, description="MCP server configurations"
    )
    connection_timeout: float = Field(
        default=30.0, description="Connection timeout in seconds"
    )
    max_retries: int = Field(
        default=3, description="Maximum retry attempts for server connections"
    )

    def validate_servers(self) -> List[str]:
        """Validate server configurations and return any errors."""
        errors = []
        for i, server in enumerate(self.servers):
            if not isinstance(server, dict):
                errors.append(f"Server {i}: Must be a dictionary")
                continue
            if "name" not in server:
                errors.append(f"Server {i}: Missing required 'name' field")
            if "command" not in server:
                errors.append(f"Server {i}: Missing required 'command' field")
        return errors


class CodeInterpreterServiceConfiguration(ServiceConfigurationBase):
    """Configuration for Code Interpreter service."""

    max_file_size_mb: float = Field(
        default=100.0, description="Maximum file size in MB"
    )
    allowed_file_types: List[str] = Field(
        default_factory=lambda: [".py", ".txt", ".json", ".csv", ".md"],
        description="Allowed file extensions",
    )
    cleanup_on_exit: bool = Field(
        default=True, description="Clean up uploaded files on exit"
    )

    def validate_file_types(self) -> List[str]:
        """Validate file type configurations."""
        errors = []
        for file_type in self.allowed_file_types:
            if not isinstance(file_type, str):
                errors.append(
                    f"File type must be string, got {type(file_type)}"
                )
            elif not file_type.startswith("."):
                errors.append(f"File type '{file_type}' must start with '.'")
        return errors


class FileSearchServiceConfiguration(ServiceConfigurationBase):
    """Configuration for File Search service."""

    max_files: int = Field(
        default=1000, description="Maximum number of files to index"
    )
    chunk_size: int = Field(
        default=800, description="Text chunk size for indexing"
    )
    overlap: int = Field(default=400, description="Text chunk overlap")
    cleanup_vector_stores: bool = Field(
        default=True, description="Clean up vector stores on exit"
    )

    def validate_chunk_settings(self) -> List[str]:
        """Validate chunk size and overlap settings."""
        errors = []
        if self.chunk_size <= 0:
            errors.append("Chunk size must be positive")
        if self.overlap < 0:
            errors.append("Overlap cannot be negative")
        if self.overlap >= self.chunk_size:
            errors.append("Overlap must be less than chunk size")
        return errors


class ServiceConfigurationValidator:
    """Validates service configurations."""

    @staticmethod
    def validate_mcp_config(config: Dict[str, Any]) -> MCPServiceConfiguration:
        """Validate MCP service configuration."""
        try:
            mcp_config = MCPServiceConfiguration(**config)
            server_errors = mcp_config.validate_servers()
            if server_errors:
                raise ValueError(
                    f"MCP server validation errors: {'; '.join(server_errors)}"
                )
            return mcp_config
        except (ValidationError, ValueError) as e:
            logger.error(f"MCP configuration validation failed: {e}")
            raise

    @staticmethod
    def validate_code_interpreter_config(
        config: Dict[str, Any],
    ) -> CodeInterpreterServiceConfiguration:
        """Validate Code Interpreter service configuration."""
        try:
            ci_config = CodeInterpreterServiceConfiguration(**config)
            file_type_errors = ci_config.validate_file_types()
            if file_type_errors:
                raise ValueError(
                    f"Code Interpreter file type errors: {'; '.join(file_type_errors)}"
                )
            return ci_config
        except (ValidationError, ValueError) as e:
            logger.error(
                f"Code Interpreter configuration validation failed: {e}"
            )
            raise

    @staticmethod
    def validate_file_search_config(
        config: Dict[str, Any],
    ) -> FileSearchServiceConfiguration:
        """Validate File Search service configuration."""
        try:
            fs_config = FileSearchServiceConfiguration(**config)
            chunk_errors = fs_config.validate_chunk_settings()
            if chunk_errors:
                raise ValueError(
                    f"File Search chunk setting errors: {'; '.join(chunk_errors)}"
                )
            return fs_config
        except (ValidationError, ValueError) as e:
            logger.error(f"File Search configuration validation failed: {e}")
            raise


class ToolManagerProtocol(Protocol):
    """Protocol defining the interface for tool managers."""

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources used by the tool manager."""
        ...

    @abstractmethod
    async def health_check(self) -> ServiceHealth:
        """Check the health status of the tool manager."""
        ...


class MCPManagerProtocol(ToolManagerProtocol):
    """Protocol for MCP server managers."""

    @abstractmethod
    def get_tools_for_responses_api(self) -> List[dict]:
        """Get tools configured for OpenAI Responses API."""
        ...


class CodeInterpreterManagerProtocol(ToolManagerProtocol):
    """Protocol for code interpreter managers."""

    @abstractmethod
    async def upload_files_for_code_interpreter(
        self, files: List[str]
    ) -> List[str]:
        """Upload files for code interpreter access."""
        ...

    @abstractmethod
    async def cleanup_uploaded_files(self) -> None:
        """Clean up uploaded files."""
        ...

    @abstractmethod
    def build_tool_config(self, file_ids: List[str]) -> Dict[str, Any]:
        """Build Code Interpreter tool configuration."""
        ...


class FileSearchManagerProtocol(ToolManagerProtocol):
    """Protocol for file search managers."""

    @abstractmethod
    async def upload_files_to_vector_store(
        self, files: List[str], vector_store_id: str
    ) -> Dict[str, Any]:
        """Upload files to vector store."""
        ...

    @abstractmethod
    async def cleanup_resources(self) -> None:
        """Clean up vector store resources."""
        ...

    @abstractmethod
    def build_tool_config(self, vector_store_id: str) -> Dict[str, Any]:
        """Build File Search tool configuration."""
        ...


class ServiceFactoryProtocol(Protocol):
    """Protocol for service factories."""

    async def create_mcp_manager(
        self, args: CLIParams
    ) -> Optional[MCPManagerProtocol]:
        """Create MCP server manager."""
        ...

    async def create_code_interpreter_manager(
        self, args: CLIParams, client: AsyncOpenAI
    ) -> Optional[CodeInterpreterManagerProtocol]:
        """Create code interpreter manager."""
        ...

    async def create_file_search_manager(
        self, args: CLIParams, client: AsyncOpenAI
    ) -> Optional[FileSearchManagerProtocol]:
        """Create file search manager."""
        ...


class DefaultServiceFactory:
    """Default factory for creating service instances."""

    async def create_mcp_manager(
        self, args: CLIParams
    ) -> Optional[MCPManagerProtocol]:
        """Create MCP server manager."""
        if not args.get("mcp_servers"):
            return None
        from .runner import process_mcp_configuration

        manager = await process_mcp_configuration(args)
        # The manager implements MCPManagerProtocol interface
        return manager  # type: ignore[return-value]

    async def create_code_interpreter_manager(
        self, args: CLIParams, client: AsyncOpenAI
    ) -> Optional[CodeInterpreterManagerProtocol]:
        """Create code interpreter manager."""
        if not args.get("code_interpreter"):
            return None
        from .runner import process_code_interpreter_configuration

        manager_info = await process_code_interpreter_configuration(
            args, client
        )
        return manager_info.get("manager") if manager_info else None

    async def create_file_search_manager(
        self, args: CLIParams, client: AsyncOpenAI
    ) -> Optional[FileSearchManagerProtocol]:
        """Create file search manager."""
        if not args.get("file_search"):
            return None
        from .runner import process_file_search_configuration

        manager_info = await process_file_search_configuration(args, client)
        return manager_info.get("manager") if manager_info else None


class ServiceContainer:
    """Service container for managing tool managers and their dependencies."""

    def __init__(
        self,
        client: AsyncOpenAI,
        args: CLIParams,
        factory: Optional[ServiceFactoryProtocol] = None,
    ):
        """Initialize service container.

        Args:
            client: Configured AsyncOpenAI client
            args: CLI parameters
            factory: Service factory for creating managers (uses default if None)
        """
        self.client = client
        self.args = args
        self.factory = factory or DefaultServiceFactory()
        self._mcp_manager: Optional[MCPManagerProtocol] = None
        self._code_interpreter_manager: Optional[
            CodeInterpreterManagerProtocol
        ] = None
        self._file_search_manager: Optional[FileSearchManagerProtocol] = None

        # Validate configurations at initialization
        self._validated_configs: Dict[
            str, Optional[ServiceConfigurationBase]
        ] = {}
        self._validate_service_configurations()

    async def get_mcp_manager(self) -> Optional[MCPManagerProtocol]:
        """Get or create MCP server manager.

        Returns:
            Configured MCP manager instance or None if not needed
        """
        if self._mcp_manager is None and self.args.get("mcp_servers"):
            self._mcp_manager = await self.factory.create_mcp_manager(
                self.args
            )
        return self._mcp_manager

    async def get_code_interpreter_manager(
        self,
    ) -> Optional[CodeInterpreterManagerProtocol]:
        """Get or create code interpreter manager.

        Returns:
            Configured code interpreter manager instance or None if not needed
        """
        if self._code_interpreter_manager is None and self.args.get(
            "code_interpreter"
        ):
            self._code_interpreter_manager = (
                await self.factory.create_code_interpreter_manager(
                    self.args, self.client
                )
            )
        return self._code_interpreter_manager

    async def get_file_search_manager(
        self,
    ) -> Optional[FileSearchManagerProtocol]:
        """Get or create file search manager.

        Returns:
            Configured file search manager instance or None if not needed
        """
        if self._file_search_manager is None and self.args.get("file_search"):
            self._file_search_manager = (
                await self.factory.create_file_search_manager(
                    self.args, self.client
                )
            )
        return self._file_search_manager

    async def cleanup(self) -> None:
        """Clean up all managed services."""
        cleanup_tasks = []

        # Clean up MCP manager if it exists
        if self._mcp_manager:
            # MCPServerManager doesn't have a cleanup method, skip it
            pass

        # Clean up code interpreter manager
        if self._code_interpreter_manager:
            # Use the specific cleanup method for code interpreter
            if hasattr(
                self._code_interpreter_manager, "cleanup_uploaded_files"
            ):
                cleanup_tasks.append(
                    self._code_interpreter_manager.cleanup_uploaded_files()
                )

        # Clean up file search manager
        if self._file_search_manager:
            # Use the specific cleanup method for file search
            if hasattr(self._file_search_manager, "cleanup_resources"):
                cleanup_tasks.append(
                    self._file_search_manager.cleanup_resources()
                )

        # Execute cleanup tasks concurrently
        if cleanup_tasks:
            import asyncio

            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    def is_configured(self, service_name: str) -> bool:
        """Check if a service is configured.

        Args:
            service_name: Name of the service to check

        Returns:
            True if the service is configured in args
        """
        service_mapping = {
            "mcp": "mcp_servers",
            "code_interpreter": "code_interpreter",
            "file_search": "file_search",
        }

        arg_key = service_mapping.get(service_name)
        if not arg_key:
            return False

        return bool(self.args.get(arg_key))

    def get_service_configuration(self, service_name: str) -> Any:
        """Get service configuration from args.

        Args:
            service_name: Name of the service

        Returns:
            Service configuration or None
        """
        service_mapping = {
            "mcp": "mcp_servers",
            "code_interpreter": "code_interpreter",
            "file_search": "file_search",
        }

        arg_key = service_mapping.get(service_name)
        if not arg_key:
            return None

        return self.args.get(arg_key)

    def _validate_service_configurations(self) -> None:
        """Validate all service configurations at container initialization."""
        validator = ServiceConfigurationValidator()

        # Validate MCP configuration if present
        if self.args.get("mcp_servers"):
            try:
                mcp_config = {"servers": self.args["mcp_servers"]}
                self._validated_configs["mcp"] = validator.validate_mcp_config(
                    mcp_config
                )
                logger.debug("MCP configuration validated successfully")
            except (ValidationError, ValueError) as e:
                logger.warning(f"MCP configuration validation failed: {e}")
                self._validated_configs["mcp"] = None

        # Validate Code Interpreter configuration if present
        if self.args.get("code_interpreter"):
            try:
                ci_config = {"enabled": True}  # Basic config, extend as needed
                self._validated_configs["code_interpreter"] = (
                    validator.validate_code_interpreter_config(ci_config)
                )
                logger.debug(
                    "Code Interpreter configuration validated successfully"
                )
            except (ValidationError, ValueError) as e:
                logger.warning(
                    f"Code Interpreter configuration validation failed: {e}"
                )
                self._validated_configs["code_interpreter"] = None

        # Validate File Search configuration if present
        if self.args.get("file_search"):
            try:
                fs_config = {"enabled": True}  # Basic config, extend as needed
                self._validated_configs["file_search"] = (
                    validator.validate_file_search_config(fs_config)
                )
                logger.debug(
                    "File Search configuration validated successfully"
                )
            except (ValidationError, ValueError) as e:
                logger.warning(
                    f"File Search configuration validation failed: {e}"
                )
                self._validated_configs["file_search"] = None

    def get_validated_config(
        self, service_name: str
    ) -> Optional[ServiceConfigurationBase]:
        """Get validated configuration for a service.

        Args:
            service_name: Name of the service

        Returns:
            Validated configuration or None if validation failed
        """
        return self._validated_configs.get(service_name)

    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """Check health of a specific service.

        Args:
            service_name: Name of the service to check

        Returns:
            ServiceHealth with status and details
        """
        if service_name == "mcp":
            mcp_manager = await self.get_mcp_manager()
            if mcp_manager and hasattr(mcp_manager, "health_check"):
                return await mcp_manager.health_check()
            elif mcp_manager:
                return ServiceHealth(
                    status=ServiceStatus.HEALTHY,
                    message="MCP manager is running",
                    details={"has_health_check": False},
                )
        elif service_name == "code_interpreter":
            ci_manager = await self.get_code_interpreter_manager()
            if ci_manager and hasattr(ci_manager, "health_check"):
                return await ci_manager.health_check()
            elif ci_manager:
                return ServiceHealth(
                    status=ServiceStatus.HEALTHY,
                    message="Code Interpreter manager is running",
                    details={"has_health_check": False},
                )
        elif service_name == "file_search":
            fs_manager = await self.get_file_search_manager()
            if fs_manager and hasattr(fs_manager, "health_check"):
                return await fs_manager.health_check()
            elif fs_manager:
                return ServiceHealth(
                    status=ServiceStatus.HEALTHY,
                    message="File Search manager is running",
                    details={"has_health_check": False},
                )

        # Service not configured or not found
        return ServiceHealth(
            status=ServiceStatus.UNKNOWN,
            message=f"Service '{service_name}' not configured or not found",
        )

    async def check_all_services_health(self) -> Dict[str, ServiceHealth]:
        """Check health of all configured services.

        Returns:
            Dictionary mapping service names to their health status
        """
        health_checks = {}

        # Check each configured service
        for service_name in ["mcp", "code_interpreter", "file_search"]:
            if self.is_configured(service_name):
                health_checks[service_name] = await self.check_service_health(
                    service_name
                )

        return health_checks

    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all services.

        Returns:
            Dictionary with service information including configuration status
        """
        service_info = {}

        for service_name in ["mcp", "code_interpreter", "file_search"]:
            is_configured = self.is_configured(service_name)
            validated_config = self.get_validated_config(service_name)

            service_info[service_name] = {
                "configured": is_configured,
                "validated": validated_config is not None,
                "config_valid": (
                    validated_config is not None if is_configured else None
                ),
                "has_manager": False,  # Will be updated when managers are created
            }

            # Check if manager exists
            if service_name == "mcp" and self._mcp_manager:
                service_info[service_name]["has_manager"] = True
            elif (
                service_name == "code_interpreter"
                and self._code_interpreter_manager
            ):
                service_info[service_name]["has_manager"] = True
            elif service_name == "file_search" and self._file_search_manager:
                service_info[service_name]["has_manager"] = True

        return service_info
