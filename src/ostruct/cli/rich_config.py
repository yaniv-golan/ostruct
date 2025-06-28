"""Rich-Click configuration for ostruct CLI.

This module configures rich-click to provide enhanced CLI help output with:
- Modern, clean visual styling
- Organized option groups with proper borders
- Professional color scheme suitable for enterprise use
- Structured layout optimized for readability

The configuration is designed to be easily extensible for future theme support.
"""

from typing import List

import rich_click as click

# ============================================================================
# RICH-CLICK CORE CONFIGURATION
# ============================================================================

# Enable rich markup and features
click.rich_click.USE_RICH_MARKUP = (
    True  # Enable [bold], [cyan], etc. in docstrings
)
click.rich_click.USE_MARKDOWN = True  # Enable markdown parsing in help text
click.rich_click.SHOW_ARGUMENTS = True  # Show arguments in help output
click.rich_click.GROUP_ARGUMENTS_OPTIONS = (
    True  # Group args and options separately
)
click.rich_click.SHOW_METAVARS_COLUMN = (
    False  # Don't show separate metavar column
)
click.rich_click.APPEND_METAVARS_HELP = True  # Append metavars to help text

# ============================================================================
# MODERN THEME STYLING - APPLIED IMMEDIATELY
# ============================================================================
# Based on our rich-click test - Modern/Vibrant theme with professional polish

# Text styling
click.rich_click.STYLE_HELPTEXT = ""  # Normal brightness (not dim)
click.rich_click.STYLE_HELPTEXT_FIRST_LINE = "bold"  # Bold first line of help
click.rich_click.STYLE_HEADER_TEXT = "bold"  # Bold section headers

# UI element styling
click.rich_click.STYLE_OPTION = "bright_blue"  # Bright blue option names
click.rich_click.STYLE_ARGUMENT = "bright_blue"  # Bright blue argument names
click.rich_click.STYLE_COMMAND = "bold blue"  # Bold blue command names
click.rich_click.STYLE_SWITCH = "bold green"  # Bold green boolean switches
click.rich_click.STYLE_METAVAR = "cyan"  # Cyan type hints
click.rich_click.STYLE_USAGE = "bold yellow"  # Bold yellow usage line

# Status and annotation styling
click.rich_click.STYLE_REQUIRED_SHORT = (
    "bold red"  # Bold red asterisk for required
)
click.rich_click.STYLE_OPTION_DEFAULT = (
    "dim cyan"  # Dim cyan for default values
)
click.rich_click.STYLE_DEPRECATED = "dim red"  # Dim red for deprecated options

# Panel and border styling
click.rich_click.STYLE_OPTIONS_PANEL_BORDER = (
    "blue"  # Blue borders around option groups
)
click.rich_click.STYLE_COMMANDS_PANEL_BORDER = (
    "blue"  # Blue borders around command groups
)
click.rich_click.STYLE_ERRORS_PANEL_BORDER = (
    "red"  # Red borders for error panels
)
click.rich_click.STYLE_ERRORS_SUGGESTION = "dim"  # Dim suggestions in errors

# Table styling for clean, professional look
click.rich_click.STYLE_OPTIONS_TABLE_SHOW_LINES = (
    False  # Clean look without table lines
)
click.rich_click.STYLE_OPTIONS_TABLE_PADDING = (0, 1)  # Minimal padding
click.rich_click.STYLE_OPTIONS_TABLE_BOX = ""  # No box borders around tables

# Width and layout settings
click.rich_click.MAX_WIDTH = 100  # Popular choice for readability
click.rich_click.WIDTH = None  # Use terminal width

# ============================================================================
# OPTION GROUPS CONFIGURATION
# ============================================================================
# Comprehensive option groups covering all ostruct CLI options

click.rich_click.OPTION_GROUPS = {
    "ostruct run": [
        {"name": "Template Data Options", "options": ["--var", "--json-var"]},
        {
            "name": "Model Configuration Options",
            "options": [
                "--model",
                "--temperature",
                "--max-output-tokens",
                "--top-p",
                "--frequency-penalty",
                "--presence-penalty",
                "--reasoning-effort",
            ],
        },
        {
            "name": "File Attachment Options",
            "options": [
                "--file",
                "--dir",
                "--collect",
                "--recursive",
                "--pattern",
            ],
        },
        {
            "name": "Tool Integration Options",
            "options": ["--enable-tool", "--disable-tool"],
        },
        {
            "name": "MCP Server Configuration",
            "options": [
                "--mcp-server",
                "--mcp-require-approval",
                "--mcp-headers",
            ],
        },
        {
            "name": "Code Interpreter Configuration",
            "options": [
                "--ci-cleanup",
                "--ci-duplicate-outputs",
                "--ci-download-dir",
            ],
        },
        {
            "name": "File Search Configuration",
            "options": [
                "--fs-timeout",
                "--fs-retries",
                "--fs-cleanup",
                "--fs-store-name",
            ],
        },
        {
            "name": "Web Search Configuration",
            "options": [
                "--ws-country",
                "--ws-city",
                "--ws-region",
                "--ws-context-size",
            ],
        },
        {
            "name": "System Prompt Options",
            "options": [
                "--sys-prompt",
                "--sys-prompt-file",
                "--sys-prompt-script",
                "--sys-prompt-template",
                "--sys-prompt-script-args",
            ],
        },
        {
            "name": "Output and Execution Options",
            "options": [
                "--output",
                "--dry-run",
                "--dry-run-json",
                "--run-summary-json",
            ],
        },
        {
            "name": "Configuration and API Options",
            "options": [
                "--config",
                "--api-key",
                "--base-url",
                "--organization",
                "--project",
                "--timeout",
            ],
        },
        {
            "name": "Security and Path Control Options",
            "options": [
                "--path-security",
                "--allow-paths",
                "--disallow-paths",
            ],
        },
        {
            "name": "Debug and Progress Options",
            "options": [
                "--template-debug",
                "--show-template",
                "--verbose",
                "--debug",
                "--progress",
            ],
        },
        {
            "name": "Experimental Features",
            "options": [
                "--enable-feature",
                "--disable-feature",
            ],
        },
    ]
}

# ============================================================================
# THEME EXTENSIBILITY (Future Enhancement)
# ============================================================================
# This structure makes it easy to add theme switching in the future


def apply_modern_theme() -> None:
    """Apply modern, clean theme with vibrant but professional colors."""
    # Text styling
    click.rich_click.STYLE_HELPTEXT = ""  # Normal brightness (not dim)
    click.rich_click.STYLE_HELPTEXT_FIRST_LINE = (
        "bold"  # Bold first line of help
    )
    click.rich_click.STYLE_HEADER_TEXT = "bold"  # Bold section headers

    # UI element styling
    click.rich_click.STYLE_OPTION = "bright_blue"  # Bright blue option names
    click.rich_click.STYLE_ARGUMENT = (
        "bright_blue"  # Bright blue argument names
    )
    click.rich_click.STYLE_COMMAND = "bold blue"  # Bold blue command names
    click.rich_click.STYLE_SWITCH = "bold green"  # Bold green boolean switches
    click.rich_click.STYLE_METAVAR = "cyan"  # Cyan type hints
    click.rich_click.STYLE_USAGE = "bold yellow"  # Bold yellow usage line

    # Status and annotation styling
    click.rich_click.STYLE_REQUIRED_SHORT = (
        "bold red"  # Bold red asterisk for required
    )
    click.rich_click.STYLE_OPTION_DEFAULT = (
        "dim cyan"  # Dim cyan for default values
    )
    click.rich_click.STYLE_DEPRECATED = (
        "dim red"  # Dim red for deprecated options
    )

    # Panel and border styling
    click.rich_click.STYLE_OPTIONS_PANEL_BORDER = (
        "blue"  # Blue borders around option groups
    )
    click.rich_click.STYLE_COMMANDS_PANEL_BORDER = (
        "blue"  # Blue borders around command groups
    )
    click.rich_click.STYLE_ERRORS_PANEL_BORDER = (
        "red"  # Red borders for error panels
    )
    click.rich_click.STYLE_ERRORS_SUGGESTION = (
        "dim"  # Dim suggestions in errors
    )

    # Table styling for clean, professional look
    click.rich_click.STYLE_OPTIONS_TABLE_SHOW_LINES = (
        False  # Clean look without table lines
    )
    click.rich_click.STYLE_OPTIONS_TABLE_PADDING = (0, 1)  # Minimal padding
    click.rich_click.STYLE_OPTIONS_TABLE_BOX = (
        ""  # No box borders around tables
    )

    # Width and layout settings
    click.rich_click.MAX_WIDTH = 100  # Popular choice for readability
    click.rich_click.WIDTH = None  # Use terminal width


def get_available_themes() -> List[str]:
    """Get list of available themes for future theme switching support."""
    return ["modern"]  # Currently only modern theme, easily extensible


def apply_theme(theme_name: str) -> bool:
    """Apply a specific theme by name.

    Args:
        theme_name: Name of theme to apply

    Returns:
        True if theme was applied successfully, False if theme not found
    """
    if theme_name == "modern":
        apply_modern_theme()
        return True
    return False


# Export public API for potential future use
__all__ = [
    "apply_modern_theme",
    "apply_theme",
    "get_available_themes",
]
