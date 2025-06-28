"""Jinja2 environment factory and configuration.

This module provides a centralized factory for creating consistently configured Jinja2 environments.
"""

from typing import Any, List, Optional, Tuple, Type, Union

import jinja2
from jinja2 import Environment
from jinja2.ext import Extension

from .template_extensions import CommentExtension
from .template_filters import (
    AliasManager,
    register_template_filters,
    register_tses_filters,
)


def create_jinja_env(
    *,
    undefined: Optional[Type[jinja2.Undefined]] = None,
    loader: Optional[jinja2.BaseLoader] = None,
    validation_mode: bool = False,
    debug_mode: bool = False,
    files: Optional[List[Any]] = None,
) -> Tuple[Environment, AliasManager]:
    """Create a consistently configured Jinja2 environment.

    Args:
        undefined: Custom undefined class to use. Defaults to StrictUndefined.
        loader: Template loader to use. Defaults to None.
        validation_mode: Whether to configure the environment for validation (uses SafeUndefined).
        debug_mode: Whether to enable debug features like undefined variable detection.
        files: Optional list of FileInfo objects to enable file reference support.

    Returns:
        Tuple of (Environment, AliasManager). AliasManager will be empty if no files provided.
    """
    if validation_mode:
        from .template_validation import SafeUndefined

        undefined = SafeUndefined
    elif undefined is None:
        undefined = jinja2.StrictUndefined

        # Configure extensions based on debug mode
    extensions: List[Union[str, Type[Extension]]] = [
        "jinja2.ext.do",
        "jinja2.ext.loopcontrols",
        CommentExtension,
    ]

    if debug_mode:
        extensions.append("jinja2.ext.debug")  # Enable {% debug %} tag

    env = Environment(
        loader=loader,
        undefined=undefined,
        autoescape=False,  # Disable HTML escaping by default
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        extensions=extensions,
    )

    # Register all template filters
    register_template_filters(env)

    # Always create an alias manager
    alias_manager = AliasManager()

    # If files are provided, set up file reference support
    if files is not None:
        # Group files by their parent alias
        alias_groups: dict[str, List[Any]] = {}
        for file_info in files:
            if hasattr(file_info, "parent_alias") and file_info.parent_alias:
                alias = file_info.parent_alias
                if alias not in alias_groups:
                    alias_groups[alias] = []
                alias_groups[alias].append(file_info)

        # Register each alias group
        for alias, file_list in alias_groups.items():
            if file_list:
                # Use the first file to determine the base path and attachment type
                first_file = file_list[0]
                base_path = getattr(first_file, "base_path", first_file.path)
                attachment_type = getattr(
                    first_file, "attachment_type", "file"
                )
                is_collection = attachment_type == "collection"

                alias_manager.register_attachment(
                    alias,
                    base_path,
                    file_list,
                    is_collection,
                )

    # Always register file reference functions in the environment
    register_tses_filters(env, alias_manager)

    return env, alias_manager
