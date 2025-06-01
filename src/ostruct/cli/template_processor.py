"""Template processing functions for ostruct CLI."""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

import click
import jinja2
import yaml

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
from .file_utils import FileInfoList, collect_files
from .path_utils import validate_path_mapping
from .security import SecurityManager
from .template_optimizer import (
    is_optimization_beneficial,
    optimize_template_for_llm,
)
from .template_utils import render_template
from .types import CLIParams

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


def _render_template_with_debug(
    template_content: str,
    context: Dict[str, Any],
    env: jinja2.Environment,
    no_optimization: bool = False,
    show_optimization_diff: bool = False,
    show_optimization_steps: bool = False,
    optimization_step_detail: str = "summary",
) -> str:
    """Render template with optimization debugging support.

    Args:
        template_content: Template content to render
        context: Template context variables
        env: Jinja2 environment
        no_optimization: Skip optimization entirely
        show_optimization_diff: Show before/after optimization comparison
        show_optimization_steps: Show detailed optimization step tracking
        optimization_step_detail: Level of detail for optimization steps

    Returns:
        Rendered template string
    """
    from .template_debug import show_optimization_diff as show_diff

    if no_optimization:
        # Skip optimization entirely - render directly
        template = env.from_string(template_content)
        return template.render(**context)

    # Handle optimization debugging (diff and/or steps)
    if show_optimization_diff or show_optimization_steps:
        # Check if optimization would be beneficial
        if is_optimization_beneficial(template_content):
            # Create step tracker if step tracking is enabled
            step_tracker = None
            if show_optimization_steps:
                from .template_debug import OptimizationStepTracker

                step_tracker = OptimizationStepTracker(enabled=True)

            # Get optimization result with optional step tracking
            optimization_result = optimize_template_for_llm(
                template_content, step_tracker
            )

            if optimization_result.has_optimizations:
                # Show the diff if requested
                if show_optimization_diff:
                    show_diff(
                        template_content,
                        optimization_result.optimized_template,
                    )

                # Show optimization steps if requested
                if show_optimization_steps and step_tracker:
                    if optimization_step_detail == "detailed":
                        step_tracker.show_detailed_steps()
                    else:
                        step_tracker.show_step_summary()

                # Render the optimized version
                template = env.from_string(
                    optimization_result.optimized_template
                )
                return template.render(**context)

        # No optimization was applied, show that too
        if show_optimization_diff:
            show_diff(template_content, template_content)
        if show_optimization_steps:
            from .template_debug import (
                show_optimization_steps as show_steps_func,
            )

            show_steps_func([], optimization_step_detail)

    # Fall back to standard rendering (which includes optimization)
    return render_template(template_content, context, env)


def process_system_prompt(
    task_template: str,
    system_prompt: Optional[str],
    system_prompt_file: Optional[str],
    template_context: Dict[str, Any],
    env: jinja2.Environment,
    ignore_task_sysprompt: bool = False,
    template_path: Optional[str] = None,
) -> str:
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
        The final system prompt string

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

    return base_prompt


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
    """Process system prompt and user prompt templates.

    Args:
        args: Command line arguments
        task_template: Validated task template
        template_context: Template context dictionary
        env: Jinja2 environment

    Returns:
        Tuple of (system_prompt, user_prompt)

    Raises:
        CLIError: For template processing errors
    """
    logger.debug("=== Template Processing Phase ===")

    # Add template debugging if enabled
    debug_enabled = args.get("debug", False)
    debug_templates_enabled = args.get("debug_templates", False)
    show_context = args.get("show_context", False)
    show_context_detailed = args.get("show_context_detailed", False)
    show_pre_optimization = args.get("show_pre_optimization", False)
    show_optimization_diff = args.get("show_optimization_diff", False)
    no_optimization = args.get("no_optimization", False)
    show_optimization_steps = args.get("show_optimization_steps", False)
    optimization_step_detail = args.get("optimization_step_detail", "summary")

    debugger = None
    if debug_enabled or debug_templates_enabled:
        from .template_debug import (
            TemplateDebugger,
            log_template_expansion,
            show_file_content_expansions,
        )

        # Initialize template debugger
        debugger = TemplateDebugger(enabled=True)

        # Log template context
        show_file_content_expansions(template_context)

        # Log raw template before expansion
        logger.debug("Raw task template:")
        logger.debug(task_template)

        # Log initial template state
        debugger.log_expansion_step(
            "Initial template loaded",
            "",
            task_template,
            {"template_path": template_path},
        )

    # Show context inspection if requested
    if show_context or show_context_detailed:
        from .template_debug import (
            display_context_detailed,
            display_context_summary,
        )

        if show_context_detailed:
            display_context_detailed(template_context)
        elif show_context:
            display_context_summary(template_context)

        # Check for undefined variables if context inspection is enabled
        from .template_debug import detect_undefined_variables

        undefined_vars = detect_undefined_variables(
            task_template, template_context
        )
        if undefined_vars:
            click.echo(
                f"⚠️  Potentially undefined variables: {', '.join(undefined_vars)}",
                err=True,
            )
            click.echo(
                f"   Available variables: {', '.join(sorted(template_context.keys()))}",
                err=True,
            )

    system_prompt = process_system_prompt(
        task_template,
        args.get("system_prompt"),
        args.get("system_prompt_file"),
        template_context,
        env,
        args.get("ignore_task_sysprompt", False),
        template_path,
    )

    # Log system prompt processing step
    if debugger:
        debugger.log_expansion_step(
            "System prompt processed",
            task_template,
            system_prompt,
            {
                "system_prompt_source": (
                    "task_template"
                    if not args.get("system_prompt")
                    else "custom"
                )
            },
        )

    # Handle pre-optimization template display
    if show_pre_optimization:
        from .template_debug import show_pre_optimization_template

        show_pre_optimization_template(task_template)

        # Handle optimization debugging with custom rendering
    if no_optimization or show_optimization_diff or show_optimization_steps:
        # We need custom handling for optimization debugging
        user_prompt = _render_template_with_debug(
            task_template,
            template_context,
            env,
            no_optimization=bool(no_optimization),
            show_optimization_diff=bool(show_optimization_diff),
            show_optimization_steps=bool(show_optimization_steps),
            optimization_step_detail=str(optimization_step_detail),
        )
    else:
        # Standard rendering with optimization
        user_prompt = render_template(task_template, template_context, env)

    # Log user prompt rendering step
    if debugger:
        debugger.log_expansion_step(
            "User prompt rendered",
            task_template,
            user_prompt,
            template_context,
        )

    # Log template expansion if debug enabled
    if debug_enabled or debug_templates_enabled:
        from .template_debug import log_template_expansion

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


def collect_template_files(
    args: CLIParams,
    security_manager: SecurityManager,
) -> Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]]:
    """Collect files from command line arguments.

    Args:
        args: Command line arguments
        security_manager: Security manager for path validation

    Returns:
        Dictionary mapping variable names to file info objects

    Raises:
        PathSecurityError: If any file paths violate security constraints
        ValueError: If file mappings are invalid or files cannot be accessed
    """
    try:
        # Get files, directories, and patterns from args - they are already tuples from Click's nargs=2
        files = list(
            args.get("files", [])
        )  # List of (name, path) tuples from Click
        dirs = args.get("dir", [])  # List of (name, dir) tuples from Click
        patterns = args.get(
            "patterns", []
        )  # List of (name, pattern) tuples from Click

        # Collect files from directories and patterns
        dir_files = collect_files(
            file_mappings=cast(List[Tuple[str, Union[str, Path]]], files),
            dir_mappings=cast(List[Tuple[str, Union[str, Path]]], dirs),
            pattern_mappings=cast(
                List[Tuple[str, Union[str, Path]]], patterns
            ),
            dir_recursive=args.get("recursive", False),
            security_manager=security_manager,
            routing_type="template",  # Indicate these are primarily for template access
        )

        # Combine results
        return cast(
            Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]],
            dir_files,
        )

    except Exception as e:
        # Check for nested security errors
        if hasattr(e, "__cause__") and hasattr(e.__cause__, "__class__"):
            if "SecurityError" in str(e.__cause__.__class__) and isinstance(
                e.__cause__, BaseException
            ):
                raise e.__cause__
            if "PathSecurityError" in str(
                e.__cause__.__class__
            ) and isinstance(e.__cause__, BaseException):
                raise e.__cause__
        # Check if this is a wrapped security error
        if isinstance(e.__cause__, PathSecurityError):
            raise e.__cause__
        # Don't wrap InvalidJSONError
        if isinstance(e, InvalidJSONError):
            raise
        # Don't wrap DuplicateFileMappingError
        if isinstance(e, DuplicateFileMappingError):
            raise
        # Catch broader exceptions and re-raise
        logger.error(
            "Error collecting template files: %s", str(e), exc_info=True
        )
        raise


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
        # Get files from routing result - include ALL routed files in template context
        template_files = routing_result.validated_files.get("template", [])
        code_interpreter_files = routing_result.validated_files.get(
            "code-interpreter", []
        )
        file_search_files = routing_result.validated_files.get(
            "file-search", []
        )

        # Convert to the format expected by create_template_context
        # For legacy compatibility, we need (name, path) tuples
        files_tuples = []
        seen_files = set()  # Track files to avoid duplicates

        # Add template files - now single-argument auto-naming only
        template_file_paths = args.get("template_files", [])
        for template_file_path in template_file_paths:
            if isinstance(template_file_path, (str, Path)):
                # Auto-generate name for single-arg form: -ft config.yaml
                file_name = _generate_template_variable_name(
                    str(template_file_path)
                )
                file_path_str = str(template_file_path)
                if file_path_str not in seen_files:
                    files_tuples.append((file_name, file_path_str))
                    seen_files.add(file_path_str)

        # Add template file aliases (from --fta) - two-argument explicit naming
        template_file_aliases = args.get("template_file_aliases", [])
        for name_path_tuple in template_file_aliases:
            if (
                isinstance(name_path_tuple, tuple)
                and len(name_path_tuple) == 2
            ):
                custom_name, file_path_raw = name_path_tuple
                file_path = str(file_path_raw)
                file_name = str(
                    custom_name
                )  # Always use custom name for aliases

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Also process template_files from routing result (for compatibility)
        for template_file_item in template_files:
            if isinstance(template_file_item, (str, Path)):
                file_name = _generate_template_variable_name(
                    str(template_file_item)
                )
                file_path_str = str(template_file_item)
                if file_path_str not in seen_files:
                    files_tuples.append((file_name, file_path_str))
                    seen_files.add(file_path_str)
            elif (
                isinstance(template_file_item, tuple)
                and len(template_file_item) == 2
            ):
                # Handle tuple format (name, path)
                _, template_file_path = template_file_item
                template_file_path_str = str(template_file_path)
                file_name = _generate_template_variable_name(
                    template_file_path_str
                )
                if template_file_path_str not in seen_files:
                    files_tuples.append((file_name, template_file_path_str))
                    seen_files.add(template_file_path_str)

        # Add code interpreter files - now single-argument auto-naming only
        code_interpreter_file_paths = args.get("code_interpreter_files", [])
        for ci_file_path in code_interpreter_file_paths:
            if isinstance(ci_file_path, (str, Path)):
                # Auto-generate name: -fc data.csv
                file_name = _generate_template_variable_name(str(ci_file_path))
                file_path_str = str(ci_file_path)
                if file_path_str not in seen_files:
                    files_tuples.append((file_name, file_path_str))
                    seen_files.add(file_path_str)

        # Add code interpreter file aliases (from --fca) - two-argument explicit naming
        code_interpreter_file_aliases = args.get(
            "code_interpreter_file_aliases", []
        )
        for name_path_tuple in code_interpreter_file_aliases:
            if (
                isinstance(name_path_tuple, tuple)
                and len(name_path_tuple) == 2
            ):
                custom_name, file_path_raw = name_path_tuple
                file_path = str(file_path_raw)
                file_name = str(
                    custom_name
                )  # Always use custom name for aliases

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Also process code_interpreter_files from routing result (for compatibility)
        for ci_file_item in code_interpreter_files:
            if isinstance(ci_file_item, (str, Path)):
                file_name = _generate_template_variable_name(str(ci_file_item))
                file_path_str = str(ci_file_item)
                if file_path_str not in seen_files:
                    files_tuples.append((file_name, file_path_str))
                    seen_files.add(file_path_str)
            elif isinstance(ci_file_item, tuple) and len(ci_file_item) == 2:
                # Handle tuple format (name, path)
                _, ci_file_path = ci_file_item
                ci_file_path_str = str(ci_file_path)
                file_name = _generate_template_variable_name(ci_file_path_str)
                if ci_file_path_str not in seen_files:
                    files_tuples.append((file_name, ci_file_path_str))
                    seen_files.add(ci_file_path_str)

        # Add file search files - now single-argument auto-naming only
        file_search_file_paths = args.get("file_search_files", [])
        for fs_file_path in file_search_file_paths:
            if isinstance(fs_file_path, (str, Path)):
                # Auto-generate name: -fs docs.pdf
                file_name = _generate_template_variable_name(str(fs_file_path))
                file_path_str = str(fs_file_path)
                if file_path_str not in seen_files:
                    files_tuples.append((file_name, file_path_str))
                    seen_files.add(file_path_str)

        # Add file search file aliases (from --fsa) - two-argument explicit naming
        file_search_file_aliases = args.get("file_search_file_aliases", [])
        for name_path_tuple in file_search_file_aliases:
            if (
                isinstance(name_path_tuple, tuple)
                and len(name_path_tuple) == 2
            ):
                custom_name, file_path_raw = name_path_tuple
                file_path = str(file_path_raw)
                file_name = str(
                    custom_name
                )  # Always use custom name for aliases

                if file_path not in seen_files:
                    files_tuples.append((file_name, file_path))
                    seen_files.add(file_path)

        # Also process file_search_files from routing result (for compatibility)
        for fs_file_item in file_search_files:
            if isinstance(fs_file_item, (str, Path)):
                file_name = _generate_template_variable_name(str(fs_file_item))
                file_path_str = str(fs_file_item)
                if file_path_str not in seen_files:
                    files_tuples.append((file_name, file_path_str))
                    seen_files.add(file_path_str)
            elif isinstance(fs_file_item, tuple) and len(fs_file_item) == 2:
                # Handle tuple format (name, path)
                _, fs_file_path = fs_file_item
                fs_file_path_str = str(fs_file_path)
                file_name = _generate_template_variable_name(fs_file_path_str)
                if fs_file_path_str not in seen_files:
                    files_tuples.append((file_name, fs_file_path_str))
                    seen_files.add(fs_file_path_str)

        # Handle directory aliases - create stable template variables for directories
        dir_mappings = []

        # Get directory aliases from routing result (these are already processed from CLI args)
        routing = routing_result.routing
        for alias_name, dir_path in routing.template_dir_aliases:
            dir_mappings.append((alias_name, str(dir_path)))
        for alias_name, dir_path in routing.code_interpreter_dir_aliases:
            dir_mappings.append((alias_name, str(dir_path)))
        for alias_name, dir_path in routing.file_search_dir_aliases:
            dir_mappings.append((alias_name, str(dir_path)))

        # Auto-naming directories (from -dt, -dc, -ds)
        template_dirs = args.get("template_dirs", [])
        for dir_path in template_dirs:
            dir_name = _generate_template_variable_name(str(dir_path))
            dir_mappings.append((dir_name, str(dir_path)))

        code_interpreter_dirs = args.get("code_interpreter_dirs", [])
        for dir_path in code_interpreter_dirs:
            dir_name = _generate_template_variable_name(str(dir_path))
            dir_mappings.append((dir_name, str(dir_path)))

        file_search_dirs = args.get("file_search_dirs", [])
        for dir_path in file_search_dirs:
            dir_name = _generate_template_variable_name(str(dir_path))
            dir_mappings.append((dir_name, str(dir_path)))

        # Process files from explicit routing
        files_dict = collect_files(
            file_mappings=cast(
                List[Tuple[str, Union[str, Path]]], files_tuples
            ),
            dir_mappings=cast(
                List[Tuple[str, Union[str, Path]]], dir_mappings
            ),
            dir_recursive=args.get("recursive", False),
            security_manager=security_manager,
            routing_type="template",  # Explicitly set routing_type for files processed here
            # This needs careful thought as files_tuples can come from various sources
            # For now, we assume files directly added to files_tuples are 'template' routed
            # if not overridden by a more specific tool routing later.
            # This is a simplification. A more robust way would be to track routing type
            # for each path as it's parsed from CLI args.
            # For the large file warning, FileInfo will default routing_type to None
            # which FileInfo.content interprets as potentially template-routed.
        )

        # Handle legacy files and directories separately to preserve variable names
        legacy_files = args.get("files", [])
        legacy_dirs = args.get("dir", [])
        legacy_patterns = args.get("patterns", [])

        if legacy_files or legacy_dirs or legacy_patterns:
            legacy_files_dict = collect_files(
                file_mappings=cast(
                    List[Tuple[str, Union[str, Path]]], legacy_files
                ),
                dir_mappings=cast(
                    List[Tuple[str, Union[str, Path]]], legacy_dirs
                ),
                pattern_mappings=cast(
                    List[Tuple[str, Union[str, Path]]], legacy_patterns
                ),
                dir_recursive=args.get("recursive", False),
                security_manager=security_manager,
                routing_type="template",  # Legacy flags are considered template-only
            )
            # Merge legacy results into the main template context
            files_dict.update(legacy_files_dict)

        # Collect simple variables
        variables = collect_simple_variables(args)

        # Collect JSON variables
        json_variables = collect_json_variables(args)

        # Get stdin content if available
        stdin_content = None
        try:
            if not sys.stdin.isatty():
                stdin_content = sys.stdin.read()
        except (OSError, IOError):
            # Skip stdin if it can't be read
            pass

        context = create_template_context(
            files=cast(
                Dict[str, Union[FileInfoList, str, List[str], Dict[str, str]]],
                files_dict,
            ),
            variables=variables,
            json_variables=json_variables,
            security_manager=security_manager,
            stdin_content=stdin_content,
        )

        # Add current model to context
        context["current_model"] = args["model"]

        # Add web search enabled flag to context
        # Use the same logic as runner.py for consistency
        web_search_from_cli = args.get("web_search", False)
        no_web_search_from_cli = args.get("no_web_search", False)

        # Load configuration to check defaults
        from .config import OstructConfig

        config_path = cast(Union[str, Path, None], args.get("config"))
        config = OstructConfig.load(config_path)
        web_search_config = config.get_web_search_config()

        # Determine if web search should be enabled
        if web_search_from_cli:
            # Explicit --web-search flag takes precedence
            web_search_enabled = True
        elif no_web_search_from_cli:
            # Explicit --no-web-search flag disables
            web_search_enabled = False
        else:
            # Use config default
            web_search_enabled = web_search_config.enable_by_default

        context["web_search_enabled"] = web_search_enabled

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
