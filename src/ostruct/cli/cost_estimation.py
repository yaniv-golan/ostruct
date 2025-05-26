"""Cost estimation functionality for ostruct CLI.

This module provides functionality to estimate the cost of API calls
before making them, helping users plan their usage and budget.
"""

from typing import Optional

from openai_model_registry import ModelRegistry

# Static pricing mapping for major models (per 1K tokens)
# These should be updated periodically or fetched from an external source
MODEL_PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o-2024-05-13": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini-2024-07-18": {"input": 0.00015, "output": 0.0006},
    "o1": {"input": 0.015, "output": 0.06},
    "o1-mini": {"input": 0.003, "output": 0.012},
    "o1-2024-12-17": {"input": 0.015, "output": 0.06},
    "o1-mini-2024-09-12": {"input": 0.003, "output": 0.012},
    "o3": {"input": 0.015, "output": 0.06},  # Estimated
    "o3-mini": {"input": 0.003, "output": 0.012},  # Estimated
    "o4-mini": {"input": 0.003, "output": 0.012},  # Estimated
    "gpt-4.1": {"input": 0.0025, "output": 0.01},  # Estimated
    "gpt-4.1-mini": {"input": 0.00015, "output": 0.0006},  # Estimated
    "gpt-4.1-nano": {"input": 0.00015, "output": 0.0006},  # Estimated
    "gpt-4.5-preview": {"input": 0.0025, "output": 0.01},  # Estimated
}


def calculate_cost_estimate(
    model: str,
    input_tokens: int,
    output_tokens: Optional[int] = None,
    registry: Optional[ModelRegistry] = None,
) -> float:
    """Calculate estimated cost for API call.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens (if None, uses max for model)
        registry: ModelRegistry instance (if None, creates new one)

    Returns:
        Estimated cost in USD
    """
    if registry is None:
        registry = ModelRegistry.get_instance()

    # Get output tokens if not specified
    if output_tokens is None:
        try:
            capabilities = registry.get_capabilities(model)
            output_tokens = capabilities.max_output_tokens
        except Exception:
            # Fallback if model capabilities not available
            output_tokens = 4096

    # Get pricing for model
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        # Try to find pricing for base model name
        base_model = model.split("-")[
            0
        ]  # e.g., "gpt-4o" from "gpt-4o-2024-05-13"
        pricing = MODEL_PRICING.get(base_model)

        if pricing is None:
            # Use default pricing as fallback
            pricing = {"input": 0.0025, "output": 0.01}

    # Calculate cost (pricing is per 1K tokens)
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]

    return input_cost + output_cost


def format_cost_breakdown(
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_cost: float,
    context_window: int,
) -> str:
    """Format cost breakdown for display.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        total_cost: Total estimated cost
        context_window: Model's context window

    Returns:
        Formatted cost breakdown string
    """
    lines = [
        "📊 Token Analysis:",
        f"   • Input tokens: {input_tokens:,}",
        f"   • Max output tokens: {output_tokens:,}",
        f"   • Context window: {context_window:,}",
        f"   • Estimated cost: ${total_cost:.4f} (using {model} rates)",
    ]

    # Add utilization percentage
    total_tokens = input_tokens + output_tokens
    utilization = (total_tokens / context_window) * 100
    lines.append(f"   • Context utilization: {utilization:.1f}%")

    return "\n".join(lines)


def check_cost_limits(
    estimated_cost: float, max_cost_per_run: Optional[float] = None
) -> Optional[str]:
    """Check if estimated cost exceeds configured limits.

    Args:
        estimated_cost: Estimated cost in USD
        max_cost_per_run: Maximum allowed cost per run

    Returns:
        Warning message if cost exceeds limits, None otherwise
    """
    if max_cost_per_run is not None and estimated_cost > max_cost_per_run:
        return (
            f"⚠️ Estimated cost (${estimated_cost:.4f}) exceeds configured "
            f"limit of ${max_cost_per_run:.4f}. Use --force to proceed anyway."
        )

    return None
