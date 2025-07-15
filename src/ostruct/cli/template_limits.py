"""Template size limits and DoS protection."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default limits for template processing to prevent DoS attacks
DEFAULT_TEMPLATE_SIZE_LIMIT = 100 * 1024 * 1024  # 100MB
DEFAULT_TEMPLATE_TOTAL_LIMIT = 500 * 1024 * 1024  # 500MB


class TemplateSizeError(ValueError):
    """Raised when template content exceeds size limits."""

    pass


class TemplateTotalSizeError(ValueError):
    """Raised when total template content exceeds size limits."""

    pass


class TemplateSizeValidator:
    """Validates template content size to prevent DoS attacks."""

    def __init__(
        self,
        max_template_size: Optional[int] = None,
        max_total_size: Optional[int] = None,
    ):
        """Initialize template size validator.

        Args:
            max_template_size: Maximum size for individual template content in bytes
            max_total_size: Maximum total size for all template content in bytes
        """
        self.max_template_size = (
            max_template_size or DEFAULT_TEMPLATE_SIZE_LIMIT
        )
        self.max_total_size = max_total_size or DEFAULT_TEMPLATE_TOTAL_LIMIT
        self.total_size_consumed = 0

    def validate_template_content(
        self, content: str, template_name: str = "template"
    ) -> None:
        """Validate template content size.

        Args:
            content: Template content to validate
            template_name: Name of the template for error messages

        Raises:
            TemplateSizeError: If content exceeds individual size limits
            TemplateTotalSizeError: If total content exceeds total size limits
        """
        content_size = len(content.encode("utf-8"))

        # Check individual template size
        if self.max_template_size and content_size > self.max_template_size:
            raise TemplateSizeError(
                f"Template '{template_name}' too large: {content_size} bytes "
                f"(max: {self.max_template_size} bytes)"
            )

        # Check total size
        new_total = self.total_size_consumed + content_size
        if self.max_total_size and new_total > self.max_total_size:
            raise TemplateTotalSizeError(
                f"Total template content too large: {new_total} bytes "
                f"(max: {self.max_total_size} bytes) after adding '{template_name}'"
            )

        # Update total size consumed
        self.total_size_consumed = new_total

        logger.debug(
            f"Template '{template_name}' validated: {content_size} bytes "
            f"(total: {self.total_size_consumed} bytes)"
        )

    def validate_rendered_template(self, rendered_content: str) -> None:
        """Validate final rendered template content.

        Args:
            rendered_content: Final rendered template content

        Raises:
            TemplateSizeError: If rendered content exceeds size limits
        """
        content_size = len(rendered_content.encode("utf-8"))

        # Use the larger of individual or total limit for final validation
        max_limit = max(self.max_template_size or 0, self.max_total_size or 0)

        if max_limit and content_size > max_limit:
            raise TemplateSizeError(
                f"Rendered template too large: {content_size} bytes "
                f"(max: {max_limit} bytes)"
            )

        logger.debug(f"Rendered template validated: {content_size} bytes")

    def reset(self) -> None:
        """Reset the validator for reuse."""
        self.total_size_consumed = 0


# Global validator instance
_default_validator = TemplateSizeValidator()


def validate_template_size(
    content: str,
    template_name: str = "template",
    max_size: Optional[int] = None,
    max_total_size: Optional[int] = None,
) -> None:
    """Validate template content size with global or custom limits.

    Args:
        content: Template content to validate
        template_name: Name of the template for error messages
        max_size: Maximum individual template size (None for default)
        max_total_size: Maximum total template size (None for default)

    Raises:
        TemplateSizeError: If content exceeds size limits
        TemplateTotalSizeError: If total content exceeds total size limits
    """
    if max_size is None and max_total_size is None:
        # Use default validator
        _default_validator.validate_template_content(content, template_name)
    else:
        # Create custom validator
        validator = TemplateSizeValidator(max_size, max_total_size)
        validator.validate_template_content(content, template_name)


def validate_rendered_template_size(
    rendered_content: str,
    max_size: Optional[int] = None,
) -> None:
    """Validate final rendered template size.

    Args:
        rendered_content: Final rendered template content
        max_size: Maximum template size (None for default)

    Raises:
        TemplateSizeError: If rendered content exceeds size limits
    """
    if max_size is None:
        _default_validator.validate_rendered_template(rendered_content)
    else:
        validator = TemplateSizeValidator(max_size, max_size)
        validator.validate_rendered_template(rendered_content)


def reset_global_validator() -> None:
    """Reset the global validator for reuse."""
    _default_validator.reset()


def get_template_size_limits() -> tuple[Optional[int], Optional[int]]:
    """Get current template size limits.

    Returns:
        Tuple of (max_template_size, max_total_size)
    """
    return (
        _default_validator.max_template_size,
        _default_validator.max_total_size,
    )
