"""Parameter handling and validation for CLI attachment syntax."""

from typing import Any, Dict, Optional, Set, Tuple, TypedDict, Union

import click

# Target mapping with explicit aliases
TARGET_NORMALISE = {
    "prompt": "prompt",
    "code-interpreter": "code-interpreter",
    "ci": "code-interpreter",
    "file-search": "file-search",
    "fs": "file-search",
}


class AttachmentSpec(TypedDict):
    """Type definition for attachment specifications."""

    alias: str
    path: Union[
        str, Tuple[str, str]
    ]  # str or ("@", "filelist.txt") for collect
    targets: Set[str]
    recursive: bool
    pattern: Optional[str]


def normalise_targets(raw: str) -> Set[str]:
    """Normalize comma-separated target list with aliases.

    Args:
        raw: Comma-separated string of targets (e.g., "prompt,ci,fs")

    Returns:
        Set of normalized target names

    Raises:
        click.BadParameter: If any target is unknown

    Examples:
        >>> normalise_targets("prompt")
        {"prompt"}
        >>> normalise_targets("ci,fs")
        {"code-interpreter", "file-search"}
        >>> normalise_targets("")
        {"prompt"}
    """
    if not raw.strip():  # Guard against empty string edge case
        return {"prompt"}

    tokens = [t.strip().lower() for t in raw.split(",") if t.strip()]
    if not tokens:  # After stripping, no valid tokens remain
        return {"prompt"}

    # Normalize all tokens and check for unknown ones
    normalized = set()
    bad_tokens = set()

    for token in tokens:
        if token in TARGET_NORMALISE:
            normalized.add(TARGET_NORMALISE[token])
        else:
            bad_tokens.add(token)

    if bad_tokens:
        valid_targets = ", ".join(sorted(TARGET_NORMALISE.keys()))
        raise click.BadParameter(
            f"Unknown target(s): {', '.join(sorted(bad_tokens))}. "
            f"Valid targets: {valid_targets}"
        )

    return normalized or {"prompt"}  # Fallback to prompt if somehow empty


def validate_attachment_alias(alias: str) -> str:
    """Validate and normalize attachment alias.

    Args:
        alias: The attachment alias to validate

    Returns:
        The validated alias

    Raises:
        click.BadParameter: If alias is invalid
    """
    if not alias or not alias.strip():
        raise click.BadParameter("Attachment alias cannot be empty")

    alias = alias.strip()

    # Basic validation - no whitespace, reasonable length
    if " " in alias or "\t" in alias:
        raise click.BadParameter("Attachment alias cannot contain whitespace")

    if len(alias) > 64:
        raise click.BadParameter(
            "Attachment alias too long (max 64 characters)"
        )

    return alias


class AttachParam(click.ParamType):
    """Custom Click parameter type for parsing attachment specifications.

    Supports space-form syntax: '[targets:]alias path'

    Examples:
        --attach data ./file.txt
        --attach ci:analysis ./data.csv
        --collect ci,fs:mixed @file-list.txt
    """

    name = "attach-spec"

    def __init__(self, multi: bool = False) -> None:
        """Initialize AttachParam.

        Args:
            multi: If True, supports @filelist syntax for collect operations
        """
        self.multi = multi

    def convert(
        self,
        value: Any,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> Dict[str, Any]:
        """Convert Click parameter value to AttachmentSpec.

        Args:
            value: Parameter value from Click (tuple for nargs=2)
            param: Click parameter object
            ctx: Click context

        Returns:
            Dict representing an AttachmentSpec

        Raises:
            click.BadParameter: If value format is invalid
        """
        # Space form only (nargs=2) - Click passes tuple
        if not isinstance(value, tuple) or len(value) != 2:
            self._fail_with_usage_examples(
                "Attachment must use space form syntax", param, ctx
            )

        spec, path = value

        # Parse spec part: [targets:]alias
        if ":" in spec:
            # Check for Windows drive letter false positive (C:\path)
            if len(spec) == 2 and spec[1] == ":" and spec[0].isalpha():
                # This is likely a drive letter, treat as alias only
                prefix, alias = "prompt", spec
            else:
                prefix, alias = spec.split(":", 1)
        else:
            prefix, alias = "prompt", spec

        # Normalize targets using the existing function
        try:
            targets = normalise_targets(prefix)
        except click.BadParameter:
            # Re-raise with context about attachment parsing
            self._fail_with_usage_examples(
                f"Invalid target(s) in '{prefix}'. Use comma-separated valid targets",
                param,
                ctx,
            )

        # Validate alias
        try:
            alias = validate_attachment_alias(alias)
        except click.BadParameter as e:
            self._fail_with_usage_examples(str(e), param, ctx)

        # Handle collect @filelist syntax
        if self.multi and path.startswith("@"):
            filelist_path = path[1:]  # Remove @
            if not filelist_path:
                self._fail_with_usage_examples(
                    "Filelist path cannot be empty after @", param, ctx
                )
            path = ("@", filelist_path)

        return {
            "alias": alias,
            "path": path,
            "targets": targets,
            "recursive": False,  # Set by flag processing
            "pattern": None,  # Set by flag processing
        }

    def _fail_with_usage_examples(
        self,
        message: str,
        param: Optional[click.Parameter],
        ctx: Optional[click.Context],
    ) -> None:
        """Provide helpful usage examples in error messages."""
        examples = [
            "--file data ./file.txt",
            "--file ci:analysis ./data.csv",
            "--dir fs:docs ./documentation",
        ]

        if self.multi:
            examples.append("--collect ci,fs:mixed @file-list.txt")

        full_message = f"{message}\n\nExamples:\n" + "\n".join(
            f"  {ex}" for ex in examples
        )
        self.fail(full_message, param, ctx)
