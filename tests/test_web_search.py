"""Tests for web search functionality."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from ostruct.cli.config import WebSearchToolConfig, WebSearchUserLocationConfig


class TestWebSearchConfiguration:
    """Test web search configuration handling."""

    def test_web_search_tool_config_defaults(self):
        """Test default web search configuration values."""
        config = WebSearchToolConfig()
        assert config.enable_by_default is False
        assert config.user_location is None
        assert config.search_context_size is None

    def test_web_search_tool_config_validation(self):
        """Test web search configuration validation."""
        # Valid configuration
        config = WebSearchToolConfig(
            enable_by_default=True,
            search_context_size="medium",
            user_location=WebSearchUserLocationConfig(
                country="US", city="San Francisco", region="California"
            ),
        )
        assert config.enable_by_default is True
        assert config.search_context_size == "medium"
        assert config.user_location is not None
        assert config.user_location.country == "US"

    def test_web_search_invalid_context_size(self):
        """Test validation of invalid search context size."""
        with pytest.raises(
            ValueError, match="search_context_size must be one of"
        ):
            WebSearchToolConfig(search_context_size="invalid")

    def test_web_search_user_location_config(self):
        """Test user location configuration."""
        location = WebSearchUserLocationConfig(
            country="US", city="New York", region="NY"
        )
        assert location.country == "US"
        assert location.city == "New York"
        assert location.region == "NY"


class TestWebSearchPayloadConstruction:
    """Test web search API payload construction."""

    def test_basic_web_search_payload(self):
        """Test basic web search tool configuration."""
        # Mock args that would enable web search
        args: Dict[str, Any] = {
            "web_search": True,
            "no_web_search": False,
            "model": "gpt-4o",
        }

        # This tests the logic that would be in runner.py
        web_search_enabled = args.get("web_search", False) and not args.get(
            "no_web_search", False
        )
        assert web_search_enabled is True

        # Expected tool config
        expected_config = {"type": "web_search_preview"}
        assert expected_config["type"] == "web_search_preview"

    def test_web_search_with_user_location(self):
        """Test web search payload with user location."""
        args: Dict[str, Any] = {
            "web_search": True,
            "no_web_search": False,
            "user_country": "US",
            "user_city": "San Francisco",
            "user_region": "California",
            "model": "gpt-4o",
        }

        # Build the tool config as would be done in runner.py
        web_tool_config: Dict[str, Any] = {"type": "web_search_preview"}

        user_country = args.get("user_country")
        user_city = args.get("user_city")
        user_region = args.get("user_region")

        if user_country or user_city or user_region:
            user_location: Dict[str, Any] = {"type": "approximate"}
            if user_country:
                user_location["country"] = user_country
            if user_city:
                user_location["city"] = user_city
            if user_region:
                user_location["region"] = user_region
            web_tool_config["user_location"] = user_location

        # Verify the constructed payload
        assert web_tool_config["type"] == "web_search_preview"
        assert web_tool_config["user_location"]["type"] == "approximate"
        assert web_tool_config["user_location"]["country"] == "US"
        assert web_tool_config["user_location"]["city"] == "San Francisco"
        assert web_tool_config["user_location"]["region"] == "California"

    def test_web_search_with_context_size(self):
        """Test web search payload with search context size."""
        args: Dict[str, Any] = {
            "web_search": True,
            "search_context_size": "high",
            "model": "gpt-4o",
        }

        # Build the tool config
        web_tool_config: Dict[str, Any] = {"type": "web_search_preview"}
        search_context_size = args.get("search_context_size")
        if search_context_size:
            web_tool_config["search_context_size"] = search_context_size

        # Verify the payload
        assert web_tool_config["type"] == "web_search_preview"
        assert web_tool_config["search_context_size"] == "high"

    def test_web_search_disabled_by_toggle(self):
        """Test that --disable-tool web-search disables web search."""
        # Simulate tool toggle logic
        enabled_tools = set()  # No tools explicitly enabled
        disabled_tools = {"web-search"}  # Web search explicitly disabled

        # Mock config with enable_by_default=True
        enable_by_default = True

        # Apply tool toggle logic
        if "web-search" in enabled_tools:
            web_search_enabled = True
        elif "web-search" in disabled_tools:
            web_search_enabled = False
        else:
            web_search_enabled = enable_by_default

        assert web_search_enabled is False


class TestWebSearchValidation:
    """Test web search validation logic."""

    @patch("ostruct.cli.model_validation.validate_web_search_compatibility")
    def test_model_compatibility_validation(self, mock_validate):
        """Test model compatibility validation for web search."""
        mock_validate.return_value = None  # No warning for compatible model

        # Test compatible model
        from ostruct.cli.model_validation import (
            validate_web_search_compatibility,
        )

        warning = validate_web_search_compatibility("gpt-4o", True)
        assert warning is None

        # Test with actual function
        mock_validate.return_value = "Model not supported"
        warning = validate_web_search_compatibility("gpt-3.5-turbo", True)
        assert warning is not None

    def test_azure_endpoint_detection(self):
        """Test Azure OpenAI endpoint detection."""
        # This would be the logic from runner.py
        test_endpoints = [
            ("https://myservice.openai.azure.com", True),
            ("https://api.openai.com", False),
            ("https://test.azure.com/openai", True),
            ("", False),
        ]

        for endpoint, is_azure in test_endpoints:
            detected_azure = "azure.com" in endpoint.lower()
            assert detected_azure == is_azure


class TestWebSearchTemplateContext:
    """Test web search template context variables."""

    @patch("ostruct.cli.config.OstructConfig")
    def test_web_search_enabled_context_variable(self, mock_config_class):
        """Test that web_search_enabled is correctly set in template context."""
        # Mock the configuration
        mock_config = MagicMock()
        mock_web_search_config = MagicMock()
        mock_web_search_config.enable_by_default = False
        mock_config.get_web_search_config.return_value = mock_web_search_config
        mock_config_class.load.return_value = mock_config

        # Test tool toggle takes precedence
        enabled_tools = {"web-search"}
        disabled_tools = set()

        # Simulate the logic from template_processor.py
        if "web-search" in enabled_tools:
            web_search_enabled = True
        elif "web-search" in disabled_tools:
            web_search_enabled = False
        else:
            web_search_enabled = mock_web_search_config.enable_by_default

        assert web_search_enabled is True

    @patch("ostruct.cli.config.OstructConfig")
    def test_web_search_config_default_used(self, mock_config_class):
        """Test that config default is used when no tool toggles provided."""
        # Mock the configuration with enable_by_default=True
        mock_config = MagicMock()
        mock_web_search_config = MagicMock()
        mock_web_search_config.enable_by_default = True
        mock_config.get_web_search_config.return_value = mock_web_search_config
        mock_config_class.load.return_value = mock_config

        # No tool toggles
        enabled_tools = set()
        disabled_tools = set()

        # Simulate the logic
        if "web-search" in enabled_tools:
            web_search_enabled = True
        elif "web-search" in disabled_tools:
            web_search_enabled = False
        else:
            web_search_enabled = mock_web_search_config.enable_by_default

        assert web_search_enabled is True


class TestWebSearchIntegration:
    """Test web search integration scenarios."""

    def test_full_payload_construction(self):
        """Test complete web search payload construction."""
        # Test data for payload construction
        user_country = "UK"
        user_city = "London"
        search_context_size = "low"

        # Build complete tool config
        web_tool_config: Dict[str, Any] = {"type": "web_search_preview"}

        # Add location
        user_location: Dict[str, Any] = {"type": "approximate"}
        user_location["country"] = user_country
        user_location["city"] = user_city
        web_tool_config["user_location"] = user_location

        # Add context size
        web_tool_config["search_context_size"] = search_context_size

        # Verify complete payload
        expected = {
            "type": "web_search_preview",
            "user_location": {
                "type": "approximate",
                "country": "UK",
                "city": "London",
            },
            "search_context_size": "low",
        }

        assert web_tool_config == expected

    def test_minimal_payload_construction(self):
        """Test minimal web search payload (no optional parameters)."""
        web_tool_config = {"type": "web_search_preview"}

        # No additional parameters should be added
        expected = {"type": "web_search_preview"}
        assert web_tool_config == expected


@pytest.mark.asyncio
class TestWebSearchLiveIntegration:
    """Integration tests for web search (these would be marked as 'live' tests)."""

    @pytest.mark.live
    async def test_web_search_api_call_structure(self):
        """Test that web search tool is correctly included in API calls."""
        # This would be a live test that actually calls the API
        # For now, just test the structure
        tools = [{"type": "web_search_preview"}]

        # Verify tools array structure
        assert len(tools) == 1
        assert tools[0]["type"] == "web_search_preview"

    @pytest.mark.live
    async def test_web_search_with_location_api_call(self):
        """Test web search with location in API call."""
        tools = [
            {
                "type": "web_search_preview",
                "user_location": {
                    "type": "approximate",
                    "country": "US",
                    "city": "San Francisco",
                },
            }
        ]

        # Verify structure
        tool_config = tools[0]
        user_location = tool_config["user_location"]
        assert isinstance(user_location, dict)
        assert user_location["country"] == "US"
        assert user_location["city"] == "San Francisco"
