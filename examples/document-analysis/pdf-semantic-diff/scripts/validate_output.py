#!/usr/bin/env python3
"""
Validation script for PDF semantic diff example output.

Compares actual ostruct output against expected results and
validates JSON schema compliance.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """Load and parse JSON file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading {file_path}: {e}")
        return None


def validate_schema(
    data: Dict[str, Any], schema: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Validate data against JSON schema."""
    try:
        import jsonschema

        jsonschema.validate(instance=data, schema=schema)
        return True, None
    except ImportError:
        print("⚠️  jsonschema not available, skipping schema validation")
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)


def compare_changes(actual: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    """Compare actual changes against expected changes."""
    actual_changes = actual.get("changes", [])
    expected_changes = expected.get("changes", [])

    print(f"📊 Actual changes: {len(actual_changes)}")
    print(f"📊 Expected changes: {len(expected_changes)}")

    # Check if we captured the major changes
    change_types_actual = [c["type"] for c in actual_changes]
    change_types_expected = [c["type"] for c in expected_changes]

    print(f"🏷️  Change types found: {set(change_types_actual)}")
    print(f"🏷️  Change types expected: {set(change_types_expected)}")

    # Check coverage (70% threshold for flexibility)
    coverage = (
        len(actual_changes) / len(expected_changes) if expected_changes else 0
    )
    print(f"📈 Coverage: {coverage:.1%}")

    # Check if all expected change types are present
    expected_types = set(change_types_expected)
    actual_types = set(change_types_actual)
    missing_types = expected_types - actual_types

    if missing_types:
        print(f"⚠️  Missing change types: {missing_types}")

    return coverage >= 0.7 and len(missing_types) == 0


def main() -> None:
    """Main validation function."""
    if len(sys.argv) != 2:
        print("Usage: python validate_output.py <output_file>")
        print("Example: python validate_output.py ../output.json")
        sys.exit(1)

    output_file = sys.argv[1]
    script_dir = Path(__file__).parent
    schema_file = script_dir.parent / "schemas" / "semantic_diff.schema.json"
    expected_file = script_dir.parent / "test_data" / "expected_output.json"

    print("🔍 PDF Semantic Diff Output Validation")
    print("=" * 40)

    # Load files
    actual = load_json(output_file)
    schema = load_json(str(schema_file))
    expected = load_json(str(expected_file))

    if not all([actual, schema, expected]):
        print("❌ Failed to load required files")
        sys.exit(1)

    # Type assertions for mypy - we know these are not None after the check above
    assert actual is not None
    assert schema is not None
    assert expected is not None

    # Validate schema
    print("\n1. Schema Validation")
    is_valid, error = validate_schema(actual, schema)
    if not is_valid:
        print(f"❌ Schema validation failed: {error}")
        sys.exit(1)

    print("✅ Schema validation passed")

    # Compare against expected
    print("\n2. Content Comparison")
    if compare_changes(actual, expected):
        print("✅ Output comparison passed")
        print("\n🎉 All validations successful!")
        sys.exit(0)
    else:
        print("❌ Output comparison failed")
        print("💡 Consider reviewing the semantic analysis quality")
        sys.exit(1)


if __name__ == "__main__":
    main()
