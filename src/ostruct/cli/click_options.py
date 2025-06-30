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

from .constants import DefaultPaths
from .help_json import print_command_help_json as print_help_json

P = ParamSpec("P")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])
CommandDecorator = Callable[[F], Command]
DecoratedCommand = Union[Command, Callable[..., Any]]

logger = logging.getLogger(__name__)


def _handle_help_debug(
    ctx: click.Context, param: click.Parameter, value: bool
) -> None:
    """Handle --help-debug flag by showing debug help and exiting."""
    if not value or ctx.resilient_parsing:
        return

    from .template_debug_help import show_template_debug_help

    show_template_debug_help()
    ctx.exit()


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
    """Custom Choice type with better error messages and help display for models."""

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

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> list:
        """Provide shell completion for model names."""
        from click.shell_completion import CompletionItem

        return [
            CompletionItem(choice)
            for choice in self.choices
            if choice.startswith(incomplete)
        ]

    def get_metavar(
        self, param: click.Parameter, ctx: click.Context | None = None
    ) -> str:
        """Override metavar to show simple model info instead of complex list."""
        choices_list = list(self.choices)

        # Simple, clean display
        return f"[{len(choices_list)} models available - run 'ostruct list-models' for full list]"


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
    """Add debug-related CLI options (now consolidated into debug_progress_options)."""
    # All debug options have been moved to debug_progress_options for better grouping
    # This function is kept for backward compatibility but does nothing
    cmd: Any = f if isinstance(f, Command) else f
    return cast(Command, cmd)


def variable_options(cmd: Callable[..., Any]) -> Callable[..., Any]:
    """Add variable-related options to a command."""
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
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
        ),
        click.option(
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
        ),
    ):
        cmd = deco(cmd)

    return cast(Callable[..., Any], cmd)


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

    # Apply Model Configuration Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--reasoning-effort",
            type=click.Choice(["low", "medium", "high"]),
            help="""Control reasoning effort (if supported by model).
            Higher values may improve output quality but take longer.""",
        ),
        click.option(
            "--presence-penalty",
            type=click.FloatRange(-2.0, 2.0),
            help="""Presence penalty for text generation.
            Range: -2.0 to 2.0. Positive values encourage new topics.""",
        ),
        click.option(
            "--frequency-penalty",
            type=click.FloatRange(-2.0, 2.0),
            help="""Frequency penalty for text generation.
            Range: -2.0 to 2.0. Positive values reduce repetition.""",
        ),
        click.option(
            "--top-p",
            type=click.FloatRange(0.0, 1.0),
            help="""Top-p (nucleus) sampling parameter. Controls diversity.
            Range: 0.0 to 1.0. Lower values are more focused.""",
        ),
        click.option(
            "--max-output-tokens",
            type=click.IntRange(1, None),
            help="""Maximum number of tokens in the output.
            Higher values allow longer responses but cost more.""",
        ),
        click.option(
            "--temperature",
            type=click.FloatRange(0.0, 2.0),
            help="""Sampling temperature. Controls randomness in the output.
            Range: 0.0 to 2.0. Lower values are more focused.""",
        ),
        click.option(
            "-m",
            "--model",
            type=model_choice,
            default=default_model,
            show_default=True,
            help="OpenAI model to use. Must support structured output. Run 'ostruct list-models' for complete list.",
        ),
    ):
        cmd = deco(cmd)

    return cast(Command, cmd)


def system_prompt_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add system prompt related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply System Prompt Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--ignore-task-sysprompt",
            is_flag=True,
            help="""Ignore system prompt in task template. By default, system prompts
            in template frontmatter are used.""",
        ),
        click.option(
            "--sys-file",
            "system_prompt_file",
            type=click.Path(exists=True, dir_okay=False),
            help="""Load system prompt from file. The file should contain the prompt text.
        Example: --sys-file prompts/code_review.txt""",
            shell_complete=click.Path(
                exists=True, file_okay=True, dir_okay=False
            ),
        ),
        click.option(
            "--sys-prompt",
            "system_prompt",
            help="""Provide system prompt directly. This sets the initial context
            for the model. Example: --sys-prompt "You are a code reviewer.\"""",
        ),
    ):
        cmd = deco(cmd)

    return cast(Command, cmd)


def output_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add output-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply Output and Execution Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--run-summary-json",
            is_flag=True,
            help="""Output run summary as JSON to stderr (cannot be used with --dry-run).
            Provides machine-readable execution summary after live runs.""",
        ),
        click.option(
            "--dry-run-json",
            is_flag=True,
            help="""Output execution plan as JSON (requires --dry-run).
        Outputs structured execution plan to stdout for programmatic consumption.""",
        ),
        click.option(
            "--dry-run",
            is_flag=True,
            help="""Validate and render but skip API call. Useful for testing
            template rendering and validation.""",
        ),
        click.option(
            "--output-file",
            type=click.Path(dir_okay=False),
            help="""Write output to file instead of stdout.
            Example: --output-file result.json""",
            shell_complete=click.Path(file_okay=True, dir_okay=False),
        ),
    ):
        cmd = deco(cmd)

    return cast(Command, cmd)


def api_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add API-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply Configuration and API Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--timeout",
            type=click.FloatRange(1.0, None),
            default=60.0,
            show_default=True,
            help="Timeout in seconds for OpenAI API calls.",
        ),
        click.option(
            "--api-key",
            help="""OpenAI API key. If not provided, uses OPENAI_API_KEY
            environment variable.""",
        ),
        click.option(
            "--config",
            type=click.Path(exists=True),
            help="Configuration file path (default: ostruct.yaml)",
        ),
    ):
        cmd = deco(cmd)

    return cast(Command, cmd)


def mcp_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add MCP (Model Context Protocol) server CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply MCP Server Configuration Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--mcp-headers",
            help="""JSON string of headers for MCP servers.
            Example: --mcp-headers '{"Authorization": "Bearer token"}'""",
        ),
        click.option(
            "--mcp-require-approval",
            type=click.Choice(["always", "never"]),
            default="never",
            show_default=True,
            help="""Approval level for MCP tool usage. CLI usage requires 'never'.""",
        ),
        click.option(
            "--mcp-allowed-tools",
            "mcp_allowed_tools",
            multiple=True,
            help="""Allowed tools per server. Format: server_label:tool1,tool2
            Example: --mcp-allowed-tools deepwiki:search,summary""",
        ),
        click.option(
            "--mcp-server",
            "mcp_servers",
            multiple=True,
            help="""🔌 [MCP] Connect to Model Context Protocol server for extended capabilities.
        MCP servers provide additional tools like web search, databases, APIs, etc.
        Format: [label@]url
        Example: --mcp-server deepwiki@https://mcp.deepwiki.com/sse""",
        ),
    ):
        cmd = deco(cmd)

    return cast(Command, cmd)


def feature_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add feature flag and configuration options (without legacy file routing)."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply Code Interpreter Configuration Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--ci-cleanup",
            is_flag=True,
            default=True,
            show_default=True,
            help="""🤖 [CODE INTERPRETER] Clean up uploaded files after execution to save storage quota.""",
        ),
        click.option(
            "--ci-duplicate-outputs",
            type=click.Choice(["overwrite", "rename", "skip"]),
            default=None,  # Will use config default or fallback to "overwrite"
            show_default="overwrite",
            help="""🤖 [CODE INTERPRETER] Handle duplicate output file names.
        'overwrite' replaces existing files (default),
        'rename' creates unique names (file_1.txt, file_2.txt),
        'skip' ignores files that already exist.
        Example: --ci-duplicate-outputs rename""",
        ),
        click.option(
            "--ci-download-dir",
            type=click.Path(file_okay=False, dir_okay=True),
            default=None,  # Will use config default or fallback in runner.py
            show_default=DefaultPaths.CODE_INTERPRETER_OUTPUT_DIR,
            help="""🤖 [CODE INTERPRETER] Directory to save files generated by Code Interpreter.
        Example: --ci-download-dir ./results""",
            shell_complete=click.Path(file_okay=False, dir_okay=True),
        ),
    ):
        cmd = deco(cmd)

    # Apply the group decorator LAST so it sees all the options
    cmd = cmd

    # Apply Experimental Features Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--disable-feature",
            "disabled_features",
            multiple=True,
            metavar="<FEATURE>",
            help="""🔧 [EXPERIMENTAL] Disable experimental features.
            Available features:
            • ci-download-hack - Force single-pass mode for Code Interpreter downloads.
              Overrides config file setting.
            Example: --disable-feature ci-download-hack""",
        ),
        click.option(
            "--enable-feature",
            "enabled_features",
            multiple=True,
            metavar="<FEATURE>",
            help="""🔧 [EXPERIMENTAL] Enable experimental features.
        Available features:
        • ci-download-hack - Enable two-pass sentinel mode for reliable Code Interpreter
          file downloads with structured output. Overrides config file setting.
        Example: --enable-feature ci-download-hack""",
        ),
    ):
        cmd = deco(cmd)

    # Apply the group decorator LAST so it sees all the options
    cmd = cmd

    return cast(Command, cmd)


def file_search_config_options(
    f: Union[Command, Callable[..., Any]],
) -> Command:
    """Add File Search configuration options (without legacy file routing)."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply File Search Configuration Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--fs-timeout",
            type=float,
            default=60.0,
            help="""📁 [FILE SEARCH] Timeout in seconds for vector store indexing operations.
            Increase for large file uploads.""",
        ),
        click.option(
            "--fs-retries",
            type=int,
            default=3,
            help="""📁 [FILE SEARCH] Number of retry attempts for file search operations.
            Increase for unreliable network connections.""",
        ),
        click.option(
            "--fs-cleanup",
            is_flag=True,
            default=True,
            help="""📁 [FILE SEARCH] Clean up uploaded files and vector stores after use.
            Disable with --no-fs-cleanup to keep files for debugging.""",
        ),
        click.option(
            "--fs-store-name",
            type=str,
            default="ostruct_search",
            help="""📁 [FILE SEARCH] Name for the vector store used for file search.
        Example: --fs-store-name project_docs""",
        ),
    ):
        cmd = deco(cmd)

    # Apply the group decorator LAST so it sees all the options
    cmd = cmd

    return cast(Command, cmd)


def web_search_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add Web Search CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply Web Search Configuration Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--ws-context-size",
            type=click.Choice(["low", "medium", "high"]),
            help="""🌐 [WEB SEARCH] Control the amount of content retrieved from search results.
            'low' = brief snippets, 'medium' = balanced content, 'high' = comprehensive content.""",
        ),
        click.option(
            "--ws-region",
            type=str,
            help="""🌐 [WEB SEARCH] Specify user region/state for geographically tailored search results.
            Used to improve search relevance by location (e.g., 'California', 'Texas').""",
        ),
        click.option(
            "--ws-city",
            type=str,
            help="""🌐 [WEB SEARCH] Specify user city for geographically tailored search results.
        Used to improve search relevance by location (e.g., 'San Francisco', 'London').""",
        ),
        click.option(
            "--ws-country",
            type=str,
            help="""🌐 [WEB SEARCH] Specify user country for geographically tailored search results.
            Used to improve search relevance by location (e.g., 'US', 'UK', 'Germany').""",
        ),
    ):
        cmd = deco(cmd)

    # Apply the group decorator LAST so it sees all the options
    cmd = cmd

    return cast(Command, cmd)


def tool_toggle_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add universal tool toggle CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply Tool Integration Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--disable-tool",
            "disabled_tools",
            multiple=True,
            metavar="<TOOL>",
            help="""🔧 [TOOL TOGGLES] Disable a tool for this run (repeatable).
            Overrides configuration file and implicit activation.
            Available tools: code-interpreter, file-search, web-search, mcp
            Example: --disable-tool web-search --disable-tool mcp""",
        ),
        click.option(
            "--enable-tool",
            "enabled_tools",
            multiple=True,
            metavar="<TOOL>",
            help="""🔧 [TOOL TOGGLES] Enable a tool for this run (repeatable).
        Overrides configuration file and implicit activation.
        Available tools: code-interpreter, file-search, web-search, mcp
        Example: --enable-tool code-interpreter --enable-tool web-search""",
        ),
    ):
        cmd = deco(cmd)

    # Apply the group decorator LAST so it sees all the options
    cmd = cmd

    return cast(Command, cmd)


def debug_progress_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add debugging and progress CLI options."""
    # Import the new infrastructure for template debug
    from .template_debug import parse_td

    cmd: Any = f if isinstance(f, Command) else f

    # Apply Debug and Development Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--help-debug",
            is_flag=True,
            is_eager=True,
            expose_value=False,
            callback=lambda ctx, param, value: _handle_help_debug(
                ctx, param, value
            ),
            help="📚 Show comprehensive template debugging help and examples",
        ),
        click.option(
            "--debug",
            is_flag=True,
            help="🐛 Enable debug-level logging including template expansion",
        ),
        click.option(
            "--debug-validation",
            is_flag=True,
            help="Show detailed validation errors",
        ),
        click.option(
            "--show-model-schema",
            is_flag=True,
            help="Show generated Pydantic model schema",
        ),
        click.option(
            "-t",
            "--template-debug",
            metavar="CAPACITIES",
            default=None,
            is_flag=False,
            flag_value="all",
            expose_value=False,
            callback=lambda ctx, p, v: (
                ctx.obj.setdefault("_template_debug_caps", parse_td(v))
                if ctx.obj is not None and v is not None
                else None
            ),
            help="🔍 Debug prompt-template expansion. "
            "Capacities: pre-expand,vars,preview,steps,post-expand "
            "(comma list or 'all'). Use -t CAPACITIES or bare -t for all capacities.",
        ),
        click.option("--verbose", is_flag=True, help="Enable verbose logging"),
        click.option(
            "--progress",
            type=click.Choice(["none", "basic", "detailed"]),
            default="basic",
            show_default=True,
            help="""Control progress display. 'none' disables progress indicators,
            'basic' shows key steps, 'detailed' shows all operations.""",
        ),
    ):
        cmd = deco(cmd)

    # Apply the group decorator LAST so it sees all the options
    cmd = cmd

    return cast(Command, cmd)


def security_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add path security and allowlist CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply Security and Path Control Options using click-option-group
    # Apply options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--allow-list",
            "allow_list",
            multiple=True,
            type=click.Path(exists=True, dir_okay=False, resolve_path=True),
            help="📋 Allow paths from file list for strict/warn mode (repeatable)",
        ),
        click.option(
            "--allow-file",
            "allow_file",
            multiple=True,
            type=click.Path(exists=True, dir_okay=False, resolve_path=True),
            help="📄 Allow specific file for strict/warn mode (repeatable)",
        ),
        click.option(
            "--allow",
            "allow_dir",
            multiple=True,
            type=click.Path(exists=True, file_okay=False),
            help="🗂️  Allow directory for strict/warn mode (repeatable)",
        ),
        click.option(
            "-S",
            "--path-security",
            type=click.Choice(
                ["permissive", "warn", "strict"], case_sensitive=False
            ),
            help="🔒 Path security mode: permissive (allow all), warn (log warnings), strict (allowlist only)",
        ),
    ):
        cmd = deco(cmd)

    # Apply the group decorator LAST so it sees all the options
    cmd = cmd

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

    # Apply File Attachment Options using click-option-group
    # Fix: Attach options first, then wrap them in the group decorator last
    cmd: Any = f if isinstance(f, Command) else f

    # Attach options first (in reverse order since they stack)
    for deco in (
        click.option(
            "--gitignore-file",
            type=click.Path(exists=True),
            help="Custom gitignore file path (default: .gitignore in target directory)",
        ),
        click.option(
            "--ignore-gitignore",
            is_flag=True,
            default=False,
            help="Ignore .gitignore files when collecting directory files (disables gitignore support)",
        ),
        click.option(
            "--pattern",
            metavar="GLOB",
            help="Apply glob pattern to all --dir/--collect attachments",
        ),
        click.option(
            "--recursive",
            is_flag=True,
            help="Apply recursively to all --dir/--collect attachments",
        ),
        click.option(
            "-C",
            "--collect",
            "collects",
            multiple=True,
            nargs=2,
            callback=validate_attachment_collect,
            metavar="[TARGETS:]ALIAS @FILELIST",
            help="Attach file collection: '[targets:]alias @file-list.txt'",
        ),
        click.option(
            "-D",
            "--dir",
            "dirs",
            multiple=True,
            nargs=2,
            callback=validate_attachment_dir,
            metavar="[TARGETS:]ALIAS PATH",
            help="Attach directory: '[targets:]alias path'. Targets: prompt (default), code-interpreter/ci, file-search/fs",
        ),
        click.option(
            "-F",
            "--file",
            "attaches",
            multiple=True,
            nargs=2,
            callback=validate_attachment_file,
            metavar="[TARGETS:]ALIAS PATH",
            help="Attach file: '[targets:]alias path'. Targets: prompt (default), code-interpreter/ci, file-search/fs",
        ),
    ):
        cmd = deco(cmd)

    # Apply the group decorator LAST so it sees all the options
    cmd = cmd

    return cast(Command, cmd)


def all_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Apply all CLI options to a command in progressive disclosure order.

    Order: Essential → Core Workflow → Advanced Features → Debug/Development
    """
    cmd: Any = f if isinstance(f, Command) else f

    # Apply option groups in progressive disclosure order (REVERSE order since they stack)
    # Debug and Development Options (last - most advanced)
    cmd = help_options(cmd)
    cmd = debug_progress_options(cmd)
    cmd = debug_options(cmd)

    # Advanced Configuration Options
    cmd = security_options(cmd)  # Path security and allowlist options
    cmd = web_search_options(cmd)
    cmd = file_search_config_options(cmd)  # File search config
    cmd = feature_options(cmd)  # Feature flags and config
    cmd = mcp_options(cmd)
    cmd = api_options(cmd)

    # Core Workflow Options
    cmd = output_options(cmd)
    cmd = system_prompt_options(cmd)
    cmd = tool_toggle_options(cmd)
    cmd = file_options(cmd)  # File attachment system
    cmd = model_options(cmd)

    # Essential Options (first - most important)
    cmd = variable_options(cmd)

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
