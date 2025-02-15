"""Token estimation utilities."""

from typing import Any, Dict, List, Union

import tiktoken


def estimate_tokens_with_encoding(
    messages: Union[str, Dict[str, str], List[Dict[str, str]]],
    model: str,
    encoder: Any = None,
) -> int:
    """Estimate the number of tokens in a chat completion.

    Args:
        messages: Message content - can be string, single message dict, or list of messages
        model: Model name
        encoder: Optional tiktoken encoder for testing

    Returns:
        int: Estimated token count
    """
    if encoder is None:
        # Use o200k_base for gpt-4o and o1 models
        if model.startswith(("gpt-4o", "o1", "o3")):
            encoder = tiktoken.get_encoding("o200k_base")
        else:
            encoder = tiktoken.get_encoding("cl100k_base")

    if isinstance(messages, str):
        return len(encoder.encode(messages))
    elif isinstance(messages, dict):
        return len(encoder.encode(str(messages.get("content", ""))))
    else:
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # message overhead
            for key, value in message.items():
                num_tokens += len(encoder.encode(str(value)))
                if key == "name":
                    num_tokens -= 1  # role is omitted
        num_tokens += 2  # reply priming
        return num_tokens
