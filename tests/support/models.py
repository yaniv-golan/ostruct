"""Support models for test fixtures."""

import pytest
from pydantic import BaseModel, Field


@pytest.mark.no_collect
class BasicMessage(BaseModel):  # type: ignore[misc]
    """Basic message model for testing."""

    message: str
    sentiment: str


@pytest.mark.no_collect
class ResponseMessage(BaseModel):  # type: ignore[misc]
    """Response message model."""

    message: str
    sentiment: str


@pytest.mark.no_collect
class SimpleMessage(BaseModel):  # type: ignore[misc]
    """Simple schema for testing basic responses."""

    message: str


@pytest.mark.no_collect
class SentimentMessage(BaseModel):  # type: ignore[misc]
    """Response model for sentiment analysis."""

    message: str = Field(..., description="The analyzed message")
    sentiment: str = Field(
        ...,
        pattern="(?i)^(positive|negative|neutral|mixed)$",
        description="Sentiment of the message",
    )
