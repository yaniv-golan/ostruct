"""Field utilities for Pydantic model creation."""

from typing import Any, Union

from pydantic import Field
from pydantic.fields import FieldInfo as FieldInfoType


def pattern(regex: str) -> Any:
    """Create a pattern constraint for string fields."""
    return Field(pattern=regex)


def min_length(length: int) -> Any:
    """Create a minimum length constraint for string fields."""
    return Field(min_length=length)


def max_length(length: int) -> Any:
    """Create a maximum length constraint for string fields."""
    return Field(max_length=length)


def ge(value: Union[int, float]) -> Any:
    """Create a greater-than-or-equal constraint for numeric fields."""
    return Field(ge=value)


def le(value: Union[int, float]) -> Any:
    """Create a less-than-or-equal constraint for numeric fields."""
    return Field(le=value)


def gt(value: Union[int, float]) -> Any:
    """Create a greater-than constraint for numeric fields."""
    return Field(gt=value)


def lt(value: Union[int, float]) -> Any:
    """Create a less-than constraint for numeric fields."""
    return Field(lt=value)


def multiple_of(value: Union[int, float]) -> Any:
    """Create a multiple-of constraint for numeric fields."""
    return Field(multiple_of=value)


def _create_field(**kwargs: Any) -> FieldInfoType:
    """Create a Pydantic field with the given constraints."""
    return Field(**kwargs)  # type: ignore[no-any-return]


def _get_type_with_constraints(
    base_type: type, constraints: dict, field_name: str = ""
) -> type:
    """Get a type with constraints applied.

    Args:
        base_type: The base Python type
        constraints: Dictionary of constraints to apply
        field_name: Name of the field (for error reporting)

    Returns:
        Type with constraints applied
    """
    # For now, just return the base type
    # This can be expanded in the future to create constrained types
    return base_type
