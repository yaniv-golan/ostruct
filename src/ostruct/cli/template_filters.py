"""Template filters for Jinja2 environment."""

import datetime
import itertools
import json
import logging
import re
import textwrap
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, TypeVar, Union

import tiktoken
from jinja2 import Environment
from pygments import highlight
from pygments.formatters import HtmlFormatter, NullFormatter, TerminalFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

logger = logging.getLogger(__name__)

T = TypeVar("T")


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
    return json.dumps(obj, indent=2)


def from_json(text: str) -> Any:
    """Parse JSON string to object."""
    return json.loads(text)


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
            f"| {i+1} | {item} |" for i, item in enumerate(items)
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


def estimate_tokens(text: str) -> int:
    """Estimate number of tokens in text."""
    try:
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(str(text)))
    except Exception as e:
        logger.warning(f"Failed to estimate tokens: {e}")
        return len(str(text).split())


def format_json(obj: Any) -> str:
    """Format JSON with indentation."""
    return json.dumps(obj, indent=2, default=str)


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
        text (str): The code text to format
        output_format (str): The output format ('terminal', 'html', or 'plain')
        language (str): The programming language for syntax highlighting

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

        return highlight(text, lexer, formatter)
    except Exception as e:
        logger.error(f"Error formatting code: {e}")
        return text


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
    }

    env.filters.update(filters)

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
        }
    )
