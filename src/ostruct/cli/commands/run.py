"""Run command for ostruct CLI."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Tuple

import rich_click as click

from ..click_options import all_options
from ..config import OstructConfig
from ..errors import (
    CLIError,
    InvalidJSONError,
    SchemaFileError,
    SchemaValidationError,
    handle_error,
)
from ..exit_codes import ExitCode
from ..runner import run_cli_async
from ..types import CLIParams

logger = logging.getLogger(__name__)


@click.command(
    cls=click.RichCommand,
    context_settings={
        "help_option_names": ["-h", "--help"],
    },
)
@click.argument("task_template", type=click.Path(exists=True))
@click.argument("schema_file", type=click.Path(exists=True))
@all_options
@click.pass_context
def run(
    ctx: click.Context,
    task_template: str,
    schema_file: str,
    **kwargs: Any,
) -> None:
    """Transform unstructured inputs into structured JSON using OpenAI APIs, Jinja2 templates, and powerful tool integrations.

    🚀 QUICK START

    ostruct run template.j2 schema.json -V name=value

    📎 FILE ATTACHMENT

    --file data file.txt              Template access (default)

    --file ci:data data.csv           Code Interpreter upload

    --file fs:docs manual.pdf         File Search upload

    🔧 TOOL INTEGRATION

    --enable-tool code-interpreter    Code execution & analysis

    --enable-tool file-search         Document search & retrieval

    --enable-tool web-search          Real-time web information

    🔧 ENVIRONMENT VARIABLES

    ```text
    Core API Configuration:
    OPENAI_API_KEY                           OpenAI API authentication key
    OPENAI_API_BASE                          Custom OpenAI API base URL

    Template Processing Limits:
    OSTRUCT_TEMPLATE_FILE_LIMIT              Max individual file size (default: 64KB)
    OSTRUCT_TEMPLATE_TOTAL_LIMIT             Max total files size (default: 1MB)
    OSTRUCT_TEMPLATE_PREVIEW_LIMIT           Template preview size limit (default: 4096)

    System Behavior:
    OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS   Disable model registry updates
    OSTRUCT_MCP_URL_<name>                   Custom MCP server URLs
    ```

    See organized option groups below for complete functionality.
    """
    try:
        # Convert Click parameters to typed dict
        params: CLIParams = {
            "task_file": task_template,
            "task": None,
            "schema_file": schema_file,
        }
        # Add all kwargs to params (type ignore for dynamic key assignment)
        for k, v in kwargs.items():
            params[k] = v  # type: ignore[literal-required]

        # UNIFIED GUIDELINES: Validate JSON flag combinations
        if kwargs.get("dry_run_json") and not kwargs.get("dry_run"):
            raise click.BadOptionUsage(
                "--dry-run-json", "--dry-run-json requires --dry-run"
            )

        if kwargs.get("run_summary_json") and kwargs.get("dry_run"):
            raise click.BadOptionUsage(
                "--run-summary-json",
                "--run-summary-json cannot be used with --dry-run",
            )

        # Process tool toggle flags (Step 2: Conflict guard & normalisation)
        enabled_tools_raw: Tuple[str, ...] = params.get("enabled_tools", ())  # type: ignore[assignment]
        disabled_tools_raw: Tuple[str, ...] = params.get("disabled_tools", ())  # type: ignore[assignment]

        logger.debug(f"Raw enabled tools: {enabled_tools_raw}")
        logger.debug(f"Raw disabled tools: {disabled_tools_raw}")

        # Ensure we have lists to iterate over (Click returns tuples for multiple=True)
        enabled_list: list[str] = list(enabled_tools_raw)
        disabled_list: list[str] = list(disabled_tools_raw)

        enabled_tools = {t.lower() for t in enabled_list}
        disabled_tools = {t.lower() for t in disabled_list}

        logger.debug(f"Enabled tools normalized: {enabled_tools}")
        logger.debug(f"Disabled tools normalized: {disabled_tools}")

        # Check for conflicts
        dupes = enabled_tools & disabled_tools
        if dupes:
            logger.error(f"Tool conflict detected: {dupes}")
            raise click.UsageError(
                f"--enable-tool and --disable-tool both specified for: {', '.join(sorted(dupes))}"
            )

        # Store normalized tool toggles for later stages
        params["_enabled_tools"] = enabled_tools  # type: ignore[typeddict-unknown-key]
        params["_disabled_tools"] = disabled_tools  # type: ignore[typeddict-unknown-key]

        # Apply configuration defaults if values not explicitly provided
        # Check for command-level config option first, then group-level
        command_config = kwargs.get("config")
        if command_config:
            config = OstructConfig.load(command_config)
        else:
            config = ctx.obj.get("config") if ctx.obj else OstructConfig()

        if params.get("model") is None:
            params["model"] = config.get_model_default()

        # Apply file collection configuration defaults
        file_collection_config = config.get_file_collection_config()
        if params.get("ignore_gitignore") is None:
            params["ignore_gitignore"] = (
                file_collection_config.ignore_gitignore
            )
        if params.get("gitignore_file") is None:
            params["gitignore_file"] = file_collection_config.gitignore_file

        # UNIFIED GUIDELINES: Perform basic validation even in dry-run mode
        if kwargs.get("dry_run"):
            # Import validation functions
            from ..attachment_processor import (
                AttachmentSpec,
                ProcessedAttachments,
            )
            from ..plan_assembly import PlanAssembler
            from ..plan_printing import PlanPrinter
            from ..validators import validate_inputs

            # Variables to track validation state
            validation_passed = True
            template_warning = None
            original_template_path = task_template

            # Process attachments for the dry-run plan
            processed_attachments = ProcessedAttachments()

            # Get global flags that apply to ALL applicable attachments
            recursive_flag = kwargs.get("recursive", False)
            pattern_flag = kwargs.get("pattern", None)

            # Get gitignore settings
            ignore_gitignore = kwargs.get("ignore_gitignore", False)
            gitignore_file = kwargs.get("gitignore_file")

            # Process --file attachments
            files = kwargs.get("attaches", [])
            for file_spec in files:
                spec = AttachmentSpec(
                    alias=file_spec["alias"],
                    path=file_spec["path"],
                    targets=file_spec["targets"],
                    recursive=False,  # Files don't use recursive
                    pattern=None,  # Files don't use pattern
                    ignore_gitignore=ignore_gitignore,
                    gitignore_file=gitignore_file,
                )
                processed_attachments.alias_map[spec.alias] = spec

                # Route to appropriate lists based on targets
                if "prompt" in spec.targets:
                    processed_attachments.template_files.append(spec)
                if "code-interpreter" in spec.targets or "ci" in spec.targets:
                    processed_attachments.ci_files.append(spec)
                if "file-search" in spec.targets or "fs" in spec.targets:
                    processed_attachments.fs_files.append(spec)

            # Process --dir attachments
            dirs = kwargs.get("dirs", [])
            for dir_spec in dirs:
                spec = AttachmentSpec(
                    alias=dir_spec["alias"],
                    path=dir_spec["path"],
                    targets=dir_spec["targets"],
                    recursive=recursive_flag,  # Apply global flag
                    pattern=pattern_flag,  # Apply global flag
                    ignore_gitignore=ignore_gitignore,
                    gitignore_file=gitignore_file,
                )
                processed_attachments.alias_map[spec.alias] = spec

                # Route to appropriate lists based on targets
                if "prompt" in spec.targets:
                    processed_attachments.template_dirs.append(spec)
                if "code-interpreter" in spec.targets or "ci" in spec.targets:
                    processed_attachments.ci_dirs.append(spec)
                if "file-search" in spec.targets or "fs" in spec.targets:
                    processed_attachments.fs_dirs.append(spec)

            # Process --collect attachments
            collects = kwargs.get("collects", [])
            for collect_spec in collects:
                spec = AttachmentSpec(
                    alias=collect_spec["alias"],
                    path=collect_spec["path"],
                    targets=collect_spec["targets"],
                    recursive=recursive_flag,  # Apply global flag
                    pattern=pattern_flag,  # Apply global flag
                    from_collection=True,
                    attachment_type="collection",
                    ignore_gitignore=ignore_gitignore,
                    gitignore_file=gitignore_file,
                )
                processed_attachments.alias_map[spec.alias] = spec

                # Route to appropriate lists based on targets
                if "prompt" in spec.targets:
                    processed_attachments.template_dirs.append(spec)
                if "code-interpreter" in spec.targets or "ci" in spec.targets:
                    processed_attachments.ci_dirs.append(spec)
                if "file-search" in spec.targets or "fs" in spec.targets:
                    processed_attachments.fs_dirs.append(spec)

            try:
                # Perform the same input validation as live runs (async)
                logger.debug("Performing dry-run validation")

                # Run async validation
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Use the same params structure as the live run
                    validation_result = loop.run_until_complete(
                        validate_inputs(params)
                    )
                    # Extract components from the tuple
                    (
                        security_manager,
                        validated_template,
                        schema,
                        template_context,
                        env,
                        template_path,
                    ) = validation_result

                    # Update task_template with validated content
                    task_template = validated_template

                    # Perform template rendering validation to catch binary file access errors
                    logger.debug("Performing template rendering validation")
                    from ..template_processor import process_templates

                    system_prompt, user_prompt = loop.run_until_complete(
                        process_templates(
                            params,
                            task_template,
                            template_context,
                            env,
                            template_path,
                        )
                    )
                    logger.debug("Template rendering validation passed")

                    # Check for template warnings by processing system prompt
                    from typing import cast

                    from ..template_processor import process_system_prompt

                    result = cast(
                        Tuple[str, bool],
                        process_system_prompt(
                            task_template,
                            params.get("system_prompt"),
                            params.get("system_prompt_file"),
                            template_context,
                            env,
                            params.get("ignore_task_sysprompt", False),
                            template_path,
                        ),
                    )
                    _system_prompt_check: str
                    template_has_conflict: bool
                    _system_prompt_check, template_has_conflict = result

                    if template_has_conflict:
                        template_warning = (
                            "Template has YAML frontmatter with 'system_prompt' field, but --sys-file was also provided. "
                            "Using --sys-file and ignoring YAML frontmatter system_prompt."
                        )

                finally:
                    loop.close()

            except Exception as e:
                validation_passed = False
                template_warning = str(e)
                logger.error(f"Dry-run validation failed: {e}")

                # For critical errors, exit immediately with proper error handling
                if not isinstance(e, (ValueError, FileNotFoundError)):
                    handle_error(e)
                    if hasattr(e, "exit_code"):
                        ctx.exit(int(e.exit_code))
                    else:
                        ctx.exit(1)

            # Build plan with warning information
            plan_kwargs = {
                "allowed_paths": params.get("allowed_paths", []),
                "cost_estimate": None,  # We don't have cost estimate in dry run
                "template_warning": template_warning,
                "original_template_path": original_template_path,
                "validation_passed": validation_passed,
            }

            # Add enabled tools from routing result and explicit tool toggles
            plan_enabled_tools: set[str] = set()

            # Get tools from routing result (auto-enabled by file attachments)
            routing_result = params.get("_routing_result")
            if routing_result and hasattr(routing_result, "enabled_tools"):
                plan_enabled_tools.update(routing_result.enabled_tools)

            # Add explicitly enabled tools
            explicit_enabled = params.get("_enabled_tools", set())
            if isinstance(explicit_enabled, set):
                plan_enabled_tools.update(explicit_enabled)

            # Remove explicitly disabled tools
            explicit_disabled = params.get("_disabled_tools", set())
            if isinstance(explicit_disabled, set):
                plan_enabled_tools -= explicit_disabled

            if plan_enabled_tools:
                plan_kwargs["enabled_tools"] = plan_enabled_tools

            # Add CI configuration for download validation
            if "code-interpreter" in plan_enabled_tools:
                config_path = params.get("config")
                config = OstructConfig.load(
                    config_path
                    if isinstance(config_path, (str, Path))
                    else None
                )
                ci_config = config.get_code_interpreter_config()
                plan_kwargs["ci_config"] = ci_config

            plan = PlanAssembler.build_execution_plan(
                processed_attachments=processed_attachments,
                template_path=original_template_path,  # Use original path, not template content
                schema_path=schema_file,
                variables=ctx.obj.get("vars", {}) if ctx.obj else {},
                security_mode=kwargs.get("path_security", "permissive"),
                model=params.get("model", "gpt-4o"),
                **plan_kwargs,
            )

            if kwargs.get("dry_run_json"):
                # Output JSON to stdout
                click.echo(json.dumps(plan, indent=2))
            else:
                # Output human-readable to stdout
                PlanPrinter.human(plan)

                # Add debug output for tool states if debug mode is enabled
                if kwargs.get("debug"):
                    click.echo("\n--- DEBUG TOOL STATES ---")
                    debug_enabled_tools = cast(
                        set[str], params.get("_enabled_tools", set())
                    )
                    debug_disabled_tools = cast(
                        set[str], params.get("_disabled_tools", set())
                    )

                    # Check web search state
                    web_search_enabled = "web-search" in debug_enabled_tools
                    if "web-search" in debug_disabled_tools:
                        web_search_enabled = False
                    click.echo(
                        f"web_search_enabled: bool ({web_search_enabled})"
                    )

                    # Check code interpreter state
                    ci_enabled = "code-interpreter" in debug_enabled_tools
                    if "code-interpreter" in debug_disabled_tools:
                        ci_enabled = False
                    # Also enable if CI attachments present
                    if plan.get("tools", {}).get("code_interpreter", False):
                        ci_enabled = True
                    click.echo(
                        f"code_interpreter_enabled: bool ({ci_enabled})"
                    )

                # Add completion message based on validation result
                if validation_passed:
                    click.echo("\nDry run completed successfully")
                else:
                    click.echo(
                        "\nDry run completed with warnings - see template status above"
                    )

            # Exit with appropriate code
            ctx.exit(0 if validation_passed else 1)

        # Run the async function synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            exit_code = loop.run_until_complete(run_cli_async(params))
            sys.exit(int(exit_code))
        except SchemaValidationError as e:
            # Log the error with full context
            logger.error("Schema validation error: %s", str(e))
            if e.context:
                logger.debug(
                    "Error context: %s", json.dumps(e.context, indent=2)
                )
            # Re-raise to preserve error chain and exit code
            raise
        except (CLIError, InvalidJSONError, SchemaFileError) as e:
            handle_error(e)
            sys.exit(
                e.exit_code
                if hasattr(e, "exit_code")
                else ExitCode.INTERNAL_ERROR
            )
        except click.UsageError as e:
            handle_error(e)
            sys.exit(ExitCode.USAGE_ERROR)
        except Exception as e:
            handle_error(e)
            sys.exit(ExitCode.INTERNAL_ERROR)
        finally:
            loop.close()
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        raise
