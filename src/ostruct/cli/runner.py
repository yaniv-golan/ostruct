"""Async execution engine for ostruct CLI operations."""

import copy
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from urllib.parse import urlparse

from openai import AsyncOpenAI, OpenAIError
from openai_model_registry import ModelRegistry
from pydantic import BaseModel

from .code_interpreter import CodeInterpreterManager
from .config import OstructConfig
from .cost_estimation import calculate_cost_estimate, format_cost_breakdown
from .errors import APIErrorMapper, CLIError, SchemaValidationError
from .exit_codes import ExitCode
from .explicit_file_processor import ProcessingResult
from .file_search import FileSearchManager
from .json_extract import split_json_and_text
from .mcp_integration import MCPConfiguration, MCPServerManager
from .progress_reporting import (
    configure_progress_reporter,
    get_progress_reporter,
    report_success,
)
from .sentinel import extract_json_block
from .serialization import LogSerializer
from .services import ServiceContainer
from .types import CLIParams


# Error classes for API operations
class APIResponseError(Exception):
    pass


class EmptyResponseError(Exception):
    pass


class InvalidResponseFormatError(Exception):
    pass


def make_strict(obj: Any) -> None:
    """Transform Pydantic schema for Responses API strict mode.

    This function recursively adds 'additionalProperties: false' to all object types
    in a JSON schema to make it compatible with OpenAI's strict mode requirement.

    Args:
        obj: The schema object to transform (modified in-place)
    """
    if isinstance(obj, dict):
        if obj.get("type") == "object" and "additionalProperties" not in obj:
            obj["additionalProperties"] = False
        for value in obj.values():
            make_strict(value)
    elif isinstance(obj, list):
        for item in obj:
            make_strict(item)


def supports_structured_output(model: str) -> bool:
    """Check if model supports structured output."""
    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)
        return getattr(capabilities, "supports_structured_output", True)
    except Exception:
        # Default to True for backward compatibility
        return True


def _assistant_text(response: Any) -> str:
    """Extract text content from API response (Responses API format)."""
    text_parts = []
    for item in response.output:
        if getattr(item, "type", None) == "message":
            for content_block in item.content or []:
                if hasattr(content_block, "text"):
                    # For Responses API, text content is directly in the text attribute
                    text_parts.append(content_block.text)
    return "\n".join(text_parts)


logger = logging.getLogger(__name__)


async def process_mcp_configuration(args: CLIParams) -> MCPServerManager:
    """Process MCP configuration from CLI arguments.

    Args:
        args: CLI parameters containing MCP settings

    Returns:
        MCPServerManager: Configured manager ready for tool integration

    Raises:
        CLIError: If MCP configuration is invalid
    """
    logger.debug("=== MCP Configuration Processing ===")

    # Parse MCP servers from CLI arguments
    servers = []
    for server_spec in args.get("mcp_servers", []):
        try:
            # Parse format: [label@]url
            if "@" in server_spec:
                label, url = server_spec.rsplit("@", 1)
            else:
                url = server_spec
                label = None

            server_config = {"url": url}
            if label:
                server_config["label"] = label

            # Add require_approval setting from CLI
            server_config["require_approval"] = args.get(
                "mcp_require_approval", "never"
            )

            # Parse headers if provided
            mcp_headers = args.get("mcp_headers")
            if mcp_headers:
                try:
                    headers = json.loads(mcp_headers)
                    server_config["headers"] = headers
                except json.JSONDecodeError as e:
                    raise CLIError(
                        f"Invalid JSON in --mcp-headers: {e}",
                        exit_code=ExitCode.USAGE_ERROR,
                    )

            servers.append(server_config)

        except Exception as e:
            raise CLIError(
                f"Failed to parse MCP server spec '{server_spec}': {e}",
                exit_code=ExitCode.USAGE_ERROR,
            )

    # Process allowed tools if specified
    allowed_tools_map = {}
    mcp_allowed_tools = args.get("mcp_allowed_tools", [])
    for tools_spec in mcp_allowed_tools:
        try:
            if ":" not in tools_spec:
                raise ValueError("Format should be server_label:tool1,tool2")
            label, tools_str = tools_spec.split(":", 1)
            tools_list = [tool.strip() for tool in tools_str.split(",")]
            allowed_tools_map[label] = tools_list
        except Exception as e:
            raise CLIError(
                f"Failed to parse MCP allowed tools '{tools_spec}': {e}",
                exit_code=ExitCode.USAGE_ERROR,
            )

    # Apply allowed tools to server configurations
    for server in servers:
        server_label = server.get("label")
        if server_label and server_label in allowed_tools_map:
            server["allowed_tools"] = allowed_tools_map[server_label]  # type: ignore[assignment]

    # Create configuration and manager
    MCPConfiguration(servers)  # Validate configuration
    manager = MCPServerManager(servers)

    # Pre-validate servers for CLI compatibility
    validation_errors = await manager.pre_validate_all_servers()
    if validation_errors:
        error_msg = "MCP server validation failed:\n" + "\n".join(
            f"- {error}" for error in validation_errors
        )
        # Map as MCP error
        mapped_error = APIErrorMapper.map_tool_error(
            "mcp", Exception(error_msg)
        )
        raise mapped_error

    logger.debug(
        "MCP configuration validated successfully with %d servers",
        len(servers),
    )
    return manager


async def process_code_interpreter_configuration(
    args: CLIParams, client: AsyncOpenAI
) -> Optional[Dict[str, Any]]:
    """Process Code Interpreter configuration from CLI arguments.

    Args:
        args: CLI parameters containing Code Interpreter settings
        client: AsyncOpenAI client for file uploads

    Returns:
        Dictionary with Code Interpreter tool config and manager, or None if no files specified

    Raises:
        CLIError: If Code Interpreter configuration is invalid
    """
    logger.debug("=== Code Interpreter Configuration Processing ===")

    # Collect all files to upload
    files_to_upload = []

    # Add individual files (extract paths from tuples)
    code_interpreter_files = args.get("code_interpreter_files", [])
    for file_entry in code_interpreter_files:
        if isinstance(file_entry, tuple):
            # Extract path from (name, path) tuple
            _, file_path = file_entry
            files_to_upload.append(str(file_path))
        else:
            # Handle legacy string format
            files_to_upload.append(str(file_entry))

    # Add files from directories
    for directory in args.get("code_interpreter_dirs", []):
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                raise CLIError(
                    f"Directory not found: {directory}",
                    exit_code=ExitCode.USAGE_ERROR,
                )

            # Get all files from directory (non-recursive for safety)
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    files_to_upload.append(str(file_path))

        except Exception as e:
            raise CLIError(
                f"Failed to process directory {directory}: {e}",
                exit_code=ExitCode.USAGE_ERROR,
            )

    # If no files specified, return None
    if not files_to_upload:
        return None

    # Load configuration for Code Interpreter
    from typing import Union, cast

    from .config import OstructConfig

    config_path = cast(Union[str, Path, None], args.get("config"))
    config = OstructConfig.load(config_path)
    ci_config = config.get_code_interpreter_config()

    # Apply CLI parameter overrides to config
    effective_ci_config = dict(ci_config)  # Make a copy

    # Override duplicate_outputs if CLI flag is provided
    if args.get("ci_duplicate_outputs") is not None:
        effective_ci_config["duplicate_outputs"] = args["ci_duplicate_outputs"]

    # Create Code Interpreter manager
    manager = CodeInterpreterManager(client, effective_ci_config)

    # Validate files before upload
    validation_errors = manager.validate_files_for_upload(files_to_upload)
    if validation_errors:
        error_msg = "Code Interpreter file validation failed:\n" + "\n".join(
            f"- {error}" for error in validation_errors
        )
        raise CLIError(error_msg, exit_code=ExitCode.USAGE_ERROR)

    try:
        # Upload files
        logger.debug(
            f"Uploading {len(files_to_upload)} files for Code Interpreter"
        )
        file_ids = await manager.upload_files_for_code_interpreter(
            files_to_upload
        )

        # Build tool configuration
        # Cast to concrete CodeInterpreterManager to access build_tool_config
        concrete_ci_manager = manager
        if hasattr(concrete_ci_manager, "build_tool_config"):
            ci_tool_config = concrete_ci_manager.build_tool_config(file_ids)
            logger.debug(f"Code Interpreter tool config: {ci_tool_config}")
            return {
                "tool_config": ci_tool_config,
                "manager": manager,
                "file_ids": file_ids,
            }
        else:
            logger.warning(
                "Code Interpreter manager does not have build_tool_config method"
            )
            return None

    except Exception as e:
        logger.error(f"Failed to configure Code Interpreter: {e}")
        # Clean up any uploaded files on error
        await manager.cleanup_uploaded_files()
        # Map tool-specific errors
        mapped_error = APIErrorMapper.map_tool_error("code-interpreter", e)
        raise mapped_error


async def process_file_search_configuration(
    args: CLIParams, client: AsyncOpenAI
) -> Optional[Dict[str, Any]]:
    """Process File Search configuration from CLI arguments.

    Args:
        args: CLI parameters containing File Search settings
        client: AsyncOpenAI client for vector store operations

    Returns:
        Dictionary with File Search tool config and manager, or None if no files specified

    Raises:
        CLIError: If File Search configuration is invalid
    """
    logger.debug("=== File Search Configuration Processing ===")

    # Collect all files to upload
    files_to_upload = []

    # Add individual files (extract paths from tuples)
    file_search_files = args.get("file_search_files", [])
    for file_entry in file_search_files:
        if isinstance(file_entry, tuple):
            # Extract path from (name, path) tuple
            _, file_path = file_entry
            files_to_upload.append(str(file_path))
        else:
            # Handle legacy string format
            files_to_upload.append(str(file_entry))

    # Add files from directories
    for directory in args.get("file_search_dirs", []):
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                raise CLIError(
                    f"Directory not found: {directory}",
                    exit_code=ExitCode.USAGE_ERROR,
                )

            # Get all files from directory (non-recursive for safety)
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    files_to_upload.append(str(file_path))

        except Exception as e:
            raise CLIError(
                f"Failed to process directory {directory}: {e}",
                exit_code=ExitCode.USAGE_ERROR,
            )

    # If no files specified, return None
    if not files_to_upload:
        return None

    # Create File Search manager
    manager = FileSearchManager(client)

    # Validate files before upload
    validation_errors = manager.validate_files_for_file_search(files_to_upload)
    if validation_errors:
        error_msg = "File Search file validation failed:\n" + "\n".join(
            f"- {error}" for error in validation_errors
        )
        raise CLIError(error_msg, exit_code=ExitCode.USAGE_ERROR)

    try:
        # Get configuration parameters
        vector_store_name = args.get("fs_store_name", "ostruct_search")
        retry_count = args.get("fs_retries", 3)
        timeout = args.get("fs_timeout", 60.0)

        # Create vector store with retry logic
        logger.debug(
            f"Creating vector store '{vector_store_name}' for {len(files_to_upload)} files"
        )
        vector_store_id = await manager.create_vector_store_with_retry(
            name=vector_store_name, max_retries=retry_count
        )

        # Upload files to vector store
        logger.debug(
            f"Uploading {len(files_to_upload)} files to vector store with {retry_count} max retries"
        )
        file_ids = await manager.upload_files_to_vector_store(
            vector_store_id=vector_store_id,
            files=files_to_upload,
            max_retries=retry_count,
        )

        # Wait for vector store to be ready
        logger.debug(
            f"Waiting for vector store indexing (timeout: {timeout}s)"
        )
        is_ready = await manager.wait_for_vector_store_ready(
            vector_store_id=vector_store_id, timeout=timeout
        )

        if not is_ready:
            logger.warning(
                f"Vector store may not be fully indexed within {timeout}s timeout"
            )
            # Continue anyway as indexing is typically instant

        # Build tool configuration
        tool_config = manager.build_tool_config(vector_store_id)

        # Get performance info for user awareness
        perf_info = manager.get_performance_info()
        logger.debug(f"File Search performance info: {perf_info}")

        return {
            "tool_config": tool_config,
            "manager": manager,
            "vector_store_id": vector_store_id,
            "file_ids": file_ids,
            "perf_info": perf_info,
        }

    except Exception as e:
        logger.error(f"Failed to configure File Search: {e}")
        # Clean up any created resources on error
        await manager.cleanup_resources()
        # Map tool-specific errors
        mapped_error = APIErrorMapper.map_tool_error("file-search", e)
        raise mapped_error


async def create_structured_output(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    output_schema: Type[BaseModel],
    output_file: Optional[str] = None,
    tools: Optional[List[dict]] = None,
    **kwargs: Any,
) -> BaseModel:
    """Create structured output from OpenAI Responses API.

    This function uses the OpenAI Responses API with strict mode schema validation
    to generate structured output that matches the provided Pydantic model.

    Args:
        client: The OpenAI client to use
        model: The model to use
        system_prompt: The system prompt to use
        user_prompt: The user prompt to use
        output_schema: The Pydantic model to validate responses against
        output_file: Optional file to write output to (unused, kept for compatibility)
        tools: Optional list of tools (e.g., MCP, Code Interpreter) to include
        **kwargs: Additional parameters to pass to the API

    Returns:
        A validated model instance

    Raises:
        ValueError: If the model does not support structured output or parameters are invalid
        APIResponseError: If there is an API error
    """
    try:
        # Check if model supports structured output using our stub function
        if not supports_structured_output(model):
            raise ValueError(
                f"Model {model} does not support structured output with json_schema response format. "
                "Please use a model that supports structured output."
            )

        # Extract non-model parameters
        on_log = kwargs.pop("on_log", None)

        # Handle model-specific parameters
        api_kwargs = {}
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)

        # Validate and include supported parameters
        for param_name, value in kwargs.items():
            if param_name in capabilities.supported_parameters:
                # Validate the parameter value
                capabilities.validate_parameter(param_name, value)
                api_kwargs[param_name] = value
            else:
                logger.warning(
                    f"Parameter {param_name} is not supported by model {model} and will be ignored"
                )

        # Prepare schema for strict mode
        schema = output_schema.model_json_schema()
        strict_schema = copy.deepcopy(schema)
        make_strict(strict_schema)

        # Generate schema name from model class name
        schema_name = output_schema.__name__.lower()

        # Combine system and user prompts into a single input string
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Prepare API call parameters
        api_params = {
            "model": model,
            "input": combined_prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": strict_schema,
                    "strict": True,
                }
            },
            "stream": False,
            **api_kwargs,
        }

        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            logger.debug("Tools: %s", json.dumps(tools, indent=2))

        # Log the API request details
        logger.debug("Making OpenAI Responses API request with:")
        logger.debug("Model: %s", model)
        logger.debug("Combined prompt: %s", combined_prompt)
        logger.debug("Parameters: %s", json.dumps(api_kwargs, indent=2))
        logger.debug("Schema: %s", json.dumps(strict_schema, indent=2))
        logger.debug("Tools being passed to API: %s", tools)
        logger.debug(
            "Complete API params: %s",
            json.dumps(api_params, indent=2, default=str),
        )

        # Use the Responses API
        api_response = await client.responses.create(**api_params)

        if on_log:
            on_log(logging.DEBUG, f"Received response: {api_response.id}", {})

        # Get the complete response content directly
        content = api_response.output_text

        if on_log:
            on_log(
                logging.DEBUG,
                f"Response content length: {len(content)}",
                {},
            )

        # Parse and validate the complete response
        try:
            # Try new JSON extraction logic first
            try:
                data, markdown_text = split_json_and_text(content)
            except ValueError:
                # Fallback to original parsing for non-fenced JSON
                try:
                    data = json.loads(content.strip())
                    markdown_text = ""
                except json.JSONDecodeError as json_error:
                    # DEFENSIVE PARSING: Handle Code Interpreter + Structured Outputs compatibility issue
                    # OpenAI's Code Interpreter can append commentary after valid JSON when using strict schemas,
                    # causing json.loads() to fail. This is a known intermittent issue documented in OpenAI forums.
                    # We extract the JSON portion and warn the user that the workaround was applied.
                    if tools and any(
                        tool.get("type") == "code_interpreter"
                        for tool in tools
                    ):
                        logger.debug(
                            "Code Interpreter detected with JSON parsing failure, attempting defensive parsing"
                        )

                        # Try to extract JSON from the beginning of the response
                        json_match = re.search(
                            r"\{.*?\}", content.strip(), re.DOTALL
                        )
                        if json_match:
                            try:
                                data = json.loads(json_match.group(0))
                                markdown_text = ""
                                logger.warning(
                                    "Code Interpreter added extra content after JSON. "
                                    "Extracted JSON successfully using defensive parsing. "
                                    "This is a known intermittent issue with OpenAI's API."
                                )
                            except json.JSONDecodeError:
                                # Even defensive parsing failed, re-raise original error
                                raise json_error
                        else:
                            # No JSON pattern found, re-raise original error
                            raise json_error
                    else:
                        # Not using Code Interpreter, re-raise original error
                        raise json_error

            validated = output_schema.model_validate(data)

            # Store full raw text for downstream processing (debug logs, etc.)
            setattr(validated, "_raw_text", content)
            # Store markdown text for annotation processing
            setattr(validated, "_markdown_text", markdown_text)
            # Store full API response for file download access
            setattr(validated, "_api_response", api_response)

            return validated

        except ValueError as e:
            logger.error(f"Failed to parse response content: {e}")
            raise InvalidResponseFormatError(
                f"Failed to parse response as valid JSON: {e}"
            )

    except Exception as e:
        # Map OpenAI errors using the error mapper
        if isinstance(e, OpenAIError):
            mapped_error = APIErrorMapper.map_openai_error(e)
            logger.error(f"OpenAI API error mapped: {mapped_error}")
            raise mapped_error

        # Re-raise already-mapped CLIError types (like SchemaValidationError)
        if isinstance(e, CLIError):
            raise

        # Handle special schema array error with detailed guidance
        if "Invalid schema for response_format" in str(
            e
        ) and 'type: "array"' in str(e):
            error_msg = (
                "OpenAI API Schema Error: The schema must have a root type of 'object', not 'array'. "
                "To fix this:\n"
                "1. Wrap your array in an object property, e.g.:\n"
                "   {\n"
                '     "type": "object",\n'
                '     "properties": {\n'
                '       "items": {\n'
                '         "type": "array",\n'
                '         "items": { ... your array items schema ... }\n'
                "       }\n"
                "     }\n"
                "   }\n"
                "2. Make sure to update your template to handle the wrapper object."
            )
            logger.error(error_msg)
            raise InvalidResponseFormatError(error_msg)

        # For non-OpenAI errors, create appropriate CLIErrors
        error_msg = str(e).lower()
        if (
            "context_length_exceeded" in error_msg
            or "maximum context length" in error_msg
        ):
            raise CLIError(
                f"Context length exceeded: {str(e)}",
                exit_code=ExitCode.API_ERROR,
            )
        elif "rate_limit" in error_msg or "429" in str(e):
            raise CLIError(
                f"Rate limit exceeded: {str(e)}", exit_code=ExitCode.API_ERROR
            )
        elif "invalid_api_key" in error_msg:
            raise CLIError(
                f"Invalid API key: {str(e)}", exit_code=ExitCode.API_ERROR
            )
        else:
            logger.error(f"Unmapped API error: {e}")
            raise APIResponseError(str(e))


# Note: validation functions are defined in cli.py to avoid circular imports


async def process_templates(
    args: CLIParams,
    task_template: str,
    template_context: Any,
    env: Any,
    template_path: str,
) -> tuple[str, str]:
    """Process templates.

    This function will be moved from cli.py later.
    For now, we import it from the main cli module to avoid circular imports.
    """
    # Import here to avoid circular dependency during refactoring
    from .template_processor import process_templates as _process_templates

    return await _process_templates(
        args, task_template, template_context, env, template_path
    )


async def _execute_two_pass_sentinel(
    client: AsyncOpenAI,
    args: CLIParams,
    system_prompt: str,
    user_prompt: str,
    output_model: Type[BaseModel],
    tools: List[dict],
    log_cb: Any,
    ci_config: Dict[str, Any],
    code_interpreter_info: Optional[Dict[str, Any]],
) -> tuple[BaseModel, List[str]]:
    """Execute two-pass sentinel approach for file downloads."""
    import json

    # ---- pass 1 (raw) ----
    logger.debug("Starting two-pass execution: Pass 1 (raw mode)")
    raw_resp = await client.responses.create(
        model=args["model"],
        input=f"{system_prompt}\n\n{user_prompt}",
        tools=tools,  # type: ignore[arg-type]
        # No text format - this allows annotations
    )

    logger.debug(f"Raw response structure: {type(raw_resp)}")
    logger.debug(
        f"Raw response output: {getattr(raw_resp, 'output', 'No output attr')}"
    )
    raw_text = _assistant_text(raw_resp)
    logger.debug(
        f"Raw response from first pass (first 500 chars): {raw_text[:500]}"
    )
    data = extract_json_block(raw_text) or {}
    logger.debug(f"Extracted JSON from sentinel markers: {bool(data)}")

    # Validate sentinel extraction
    if not data:
        logger.warning(
            "No sentinel JSON found in first pass, falling back to single-pass"
        )
        return await _fallback_single_pass(
            client,
            args,
            system_prompt,
            user_prompt,
            output_model,
            tools,
            log_cb,
        )

    # download files from first pass
    downloaded_files = []
    if code_interpreter_info and code_interpreter_info.get("manager"):
        cm = code_interpreter_info["manager"]
        # Use output directory from config, fallback to args, then default
        from .constants import DefaultPaths

        download_dir = (
            ci_config.get("output_directory")
            or args.get("ci_download_dir")
            or DefaultPaths.CODE_INTERPRETER_OUTPUT_DIR
        )
        logger.debug(f"Downloading files to: {download_dir}")
        downloaded_files = await cm.download_generated_files(
            raw_resp, download_dir
        )
        if downloaded_files:
            logger.info(
                f"Downloaded {len(downloaded_files)} files from first pass"
            )

    # ---- pass 2 (strict) ----
    logger.debug("Starting two-pass execution: Pass 2 (structured mode)")
    strict_sys = (
        system_prompt
        + "\n\nReuse ONLY these values; do not repeat external calls:\n"
        + json.dumps(data, indent=2)
    )

    # Prepare schema for strict mode
    schema = output_model.model_json_schema()
    strict_schema = copy.deepcopy(schema)
    make_strict(strict_schema)
    schema_name = output_model.__name__.lower()

    strict_resp = await client.responses.create(
        model=args["model"],
        input=f"{strict_sys}\n\n{user_prompt}",
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": strict_schema,
                "strict": True,
            }
        },
        tools=[],  # No tools needed for formatting
        stream=False,
    )

    # Parse and validate the structured response
    content = strict_resp.output_text
    try:
        # Try new JSON extraction logic first
        try:
            data_final, markdown_text = split_json_and_text(content)
        except ValueError:
            # Fallback to original parsing for non-fenced JSON
            try:
                data_final = json.loads(content.strip())
                markdown_text = ""
            except json.JSONDecodeError as json_error:
                # DEFENSIVE PARSING: Handle Code Interpreter + Structured Outputs compatibility issue
                # In two-pass mode, the second pass should be clean, but apply defensive parsing
                # as a safety net in case the issue still occurs.
                logger.debug(
                    "JSON parsing failure in two-pass mode, attempting defensive parsing"
                )

                # Try to extract JSON from the beginning of the response
                json_match = re.search(r"\{.*?\}", content.strip(), re.DOTALL)
                if json_match:
                    try:
                        data_final = json.loads(json_match.group(0))
                        markdown_text = ""
                        logger.warning(
                            "Two-pass mode: Extra content found after JSON in structured response. "
                            "Extracted JSON successfully using defensive parsing. "
                            "This should not happen in pass 2 - please report this issue."
                        )
                    except json.JSONDecodeError:
                        # Even defensive parsing failed, re-raise original error
                        raise json_error
                else:
                    # No JSON pattern found, re-raise original error
                    raise json_error

        validated = output_model.model_validate(data_final)

        # Store full raw text for downstream processing (debug logs, etc.)
        setattr(validated, "_raw_text", content)
        # Store markdown text for annotation processing
        setattr(validated, "_markdown_text", markdown_text)
        # Store full API response for file download access
        setattr(validated, "_api_response", strict_resp)

        return validated, downloaded_files

    except ValueError as e:
        logger.error(f"Failed to parse structured response content: {e}")
        raise InvalidResponseFormatError(
            f"Failed to parse response as valid JSON: {e}"
        )


async def _fallback_single_pass(
    client: AsyncOpenAI,
    args: CLIParams,
    system_prompt: str,
    user_prompt: str,
    output_model: Type[BaseModel],
    tools: List[dict],
    log_cb: Any,
) -> tuple[BaseModel, List[str]]:
    """Fallback to single-pass execution."""
    logger.debug("Executing single-pass fallback")
    response = await create_structured_output(
        client=client,
        model=args["model"],
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_schema=output_model,
        output_file=args.get("output_file"),
        on_log=log_cb,
        tools=tools,
    )
    return response, []  # No files downloaded in fallback


def _get_effective_download_strategy(
    args: CLIParams, ci_config: Dict[str, Any]
) -> str:
    """Determine the effective download strategy from config and feature flags.

    Args:
        args: CLI parameters including enabled_features and disabled_features
        ci_config: Code interpreter configuration

    Returns:
        Either "single_pass" or "two_pass_sentinel"
    """
    # Start with config default
    strategy: str = ci_config.get("download_strategy", "single_pass")

    # Check for feature flag override
    enabled_features = args.get("enabled_features", [])
    disabled_features = args.get("disabled_features", [])

    if enabled_features or disabled_features:
        from .click_options import parse_feature_flags

        try:
            parsed_flags = parse_feature_flags(
                tuple(enabled_features), tuple(disabled_features)
            )
            ci_hack_flag = parsed_flags.get("ci-download-hack")
            if ci_hack_flag == "on":
                strategy = "two_pass_sentinel"
            elif ci_hack_flag == "off":
                strategy = "single_pass"
        except Exception as e:
            logger.warning(f"Failed to parse feature flags: {e}")

    return strategy


async def execute_model(
    args: CLIParams,
    params: Dict[str, Any],
    output_model: Type[BaseModel],
    system_prompt: str,
    user_prompt: str,
) -> ExitCode:
    """Execute the model with the given parameters."""
    logger.debug("=== Execution Phase ===")

    # Pre-validate unattended compatibility
    # Note: MCP validation is handled during MCP configuration processing
    # mcp_servers = args.get("mcp_servers", [])
    # if mcp_servers:
    #     validator = UnattendedCompatibilityValidator()
    #     validation_errors = validator.validate_mcp_servers(mcp_servers)
    #     if validation_errors:
    #         error_msg = "Unattended operation compatibility errors:\n" + "\n".join(
    #             f"  • {err}" for err in validation_errors
    #         )
    #         logger.error(error_msg)
    #         raise CLIError(error_msg, exit_code=ExitCode.VALIDATION_ERROR)

    api_key = args.get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = (
            "No OpenAI API key found. Please:\n"
            "  • Set OPENAI_API_KEY environment variable, or\n"
            "  • Create a .env file with OPENAI_API_KEY=your-key-here, or\n"
            "  • Use --api-key option (not recommended for production)\n"
            "\n"
            "Get your API key from: https://platform.openai.com/api-keys"
        )
        logger.error(msg)
        raise CLIError(msg, exit_code=ExitCode.API_ERROR)

    # Get API timeout
    api_timeout = args.get("timeout", 60.0)
    client = AsyncOpenAI(
        api_key=api_key,
        timeout=min(float(api_timeout), 300.0),
    )  # Cap at 5 min for client timeout

    # Create service container for dependency management
    services = ServiceContainer(client, args)

    # Initialize variables that will be used in nested functions
    code_interpreter_info = None
    file_search_info = None

    # Create detailed log callback
    def log_callback(level: int, message: str, extra: dict[str, Any]) -> None:
        if args.get("verbose", False):
            if extra:
                extra_str = LogSerializer.serialize_log_extra(extra)
                if extra_str:
                    logger.debug("%s\nExtra:\n%s", message, extra_str)
                else:
                    logger.debug("%s\nExtra: Failed to serialize", message)
            else:
                logger.debug(message)

    async def execute_main_operation() -> ExitCode:
        """Main execution operation wrapped for timeout handling."""
        # Create output buffer
        output_buffer = []

        # Process tool configurations
        tools = []
        nonlocal code_interpreter_info, file_search_info

        # Get universal tool toggle overrides first
        enabled_tools: set[str] = args.get("_enabled_tools", set())  # type: ignore[assignment]
        disabled_tools: set[str] = args.get("_disabled_tools", set())  # type: ignore[assignment]

        # Initialize shared upload manager for multi-tool file sharing (T3.2)
        shared_upload_manager = None

        # Check if we have new attachment system with multi-tool attachments
        from .attachment_processor import (
            _extract_attachments_from_args,
            _has_new_attachment_syntax,
        )

        if _has_new_attachment_syntax(args):
            logger.debug(
                "Initializing shared upload manager for new attachment system"
            )
            from .attachment_processor import AttachmentProcessor
            from .upload_manager import SharedUploadManager
            from .validators import validate_security_manager

            shared_upload_manager = SharedUploadManager(client)

            # Get security manager for file validation
            security_manager = validate_security_manager(
                base_dir=args.get("base_dir"),
                allowed_dirs=args.get("allowed_dirs"),
                allowed_dir_file=args.get("allowed_dir_file"),
            )

            # Process and register attachments
            processor = AttachmentProcessor(security_manager)
            attachments = _extract_attachments_from_args(args)
            processed_attachments = processor.process_attachments(attachments)

            # Register all attachments with the shared manager
            shared_upload_manager.register_attachments(processed_attachments)

            logger.debug("Registered attachments with shared upload manager")

        # Process MCP configuration if provided
        # Apply universal tool toggle overrides for mcp
        mcp_enabled_by_config = services.is_configured("mcp")
        mcp_enabled_by_toggle = "mcp" in enabled_tools
        mcp_disabled_by_toggle = "mcp" in disabled_tools

        # Determine final enablement state
        mcp_should_enable = False
        if mcp_enabled_by_toggle:
            # Universal --enable-tool takes highest precedence
            mcp_should_enable = True
            logger.debug("MCP enabled via --enable-tool")
        elif mcp_disabled_by_toggle:
            # Universal --disable-tool takes highest precedence
            mcp_should_enable = False
            logger.debug("MCP disabled via --disable-tool")
        else:
            # Fall back to config-based enablement
            mcp_should_enable = mcp_enabled_by_config

        if mcp_should_enable and services.is_configured("mcp"):
            mcp_manager = await services.get_mcp_manager()
            if mcp_manager:
                tools.extend(mcp_manager.get_tools_for_responses_api())

        # Get routing result from explicit file processor
        routing_result = args.get("_routing_result")
        if routing_result is not None and not isinstance(
            routing_result, ProcessingResult
        ):
            routing_result = None  # Invalid type, treat as None
        routing_result_typed: Optional[ProcessingResult] = routing_result

        # Process Code Interpreter configuration if enabled
        # Apply universal tool toggle overrides for code-interpreter
        ci_enabled_by_routing = (
            routing_result_typed
            and "code-interpreter" in routing_result_typed.enabled_tools
        )
        ci_enabled_by_toggle = "code-interpreter" in enabled_tools
        ci_disabled_by_toggle = "code-interpreter" in disabled_tools

        # Determine final enablement state
        ci_should_enable = False
        if ci_enabled_by_toggle:
            # Universal --enable-tool takes highest precedence
            ci_should_enable = True
            logger.debug("Code Interpreter enabled via --enable-tool")
        elif ci_disabled_by_toggle:
            # Universal --disable-tool takes highest precedence
            ci_should_enable = False
            logger.debug("Code Interpreter disabled via --disable-tool")
        else:
            # Fall back to routing-based enablement
            ci_should_enable = bool(ci_enabled_by_routing)

        if ci_should_enable:
            code_interpreter_manager = None
            file_ids = []

            if shared_upload_manager:
                # Use shared upload manager for new attachment system
                logger.debug(
                    "Using shared upload manager for Code Interpreter"
                )
                from .code_interpreter import CodeInterpreterManager

                code_interpreter_manager = CodeInterpreterManager(
                    client, upload_manager=shared_upload_manager
                )

                # Get file IDs from shared manager
                file_ids = (
                    await code_interpreter_manager.get_files_from_shared_manager()
                )
                logger.debug(
                    f"Got {len(file_ids)} file IDs from shared manager for CI"
                )

            elif routing_result_typed:
                # Legacy routing system - process individual files
                code_interpreter_files = (
                    routing_result_typed.validated_files.get(
                        "code-interpreter", []
                    )
                )
                if code_interpreter_files:
                    # Override args with routed files for Code Interpreter processing
                    ci_args = dict(args)
                    ci_args["code_interpreter_files"] = code_interpreter_files
                    ci_args["code_interpreter_dirs"] = (
                        []
                    )  # Files already expanded from dirs
                    ci_args["code_interpreter"] = (
                        True  # Enable for service container
                    )

                    # Create temporary service container with updated args
                    ci_services = ServiceContainer(client, ci_args)  # type: ignore[arg-type]
                    code_interpreter_manager_protocol = (
                        await ci_services.get_code_interpreter_manager()
                    )
                    # Cast to the concrete type we know we're getting
                    ci_manager: Optional[CodeInterpreterManager] = None
                    if code_interpreter_manager_protocol:
                        from .code_interpreter import CodeInterpreterManager

                        ci_manager = code_interpreter_manager_protocol  # type: ignore[assignment]
                    if ci_manager:
                        # Get the uploaded file IDs from the manager
                        if (
                            hasattr(ci_manager, "uploaded_file_ids")
                            and ci_manager.uploaded_file_ids
                        ):
                            file_ids = ci_manager.uploaded_file_ids
                        else:
                            logger.warning(
                                "Code Interpreter manager has no uploaded file IDs"
                            )

            # Build tool configuration if we have a manager and files
            if code_interpreter_manager and file_ids:
                # Cast to concrete CodeInterpreterManager to access build_tool_config
                concrete_ci_manager = code_interpreter_manager
                if hasattr(concrete_ci_manager, "build_tool_config"):
                    ci_tool_config = concrete_ci_manager.build_tool_config(
                        file_ids
                    )
                    logger.debug(
                        f"Code Interpreter tool config: {ci_tool_config}"
                    )
                    code_interpreter_info = {
                        "manager": code_interpreter_manager,
                        "tool_config": ci_tool_config,
                    }
                    tools.append(ci_tool_config)

        # Process File Search configuration if enabled
        # Apply universal tool toggle overrides for file-search
        fs_enabled_by_routing = (
            routing_result_typed
            and "file-search" in routing_result_typed.enabled_tools
        )
        fs_enabled_by_toggle = "file-search" in enabled_tools
        fs_disabled_by_toggle = "file-search" in disabled_tools

        # Determine final enablement state
        fs_should_enable = False
        if fs_enabled_by_toggle:
            # Universal --enable-tool takes highest precedence
            fs_should_enable = True
            logger.debug("File Search enabled via --enable-tool")
        elif fs_disabled_by_toggle:
            # Universal --disable-tool takes highest precedence
            fs_should_enable = False
            logger.debug("File Search disabled via --disable-tool")
        else:
            # Fall back to routing-based enablement
            fs_should_enable = bool(fs_enabled_by_routing)

        if fs_should_enable:
            file_search_manager = None
            vector_store_id = None

            if shared_upload_manager:
                # Use shared upload manager for new attachment system
                logger.debug("Using shared upload manager for File Search")
                from .file_search import FileSearchManager

                file_search_manager = FileSearchManager(
                    client, upload_manager=shared_upload_manager
                )

                # Create vector store with files from shared manager
                vector_store_id = await file_search_manager.create_vector_store_from_shared_manager(
                    "ostruct_vector_store"
                )
                logger.debug(
                    f"Created vector store {vector_store_id} from shared manager"
                )

            elif routing_result_typed:
                # Legacy routing system - process individual files
                file_search_files = routing_result_typed.validated_files.get(
                    "file-search", []
                )
                if file_search_files:
                    # Override args with routed files for File Search processing
                    fs_args = dict(args)
                    fs_args["file_search_files"] = file_search_files
                    fs_args["file_search_dirs"] = (
                        []
                    )  # Files already expanded from dirs
                    fs_args["file_search"] = (
                        True  # Enable for service container
                    )

                    # Create temporary service container with updated args
                    fs_services = ServiceContainer(client, fs_args)  # type: ignore[arg-type]
                    file_search_manager_protocol = (
                        await fs_services.get_file_search_manager()
                    )
                    # Cast to the concrete type we know we're getting
                    fs_manager: Optional[FileSearchManager] = None
                    if file_search_manager_protocol:
                        from .file_search import FileSearchManager

                        fs_manager = file_search_manager_protocol  # type: ignore[assignment]
                    if fs_manager:
                        # Get the vector store ID from the manager's created vector stores
                        # The most recent one should be the one we need
                        if (
                            hasattr(fs_manager, "created_vector_stores")
                            and fs_manager.created_vector_stores
                        ):
                            vector_store_id = fs_manager.created_vector_stores[
                                -1
                            ]
                        else:
                            logger.warning(
                                "File Search manager has no created vector stores"
                            )

            # Build tool configuration if we have a manager and vector store
            if file_search_manager and vector_store_id:
                # Cast to concrete FileSearchManager to access build_tool_config
                concrete_fs_manager = file_search_manager
                if hasattr(concrete_fs_manager, "build_tool_config"):
                    fs_tool_config = concrete_fs_manager.build_tool_config(
                        vector_store_id
                    )
                    logger.debug(f"File Search tool config: {fs_tool_config}")
                    file_search_info = {
                        "manager": file_search_manager,
                        "tool_config": fs_tool_config,
                    }
                    tools.append(fs_tool_config)

        # Process Web Search configuration if enabled
        # Apply universal tool toggle overrides for web-search
        from typing import cast

        config_path = cast(Union[str, Path, None], args.get("config"))
        config = OstructConfig.load(config_path)
        web_search_config = config.get_web_search_config()

        # Determine if web search should be enabled
        web_search_enabled = False
        if "web-search" in enabled_tools:
            # Universal --enable-tool web-search takes highest precedence
            web_search_enabled = True
            logger.debug("Web search enabled via --enable-tool")
        elif "web-search" in disabled_tools:
            # Universal --disable-tool web-search takes highest precedence
            web_search_enabled = False
            logger.debug("Web search disabled via --disable-tool")
        else:
            # Use config default
            web_search_enabled = web_search_config.enable_by_default

        if web_search_enabled:
            # Import validation function
            from .model_validation import validate_web_search_compatibility

            # Check model compatibility
            compatibility_warning = validate_web_search_compatibility(
                args["model"], True
            )
            if compatibility_warning:
                logger.warning(compatibility_warning)
                # For now, we'll warn but still allow the user to proceed
                # In the future, this could be made stricter based on user feedback

            # Check for Azure OpenAI endpoint guard-rail
            api_base = os.getenv("OPENAI_API_BASE", "")
            hostname = urlparse(api_base).hostname or ""
            if hostname.endswith("azure.com"):
                logger.warning(
                    "Web search is not currently supported or may be unreliable with Azure OpenAI endpoints and has been disabled."
                )
            else:
                web_tool_config: Dict[str, Any] = {
                    "type": "web_search_preview"
                }

                # Get user location from CLI args or config
                ws_country = args.get("ws_country")
                ws_city = args.get("ws_city")
                ws_region = args.get("ws_region")

                # Use config defaults if CLI args not provided
                if (
                    not any([ws_country, ws_city, ws_region])
                    and web_search_config.user_location
                ):
                    ws_country = web_search_config.user_location.country
                    ws_city = web_search_config.user_location.city
                    ws_region = web_search_config.user_location.region

                if ws_country or ws_city or ws_region:
                    user_location: Dict[str, Any] = {"type": "approximate"}
                    if ws_country:
                        user_location["country"] = ws_country
                    if ws_city:
                        user_location["city"] = ws_city
                    if ws_region:
                        user_location["region"] = ws_region
                    web_tool_config["user_location"] = user_location

                # Add ws_context_size if provided via CLI or config
                ws_context_size = (
                    args.get("ws_context_size")
                    or web_search_config.search_context_size
                )
                if ws_context_size:
                    web_tool_config["search_context_size"] = ws_context_size

                tools.append(web_tool_config)
                logger.debug(f"Web Search tool config: {web_tool_config}")

        # Debug log the final tools array
        logger.debug(f"Final tools array being passed to API: {tools}")

        # Check for two-pass sentinel mode
        ci_config = config.get_code_interpreter_config()
        effective_strategy = _get_effective_download_strategy(args, ci_config)
        if (
            effective_strategy == "two_pass_sentinel"
            and output_model
            and code_interpreter_info
        ):
            try:
                logger.debug(
                    "Using two-pass sentinel mode for Code Interpreter file downloads"
                )
                resp, downloaded_files = await _execute_two_pass_sentinel(
                    client,
                    args,
                    system_prompt,
                    user_prompt,
                    output_model,
                    tools,
                    log_callback,
                    ci_config,
                    code_interpreter_info,
                )
                response = resp
                # Store downloaded files info for later use
                if downloaded_files:
                    setattr(response, "_downloaded_files", downloaded_files)
            except Exception as e:
                logger.warning(
                    f"Two-pass execution failed, falling back to single-pass: {e}"
                )
                resp, _ = await _fallback_single_pass(
                    client,
                    args,
                    system_prompt,
                    user_prompt,
                    output_model,
                    tools,
                    log_callback,
                )
                response = resp
        else:
            # Create the response using the API (single-pass mode)
            logger.debug(f"Tools being passed to API: {tools}")
            response = await create_structured_output(
                client=client,
                model=args["model"],
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_model,
                output_file=args.get("output_file"),
                on_log=log_callback,
                tools=tools,
            )
        output_buffer.append(response)

        # Handle final output
        output_file = args.get("output_file")
        if output_file:
            with open(output_file, "w") as f:
                if len(output_buffer) == 1:
                    f.write(output_buffer[0].model_dump_json(indent=2))
                else:
                    # Build complete JSON array as a single string
                    json_output = "[\n"
                    for i, response in enumerate(output_buffer):
                        if i > 0:
                            json_output += ",\n"
                        json_output += "  " + response.model_dump_json(
                            indent=2
                        ).replace("\n", "\n  ")
                    json_output += "\n]"
                    f.write(json_output)
        else:
            # Write to stdout when no output file is specified
            if len(output_buffer) == 1:
                print(output_buffer[0].model_dump_json(indent=2))
            else:
                # Build complete JSON array as a single string
                json_output = "[\n"
                for i, response in enumerate(output_buffer):
                    if i > 0:
                        json_output += ",\n"
                    json_output += "  " + response.model_dump_json(
                        indent=2
                    ).replace("\n", "\n  ")
                json_output += "\n]"
                print(json_output)

        # Handle file downloads from Code Interpreter if any were generated
        if code_interpreter_info and output_buffer:
            try:
                # Get the API response from the last output item
                last_response = output_buffer[-1]
                if hasattr(last_response, "_api_response"):
                    api_response = getattr(last_response, "_api_response")
                    # Responses API has 'output' attribute, not 'messages'
                    if hasattr(api_response, "output"):
                        from .constants import DefaultPaths

                        download_dir = args.get(
                            "ci_download_dir",
                            DefaultPaths.CODE_INTERPRETER_OUTPUT_DIR,
                        )
                        manager = code_interpreter_info["manager"]

                        # Debug: Log response structure for Responses API
                        logger.debug(
                            f"Response has {len(api_response.output)} output items"
                        )
                        for i, item in enumerate(api_response.output):
                            logger.debug(f"Output item {i}: {type(item)}")
                            if hasattr(item, "type"):
                                logger.debug(f"  Type: {item.type}")
                            if hasattr(item, "content"):
                                content_str = (
                                    str(item.content)[:200] + "..."
                                    if len(str(item.content)) > 200
                                    else str(item.content)
                                )
                                logger.debug(
                                    f"  Content preview: {content_str}"
                                )
                            # Debug tool call outputs for file detection
                            if hasattr(item, "outputs"):
                                logger.debug(
                                    f"  Outputs: {len(item.outputs or [])} items"
                                )
                                for j, output in enumerate(item.outputs or []):
                                    logger.debug(
                                        f"    Output {j}: {type(output)}"
                                    )
                                    if hasattr(output, "type"):
                                        logger.debug(
                                            f"      Type: {output.type}"
                                        )
                                    if hasattr(output, "file_id"):
                                        logger.debug(
                                            f"      File ID: {output.file_id}"
                                        )
                                    if hasattr(output, "filename"):
                                        logger.debug(
                                            f"      Filename: {output.filename}"
                                        )

                        # Type ignore since we know this is a CodeInterpreterManager
                        downloaded_files = await manager.download_generated_files(  # type: ignore[attr-defined]
                            api_response, download_dir
                        )
                        if downloaded_files:
                            logger.info(
                                f"Downloaded {len(downloaded_files)} generated files to {download_dir}"
                            )
                            for file_path in downloaded_files:
                                logger.info(f"  - {file_path}")
                        else:
                            logger.debug(
                                "No files were downloaded from Code Interpreter"
                            )
                    else:
                        logger.debug("API response has no output attribute")
                else:
                    logger.debug(
                        "Last response has no _api_response attribute"
                    )
            except Exception as e:
                logger.warning(f"Failed to download generated files: {e}")

        return ExitCode.SUCCESS

    # Execute main operation
    try:
        result = await execute_main_operation()
        return result
    except (
        APIResponseError,
        EmptyResponseError,
        InvalidResponseFormatError,
    ) as e:
        logger.error("API error: %s", str(e))
        raise CLIError(str(e), exit_code=ExitCode.API_ERROR)
    except CLIError:
        # Re-raise CLIError types (like SchemaValidationError) without wrapping
        raise
    except Exception as e:
        logger.exception("Unexpected error during execution")
        raise CLIError(str(e), exit_code=ExitCode.UNKNOWN_ERROR)
    finally:
        # Clean up Code Interpreter files if requested
        if code_interpreter_info and args.get("ci_cleanup", True):
            try:
                manager = code_interpreter_info["manager"]
                # Type ignore since we know this is a CodeInterpreterManager
                await manager.cleanup_uploaded_files()  # type: ignore[attr-defined]
                logger.debug("Cleaned up Code Interpreter uploaded files")
            except Exception as e:
                logger.warning(
                    f"Failed to clean up Code Interpreter files: {e}"
                )

        # Clean up File Search resources if requested
        if file_search_info and args.get("fs_cleanup", True):
            try:
                manager = file_search_info["manager"]
                # Type ignore since we know this is a FileSearchManager
                await manager.cleanup_resources()  # type: ignore[attr-defined]
                logger.debug("Cleaned up File Search vector stores and files")
            except Exception as e:
                logger.warning(
                    f"Failed to clean up File Search resources: {e}"
                )

        # Clean up service container
        try:
            await services.cleanup()
            logger.debug("Cleaned up service container")
        except Exception as e:
            logger.warning(f"Failed to clean up service container: {e}")

        await client.close()


async def run_cli_async(args: CLIParams) -> ExitCode:
    """Async wrapper for CLI operations.

    Args:
        args: CLI parameters.

    Returns:
        Exit code.

    Raises:
        CLIError: For errors during CLI operations.
    """
    try:
        # 0. Configure Debug Logging
        from .template_debug import configure_debug_logging

        configure_debug_logging(
            verbose=bool(args.get("verbose", False)),
            debug=bool(args.get("debug", False)),
        )

        # 0a. Help Debug Request is now handled by callback in click_options.py

        # 0. Configure Progress Reporting
        configure_progress_reporter(
            verbose=args.get("verbose", False),
            progress=args.get("progress", "basic"),
        )
        progress_reporter = get_progress_reporter()

        # 0. Model Parameter Validation
        progress_reporter.report_phase("Validating configuration", "🔧")
        logger.debug("=== Model Parameter Validation ===")
        # Import here to avoid circular dependency
        from .model_validation import validate_model_params

        params = await validate_model_params(args)

        # 1. Input Validation Phase (includes schema validation)
        progress_reporter.report_phase("Processing input files", "📂")
        # Import here to avoid circular dependency
        from .validators import validate_inputs

        (
            security_manager,
            task_template,
            schema,
            template_context,
            env,
            template_path,
        ) = await validate_inputs(args)

        # Report file routing decisions
        routing_result = args.get("_routing_result")
        if routing_result is not None and not isinstance(
            routing_result, ProcessingResult
        ):
            routing_result = None  # Invalid type, treat as None
        routing_result_typed: Optional[ProcessingResult] = routing_result
        if routing_result_typed:
            template_files = routing_result_typed.validated_files.get(
                "template", []
            )
            container_files = routing_result_typed.validated_files.get(
                "code-interpreter", []
            )
            vector_files = routing_result_typed.validated_files.get(
                "file-search", []
            )
            progress_reporter.report_file_routing(
                template_files, container_files, vector_files
            )

        # 2. Template Processing Phase
        progress_reporter.report_phase("Rendering template", "📝")
        system_prompt, user_prompt = await process_templates(
            args, task_template, template_context, env, template_path or ""
        )

        # 3. Model & Schema Validation Phase
        progress_reporter.report_phase("Validating model and schema", "✅")
        # Import here to avoid circular dependency
        from .model_validation import validate_model_and_schema

        (
            output_model,
            messages,
            total_tokens,
            registry,
        ) = await validate_model_and_schema(
            args,
            schema,
            system_prompt,
            user_prompt,
            template_context,
        )

        # Report validation results
        if registry is not None:
            capabilities = registry.get_capabilities(args["model"])
            progress_reporter.report_validation_results(
                schema_valid=True,  # If we got here, schema is valid
                template_valid=True,  # If we got here, template is valid
                token_count=total_tokens,
                token_limit=capabilities.context_window,
            )
        else:
            # Fallback for test environments where registry might be None
            progress_reporter.report_validation_results(
                schema_valid=True,  # If we got here, schema is valid
                template_valid=True,  # If we got here, template is valid
                token_count=total_tokens,
                token_limit=128000,  # Default fallback
            )

        # 4. Dry Run Output Phase - Moved after all validations
        if args.get("dry_run", False):
            report_success(
                "Dry run completed successfully - all validations passed"
            )

            # Calculate cost estimate
            if registry is not None:
                capabilities = registry.get_capabilities(args["model"])
                estimated_cost = calculate_cost_estimate(
                    model=args["model"],
                    input_tokens=total_tokens,
                    output_tokens=capabilities.max_output_tokens,
                    registry=registry,
                )

                # Enhanced dry-run output with cost estimation
                cost_breakdown = format_cost_breakdown(
                    model=args["model"],
                    input_tokens=total_tokens,
                    output_tokens=capabilities.max_output_tokens,
                    total_cost=estimated_cost,
                    context_window=capabilities.context_window,
                )
            else:
                # Fallback for test environments
                cost_breakdown = f"Token Analysis\nModel: {args['model']}\nInput tokens: {total_tokens}\nRegistry not available in test environment"
            print(cost_breakdown)

            # Show template content based on debug flags
            from .template_debug import show_template_content

            show_template_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                debug=bool(args.get("debug", False)),
            )

            # Legacy verbose support for backward compatibility
            from .template_debug import TDCap, is_capacity_active

            if (
                args.get("verbose", False)
                and not args.get("debug", False)
                and not is_capacity_active(TDCap.POST_EXPAND)
            ):
                logger.info("\nSystem Prompt:")
                logger.info("-" * 40)
                logger.info(system_prompt)
                logger.info("\nRendered Template:")
                logger.info("-" * 40)
                logger.info(user_prompt)

            # Return success only if we got here (no validation errors)
            return ExitCode.SUCCESS

        # 5. Execution Phase
        progress_reporter.report_phase("Generating response", "🤖")
        return await execute_model(
            args, params, output_model, system_prompt, user_prompt
        )

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        raise
    except SchemaValidationError as e:
        # Ensure schema validation errors are properly propagated with the correct exit code
        logger.error("Schema validation error: %s", str(e))
        raise  # Re-raise the SchemaValidationError to preserve the error chain
    except Exception as e:
        if isinstance(e, CLIError):
            raise  # Let our custom errors propagate
        logger.exception("Unexpected error")
        raise CLIError(str(e), context={"error_type": type(e).__name__})


class OstructRunner:
    """Clean interface for running ostruct operations.

    This class encapsulates the execution logic and provides a clean,
    testable interface for running ostruct operations.
    """

    def __init__(self, args: CLIParams):
        """Initialize the runner with CLI parameters.

        Args:
            args: CLI parameters dictionary
        """
        self.args = args

    async def run(self) -> ExitCode:
        """Main execution entry point.

        Returns:
            Exit code indicating success or failure

        Raises:
            CLIError: For errors during CLI operations
        """
        return await run_cli_async(self.args)

    async def validate_only(self) -> ExitCode:
        """Run validation without executing the model.

        This runs all validation phases and returns without making
        API calls. Useful for dry runs and validation testing.

        Returns:
            Exit code indicating validation success or failure
        """
        # Create a copy of args with dry_run enabled
        validation_args = dict(self.args)
        validation_args["dry_run"] = True
        return await run_cli_async(validation_args)  # type: ignore[arg-type]

    async def execute_with_validation(self) -> ExitCode:
        """Run with full validation and execution.

        This is the standard execution path that includes all
        validation phases followed by model execution.

        Returns:
            Exit code indicating success or failure
        """
        # Ensure dry_run is disabled for full execution
        execution_args = dict(self.args)
        execution_args["dry_run"] = False
        return await run_cli_async(execution_args)  # type: ignore[arg-type]

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration.

        Returns:
            Dictionary containing configuration information
        """
        # Check for new attachment system
        has_new_attachments = self._has_new_attachment_syntax()

        if has_new_attachments:
            attachment_summary = self._get_attachment_summary()
            return {
                "model": self.args.get("model"),
                "dry_run": self.args.get("dry_run", False),
                "verbose": self.args.get("verbose", False),
                "mcp_servers": len(self.args.get("mcp_servers", [])),
                "attachment_system": "new",
                "attachments": attachment_summary,
                "template_source": (
                    "file" if self.args.get("task_file") else "string"
                ),
                "schema_source": (
                    "file" if self.args.get("schema_file") else "inline"
                ),
            }
        else:
            # Legacy configuration summary
            return {
                "model": self.args.get("model"),
                "dry_run": self.args.get("dry_run", False),
                "verbose": self.args.get("verbose", False),
                "mcp_servers": len(self.args.get("mcp_servers", [])),
                "attachment_system": "legacy",
                "code_interpreter_enabled": bool(
                    self.args.get("code_interpreter_files")
                    or self.args.get("code_interpreter_dirs")
                ),
                "file_search_enabled": bool(
                    self.args.get("file_search_files")
                    or self.args.get("file_search_dirs")
                ),
                "template_source": (
                    "file" if self.args.get("task_file") else "string"
                ),
                "schema_source": (
                    "file" if self.args.get("schema_file") else "inline"
                ),
            }

    def _has_new_attachment_syntax(self) -> bool:
        """Check if CLI args contain new attachment syntax.

        Returns:
            True if new attachment syntax is present
        """
        new_syntax_keys = ["attaches", "dirs", "collects"]
        return any(self.args.get(key) for key in new_syntax_keys)

    def _get_attachment_summary(self) -> Dict[str, Any]:
        """Get summary of new-style attachments.

        Returns:
            Dictionary containing attachment summary
        """
        total_attachments = 0
        targets_used = set()

        for key in ["attaches", "dirs", "collects"]:
            attachments = self.args.get(key, [])
            if isinstance(attachments, list):
                total_attachments += len(attachments)

                for attachment in attachments:
                    if isinstance(attachment, dict):
                        targets = attachment.get("targets", [])
                        if isinstance(targets, list):
                            targets_used.update(targets)

        # Helper function to safely get list length
        def safe_len(key: str) -> int:
            value = self.args.get(key, [])
            return len(value) if isinstance(value, list) else 0

        return {
            "total_attachments": total_attachments,
            "targets_used": list(targets_used),
            "attach_count": safe_len("attaches"),
            "dir_count": safe_len("dirs"),
            "collect_count": safe_len("collects"),
        }
