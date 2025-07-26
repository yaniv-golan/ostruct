"""File management commands for ostruct."""

import asyncio
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional

import click
import questionary
from openai import AsyncOpenAI
from pydantic import BaseModel
from tabulate import tabulate

from ..cache_utils import get_default_cache_path
from ..file_search import FileSearchManager
from ..upload_cache import UploadCache
from ..upload_manager import SharedUploadManager
from ..utils.attachment_utils import AttachmentProcessor
from ..utils.error_utils import ErrorCollector
from ..utils.json_models import ErrorResult
from ..utils.json_output import JSONOutputHandler
from ..utils.progress_utils import ProgressHandler

logger = logging.getLogger(__name__)


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_path_display(file_path: str) -> str:
    """Format file path for display, showing relative to CWD when possible."""
    if not file_path:
        return "N/A"

    try:
        path_obj = Path(file_path)
        cwd = Path.cwd()

        # If the path is absolute and within CWD, make it relative
        if path_obj.is_absolute():
            try:
                relative_path = path_obj.relative_to(cwd)
                return str(relative_path)
            except ValueError:
                # Path is not within CWD, keep absolute
                return file_path
        else:
            # Already relative, return as-is
            return file_path
    except Exception:
        # If any error occurs, return original path
        return file_path


def truncate_with_ellipsis(text: str, max_width: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_width:
        return text
    if max_width <= 3:
        return "..." if max_width == 3 else text[:max_width]
    return text[: max_width - 3] + "..."


def format_bindings(bindings: Dict[str, Any]) -> str:
    """Format bindings dictionary for display."""
    if not bindings:
        return "none"

    tools = []
    if bindings.get("user_data"):
        tools.append("user-data")
    if bindings.get("code_interpreter"):
        tools.append("code-interpreter")
    if bindings.get("file_search"):
        tools.append("file-search")

    return ", ".join(tools) if tools else "none"


class FileBindings(BaseModel):
    """File tool bindings."""

    user_data: bool = False
    code_interpreter: bool = False
    file_search: bool = False
    vector_store_ids: List[str] = []


class UploadResult(BaseModel):
    """Result of a file upload operation."""

    file_id: str
    path: str
    cached: bool
    bindings: FileBindings
    tags: Dict[str, str] = {}


def render_responsive_table(
    data: List[Any],
    table_type: str,
    text_formatter: Optional[Callable[[Any], str]] = None,
) -> None:
    """Render a responsive table based on terminal width."""
    if not data:
        click.echo("No data to display.")
        return

    # For files, always use tabular format for consistency with list-models
    # and to avoid printing raw CachedFileInfo objects in narrow terminals
    if table_type == "files":
        headers = ["File ID", "Size", "Uploaded", "Tools", "Tags", "Path"]
        rows = []
        for file_info in data:
            metadata = file_info.metadata or {}
            bindings = metadata.get("bindings", {})
            tags = metadata.get("tags", {})

            # Path as last column - no truncation needed since it's rightmost
            path_display = format_path_display(file_info.path)

            rows.append(
                [
                    (
                        file_info.file_id[:12] + "..."
                        if len(file_info.file_id) > 15
                        else file_info.file_id
                    ),
                    format_size(file_info.size),
                    datetime.fromtimestamp(file_info.created_at).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    format_bindings(bindings),
                    (
                        ", ".join(f"{k}={v}" for k, v in tags.items())
                        if tags
                        else ""
                    ),
                    path_display,
                ]
            )

        click.echo(tabulate(rows, headers=headers, tablefmt="simple"))
    else:
        # For other table types, keep the responsive behavior
        # Get terminal width
        try:
            terminal_width = shutil.get_terminal_size().columns
        except OSError:
            terminal_width = 80

        # For narrow terminals, use simple list format
        if terminal_width < 100:
            for item in data:
                if text_formatter:
                    click.echo(text_formatter(item))
                else:
                    click.echo(str(item))
        else:
            # Wide terminal - use tabular format (fallback for unknown table types)
            for item in data:
                if text_formatter:
                    click.echo(text_formatter(item))
                else:
                    click.echo(str(item))


@click.group()
def files() -> None:
    """Manage file uploads and cache."""
    pass


@files.command()
@click.option(
    "--file",
    "files",
    multiple=True,
    type=str,
    help="Upload individual files (repeatable)",
)
@click.option(
    "--dir",
    "directories",
    multiple=True,
    type=str,
    help="Upload directories recursively (repeatable)",
)
@click.option(
    "--collect",
    "collections",
    multiple=True,
    type=str,
    help="Upload files listed in text file (one path per line, repeatable)",
)
@click.option(
    "--pattern",
    type=str,
    help="Global file pattern filter (e.g., '*.pdf', '*.{png,jpg}')",
)
@click.option(
    "--tools",
    type=str,
    multiple=True,
    # NOTE: No default= here to avoid rich-click parsing bug where defaults
    # for multiple=True options get injected as bare strings during help generation,
    # causing Click to treat them as unexpected positional arguments.
    # See: https://github.com/ewels/rich-click/issues/145
    help="Tool bindings (repeatable: --tools user-data --tools file-search)",
)
@click.option(
    "--tag",
    multiple=True,
    metavar="KEY=VALUE",
    help="Free-form metadata stored in cache JSON column",
)
@click.option(
    "--vector-store",
    type=str,
    default="ostruct",
    help='Named vector store for file search (default: "ostruct")',
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview uploads without making API calls",
)
@click.option(
    "--progress",
    type=click.Choice(["none", "basic", "detailed"]),
    default="basic",
    show_default=True,
    help="Control progress display. 'none' disables progress indicators, 'basic' shows key steps, 'detailed' shows all operations.",
)
@click.option(
    "--json", "output_json", is_flag=True, help="Emit machine-readable JSON"
)
@click.pass_context
def upload(
    ctx: click.Context,
    files: tuple[str, ...],
    directories: tuple[str, ...],
    collections: tuple[str, ...],
    pattern: str | None,
    tools: tuple[str, ...],
    tag: tuple[str, ...],
    vector_store: str,
    dry_run: bool,
    progress: str,
    output_json: bool,
) -> None:
    """Upload files with batch support and interactive mode.

    Examples:
        # Single file (user-data enabled by default)
        ostruct files upload --file chart.png --tag project=alpha --tag doctype=spec

        # Batch files with file-search
        ostruct files upload --file doc1.pdf --file doc2.csv --tools file-search

        # Directory upload with pattern for code-interpreter
        ostruct files upload --dir ./docs --pattern '*.pdf' --tools code-interpreter

        # Collection with multiple tools
        ostruct files upload --collect @filelist.txt --tools file-search,code-interpreter

        # Interactive mode (no arguments)
        ostruct files upload
    """
    # Configure progress reporting
    handler = ProgressHandler(
        verbose=ctx.obj.get("verbose", False) if ctx.obj else False,
        progress=progress,
    )

    # Parse tools (now multiple=True, so tools is a tuple)
    # Support both --tools user-data --tools file-search and --tools user-data,file-search
    valid_tools = {"user-data", "file-search", "code-interpreter"}

    # ---------------------------------------------------------------------
    # Work-around for rich-click default-injection bug
    # ---------------------------------------------------------------------
    # Background
    # ==========
    # When an option is declared with ``multiple=True`` **and** has an *implicit*
    # default value, the rich-click help-generation shim walks over the Click
    # ``Option`` objects **before** the main parser runs. During this walk it
    # injects the default into Click’s internal default-map so that it can be
    # rendered in the beautiful help output. Unfortunately, Click reuses that
    # default-map on *subsequent* parse passes (one is triggered when the
    # command exits via ``ctx.exit()``). In our specific early-exit path
    # (``--dry-run --json``) this results in the bare string ``"user-data"``
    # being appended to ``ctx.args`` and we end up with the dreaded:
    #
    #     Error: Got unexpected extra argument (user-data)
    #
    # Upstream issue: https://github.com/ewels/rich-click/issues/145
    #
    # Work-around
    # ----------
    # 1. Declare the ``--tools`` option *without* a Click-level default.
    # 2. Apply our own fallback default *only* when generating **human** output.
    #    Machine consumers running with ``--json`` get an empty list so nothing
    #    leaks back into ``ctx.args`` on the secondary parse.
    #
    # Once rich-click >= 1.9.0 (or whichever version ships
    # ``USE_PARAMETER_DEFAULTS_HELP``) is adopted, this section can be removed
    # and the simpler code restored.

    # Build final tools list without mutating Click's parsed value. Mutating the
    # tuple would re-bind the Click option value and bring us back to the same
    # opt-parse corruption described above.

    tools_list: List[str] = []

    for tool_arg in tools:
        # Support both --tools user-data --tools file-search and
        # --tools user-data,file-search
        tools_list.extend(
            [t.strip() for t in tool_arg.split(",") if t.strip()]
        )

    # Apply implicit default only in human-readable mode for the reasons
    # detailed above. This keeps ``tools_list`` empty in JSON mode, preventing
    # rich-click from ever seeing a default value that it could inject.
    if not tools_list and not output_json:
        tools_list = ["user-data"]

    # Validate tools
    invalid_tools = [tool for tool in tools_list if tool not in valid_tools]
    if invalid_tools:
        error_msg = f"Invalid tools: {', '.join(invalid_tools)}. Valid choices: {', '.join(sorted(valid_tools))}"
        if output_json:
            joh = JSONOutputHandler(indent=2)
            error_result = ErrorResult(exit_code=1, error=error_msg)
            click.echo(
                joh.to_json(
                    joh.format_generic(error_result.model_dump(), "upload")
                )
            )
        else:
            click.echo(f"❌ Error: {error_msg}")
        sys.exit(1)

    effective_tools: tuple[str, ...] = tuple(tools_list)

    # If no attachment options provided, enter interactive mode
    if not (files or directories or collections) and not output_json:
        try:
            # Interactive file selection - avoid executable files to prevent
            # macOS Spotlight from triggering nested ostruct CLI invocations
            available_files = [
                p
                for p in Path.cwd().rglob("*")
                if p.is_file()
                and not p.is_symlink()
                and not (p.stat().st_mode & 0o111)  # skip executables
            ][
                :100
            ]  # Limit for UX and performance

            if not available_files:
                click.echo("No files found in current directory.")
                return

            # Display relative paths for better UX, but store absolute paths for processing
            cwd = Path.cwd()
            file_choices = []
            file_path_map = {}  # Map display path -> absolute path

            for f in available_files:
                try:
                    # Show relative path if within CWD, otherwise show absolute
                    if f.is_absolute():
                        try:
                            relative_path = f.relative_to(cwd)
                            display_path = str(relative_path)
                        except ValueError:
                            # Path is not within CWD, keep absolute
                            display_path = str(f)
                    else:
                        display_path = str(f)

                    file_choices.append(display_path)
                    file_path_map[display_path] = str(
                        f
                    )  # Store absolute path for processing
                except Exception:
                    # If any error occurs, use absolute path
                    display_path = str(f)
                    file_choices.append(display_path)
                    file_path_map[display_path] = str(f)
            selected_files = questionary.checkbox(
                "Select files to upload:", choices=file_choices
            ).ask()

            if not selected_files:
                click.echo("No files selected.")
                return

            # Convert display paths back to absolute paths for processing
            # Handle both mapped paths (from file discovery) and direct paths (from tests/mocks)
            files = tuple(
                file_path_map.get(display_path, display_path)
                for display_path in selected_files
            )

            # Interactive tool selection
            selected_tools = questionary.checkbox(
                "Select tools to bind:",
                choices=["user-data", "file-search", "code-interpreter"],
            ).ask()

            # Default to user-data if nothing selected
            if not selected_tools:
                selected_tools = ["user-data"]

            # Preserve original Click option but update effective_tools only.
            effective_tools = tuple(selected_tools)

        except KeyboardInterrupt:
            click.echo("\nOperation cancelled.")
            return

    elif not (files or directories or collections):
        # JSON mode with no args - error
        if output_json:
            error_result = ErrorResult(
                exit_code=1,
                error="No files specified. Use --file, --dir, or --collect options.",
            )
            joh = JSONOutputHandler(indent=2)
            click.echo(
                joh.to_json(
                    joh.format_generic(error_result.model_dump(), "upload")
                )
            )
        else:
            click.echo(
                "❌ Error: No files specified. Use --file, --dir, or --collect options."
            )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Dry-run + JSON early-exit contract
    # ------------------------------------------------------------------
    # For machine consumption (``--dry-run --json``) the CLI *must not* emit a
    # preview table — tests expect **no stdout** so that tooling can safely
    # parse an empty string and rely solely on the exit-code. We therefore
    # short-circuit before calling the preview helper.
    if dry_run:
        # Silent path for JSON mode
        # ------------------------
        # Returning here exits the callback with code 0. Click will tidy up
        # without triggering the second parse pass that used to cause the
        # "unexpected extra argument" failure.
        if output_json:
            return
        # Use synchronous dry-run path to avoid Click context issues
        _dry_run_sync(
            files,
            directories,
            collections,
            pattern,
            effective_tools,
            tag,
            vector_store,
            output_json,
            handler,
        )
        return
    else:
        # Use asynchronous real upload path
        asyncio.run(
            _batch_upload(
                files,
                directories,
                collections,
                pattern,
                effective_tools,
                tag,
                vector_store,
                dry_run,
                progress,
                output_json,
                handler,
            )
        )


def _dry_run_sync(
    files: tuple[str, ...],
    directories: tuple[str, ...],
    collections: tuple[str, ...],
    pattern: str | None,
    effective_tools: tuple[str, ...],
    tag: tuple[str, ...],
    vector_store: str,
    output_json: bool,
    handler: ProgressHandler,
) -> None:
    """Synchronous dry-run preview without async calls to avoid Click context issues.

    This function performs full validation and generates a preview, then exits with
    appropriate code using Click's context to avoid corrupting the parser state.
    """
    ctx = click.get_current_context()

    try:
        # Parse tags
        tags = {}
        for tag_str in tag:
            if "=" not in tag_str:
                error_msg = f"Tag must be in format KEY=VALUE: {tag_str}"
                if output_json:
                    joh = JSONOutputHandler(indent=2)
                    error_result = ErrorResult(exit_code=1, error=error_msg)
                    click.echo(
                        joh.to_json(
                            joh.format_generic(
                                error_result.model_dump(), "upload"
                            )
                        )
                    )
                else:
                    click.echo(f"❌ Error: {error_msg}")
                ctx.exit(1)
            key, value = tag_str.split("=", 1)
            tags[key] = value

        # Use AttachmentProcessor to collect and validate files (sync version)
        processor = AttachmentProcessor(
            support_aliases=False,
            progress_handler=handler,
            validate_files=True,
        )

        all_files = processor.collect_files_sync(
            files, directories, collections, pattern
        )

        if not all_files:
            error_msg = "No files found matching criteria."
            if output_json:
                joh = JSONOutputHandler(indent=2)
                error_result = ErrorResult(exit_code=1, error=error_msg)
                click.echo(
                    joh.to_json(
                        joh.format_generic(error_result.model_dump(), "upload")
                    )
                )
            else:
                click.echo(error_msg)
            ctx.exit(1)

        # Generate dry-run preview
        total_size = sum(f.stat().st_size for f in all_files)

        if output_json:
            # JSON output
            preview = {
                "files": [
                    {"path": str(f), "size": f.stat().st_size}
                    for f in all_files
                ],
                "total_files": len(all_files),
                "total_size": total_size,
                "tools": list(effective_tools),
                "vector_store": vector_store,
                "tags": tags,
            }
            joh = JSONOutputHandler(indent=2)
            click.echo(
                joh.to_json(joh.format_dry_run_response(preview, "upload"))
            )
        else:
            # Human-readable output
            click.echo("Dry run preview:")
            click.echo(f"  Files to upload: {len(all_files)}")
            click.echo(f"  Total size: {total_size:,} bytes")
            click.echo(f"  Tools: {', '.join(effective_tools)}")
            click.echo(f"  Vector store: {vector_store}")
            if tags:
                click.echo(
                    f"  Tags: {', '.join(f'{k}={v}' for k, v in tags.items())}"
                )

        return

    except Exception as e:
        # Handle file validation errors
        if hasattr(e, "exit_code"):
            if output_json:
                joh = JSONOutputHandler(indent=2)
                error_result = ErrorResult(exit_code=e.exit_code, error=str(e))
                click.echo(
                    joh.to_json(
                        joh.format_generic(error_result.model_dump(), "upload")
                    )
                )
            else:
                click.echo(f"❌ Error: {str(e)}")
            ctx.exit(e.exit_code)
        else:
            # Re-raise unexpected errors
            raise


async def _batch_upload(
    files: tuple[str, ...],
    directories: tuple[str, ...],
    collections: tuple[str, ...],
    pattern: str | None,
    effective_tools: tuple[str, ...],
    tag: tuple[str, ...],
    vector_store: str,
    dry_run: bool,
    progress: str,
    output_json: bool,
    handler: ProgressHandler,
) -> None:
    """Perform the actual batch upload operation."""
    try:
        # Create OpenAI client
        from ..utils.client_utils import create_openai_client

        client = create_openai_client(timeout=60.0)
        cache = UploadCache(get_default_cache_path())
        upload_manager = SharedUploadManager(client, cache=cache)

        # Parse tags
        tags = {}
        for tag_str in tag:
            if "=" not in tag_str:
                raise click.BadParameter(
                    f"Tag must be in format KEY=VALUE: {tag_str}"
                )
            key, value = tag_str.split("=", 1)
            tags[key] = value

        # Use AttachmentProcessor to collect files
        processor = AttachmentProcessor(
            support_aliases=False,
            progress_handler=handler,
            validate_files=True,  # Always validate, even in dry-run mode
        )

        try:
            all_files = await processor.collect_files(
                files, directories, collections, pattern
            )
        except Exception as e:
            # Handle file validation errors
            if hasattr(e, "exit_code"):
                # This is one of our file validation errors
                if output_json:
                    joh = JSONOutputHandler(indent=2)
                    error_result = ErrorResult(
                        exit_code=e.exit_code, error=str(e)
                    )
                    click.echo(
                        joh.to_json(
                            joh.format_generic(
                                error_result.model_dump(), "upload"
                            )
                        )
                    )
                else:
                    click.echo(f"❌ Error: {str(e)}")
                sys.exit(e.exit_code)
            else:
                # Re-raise unexpected errors
                raise

        # Initialize error collector for standardized error handling
        error_collector = ErrorCollector()

        if not all_files:
            if output_json:
                joh = JSONOutputHandler(indent=2)
                empty_result = joh.format_results(
                    success_items=[],
                    cached_items=[],
                    errors=[],
                    summary={"total": 0},
                    operation="upload",
                )
                click.echo(joh.to_json(empty_result))
            else:
                click.echo("No files found matching criteria.")
            return

        # Dry run preview
        if dry_run:
            total_size = sum(f.stat().st_size for f in all_files)
            if output_json:
                preview = {
                    "files": [
                        {"path": str(f), "size": f.stat().st_size}
                        for f in all_files
                    ],
                    "total_files": len(all_files),
                    "total_size": total_size,
                    "tools": list(effective_tools),
                    "vector_store": vector_store,
                    "tags": tags,
                }
                joh = JSONOutputHandler(indent=2)
                click.echo(
                    joh.to_json(joh.format_dry_run_response(preview, "upload"))
                )
            else:
                click.echo("Dry run preview:")
                click.echo(f"  Files to upload: {len(all_files)}")
                click.echo(f"  Total size: {total_size:,} bytes")
                click.echo(f"  Tools: {', '.join(effective_tools)}")
                click.echo(f"  Vector store: {vector_store}")
                if tags:
                    click.echo(
                        f"  Tags: {', '.join(f'{k}={v}' for k, v in tags.items())}"
                    )
            return

        # Process files with progress tracking
        results: List[UploadResult] = []

        # Disable progress bars in JSON mode to avoid corrupting output
        show_progress = progress != "none" and not output_json

        # Use progress handler for batch processing
        if show_progress:
            with handler.batch_phase(
                "Uploading files", "📤", len(all_files)
            ) as phase:
                for file_path in all_files:
                    try:
                        result = await _upload_single_file(
                            file_path,
                            effective_tools,
                            tags,
                            vector_store,
                            client,
                            cache,
                            upload_manager,
                        )
                        results.append(result)

                        # Update progress
                        filename = Path(file_path).name
                        msg = (
                            f"Uploaded {filename}"
                            if progress == "detailed"
                            else None
                        )
                        phase.advance(advance=1, msg=msg)

                    except Exception as e:
                        # Use error collector for standardized formatting
                        error_collector.add_error(str(file_path), e)
                        error_msg = error_collector.format_error(
                            str(file_path), e
                        )
                        logger.error(error_msg)

                        # Update progress even on error
                        filename = Path(file_path).name
                        msg = (
                            f"Error with {filename}"
                            if progress == "detailed"
                            else None
                        )
                        phase.advance(advance=1, msg=msg)
        else:
            # No progress tracking - process files without progress bars
            for file_path in all_files:
                try:
                    result = await _upload_single_file(
                        file_path,
                        effective_tools,
                        tags,
                        vector_store,
                        client,
                        cache,
                        upload_manager,
                    )
                    results.append(result)

                except Exception as e:
                    # Use error collector for standardized formatting
                    error_collector.add_error(str(file_path), e)
                    error_msg = error_collector.format_error(str(file_path), e)
                    logger.error(error_msg)

        # Output results
        formatted_errors = error_collector.get_formatted_errors()

        if output_json:
            joh = JSONOutputHandler(indent=2)

            uploaded_count = len([r for r in results if not r.cached])
            cached_count = len([r for r in results if r.cached])

            summary = joh.format_summary(
                total=len(all_files),
                uploaded=uploaded_count,
                cached=cached_count,
                errors=error_collector.get_error_count(),
            )

            json_result = joh.format_results(
                success_items=[
                    r.model_dump() for r in results if not r.cached
                ],
                cached_items=[r.model_dump() for r in results if r.cached],
                errors=formatted_errors,
                summary=summary,
            )

            click.echo(joh.to_json(json_result))
        else:
            # Human-readable output
            for result in results:
                status = "✅ Cached" if result.cached else "✅ Uploaded"
                filename = Path(result.path).name

                tool_names = []
                if result.bindings.user_data:
                    tool_names.append("user_data")
                if result.bindings.code_interpreter:
                    tool_names.append("code_interpreter")
                if result.bindings.file_search:
                    tool_names.append("file_search")

                tools_str = ", ".join(tool_names) if tool_names else "none"
                click.echo(f"{status} {filename} → {result.file_id}")
                click.echo(f"   Tools: {tools_str}")

            if error_collector.has_errors():
                click.echo(f"\n❌ {error_collector.get_error_count()} errors:")
                for error in formatted_errors:
                    click.echo(f"   {error}")

            # Summary
            uploaded_count = len([r for r in results if not r.cached])
            cached_count = len([r for r in results if r.cached])
            click.echo(
                f"\n📊 Summary: {uploaded_count} uploaded, {cached_count} cached, {error_collector.get_error_count()} errors"
            )

    except Exception as e:
        if output_json:
            joh = JSONOutputHandler(indent=2)
            error_result = ErrorResult(exit_code=1, error=str(e))
            click.echo(
                joh.to_json(
                    joh.format_generic(error_result.model_dump(), "upload")
                )
            )
        else:
            click.echo(f"❌ Error: {str(e)}")
        sys.exit(1)


async def _upload_single_file(
    file_path: Path,
    tools: tuple[str, ...],
    tags: dict[str, str],
    vector_store: str,
    client: AsyncOpenAI,
    cache: UploadCache,
    upload_manager: SharedUploadManager,
) -> UploadResult:
    """Upload a single file and return result."""
    # Check cache
    file_hash = cache.compute_file_hash(file_path)
    cached_file_id = cache.lookup_with_validation(file_path, file_hash)

    if cached_file_id:
        file_id = cached_file_id
        logger.info(f"Cache hit: {file_path} → {file_id}")
        cached = True
    else:
        # Upload with correct purpose mapping
        if "file-search" in tools or "code-interpreter" in tools:
            purpose: Literal["assistants", "user_data"] = "assistants"
        else:
            purpose = "user_data"

        file_id = await upload_manager._perform_upload(
            file_path, purpose=purpose
        )

        # Store in cache
        file_stat = file_path.stat()
        cache.store(
            file_hash,
            file_id,
            int(file_stat.st_size),
            int(file_stat.st_mtime),
            {"purpose": purpose},
            file_path=str(file_path),
        )

        logger.info(f"Uploaded: {file_path} → {file_id}")
        cached = False

    # Update metadata with tags and bindings
    metadata: Dict[str, Any] = {
        "tags": tags,
        "bindings": {
            "user_data": "user-data" in tools,
            "code_interpreter": "code-interpreter" in tools,
            "file_search": False,
            "vector_store_ids": [],
        },
        "files_cmd_version": "1.0",
    }

    # Handle file-search binding
    if "file-search" in tools:
        fs_manager = FileSearchManager(client)

        vector_store_name = f"ostruct_{vector_store}"
        existing_vs_id = cache.get_vector_store_by_name(vector_store_name)

        if existing_vs_id:
            vector_store_id = existing_vs_id
        else:
            vector_store_id = await fs_manager.create_vector_store_with_retry(
                name=vector_store_name
            )
            cache.register_vector_store(vector_store_id, vector_store_name)

        await fs_manager._add_files_to_vector_store_with_retry(
            vector_store_id, [file_id], max_retries=3, retry_delay=1.0
        )
        cache.add_file_to_vector_store(file_hash, vector_store_id)

        metadata["bindings"]["file_search"] = True
        metadata["bindings"]["vector_store_ids"] = [vector_store_id]

    # Update cache with metadata
    cache.update_metadata(file_id, metadata)

    # Build result
    bindings = FileBindings(
        user_data=metadata["bindings"]["user_data"],
        code_interpreter=metadata["bindings"]["code_interpreter"],
        file_search=metadata["bindings"]["file_search"],
        vector_store_ids=metadata["bindings"]["vector_store_ids"],
    )

    return UploadResult(
        file_id=file_id,
        path=str(file_path),
        cached=cached,
        bindings=bindings,
        tags=tags,
    )


@files.command()
@click.option(
    "--json", "output_json", is_flag=True, help="Output machine-readable JSON"
)
@click.option(
    "--vector-store", type=str, help="Filter by specific vector store name"
)
def list(output_json: bool, vector_store: Optional[str]) -> None:
    """Show cache inventory.

    Examples:
        ostruct files list
        ostruct files list --json
        ostruct files list --vector-store project_docs
    """
    try:
        cache = UploadCache(get_default_cache_path())
        files = cache.list_all()

        # Filter by vector store if specified
        if vector_store:
            # Get vector store ID by name
            vector_store_name = f"ostruct_{vector_store}"
            vector_store_id = cache.get_vector_store_by_name(vector_store_name)

            if vector_store_id:
                # Get file hashes in this vector store
                file_hashes_in_vs = set(
                    cache.get_files_in_vector_store(vector_store_id)
                )

                # Filter files to only those in the vector store
                filtered_files = []
                for file_info in files:
                    if file_info.hash in file_hashes_in_vs:
                        filtered_files.append(file_info)
                files = filtered_files
            else:
                # Vector store not found, return empty list
                files = []

        if output_json:
            result = []
            for file_info in files:
                metadata = file_info.metadata or {}
                result.append(
                    {
                        "file_id": file_info.file_id,
                        "hash": file_info.hash,
                        "size": file_info.size,
                        "path": file_info.path,
                        "uploaded": datetime.fromtimestamp(
                            file_info.created_at
                        ).isoformat(),
                        "bindings": metadata.get("bindings", {}),
                        "tags": metadata.get("tags", {}),
                    }
                )
            joh = JSONOutputHandler(indent=2)
            click.echo(
                joh.to_json(
                    joh.format_generic(result, "list", total_files=len(result))
                )
            )
        else:
            render_responsive_table(files, "files")

    except Exception as e:
        error_result = ErrorResult(exit_code=1, error=str(e))

        def format_error(r: BaseModel) -> str:
            if isinstance(r, ErrorResult):
                return f"Error: {r.error}"
            return str(r)

        if output_json:
            joh = JSONOutputHandler(indent=2)
            click.echo(
                joh.to_json(
                    joh.format_generic(error_result.model_dump(), "list")
                )
            )
        else:
            click.echo(format_error(error_result))
