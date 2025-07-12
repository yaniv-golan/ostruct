from __future__ import annotations

# ---------------------------------------------------------------------------
# Test helper: ostruct's CLI package depends on `rich_click`. When running the
# schema-validation unit tests in isolation we don't actually need the full
# rich-click implementation.  To avoid pulling an extra dependency into the
# test environment, register a lightweight stub in ``sys.modules`` *before*
# ostruct is imported.  This satisfies the import machinery so that
# ``import rich_click as click`` in ostruct behaves as expected.
# ---------------------------------------------------------------------------
import sys
import types

if "rich_click" not in sys.modules:
    sys.modules["rich_click"] = types.ModuleType("rich_click")

import pytest
from ostruct.cli.schema_validation import (
    SchemaValidationError,
    validate_openai_schema,
)


def _generate_schema_with_properties(count: int) -> dict:
    """Utility: create a flat object schema with *count* string properties."""
    return {
        "type": "object",
        "properties": {f"field{i}": {"type": "string"} for i in range(count)},
        "required": [f"field{i}" for i in range(count)],
        "additionalProperties": False,
    }


def _generate_enum_schema(values: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "choice": {"type": "string", "enum": values},
        },
        "required": ["choice"],
        "additionalProperties": False,
    }


class TestSchemaLimits:
    """Boundary‐condition tests for SchemaLimits constants."""

    def test_property_limit_accepts_5000(self) -> None:
        schema = _generate_schema_with_properties(5000)
        # Should NOT raise
        validate_openai_schema(schema)

    def test_property_limit_rejects_5001(self) -> None:
        schema = _generate_schema_with_properties(5001)
        with pytest.raises(SchemaValidationError):
            validate_openai_schema(schema)

    def test_enum_limit_accepts_1000(self) -> None:
        values = [f"opt{i}" for i in range(1000)]
        schema = _generate_enum_schema(values)
        validate_openai_schema(schema)

    def test_enum_limit_rejects_1001(self) -> None:
        values = [f"opt{i}" for i in range(1001)]
        schema = _generate_enum_schema(values)
        with pytest.raises(SchemaValidationError):
            validate_openai_schema(schema)

    def test_enum_total_char_limit(self) -> None:
        # Build >15,000 char total to trigger error.
        base = "x" * 61  # 61*250 = 15250 > 15000
        values = [f"{base}{i}" for i in range(251)]
        schema = _generate_enum_schema(values)
        with pytest.raises(SchemaValidationError):
            validate_openai_schema(schema)
