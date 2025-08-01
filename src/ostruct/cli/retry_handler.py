"""Retry logic with exponential backoff for download operations."""

import asyncio
import logging
import random
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    config: RetryConfig,
    *args: Any,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    **kwargs: Any,
) -> T:
    """Retry function with exponential backoff"""

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)

        except retryable_exceptions as e:
            last_exception = e

            if attempt == config.max_attempts - 1:
                # Last attempt failed
                break

            # Calculate delay
            delay = min(
                config.base_delay * (config.exponential_base**attempt),
                config.max_delay,
            )

            # Add jitter to prevent thundering herd
            if config.jitter:
                delay *= 0.5 + random.random() * 0.5

            logger.debug(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s"
            )
            await asyncio.sleep(delay)

    # All attempts failed
    if last_exception is not None:
        raise last_exception
    else:
        raise RuntimeError(
            "All retry attempts failed but no exception was captured"
        )


# Usage in download logic
async def download_with_retry(
    download_func: Callable[..., Awaitable[bytes]],
    file_id: str,
    container_id: str,
) -> bytes:
    """Download file with retry logic"""

    config = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0)

    import httpx

    return await retry_with_backoff(
        download_func,
        config,
        file_id,
        container_id,
        retryable_exceptions=(
            httpx.TimeoutException,
            httpx.RequestError,
            httpx.HTTPStatusError,  # Includes 429 rate limits
        ),
    )
