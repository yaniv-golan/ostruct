"""Render context for tracking template-time attachments and embeddings."""

import asyncio
import contextvars
import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class RenderContext:
    """Tracks attachments and embeddings during template rendering."""

    # Files requested for binary attachment (vision/CI)
    attached_files: Set[str] = field(default_factory=set)

    # Aliases requested for text embedding (XML appendix)
    embedded_aliases: Set[str] = field(default_factory=set)

    # Labels referenced in text (for lint validation)
    referenced_labels: Set[str] = field(default_factory=set)

    # Thread safety for concurrent renders
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def register_attachment(self, file_path: str) -> None:
        """Register a file for binary attachment (uses canonical path)."""
        # Use os.path.realpath for consistent canonical paths across platforms
        canonical_path = os.path.realpath(str(file_path))
        self.attached_files.add(canonical_path)
        logger.debug(f"Registered attachment: {file_path} -> {canonical_path}")

    def register_embedding(self, alias: str) -> None:
        """Register an alias for text embedding."""
        self.embedded_aliases.add(alias)
        logger.debug(f"Registered embedding: {alias}")

    def register_label_reference(self, label: str) -> None:
        """Register a label reference for lint validation."""
        self.referenced_labels.add(label)
        logger.debug(f"Registered label reference: {label}")

    def clear(self) -> None:
        """Clear all tracked data for new render."""
        self.attached_files.clear()
        self.embedded_aliases.clear()
        self.referenced_labels.clear()


# Context variable for async-local tracking (handles concurrent renders)
_render_context_var: contextvars.ContextVar[Optional[RenderContext]] = (
    contextvars.ContextVar("render_context", default=None)
)

# Global fallback for CLI usage
_global_render_context: Optional[RenderContext] = None


def get_render_context() -> RenderContext:
    """Get the current render context (async-local or global fallback)."""
    # Try async-local context first (for concurrent renders)
    context = _render_context_var.get(None)
    if context is not None:
        return context

    # Fall back to global context for CLI usage
    global _global_render_context
    if _global_render_context is None:
        _global_render_context = RenderContext()
    return _global_render_context


def set_render_context(context: RenderContext) -> None:
    """Set the render context for the current async context."""
    _render_context_var.set(context)


def clear_render_context() -> None:
    """Clear the render context."""
    # Clear async-local context
    _render_context_var.set(None)

    # Clear global context
    global _global_render_context
    if _global_render_context:
        _global_render_context.clear()
