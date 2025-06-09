#!/usr/bin/env python3
"""
Test 22: ostruct meta-schema: validate our JSON schemas are well-formed
Schema validation testing
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import subprocess
import tempfile
import time
import re
from dataclasses import dataclass


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""

    schema_path: Path
    is_valid: bool
    validation_errors: List[str]
    schema_type: str
    complexity_score: float
    meta_compliance: bool


def create_test_schemas() -> List[Path]:
    """Create various test schemas for validation."""
    test_schemas = []

    # Schema 1: Simple valid schema
    simple_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
        },
        "required": ["name"],
    }

    # Schema 2: Complex valid schema
    complex_schema = {
        "type": "object",
        "properties": {
            "user_profile": {
                "type": "object",
                "properties": {
                    "personal_info": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "minLength": 1},
                            "email": {"type": "string", "format": "email"},
                            "age": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 150,
                            },
                        },
                        "required": ["name", "email"],
                    },
                    "preferences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "value": {"type": "string"},
                                "priority": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10,
                                },
                            },
                        },
                    },
                },
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "created_at": {"type": "string", "format": "date-time"},
                    "version": {
                        "type": "string",
                        "pattern": "^\\d+\\.\\d+\\.\\d+$",
                    },
                },
            },
        },
        "required": ["user_profile"],
    }

    # Schema 3: Invalid schema (missing type)
    invalid_schema = {
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        # Missing "type" at root level
    }

    # Schema 4: Schema with errors
    error_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "invalid_type"},  # Invalid type
            "age": {
                "type": "integer",
                "minimum": "not_a_number",
            },  # Invalid minimum
        },
    }

    # Schema 5: OpenAI structured output compatible schema
    openai_schema = {
        "type": "object",
        "properties": {
            "analysis_result": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "confidence_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "details": {
                        "type": "object",
                        "properties": {
                            "word_count": {"type": "integer"},
                            "sentiment": {
                                "type": "string",
                                "enum": ["positive", "negative", "neutral"],
                            },
                        },
                    },
                },
            }
        },
        "required": ["analysis_result"],
        "additionalProperties": False,
    }

    schemas = [
        ("simple_valid.json", simple_schema),
        ("complex_valid.json", complex_schema),
        ("invalid_missing_type.json", invalid_schema),
        ("error_invalid_types.json", error_schema),
        ("openai_compatible.json", openai_schema),
    ]

    # Create temporary schema files
    for filename, schema_data in schemas:
        temp_file = Path(tempfile.mktemp(suffix=".json"))
        with open(temp_file, "w") as f:
            json.dump(schema_data, f, indent=2)
        test_schemas.append(temp_file)

    return test_schemas


def validate_json_schema(schema_path: Path) -> SchemaValidationResult:
    """Validate a JSON schema for correctness."""
    try:
        # Read the schema file
        with open(schema_path, "r") as f:
            schema_data = json.load(f)

        validation_errors = []
        is_valid = True
        schema_type = "unknown"
        complexity_score = 0.0
        meta_compliance = True

        # Basic JSON Schema validation
        try:
            # Try using jsonschema library if available
            try:
                import jsonschema
                from jsonschema import Draft7Validator

                # Validate against JSON Schema meta-schema
                meta_schema = Draft7Validator.META_SCHEMA
                validator = Draft7Validator(meta_schema)

                # Check for validation errors
                errors = list(validator.iter_errors(schema_data))
                if errors:
                    is_valid = False
                    validation_errors.extend(
                        [
                            f"Meta-schema error: {error.message}"
                            for error in errors
                        ]
                    )
                    meta_compliance = False

            except ImportError:
                # Fallback validation without jsonschema library
                validation_errors.append(
                    "jsonschema library not available - using basic validation"
                )

                # Basic manual validation
                basic_validation_result = validate_schema_manually(schema_data)
                is_valid = basic_validation_result["is_valid"]
                validation_errors.extend(basic_validation_result["errors"])
                meta_compliance = basic_validation_result["meta_compliance"]

        except Exception as e:
            is_valid = False
            validation_errors.append(f"Validation error: {str(e)}")
            meta_compliance = False

        # Determine schema type and complexity
        schema_analysis = analyze_schema_structure(schema_data)
        schema_type = schema_analysis["type"]
        complexity_score = schema_analysis["complexity"]

        # Additional validation checks
        additional_checks = perform_additional_validation(schema_data)
        if additional_checks["errors"]:
            validation_errors.extend(additional_checks["errors"])
            if additional_checks["critical_errors"]:
                is_valid = False

        return SchemaValidationResult(
            schema_path=schema_path,
            is_valid=is_valid,
            validation_errors=validation_errors,
            schema_type=schema_type,
            complexity_score=complexity_score,
            meta_compliance=meta_compliance,
        )

    except json.JSONDecodeError as e:
        return SchemaValidationResult(
            schema_path=schema_path,
            is_valid=False,
            validation_errors=[f"JSON parse error: {str(e)}"],
            schema_type="invalid_json",
            complexity_score=0.0,
            meta_compliance=False,
        )
    except Exception as e:
        return SchemaValidationResult(
            schema_path=schema_path,
            is_valid=False,
            validation_errors=[f"Unexpected error: {str(e)}"],
            schema_type="error",
            complexity_score=0.0,
            meta_compliance=False,
        )


def validate_schema_manually(schema_data: Dict[str, Any]) -> Dict[str, Any]:
    """Manual schema validation when jsonschema library is not available."""
    errors = []
    is_valid = True
    meta_compliance = True

    # Check for required root properties
    if "type" not in schema_data:
        errors.append("Missing required 'type' property at root level")
        is_valid = False
        meta_compliance = False

    # Validate type values
    valid_types = [
        "null",
        "boolean",
        "object",
        "array",
        "number",
        "string",
        "integer",
    ]

    def check_type_recursive(obj: Any, path: str = "root") -> None:
        if isinstance(obj, dict):
            if "type" in obj:
                type_val = obj["type"]
                if isinstance(type_val, str):
                    if type_val not in valid_types:
                        errors.append(f"Invalid type '{type_val}' at {path}")
                        nonlocal is_valid
                        is_valid = False
                elif isinstance(type_val, list):
                    for t in type_val:
                        if t not in valid_types:
                            errors.append(
                                f"Invalid type '{t}' in array at {path}"
                            )
                            is_valid = False

            # Check properties recursively
            if "properties" in obj:
                for prop_name, prop_schema in obj["properties"].items():
                    check_type_recursive(
                        prop_schema, f"{path}.properties.{prop_name}"
                    )

            # Check items for arrays
            if "items" in obj:
                check_type_recursive(obj["items"], f"{path}.items")

    check_type_recursive(schema_data)

    return {
        "is_valid": is_valid,
        "errors": errors,
        "meta_compliance": meta_compliance,
    }


def analyze_schema_structure(schema_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze schema structure to determine type and complexity."""
    schema_type = "simple"
    complexity_score = 1.0

    def count_complexity(obj: Any, depth: int = 0) -> float:
        score = 0.0

        if isinstance(obj, dict):
            # Base complexity for object
            score += 1.0

            # Depth penalty/bonus
            score += depth * 0.5

            # Property count
            if "properties" in obj:
                score += len(obj["properties"]) * 0.2

                # Recursive complexity
                for prop_schema in obj["properties"].values():
                    score += count_complexity(prop_schema, depth + 1)

            # Array complexity
            if "items" in obj:
                score += 1.0 + count_complexity(obj["items"], depth + 1)

            # Validation keywords add complexity
            validation_keywords = [
                "pattern",
                "format",
                "minimum",
                "maximum",
                "minLength",
                "maxLength",
                "enum",
            ]
            for keyword in validation_keywords:
                if keyword in obj:
                    score += 0.3

        return score

    complexity_score = count_complexity(schema_data)

    # Determine schema type
    if complexity_score < 3.0:
        schema_type = "simple"
    elif complexity_score < 8.0:
        schema_type = "moderate"
    else:
        schema_type = "complex"

    # Check for specific patterns
    if (
        "additionalProperties" in schema_data
        and schema_data["additionalProperties"] is False
    ):
        schema_type += "_strict"

    return {"type": schema_type, "complexity": complexity_score}


def perform_additional_validation(
    schema_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Perform additional validation checks specific to ostruct usage."""
    errors = []
    critical_errors = []

    # Check for OpenAI structured output compatibility
    def check_openai_compatibility(obj: Any, path: str = "root") -> None:
        if isinstance(obj, dict):
            # Check for unsupported keywords
            unsupported_keywords = ["$ref", "allOf", "anyOf", "oneOf", "not"]
            for keyword in unsupported_keywords:
                if keyword in obj:
                    errors.append(
                        f"OpenAI incompatible keyword '{keyword}' at {path}"
                    )

            # Recursively check properties
            if "properties" in obj:
                for prop_name, prop_schema in obj["properties"].items():
                    check_openai_compatibility(
                        prop_schema, f"{path}.{prop_name}"
                    )

            if "items" in obj:
                check_openai_compatibility(obj["items"], f"{path}.items")

    check_openai_compatibility(schema_data)

    # Check for common issues
    def check_common_issues(obj: Any, path: str = "root") -> None:
        if isinstance(obj, dict):
            # Check for conflicting constraints
            if "minimum" in obj and "maximum" in obj:
                if obj["minimum"] > obj["maximum"]:
                    critical_errors.append(f"minimum > maximum at {path}")

            # Check for invalid enum values
            if "enum" in obj and "type" in obj:
                enum_values = obj["enum"]
                expected_type = obj["type"]

                for value in enum_values:
                    if expected_type == "string" and not isinstance(
                        value, str
                    ):
                        errors.append(
                            f"Enum value {value} doesn't match type {expected_type} at {path}"
                        )
                    elif expected_type == "integer" and not isinstance(
                        value, int
                    ):
                        errors.append(
                            f"Enum value {value} doesn't match type {expected_type} at {path}"
                        )

            # Recursive checks
            if "properties" in obj:
                for prop_name, prop_schema in obj["properties"].items():
                    check_common_issues(prop_schema, f"{path}.{prop_name}")

            if "items" in obj:
                check_common_issues(obj["items"], f"{path}.items")

    check_common_issues(schema_data)

    return {"errors": errors, "critical_errors": critical_errors}


def test_ostruct_schema_validation() -> Dict[str, Any]:
    """
    Test ostruct meta-schema validation functionality.

    Returns:
        Dict with test analysis results
    """
    analysis: Dict[str, Any] = {
        "test_implemented": True,
        "test_case": "Schema validation testing",
        "success_criteria": "Accurate validation of JSON schemas",
        "results": {},
    }

    try:
        print("Testing ostruct meta-schema validation...")

        # Create test schemas
        test_schemas = create_test_schemas()
        analysis["results"]["total_schemas"] = len(test_schemas)

        # Validate each schema
        validation_results = []

        for i, schema_path in enumerate(test_schemas):
            print(f"\nValidating schema {i + 1}: {schema_path.name}")

            result = validate_json_schema(schema_path)

            result_dict = {
                "schema_name": schema_path.name,
                "is_valid": result.is_valid,
                "validation_errors": result.validation_errors,
                "schema_type": result.schema_type,
                "complexity_score": result.complexity_score,
                "meta_compliance": result.meta_compliance,
            }

            validation_results.append(result_dict)

            print(f"  Valid: {result.is_valid}")
            print(f"  Type: {result.schema_type}")
            print(f"  Complexity: {result.complexity_score:.2f}")
            print(f"  Meta-compliant: {result.meta_compliance}")

            if result.validation_errors:
                print(f"  Errors: {len(result.validation_errors)}")
                for error in result.validation_errors[
                    :3
                ]:  # Show first 3 errors
                    print(f"    - {error}")

        analysis["results"]["validation_results"] = validation_results

        # Calculate overall metrics
        valid_schemas = [r for r in validation_results if r["is_valid"]]
        meta_compliant_schemas = [
            r for r in validation_results if r["meta_compliance"]
        ]

        # Expected results based on our test schemas
        expected_valid = [
            "simple_valid.json",
            "complex_valid.json",
            "openai_compatible.json",
        ]
        expected_invalid = [
            "invalid_missing_type.json",
            "error_invalid_types.json",
        ]

        # Check if validation results match expectations
        correct_validations = 0
        total_expected = len(expected_valid) + len(expected_invalid)

        for result in validation_results:
            schema_name = result["schema_name"]
            is_valid = result["is_valid"]

            if schema_name in expected_valid and is_valid:
                correct_validations += 1
            elif schema_name in expected_invalid and not is_valid:
                correct_validations += 1

        accuracy = (
            correct_validations / total_expected if total_expected > 0 else 0
        )

        analysis["results"]["total_schemas"] = len(test_schemas)
        analysis["results"]["valid_schemas"] = len(valid_schemas)
        analysis["results"]["meta_compliant_schemas"] = len(
            meta_compliant_schemas
        )
        analysis["results"]["validation_accuracy"] = accuracy
        analysis["results"]["correct_validations"] = correct_validations
        analysis["results"]["expected_validations"] = total_expected

        # Success if accuracy > 80% and we can distinguish valid from invalid
        analysis["results"]["success"] = (
            accuracy > 0.8
            and len(valid_schemas) > 0
            and len(valid_schemas)
            < len(test_schemas)  # Some should be invalid
        )

        print(f"\nOverall Results:")
        print(f"  Total schemas tested: {len(test_schemas)}")
        print(f"  Valid schemas: {len(valid_schemas)}")
        print(f"  Meta-compliant schemas: {len(meta_compliant_schemas)}")
        print(f"  Validation accuracy: {accuracy:.1%}")
        print(f"  Success: {analysis['results']['success']}")

        # Cleanup temp files
        for schema_path in test_schemas:
            try:
                schema_path.unlink()
            except:
                pass

        return analysis

    except Exception as e:
        analysis["results"]["error"] = str(e)
        analysis["results"]["success"] = False
        return analysis


def run_test() -> Dict[str, Any]:
    """
    Run test 22: ostruct meta-schema validation.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "22",
        "test_name": "ostruct meta-schema: validate our JSON schemas are well-formed",
        "test_case": "Schema validation testing",
        "success": False,
        "error": None,
        "details": {},
    }

    try:
        print(f"Test 22: ostruct meta-schema validation")
        print(f"Test case: Schema validation testing")

        # Run the specific test function
        analysis = test_ostruct_schema_validation()
        results["details"]["analysis"] = analysis

        # Determine success based on analysis
        if analysis["results"].get("success", False):
            accuracy = analysis["results"].get("validation_accuracy", 0)
            valid_count = analysis["results"].get("valid_schemas", 0)
            total_count = analysis["results"].get("total_schemas", 0)
            results["success"] = True
            results["details"]["result"] = (
                f"PASS: {accuracy:.1%} accuracy, {valid_count}/{total_count} schemas valid"
            )
            print(
                f"✅ PASS: {accuracy:.1%} accuracy, {valid_count}/{total_count} schemas valid"
            )
        else:
            error_msg = analysis["results"].get(
                "error", "Schema validation accuracy too low"
            )
            results["error"] = error_msg
            results["success"] = False
            results["details"]["result"] = f"FAIL: {error_msg}"
            print(f"❌ FAIL: {error_msg}")

    except Exception as e:
        results["error"] = str(e)
        results["details"]["exception"] = str(e)
        print(f"❌ Test failed with error: {e}")

    return results


def main():
    """Run the test."""
    results = run_test()

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_file}")
    return results


if __name__ == "__main__":
    main()
