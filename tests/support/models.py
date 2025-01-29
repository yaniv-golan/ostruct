"""Support models for test fixtures."""

from dataclasses import dataclass
from typing import Optional

import pytest
from pydantic import BaseModel, Field


@pytest.mark.no_collect
class BasicMessage(BaseModel):
    """Basic message model for testing."""

    message: str
    sentiment: str


@pytest.mark.no_collect
class ResponseMessage(BaseModel):
    """Response message model."""

    message: str
    sentiment: str


@pytest.mark.no_collect
class SimpleMessage(BaseModel):
    """Simple schema for testing basic responses."""

    message: str


@pytest.mark.no_collect
class SentimentMessage(BaseModel):
    """Response model for sentiment analysis."""

    message: str = Field(..., description="The analyzed message")
    sentiment: str = Field(
        ...,
        pattern="(?i)^(positive|negative|neutral|mixed)$",
        description="Sentiment of the message",
    )


@dataclass
class SimpleModel:
    """Simple model for testing."""

    name: str
    value: int


@dataclass
class NestedModel:
    """Model with nested attributes for testing."""

    id: str
    simple: SimpleModel


@dataclass
class OptionalModel:
    """Model with optional fields for testing."""

    name: str
    value: Optional[int] = None


@dataclass
class ComplexModel:
    """Model with multiple fields and nesting for testing."""

    id: str
    name: str
    nested: Optional[NestedModel] = None
