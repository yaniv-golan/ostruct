"""Common utilities for the CLI package."""

from typing import Tuple

from .errors import VariableNameError, VariableValueError


def parse_mapping(mapping: str) -> Tuple[str, str]:
    """Parse a mapping string in the format 'name=value'.

    Args:
        mapping: Mapping string in format 'name=value'

    Returns:
        Tuple of (name, value)

    Raises:
        ValueError: If mapping format is invalid
        VariableNameError: If name part is empty
        VariableValueError: If value part is empty
    """
    if not mapping or "=" not in mapping:
        raise ValueError("Invalid mapping format")

    name, value = mapping.split("=", 1)
    if not name:
        raise VariableNameError("Empty name in mapping")
    if not value:
        raise VariableValueError("Empty value in mapping")

    return name, value
