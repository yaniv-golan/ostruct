"""Jinja2 environment factory and configuration.

This module provides a centralized factory for creating consistently configured Jinja2 environments.
"""

from typing import Optional, Type

import jinja2
from jinja2 import Environment

from .template_extensions import CommentExtension
from .template_filters import register_template_filters


def create_jinja_env(
    *,
    undefined: Optional[Type[jinja2.Undefined]] = None,
    loader: Optional[jinja2.BaseLoader] = None,
    validation_mode: bool = False,
) -> Environment:
    """Create a consistently configured Jinja2 environment.

    Args:
        undefined: Custom undefined class to use. Defaults to StrictUndefined.
        loader: Template loader to use. Defaults to None.
        validation_mode: Whether to configure the environment for validation (uses SafeUndefined).

    Returns:
        A configured Jinja2 environment.
    """
    if validation_mode:
        from .template_validation import SafeUndefined

        undefined = SafeUndefined
    elif undefined is None:
        undefined = jinja2.StrictUndefined

    env = Environment(
        loader=loader,
        undefined=undefined,
        autoescape=False,  # Disable HTML escaping by default
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        extensions=[
            "jinja2.ext.do",
            "jinja2.ext.loopcontrols",
            CommentExtension,
        ],
    )

    # Register all template filters
    register_template_filters(env)

    return env
