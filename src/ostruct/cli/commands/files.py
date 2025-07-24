"""File management commands for ostruct."""

import asyncio
import fnmatch
import json
import logging
import os
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
from ..progress_reporting import (
    configure_progress_reporter,
    get_progress_reporter,
)
from ..upload_cache import UploadCache
from ..upload_manager import SharedUploadManager

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


class ErrorResult(BaseModel):
    """Error result."""

    exit_code: int
    error: str


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
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, path_type=str
    ),
    help="Upload directories recursively (repeatable)",
)
@click.option(
    "--collect",
    "collections",
    multiple=True,
    type=click.Path(exists=True, path_type=str),
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
    help="Comma-separated list of tools to bind (choices: user-data,file-search,code-interpreter)",
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
    tools: str,
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
    configure_progress_reporter(
        verbose=ctx.obj.get("verbose", False) if ctx.obj else False,
        progress=progress,
    )

    # Parse comma-separated tools string
    valid_tools = {"user-data", "file-search", "code-interpreter"}
    if tools is None or tools.strip() == "":
        tools_list = ["user-data"]
    else:
        tools_list = [tool.strip() for tool in tools.split(",")]

    # Validate tools
    invalid_tools = [tool for tool in tools_list if tool not in valid_tools]
    if invalid_tools:
        error_msg = f"Invalid tools: {', '.join(invalid_tools)}. Valid choices: {', '.join(sorted(valid_tools))}"
        if output_json:
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(f"❌ Error: {error_msg}")
        sys.exit(1)

    effective_tools = tuple(tools_list)

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

            # Convert to comma-separated string
            tools = ",".join(selected_tools)
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
            click.echo(json.dumps({"error": error_result.error}))
        else:
            click.echo(
                "❌ Error: No files specified. Use --file, --dir, or --collect options."
            )
        sys.exit(1)

    # call async batch
    if dry_run and output_json:
        # Early return to avoid nested Click context issues when combining --dry-run and --json
        # The dry-run preview has already been output above, so we can exit cleanly here
        return

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
        )
    )


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
) -> None:
    """Perform the actual batch upload operation."""
    try:
        # Create OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise click.ClickException(
                "OPENAI_API_KEY environment variable not set"
            )

        client = AsyncOpenAI(api_key=api_key, timeout=60.0)
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

        # Collect all files to process
        all_files: List[Path] = []
        errors: List[str] = []

        # Add individual files (with glob support)
        for file_path_str in files:
            file_path_obj = Path(file_path_str)
            if (
                "*" in file_path_str
                or "?" in file_path_str
                or "[" in file_path_str
            ):
                # Glob pattern
                parent = (
                    file_path_obj.parent
                    if file_path_obj.parent != Path(".")
                    else Path.cwd()
                )
                glob_pattern = file_path_obj.name
                for matched_file in parent.glob(glob_pattern):
                    if matched_file.is_file():
                        all_files.append(matched_file)
            else:
                # Regular file path
                if file_path_obj.exists() and file_path_obj.is_file():
                    all_files.append(file_path_obj)
                else:
                    errors.append(f"File not found: {file_path_str}")

        # Add files from directories (with glob support)
        for dir_path_str in directories:
            dir_path_obj = Path(dir_path_str)
            if (
                "*" in dir_path_str
                or "?" in dir_path_str
                or "[" in dir_path_str
            ):
                # Glob pattern for directories
                parent = (
                    dir_path_obj.parent
                    if dir_path_obj.parent != Path(".")
                    else Path.cwd()
                )
                glob_pattern = dir_path_obj.name
                for matched_dir in parent.glob(glob_pattern):
                    if matched_dir.is_dir():
                        for file_path in matched_dir.rglob("*"):
                            if file_path.is_file():
                                all_files.append(file_path)
            else:
                # Regular directory path
                for file_path in dir_path_obj.rglob("*"):
                    if file_path.is_file():
                        all_files.append(file_path)

        # Add files from collections
        for collection_path_str in collections:
            collection_file = Path(collection_path_str)
            if collection_file.name.startswith("@"):
                # Handle @filelist.txt syntax
                actual_path = Path(collection_file.name[1:])
                if actual_path.exists():
                    collection_file = actual_path

            with collection_file.open("r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        file_path = Path(line)
                        if file_path.exists() and file_path.is_file():
                            all_files.append(file_path)
                        else:
                            errors.append(
                                f"File not found in collection: {line}"
                            )

        # Apply global pattern filter
        if pattern:
            filtered_files = []
            for file_path in all_files:
                if fnmatch.fnmatch(file_path.name, pattern):
                    filtered_files.append(file_path)
            all_files = filtered_files

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for file_path in all_files:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)
        all_files = unique_files

        if not all_files:
            if output_json:
                empty_result = {
                    "uploaded": [],
                    "cached": [],
                    "errors": [],
                    "summary": {"total": 0},
                }
                click.echo(json.dumps(empty_result))
            else:
                click.echo("No files found matching criteria.")
            return

        # Dry run preview
        if dry_run:
            total_size = sum(f.stat().st_size for f in all_files)
            if output_json:
                preview = {
                    "dry_run": True,
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
                click.echo(json.dumps(preview))
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

        # Get progress reporter and start phase
        reporter = get_progress_reporter()
        handle = None
        if show_progress:
            handle = reporter.start_phase(
                "Uploading files", "📤", expected_steps=len(all_files)
            )

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
                if handle:
                    filename = Path(file_path).name
                    msg = (
                        f"Uploaded {filename}"
                        if progress == "detailed"
                        else None
                    )
                    reporter.advance(handle, advance=1, msg=msg)

            except Exception as e:
                error_msg = f"{file_path}: {str(e)}"

                # Improve error messages for common issues
                error_str = str(e)
                if (
                    "Files without extensions" in error_str
                    and "not supported for file-search" in error_str
                ):
                    # More concise message for extension issues
                    filename = Path(file_path).name
                    error_msg = f"{filename}: Cannot use with file-search (no file extension). File was uploaded successfully for template use."
                elif "Failed to add files to vector store" in error_str:
                    # Simplify vector store errors
                    filename = Path(file_path).name
                    error_msg = f"{filename}: Upload succeeded but file-search binding failed. File available for template use."

                errors.append(error_msg)
                logger.error(error_msg)

                # Update progress even on error
                if handle:
                    filename = Path(file_path).name
                    msg = (
                        f"Error with {filename}"
                        if progress == "detailed"
                        else None
                    )
                    reporter.advance(handle, advance=1, msg=msg)

        # Complete the phase
        if handle:
            success = len(errors) == 0
            summary = f"Uploaded {len(results)} files" + (
                f" ({len(errors)} errors)" if errors else ""
            )
            reporter.complete(handle, success=success, final_message=summary)

        # Output results
        if output_json:
            json_result = {
                "uploaded": [r.model_dump() for r in results if not r.cached],
                "cached": [r.model_dump() for r in results if r.cached],
                "errors": errors,
                "summary": {
                    "total": len(all_files),
                    "uploaded": len([r for r in results if not r.cached]),
                    "cached": len([r for r in results if r.cached]),
                    "errors": len(errors),
                },
            }
            click.echo(json.dumps(json_result))
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

            if errors:
                click.echo(f"\n❌ {len(errors)} errors:")
                for error in errors:
                    click.echo(f"   {error}")

            # Summary
            uploaded_count = len([r for r in results if not r.cached])
            cached_count = len([r for r in results if r.cached])
            click.echo(
                f"\n📊 Summary: {uploaded_count} uploaded, {cached_count} cached, {len(errors)} errors"
            )

    except Exception as e:
        if output_json:
            click.echo(json.dumps({"error": str(e)}))
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
            click.echo(json.dumps(result, indent=2))
        else:
            render_responsive_table(files, "files")

    except Exception as e:
        error_result = ErrorResult(exit_code=1, error=str(e))

        def format_error(r: BaseModel) -> str:
            if isinstance(r, ErrorResult):
                return f"Error: {r.error}"
            return str(r)

        if output_json:
            click.echo(json.dumps({"error": error_result.error}))
        else:
            click.echo(format_error(error_result))
