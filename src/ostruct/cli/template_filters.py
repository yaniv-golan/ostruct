"""Template filters for Jinja2 environment."""

import datetime
import itertools
import json
import logging
import re
import textwrap
from collections import Counter
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    TypeVar,
    Union,
)

import tiktoken
from jinja2 import Environment, TemplateRuntimeError, pass_context
from pygments import highlight
from pygments.formatters import HtmlFormatter, NullFormatter, TerminalFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Template Structure Enhancement System (TSES) Components
# ============================================================================


class TemplateStructureError(Exception):
    """Exception for TSES-specific errors with helpful suggestions."""

    def __init__(self, message: str, suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.suggestions = suggestions or []


def format_tses_error(error: TemplateStructureError) -> str:
    """Format TSES error with suggestions."""
    lines = [f"Template Structure Error: {error}"]
    if error.suggestions:
        lines.append("Suggestions:")
        for suggestion in error.suggestions:
            lines.append(f"  • {suggestion}")
    return "\n".join(lines)


class AliasManager:
    """Manages file aliases and tracks references."""

    def __init__(self) -> None:
        self.aliases: Dict[str, Dict[str, Any]] = {}
        self.referenced: Set[str] = set()

    def register_attachment(
        self,
        alias: str,
        path: str,
        files: List[Any],
        is_collection: bool = False,
    ) -> None:
        """Register files attached via CLI with their alias."""
        # Determine attachment type from the files themselves
        if is_collection:
            attachment_type = "collection"
        elif files:
            # Use the attachment_type from the first file if available
            first_file = files[0]
            attachment_type = getattr(first_file, "attachment_type", "file")
        else:
            # Fallback for empty file lists
            attachment_type = "file"

        self.aliases[alias] = {
            "type": attachment_type,
            "path": path,
            "files": files,
        }

    def reference_alias(self, alias: str) -> None:
        """Mark an alias as referenced by file_ref()."""
        if alias not in self.aliases:
            available = list(self.aliases.keys())
            raise TemplateStructureError(
                f"Unknown alias '{alias}' in file_ref()",
                [
                    f"Available aliases: {', '.join(available) if available else 'none'}",
                    "Check your --dir and --file attachments",
                ],
            )
        self.referenced.add(alias)

    def get_referenced_aliases(self) -> Dict[str, Dict[str, Any]]:
        """Get only the aliases that were actually referenced."""
        return {
            alias: data
            for alias, data in self.aliases.items()
            if alias in self.referenced
        }


class XMLAppendixBuilder:
    """Builds XML appendix for referenced file aliases."""

    def __init__(self, alias_manager: AliasManager) -> None:
        self.alias_manager = alias_manager

    def build_appendix(self) -> str:
        """Build XML appendix for all referenced aliases."""
        referenced = self.alias_manager.get_referenced_aliases()

        if not referenced:
            return ""

        lines = ["<files>"]

        for alias, data in referenced.items():
            alias_type = data["type"]
            path = data["path"]
            files = data["files"]

            if alias_type == "file":
                # Single file
                file_info = files[0]
                lines.append(f'  <file alias="{alias}" path="{path}">')
                lines.append(
                    f"    <content><![CDATA[{file_info.content}]]></content>"
                )
                lines.append("  </file>")

            elif alias_type == "dir":
                # Directory with multiple files
                lines.append(f'  <dir alias="{alias}" path="{path}">')
                for file_info in files:
                    rel_path = getattr(
                        file_info, "relative_path", file_info.name
                    )
                    lines.append(f'    <file path="{rel_path}">')
                    lines.append(
                        f"      <content><![CDATA[{file_info.content}]]></content>"
                    )
                    lines.append("    </file>")
                lines.append("  </dir>")

            elif alias_type == "collection":
                # File collection
                lines.append(f'  <collection alias="{alias}" path="{path}">')
                for file_info in files:
                    file_path = getattr(file_info, "path", file_info.name)
                    lines.append(f'    <file path="{file_path}">')
                    lines.append(
                        f"      <content><![CDATA[{file_info.content}]]></content>"
                    )
                    lines.append("    </file>")
                lines.append("  </collection>")

        lines.append("</files>")
        return "\n".join(lines)


# Global alias manager instance (set during environment creation)
_alias_manager: Optional[AliasManager] = None


def file_ref(alias_name: str) -> str:
    """Reference a file collection by its CLI alias name.

    Args:
        alias_name: The alias from --dir or --file attachment

    Returns:
        Reference string that renders as <alias_name>

    Usage:
        {{ file_ref("source-code") }}  -> renders as "<source-code>"
    """
    global _alias_manager

    if not _alias_manager:
        raise TemplateStructureError(
            "File references not initialized",
            [
                "Check template processing pipeline",
                "Ensure files are properly attached via CLI",
            ],
        )

    # Register this alias as referenced
    _alias_manager.reference_alias(alias_name)

    # Return the reference format
    return f"<{alias_name}>"


def register_tses_filters(
    env: Environment, alias_manager: AliasManager
) -> None:
    """Register TSES functions in Jinja2 environment."""
    global _alias_manager
    _alias_manager = alias_manager

    # Register file_ref as a global function
    env.globals["file_ref"] = file_ref


# ============================================================================
# End TSES v2.0 Components
# ============================================================================


def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text."""
    return text.split()


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def char_count(text: str) -> int:
    """Count characters in text."""
    return len(text)


def to_json(obj: Any) -> str:
    """Convert object to JSON string."""
    return json.dumps(obj)


def from_json(json_str: str) -> Any:
    """Parse JSON string to object."""
    return json.loads(json_str)


def remove_comments(text: str) -> str:
    """Remove comments from text."""
    return re.sub(r"#.*$|//.*$|/\*[\s\S]*?\*/", "", text, flags=re.MULTILINE)


def wrap_text(text: str, width: int = 80) -> str:
    """Wrap text to specified width."""
    return textwrap.fill(text, width)


def indent_text(text: str, width: int = 4) -> str:
    """Indent text by specified width."""
    return textwrap.indent(text, " " * width)


def dedent_text(text: str) -> str:
    """Remove common leading whitespace from text."""
    return textwrap.dedent(text)


def normalize_text(text: str) -> str:
    """Normalize whitespace in text."""
    return " ".join(text.split())


def strip_markdown(text: str) -> str:
    """Remove markdown formatting characters."""
    return re.sub(r"[#*`_~]", "", text)


def format_table(headers: Sequence[Any], rows: Sequence[Sequence[Any]]) -> str:
    """Format data as a markdown table."""
    return (
        f"| {' | '.join(str(h) for h in headers)} |\n"
        f"| {' | '.join('-' * max(len(str(h)), 3) for h in headers)} |\n"
        + "\n".join(
            f"| {' | '.join(str(cell) for cell in row)} |" for row in rows
        )
    )


def align_table(
    headers: Sequence[Any],
    rows: Sequence[Sequence[Any]],
    alignments: Optional[Sequence[str]] = None,
) -> str:
    """Format table with column alignments."""
    alignments_list = alignments or ["left"] * len(headers)
    alignment_markers = []
    for a in alignments_list:
        if a == "center":
            alignment_markers.append(":---:")
        elif a == "left":
            alignment_markers.append(":---")
        elif a == "right":
            alignment_markers.append("---:")
        else:
            alignment_markers.append("---")

    return (
        f"| {' | '.join(str(h) for h in headers)} |\n"
        f"| {' | '.join(alignment_markers)} |\n"
        + "\n".join(
            f"| {' | '.join(str(cell) for cell in row)} |" for row in rows
        )
    )


def dict_to_table(data: Dict[Any, Any]) -> str:
    """Convert dictionary to markdown table."""
    return "| Key | Value |\n| --- | --- |\n" + "\n".join(
        f"| {k} | {v} |" for k, v in data.items()
    )


def list_to_table(
    items: Sequence[Any], headers: Optional[Sequence[str]] = None
) -> str:
    """Convert list to markdown table."""
    if not headers:
        return "| # | Value |\n| --- | --- |\n" + "\n".join(
            f"| {i + 1} | {item} |" for i, item in enumerate(items)
        )
    return (
        f"| {' | '.join(headers)} |\n| {' | '.join('-' * len(h) for h in headers)} |\n"
        + "\n".join(
            f"| {' | '.join(str(cell) for cell in row)} |" for row in items
        )
    )


def escape_special(text: str) -> str:
    """Escape special characters in text."""
    return re.sub(r'([{}\[\]"\'\\])', r"\\\1", text)


def debug_print(x: Any) -> None:
    """Print debug information."""
    print(f"DEBUG: {x}")


def format_json(obj: Any) -> str:
    """Format JSON with proper indentation."""
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError:
            return str(obj)
    return json.dumps(obj, indent=2, ensure_ascii=False)


def type_of(x: Any) -> str:
    """Get type name of object."""
    return type(x).__name__


def dir_of(x: Any) -> List[str]:
    """Get list of attributes."""
    return dir(x)


def len_of(x: Any) -> Optional[int]:
    """Get length of object if available."""
    return len(x) if hasattr(x, "__len__") else None


def validate_json(text: str) -> bool:
    """Check if text is valid JSON."""
    if not text:
        return False
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def format_error(e: Exception) -> str:
    """Format exception as string."""
    return f"{type(e).__name__}: {str(e)}"


@pass_context
def safe_get(context: Any, *args: Any) -> Any:
    """Safely get a nested attribute path, returning default if any part is undefined.

    This function provides safe access to nested object attributes without raising
    UndefinedError when intermediate objects don't exist.

    Template Usage:
        safe_get(path: str, default_value: Any = "") -> Any

    Args:
        path: Dot-separated path to the attribute (e.g., "transcript.content")
        default_value: Value to return if path doesn't exist (default: "")

    Returns:
        The value at the path if it exists and is non-empty, otherwise default_value

    Examples:
        {{ safe_get("transcript.content", "No transcript available") }}
        {{ safe_get("user.profile.bio", "No bio provided") }}
        {{ safe_get("config.debug") }}  # Uses empty string as default

    Common Mistakes:
        ❌ {{ safe_get(object, 'property', 'default') }}  # Wrong: passing object
        ✅ {{ safe_get('object.property', 'default') }}   # Right: string path

        ❌ {{ safe_get(user_data, 'name') }}              # Wrong: object first
        ✅ {{ safe_get('user_data.name') }}               # Right: string path

    Raises:
        TemplateStructureError: If arguments are incorrect or malformed
    """
    # Import here to avoid circular imports

    # Validate argument count
    if len(args) < 1 or len(args) > 2:
        raise TemplateStructureError(
            f"safe_get() takes 1 or 2 arguments, got {len(args)}",
            [
                "Correct usage: safe_get('path.to.property', 'default_value')",
                "Example: safe_get('user.name', 'Anonymous')",
                f"You provided: {len(args)} arguments",
            ],
        )

    # Extract arguments
    path = args[0]
    default_value = args[1] if len(args) > 1 else ""

    # Validate path parameter type
    if not isinstance(path, str):
        # Provide helpful error message for common mistakes
        path_type = type(path).__name__
        if hasattr(path, "__class__") and hasattr(
            path.__class__, "__module__"
        ):
            # For complex objects, show module.class
            module_name = path.__class__.__module__
            if module_name != "builtins":
                path_type = f"{module_name}.{path.__class__.__name__}"

        # Check for common mistake patterns
        suggestions = [
            "Use string path syntax: safe_get('object.property', 'default')",
            f"You passed: {path_type} as first argument",
            "WRONG: safe_get(object, 'property', 'default')",
            "RIGHT: safe_get('object.property', 'default')",
        ]

        # Add specific suggestions based on the type
        if hasattr(path, "name") or hasattr(path, "content"):
            suggestions.append(
                "For file objects, use: safe_get('filename.property', 'default')"
            )
        elif isinstance(path, (list, tuple)):
            suggestions.append(
                "For collections, iterate first: {% for item in collection %}"
            )
        elif hasattr(path, "__dict__"):
            suggestions.append(
                "For objects, use dot notation in quotes: safe_get('object.attribute', 'default')"
            )

        raise TemplateStructureError(
            f"safe_get() expects a string path, got {path_type}", suggestions
        )

    # Validate path is not empty
    if not path.strip():
        raise TemplateStructureError(
            "safe_get() path cannot be empty",
            [
                "Provide a valid dot-separated path like 'object.property'",
                "Example: safe_get('user.name', 'Anonymous')",
            ],
        )

    try:
        # Split the path and traverse the object tree
        parts = path.split(".")
        current = context

        # Start from the first part in the context
        for i, part in enumerate(parts):
            if i == 0:
                # First part: look in the template context
                if part in context:
                    current = context[part]
                else:
                    return default_value
            else:
                # Subsequent parts: traverse the object
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    # Path doesn't exist, return default
                    return default_value

        # Apply emptiness check to the final value
        # Check for None
        if current is None:
            return default_value

        # Check for empty string
        if isinstance(current, str) and not current.strip():
            return default_value

        # Check for empty collections (list, dict, etc.)
        if hasattr(current, "__len__") and len(current) == 0:
            return default_value

        # Return the value (preserving intentional falsy values like False or 0)
        return current

    except AttributeError as e:
        # More specific error handling for attribute access issues
        logger.debug(f"safe_get attribute error for path '{path}': {e}")
        return default_value
    except (KeyError, TypeError) as e:
        # Handle other access issues
        logger.debug(f"safe_get access error for path '{path}': {e}")
        return default_value
    except Exception as e:
        # Catch any other unexpected errors but log them for debugging
        logger.warning(f"Unexpected error in safe_get for path '{path}': {e}")
        return default_value


@pass_context
def estimate_tokens(context: Any, text: str) -> int:
    """Estimate number of tokens in text."""
    try:
        # Use o200k_base encoding for token estimation
        encoding = tiktoken.get_encoding("o200k_base")
        return len(encoding.encode(str(text)))
    except Exception as e:
        logger.warning(f"Failed to estimate tokens: {e}")
        return len(str(text).split())


def auto_table(data: Any) -> str:
    """Format data as table based on type."""
    if isinstance(data, dict):
        return dict_to_table(data)
    if isinstance(data, (list, tuple)):
        return list_to_table(data)
    return str(data)


def sort_by(items: Sequence[T], key: str) -> List[T]:
    """Sort items by key."""

    def get_key(x: T) -> Any:
        if isinstance(x, dict):
            return x.get(key, 0)
        return getattr(x, key, 0)

    return sorted(items, key=get_key)


def group_by(items: Sequence[T], key: str) -> Dict[Any, List[T]]:
    """Group items by key."""

    def safe_get_key(x: T) -> Any:
        if isinstance(x, dict):
            return x.get(key)
        return getattr(x, key, None)

    sorted_items = sorted(items, key=safe_get_key)
    return {
        k: list(g)
        for k, g in itertools.groupby(sorted_items, key=safe_get_key)
    }


def filter_by(items: Sequence[T], key: str, value: Any) -> List[T]:
    """Filter items by key-value pair."""
    return [
        x
        for x in items
        if (x.get(key) if isinstance(x, dict) else getattr(x, key, None))
        == value
    ]


def extract_field(items: Sequence[Any], key: str) -> List[Any]:
    """Extract field from each item."""
    return [
        x.get(key) if isinstance(x, dict) else getattr(x, key, None)
        for x in items
    ]


def frequency(items: Sequence[T]) -> Dict[T, int]:
    """Count frequency of items."""
    return dict(Counter(items))


def aggregate(
    items: Sequence[Any], key: Optional[str] = None
) -> Dict[str, Union[int, float]]:
    """Calculate aggregate statistics."""
    if not items:
        return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

    def get_value(x: Any) -> float:
        if key is None:
            if isinstance(x, (int, float)):
                return float(x)
            raise ValueError(f"Cannot convert {type(x)} to float")
        val = x.get(key) if isinstance(x, dict) else getattr(x, key, 0)
        if val is None:
            return 0.0
        return float(val)

    values = [get_value(x) for x in items]
    return {
        "count": len(values),
        "sum": sum(values),
        "avg": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


def unique(items: Sequence[Any]) -> List[Any]:
    """Get unique values while preserving order."""
    return list(dict.fromkeys(items))


def pivot_table(
    data: Sequence[Dict[str, Any]],
    index: str,
    value: str,
    aggfunc: str = "sum",
) -> Dict[str, Dict[str, Any]]:
    """Create pivot table from data."""
    if not data:
        logger.debug("Empty data provided to pivot_table")
        return {
            "aggregates": {},
            "metadata": {"total_records": 0, "null_index_count": 0},
        }

    # Validate aggfunc
    valid_aggfuncs = {"sum", "mean", "count"}
    if aggfunc not in valid_aggfuncs:
        raise ValueError(
            f"Invalid aggfunc: {aggfunc}. Must be one of {valid_aggfuncs}"
        )

    # Validate columns exist in first row
    if data and (index not in data[0] or value not in data[0]):
        missing = []
        if index not in data[0]:
            missing.append(f"index column '{index}'")
        if value not in data[0]:
            missing.append(f"value column '{value}'")
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    # Count records with null index
    null_index_count = sum(1 for row in data if row.get(index) is None)
    if null_index_count:
        logger.warning(f"Found {null_index_count} rows with null index values")

    # Group by index
    groups: Dict[str, List[float]] = {}
    invalid_values = 0
    for row in data:
        idx = str(row.get(index, ""))
        try:
            val = float(row.get(value, 0))
        except (TypeError, ValueError):
            invalid_values += 1
            logger.warning(
                f"Invalid value for {value} in row with index {idx}, using 0"
            )
            val = 0.0

        if idx not in groups:
            groups[idx] = []
        groups[idx].append(val)

    if invalid_values:
        logger.warning(
            f"Found {invalid_values} invalid values in column {value}"
        )

    result: Dict[str, Dict[str, Any]] = {"aggregates": {}, "metadata": {}}
    for idx, values in groups.items():
        if aggfunc == "sum":
            result["aggregates"][idx] = {"value": sum(values)}
        elif aggfunc == "mean":
            result["aggregates"][idx] = {"value": sum(values) / len(values)}
        else:  # count
            result["aggregates"][idx] = {"value": len(values)}

    result["metadata"] = {
        "total_records": len(data),
        "null_index_count": null_index_count,
        "invalid_values": invalid_values,
    }
    return result


def summarize(
    data: Sequence[Any], keys: Optional[Sequence[str]] = None
) -> Dict[str, Any]:
    """Generate summary statistics for data fields."""
    if not data:
        logger.debug("Empty data provided to summarize")
        return {"total_records": 0, "fields": {}}

    # Validate data type
    if not isinstance(data[0], dict) and not hasattr(data[0], "__dict__"):
        raise TypeError("Data items must be dictionaries or objects")

    def get_field_value(item: Any, field: str) -> Any:
        try:
            if isinstance(item, dict):
                return item.get(field)
            return getattr(item, field, None)
        except Exception as e:
            logger.warning(f"Error accessing field {field}: {e}")
            return None

    def get_field_type(values: List[Any]) -> str:
        """Determine field type from non-null values."""
        non_null = [v for v in values if v is not None]
        if not non_null:
            return "NoneType"

        # Check if all values are of the same type
        types = {type(v) for v in non_null}
        if len(types) == 1:
            return next(iter(types)).__name__

        # Handle mixed numeric types
        if all(isinstance(v, (int, float)) for v in non_null):
            return "number"

        # Default to most specific common ancestor type
        return "mixed"

    def analyze_field(field: str) -> Dict[str, Any]:
        logger.debug(f"Analyzing field: {field}")
        values = [get_field_value(x, field) for x in data]
        non_null = [v for v in values if v is not None]

        stats = {
            "type": get_field_type(values),
            "total": len(values),
            "null_count": len(values) - len(non_null),
            "unique": len(set(non_null)),
        }

        # Add numeric statistics if applicable
        if stats["type"] in ("int", "float", "number"):
            try:
                nums = [float(x) for x in non_null]
                stats.update(
                    {
                        "min": min(nums) if nums else None,
                        "max": max(nums) if nums else None,
                        "avg": sum(nums) / len(nums) if nums else None,
                    }
                )
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Error calculating numeric stats for {field}: {e}"
                )

        # Add most common values
        if non_null:
            try:
                most_common = Counter(non_null).most_common(5)
                stats["most_common"] = [
                    {"value": str(v), "count": c} for v, c in most_common
                ]
            except TypeError as e:
                logger.warning(
                    f"Error calculating most common values for {field}: {e}"
                )

        return stats

    try:
        available_keys = keys or (
            list(data[0].keys())
            if isinstance(data[0], dict)
            else [k for k in dir(data[0]) if not k.startswith("_")]
        )

        if not available_keys:
            raise ValueError("No valid keys found in data")

        logger.debug(
            f"Analyzing {len(data)} records with {len(available_keys)} fields"
        )
        result = {
            "total_records": len(data),
            "fields": {k: analyze_field(k) for k in available_keys},
        }
        logger.debug("Analysis complete")
        return result

    except Exception as e:
        logger.error(f"Failed to analyze data: {e}", exc_info=True)
        raise ValueError(f"Failed to analyze data: {str(e)}")


def strip_comments(text: str, lang: str = "python") -> str:
    """Remove comments from code text based on language.

    Args:
        text: Code text to process
        lang: Programming language

    Returns:
        Text with comments removed if language is supported,
        otherwise returns original text with a warning
    """
    # Define comment patterns for different languages
    single_line_comments = {
        "python": "#",
        "javascript": "//",
        "typescript": "//",
        "java": "//",
        "c": "//",
        "cpp": "//",
        "go": "//",
        "rust": "//",
        "swift": "//",
        "ruby": "#",
        "perl": "#",
        "shell": "#",
        "bash": "#",
        "php": "//",
    }

    multi_line_comments = {
        "javascript": ("/*", "*/"),
        "typescript": ("/*", "*/"),
        "java": ("/*", "*/"),
        "c": ("/*", "*/"),
        "cpp": ("/*", "*/"),
        "go": ("/*", "*/"),
        "rust": ("/*", "*/"),
        "swift": ("/*", "*/"),
        "php": ("/*", "*/"),
    }

    # Return original text if language is not supported
    if lang not in single_line_comments and lang not in multi_line_comments:
        logger.debug(
            f"Language '{lang}' is not supported for comment removal. "
            f"Comments will be preserved in the output."
        )
        return text

    lines = text.splitlines()
    cleaned_lines = []

    # Handle single-line comments
    if lang in single_line_comments:
        comment_char = single_line_comments[lang]
        for line in lines:
            # Remove inline comments
            line = re.sub(f"\\s*{re.escape(comment_char)}.*$", "", line)
            # Keep non-empty lines
            if line.strip():
                cleaned_lines.append(line)
        text = "\n".join(cleaned_lines)

    # Handle multi-line comments
    if lang in multi_line_comments:
        start, end = multi_line_comments[lang]
        # Remove multi-line comments
        text = re.sub(
            f"{re.escape(start)}.*?{re.escape(end)}", "", text, flags=re.DOTALL
        )

    return text


def format_code(
    text: str, output_format: str = "terminal", language: str = "python"
) -> str:
    """Format code with syntax highlighting.

    Args:
        text: The code text to format
        output_format: The output format ('terminal', 'html', or 'plain')
        language: The programming language for syntax highlighting

    Returns:
        str: Formatted code string

    Raises:
        ValueError: If output_format is not one of 'terminal', 'html', or 'plain'
    """
    if not text:
        return ""

    if output_format not in ["terminal", "html", "plain"]:
        raise ValueError(
            "output_format must be one of 'terminal', 'html', or 'plain'"
        )

    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        try:
            lexer = guess_lexer(text)
        except ClassNotFound:
            lexer = TextLexer()

    try:
        if output_format == "terminal":
            formatter: Union[
                TerminalFormatter[str], HtmlFormatter[str], NullFormatter[str]
            ] = TerminalFormatter[str]()
        elif output_format == "html":
            formatter = HtmlFormatter[str]()
        else:  # plain
            formatter = NullFormatter[str]()

        result = highlight(text, lexer, formatter)
        if isinstance(result, bytes):
            return result.decode("utf-8")
        return str(result)
    except Exception as e:
        logger.error(f"Error formatting code: {e}")
        return str(text)


def single_filter(value: Any) -> Any:
    """Extract single item from a list, ensuring exactly one item exists."""
    # Import here to avoid circular imports
    try:
        from .file_list import FileInfoList

        FileInfoListType = FileInfoList
    except ImportError:
        # Fallback if imports fail
        FileInfoListType = None

    if FileInfoListType and isinstance(value, FileInfoListType):
        var_alias = getattr(value, "_var_alias", None) or "list"
        if len(value) == 1:
            return value[0]  # ✅ Return the FileInfo object, not the list
        else:
            raise TemplateRuntimeError(
                f"Filter 'single' expected exactly 1 file for '{var_alias}', got {len(value)}."
            )

    # For other list types (but not strings or dicts)
    if (
        hasattr(value, "__len__")
        and hasattr(value, "__getitem__")
        and not isinstance(value, (str, dict))
        and hasattr(value, "__iter__")
    ):
        if len(value) == 1:
            return value[0]
        else:
            raise TemplateRuntimeError(
                f"Filter 'single' expected exactly 1 item, got {len(value)}."
            )

    # Pass through non-list types (including FileInfo and strings)
    return value


def files_filter(value: Any) -> List[Any]:
    """Ensure a file-bearing value is iterable.

    This filter implements the file-sequence protocol by ensuring that
    any file-bearing value can be iterated over. Single files yield
    themselves, while collections remain as-is.

    Args:
        value: A file-bearing value (FileInfo, FileInfoList, or other iterable)

    Returns:
        A list containing the file(s) for uniform iteration
    """
    # Handle strings and bytes specially - treat as single items, not character sequences
    if isinstance(value, (str, bytes)):
        return [value]

    try:
        # If it's already iterable (but not string/bytes), convert to list
        return list(value)
    except TypeError:
        # If not iterable, wrap in a list
        return [value]


def is_fileish(value: Any) -> bool:
    """Test if a value is file-like (iterable collection of file objects).

    This test function helps templates identify file-bearing values
    that implement the file-sequence protocol.

    Args:
        value: The value to test

    Returns:
        True if the value is iterable and contains file-like objects
    """
    try:
        # Import here to avoid circular imports
        from .file_info import FileInfo

        # Check if it's iterable
        if not hasattr(value, "__iter__"):
            return False

        # Convert to list to check contents
        items = list(value)

        # Check if all items are FileInfo objects
        return all(isinstance(item, FileInfo) for item in items)
    except (TypeError, ImportError):
        return False


def register_template_filters(env: Environment) -> None:
    """Register all template filters with the Jinja2 environment.

    Args:
        env: The Jinja2 environment to register filters with.
    """
    filters = {
        # Text processing
        "extract_keywords": extract_keywords,
        "word_count": word_count,
        "char_count": char_count,
        "to_json": to_json,
        "from_json": from_json,
        "remove_comments": remove_comments,
        "wrap": wrap_text,
        "indent": indent_text,
        "dedent": dedent_text,
        "normalize": normalize_text,
        "strip_markdown": strip_markdown,
        # Data processing
        "sort_by": sort_by,
        "group_by": group_by,
        "filter_by": filter_by,
        "extract_field": extract_field,
        "unique": unique,
        "frequency": frequency,
        "aggregate": aggregate,
        # Table formatting
        "table": format_table,
        "align_table": align_table,
        "dict_to_table": dict_to_table,
        "list_to_table": list_to_table,
        # Code processing
        "format_code": format_code,
        "strip_comments": strip_comments,
        # Special character handling
        "escape_special": escape_special,
        # Table utilities
        "auto_table": auto_table,
        # Single item extraction
        "single": single_filter,
        # File-sequence protocol support
        "files": files_filter,
    }

    env.filters.update(filters)

    # Add template tests
    tests = {
        "fileish": is_fileish,
    }

    env.tests.update(tests)

    # Add template globals
    env.globals.update(
        {
            "estimate_tokens": estimate_tokens,
            "format_json": format_json,
            "now": datetime.datetime.now,
            "debug": debug_print,
            "type_of": type_of,
            "dir_of": dir_of,
            "len_of": len_of,
            "validate_json": validate_json,
            "format_error": format_error,
            # Data analysis globals
            "summarize": summarize,
            "pivot_table": pivot_table,
            # Table utilities
            "auto_table": auto_table,
            # Safe access utilities
            "safe_get": safe_get,
        }
    )
