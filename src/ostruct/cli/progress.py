"""Progress reporting for CLI operations."""

import logging
from typing import Any, Optional, Type

logger = logging.getLogger(__name__)


class ProgressContext:
    """Simple context manager for output handling.

    This is a minimal implementation that just handles direct output to stdout.
    No progress reporting is implemented - it simply prints output directly.
    """

    def __init__(
        self,
        description: str = "Processing",
        total: Optional[int] = None,
        level: str = "basic",
        output_file: Optional[str] = None,
    ):
        logger.debug(
            "Initializing ProgressContext with level=%s, output_file=%s",
            level,
            output_file,
        )
        logger.debug("Description: %s, total: %s", description, total)
        self._output_file = output_file
        self._level = level
        self.enabled = level != "none"
        self.current: int = 0
        logger.debug(
            "ProgressContext initialized with enabled=%s", self.enabled
        )

    def __enter__(self) -> "ProgressContext":
        logger.debug("Entering ProgressContext with level=%s", self._level)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        logger.debug(
            "Exiting ProgressContext. Had exception: %s", exc_type is not None
        )
        if exc_type:
            logger.error(
                "Exception in ProgressContext: %s - %s", exc_type, exc_val
            )
        pass

    def update(self, amount: int = 1, force: bool = False) -> None:
        """No-op update method kept for compatibility."""
        logger.debug(
            "Update called with amount=%d, force=%s, current=%d",
            amount,
            force,
            self.current,
        )
        self.current += amount
        pass

    def print_output(self, text: str) -> None:
        """Print output to stdout or file.

        Args:
            text: Text to print
        """
        logger.debug("print_output called with text length=%d", len(text))
        logger.debug("First 100 chars of text: %s", text[:100] if text else "")
        logger.debug(
            "Output file: %s, enabled=%s, level=%s",
            self._output_file,
            self.enabled,
            self._level,
        )

        try:
            if self._output_file:
                logger.debug("Writing to output file: %s", self._output_file)
                with open(self._output_file, "a", encoding="utf-8") as f:
                    logger.debug("File opened successfully, writing content")
                    f.write(text)
                    f.write("\n")
                    logger.debug(
                        "Successfully wrote %d chars to file", len(text)
                    )
            else:
                logger.debug("Writing to stdout")
                print(text)
                logger.debug(
                    "Successfully wrote %d chars to stdout", len(text)
                )
        except Exception as e:
            logger.error("Failed to write output: %s", e)
            raise

    def step(self, description: str) -> "ProgressContext":
        """No-op step method kept for compatibility."""
        logger.debug("Step called with description: %s", description)
        return self
