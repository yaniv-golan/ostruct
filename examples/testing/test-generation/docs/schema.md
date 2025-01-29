# Test Generation Schema Documentation

This document describes the JSON schema used for test generation output. The schema ensures consistent, structured output that can be used to create or update test files.

## Schema Overview

The output is a JSON object with two main sections:

1. `test_suites`: Array of test suites to generate
2. `summary`: Overall statistics and coverage information

## Test Suites

Each test suite represents tests for a single source file:

```json
{
  "source_file": "src/calculator.py",
  "test_file": "tests/test_calculator.py",
  "framework": "pytest",
  "test_cases": [...]
}
```

### Fields

- `source_file` (string, required): Path to the source file being tested
- `test_file` (string, required): Path where the test file should be created/updated
- `framework` (string, enum): Testing framework to use
  - Allowed values: `"pytest"`, `"unittest"`, `"jest"`
  - Default: `"pytest"`

## Test Cases

Each test case represents a single test function:

```json
{
  "name": "test_add_positive_numbers",
  "type": "unit",
  "target": "Calculator.add",
  "description": "Test addition of two positive numbers",
  "code": "def test_add_positive_numbers():\n    calc = Calculator()\n    result = calc.add(2, 3)\n    assert result == 5",
  "setup": "@pytest.fixture\ndef calculator():\n    return Calculator()",
  "dependencies": ["pytest", "Calculator"]
}
```

### Fields

- `name` (string, required): Name of the test function
- `type` (string, required): Type of test
  - Allowed values: `"unit"`, `"integration"`, `"edge_case"`
- `target` (string): Function or class being tested
- `description` (string): What this test verifies
- `code` (string, required): The actual test code
- `setup` (string): Any setup code needed (fixtures, mocks)
- `dependencies` (array): Required imports or fixtures

## Summary

The summary section provides overview statistics:

```json
{
  "total_files": 3,
  "total_tests": 25,
  "coverage_estimate": {
    "percentage": 85.5,
    "gaps": [
      {
        "file": "src/calculator.py",
        "function": "divide",
        "reason": "Missing edge case for division by zero"
      }
    ]
  }
}
```

### Fields

- `total_files` (integer): Number of source files processed
- `total_tests` (integer): Number of test cases generated
- `coverage_estimate`: Coverage information
  - `percentage` (number): Estimated coverage percentage (0-100)
  - `gaps` (array): List of identified coverage gaps
    - `file` (string): File with missing coverage
    - `function` (string): Function lacking tests
    - `reason` (string): Why this needs coverage

## Example Output

Here's a complete example output:

```json
{
  "test_suites": [
    {
      "source_file": "src/calculator.py",
      "test_file": "tests/test_calculator.py",
      "framework": "pytest",
      "test_cases": [
        {
          "name": "test_add_positive_numbers",
          "type": "unit",
          "target": "Calculator.add",
          "description": "Test addition of two positive numbers",
          "code": "def test_add_positive_numbers(calculator):\n    result = calculator.add(2, 3)\n    assert result == 5",
          "setup": "@pytest.fixture\ndef calculator():\n    return Calculator()",
          "dependencies": ["pytest", "Calculator"]
        },
        {
          "name": "test_add_negative_numbers",
          "type": "unit",
          "target": "Calculator.add",
          "description": "Test addition with negative numbers",
          "code": "def test_add_negative_numbers(calculator):\n    result = calculator.add(-2, -3)\n    assert result == -5",
          "dependencies": ["pytest", "Calculator"]
        }
      ]
    }
  ],
  "summary": {
    "total_files": 1,
    "total_tests": 2,
    "coverage_estimate": {
      "percentage": 75.0,
      "gaps": [
        {
          "file": "src/calculator.py",
          "function": "add",
          "reason": "Missing test for string number inputs"
        }
      ]
    }
  }
}
