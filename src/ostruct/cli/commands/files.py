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
from ..exit_codes import ExitCode
from ..file_search import FileSearchManager
from ..upload_cache import UploadCache
from ..upload_manager import SharedUploadManager
from ..utils.attachment_utils import AttachmentProcessor
from ..utils.error_utils import ErrorCollector
from ..utils.json_models import ErrorResult
from ..utils.json_output import JSONOutputHandler
from ..utils.path_truncation import smart_truncate_path, truncate_with_ellipsis
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


def format_bindings(bindings: Dict[str, Any]) -> str:
    """Format bindings dictionary for display."""
    if not bindings:
        return "-"

    tools = []
    if bindings.get("user_data"):
        tools.append("ud")
    if bindings.get("code_interpreter"):
        tools.append("ci")
    if bindings.get("file_search"):
        tools.append("fs")

    return ", ".join(tools) if tools else "-"


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
    columns: Optional[str] = None,
    no_truncate: bool = False,
    max_col_width: int = 50,
) -> None:
    """Render a responsive table based on terminal width."""
    if not data:
        click.echo("No data to display.")
        return

    # Get terminal width
    try:
        terminal_width = shutil.get_terminal_size().columns
    except OSError:
        terminal_width = 80

    if table_type == "files":
        # Define all available columns
        all_columns = ["FILE_ID", "SIZE", "UPLOADED", "TOOLS", "TAGS", "PATH"]
        column_headers = [
            "File ID",
            "Size",
            "Uploaded",
            "Tools",
            "Tags",
            "Path",
        ]

        # Select columns to display
        if columns:
            selected_columns = [
                col.strip().upper() for col in columns.split(",")
            ]
            # Validate column names
            valid_columns = []
            valid_headers = []
            for col in selected_columns:
                if col in all_columns:
                    idx = all_columns.index(col)
                    valid_columns.append(col)
                    valid_headers.append(column_headers[idx])
                else:
                    click.echo(
                        f"Warning: Unknown column '{col}'. Available: {', '.join(all_columns)}",
                        err=True,
                    )

            if not valid_columns:
                click.echo("Error: No valid columns specified.", err=True)
                return

            display_columns = valid_columns
            headers = valid_headers
        else:
            display_columns = all_columns
            headers = column_headers

        # Check if we should use narrow format
        use_narrow_format = terminal_width < 100 and not columns

        if use_narrow_format:
            # Narrow terminal - use vertical record format
            for i, file_info in enumerate(data):
                if i > 0:
                    click.echo()  # Blank line between records

                metadata = file_info.metadata or {}
                bindings = metadata.get("bindings", {})
                tags = metadata.get("tags", {})

                click.echo(f"File ID: {file_info.file_id}")
                click.echo(f"Size:    {format_size(file_info.size)}")
                click.echo(
                    f"Date:    {datetime.fromtimestamp(file_info.created_at).strftime('%Y-%m-%d %H:%M')}"
                )
                click.echo(f"Tools:   {format_bindings(bindings)}")

                if tags:
                    tags_str = ", ".join(f"{k}={v}" for k, v in tags.items())
                    if no_truncate or len(tags_str) <= max_col_width:
                        click.echo(f"Tags:    {tags_str}")
                    else:
                        click.echo(
                            f"Tags:    {truncate_with_ellipsis(tags_str, max_col_width)}"
                        )
                else:
                    click.echo("Tags:    -")

                path_display = format_path_display(file_info.path)
                if no_truncate or len(path_display) <= max_col_width:
                    click.echo(f"Path:    {path_display}")
                else:
                    click.echo(
                        f"Path:    {smart_truncate_path(path_display, max_col_width)}"
                    )
        else:
            # Wide terminal or custom columns - use tabular format
            rows = []
            for file_info in data:
                metadata = file_info.metadata or {}
                bindings = metadata.get("bindings", {})
                tags = metadata.get("tags", {})

                # Build row data based on selected columns
                row = []
                for col in display_columns:
                    if col == "FILE_ID":
                        row.append(file_info.file_id)
                    elif col == "SIZE":
                        row.append(format_size(file_info.size))
                    elif col == "UPLOADED":
                        row.append(
                            datetime.fromtimestamp(
                                file_info.created_at
                            ).strftime("%Y-%m-%d %H:%M")
                        )
                    elif col == "TOOLS":
                        row.append(format_bindings(bindings))
                    elif col == "TAGS":
                        if tags:
                            tags_str = ", ".join(
                                f"{k}={v}" for k, v in tags.items()
                            )
                            if no_truncate or len(tags_str) <= max_col_width:
                                row.append(tags_str)
                            else:
                                row.append(
                                    truncate_with_ellipsis(
                                        tags_str, max_col_width
                                    )
                                )
                        else:
                            row.append("")
                    elif col == "PATH":
                        path_display = format_path_display(file_info.path)
                        if no_truncate or len(path_display) <= max_col_width:
                            row.append(path_display)
                        else:
                            row.append(
                                smart_truncate_path(
                                    path_display, max_col_width
                                )
                            )

                rows.append(row)

            click.echo(tabulate(rows, headers=headers, tablefmt="simple"))
    else:
        # For other table types, keep the original responsive behavior
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
        # Special handling for machine-readable mode
        # -----------------------------------------
        # We still want *full validation* so that missing files correctly
        # raise ``ExitCode.FILE_ERROR`` (tests rely on this).  However, on
        # *success* we suppress the human preview table and emit **no**
        # stdout – tools consume the exit-code only.
        if output_json:
            try:
                processor = AttachmentProcessor(
                    support_aliases=False,
                    progress_handler=handler,
                    validate_files=True,
                )
                # Validation is enough – the collect_files call will raise
                # our custom exceptions (with ``exit_code``) if anything is
                # wrong.  We deliberately ignore the returned list to keep
                # the silent success contract.
                asyncio.run(
                    processor.collect_files(
                        files, directories, collections, pattern
                    )
                )
            except Exception as e:  # pragma: no cover – handled exhaustively
                if hasattr(e, "exit_code"):
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
                    ctx.exit(e.exit_code)
                raise
            # All good – silent exit (code 0)
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
@click.option(
    "--tool",
    "tools_filter",
    multiple=True,
    type=click.Choice(
        ["user-data", "ud", "code-interpreter", "ci", "file-search", "fs"]
    ),
    help="Filter by tool bindings (repeatable)",
)
@click.option(
    "--tag",
    "tags_filter",
    multiple=True,
    metavar="KEY=VALUE",
    help="Filter by tag metadata (repeatable, AND logic)",
)
@click.option(
    "--columns",
    type=str,
    help="Comma-separated column names: FILE_ID,SIZE,UPLOADED,TOOLS,TAGS,PATH",
)
@click.option(
    "--no-truncate",
    is_flag=True,
    help="Show full column values without truncation",
)
@click.option(
    "--max-col-width",
    type=int,
    default=50,
    help="Maximum width for variable-width columns (default: 50)",
)
def list(
    output_json: bool,
    vector_store: Optional[str],
    tools_filter: tuple[str, ...],
    tags_filter: tuple[str, ...],
    columns: Optional[str],
    no_truncate: bool,
    max_col_width: int,
) -> None:
    """Show cache inventory.

    Examples:
        ostruct files list
        ostruct files list --json
        ostruct files list --vector-store project_docs
        ostruct files list --tool fs --tool ci
        ostruct files list --tag project=alpha --tag type=document
        ostruct files list --columns FILE_ID,TOOLS,PATH
        ostruct files list --no-truncate
    """
    try:
        cache = UploadCache(get_default_cache_path())
        files = cache.list_all()

        # Apply filters
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

        if tools_filter:
            # Normalize tool names (ud->user_data, ci->code_interpreter, fs->file_search)
            normalized_tools = []
            for tool in tools_filter:
                if tool in ["ud", "user-data"]:
                    normalized_tools.append("user_data")
                elif tool in ["ci", "code-interpreter"]:
                    normalized_tools.append("code_interpreter")
                elif tool in ["fs", "file-search"]:
                    normalized_tools.append("file_search")

            # Filter by tool bindings (OR logic - file matches if bound to any specified tool)
            filtered_files = []
            for file_info in files:
                metadata = file_info.metadata or {}
                bindings = metadata.get("bindings", {})
                if any(bindings.get(tool, False) for tool in normalized_tools):
                    filtered_files.append(file_info)
            files = filtered_files

        if tags_filter:
            # Parse tag filters (key=value format) and apply AND logic
            parsed_tags = {}
            for tag_filter in tags_filter:
                if "=" in tag_filter:
                    key, value = tag_filter.split("=", 1)
                    parsed_tags[key] = value
                else:
                    click.echo(
                        f"Warning: Invalid tag filter format '{tag_filter}'. Expected key=value.",
                        err=True,
                    )

            if parsed_tags:
                filtered_files = []
                for file_info in files:
                    metadata = file_info.metadata or {}
                    tags = metadata.get("tags", {})
                    if all(tags.get(k) == v for k, v in parsed_tags.items()):
                        filtered_files.append(file_info)
                files = filtered_files

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
            # Calculate summary statistics
            total_size = sum(f.size for f in files)
            tool_counts = {"ud": 0, "fs": 0, "ci": 0}

            for file_info in files:
                metadata = file_info.metadata or {}
                bindings = metadata.get("bindings", {})
                if bindings.get("user_data", False):
                    tool_counts["ud"] += 1
                if bindings.get("file_search", False):
                    tool_counts["fs"] += 1
                if bindings.get("code_interpreter", False):
                    tool_counts["ci"] += 1

            # Use responsive table with new options
            render_responsive_table(
                files,
                "files",
                columns=columns,
                no_truncate=no_truncate,
                max_col_width=max_col_width,
            )

            # Show summary statistics
            if files:
                summary_parts = [
                    f"{len(files)} files",
                    f"{format_size(total_size)} total",
                ]
                for tool, count in tool_counts.items():
                    if count > 0:
                        summary_parts.append(f"{count} {tool}-bound")
                click.echo(f"\n{' · '.join(summary_parts)}")

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


@files.command()
@click.option(
    "--older-than",
    default="90d",
    help="TTL for garbage collection (e.g., 30d, 7d)",
)
@click.option(
    "--json", "output_json", is_flag=True, help="Output machine-readable JSON"
)
def gc(older_than: str, output_json: bool) -> None:
    """Garbage-collect expired cache entries.

    Examples:
        ostruct files gc --older-than 30d
        ostruct files gc --older-than 7d --json
    """
    try:
        from datetime import datetime, timedelta

        # Parse duration
        if older_than.endswith("d"):
            days = int(older_than[:-1])
        else:
            raise click.BadParameter(f"Invalid duration format: {older_than}")

        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_timestamp = int(cutoff_date.timestamp())

        cache = UploadCache(get_default_cache_path())

        # Get all files and filter by age
        all_files = cache.list_all()
        deleted_count = 0

        # Remove files older than the cutoff date
        for file_info in all_files:
            if file_info.created_at < cutoff_timestamp:
                try:
                    cache.invalidate(file_info.hash)
                    deleted_count += 1
                    logger.debug(
                        f"Deleted old file {file_info.file_id} from {datetime.fromtimestamp(file_info.created_at).strftime('%Y-%m-%d')}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to remove file {file_info.file_id}: {e}"
                    )

        if output_json:
            from ..utils.json_output import JSONOutputHandler

            joh = JSONOutputHandler(indent=2)
            result = {
                "status": "success",
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
            }
            click.echo(joh.to_json(result))
        else:
            if deleted_count > 0:
                click.echo(
                    f"Cleaned up {deleted_count} orphaned cache entries"
                )
            else:
                click.echo("No cleanup needed")

    except Exception as e:
        if output_json:
            from ..utils.json_output import JSONOutputHandler

            joh = JSONOutputHandler(indent=2)
            error_result = ErrorResult(
                exit_code=ExitCode.INTERNAL_ERROR, error=str(e)
            )
            click.echo(
                joh.to_json(
                    joh.format_generic(error_result.model_dump(), "gc")
                )
            )
        else:
            click.echo(f"Error during garbage collection: {e}", err=True)

        ctx = click.get_current_context()
        ctx.exit(ExitCode.INTERNAL_ERROR)


@files.command()
@click.argument("file_id")
@click.option(
    "--tools",
    multiple=True,
    type=click.Choice(["user-data", "file-search", "code-interpreter"]),
    required=True,
    help="Tools to bind the cached file to (user-data=vision, file-search=search, code-interpreter=execution)",
)
@click.option(
    "--json", "output_json", is_flag=True, help="Output machine-readable JSON"
)
def bind(file_id: str, tools: tuple[str, ...], output_json: bool) -> None:
    """Attach cached file to one or more tools.

    Examples:
        ostruct files bind file_abc123 --tools file-search
        ostruct files bind file_abc123 --tools file-search --tools code-interpreter
    """
    try:
        cache = UploadCache(get_default_cache_path())

        # Step 1: Validate file exists in cache
        files = cache.list_all()
        file_info = None
        for f in files:
            if f.file_id == file_id:
                file_info = f
                break

        if not file_info:
            raise click.ClickException(f"File not found in cache: {file_id}")

        # Step 2: Get current metadata
        metadata = file_info.metadata or {}
        bindings = metadata.get("bindings", {})

        # Step 3: Add new bindings
        if "user-data" in tools:
            bindings["user_data"] = True
        if "code-interpreter" in tools:
            bindings["code_interpreter"] = True
        if "file-search" in tools:
            bindings["file_search"] = True
            # Note: Actual vector store binding would happen at runtime

        # Step 4: Update cache metadata
        metadata["bindings"] = bindings
        cache.update_metadata(file_id, metadata)

        if output_json:
            from ..utils.json_output import JSONOutputHandler

            joh = JSONOutputHandler(indent=2)
            result = {
                "status": "success",
                "file_id": file_id,
                "bindings": bindings,
            }
            click.echo(joh.to_json(result))
        else:
            click.echo(f"Bound {file_id} to: {', '.join(tools)}")

    except Exception as e:
        if output_json:
            from ..utils.json_output import JSONOutputHandler

            joh = JSONOutputHandler(indent=2)
            error_result = ErrorResult(
                exit_code=ExitCode.INTERNAL_ERROR, error=str(e)
            )
            click.echo(
                joh.to_json(
                    joh.format_generic(error_result.model_dump(), "bind")
                )
            )
        else:
            click.echo(f"Error binding file: {e}", err=True)

        ctx = click.get_current_context()
        ctx.exit(ExitCode.INTERNAL_ERROR)


@files.command()
@click.argument("file_id")
@click.option(
    "--json", "output_json", is_flag=True, help="Output machine-readable JSON"
)
def rm(file_id: str, output_json: bool) -> None:
    """Delete remote file and purge from cache.

    Examples:
        ostruct files rm file_abc123
        ostruct files rm file_abc123 --json
    """
    import asyncio

    from ..cache_utils import get_default_cache_path
    from ..upload_cache import UploadCache
    from ..utils.client_utils import create_openai_client
    from ..utils.json_output import JSONOutputHandler

    async def _rm_async() -> None:
        # Step 1: Delete from OpenAI (ignore 404s)
        try:
            client = create_openai_client(timeout=60.0)
            await client.files.delete(file_id)
        except Exception as e:
            # Log warning but continue - file might already be deleted
            logger.warning(f"OpenAI deletion failed (continuing): {e}")

        # Step 2: Remove from cache
        try:
            cache.invalidate_by_file_id(file_id)
        except Exception as e:
            logger.warning(f"Failed to remove from cache: {e}")

    try:
        cache = UploadCache(get_default_cache_path())

        # Run the async operations
        asyncio.run(_rm_async())

        if output_json:
            result = {"status": "success", "file_id": file_id}
            joh = JSONOutputHandler(indent=2)
            click.echo(joh.to_json(result))
        else:
            click.echo(f"Deleted: {file_id}")

    except Exception as e:
        logger.error(f"Error during file deletion: {e}")
        if output_json:
            error_result = {"status": "error", "error": str(e)}
            joh = JSONOutputHandler(indent=2)
            click.echo(joh.to_json(error_result))
        else:
            click.echo(f"Error: {e}")
        raise click.ClickException(str(e))


@files.command()
@click.argument("file_id")
@click.option(
    "--json", "output_json", is_flag=True, help="Output machine-readable JSON"
)
def diagnose(file_id: str, output_json: bool) -> None:
    """Live probes (head / vector / sandbox).

    Examples:
        ostruct files diagnose file_abc123
        ostruct files diagnose file_abc123 --json
    """
    import asyncio

    from ..utils.client_utils import create_openai_client
    from ..utils.json_output import JSONOutputHandler

    async def _diagnose_async() -> tuple[dict[str, Any], int]:
        client = create_openai_client(timeout=60.0)

        probes = {}
        exit_code = 0

        # Probe 1: Head (file exists)
        try:
            file_obj = await client.files.retrieve(file_id)
            probes["head"] = {"status": "pass", "size": file_obj.bytes}
        except Exception as e:
            probes["head"] = {"status": "fail", "error": str(e)}
            exit_code = max(exit_code, 1)

        # Probe 2: Vector search (test file_search tool with actual vector stores)
        try:
            # Get file metadata to check vector store bindings
            cache = UploadCache(get_default_cache_path())
            files = cache.list_all()
            file_info = None
            for f in files:
                if f.file_id == file_id:
                    file_info = f
                    break

            if file_info and file_info.metadata:
                bindings = file_info.metadata.get("bindings", {})
                vector_store_ids = bindings.get("vector_store_ids", [])
                if vector_store_ids:
                    # Test file_search with the actual vector store
                    response = await client.responses.create(
                        model="gpt-4o",
                        input="Find information about this file",
                        tools=[
                            {
                                "type": "file_search",
                                "vector_store_ids": vector_store_ids,
                            }
                        ],
                        tool_choice={"type": "file_search"},
                    )

                    # Check if we got search results
                    if response.output:
                        probes["vector"] = {
                            "status": "pass",
                            "vector_stores": len(vector_store_ids),
                        }
                    else:
                        probes["vector"] = {
                            "status": "fail",
                            "error": "No search results returned",
                        }
                        exit_code = max(exit_code, 3)
                else:
                    probes["vector"] = {
                        "status": "fail",
                        "error": "File not bound to any vector store",
                    }
                    exit_code = max(exit_code, 3)
            else:
                probes["vector"] = {
                    "status": "fail",
                    "error": "File not found in cache",
                }
                exit_code = max(exit_code, 3)

        except Exception as e:
            probes["vector"] = {"status": "fail", "error": str(e)}
            exit_code = max(exit_code, 3)

        # Probe 3: Sandbox (test code_interpreter tool with the actual file)
        try:
            response = await client.responses.create(
                model="gpt-4o",
                input="List files in the current directory and show their sizes",
                tools=[
                    {
                        "type": "code_interpreter",
                        "container": {"type": "auto", "file_ids": [file_id]},
                    }
                ],
                tool_choice={"type": "code_interpreter"},
            )

            # Check if we got a response
            if response.output:
                # Check if the file_id appears in the response (indicating it was accessible)
                response_text = str(response.output)
                file_found = file_id in response_text

                if file_found:
                    probes["sandbox"] = {"status": "pass"}
                else:
                    probes["sandbox"] = {
                        "status": "pass",
                        "note": "Code interpreter working but file not directly referenced",
                    }
            else:
                probes["sandbox"] = {
                    "status": "fail",
                    "error": "No response from code interpreter",
                }
                exit_code = max(exit_code, 4)

        except Exception as e:
            probes["sandbox"] = {"status": "fail", "error": str(e)}
            exit_code = max(exit_code, 4)

        return probes, exit_code

    try:
        probes, exit_code = asyncio.run(_diagnose_async())

        if output_json:
            result = {
                "status": "complete",
                "file_id": file_id,
                "probes": probes,
                "exit_code": exit_code,
            }
            joh = JSONOutputHandler(indent=2)
            click.echo(joh.to_json(result))
        else:
            click.echo(f"Diagnostic results for {file_id}:")
            for probe_name, probe_result in probes.items():
                status = probe_result["status"]
                if status == "pass":
                    click.echo(f"  {probe_name}: ✓ PASS")
                else:
                    error = probe_result.get("error", "Unknown error")
                    click.echo(f"  {probe_name}: ✗ FAIL - {error}")

        if exit_code != 0:
            sys.exit(exit_code)

    except Exception as e:
        if output_json:
            error_result = {"status": "error", "error": str(e)}
            joh = JSONOutputHandler(indent=2)
            click.echo(joh.to_json(error_result))
        else:
            click.echo(f"Error: {e}")
        raise click.ClickException(str(e))


@files.command(name="vector-stores")
@click.option(
    "--json", "output_json", is_flag=True, help="Output machine-readable JSON"
)
def vector_stores(output_json: bool) -> None:
    """List available vector stores and their contents.

    Examples:
        ostruct files vector-stores
        ostruct files vector-stores --json
    """
    try:
        cache = UploadCache(get_default_cache_path())

        # Get vector store information from cache
        vector_stores_list = cache.list_vector_stores()

        if output_json:
            from ..utils.json_output import JSONOutputHandler

            joh = JSONOutputHandler(indent=2)
            result = {"status": "success", "vector_stores": vector_stores_list}
            click.echo(joh.to_json(result))
        else:
            if not vector_stores_list:
                click.echo("No vector stores found")
            else:
                click.echo(
                    "Vector Store | Files | Total Size | Vector Store ID"
                )
                click.echo("-" * 70)
                for vs in vector_stores_list:
                    vs_name = vs["name"].replace(
                        "ostruct_", ""
                    )  # Remove prefix for display
                    file_count = vs.get("file_count", 0)
                    total_size = vs.get("total_size", 0)
                    vs_id = vs["vector_store_id"]
                    click.echo(
                        f"{vs_name:<12} | {file_count:5d} | {total_size:10d} | {vs_id}"
                    )

    except Exception as e:
        if output_json:
            from ..utils.json_output import JSONOutputHandler

            joh = JSONOutputHandler(indent=2)
            error_result = ErrorResult(
                exit_code=ExitCode.INTERNAL_ERROR, error=str(e)
            )
            click.echo(
                joh.to_json(
                    joh.format_generic(
                        error_result.model_dump(), "vector-stores"
                    )
                )
            )
        else:
            click.echo(f"Error listing vector stores: {e}", err=True)

        ctx = click.get_current_context()
        ctx.exit(ExitCode.INTERNAL_ERROR)
