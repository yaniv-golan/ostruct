"""Template input sanitization to prevent injection attacks."""

import logging
import re

logger = logging.getLogger(__name__)


class TemplateSanitizer:
    """Sanitizes template content to prevent injection attacks."""

    # Patterns for detecting potentially dangerous template constructs
    DANGEROUS_PATTERNS = [
        # Jinja2 template syntax that could be injection attempts
        re.compile(
            r"{%\s*(?:exec|eval|import|from|__import__|compile)\s*%}",
            re.IGNORECASE,
        ),
        # Python code execution attempts
        re.compile(
            r"{{\s*(?:exec|eval|__import__|compile)\s*\(", re.IGNORECASE
        ),
        # Access to dangerous attributes
        re.compile(
            r"{{\s*[^}]*\.__(?:class|bases|subclasses|mro)__", re.IGNORECASE
        ),
        # File system access attempts
        re.compile(
            r"{{\s*[^}]*\.(?:open|read|write|system|popen)", re.IGNORECASE
        ),
        # Module access attempts
        re.compile(
            r"{{\s*[^}]*\.(?:sys|os|subprocess|importlib)", re.IGNORECASE
        ),
        # Dangerous built-ins access
        re.compile(
            r"{{\s*(?:globals|locals|vars|dir|getattr|setattr|delattr|hasattr)\s*\(",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def validate_template_content(cls, template_content: str) -> str:
        """Validate template content for dangerous patterns.

        Args:
            template_content: Template content to validate

        Returns:
            Validated template content

        Raises:
            ValueError: If template contains dangerous patterns
        """
        if not isinstance(template_content, str):
            raise ValueError("Template content must be a string")

        # Check for dangerous patterns in template itself
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(template_content):
                logger.warning(
                    f"Potentially dangerous pattern detected in template: {pattern.pattern}"
                )
                raise ValueError(
                    f"Template contains potentially dangerous syntax: {pattern.pattern}"
                )

        return template_content
