"""Validators for CLI options and arguments."""

import json
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

import click

from .errors import InvalidJSONError, VariableNameError


def validate_name_path_pair(
    ctx: click.Context,
    param: click.Parameter,
    value: List[Tuple[str, Union[str, Path]]],
) -> List[Tuple[str, Union[str, Path]]]:
    """Validate name/path pairs for files and directories.

    Args:
        ctx: Click context
        param: Click parameter
        value: List of (name, path) tuples

    Returns:
        List of validated (name, Path) tuples

    Raises:
        click.BadParameter: If validation fails
    """
    if not value:
        return value

    result: List[Tuple[str, Union[str, Path]]] = []
    for name, path in value:
        if not name.isidentifier():
            raise click.BadParameter(f"Invalid variable name: {name}")
        result.append((name, Path(path)))
    return result


def validate_variable(
    ctx: click.Context, param: click.Parameter, value: Optional[List[str]]
) -> Optional[List[Tuple[str, str]]]:
    """Validate name=value format for simple variables.

    Args:
        ctx: Click context
        param: Click parameter
        value: List of "name=value" strings

    Returns:
        List of validated (name, value) tuples with whitespace stripped from both parts

    Raises:
        click.BadParameter: If validation fails
    """
    if not value:
        return None

    result = []
    for var in value:
        if "=" not in var:
            raise click.BadParameter(
                f"Variable must be in format name=value: {var}"
            )
        name, val = var.split("=", 1)
        name = name.strip()
        val = val.strip()
        if not name.isidentifier():
            raise click.BadParameter(f"Invalid variable name: {name}")
        result.append((name, val))
    return result


def validate_json_variable(
    ctx: click.Context, param: click.Parameter, value: Optional[List[str]]
) -> Optional[List[Tuple[str, Any]]]:
    """Validate JSON variable format.

    Args:
        ctx: Click context
        param: Click parameter
        value: List of "name=json_string" values

    Returns:
        List of validated (name, parsed_json) tuples with whitespace stripped from name

    Raises:
        click.BadParameter: If validation fails
    """
    if not value:
        return None

    result = []
    for var in value:
        if "=" not in var:
            raise InvalidJSONError(
                f'JSON variable must be in format name=\'{"json":"value"}\': {var}'
            )
        name, json_str = var.split("=", 1)
        name = name.strip()
        json_str = json_str.strip()
        if not name.isidentifier():
            raise VariableNameError(f"Invalid variable name: {name}")
        try:
            json_value = json.loads(json_str)
            result.append((name, json_value))
        except json.JSONDecodeError as e:
            raise InvalidJSONError(
                f"Invalid JSON value for variable {name!r}: {json_str!r}",
                context={"variable_name": name},
            ) from e
    return result
