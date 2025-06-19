"""Click command and options for the CLI.

This module contains all Click-related code separated from the main CLI logic.
We isolate this code here and provide proper type annotations for Click's
decorator-based API.
"""

import logging
from typing import Any, Callable, List, TypeVar, Union, cast

import click
from click import Command
from typing_extensions import ParamSpec

from ostruct import __version__
from ostruct.cli.errors import (  # noqa: F401 - Used in error handling
    SystemPromptError,
    TaskTemplateVariableError,
)
from ostruct.cli.validators import validate_json_variable, validate_variable

from .help_json import print_command_help_json as print_help_json

P = ParamSpec("P")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])
CommandDecorator = Callable[[F], Command]
DecoratedCommand = Union[Command, Callable[..., Any]]

logger = logging.getLogger(__name__)


def get_available_models() -> List[str]:
    """Get list of available models from registry that support structured output.

    Returns:
        Sorted list of model names that support structured output

    Note:
        Registry handles its own caching internally.
        Falls back to basic model list if registry fails.
    """
    try:
        from openai_model_registry import ModelRegistry

        registry = ModelRegistry.get_instance()
        all_models = list(registry.models)

        # Filter to only models that support structured output
        supported_models = []
        for model in all_models:
            try:
                capabilities = registry.get_capabilities(model)
                if getattr(capabilities, "supports_structured_output", True):
                    supported_models.append(model)
            except Exception:
                continue

        return (
            sorted(supported_models)
            if supported_models
            else _get_fallback_models()
        )

    except Exception as e:
        logger.debug(f"Failed to load models from registry: {e}")
        return _get_fallback_models()


def _get_fallback_models() -> List[str]:
    """Fallback model list when registry is unavailable."""
    return ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o3-mini"]


class ModelChoice(click.Choice):
    """Custom Choice type with better error messages for models."""

    def convert(
        self,
        value: Any,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> str:
        try:
            return super().convert(value, param, ctx)
        except click.BadParameter:
            choices_list = list(self.choices)
            available = ", ".join(choices_list[:5])
            more_count = len(choices_list) - 5
            more_text = f" (and {more_count} more)" if more_count > 0 else ""

            raise click.BadParameter(
                f"Invalid model '{value}'. Available models: {available}{more_text}.\n"
                f"Run 'ostruct list-models' to see all {len(choices_list)} available models."
            )


def create_model_choice() -> ModelChoice:
    """Create a ModelChoice object for model selection with error handling."""
    try:
        models = get_available_models()
        if not models:
            raise ValueError("No models available")
        return ModelChoice(models, case_sensitive=True)
    except Exception as e:
        logger.warning(f"Failed to load dynamic model list: {e}")
        logger.warning("Falling back to basic model validation")

        fallback_models = _get_fallback_models()
        return ModelChoice(fallback_models, case_sensitive=True)


def parse_feature_flags(
    enabled_features: tuple[str, ...], disabled_features: tuple[str, ...]
) -> dict[str, str]:
    """Parse feature flags from CLI arguments.

    Args:
        enabled_features: Tuple of feature names to enable
        disabled_features: Tuple of feature names to disable

    Returns:
        Dictionary mapping feature names to "on" or "off"

    Raises:
        click.BadParameter: If flag format is invalid or conflicts exist
    """
    parsed = {}

    # Process enabled features
    for feature in enabled_features:
        feature = feature.strip()
        if not feature:
            raise click.BadParameter("Feature name cannot be empty")

        # Validate known feature flags
        if feature == "ci-download-hack":
            parsed[feature] = "on"
        else:
            raise click.BadParameter(f"Unknown feature: {feature}")

    # Process disabled features
    for feature in disabled_features:
        feature = feature.strip()
        if not feature:
            raise click.BadParameter("Feature name cannot be empty")

        # Check for conflicts
        if feature in parsed:
            raise click.BadParameter(
                f"Feature '{feature}' cannot be both enabled and disabled"
            )

        # Validate known feature flags
        if feature == "ci-download-hack":
            parsed[feature] = "off"
        else:
            raise click.BadParameter(f"Unknown feature: {feature}")

    return parsed


# Helper functions moved to help_json.py for unified help system


def debug_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add debug-related CLI options."""
    # Initial conversion to Command if needed
    cmd: Any = f if isinstance(f, Command) else f

    # Add options without redundant casts
    cmd = click.option(
        "--show-model-schema",
        is_flag=True,
        help="Show generated Pydantic model schema",
    )(cmd)

    cmd = click.option(
        "--debug-validation",
        is_flag=True,
        help="Show detailed validation errors",
    )(cmd)

    cmd = click.option(
        "--debug",
        is_flag=True,
        help="🐛 Enable debug-level logging including template expansion",
    )(cmd)

    cmd = click.option(
        "--show-templates",
        is_flag=True,
        help="📝 Show expanded templates before sending to API",
    )(cmd)

    cmd = click.option(
        "--debug-templates",
        is_flag=True,
        help="🔍 Enable detailed template expansion debugging with step-by-step analysis",
    )(cmd)

    cmd = click.option(
        "--show-context",
        is_flag=True,
        help="📋 Show template variable context summary",
    )(cmd)

    cmd = click.option(
        "--show-context-detailed",
        is_flag=True,
        help="📋 Show detailed template variable context with content preview",
    )(cmd)

    cmd = click.option(
        "--show-pre-optimization",
        is_flag=True,
        help="🔧 Show template content before optimization is applied",
    )(cmd)

    cmd = click.option(
        "--show-optimization-diff",
        is_flag=True,
        help="🔄 Show template optimization changes (before/after comparison)",
    )(cmd)

    cmd = click.option(
        "--no-optimization",
        is_flag=True,
        help="⚡ Skip template optimization entirely for debugging",
    )(cmd)

    cmd = click.option(
        "--show-optimization-steps",
        is_flag=True,
        help="🔧 Show detailed optimization step tracking with before/after changes",
    )(cmd)

    cmd = click.option(
        "--optimization-step-detail",
        type=click.Choice(["summary", "detailed"]),
        default="summary",
        help="📊 Level of optimization step detail (summary shows overview, detailed shows full diffs)",
    )(cmd)

    cmd = click.option(
        "--help-debug",
        is_flag=True,
        help="📚 Show comprehensive template debugging help and examples",
    )(cmd)

    # Final cast to Command for return type
    return cast(Command, cmd)


def variable_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add variable-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "-V",
        "--var",
        "var",
        multiple=True,
        metavar="name=value",
        callback=validate_variable,
        help="""🏷️  [VARIABLES] Define a simple string variable for template substitution.
        Variables are available in your template as {{ variable_name }}.
        Format: name=value
        Example: -V debug=true -V env=prod""",
    )(cmd)

    cmd = click.option(
        "-J",
        "--json-var",
        "json_var",
        multiple=True,
        metavar='name=\'{"json":"value"}\'',
        callback=validate_json_variable,
        help="""📋 [VARIABLES] Define a JSON variable for complex data structures.
        JSON variables are parsed and available in templates as structured objects.
        Format: name='{"key":"value"}'
        Example: -J config='{"env":"prod","debug":true}'""",
    )(cmd)

    return cast(Command, cmd)


def model_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add model-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Create model choice with enhanced error handling
    model_choice = create_model_choice()

    # Ensure default is in the list
    default_model = "gpt-4o"
    choices_list = list(model_choice.choices)
    if default_model not in choices_list and choices_list:
        default_model = choices_list[0]

    cmd = click.option(
        "-m",
        "--model",
        type=model_choice,
        default=default_model,
        show_default=True,
        help="OpenAI model to use. Must support structured output.",
    )(cmd)

    cmd = click.option(
        "--temperature",
        type=click.FloatRange(0.0, 2.0),
        help="""Sampling temperature. Controls randomness in the output.
        Range: 0.0 to 2.0. Lower values are more focused.""",
    )(cmd)

    cmd = click.option(
        "--max-output-tokens",
        type=click.IntRange(1, None),
        help="""Maximum number of tokens in the output.
        Higher values allow longer responses but cost more.""",
    )(cmd)

    cmd = click.option(
        "--top-p",
        type=click.FloatRange(0.0, 1.0),
        help="""Top-p (nucleus) sampling parameter. Controls diversity.
        Range: 0.0 to 1.0. Lower values are more focused.""",
    )(cmd)

    cmd = click.option(
        "--frequency-penalty",
        type=click.FloatRange(-2.0, 2.0),
        help="""Frequency penalty for text generation.
        Range: -2.0 to 2.0. Positive values reduce repetition.""",
    )(cmd)

    cmd = click.option(
        "--presence-penalty",
        type=click.FloatRange(-2.0, 2.0),
        help="""Presence penalty for text generation.
        Range: -2.0 to 2.0. Positive values encourage new topics.""",
    )(cmd)

    cmd = click.option(
        "--reasoning-effort",
        type=click.Choice(["low", "medium", "high"]),
        help="""Control reasoning effort (if supported by model).
        Higher values may improve output quality but take longer.""",
    )(cmd)

    return cast(Command, cmd)


def system_prompt_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add system prompt related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--sys-prompt",
        "system_prompt",
        help="""Provide system prompt directly. This sets the initial context
        for the model. Example: --sys-prompt "You are a code reviewer." """,
    )(cmd)

    cmd = click.option(
        "--sys-file",
        "system_prompt_file",
        type=click.Path(exists=True, dir_okay=False),
        help="""Load system prompt from file. The file should contain the prompt text.
        Example: --sys-file prompts/code_review.txt""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "--ignore-task-sysprompt",
        is_flag=True,
        help="""Ignore system prompt in task template. By default, system prompts
        in template frontmatter are used.""",
    )(cmd)

    return cast(Command, cmd)


def output_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add output-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--output-file",
        type=click.Path(dir_okay=False),
        help="""Write output to file instead of stdout.
        Example: --output-file result.json""",
        shell_complete=click.Path(file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "--dry-run",
        is_flag=True,
        help="""Validate and render but skip API call. Useful for testing
        template rendering and validation.""",
    )(cmd)

    # JSON output options per unified guidelines
    cmd = click.option(
        "--dry-run-json",
        is_flag=True,
        help="""Output execution plan as JSON (requires --dry-run).
        Outputs structured execution plan to stdout for programmatic consumption.""",
    )(cmd)

    cmd = click.option(
        "--run-summary-json",
        is_flag=True,
        help="""Output run summary as JSON to stderr (cannot be used with --dry-run).
        Provides machine-readable execution summary after live runs.""",
    )(cmd)

    return cast(Command, cmd)


def api_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add API-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--config",
        type=click.Path(exists=True),
        help="Configuration file path (default: ostruct.yaml)",
    )(cmd)

    cmd = click.option(
        "--api-key",
        help="""OpenAI API key. If not provided, uses OPENAI_API_KEY
        environment variable.""",
    )(cmd)

    # API timeout for OpenAI calls
    cmd = click.option(
        "--timeout",
        type=click.FloatRange(1.0, None),
        default=60.0,
        show_default=True,
        help="Timeout in seconds for OpenAI API calls.",
    )(cmd)

    return cast(Command, cmd)


def mcp_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add MCP (Model Context Protocol) server CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--mcp-server",
        "mcp_servers",
        multiple=True,
        help="""🔌 [MCP] Connect to Model Context Protocol server for extended capabilities.
        MCP servers provide additional tools like web search, databases, APIs, etc.
        Format: [label@]url
        Example: --mcp-server deepwiki@https://mcp.deepwiki.com/sse""",
    )(cmd)

    cmd = click.option(
        "--mcp-allowed-tools",
        "mcp_allowed_tools",
        multiple=True,
        help="""Allowed tools per server. Format: server_label:tool1,tool2
        Example: --mcp-allowed-tools deepwiki:search,summary""",
    )(cmd)

    cmd = click.option(
        "--mcp-require-approval",
        type=click.Choice(["always", "never"]),
        default="never",
        show_default=True,
        help="""Approval level for MCP tool usage. CLI usage requires 'never'.""",
    )(cmd)

    cmd = click.option(
        "--mcp-headers",
        help="""JSON string of headers for MCP servers.
        Example: --mcp-headers '{"Authorization": "Bearer token"}'""",
    )(cmd)

    return cast(Command, cmd)


def feature_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add feature flag and configuration options (without legacy file routing)."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--ci-download-dir",
        type=click.Path(file_okay=False, dir_okay=True),
        default="./downloads",
        show_default=True,
        help="""🤖 [CODE INTERPRETER] Directory to save files generated by Code Interpreter.
        Example: --ci-download-dir ./results""",
        shell_complete=click.Path(file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "--ci-cleanup",
        is_flag=True,
        default=True,
        show_default=True,
        help="""🤖 [CODE INTERPRETER] Clean up uploaded files after execution to save storage quota.""",
    )(cmd)

    # Feature flags for experimental features
    cmd = click.option(
        "--enable-feature",
        "enabled_features",
        multiple=True,
        metavar="<FEATURE>",
        help="""🔧 [EXPERIMENTAL] Enable experimental features.
        Available features:
        • ci-download-hack - Enable two-pass sentinel mode for reliable Code Interpreter
          file downloads with structured output. Overrides config file setting.
        Example: --enable-feature ci-download-hack""",
    )(cmd)

    cmd = click.option(
        "--disable-feature",
        "disabled_features",
        multiple=True,
        metavar="<FEATURE>",
        help="""🔧 [EXPERIMENTAL] Disable experimental features.
        Available features:
        • ci-download-hack - Force single-pass mode for Code Interpreter downloads.
          Overrides config file setting.
        Example: --disable-feature ci-download-hack""",
    )(cmd)

    return cast(Command, cmd)


def file_search_config_options(
    f: Union[Command, Callable[..., Any]],
) -> Command:
    """Add File Search configuration options (without legacy file routing)."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--fs-store-name",
        type=str,
        default="ostruct_search",
        help="""📁 [FILE SEARCH] Name for the vector store used for file search.
        Example: --fs-store-name project_docs""",
    )(cmd)

    cmd = click.option(
        "--fs-cleanup",
        is_flag=True,
        default=True,
        help="""📁 [FILE SEARCH] Clean up uploaded files and vector stores after use.
        Disable with --no-fs-cleanup to keep files for debugging.""",
    )(cmd)

    cmd = click.option(
        "--fs-retries",
        type=int,
        default=3,
        help="""📁 [FILE SEARCH] Number of retry attempts for file search operations.
        Increase for unreliable network connections.""",
    )(cmd)

    cmd = click.option(
        "--fs-timeout",
        type=float,
        default=60.0,
        help="""📁 [FILE SEARCH] Timeout in seconds for vector store indexing operations.
        Increase for large file uploads.""",
    )(cmd)

    return cast(Command, cmd)


def web_search_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add Web Search CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--ws-country",
        type=str,
        help="""🌐 [WEB SEARCH] Specify user country for geographically tailored search results.
        Used to improve search relevance by location (e.g., 'US', 'UK', 'Germany').""",
    )(cmd)

    cmd = click.option(
        "--ws-city",
        type=str,
        help="""🌐 [WEB SEARCH] Specify user city for geographically tailored search results.
        Used to improve search relevance by location (e.g., 'San Francisco', 'London').""",
    )(cmd)

    cmd = click.option(
        "--ws-region",
        type=str,
        help="""🌐 [WEB SEARCH] Specify user region/state for geographically tailored search results.
        Used to improve search relevance by location (e.g., 'California', 'Texas').""",
    )(cmd)

    cmd = click.option(
        "--ws-context-size",
        type=click.Choice(["low", "medium", "high"]),
        help="""🌐 [WEB SEARCH] Control the amount of content retrieved from search results.
        'low' = brief snippets, 'medium' = balanced content, 'high' = comprehensive content.""",
    )(cmd)

    return cast(Command, cmd)


def tool_toggle_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add universal tool toggle CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--enable-tool",
        "enabled_tools",
        multiple=True,
        metavar="<TOOL>",
        help="""🔧 [TOOL TOGGLES] Enable a tool for this run (repeatable).
        Overrides configuration file and implicit activation.
        Available tools: code-interpreter, file-search, web-search, mcp
        Example: --enable-tool code-interpreter --enable-tool web-search""",
    )(cmd)

    cmd = click.option(
        "--disable-tool",
        "disabled_tools",
        multiple=True,
        metavar="<TOOL>",
        help="""🔧 [TOOL TOGGLES] Disable a tool for this run (repeatable).
        Overrides configuration file and implicit activation.
        Available tools: code-interpreter, file-search, web-search, mcp
        Example: --disable-tool web-search --disable-tool mcp""",
    )(cmd)

    return cast(Command, cmd)


def debug_progress_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add debugging and progress CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--no-progress", is_flag=True, help="Disable progress indicators"
    )(cmd)

    cmd = click.option(
        "--progress-level",
        type=click.Choice(["none", "basic", "detailed"]),
        default="basic",
        show_default=True,
        help="""Control progress verbosity. 'none' shows no progress,
        'basic' shows key steps, 'detailed' shows all steps.""",
    )(cmd)

    cmd = click.option(
        "--verbose", is_flag=True, help="Enable verbose logging"
    )(cmd)

    return cast(Command, cmd)


def security_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add path security and allowlist CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "-S",
        "--path-security",
        type=click.Choice(
            ["permissive", "warn", "strict"], case_sensitive=False
        ),
        help="🔒 Path security mode: permissive (allow all), warn (log warnings), strict (allowlist only)",
    )(cmd)

    cmd = click.option(
        "--allow",
        "allow_dir",
        multiple=True,
        type=click.Path(exists=True, file_okay=False),
        help="🗂️  Allow directory for strict/warn mode (repeatable)",
    )(cmd)

    cmd = click.option(
        "--allow-file",
        "allow_file",
        multiple=True,
        type=click.Path(exists=True, dir_okay=False, resolve_path=True),
        help="📄 Allow specific file for strict/warn mode (repeatable)",
    )(cmd)

    cmd = click.option(
        "--allow-list",
        "allow_list",
        multiple=True,
        type=click.Path(exists=True, dir_okay=False, resolve_path=True),
        help="📋 Allow paths from file list for strict/warn mode (repeatable)",
    )(cmd)

    return cast(Command, cmd)


def help_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add help-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--help-json",
        is_flag=True,
        callback=print_help_json,
        expose_value=False,
        is_eager=True,
        hidden=True,  # Hide from help output - feature not ready for release
        help="📖 Output command help in JSON format for programmatic consumption",
    )(cmd)

    return cast(Command, cmd)


def file_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add file attachment options with target/alias syntax."""

    cmd: Any = f if isinstance(f, Command) else f

    # Import validation functions here to avoid circular imports
    def validate_attachment_file(
        ctx: click.Context, param: click.Parameter, value: Any
    ) -> Any:
        from .params import normalise_targets, validate_attachment_alias

        if not value:
            return []

        result = []
        for spec, path in value:
            # Parse spec part: [targets:]alias
            if ":" in spec:
                # Check for Windows drive letter false positive
                if len(spec) == 2 and spec[1] == ":" and spec[0].isalpha():
                    prefix, alias = "prompt", spec
                else:
                    prefix, alias = spec.split(":", 1)
            else:
                prefix, alias = "prompt", spec

            # Normalize targets
            try:
                targets = normalise_targets(prefix)
            except click.BadParameter as e:
                raise click.BadParameter(
                    f"Invalid target(s) in '{prefix}' for {param.name}. {e}"
                )

            # Validate alias
            try:
                alias = validate_attachment_alias(alias)
            except click.BadParameter as e:
                raise click.BadParameter(
                    f"Invalid alias for {param.name}: {e}"
                )

            result.append(
                {
                    "alias": alias,
                    "path": path,
                    "targets": targets,
                    "recursive": False,
                    "pattern": None,
                }
            )

        return result

    def validate_attachment_dir(
        ctx: click.Context, param: click.Parameter, value: Any
    ) -> Any:
        return validate_attachment_file(ctx, param, value)

    def validate_attachment_collect(
        ctx: click.Context, param: click.Parameter, value: Any
    ) -> Any:
        if not value:
            return []

        result = []
        for spec, path in value:
            # Parse spec part: [targets:]alias
            if ":" in spec:
                if len(spec) == 2 and spec[1] == ":" and spec[0].isalpha():
                    prefix, alias = "prompt", spec
                else:
                    prefix, alias = spec.split(":", 1)
            else:
                prefix, alias = "prompt", spec

            # Handle collect @filelist syntax
            processed_path = path
            if path.startswith("@"):
                filelist_path = path[1:]  # Remove @
                if not filelist_path:
                    raise click.BadParameter(
                        f"Filelist path cannot be empty after @ for {param.name}"
                    )
                processed_path = ("@", filelist_path)

            result.append(
                {
                    "alias": alias,
                    "path": processed_path,
                    "targets": set([prefix.lower()]),
                    "recursive": False,
                    "pattern": None,
                }
            )

        return result

    # Modern file attachment options
    cmd = click.option(
        "-F",
        "--file",
        "attaches",
        multiple=True,
        nargs=2,
        callback=validate_attachment_file,
        metavar="[TARGETS:]ALIAS PATH",
        help="Attach file: '[targets:]alias path'. Targets: prompt (default), code-interpreter/ci, file-search/fs",
    )(cmd)

    cmd = click.option(
        "-D",
        "--dir",
        "dirs",
        multiple=True,
        nargs=2,
        callback=validate_attachment_dir,
        metavar="[TARGETS:]ALIAS PATH",
        help="Attach directory: '[targets:]alias path'. Targets: prompt (default), code-interpreter/ci, file-search/fs",
    )(cmd)

    cmd = click.option(
        "-C",
        "--collect",
        "collects",
        multiple=True,
        nargs=2,
        callback=validate_attachment_collect,
        metavar="[TARGETS:]ALIAS @FILELIST",
        help="Attach file collection: '[targets:]alias @file-list.txt'",
    )(cmd)

    cmd = click.option(
        "--recursive",
        is_flag=True,
        help="Apply to last --dir/--collect",
    )(cmd)

    cmd = click.option(
        "--pattern",
        metavar="GLOB",
        help="Apply to last --dir/--collect (replaces legacy --glob)",
    )(cmd)

    return cast(Command, cmd)


def all_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Apply all CLI options to a command.

    Uses modern file attachment system instead of legacy options.
    """
    cmd: Any = f if isinstance(f, Command) else f

    # Apply option groups in order
    cmd = variable_options(cmd)
    cmd = model_options(cmd)
    cmd = system_prompt_options(cmd)
    cmd = output_options(cmd)
    cmd = api_options(cmd)
    cmd = mcp_options(cmd)
    cmd = file_options(cmd)  # File attachment system
    cmd = security_options(cmd)  # Path security and allowlist options
    cmd = feature_options(
        cmd
    )  # Feature flags and config (no legacy file options)
    cmd = file_search_config_options(
        cmd
    )  # File search config (no legacy file options)
    cmd = web_search_options(cmd)
    cmd = tool_toggle_options(cmd)
    cmd = debug_options(cmd)
    cmd = debug_progress_options(cmd)
    cmd = help_options(cmd)

    return cast(Command, cmd)


def create_click_command() -> CommandDecorator:
    """Create the Click command with all options.

    Returns:
        A decorator function that adds all CLI options to the command.
    """

    def decorator(f: F) -> Command:
        # Initial command creation
        cmd: Any = click.command()(f)

        # Add version option
        cmd = click.version_option(
            __version__,
            "--version",
            "-V",
            message="%(prog)s CLI version %(version)s",
        )(cmd)

        return cast(Command, cmd)

    return decorator
