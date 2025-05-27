"""Type definitions for ostruct CLI."""

from pathlib import Path
from typing import List, Optional, Tuple, TypedDict, Union

# Import FileRoutingResult from validators
FileRoutingResult = List[Tuple[Optional[str], Union[str, Path]]]


class CLIParams(TypedDict, total=False):
    """Type-safe CLI parameters."""

    files: List[
        Tuple[str, str]
    ]  # List of (name, path) tuples from Click's nargs=2
    dir: List[
        Tuple[str, str]
    ]  # List of (name, dir) tuples from Click's nargs=2
    patterns: List[
        Tuple[str, str]
    ]  # List of (name, pattern) tuples from Click's nargs=2
    allowed_dirs: List[str]
    base_dir: str
    allowed_dir_file: Optional[str]
    recursive: bool
    var: List[str]
    json_var: List[str]
    system_prompt: Optional[str]
    system_prompt_file: Optional[str]
    ignore_task_sysprompt: bool
    model: str
    timeout: float
    output_file: Optional[str]
    dry_run: bool
    no_progress: bool
    api_key: Optional[str]
    verbose: bool
    debug_openai_stream: bool
    show_model_schema: bool
    debug_validation: bool
    temperature: Optional[float]
    max_output_tokens: Optional[int]
    top_p: Optional[float]
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    reasoning_effort: Optional[str]
    progress_level: str
    task_file: Optional[str]
    task: Optional[str]
    schema_file: str
    mcp_servers: List[str]
    mcp_allowed_tools: List[str]
    mcp_require_approval: str
    mcp_headers: Optional[str]
    code_interpreter_files: FileRoutingResult  # Fixed: was List[str]
    code_interpreter_dirs: List[str]
    code_interpreter_download_dir: str
    code_interpreter_cleanup: bool
    file_search_files: FileRoutingResult  # Fixed: was List[str]
    file_search_dirs: List[str]
    file_search_vector_store_name: str
    file_search_cleanup: bool
    file_search_retry_count: int
    file_search_timeout: float
    template_files: FileRoutingResult  # Fixed: was List[str]
    template_dirs: List[str]
    template_file_aliases: List[
        Tuple[str, Union[str, Path]]
    ]  # Fixed: was List[Tuple[str, str]]
    code_interpreter_file_aliases: List[
        Tuple[str, Union[str, Path]]
    ]  # Fixed: was List[Tuple[str, str]]
    file_search_file_aliases: List[
        Tuple[str, Union[str, Path]]
    ]  # Fixed: was List[Tuple[str, str]]
    tool_files: List[
        Tuple[str, str]
    ]  # List of (tool, path) tuples from --file-for
