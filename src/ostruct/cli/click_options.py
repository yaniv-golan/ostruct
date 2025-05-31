"""Click command and options for the CLI.

This module contains all Click-related code separated from the main CLI logic.
We isolate this code here and provide proper type annotations for Click's
decorator-based API.
"""

from typing import Any, Callable, TypeVar, Union, cast

import click
from click import Command
from typing_extensions import ParamSpec

from ostruct import __version__
from ostruct.cli.errors import (  # noqa: F401 - Used in error handling
    SystemPromptError,
    TaskTemplateVariableError,
)
from ostruct.cli.validators import (
    validate_json_variable,
    validate_name_path_pair,
    validate_variable,
)

P = ParamSpec("P")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])
CommandDecorator = Callable[[F], Command]
DecoratedCommand = Union[Command, Callable[..., Any]]


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


def file_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add file-related CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "-f",
        "--file",
        "files",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATH>",
        callback=validate_name_path_pair,
        help="""[LEGACY] Associate a file with a variable name for template access only.
        The file will be available in your template as the specified variable.
        For explicit tool routing, use -ft, -fc, or -fs instead.
        Example: -f code main.py -f test test_main.py""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "-d",
        "--dir",
        "dir",
        multiple=True,
        nargs=2,
        metavar="<NAME> <DIR>",
        callback=validate_name_path_pair,
        help="""[LEGACY] Associate a directory with a variable name for template access only.
        All files in the directory will be available in your template. Use -R for recursive scanning.
        For explicit tool routing, use -dt, -dc, or -ds instead.
        Example: -d src ./src""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    # Template files with auto-naming ONLY (single argument)
    cmd = click.option(
        "-ft",
        "--file-for-template",
        "template_files",
        multiple=True,
        type=click.Path(exists=True, file_okay=True, dir_okay=False),
        help="""📄 [TEMPLATE] Files for template access only (auto-naming). These files will be available
        in your template but will not be uploaded to any tools. Use for configuration files,
        small data files, or any content you want to reference in templates.
        Format: -ft path (auto-generates variable name from filename).
        Access file content: {{ variable.content }} (not just {{ variable }})
        Example: -ft config.yaml → config_yaml variable, use {{ config_yaml.content }}""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    # Template files with two-argument alias syntax (explicit naming)
    cmd = click.option(
        "--fta",
        "--file-for-template-alias",
        "template_file_aliases",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATH>",
        callback=validate_name_path_pair,
        help="""📄 [TEMPLATE] Files for template with custom aliases. Use this for reusable
        templates where you need stable variable names independent of file paths.
        Format: --fta name path (supports tab completion for paths).
        Access file content: {{ name.content }} (not just {{ name }})
        Example: --fta config_data config.yaml → use {{ config_data.content }}""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "-dt",
        "--dir-for-template",
        "template_dirs",
        multiple=True,
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="""📁 [TEMPLATE] Directories for template access only (auto-naming). All files will be available
        in your template but will not be uploaded to any tools. Use for project configurations,
        reference data, or any directory content you want accessible in templates.
        Format: -dt path (auto-generates variable name from directory name).
        Example: -dt ./config -dt ./data""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    # Template directories with two-argument alias syntax (explicit naming)
    cmd = click.option(
        "--dta",
        "--dir-for-template-alias",
        "template_dir_aliases",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATH>",
        callback=validate_name_path_pair,
        help="""📁 [TEMPLATE] Directories for template with custom aliases. Use this for reusable
        templates where you need stable variable names independent of directory paths.
        Format: --dta name path (supports tab completion for paths).
        Example: --dta config_data ./settings --dta source_code ./src""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "--file-for",
        "tool_files",
        nargs=2,
        multiple=True,
        metavar="TOOL PATH",
        help="""🔄 [ADVANCED] Route files to specific tools. Use this for precise control
        over which tools receive which files. Supports tab completion for both tool names
        and file paths.
        Format: --file-for TOOL PATH
        Examples:
          --file-for code-interpreter analysis.py
          --file-for file-search docs.pdf
          --file-for template config.yaml""",
    )(cmd)

    cmd = click.option(
        "-p",
        "--pattern",
        "patterns",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATTERN>",
        help="""[LEGACY] Associate a glob pattern with a variable name. Matching files will be
        available in your template. Use -R for recursive matching.
        Example: -p logs '*.log'""",
    )(cmd)

    cmd = click.option(
        "-R",
        "--recursive",
        is_flag=True,
        help="Process directories and patterns recursively",
    )(cmd)

    cmd = click.option(
        "--base-dir",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="""Base directory for resolving relative paths. All file operations will be
        relative to this directory. Defaults to current directory.""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "-A",
        "--allow",
        "allowed_dirs",
        multiple=True,
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="""Add an allowed directory for security. Files must be within allowed
        directories. Can be specified multiple times.""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "--allowed-dir-file",
        type=click.Path(exists=True, file_okay=True, dir_okay=False),
        help="""File containing allowed directory paths, one per line. Lines starting
        with # are treated as comments.""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

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

    cmd = click.option(
        "-m",
        "--model",
        default="gpt-4o",
        show_default=True,
        help="""OpenAI model to use. Must support structured output.
        Supported models:
        - gpt-4o (128k context window)
        - o1 (200k context window)
        - o3-mini (200k context window)""",
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

    cmd = click.option(
        "--timeout",
        type=click.FloatRange(1.0, None),
        default=60.0,
        show_default=True,
        help="API timeout in seconds.",
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


def code_interpreter_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add Code Interpreter CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # Code interpreter files with auto-naming ONLY (single argument)
    cmd = click.option(
        "-fc",
        "--file-for-code-interpreter",
        "code_interpreter_files",
        multiple=True,
        type=click.Path(exists=True, file_okay=True, dir_okay=False),
        help="""💻 [CODE INTERPRETER] Files to upload for code execution and analysis (auto-naming).
        Perfect for data files (CSV, JSON), code files (Python, R), or any files that
        need computational processing. Files are uploaded to an isolated execution environment.
        Format: -fc path (auto-generates variable name from filename).
        Example: -fc data.csv → data_csv variable, -fc analysis.py → analysis_py variable""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    # Code interpreter files with two-argument alias syntax (explicit naming)
    cmd = click.option(
        "--fca",
        "--file-for-code-interpreter-alias",
        "code_interpreter_file_aliases",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATH>",
        callback=validate_name_path_pair,
        help="""💻 [CODE INTERPRETER] Files for code execution with custom aliases.
        Format: --fca name path (supports tab completion for paths).
        Example: --fca dataset src/data.csv --fca script analysis.py""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "-dc",
        "--dir-for-code-interpreter",
        "code_interpreter_dirs",
        multiple=True,
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="""📂 [CODE INTERPRETER] Directories to upload for code execution (auto-naming). All files
        in the directory will be uploaded to the execution environment. Use for datasets,
        code repositories, or any directory that needs computational processing.
        Format: -dc path (auto-generates variable name from directory name).
        Example: -dc ./data -dc ./scripts""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    # Code interpreter directories with two-argument alias syntax (explicit naming)
    cmd = click.option(
        "--dca",
        "--dir-for-code-interpreter-alias",
        "code_interpreter_dir_aliases",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATH>",
        callback=validate_name_path_pair,
        help="""📂 [CODE INTERPRETER] Directories for code execution with custom aliases.
        Format: --dca name path (supports tab completion for paths).
        Example: --dca dataset ./data --dca source_code ./src""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "--code-interpreter-download-dir",
        type=click.Path(file_okay=False, dir_okay=True),
        default="./downloads",
        show_default=True,
        help="""Directory to save files generated by Code Interpreter.
        Example: --code-interpreter-download-dir ./results""",
        shell_complete=click.Path(file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "--code-interpreter-cleanup",
        is_flag=True,
        default=True,
        show_default=True,
        help="""Clean up uploaded files after execution to save storage quota.""",
    )(cmd)

    return cast(Command, cmd)


def file_search_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add File Search CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    # File search files with auto-naming ONLY (single argument)
    cmd = click.option(
        "-fs",
        "--file-for-search",
        "file_search_files",
        multiple=True,
        type=click.Path(exists=True, file_okay=True, dir_okay=False),
        help="""🔍 [FILE SEARCH] Files to upload for semantic vector search (auto-naming). Perfect for
        documents (PDF, TXT, MD), manuals, knowledge bases, or any text content you want to
        search through. Files are processed into a searchable vector store.
        Format: -fs path (auto-generates variable name from filename).
        Example: -fs docs.pdf → docs_pdf variable, -fs manual.txt → manual_txt variable""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    # File search files with two-argument alias syntax (explicit naming)
    cmd = click.option(
        "--fsa",
        "--file-for-search-alias",
        "file_search_file_aliases",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATH>",
        callback=validate_name_path_pair,
        help="""🔍 [FILE SEARCH] Files for search with custom aliases.
        Format: --fsa name path (supports tab completion for paths).
        Example: --fsa manual src/docs.pdf --fsa knowledge base.txt""",
        shell_complete=click.Path(exists=True, file_okay=True, dir_okay=False),
    )(cmd)

    cmd = click.option(
        "-ds",
        "--dir-for-search",
        "file_search_dirs",
        multiple=True,
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="""📁 [FILE SEARCH] Directories to upload for semantic search (auto-naming). All files in the
        directory will be processed into a searchable vector store. Use for documentation
        directories, knowledge bases, or any collection of searchable documents.
        Format: -ds path (auto-generates variable name from directory name).
        Example: -ds ./docs -ds ./manuals""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    # File search directories with two-argument alias syntax (explicit naming)
    cmd = click.option(
        "--dsa",
        "--dir-for-search-alias",
        "file_search_dir_aliases",
        multiple=True,
        nargs=2,
        metavar="<NAME> <PATH>",
        callback=validate_name_path_pair,
        help="""📁 [FILE SEARCH] Directories for search with custom aliases.
        Format: --dsa name path (supports tab completion for paths).
        Example: --dsa documentation ./docs --dsa knowledge_base ./manuals""",
        shell_complete=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(cmd)

    cmd = click.option(
        "--file-search-vector-store-name",
        default="ostruct_search",
        show_default=True,
        help="""Name for the vector store created for File Search.
        Example: --file-search-vector-store-name project_docs""",
    )(cmd)

    cmd = click.option(
        "--file-search-cleanup",
        is_flag=True,
        default=True,
        show_default=True,
        help="""Clean up uploaded files and vector stores after execution.""",
    )(cmd)

    cmd = click.option(
        "--file-search-retry-count",
        type=click.IntRange(1, 10),
        default=3,
        show_default=True,
        help="""Number of retry attempts for File Search operations.
        Higher values improve reliability for intermittent failures.""",
    )(cmd)

    cmd = click.option(
        "--file-search-timeout",
        type=click.FloatRange(10.0, 300.0),
        default=60.0,
        show_default=True,
        help="""Timeout in seconds for vector store indexing.
        Typically instant but may take longer for large files.""",
    )(cmd)

    return cast(Command, cmd)


def web_search_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Add Web Search CLI options."""
    cmd: Any = f if isinstance(f, Command) else f

    cmd = click.option(
        "--web-search",
        is_flag=True,
        help="""🌐 [WEB SEARCH] Enable OpenAI web search tool for up-to-date information.
        Allows the model to search the web for current events, recent updates, and real-time data.
        Note: Search queries may be sent to external services via OpenAI.""",
    )(cmd)

    cmd = click.option(
        "--no-web-search",
        is_flag=True,
        help="""Explicitly disable web search even if enabled by default in configuration.""",
    )(cmd)

    cmd = click.option(
        "--user-country",
        type=str,
        help="""🌐 [WEB SEARCH] Specify user country for geographically tailored search results.
        Used to improve search relevance by location (e.g., 'US', 'UK', 'Germany').""",
    )(cmd)

    cmd = click.option(
        "--user-city",
        type=str,
        help="""🌐 [WEB SEARCH] Specify user city for geographically tailored search results.
        Used to improve search relevance by location (e.g., 'San Francisco', 'London').""",
    )(cmd)

    cmd = click.option(
        "--user-region",
        type=str,
        help="""🌐 [WEB SEARCH] Specify user region/state for geographically tailored search results.
        Used to improve search relevance by location (e.g., 'California', 'Bavaria').""",
    )(cmd)

    cmd = click.option(
        "--search-context-size",
        type=click.Choice(["low", "medium", "high"]),
        help="""🌐 [WEB SEARCH] Control the amount of content retrieved from web pages.
        'low' retrieves minimal content, 'high' retrieves comprehensive content. Default: medium.""",
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

    cmd = click.option(
        "--debug-openai-stream",
        is_flag=True,
        help="Debug OpenAI streaming process",
    )(cmd)

    cmd = click.option(
        "--timeout",
        type=int,
        default=3600,
        help="Operation timeout in seconds (default: 3600 = 1 hour)",
    )(cmd)

    return cast(Command, cmd)


def all_options(f: Union[Command, Callable[..., Any]]) -> Command:
    """Apply all CLI options to a command."""
    cmd: Any = f if isinstance(f, Command) else f

    # Apply option groups in order
    cmd = file_options(cmd)
    cmd = variable_options(cmd)
    cmd = model_options(cmd)
    cmd = system_prompt_options(cmd)
    cmd = output_options(cmd)
    cmd = api_options(cmd)
    cmd = mcp_options(cmd)
    cmd = code_interpreter_options(cmd)
    cmd = file_search_options(cmd)
    cmd = web_search_options(cmd)
    cmd = debug_options(cmd)
    cmd = debug_progress_options(cmd)

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
