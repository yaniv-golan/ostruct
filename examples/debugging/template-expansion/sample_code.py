#!/usr/bin/env python3
"""
Template debugging sample code
This file demonstrates debugging with code file analysis
"""

from typing import List, Dict, Any
import logging
import yaml


class TemplateDebugger:
    """Example class for template debugging demonstration."""

    def __init__(self, config_path: str):
        """Initialize debugger with configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {self.config_path}")
            return {}

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger(__name__)

        level = self.config.get("settings", {}).get("log_level", "info")
        logger.setLevel(getattr(logging, level.upper()))

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def analyze_template(self, template_content: str) -> Dict[str, Any]:
        """Analyze template content for debugging."""
        self.logger.info("Starting template analysis")

        analysis = {
            "length": len(template_content),
            "lines": len(template_content.split("\n")),
            "variables": self._extract_variables(template_content),
            "blocks": self._extract_blocks(template_content),
        }

        self.logger.info(f"Analysis complete: {analysis}")
        return analysis

    def _extract_variables(self, content: str) -> List[str]:
        """Extract Jinja2 variables from template content."""
        import re

        pattern = r"\{\{\s*([^}]+)\s*\}\}"
        matches = re.findall(pattern, content)
        return [match.strip() for match in matches]

    def _extract_blocks(self, content: str) -> List[str]:
        """Extract Jinja2 blocks from template content."""
        import re

        pattern = r"\{%\s*(\w+)"
        matches = re.findall(pattern, content)
        return list(set(matches))


def main():
    """Main function for demonstration."""
    debugger = TemplateDebugger("example_config.yaml")

    sample_template = """
    Hello {{ user_name }}!
    {% for item in items %}
    - {{ item }}
    {% endfor %}
    """

    result = debugger.analyze_template(sample_template)
    print(f"Template analysis result: {result}")


if __name__ == "__main__":
    main()
