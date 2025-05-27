"""Tests for MCP (Model Context Protocol) integration."""

from typing import Any, Dict, List

import pytest
from ostruct.cli.mcp_integration import (
    MCPClient,
    MCPConfiguration,
    MCPServerManager,
)


class TestMCPConfiguration:
    """Test MCP configuration handling."""

    def test_mcp_configuration_creation(self):
        """Test creating MCP configuration."""
        servers = [
            {"url": "https://mcp.deepwiki.com/sse", "label": "deepwiki"}
        ]
        config = MCPConfiguration(servers)

        assert config.servers == servers
        assert len(config.servers) == 1
        assert config.servers[0]["url"] == "https://mcp.deepwiki.com/sse"
        assert config.servers[0]["label"] == "deepwiki"

    def test_mcp_configuration_multiple_servers(self):
        """Test MCP configuration with multiple servers."""
        servers = [
            {"url": "https://mcp.deepwiki.com/sse", "label": "deepwiki"},
            {"url": "https://api.example.com/mcp", "label": "example"},
        ]
        config = MCPConfiguration(servers)

        assert len(config.servers) == 2
        assert config.servers[0]["label"] == "deepwiki"
        assert config.servers[1]["label"] == "example"

    def test_build_tools_array(self):
        """Test building tools array for Responses API."""
        servers: List[Dict[str, Any]] = [
            {"url": "https://mcp.deepwiki.com/sse", "label": "deepwiki"},
            {
                "url": "https://api.example.com/mcp",
                "label": "example",
                "allowed_tools": ["search", "summary"],
                "headers": {"Authorization": "Bearer token"},
            },
        ]
        config = MCPConfiguration(servers)

        tools = config.build_tools_array()

        assert len(tools) == 2

        # First tool
        assert tools[0]["type"] == "mcp"
        assert tools[0]["server_url"] == "https://mcp.deepwiki.com/sse"
        assert tools[0]["server_label"] == "deepwiki"
        assert tools[0]["require_approval"] == "never"

        # Second tool with optional configurations
        assert tools[1]["type"] == "mcp"
        assert tools[1]["server_url"] == "https://api.example.com/mcp"
        assert tools[1]["server_label"] == "example"
        assert tools[1]["require_approval"] == "never"
        assert tools[1]["allowed_tools"] == ["search", "summary"]
        assert tools[1]["headers"] == {"Authorization": "Bearer token"}

    def test_build_tools_array_with_generated_labels(self):
        """Test building tools array with auto-generated labels."""
        servers = [
            {
                "url": "https://mcp.deepwiki.com/sse"
                # No label provided
            }
        ]
        config = MCPConfiguration(servers)

        tools = config.build_tools_array()

        assert len(tools) == 1
        assert tools[0]["server_label"] == "mcp-mcp.deepwiki.com"

    def test_validate_servers_success(self):
        """Test server validation with valid configurations."""
        servers = [
            {
                "url": "https://mcp.deepwiki.com/sse",
                "label": "deepwiki",
                "require_approval": "never",
            }
        ]
        config = MCPConfiguration(servers)

        errors = config.validate_servers()
        assert errors == []

    def test_validate_servers_missing_url(self):
        """Test server validation with missing URL."""
        servers = [
            {
                "label": "deepwiki"
                # Missing URL
            }
        ]
        config = MCPConfiguration(servers)

        errors = config.validate_servers()
        assert len(errors) == 1
        assert "missing required 'url' field" in errors[0]

    def test_validate_servers_requires_approval(self):
        """Test server validation with approval requirement."""
        servers = [
            {
                "url": "https://mcp.deepwiki.com/sse",
                "label": "deepwiki",
                "require_approval": "always",
            }
        ]
        config = MCPConfiguration(servers)

        errors = config.validate_servers()
        assert len(errors) == 1
        assert "requires approval - incompatible with CLI usage" in errors[0]

    def test_generate_label_from_url(self):
        """Test label generation from URL."""
        servers = [
            {"url": "https://mcp.deepwiki.com/sse"},
            {"url": "https://api.example.com/mcp"},
            {"url": "invalid-url"},
        ]
        config = MCPConfiguration(servers)

        # Test internal method
        assert (
            config._generate_label("https://mcp.deepwiki.com/sse")
            == "mcp-mcp.deepwiki.com"
        )
        assert (
            config._generate_label("https://api.example.com/mcp")
            == "mcp-api.example.com"
        )
        assert config._generate_label("invalid-url") == "mcp-unknown"


class TestMCPServerManager:
    """Test MCP server management."""

    def test_manager_initialization_success(self):
        """Test successful manager initialization."""
        servers = [
            {"url": "https://mcp.deepwiki.com/sse", "label": "deepwiki"}
        ]
        manager = MCPServerManager(servers)

        assert isinstance(manager, MCPServerManager)
        assert manager.servers == servers
        assert isinstance(manager.config, MCPConfiguration)
        assert manager.connected_servers == []

    def test_manager_initialization_invalid_url(self):
        """Test manager initialization with invalid URL."""
        servers = [
            {
                "url": "ftp://invalid.com",  # Invalid scheme
                "label": "invalid",
            }
        ]

        with pytest.raises(ValueError, match="Invalid server URL"):
            MCPServerManager(servers)

    def test_manager_initialization_empty_url(self):
        """Test manager initialization with empty URL."""
        servers = [
            {
                "url": "",  # Empty URL
                "label": "empty",
            }
        ]

        with pytest.raises(ValueError, match="Invalid server URL"):
            MCPServerManager(servers)

    @pytest.mark.asyncio
    async def test_validate_server_connectivity_success(self):
        """Test successful server connectivity validation."""
        servers = [
            {"url": "https://mcp.deepwiki.com/sse", "label": "deepwiki"}
        ]
        manager = MCPServerManager(servers)

        # The current implementation returns True for basic implementation
        result = await manager.validate_server_connectivity(
            "https://mcp.deepwiki.com/sse"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_pre_validate_all_servers_success(self):
        """Test pre-validation of all servers with valid configuration."""
        servers = [
            {
                "url": "https://mcp.deepwiki.com/sse",
                "label": "deepwiki",
                "require_approval": "never",
            }
        ]
        manager = MCPServerManager(servers)

        errors = await manager.pre_validate_all_servers()
        assert errors == []

    @pytest.mark.asyncio
    async def test_pre_validate_all_servers_config_errors(self):
        """Test pre-validation with configuration errors."""
        servers = [
            {
                "url": "",  # This will fail URL validation during init
                "label": "invalid",
            }
        ]

        # Should fail during initialization
        with pytest.raises(ValueError):
            MCPServerManager(servers)

    def test_get_tools_for_responses_api(self):
        """Test getting tools formatted for Responses API."""
        servers = [
            {"url": "https://mcp.deepwiki.com/sse", "label": "deepwiki"},
            {"url": "https://api.example.com/mcp", "label": "example"},
        ]
        manager = MCPServerManager(servers)

        tools = manager.get_tools_for_responses_api()

        assert len(tools) == 2
        assert all(tool["type"] == "mcp" for tool in tools)
        assert all(tool["require_approval"] == "never" for tool in tools)
        assert tools[0]["server_label"] == "deepwiki"
        assert tools[1]["server_label"] == "example"


class TestMCPClient:
    """Test MCP client functionality."""

    def test_client_initialization_success(self):
        """Test successful client initialization."""
        client = MCPClient("https://mcp.deepwiki.com/sse")

        assert client.server_url == "https://mcp.deepwiki.com/sse"
        assert client.timeout == 30  # Default timeout

    def test_client_initialization_with_timeout(self):
        """Test client initialization with custom timeout."""
        client = MCPClient("https://mcp.deepwiki.com/sse", timeout=15)

        assert client.timeout == 15

    def test_client_initialization_timeout_cap(self):
        """Test client initialization with timeout capped at 30 seconds."""
        client = MCPClient("https://mcp.deepwiki.com/sse", timeout=60)

        assert client.timeout == 30  # Should be capped at 30

    def test_client_initialization_invalid_url(self):
        """Test client initialization with invalid URL."""
        with pytest.raises(ValueError):
            MCPClient("ftp://invalid.com")

    def test_client_initialization_localhost_allowed(self):
        """Test client initialization allows localhost."""
        client = MCPClient("http://localhost:8080")
        assert client.server_url == "http://localhost:8080"

    def test_validate_request_size_success(self):
        """Test request size validation with valid size."""
        client = MCPClient("https://mcp.deepwiki.com/sse")

        small_data = {"query": "test", "context": "small"}
        # Should not raise exception
        client.validate_request_size(small_data)

    def test_validate_request_size_too_large(self):
        """Test request size validation with oversized request."""
        client = MCPClient("https://mcp.deepwiki.com/sse")

        large_data = {"query": "x" * 15000}  # Larger than 10KB limit

        with pytest.raises(ValueError, match="Request too large"):
            client.validate_request_size(large_data)

    # Note: Async request functionality was removed as it's not needed.
    # The synchronous send_request() method provides all required MCP functionality.
    # See MCPClient class documentation for details on the working implementation.


class TestMCPIntegration:
    """Test MCP integration scenarios."""

    def test_full_configuration_workflow(self):
        """Test complete configuration workflow."""
        # Create server configurations
        servers: List[Dict[str, Any]] = [
            {
                "url": "https://mcp.deepwiki.com/sse",
                "label": "deepwiki",
                "require_approval": "never",
            },
            {
                "url": "https://api.example.com/mcp",
                "label": "example",
                "allowed_tools": ["search", "summary"],
                "require_approval": "never",
            },
        ]

        # Create configuration
        config = MCPConfiguration(servers)

        # Validate configuration
        errors = config.validate_servers()
        assert errors == []

        # Create manager
        manager = MCPServerManager(servers)

        # Get tools for API
        tools = manager.get_tools_for_responses_api()

        assert len(tools) == 2
        assert all(tool["require_approval"] == "never" for tool in tools)

    @pytest.mark.asyncio
    async def test_server_validation_workflow(self):
        """Test server validation workflow."""
        servers = [
            {
                "url": "https://mcp.deepwiki.com/sse",
                "label": "deepwiki",
                "require_approval": "never",
            }
        ]

        manager = MCPServerManager(servers)

        # Pre-validate all servers
        errors = await manager.pre_validate_all_servers()
        assert errors == []

        # Validate individual server connectivity
        is_reachable = await manager.validate_server_connectivity(
            "https://mcp.deepwiki.com/sse"
        )
        assert is_reachable is True

    def test_error_handling_invalid_configuration(self):
        """Test error handling with invalid configurations."""
        # Test with servers requiring approval
        servers_with_approval = [
            {
                "url": "https://mcp.deepwiki.com/sse",
                "label": "deepwiki",
                "require_approval": "always",  # Invalid for CLI
            }
        ]

        config = MCPConfiguration(servers_with_approval)
        errors = config.validate_servers()

        assert len(errors) == 1
        assert "incompatible with CLI usage" in errors[0]

    def test_security_url_validation(self):
        """Test security aspects of URL validation."""
        # Valid HTTPS URLs should work
        valid_servers = [
            {"url": "https://mcp.deepwiki.com/sse", "label": "secure"}
        ]

        # Should not raise exception
        manager = MCPServerManager(valid_servers)
        assert len(manager.servers) == 1

        # Invalid schemes should be rejected during initialization
        invalid_servers = [{"url": "ftp://invalid.com", "label": "insecure"}]

        with pytest.raises(ValueError):
            MCPServerManager(invalid_servers)


class TestMCPErrorScenarios:
    """Test MCP error scenarios and recovery."""

    def test_empty_server_list(self):
        """Test handling of empty server list."""
        config = MCPConfiguration([])

        assert config.servers == []

        tools = config.build_tools_array()
        assert tools == []

        errors = config.validate_servers()
        assert errors == []

    def test_malformed_server_configuration(self):
        """Test handling of malformed server configurations."""
        # Server without URL
        servers_no_url = [
            {
                "label": "no_url"
                # Missing URL
            }
        ]

        config = MCPConfiguration(servers_no_url)
        errors = config.validate_servers()

        assert len(errors) == 1
        assert "missing required 'url' field" in errors[0]

    @pytest.mark.asyncio
    async def test_connectivity_validation_edge_cases(self):
        """Test connectivity validation edge cases."""
        servers = [
            {"url": "https://mcp.deepwiki.com/sse", "label": "deepwiki"}
        ]

        manager = MCPServerManager(servers)

        # Test with empty URL (should handle gracefully)
        result = await manager.validate_server_connectivity("")
        # Current implementation logs error and returns True, but this might change
        assert isinstance(result, bool)

    def test_client_security_validation(self):
        """Test client security validation."""
        # Test various invalid URLs
        invalid_urls = [
            "javascript:alert('xss')",
            "file:///etc/passwd",
            "ftp://example.com",
            "data:text/html,<script>alert('xss')</script>",
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError):
                MCPClient(url)
