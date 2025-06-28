"""Template processing functions for ostruct CLI."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import click
import jinja2
import yaml

from .constants import DefaultConfig
from .errors import (
    DirectoryNotFoundError,
    DuplicateFileMappingError,
    InvalidJSONError,
    OstructFileNotFoundError,
    PathSecurityError,
    SystemPromptError,
    TaskTemplateSyntaxError,
    TaskTemplateVariableError,
    VariableNameError,
)
from .explicit_file_processor import ProcessingResult
from .file_utils import FileInfoList
from .path_utils import validate_path_mapping
from .security import SecurityManager
from .template_debug import (
    TDCap,
    is_capacity_active,
    td_log_if_active,
    td_log_preview,
    td_log_vars,
)
from .template_utils import render_template
from .types import CLIParams

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = DefaultConfig.TEMPLATE["system_prompt"]


def _render_template_with_debug(
    template_content: str,
    context: Dict[str, Any],
    env: jinja2.Environment,
    debug_capacities: Optional[Set[TDCap]] = None,
) -> str:
    """Render template with debugging support.

    Args:
        template_content: Template content to render
        context: Template context variables
        env: Jinja2 environment
        debug_capacities: Set of active debug capacities (unused but kept for compatibility)

    Returns:
        Rendered template string
    """
    # Simple template rendering without optimization
    template = env.from_string(template_content)
    return template.render(**context)


def process_system_prompt(
    task_template: str,
    system_prompt: Optional[str],
    system_prompt_file: Optional[str],
    template_context: Dict[str, Any],
    env: jinja2.Environment,
    ignore_task_sysprompt: bool = False,
    template_path: Optional[str] = None,
) -> Tuple[str, bool]:
    """Process system prompt from various sources.

    Args:
        task_template: The task template string
        system_prompt: Optional system prompt string
        system_prompt_file: Optional path to system prompt file
        template_context: Template context for rendering
        env: Jinja2 environment
        ignore_task_sysprompt: Whether to ignore system prompt in task template
        template_path: Optional path to template file for include_system resolution

    Returns:
        Tuple of (final system prompt string, template_has_system_prompt)

    Raises:
        SystemPromptError: If the system prompt cannot be loaded or rendered
        FileNotFoundError: If a prompt file does not exist
        PathSecurityError: If a prompt file path violates security constraints
    """
    # Check for conflicting arguments
    if system_prompt is not None and system_prompt_file is not None:
        raise SystemPromptError(
            "Cannot specify both --system-prompt and --system-prompt-file"
        )

    # CLI system prompt takes precedence and stops further processing
    if system_prompt_file is not None:
        # Check for conflict with YAML frontmatter system_prompt and warn
        template_has_system_prompt = False
        if task_template.startswith("---\n"):
            end = task_template.find("\n---\n", 4)
            if end != -1:
                frontmatter = task_template[4:end]
                try:
                    metadata = yaml.safe_load(frontmatter)
                    if (
                        isinstance(metadata, dict)
                        and "system_prompt" in metadata
                    ):
                        template_has_system_prompt = True
                        logger.warning(
                            "Template has YAML frontmatter with 'system_prompt' field, but --sys-file was also provided. "
                            "Using --sys-file and ignoring YAML frontmatter system_prompt."
                        )
                except yaml.YAMLError:
                    # If YAML is invalid, we'll catch it later in template processing
                    pass

        try:
            name, path = validate_path_mapping(
                f"system_prompt={system_prompt_file}"
            )
            with open(path, "r", encoding="utf-8") as f:
                cli_system_prompt = f.read().strip()
        except OstructFileNotFoundError as e:
            raise SystemPromptError(
                f"Failed to load system prompt file: {e}"
            ) from e
        except PathSecurityError as e:
            raise SystemPromptError(f"Invalid system prompt file: {e}") from e

        try:
            template = env.from_string(cli_system_prompt)
            base_prompt = template.render(**template_context).strip()
        except jinja2.TemplateError as e:
            raise SystemPromptError(f"Error rendering system prompt: {e}")

        # Return the warning information along with the prompt
        return base_prompt, template_has_system_prompt

    elif system_prompt is not None:
        try:
            template = env.from_string(system_prompt)
            base_prompt = template.render(**template_context).strip()
        except jinja2.TemplateError as e:
            raise SystemPromptError(f"Error rendering system prompt: {e}")

    else:
        # Build message parts from template in order: auto-stub, include_system, system_prompt
        message_parts = []

        # 1. Auto-stub (default system prompt)
        message_parts.append("You are a helpful assistant.")

        # 2. Template-based system prompts (include_system and system_prompt)
        if not ignore_task_sysprompt:
            try:
                # Extract YAML frontmatter
                if task_template.startswith("---\n"):
                    end = task_template.find("\n---\n", 4)
                    if end != -1:
                        frontmatter = task_template[4:end]
                        try:
                            metadata = yaml.safe_load(frontmatter)
                            if isinstance(metadata, dict):
                                # 2a. include_system: from template
                                inc = metadata.get("include_system")
                                if inc and template_path:
                                    inc_path = (
                                        Path(template_path).parent / inc
                                    ).resolve()
                                    if not inc_path.is_file():
                                        raise click.ClickException(
                                            f"include_system file not found: {inc}"
                                        )
                                    include_txt = inc_path.read_text(
                                        encoding="utf-8"
                                    )
                                    message_parts.append(include_txt)

                                # 2b. system_prompt: from template
                                if "system_prompt" in metadata:
                                    template_system_prompt = str(
                                        metadata["system_prompt"]
                                    )
                                    try:
                                        template = env.from_string(
                                            template_system_prompt
                                        )
                                        message_parts.append(
                                            template.render(
                                                **template_context
                                            ).strip()
                                        )
                                    except jinja2.TemplateError as e:
                                        raise SystemPromptError(
                                            f"Error rendering system prompt: {e}"
                                        )
                        except yaml.YAMLError as e:
                            raise SystemPromptError(
                                f"Invalid YAML frontmatter: {e}"
                            )

            except Exception as e:
                raise SystemPromptError(
                    f"Error extracting system prompt from template: {e}"
                )

        # Return the combined message (remove default if we have other content)
        if len(message_parts) > 1:
            # Remove the default auto-stub if we have other content
            base_prompt = "\n\n".join(message_parts[1:]).strip()
        else:
            # Return just the default
            base_prompt = message_parts[0]

    # Add web search tool instructions if web search is enabled
    web_search_enabled = template_context.get("web_search_enabled", False)
    if web_search_enabled:
        web_search_instructions = (
            "\n\nYou have access to a web search tool for finding up-to-date information. "
            "Use it when you need current events, recent data, or real-time information. "
            "When using web search results, cite your sources in any 'sources' or 'references' "
            "field in the JSON schema if available. Do not include [n] citation markers "
            "within other JSON fields - keep the main content clean and put citations "
            "in dedicated source fields."
        )
        base_prompt += web_search_instructions

    # Add Code Interpreter download instructions if CI is enabled and auto_download is true
    code_interpreter_enabled = template_context.get(
        "code_interpreter_enabled", False
    )
    auto_download_enabled = template_context.get("auto_download_enabled", True)

    if code_interpreter_enabled and auto_download_enabled:
        ci_download_instructions = (
            "\n\nWhen using Code Interpreter to create files, always include markdown download links "
            "in your response using this exact format: [Download filename.ext](sandbox:/mnt/data/filename.ext). "
            "This enables automatic file download for the user. Include the download link immediately "
            "after creating each file."
        )

        # Add sentinel instructions for two-pass mode
        ci_config = template_context.get("code_interpreter_config", {})
        if ci_config.get("download_strategy") == "two_pass_sentinel":
            ci_download_instructions += (
                "\n\nAfter saving your files and printing the download links, output "
                "your JSON response between exactly these markers:\n"
                "===BEGIN_JSON===\n{ ... }\n===END_JSON===\n"
            )

        base_prompt += ci_download_instructions

    return base_prompt, False


def validate_task_template(
    task: Optional[str], task_file: Optional[str]
) -> str:
    """Validate and load a task template.

    Args:
        task: The task template string
        task_file: Path to task template file

    Returns:
        The task template string

    Raises:
        TaskTemplateVariableError: If neither task nor task_file is provided, or if both are provided
        TaskTemplateSyntaxError: If the template has invalid syntax
        FileNotFoundError: If the template file does not exist
        PathSecurityError: If the template file path violates security constraints
    """
    if task is not None and task_file is not None:
        raise TaskTemplateVariableError(
            "Cannot specify both --task and --task-file"
        )

    if task is None and task_file is None:
        raise TaskTemplateVariableError(
            "Must specify either --task or --task-file"
        )

    template_content: str
    if task_file is not None:
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                template_content = f.read()
        except FileNotFoundError:
            raise TaskTemplateVariableError(
                f"Task template file not found: {task_file}"
            )
        except PermissionError:
            raise TaskTemplateVariableError(
                f"Permission denied reading task template file: {task_file}"
            )
        except Exception as e:
            raise TaskTemplateVariableError(
                f"Error reading task template file: {e}"
            )
    else:
        template_content = task  # type: ignore  # We know task is str here due to the checks above

    try:
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.parse(template_content)
        return template_content
    except jinja2.TemplateSyntaxError as e:
        raise TaskTemplateSyntaxError(
            f"Invalid Jinja2 template syntax: {e.message}",
            context={
                "line": e.lineno,
                "template_file": task_file,
                "template_preview": template_content[:200],
            },
        )


async def process_templates(
    args: CLIParams,
    task_template: str,
    template_context: Dict[str, Any],
    env: jinja2.Environment,
    template_path: Optional[str] = None,
) -> Tuple[str, str]:
    """Process system and user prompt templates.

    Args:
        args: CLI parameters
        task_template: Task template content
        template_context: Template context variables
        env: Jinja2 environment with file reference support already configured
        template_path: Path to template file (for debugging)

    Returns:
        Tuple of (system_prompt, user_prompt)

    Raises:
        TemplateError: If template processing fails
        ValidationError: If template validation fails
    """
    # Show original template content if PRE_EXPAND capacity is active
    td_log_if_active(TDCap.PRE_EXPAND, "--- original template content ---")
    td_log_if_active(TDCap.PRE_EXPAND, task_template)
    td_log_if_active(TDCap.PRE_EXPAND, "--- end original template ---")

    # Check for debug mode
    debug_enabled = args.get("debug", False)
    debugger = None

    if debug_enabled or is_capacity_active(TDCap.POST_EXPAND):
        from .template_debug import TemplateDebugger

        debugger = TemplateDebugger()

    # System prompt processing
    system_prompt, _ = process_system_prompt(
        task_template,
        args.get("system_prompt"),
        args.get("system_prompt_file"),
        template_context,
        env,
        ignore_task_sysprompt=args.get("ignore_task_sysprompt", False),
        template_path=template_path,
    )

    # Render user prompt template
    user_prompt = render_template(task_template, template_context, env)

    # Generate XML appendix for referenced files if alias manager is available
    alias_manager = args.get("_alias_manager")
    if alias_manager:
        from .template_filters import AliasManager, XMLAppendixBuilder

        # Type assertion since we know this is an AliasManager
        assert isinstance(alias_manager, AliasManager)
        appendix_builder = XMLAppendixBuilder(alias_manager)
        appendix_content = appendix_builder.build_appendix()

        # Append XML content if any aliases were referenced
        if appendix_content:
            user_prompt = user_prompt + "\n\n" + appendix_content

    # Log user prompt rendering step
    if debugger:
        debugger.log_expansion_step(
            "User prompt rendered",
            task_template,
            user_prompt,
            template_context,
        )

    # Add post-expand logging
    td_log_if_active(TDCap.POST_EXPAND, "--- prompt 1/2 (system) ---")
    td_log_if_active(TDCap.POST_EXPAND, system_prompt)
    td_log_if_active(TDCap.POST_EXPAND, "--- prompt 2/2 (user) ---")
    td_log_if_active(TDCap.POST_EXPAND, user_prompt)

    # Log template expansion if debug enabled
    if debug_enabled or is_capacity_active(TDCap.STEPS):
        from .template_debug import log_template_expansion

        if debug_enabled:
            log_template_expansion(
                template_content=task_template,
                context=template_context,
                expanded=user_prompt,
                template_file=template_path,
            )

        # Show expansion summary and detailed steps
        if debugger:
            debugger.show_expansion_summary()
            debugger.show_detailed_expansion()

            # Show expansion statistics
            stats = debugger.get_expansion_stats()
            if stats:
                logger.debug(
                    f"📊 Expansion Stats: {stats['total_steps']} steps, {stats['unique_variables']} variables"
                )

    return system_prompt, user_prompt


def collect_simple_variables(args: CLIParams) -> Dict[str, str]:
    """Collect simple string variables from --var arguments.

    Args:
        args: Command line arguments

    Returns:
        Dictionary mapping variable names to string values

    Raises:
        VariableNameError: If a variable name is invalid or duplicate
    """
    variables: Dict[str, str] = {}
    all_names: Set[str] = set()

    if args.get("var"):
        for mapping in args["var"]:
            try:
                # Handle both tuple format and string format
                if isinstance(mapping, tuple):
                    name, value = mapping
                else:
                    name, value = mapping.split("=", 1)

                if not name.isidentifier():
                    raise VariableNameError(f"Invalid variable name: {name}")
                if name in all_names:
                    raise VariableNameError(f"Duplicate variable name: {name}")
                variables[name] = value
                all_names.add(name)
            except ValueError:
                raise VariableNameError(
                    f"Invalid variable mapping (expected name=value format): {mapping!r}"
                )

    return variables


def collect_json_variables(args: CLIParams) -> Dict[str, Any]:
    """Collect JSON variables from --json-var arguments.

    Args:
        args: Command line arguments

    Returns:
        Dictionary mapping variable names to parsed JSON values

    Raises:
        VariableNameError: If a variable name is invalid or duplicate
        InvalidJSONError: If a JSON value is invalid
    """
    variables: Dict[str, Any] = {}
    all_names: Set[str] = set()

    if args.get("json_var"):
        for mapping in args["json_var"]:
            try:
                # Handle both tuple format and string format
                if isinstance(mapping, tuple):
                    name, value = (
                        mapping  # Value is already parsed by Click validator
                    )
                else:
                    try:
                        name, json_str = mapping.split("=", 1)
                    except ValueError:
                        raise VariableNameError(
                            f"Invalid JSON variable mapping format: {mapping}. Expected name=json"
                        )
                    try:
                        value = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        raise InvalidJSONError(
                            f"Invalid JSON value for variable '{name}': {json_str}",
                            context={"variable_name": name},
                        ) from e

                if not name.isidentifier():
                    raise VariableNameError(f"Invalid variable name: {name}")
                if name in all_names:
                    raise VariableNameError(f"Duplicate variable name: {name}")

                variables[name] = value
                all_names.add(name)
            except (VariableNameError, InvalidJSONError):
                raise

    return variables


def extract_template_file_paths(template_context: Dict[str, Any]) -> List[str]:
    """Extract actual file paths from template context for token validation.

    Args:
        template_context: Template context dictionary containing FileInfoList objects

    Returns:
        List of file paths that were included in template rendering
    """
    file_paths = []

    for key, value in template_context.items():
        if isinstance(value, FileInfoList):
            # Extract paths from FileInfoList
            for file_info in value:
                if hasattr(file_info, "path"):
                    file_paths.append(file_info.path)
        elif key == "stdin":
            # Skip stdin content - it's already counted in template
            continue
        elif key == "current_model":
            # Skip model name
            continue

    return file_paths


def create_template_context(
    files: Optional[
        Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]]
    ] = None,
    variables: Optional[Dict[str, str]] = None,
    json_variables: Optional[Dict[str, Any]] = None,
    security_manager: Optional[SecurityManager] = None,
    stdin_content: Optional[str] = None,
) -> Dict[str, Any]:
    """Create template context from files and variables."""
    context: Dict[str, Any] = {}

    # Add file variables
    if files:
        for name, file_list in files.items():
            context[name] = file_list  # Always keep FileInfoList wrapper

    # Add simple variables
    if variables:
        context.update(variables)

    # Add JSON variables
    if json_variables:
        context.update(json_variables)

    # Add stdin if provided
    if stdin_content is not None:
        context["stdin"] = stdin_content

    return context


def _build_tool_context(
    args: CLIParams, routing_result: ProcessingResult
) -> Dict[str, Any]:
    """Build tool-related context variables.

    Args:
        args: Command line arguments
        routing_result: File routing result

    Returns:
        Dictionary with tool enablement and configuration context
    """
    from .config import OstructConfig

    context: Dict[str, Any] = {}

    # Load configuration
    config_path = args.get("config")
    config = OstructConfig.load(config_path)  # type: ignore[arg-type]

    # Universal tool toggle overrides
    enabled_tools: set[str] = args.get("_enabled_tools", set())  # type: ignore[assignment]
    disabled_tools: set[str] = args.get("_disabled_tools", set())  # type: ignore[assignment]

    # Web search configuration
    web_search_config = config.get_web_search_config()

    if "web-search" in enabled_tools:
        web_search_enabled = True
    elif "web-search" in disabled_tools:
        web_search_enabled = False
    else:
        web_search_enabled = web_search_config.enable_by_default

    context["web_search_enabled"] = web_search_enabled

    # Code interpreter configuration
    ci_enabled_by_routing = "code-interpreter" in routing_result.enabled_tools

    if "code-interpreter" in enabled_tools:
        code_interpreter_enabled = True
    elif "code-interpreter" in disabled_tools:
        code_interpreter_enabled = False
    else:
        code_interpreter_enabled = ci_enabled_by_routing

    context["code_interpreter_enabled"] = code_interpreter_enabled

    # Add CI config if enabled
    if code_interpreter_enabled:
        ci_config = config.get_code_interpreter_config()
        context["auto_download_enabled"] = ci_config.get("auto_download", True)

        # Handle feature flags for CI config
        effective_ci_config = dict(ci_config)
        enabled_features = args.get("enabled_features", [])
        disabled_features = args.get("disabled_features", [])

        if enabled_features or disabled_features:
            try:
                from .click_options import parse_feature_flags

                parsed_flags = parse_feature_flags(
                    tuple(enabled_features), tuple(disabled_features)
                )
                ci_hack_flag = parsed_flags.get("ci-download-hack")
                if ci_hack_flag == "on":
                    effective_ci_config["download_strategy"] = (
                        "two_pass_sentinel"
                    )
                elif ci_hack_flag == "off":
                    effective_ci_config["download_strategy"] = "single_pass"
            except Exception as e:
                logger.warning(f"Failed to parse feature flags: {e}")

        context["code_interpreter_config"] = effective_ci_config
    else:
        context["auto_download_enabled"] = False
        context["code_interpreter_config"] = {}

    return context


def _generate_template_variable_name(file_path: str) -> str:
    """Generate a template variable name from a file path.

    Converts filename to a valid template variable name by:
    1. Taking the full filename (with extension)
    2. Replacing dots and other special characters with underscores
    3. Ensuring it starts with a letter or underscore

    Examples:
        data.csv -> data_csv
        data.json -> data_json
        my-file.txt -> my_file_txt
        123data.xml -> _123data_xml

    Args:
        file_path: Path to the file

    Returns:
        Valid template variable name
    """
    filename = Path(file_path).name
    # Replace special characters with underscores
    var_name = re.sub(r"[^a-zA-Z0-9_]", "_", filename)
    # Ensure it starts with letter or underscore
    if var_name and var_name[0].isdigit():
        var_name = "_" + var_name
    return var_name


async def create_template_context_from_routing(
    args: CLIParams,
    security_manager: SecurityManager,
    routing_result: ProcessingResult,
) -> Dict[str, Any]:
    """Create template context from explicit file routing result.

    Args:
        args: Command line arguments
        security_manager: Security manager for path validation
        routing_result: Result from explicit file processor

    Returns:
        Template context dictionary

    Raises:
        PathSecurityError: If any file paths violate security constraints
        VariableError: If variable mappings are invalid
        ValueError: If file mappings are invalid or files cannot be accessed
    """
    try:
        # Template context creation from new attachment system (T3.1)
        logger.debug("Creating template context from new attachment system")

        from .attachment_processor import (
            AttachmentProcessor,
            ProcessedAttachments,
            _extract_attachments_from_args,
            _has_new_attachment_syntax,
        )
        from .attachment_template_bridge import (
            build_template_context_from_attachments,
        )

        # Check if we have new attachment syntax
        if _has_new_attachment_syntax(args):
            # Re-process attachments for template context creation
            # This ensures we have the full ProcessedAttachments structure
            processor = AttachmentProcessor(security_manager)
            attachments = _extract_attachments_from_args(args)
            processed_attachments = processor.process_attachments(attachments)
        else:
            # No attachments specified - create empty processed attachments
            processed_attachments = ProcessedAttachments()

        # Build base context from variables
        base_context = {}

        # Collect simple variables
        variables = collect_simple_variables(args)
        base_context.update(variables)

        # Collect JSON variables
        json_variables = collect_json_variables(args)
        base_context.update(json_variables)

        # Add standard context variables
        import sys

        stdin_content = None
        try:
            if not sys.stdin.isatty():
                stdin_content = sys.stdin.read()
        except (OSError, IOError):
            pass

        if stdin_content is not None:
            base_context["stdin"] = stdin_content

        # Add current model to context
        base_context["current_model"] = args["model"]

        # Add tool enablement flags
        base_context.update(_build_tool_context(args, routing_result))

        # Build attachment-based context
        # In dry-run mode, use strict mode to fail fast on binary file errors
        strict_mode = args.get("dry_run", False)
        context = build_template_context_from_attachments(
            processed_attachments,
            security_manager,
            base_context,
            strict_mode=strict_mode,
        )

        # Add debugging support for new attachment system
        debug_enabled = args.get("debug", False)

        if (
            debug_enabled
            or is_capacity_active(TDCap.VARS)
            or is_capacity_active(TDCap.PREVIEW)
        ):
            from .attachment_template_bridge import AttachmentTemplateContext

            context_builder = AttachmentTemplateContext(security_manager)
            context_builder.debug_attachment_context(
                context,
                processed_attachments,
                show_detailed=(
                    debug_enabled or is_capacity_active(TDCap.PREVIEW)
                ),
            )

        # Add proper template debug capacity logging with prefixes
        if is_capacity_active(TDCap.VARS):
            td_log_vars(context)

        if is_capacity_active(TDCap.PREVIEW):
            td_log_preview(context)

        logger.debug(
            f"Built attachment-based template context with {len(context)} variables"
        )
        return context

    except PathSecurityError:
        # Let PathSecurityError propagate without wrapping
        raise
    except (FileNotFoundError, DirectoryNotFoundError) as e:
        # Convert FileNotFoundError to OstructFileNotFoundError
        if isinstance(e, FileNotFoundError):
            raise OstructFileNotFoundError(str(e))
        # Let DirectoryNotFoundError propagate
        raise
    except Exception as e:
        # Don't wrap InvalidJSONError
        if isinstance(e, InvalidJSONError):
            raise
        # Don't wrap DuplicateFileMappingError
        if isinstance(e, DuplicateFileMappingError):
            raise
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            raise e.__cause__
        # Wrap other errors
        raise ValueError(f"Error collecting files: {e}")
