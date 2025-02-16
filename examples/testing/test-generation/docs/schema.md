# Test Generation Schema Documentation

This document describes the JSON schema used for test generation output. The schema ensures consistent, structured output that can be used to create or update test files.

## Schema Overview

The output is a JSON object with two main sections:

1. `test_cases`: Array of test cases to generate
2. `summary`: Overall statistics and coverage information

## Test Cases

Each test case represents a single test function:

```json
{
  "function_name": "add_numbers",
  "test_name": "test_add_positive_numbers",
  "test_type": "unit",
  "description": "Test addition of two positive numbers",
  "code": "def test_add_positive_numbers():\n    calc = Calculator()\n    result = calc.add(2, 3)\n    assert result == 5",
  "coverage_impact": {
    "lines_covered": [10, 11, 12],
    "branches_covered": [1, 2]
  }
}
```

### Fields

- `function_name` (string, required): Name of the function being tested
- `test_name` (string, required): Name of the generated test function
- `test_type` (string, required): Type of test
  - Allowed values: `"unit"`, `"integration"`, `"edge_case"`
- `description` (string, required): What this test verifies
- `code` (string, required): The actual test code
- `coverage_impact` (object): Expected coverage information
  - `lines_covered` (array): Line numbers this test is expected to cover
  - `branches_covered` (array): Branch numbers this test is expected to cover

## Summary

The summary section provides overview statistics:

```json
{
  "total_functions": 5,
  "functions_with_tests": 4,
  "coverage_delta": 80.5
}
```

### Fields

- `total_functions` (integer, required): Total number of functions analyzed
- `functions_with_tests` (integer, required): Number of functions that have tests
- `coverage_delta` (number, required): Estimated coverage improvement from new tests (0-100)

## Extended Features

The schema can be extended to support additional features:

### Test Suite Organization

Group tests by source file:

```json
{
  "source_file": "src/calculator.py",
  "test_file": "tests/test_calculator.py",
  "framework": "pytest",
  "test_cases": [...]
}
```

#### Additional Fields

- `source_file` (string): Path to the source file being tested
- `test_file` (string): Path where the test file should be created/updated
- `framework` (string, enum): Testing framework to use
  - Allowed values: `"pytest"`, `"unittest"`, `"jest"`
  - Default: `"pytest"`

### Enhanced Test Cases

Additional test case details:

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

#### Additional Fields

- `target` (string): Function or class being tested
- `setup` (string): Any setup code needed (fixtures, mocks)
- `dependencies` (array): Required imports or fixtures

### Detailed Coverage Analysis

Enhanced coverage information:

```json
{
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

#### Additional Fields

- `coverage_estimate`: Detailed coverage information
  - `percentage` (number): Coverage percentage (0-100)
  - `gaps` (array): List of identified coverage gaps
    - `file` (string): File with missing coverage
    - `function` (string): Function lacking tests
    - `reason` (string): Why this needs coverage

## Complete Example with Extended Features

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
    "total_functions": 1,
    "functions_with_tests": 1,
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
