"""Async execution engine for ostruct CLI operations."""

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Type, Union

from openai import AsyncOpenAI, OpenAIError
from openai_model_registry import ModelRegistry
from pydantic import BaseModel

from .code_interpreter import CodeInterpreterManager
from .config import OstructConfig
from .cost_estimation import calculate_cost_estimate, format_cost_breakdown
from .errors import (
    APIErrorMapper,
    CLIError,
    SchemaValidationError,
    StreamInterruptedError,
    StreamParseError,
)
from .exit_codes import ExitCode
from .explicit_file_processor import ProcessingResult
from .file_search import FileSearchManager
from .mcp_integration import MCPConfiguration, MCPServerManager
from .progress_reporting import (
    configure_progress_reporter,
    get_progress_reporter,
    report_success,
)
from .serialization import LogSerializer
from .services import ServiceContainer
from .types import CLIParams
from .unattended_operation import (
    UnattendedOperationManager,
)


# Error classes for streaming operations (duplicated from cli.py for now)
class APIResponseError(Exception):
    pass


class EmptyResponseError(Exception):
    pass


class InvalidResponseFormatError(Exception):
    pass


class StreamBufferError(Exception):
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

    # Create Code Interpreter manager
    manager = CodeInterpreterManager(client)

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
        vector_store_name = args.get(
            "file_search_vector_store_name", "ostruct_search"
        )
        retry_count = args.get("file_search_retry_count", 3)
        timeout = args.get("file_search_timeout", 60.0)

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


async def stream_structured_output(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    output_schema: Type[BaseModel],
    output_file: Optional[str] = None,
    tools: Optional[List[dict]] = None,
    **kwargs: Any,
) -> AsyncGenerator[BaseModel, None]:
    """Stream structured output from OpenAI API using Responses API.

    This function uses the OpenAI Responses API with strict mode schema validation
    to generate structured output that matches the provided Pydantic model.

    Args:
        client: The OpenAI client to use
        model: The model to use
        system_prompt: The system prompt to use
        user_prompt: The user prompt to use
        output_schema: The Pydantic model to validate responses against
        output_file: Optional file to write output to
        tools: Optional list of tools (e.g., MCP, Code Interpreter) to include
        **kwargs: Additional parameters to pass to the API

    Returns:
        An async generator yielding validated model instances

    Raises:
        ValueError: If the model does not support structured output or parameters are invalid
        StreamInterruptedError: If the stream is interrupted
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
        stream_kwargs = {}
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)

        # Validate and include supported parameters
        for param_name, value in kwargs.items():
            if param_name in capabilities.supported_parameters:
                # Validate the parameter value
                capabilities.validate_parameter(param_name, value)
                stream_kwargs[param_name] = value
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
            "stream": True,
            **stream_kwargs,
        }

        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            logger.debug("Tools: %s", json.dumps(tools, indent=2))

        # Log the API request details
        logger.debug("Making OpenAI Responses API request with:")
        logger.debug("Model: %s", model)
        logger.debug("Combined prompt: %s", combined_prompt)
        logger.debug("Parameters: %s", json.dumps(stream_kwargs, indent=2))
        logger.debug("Schema: %s", json.dumps(strict_schema, indent=2))
        logger.debug("Tools being passed to API: %s", tools)
        logger.debug(
            "Complete API params: %s",
            json.dumps(api_params, indent=2, default=str),
        )

        # Use the Responses API with streaming
        response = await client.responses.create(**api_params)

        # Process streaming response
        accumulated_content = ""
        async for chunk in response:
            if on_log:
                on_log(logging.DEBUG, f"Received chunk: {chunk}", {})

            # Check for tool calls (including web search)
            if hasattr(chunk, "choices") and chunk.choices:
                choice = chunk.choices[0]
                # Log tool calls if present
                if (
                    hasattr(choice, "delta")
                    and hasattr(choice.delta, "tool_calls")
                    and choice.delta.tool_calls
                ):
                    for tool_call in choice.delta.tool_calls:
                        if (
                            hasattr(tool_call, "type")
                            and tool_call.type == "web_search_preview"
                        ):
                            tool_id = getattr(tool_call, "id", "unknown")
                            logger.debug(
                                f"Web search tool invoked (id={tool_id})"
                            )
                        elif hasattr(tool_call, "function") and hasattr(
                            tool_call.function, "name"
                        ):
                            # Handle other tool types for completeness
                            tool_name = tool_call.function.name
                            tool_id = getattr(tool_call, "id", "unknown")
                            logger.debug(
                                f"Tool '{tool_name}' invoked (id={tool_id})"
                            )

            # Handle different response formats based on the chunk structure
            content_added = False

            # Try different possible response formats
            if hasattr(chunk, "choices") and chunk.choices:
                # Standard chat completion format
                choice = chunk.choices[0]
                if (
                    hasattr(choice, "delta")
                    and hasattr(choice.delta, "content")
                    and choice.delta.content
                ):
                    accumulated_content += choice.delta.content
                    content_added = True
                elif (
                    hasattr(choice, "message")
                    and hasattr(choice.message, "content")
                    and choice.message.content
                ):
                    accumulated_content += choice.message.content
                    content_added = True
            elif hasattr(chunk, "response") and hasattr(
                chunk.response, "body"
            ):
                # Responses API format
                accumulated_content += chunk.response.body
                content_added = True
            elif hasattr(chunk, "content"):
                # Direct content
                accumulated_content += chunk.content
                content_added = True
            elif hasattr(chunk, "text"):
                # Text content
                accumulated_content += chunk.text
                content_added = True

            if on_log and content_added:
                on_log(
                    logging.DEBUG,
                    f"Added content, total length: {len(accumulated_content)}",
                    {},
                )

            # Try to parse and validate accumulated content as complete JSON
            try:
                if accumulated_content.strip():
                    # Attempt to parse as complete JSON
                    data = json.loads(accumulated_content.strip())
                    validated = output_schema.model_validate(data)
                    yield validated
                    # Reset for next complete response (if any)
                    accumulated_content = ""
            except (json.JSONDecodeError, ValueError):
                # Not yet complete JSON, continue accumulating
                continue

        # Handle any remaining content
        if accumulated_content.strip():
            try:
                data = json.loads(accumulated_content.strip())
                validated = output_schema.model_validate(data)
                yield validated
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse final accumulated content: {e}")
                raise StreamParseError(
                    f"Failed to parse response as valid JSON: {e}"
                )

    except Exception as e:
        # Map OpenAI errors using the error mapper

        if isinstance(e, OpenAIError):
            mapped_error = APIErrorMapper.map_openai_error(e)
            logger.error(f"OpenAI API error mapped: {mapped_error}")
            raise mapped_error

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
    finally:
        # Note: We don't close the client here as it may be reused
        # The caller is responsible for client lifecycle management
        pass


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


async def execute_model(
    args: CLIParams,
    params: Dict[str, Any],
    output_model: Type[BaseModel],
    system_prompt: str,
    user_prompt: str,
) -> ExitCode:
    """Execute the model and handle the response.

    Args:
        args: Command line arguments
        params: Validated model parameters
        output_model: Generated Pydantic model
        system_prompt: Processed system prompt
        user_prompt: Processed user prompt

    Returns:
        Exit code indicating success or failure

    Raises:
        CLIError: For execution errors
        UnattendedOperationTimeoutError: For operation timeouts
    """
    logger.debug("=== Execution Phase ===")

    # Initialize unattended operation manager
    timeout_seconds = int(args.get("timeout", 3600))
    operation_manager = UnattendedOperationManager(timeout_seconds)

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
        msg = "No API key provided. Set OPENAI_API_KEY environment variable or use --api-key"
        logger.error(msg)
        raise CLIError(msg, exit_code=ExitCode.API_ERROR)

    client = AsyncOpenAI(
        api_key=api_key, timeout=min(args.get("timeout", 60.0), 300.0)
    )  # Cap at 5 min for client timeout

    # Create service container for dependency management
    services = ServiceContainer(client, args)

    # Initialize variables that will be used in nested functions
    code_interpreter_info = None
    file_search_info = None

    # Create detailed log callback
    def log_callback(level: int, message: str, extra: dict[str, Any]) -> None:
        if args.get("debug_openai_stream", False):
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

        # Process MCP configuration if provided
        if services.is_configured("mcp"):
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
        if (
            routing_result_typed
            and "code-interpreter" in routing_result_typed.enabled_tools
        ):
            code_interpreter_files = routing_result_typed.validated_files.get(
                "code-interpreter", []
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
                code_interpreter_manager = (
                    await ci_services.get_code_interpreter_manager()
                )
                if code_interpreter_manager:
                    # Get the uploaded file IDs from the manager
                    if (
                        hasattr(code_interpreter_manager, "uploaded_file_ids")
                        and code_interpreter_manager.uploaded_file_ids
                    ):
                        file_ids = code_interpreter_manager.uploaded_file_ids
                        # Cast to concrete CodeInterpreterManager to access build_tool_config
                        concrete_ci_manager = code_interpreter_manager
                        if hasattr(concrete_ci_manager, "build_tool_config"):
                            ci_tool_config = (
                                concrete_ci_manager.build_tool_config(file_ids)
                            )
                            logger.debug(
                                f"Code Interpreter tool config: {ci_tool_config}"
                            )
                            code_interpreter_info = {
                                "manager": code_interpreter_manager,
                                "tool_config": ci_tool_config,
                            }
                            tools.append(ci_tool_config)
                    else:
                        logger.warning(
                            "Code Interpreter manager has no uploaded file IDs"
                        )

        # Process File Search configuration if enabled
        if (
            routing_result_typed
            and "file-search" in routing_result_typed.enabled_tools
        ):
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
                fs_args["file_search"] = True  # Enable for service container

                # Create temporary service container with updated args
                fs_services = ServiceContainer(client, fs_args)  # type: ignore[arg-type]
                file_search_manager = (
                    await fs_services.get_file_search_manager()
                )
                if file_search_manager:
                    # Get the vector store ID from the manager's created vector stores
                    # The most recent one should be the one we need
                    if (
                        hasattr(file_search_manager, "created_vector_stores")
                        and file_search_manager.created_vector_stores
                    ):
                        vector_store_id = (
                            file_search_manager.created_vector_stores[-1]
                        )
                        # Cast to concrete FileSearchManager to access build_tool_config
                        concrete_fs_manager = file_search_manager
                        if hasattr(concrete_fs_manager, "build_tool_config"):
                            fs_tool_config = (
                                concrete_fs_manager.build_tool_config(
                                    vector_store_id
                                )
                            )
                            logger.debug(
                                f"File Search tool config: {fs_tool_config}"
                            )
                            file_search_info = {
                                "manager": file_search_manager,
                                "tool_config": fs_tool_config,
                            }
                            tools.append(fs_tool_config)
                    else:
                        logger.warning(
                            "File Search manager has no created vector stores"
                        )

        # Process Web Search configuration if enabled
        # Check CLI flags first, then fall back to config defaults
        web_search_from_cli = args.get("web_search", False)
        no_web_search_from_cli = args.get("no_web_search", False)

        # Load configuration to check defaults
        from typing import cast

        config_path = cast(Union[str, Path, None], args.get("config"))
        config = OstructConfig.load(config_path)
        web_search_config = config.get_web_search_config()

        # Determine if web search should be enabled
        web_search_enabled = False
        if web_search_from_cli:
            # Explicit --web-search flag takes precedence
            web_search_enabled = True
        elif no_web_search_from_cli:
            # Explicit --no-web-search flag disables
            web_search_enabled = False
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
            if "azure.com" in api_base.lower():
                logger.warning(
                    "Web search is not currently supported or may be unreliable with Azure OpenAI endpoints and has been disabled."
                )
            else:
                web_tool_config: Dict[str, Any] = {
                    "type": "web_search_preview"
                }

                # Add user_location if provided via CLI or config
                user_country = args.get("user_country")
                user_city = args.get("user_city")
                user_region = args.get("user_region")

                # Fall back to config if not provided via CLI
                if (
                    not any([user_country, user_city, user_region])
                    and web_search_config.user_location
                ):
                    user_country = web_search_config.user_location.country
                    user_city = web_search_config.user_location.city
                    user_region = web_search_config.user_location.region

                if user_country or user_city or user_region:
                    user_location: Dict[str, Any] = {"type": "approximate"}
                    if user_country:
                        user_location["country"] = user_country
                    if user_city:
                        user_location["city"] = user_city
                    if user_region:
                        user_location["region"] = user_region

                    web_tool_config["user_location"] = user_location

                # Add search_context_size if provided via CLI or config
                search_context_size = (
                    args.get("search_context_size")
                    or web_search_config.search_context_size
                )
                if search_context_size:
                    web_tool_config["search_context_size"] = (
                        search_context_size
                    )

                tools.append(web_tool_config)
                logger.debug(f"Web Search tool config: {web_tool_config}")

        # Debug log the final tools array
        logger.debug(f"Final tools array being passed to API: {tools}")

        # Stream the response
        logger.debug(f"Tools being passed to API: {tools}")
        async for response in stream_structured_output(
            client=client,
            model=args["model"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_model,
            output_file=args.get("output_file"),
            on_log=log_callback,
            tools=tools,
        ):
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
        if (
            code_interpreter_info
            and hasattr(response, "file_ids")
            and response.file_ids
        ):
            try:
                download_dir = args.get(
                    "code_interpreter_download_dir", "./downloads"
                )
                manager = code_interpreter_info["manager"]
                # Type ignore since we know this is a CodeInterpreterManager
                downloaded_files = await manager.download_generated_files(  # type: ignore[attr-defined]
                    response.file_ids, download_dir
                )
                if downloaded_files:
                    logger.info(
                        f"Downloaded {len(downloaded_files)} generated files to {download_dir}"
                    )
                    for file_path in downloaded_files:
                        logger.info(f"  - {file_path}")
            except Exception as e:
                logger.warning(f"Failed to download generated files: {e}")

        return ExitCode.SUCCESS

    # Execute main operation with timeout safeguards
    try:
        result = await operation_manager.execute_with_safeguards(
            execute_main_operation, "model execution"
        )
        # The result should be an ExitCode from execute_main_operation
        return result  # type: ignore[no-any-return]
    except (
        StreamInterruptedError,
        StreamBufferError,
        StreamParseError,
        APIResponseError,
        EmptyResponseError,
        InvalidResponseFormatError,
    ) as e:
        logger.error("Stream error: %s", str(e))
        raise CLIError(str(e), exit_code=ExitCode.API_ERROR)
    except Exception as e:
        logger.exception("Unexpected error during streaming")
        raise CLIError(str(e), exit_code=ExitCode.UNKNOWN_ERROR)
    finally:
        # Clean up Code Interpreter files if requested
        if code_interpreter_info and args.get(
            "code_interpreter_cleanup", True
        ):
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
        if file_search_info and args.get("file_search_cleanup", True):
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
            debug=bool(args.get("debug", False))
            or bool(args.get("debug_templates", False)),
        )

        # 0a. Handle Debug Help Request
        if args.get("help_debug", False):
            from .template_debug_help import show_template_debug_help

            show_template_debug_help()
            return ExitCode.SUCCESS

        # 0. Configure Progress Reporting
        configure_progress_reporter(
            verbose=args.get("verbose", False),
            progress_level=args.get("progress_level", "basic"),
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

        # 3a. Web Search Compatibility Validation
        if args.get("web_search", False) and not args.get(
            "no_web_search", False
        ):
            from .model_validation import validate_web_search_compatibility

            compatibility_warning = validate_web_search_compatibility(
                args["model"], True
            )
            if compatibility_warning:
                logger.warning(compatibility_warning)
                # For production usage, consider making this an error instead of warning
                # raise CLIError(compatibility_warning, exit_code=ExitCode.VALIDATION_ERROR)

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
                show_templates=bool(args.get("show_templates", False)),
                debug=bool(args.get("debug", False))
                or bool(args.get("debug_templates", False)),
            )

            # Legacy verbose support for backward compatibility
            if (
                args.get("verbose", False)
                and not args.get("debug", False)
                and not args.get("show_templates", False)
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
        return {
            "model": self.args.get("model"),
            "dry_run": self.args.get("dry_run", False),
            "verbose": self.args.get("verbose", False),
            "mcp_servers": len(self.args.get("mcp_servers", [])),
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
