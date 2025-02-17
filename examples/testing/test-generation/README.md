# Test Case Generation & Optimization

This use case demonstrates how to automatically generate and optimize test cases for your codebase using the OpenAI Structured CLI. It analyzes your code to create comprehensive test suites, identify coverage gaps, and suggest improvements to existing tests.

## Features

- Automatic test case generation for untested functions
- Coverage gap identification and reporting
- Test suite optimization suggestions
- Support for multiple testing frameworks (pytest, unittest)
- Integration with existing test suites

## Directory Structure

```
.
├── README.md           # This file
├── prompts/           # AI prompts
│   ├── system.txt     # AI's role and expertise
│   └── task.j2        # Test generation template
├── schemas/           # Output structure
│   └── test_cases.json
├── examples/          # Sample code to test
│   ├── untested/      # Code without tests
│   │   ├── calculator.py     # Basic arithmetic operations
│   │   └── data_processor.py # Data transformation functions
│   ├── partial/       # Code with incomplete tests
│   │   ├── user_service.py   # User management with gaps
│   │   └── test_user_service.py  # Existing partial tests
│   └── complex/       # Complex testing scenarios
│       └── async_worker.py   # Async operations
└── docs/             # Documentation
    ├── customization.md  # How to customize
    └── schema.md        # Schema reference
```

## Usage

1. **Basic Usage**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/test_cases.json \
     -d code path/to/your/code \
     -R \
     --sys-file prompts/system.txt \
     -V framework=pytest
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/test_cases.json \
     -d code examples/untested \
     -R \
     --sys-file prompts/system.txt \
     -V framework=pytest
   ```

2. **With Different Framework**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/test_cases.json \
     -d code path/to/your/code \
     -R \
     --sys-file prompts/system.txt \
     -V framework=unittest
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/test_cases.json \
     -d code examples/complex \
     -R \
     --sys-file prompts/system.txt \
     -V framework=unittest
   ```

3. **Generate Missing Tests Only**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/test_cases.json \
     -d code path/to/your/code \
     -R \
     --sys-file prompts/system.txt \
     -V framework=pytest \
     -V mode=missing
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/test_cases.json \
     -d code examples/partial \
     -R \
     --sys-file prompts/system.txt \
     -V framework=pytest \
     -V mode=missing
   ```

4. **Output to File**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/test_cases.json \
     -d code path/to/your/code \
     -R \
     --sys-file prompts/system.txt \
     -V framework=pytest \
     --output-file test_results.json
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/test_cases.json \
     -d code examples/untested \
     -R \
     --sys-file prompts/system.txt \
     -V framework=pytest \
     --output-file untested_results.json
   ```

## Example Files

1. **Calculator (Untested)**
   - Basic arithmetic operations
   - Type hints and docstrings
   - Edge cases (division by zero)

2. **Data Processor (Untested)**
   - Date format normalization
   - Deep dictionary merging
   - Nested value extraction
   - JSON validation

3. **User Service (Partial Tests)**
   - User management and authentication
   - Database interaction
   - Session handling
   - Existing tests for basic functionality
   - Missing tests for edge cases

4. **Async Worker (Complex)**
   - Asynchronous job queue
   - Priority handling
   - Timeout and retry logic
   - Complex state management

## Customization

See `docs/customization.md` for detailed instructions on:

- Supporting additional test frameworks
- Customizing test generation style
- Adding custom assertions
- Integrating with CI/CD

## Schema

The test generation results follow a structured schema defined in `schemas/test_cases.json`. The output is a JSON object containing:

1. `test_cases`: Array of test cases, each with:
   - `function_name`: Name of the function being tested
   - `test_name`: Name of the test function
   - `test_type`: One of "unit", "integration", or "edge_case"
   - `description`: What the test verifies
   - `code`: The actual test code
   - `lines_covered`: Comma-separated list of line numbers this test is expected to cover
   - `branches_covered`: Comma-separated list of branch numbers this test is expected to cover

2. `summary`: Object with:
   - `total_functions`: Number of functions analyzed
   - `functions_with_tests`: Number of functions that have tests
   - `coverage_delta`: Estimated coverage improvement

Example output:

```json
{
  "test_cases": [
    {
      "function_name": "add",
      "test_name": "test_add_positive",
      "test_type": "unit",
      "description": "Test addition of two positive numbers",
      "code": "def test_add_positive():\n    result = add(2, 3)\n    assert result == 5",
      "lines_covered": "1,2",
      "branches_covered": "1"
    }
  ],
  "summary": {
    "total_functions": 1,
    "functions_with_tests": 1,
    "coverage_delta": 0.8
  }
}
```

## Integration

### GitHub Actions

```yaml
- name: Generate Tests
  run: |
    ostruct run prompts/task.j2 schemas/test_cases.json \
      -d code . \
      -R \
      --sys-file prompts/system.txt \
      -V framework=pytest
```

### GitLab CI

```yaml
test_generation:
  script:
    - ostruct run prompts/task.j2 schemas/test_cases.json \
        -d code . \
        -R \
        --sys-file prompts/system.txt \
        -V framework=pytest
```

## Prerequisites

- OpenAI Structured CLI installed
- OpenAI API key configured
- Python code to test (for Python examples)

## Limitations

- Complex mocking scenarios may need manual refinement
- Some edge cases might require human review
- Framework-specific features may vary
