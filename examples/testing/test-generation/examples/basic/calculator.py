from typing import Optional, Union


class Calculator:
    """A simple calculator class demonstrating common testing scenarios."""

    def add(
        self, a: Union[int, float], b: Union[int, float]
    ) -> Union[int, float]:
        """Add two numbers."""
        return a + b

    def divide(
        self, a: Union[int, float], b: Union[int, float]
    ) -> Optional[float]:
        """Divide a by b, returns None if b is zero."""
        if b == 0:
            return None
        return a / b

    def average(self, numbers: list[Union[int, float]]) -> Optional[float]:
        """Calculate average of numbers. Returns None for empty list."""
        if not numbers:
            return None
        return sum(numbers) / len(numbers)
