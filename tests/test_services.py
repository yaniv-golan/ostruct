"""Tests for service container and dependency injection."""

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import AsyncOpenAI

from ostruct.cli.services import (
    CodeInterpreterManagerProtocol,
    CodeInterpreterServiceConfiguration,
    DefaultServiceFactory,
    FileSearchManagerProtocol,
    FileSearchServiceConfiguration,
    MCPManagerProtocol,
    MCPServiceConfiguration,
    ServiceConfigurationValidator,
    ServiceContainer,
    ServiceHealth,
    ServiceStatus,
)


class MockMCPManager:
    """Mock MCP manager for testing."""

    def get_tools_for_responses_api(self) -> List[dict]:
        return [{"type": "function", "function": {"name": "test_tool"}}]

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(
            status=ServiceStatus.HEALTHY,
            message="MCP manager is healthy",
            details={"servers": 1},
        )


class MockCodeInterpreterManager:
    """Mock code interpreter manager for testing."""

    async def upload_files_for_code_interpreter(
        self, files: List[str]
    ) -> List[str]:
        return ["file_id_1", "file_id_2"]

    async def cleanup_uploaded_files(self) -> None:
        pass

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(
            status=ServiceStatus.HEALTHY,
            message="Code Interpreter manager is healthy",
        )


class MockFileSearchManager:
    """Mock file search manager for testing."""

    async def upload_files_to_vector_store(
        self, files: List[str], vector_store_id: str
    ) -> Dict[str, Any]:
        return {
            "vector_store_id": vector_store_id,
            "file_ids": ["file_1", "file_2"],
        }

    async def cleanup_resources(self) -> None:
        pass

    async def health_check(self) -> ServiceHealth:
        return ServiceHealth(
            status=ServiceStatus.HEALTHY,
            message="File Search manager is healthy",
        )


class MockServiceFactory:
    """Mock service factory for testing."""

    def __init__(self):
        self.mcp_manager = MockMCPManager()
        self.code_interpreter_manager = MockCodeInterpreterManager()
        self.file_search_manager = MockFileSearchManager()

    async def create_mcp_manager(
        self, args: Dict[str, Any]
    ) -> Optional[MCPManagerProtocol]:
        return self.mcp_manager if args.get("mcp_servers") else None

    async def create_code_interpreter_manager(
        self, args: Dict[str, Any], client: AsyncOpenAI
    ) -> Optional[CodeInterpreterManagerProtocol]:
        return (
            self.code_interpreter_manager
            if args.get("code_interpreter")
            else None
        )

    async def create_file_search_manager(
        self, args: Dict[str, Any], client: AsyncOpenAI
    ) -> Optional[FileSearchManagerProtocol]:
        return self.file_search_manager if args.get("file_search") else None


class TestServiceContainer:
    """Test cases for ServiceContainer."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AsyncOpenAI client."""
        return MagicMock(spec=AsyncOpenAI)

    @pytest.fixture
    def mock_factory(self):
        """Create mock service factory."""
        return MockServiceFactory()

    @pytest.fixture
    def service_container(self, mock_client, mock_factory):
        """Create service container with mock factory."""
        args = {
            "mcp_servers": ["server1"],
            "code_interpreter": True,
            "file_search": True,
        }
        return ServiceContainer(mock_client, args, mock_factory)

    @pytest.mark.asyncio
    async def test_mcp_manager_creation(self, service_container):
        """Test MCP manager creation through dependency injection."""
        manager = await service_container.get_mcp_manager()
        assert manager is not None
        assert hasattr(manager, "get_tools_for_responses_api")

        tools = manager.get_tools_for_responses_api()
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_code_interpreter_manager_creation(self, service_container):
        """Test code interpreter manager creation through dependency injection."""
        manager = await service_container.get_code_interpreter_manager()
        assert manager is not None
        assert hasattr(manager, "upload_files_for_code_interpreter")

        file_ids = await manager.upload_files_for_code_interpreter(
            ["file1.py", "file2.py"]
        )
        assert file_ids == ["file_id_1", "file_id_2"]

    @pytest.mark.asyncio
    async def test_file_search_manager_creation(self, service_container):
        """Test file search manager creation through dependency injection."""
        manager = await service_container.get_file_search_manager()
        assert manager is not None
        assert hasattr(manager, "upload_files_to_vector_store")

        result = await manager.upload_files_to_vector_store(
            ["doc1.txt"], "vs_123"
        )
        assert result["vector_store_id"] == "vs_123"
        assert result["file_ids"] == ["file_1", "file_2"]

    @pytest.mark.asyncio
    async def test_lazy_loading(self, mock_client, mock_factory):
        """Test that managers are only created when requested."""
        args = {"mcp_servers": ["server1"]}
        container = ServiceContainer(mock_client, args, mock_factory)

        # Initially no managers should be created
        assert container._mcp_manager is None
        assert container._code_interpreter_manager is None
        assert container._file_search_manager is None

        # Request MCP manager
        mcp_manager = await container.get_mcp_manager()
        assert mcp_manager is not None
        assert container._mcp_manager is not None

        # Other managers should still be None
        assert container._code_interpreter_manager is None
        assert container._file_search_manager is None

    @pytest.mark.asyncio
    async def test_service_not_configured(self, mock_client, mock_factory):
        """Test behavior when services are not configured."""
        args = {}  # No services configured
        container = ServiceContainer(mock_client, args, mock_factory)

        mcp_manager = await container.get_mcp_manager()
        assert mcp_manager is None

        ci_manager = await container.get_code_interpreter_manager()
        assert ci_manager is None

        fs_manager = await container.get_file_search_manager()
        assert fs_manager is None

    def test_is_configured(self, service_container):
        """Test service configuration checking."""
        assert service_container.is_configured("mcp") is True
        assert service_container.is_configured("code_interpreter") is True
        assert service_container.is_configured("file_search") is True

        # Test with empty container
        empty_container = ServiceContainer(
            MagicMock(), {}, MockServiceFactory()
        )
        assert empty_container.is_configured("mcp") is False
        assert empty_container.is_configured("code_interpreter") is False
        assert empty_container.is_configured("file_search") is False

    def test_get_service_configuration(self, service_container):
        """Test getting service configuration."""
        assert service_container.get_service_configuration("mcp") == [
            "server1"
        ]
        assert (
            service_container.get_service_configuration("code_interpreter")
            is True
        )
        assert (
            service_container.get_service_configuration("file_search") is True
        )
        assert service_container.get_service_configuration("unknown") is None

    @pytest.mark.asyncio
    async def test_cleanup(self, service_container):
        """Test service cleanup coordination."""
        # Create managers
        await service_container.get_mcp_manager()
        await service_container.get_code_interpreter_manager()
        await service_container.get_file_search_manager()

        # Mock cleanup methods to verify they're called
        service_container._code_interpreter_manager.cleanup_uploaded_files = (
            AsyncMock()
        )
        service_container._file_search_manager.cleanup_resources = AsyncMock()

        # Call cleanup
        await service_container.cleanup()

        # Verify cleanup methods were called
        service_container._code_interpreter_manager.cleanup_uploaded_files.assert_called_once()
        service_container._file_search_manager.cleanup_resources.assert_called_once()


class TestDefaultServiceFactory:
    """Test cases for DefaultServiceFactory."""

    @pytest.fixture
    def mock_client(self):
        """Create mock AsyncOpenAI client."""
        return MagicMock(spec=AsyncOpenAI)

    @pytest.fixture
    def default_factory(self):
        """Create default service factory."""
        return DefaultServiceFactory()

    @pytest.mark.asyncio
    async def test_factory_interface_compliance(
        self, default_factory, mock_client
    ):
        """Test that default factory implements the protocol correctly."""
        # Verify it has the required methods
        assert hasattr(default_factory, "create_mcp_manager")
        assert hasattr(default_factory, "create_code_interpreter_manager")
        assert hasattr(default_factory, "create_file_search_manager")

        # Test method signatures (they should be callable)
        args = {}

        # These will import process_*_configuration functions, but won't create managers
        # since the args don't have the required configuration
        mcp_manager = await default_factory.create_mcp_manager(args)
        assert mcp_manager is None  # No mcp_servers configured

        ci_manager = await default_factory.create_code_interpreter_manager(
            args, mock_client
        )
        assert ci_manager is None  # No code_interpreter configured

        fs_manager = await default_factory.create_file_search_manager(
            args, mock_client
        )
        assert fs_manager is None  # No file_search configured


@pytest.mark.asyncio
async def test_service_container_integration():
    """Integration test showing complete dependency injection workflow."""
    # Setup
    mock_client = MagicMock(spec=AsyncOpenAI)
    mock_factory = MockServiceFactory()
    args = {
        "mcp_servers": ["test_server"],
        "code_interpreter": True,
        "file_search": True,
    }

    # Create service container
    container = ServiceContainer(mock_client, args, mock_factory)

    # Test the complete workflow
    # 1. Check configuration
    assert container.is_configured("mcp")
    assert container.is_configured("code_interpreter")
    assert container.is_configured("file_search")

    # 2. Get managers (lazy loading)
    mcp_manager = await container.get_mcp_manager()
    ci_manager = await container.get_code_interpreter_manager()
    fs_manager = await container.get_file_search_manager()

    # 3. Verify managers work
    assert (
        mcp_manager.get_tools_for_responses_api()[0]["function"]["name"]
        == "test_tool"
    )
    assert await ci_manager.upload_files_for_code_interpreter(["test.py"]) == [
        "file_id_1",
        "file_id_2",
    ]
    assert (await fs_manager.upload_files_to_vector_store(["doc.txt"], "vs1"))[
        "vector_store_id"
    ] == "vs1"

    # 4. Test cleanup
    await container.cleanup()

    # Integration test passes if no exceptions are raised


class TestServiceConfiguration:
    """Test service configuration validation and management."""

    def test_mcp_service_configuration_validation(self):
        """Test MCP service configuration validation."""
        validator = ServiceConfigurationValidator()

        # Valid configuration
        valid_config = {
            "servers": [
                {"name": "server1", "command": ["node", "server.js"]},
                {"name": "server2", "command": ["python", "server.py"]},
            ]
        }
        mcp_config = validator.validate_mcp_config(valid_config)
        assert isinstance(mcp_config, MCPServiceConfiguration)
        assert len(mcp_config.servers) == 2
        assert mcp_config.validate_servers() == []  # No errors

        # Invalid configuration - missing required fields
        invalid_config = {
            "servers": [
                {"name": "server1"},  # Missing command
                {"command": ["node", "server.js"]},  # Missing name
            ]
        }

        with pytest.raises(Exception):  # ValidationError or similar
            validator.validate_mcp_config(invalid_config)

    def test_code_interpreter_service_configuration_validation(self):
        """Test Code Interpreter service configuration validation."""
        validator = ServiceConfigurationValidator()

        # Valid configuration
        valid_config = {
            "enabled": True,
            "max_file_size_mb": 50.0,
            "allowed_file_types": [".py", ".txt", ".json"],
        }
        ci_config = validator.validate_code_interpreter_config(valid_config)
        assert isinstance(ci_config, CodeInterpreterServiceConfiguration)
        assert ci_config.max_file_size_mb == 50.0
        assert ".py" in ci_config.allowed_file_types
        assert ci_config.validate_file_types() == []  # No errors

        # Invalid configuration - bad file types
        invalid_config = {
            "enabled": True,
            "allowed_file_types": ["py", ".txt"],  # Missing dot prefix
        }

        with pytest.raises(Exception):  # ValidationError or similar
            validator.validate_code_interpreter_config(invalid_config)

    def test_file_search_service_configuration_validation(self):
        """Test File Search service configuration validation."""
        validator = ServiceConfigurationValidator()

        # Valid configuration
        valid_config = {"enabled": True, "chunk_size": 1000, "overlap": 200}
        fs_config = validator.validate_file_search_config(valid_config)
        assert isinstance(fs_config, FileSearchServiceConfiguration)
        assert fs_config.chunk_size == 1000
        assert fs_config.overlap == 200
        assert fs_config.validate_chunk_settings() == []  # No errors

        # Invalid configuration - overlap >= chunk_size
        invalid_config = {
            "enabled": True,
            "chunk_size": 500,
            "overlap": 500,  # Must be < chunk_size
        }

        with pytest.raises(Exception):  # ValidationError or similar
            validator.validate_file_search_config(invalid_config)


@pytest.mark.asyncio
class TestServiceContainerConfiguration:
    """Test service container configuration management."""

    async def test_service_container_validates_configurations_on_init(self):
        """Test that service container validates configurations during initialization."""
        mock_client = MagicMock(spec=AsyncOpenAI)

        # Valid configurations
        args = {
            "mcp_servers": [
                {"name": "test", "command": ["node", "server.js"]}
            ],
            "code_interpreter": True,
            "file_search": True,
        }

        container = ServiceContainer(mock_client, args)

        # Check that configurations were validated
        mcp_config = container.get_validated_config("mcp")
        assert isinstance(mcp_config, MCPServiceConfiguration)

        ci_config = container.get_validated_config("code_interpreter")
        assert isinstance(ci_config, CodeInterpreterServiceConfiguration)

        fs_config = container.get_validated_config("file_search")
        assert isinstance(fs_config, FileSearchServiceConfiguration)

    async def test_service_container_handles_invalid_configurations(self):
        """Test that service container handles invalid configurations gracefully."""
        mock_client = MagicMock(spec=AsyncOpenAI)

        # Invalid MCP configuration
        args = {
            "mcp_servers": [{"name": "test"}],  # Missing command
        }

        # Should not raise exception, but log warning
        container = ServiceContainer(mock_client, args)

        # Configuration should be None for invalid config
        mcp_config = container.get_validated_config("mcp")
        assert mcp_config is None

    async def test_service_health_checks(self):
        """Test service health check functionality."""
        mock_client = MagicMock(spec=AsyncOpenAI)
        mock_factory = MockServiceFactory()

        args = {
            "mcp_servers": [
                {"name": "test", "command": ["node", "server.js"]}
            ],
            "code_interpreter": True,
            "file_search": True,
        }

        container = ServiceContainer(mock_client, args, mock_factory)

        # Test individual health checks
        mcp_health = await container.check_service_health("mcp")
        assert mcp_health.status == ServiceStatus.HEALTHY
        assert "healthy" in mcp_health.message.lower()

        ci_health = await container.check_service_health("code_interpreter")
        assert ci_health.status == ServiceStatus.HEALTHY

        fs_health = await container.check_service_health("file_search")
        assert fs_health.status == ServiceStatus.HEALTHY

        # Test unconfigured service
        unconfigured_health = await container.check_service_health(
            "nonexistent"
        )
        assert unconfigured_health.status == ServiceStatus.UNKNOWN

        # Test all services health check
        all_health = await container.check_all_services_health()
        assert len(all_health) == 3  # All three services configured
        assert all(
            health.status == ServiceStatus.HEALTHY
            for health in all_health.values()
        )

    async def test_service_info_reporting(self):
        """Test service information reporting."""
        mock_client = MagicMock(spec=AsyncOpenAI)
        mock_factory = MockServiceFactory()

        args = {
            "mcp_servers": [
                {"name": "test", "command": ["node", "server.js"]}
            ],
            "code_interpreter": True,
            # file_search not configured
        }

        container = ServiceContainer(mock_client, args, mock_factory)

        # Get service info before creating managers
        service_info = container.get_service_info()

        assert service_info["mcp"]["configured"] is True
        assert service_info["mcp"]["validated"] is True
        assert service_info["mcp"]["has_manager"] is False  # Not created yet

        assert service_info["code_interpreter"]["configured"] is True
        assert service_info["code_interpreter"]["validated"] is True

        assert service_info["file_search"]["configured"] is False
        assert service_info["file_search"]["config_valid"] is None

        # Create a manager and check info again
        await container.get_mcp_manager()
        service_info_after = container.get_service_info()
        assert service_info_after["mcp"]["has_manager"] is True
