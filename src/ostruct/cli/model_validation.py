"""Model validation utilities for ostruct CLI."""

import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from openai_model_registry import (
    ModelNotSupportedError,
    ModelRegistry,
    ParameterNotSupportedError,
    ParameterValidationError,
)
from pydantic import BaseModel

from .errors import (
    CLIError,
    InvalidJSONError,
    ModelCreationError,
    SchemaFileError,
    SchemaValidationError,
    UserDataNotSupportedError,
)
from .exit_codes import ExitCode
from .file_info import FileRoutingIntent
from .model_creation import create_dynamic_model
from .schema_utils import supports_structured_output
from .token_validation import validate_token_limits
from .types import CLIParams

logger = logging.getLogger(__name__)


def validate_user_data_support(model: str, has_user_data_files: bool) -> None:
    """Validate that the model supports user-data files if they are present.

    Args:
        model: The model name to validate
        has_user_data_files: Whether user-data files are being used

    Raises:
        UserDataNotSupportedError: If user-data files are used with non-vision model
    """
    if not has_user_data_files:
        return

    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)

        # Check if model has vision capability
        # If the vision attribute is missing from the registry, be optimistic
        # and let the API validate the capability
        if hasattr(capabilities, "vision"):
            vision_supported = capabilities.vision
            if (
                vision_supported is False
            ):  # Explicitly False (not None or missing)
                raise UserDataNotSupportedError(
                    f"Model '{model}' does not support user-data files. "
                    f"User-data files require a vision-enabled model.",
                    model_id=model,
                )
            logger.debug(
                f"Model '{model}' supports user-data files (vision: {vision_supported})"
            )
        else:
            # Vision capability not defined in registry - be optimistic
            logger.debug(
                f"Model '{model}' vision capability not defined in registry. "
                f"Assuming support - API will validate if needed."
            )

    except ModelNotSupportedError:
        # If model not in registry, fall back to optimistic approach
        # Let the API call fail with appropriate error
        logger.warning(
            f"Model '{model}' not found in registry. "
            f"User-data support validation skipped - will be validated by API."
        )
    except Exception as e:
        # For other errors, log warning but don't fail
        logger.warning(
            f"Could not validate user-data support for model '{model}': {e}. "
            f"Validation will be performed by the API."
        )


def validate_model_parameters(model: str, params: Dict[str, Any]) -> None:
    """Validate model parameters against model capabilities.

    Args:
        model: The model name to validate parameters for
        params: Dictionary of parameter names and values to validate

    Raises:
        CLIError: If parameters are invalid for the model
    """
    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)

        # Validate each parameter
        for param_name, value in params.items():
            try:
                capabilities.validate_parameter(param_name, value)
            except ParameterNotSupportedError as e:
                raise CLIError(
                    f"Parameter '{param_name}' not supported for model '{model}': {e}",
                    exit_code=ExitCode.VALIDATION_ERROR,
                ) from e
            except ParameterValidationError as e:
                raise CLIError(
                    f"Invalid value for parameter '{param_name}' on model '{model}': {e}",
                    exit_code=ExitCode.VALIDATION_ERROR,
                ) from e

    except ModelNotSupportedError as e:
        raise CLIError(
            f"Model '{model}' is not supported: {e}",
            exit_code=ExitCode.VALIDATION_ERROR,
        ) from e
    except Exception as e:
        logger.warning(
            f"Could not validate parameters for model '{model}': {e}"
        )
        # Don't fail for unexpected validation errors


async def validate_model_params(args: CLIParams) -> Dict[str, Any]:
    """Validate model parameters and return a dictionary of valid parameters.

    Args:
        args: Command line arguments

    Returns:
        Dictionary of validated model parameters

    Raises:
        CLIError: If model parameters are invalid
    """
    params = {
        "temperature": args.get("temperature"),
        "max_output_tokens": args.get("max_output_tokens"),
        "top_p": args.get("top_p"),
        "frequency_penalty": args.get("frequency_penalty"),
        "presence_penalty": args.get("presence_penalty"),
        "reasoning_effort": args.get("reasoning_effort"),
    }
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    validate_model_parameters(args["model"], params)
    return params


async def validate_model_and_schema(
    args: CLIParams,
    schema: Dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    template_context: Dict[str, Any],
) -> Tuple[
    Type[BaseModel], List[Dict[str, str]], int, Optional[ModelRegistry]
]:
    """Validate model compatibility and schema, and check token limits.

    Args:
        args: Command line arguments
        schema: Schema dictionary
        system_prompt: Processed system prompt
        user_prompt: Processed user prompt
        template_context: Template context with file information

    Returns:
        Tuple of (output_model, messages, total_tokens, registry)

    Raises:
        CLIError: For validation errors
        ModelCreationError: When model creation fails
        SchemaValidationError: When schema is invalid
        PromptTooLargeError: When prompt exceeds context window with actionable guidance
    """
    logger.debug("=== Model & Schema Validation Phase ===")
    try:
        output_model = create_dynamic_model(
            schema,
            show_schema=args.get("show_model_schema", False),
            debug_validation=args.get("debug_validation", False),
        )
        logger.debug("Successfully created output model")
    except (
        SchemaFileError,
        InvalidJSONError,
        SchemaValidationError,
        ModelCreationError,
    ) as e:
        logger.error("Schema error: %s", str(e))
        # Pass through the error without additional wrapping
        raise

    if not supports_structured_output(args["model"]):
        msg = f"Model {args['model']} does not support structured output"
        logger.error(msg)
        raise ModelNotSupportedError(msg)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Token validation - only count files with TEMPLATE_ONLY routing intent
    # Also check for user-data files to validate model compatibility
    files = template_context.get("files", [])
    template_files = []
    has_user_data_files = False

    for file_info in files:
        routing_intent = getattr(file_info, "routing_intent", None)
        if routing_intent == FileRoutingIntent.TEMPLATE_ONLY:
            template_files.append(str(file_info.path))
        elif routing_intent == FileRoutingIntent.USER_DATA:
            has_user_data_files = True
        # Tool files (FILE_SEARCH, CODE_INTERPRETER) are ignored for token validation

    # Validate user-data support if user-data files are present
    validate_user_data_support(args["model"], has_user_data_files)

    combined_template_content = system_prompt + user_prompt
    validate_token_limits(
        combined_template_content, template_files, args["model"]
    )

    # For now, simplified token counting - the full implementation needs more imports
    total_tokens = len(system_prompt) + len(user_prompt)  # Rough estimate
    registry = ModelRegistry.get_instance()

    return output_model, messages, total_tokens, registry


def supports_web_search(model: str) -> bool:
    """Check if model supports web search capabilities.

    Args:
        model: The model name to check

    Returns:
        True if the model supports web search, False otherwise
    """
    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)
        return getattr(capabilities, "supports_web_search", False)
    except Exception:
        # Default to False for safety if we can't determine support
        return False


def validate_web_search_compatibility(
    model: str, web_search_enabled: bool
) -> Optional[str]:
    """Validate web search compatibility and return warning message if needed.

    Args:
        model: The model name to validate
        web_search_enabled: Whether web search is enabled

    Returns:
        Warning message if there's a compatibility issue, None otherwise
    """
    if not web_search_enabled:
        return None

    if not supports_web_search(model):
        return (
            f"Model '{model}' does not support web search capabilities. "
            f"Consider using a compatible model like 'gpt-4o', 'gpt-4.1', or an O-series model."
        )

    return None
