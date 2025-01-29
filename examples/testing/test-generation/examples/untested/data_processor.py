import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def normalize_dates(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize different date formats in a list of dictionaries to ISO format.
    Handles common date formats and skips invalid dates.

    Args:
        data: List of dictionaries containing date fields

    Returns:
        List of dictionaries with normalized date fields
    """
    date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d", "%d-%b-%Y"]

    result = []
    for item in data:
        normalized = item.copy()
        for key, value in item.items():
            if not isinstance(value, str):
                continue

            # Try each format
            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    normalized[key] = date_obj.isoformat()[:10]
                    break
                except ValueError:
                    continue

        result.append(normalized)

    return result


def merge_nested_objects(
    obj1: Dict[str, Any], obj2: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with obj2 taking precedence.
    Handles nested dictionaries and lists.

    Args:
        obj1: First dictionary
        obj2: Second dictionary (overrides obj1)

    Returns:
        Merged dictionary
    """
    result = obj1.copy()

    for key, value in obj2.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = merge_nested_objects(result[key], value)
        elif (
            key in result
            and isinstance(result[key], list)
            and isinstance(value, list)
        ):
            result[key].extend(value)
        else:
            result[key] = value

    return result


def extract_nested_values(obj: Dict[str, Any], key_path: str) -> List[Any]:
    """
    Extract values from nested dictionaries using dot notation.
    Example: extract_nested_values({'a': {'b': [1, 2]}}, 'a.b') returns [1, 2]

    Args:
        obj: Dictionary to extract from
        key_path: Path to the value using dot notation

    Returns:
        List of values found at the specified path
    """
    keys = key_path.split(".")
    current = obj

    try:
        for key in keys:
            if isinstance(current, dict):
                current = current[key]
            elif isinstance(current, list):
                results = []
                for item in current:
                    if isinstance(item, dict) and key in item:
                        results.append(item[key])
                return results
            else:
                return []

        if isinstance(current, list):
            return current
        return [current]
    except (KeyError, TypeError):
        return []


def validate_json_structure(
    data: str, required_fields: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Validate JSON string against required fields and return parsed data if valid.

    Args:
        data: JSON string to validate
        required_fields: List of required field names

    Returns:
        Parsed JSON if valid, None if invalid
    """
    try:
        parsed = json.loads(data)
        if not isinstance(parsed, dict):
            return None

        # Check required fields
        for field in required_fields:
            if field not in parsed:
                return None

        return parsed
    except json.JSONDecodeError:
        return None
