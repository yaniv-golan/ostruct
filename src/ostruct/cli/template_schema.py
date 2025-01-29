"""Schema validation and proxy objects for template processing.

Provides proxy objects that validate attribute/key access during template validation
by checking against actual data structures passed to the proxies.

Classes:
    - ValidationProxy: Base proxy class for validation
    - FileInfoProxy: Proxy for file information objects with standard attributes
    - DictProxy: Proxy for dictionary objects that validates against actual structure
    - ListProxy: Proxy for list/iterable objects that validates indices and content
    - StdinProxy: Proxy for lazy stdin access
    - LazyValidationProxy: Proxy that delays attribute access until string conversion
    - DotDict: Dictionary wrapper that supports both dot notation and dictionary access

Examples:
    Create validation context with actual data:
    >>> data = {
    ...     'config': {'debug': True, 'settings': {'mode': 'test'}},
    ...     'source_file': FileInfo('test.txt')
    ... }
    >>> context = create_validation_context(data)
    >>> # config will be a DictProxy validating against actual structure
    >>> # source_file will be a FileInfoProxy with standard attributes

    Access validation:
    >>> # Valid access patterns:
    >>> config = context['config']
    >>> debug_value = config.debug  # OK - debug exists in data
    >>> mode = config.settings.mode  # OK - settings.mode exists in data
    >>>
    >>> # Invalid access raises ValueError:
    >>> config.invalid  # Raises ValueError - key doesn't exist
    >>> config.settings.invalid  # Raises ValueError - nested key doesn't exist

    File info validation:
    >>> file = context['source_file']
    >>> name = file.name  # OK - standard attribute
    >>> content = file.content  # OK - standard attribute
    >>> file.invalid  # Raises ValueError - invalid attribute

Notes:
    - DictProxy validates against actual dictionary structure
    - FileInfoProxy validates standard file attributes
    - ListProxy validates indices and returns appropriate proxies
    - All invalid attribute/key access raises ValueError with details
"""

import logging
import sys
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union, cast

from .file_utils import FileInfo

logger = logging.getLogger(__name__)


class ValidationProxy:
    """Proxy object that validates attribute/key access during template validation."""

    def __init__(
        self,
        var_name: str,
        value: Any = None,
        valid_attrs: Optional[Set[str]] = None,
        nested_attrs: Optional[Dict[str, Any]] = None,
        allow_nested: bool = True,
    ) -> None:
        """Initialize the proxy.

        Args:
            var_name: The name of the variable being proxied.
            value: The value being proxied (optional).
            valid_attrs: Set of valid attribute names.
            nested_attrs: Dictionary of nested attributes and their allowed values.
            allow_nested: Whether to allow nested attribute access.
        """
        self._var_name = var_name
        self._value = value
        self._valid_attrs = valid_attrs or set()
        self._nested_attrs = nested_attrs or {}
        self._allow_nested = allow_nested
        self._accessed_attributes: Set[str] = set()
        logger.debug(
            "Created ValidationProxy for %s with valid_attrs=%s, nested_attrs=%s, allow_nested=%s",
            var_name,
            valid_attrs,
            nested_attrs,
            allow_nested,
        )

    def __getattr__(self, name: str) -> Union["ValidationProxy", "DictProxy"]:
        """Validate attribute access during template validation."""
        logger.debug("\n=== ValidationProxy.__getattr__ ===")
        logger.debug("Called for: %s.%s", self._var_name, name)
        logger.debug(
            "State: valid_attrs=%s, nested_attrs=%s, allow_nested=%s",
            self._valid_attrs,
            self._nested_attrs,
            self._allow_nested,
        )

        self._accessed_attributes.add(name)

        # Allow HTML escaping attributes for all variables
        if name in {"__html__", "__html_format__"}:
            logger.debug(
                "Allowing HTML escape attribute %s for %s",
                name,
                self._var_name,
            )
            return ValidationProxy(f"{self._var_name}.{name}", value="")

        # Check nested attributes
        if name in self._nested_attrs:
            nested_value = self._nested_attrs[name]
            if isinstance(nested_value, dict):
                return ValidationProxy(
                    f"{self._var_name}.{name}",
                    nested_attrs=nested_value,
                    allow_nested=True,
                )
            elif isinstance(nested_value, set):
                if (
                    not nested_value
                ):  # Empty set means "any nested keys allowed"
                    return ValidationProxy(
                        f"{self._var_name}.{name}", allow_nested=True
                    )
                return ValidationProxy(
                    f"{self._var_name}.{name}",
                    valid_attrs=nested_value,
                    allow_nested=False,
                )

        # Validate against valid_attrs if present
        if self._valid_attrs:
            if name not in self._valid_attrs:
                raise ValueError(
                    f"Task template uses undefined attribute '{self._var_name}.{name}'"
                )
            return ValidationProxy(
                f"{self._var_name}.{name}", allow_nested=False
            )

        # Check nesting allowance and get actual value
        if not self._allow_nested:
            raise ValueError(
                f"Task template uses undefined attribute '{self._var_name}.{name}'"
            )

        value = None
        if self._value is not None and hasattr(self._value, name):
            value = getattr(self._value, name)

        return ValidationProxy(
            f"{self._var_name}.{name}", value=value, allow_nested=True
        )

    def __getitem__(self, key: Any) -> Union["ValidationProxy", "DictProxy"]:
        """Support item access for validation."""
        key_str = f"['{key}']" if isinstance(key, str) else f"[{key}]"
        return ValidationProxy(
            f"{self._var_name}{key_str}",
            valid_attrs=self._valid_attrs,
            allow_nested=self._allow_nested,
        )

    def __str__(self) -> str:
        """Convert the proxy value to a string."""
        return str(self._value) if self._value is not None else ""

    def __html__(self) -> str:
        """Return HTML representation."""
        return str(self)

    def __html_format__(self, format_spec: str) -> str:
        """Return formatted HTML representation."""
        return str(self)

    def __iter__(self) -> Iterator[Union["ValidationProxy", "DictProxy"]]:
        """Support iteration for validation."""
        yield ValidationProxy(
            f"{self._var_name}[0]", valid_attrs=self._valid_attrs
        )

    def get_accessed_attributes(self) -> Set[str]:
        """Get the set of accessed attributes."""
        return self._accessed_attributes.copy()


class FileInfoProxy:
    """Proxy for FileInfo that provides validation during template rendering.

    This class wraps FileInfo to provide validation during template rendering.
    It ensures that only valid attributes are accessed and returns empty strings
    for content to support filtering in templates.

    Attributes:
        _var_name: Base variable name for error messages
        _value: The wrapped FileInfo object
        _accessed_attrs: Set of attributes that have been accessed
        _valid_attrs: Set of valid attribute names
    """

    def __init__(self, var_name: str, value: FileInfo) -> None:
        """Initialize FileInfoProxy.

        Args:
            var_name: Base variable name for error messages
            value: FileInfo object to validate
        """
        self._var_name = var_name
        self._value = value
        self._accessed_attrs: Set[str] = set()
        self._valid_attrs = {
            "name",
            "path",
            "content",
            "ext",
            "basename",
            "dirname",
            "abs_path",
            "exists",
            "is_file",
            "is_dir",
            "size",
            "mtime",
            "encoding",
            "hash",
            "extension",
            "parent",
            "stem",
            "suffix",
            "__html__",
            "__html_format__",
        }

    def __getattr__(self, name: str) -> str:
        """Get attribute value with validation.

        Args:
            name: Attribute name to get

        Returns:
            Empty string for content, actual value for other attributes

        Raises:
            ValueError: If attribute name is not valid
        """
        if name not in self._valid_attrs:
            raise ValueError(
                f"undefined attribute '{name}' for file {self._var_name}"
            )

        self._accessed_attrs.add(name)

        # Return empty string for content and HTML methods to support filtering
        if name in ("content", "__html__", "__html_format__"):
            return ""

        # Return actual value for all other attributes
        return str(getattr(self._value, name))

    def __str__(self) -> str:
        """Convert to string.

        Returns:
            Empty string to support filtering
        """
        return ""

    def __html__(self) -> str:
        """Convert to HTML-safe string.

        Returns:
            Empty string to support filtering
        """
        return ""


class DictProxy:
    """Proxy for dictionary access during validation.

    Validates all attribute/key access against the actual dictionary structure.
    Provides standard dictionary methods (get, items, keys, values).
    Supports HTML escaping for Jinja2 compatibility.
    """

    def __init__(self, name: str, value: Dict[str, Any]) -> None:
        """Initialize the proxy.

        Args:
            name: The name of the variable being proxied.
            value: The dictionary being proxied.
        """
        self._name = name
        self._value = value

    def __getattr__(self, name: str) -> Union["DictProxy", ValidationProxy]:
        """Validate attribute access against actual dictionary structure."""
        if name in {"get", "items", "keys", "values"}:
            return cast(
                Union["DictProxy", ValidationProxy], getattr(self, f"_{name}")
            )

        if name not in self._value:
            raise ValueError(
                f"Task template uses undefined attribute '{self._name}.{name}'"
            )

        if isinstance(self._value[name], dict):
            return DictProxy(f"{self._name}.{name}", self._value[name])
        return ValidationProxy(f"{self._name}.{name}")

    def __getitem__(self, key: Any) -> Union["DictProxy", ValidationProxy]:
        """Validate dictionary key access."""
        if isinstance(key, int):
            key = str(key)

        if key not in self._value:
            raise ValueError(
                f"Task template uses undefined key '{self._name}['{key}']'"
            )

        if isinstance(self._value[key], dict):
            return DictProxy(f"{self._name}['{key}']", self._value[key])
        return ValidationProxy(f"{self._name}['{key}']")

    def __contains__(self, key: Any) -> bool:
        """Support 'in' operator for validation."""
        if isinstance(key, int):
            key = str(key)
        return key in self._value

    def _get(self, key: str, default: Any = None) -> Any:
        """Implement dict.get() method."""
        try:
            return self[key]
        except ValueError:
            return default

    def _items(
        self,
    ) -> Iterator[Tuple[str, Union["DictProxy", ValidationProxy]]]:
        """Implement dict.items() method."""
        for key, value in self._value.items():
            if isinstance(value, dict):
                yield (key, DictProxy(f"{self._name}['{key}']", value))
            else:
                yield (key, ValidationProxy(f"{self._name}['{key}']"))

    def _keys(self) -> Iterator[str]:
        """Implement dict.keys() method."""
        for key in self._value.keys():
            yield key

    def _values(self) -> Iterator[Union["DictProxy", ValidationProxy]]:
        """Implement dict.values() method."""
        for key, value in self._value.items():
            if isinstance(value, dict):
                yield DictProxy(f"{self._name}['{key}']", value)
            else:
                yield ValidationProxy(f"{self._name}['{key}']")

    def __html__(self) -> str:
        """Support HTML escaping."""
        return ""

    def __html_format__(self, spec: str) -> str:
        """Support HTML formatting."""
        return ""


class ListProxy(ValidationProxy):
    """Proxy for list/iterable objects during validation.

    For file lists (from --files or --dir), validates that only valid file attributes
    are accessed. For other lists, validates indices and returns appropriate proxies
    based on the actual content type.
    """

    def __init__(self, var_name: str, value: List[Any]) -> None:
        """Initialize the proxy.

        Args:
            var_name: The name of the variable being proxied.
            value: The list being proxied.
        """
        super().__init__(var_name)
        self._value = value
        # Determine if this is a list of files
        self._is_file_list = value and all(
            isinstance(item, FileInfo) for item in value
        )
        self._file_attrs = {
            "name",
            "path",
            "abs_path",
            "content",
            "size",
            "extension",
            "exists",
            "mtime",
            "encoding",
            "dir",
            "hash",
            "is_file",
            "is_dir",
            "parent",
            "stem",
            "suffix",
        }

    def __len__(self) -> int:
        """Support len() for validation."""
        return len(self._value)

    def __iter__(self) -> Iterator[Union[ValidationProxy, DictProxy]]:
        """Support iteration, returning appropriate proxies."""
        if self._is_file_list:
            # For file lists, return FileInfoProxy for validation
            for i in range(len(self._value)):
                yield cast(
                    Union[ValidationProxy, DictProxy],
                    FileInfoProxy(f"{self._var_name}[{i}]", self._value[i]),
                )
        else:
            # For other lists, return basic ValidationProxy
            for i in range(len(self._value)):
                if isinstance(self._value[i], dict):
                    yield DictProxy(f"{self._var_name}[{i}]", self._value[i])
                else:
                    yield ValidationProxy(f"{self._var_name}[{i}]")

    def __getitem__(self, key: Any) -> Union[ValidationProxy, DictProxy]:
        """Validate list index access and return appropriate proxy."""
        if isinstance(key, int) and (key < 0 or key >= len(self._value)):
            raise ValueError(
                f"List index {key} out of range for {self._var_name}"
            )

        key_str = f"['{key}']" if isinstance(key, str) else f"[{key}]"

        if self._is_file_list:
            return cast(
                Union[ValidationProxy, DictProxy],
                FileInfoProxy(f"{self._var_name}{key_str}", self._value[key]),
            )
        else:
            value = self._value[key]
            if isinstance(value, dict):
                return DictProxy(f"{self._var_name}{key_str}", value)
            return ValidationProxy(f"{self._var_name}{key_str}")


class StdinProxy:
    """Proxy for lazy stdin access.

    This proxy only reads from stdin when the content is actually accessed.
    This prevents unnecessary stdin reads when the template doesn't use stdin.
    """

    def __init__(self) -> None:
        """Initialize the proxy."""
        self._content: Optional[str] = None

    def __str__(self) -> str:
        """Return stdin content when converted to string."""
        if self._content is None:
            if sys.stdin.isatty():
                raise ValueError("No input available on stdin")
            self._content = sys.stdin.read()
        return self._content or ""

    def __html__(self) -> str:
        """Support HTML escaping."""
        return str(self)

    def __html_format__(self, spec: str) -> str:
        """Support HTML formatting."""
        return str(self)


class DotDict:
    """Dictionary wrapper that supports both dot notation and dictionary access."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __getattr__(self, name: str) -> Any:
        try:
            value = self._data[name]
            return DotDict(value) if isinstance(value, dict) else value
        except KeyError:
            raise AttributeError(f"'DotDict' object has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        value = self._data[key]
        return DotDict(value) if isinstance(value, dict) else value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        value = self._data.get(key, default)
        return DotDict(value) if isinstance(value, dict) else value

    def items(self) -> List[Tuple[str, Any]]:
        return [
            (k, DotDict(v) if isinstance(v, dict) else v)
            for k, v in self._data.items()
        ]

    def keys(self) -> List[str]:
        return list(self._data.keys())

    def values(self) -> List[Any]:
        return [
            DotDict(v) if isinstance(v, dict) else v
            for v in self._data.values()
        ]


def create_validation_context(
    template_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Create validation context with proxy objects.

    Creates appropriate proxy objects based on the actual type and content
    of each value in the mappings. Validates all attribute/key access
    against the actual data structures.

    Args:
        template_context: Original template context with actual values

    Returns:
        Dictionary with proxy objects for validation

    Example:
        >>> data = {'config': {'debug': True}, 'files': [FileInfo('test.txt')]}
        >>> context = create_validation_context(data)
        >>> # context['config'] will be DictProxy validating against {'debug': True}
        >>> # context['files'] will be ListProxy validating file attributes
    """
    logger.debug("Creating validation context for: %s", template_context)
    validation_context: Dict[str, Any] = {}

    # Add stdin proxy by default - it will only read if accessed
    validation_context["stdin"] = StdinProxy()

    for name, value in template_context.items():
        if isinstance(value, FileInfo):
            validation_context[name] = FileInfoProxy(name, value)
        elif isinstance(value, dict):
            validation_context[name] = DictProxy(name, value)
        elif isinstance(value, list):
            validation_context[name] = ListProxy(name, value)
        else:
            # For primitive values, create a ValidationProxy that disallows attribute access
            validation_context[name] = ValidationProxy(
                name, value=value, allow_nested=False
            )

    logger.debug("Created validation context: %s", validation_context)
    return validation_context
