# Test Generation Customization Guide

This guide explains how to customize the test generation process to match your project's needs.

## Test Framework Support

### Adding a New Framework

To add support for a new testing framework:

1. Update the schema in `schemas/test_cases.json`:

   ```json
   "framework": {
     "enum": ["pytest", "unittest", "jest", "your_framework"]
   }
   ```

2. Add framework-specific templates to the system prompt:

   ```text
   For your_framework, use these patterns:
   - Test function naming: test_*
   - Assertion style: assert_equals(actual, expected)
   - Setup functions: @before_each
   ```

### Framework-Specific Features

Each framework has unique features that can be utilized:

#### pytest

- Fixtures for setup/teardown
- Parametrized tests
- Marks for categorization

#### unittest

- setUp/tearDown methods
- Test class inheritance
- Test suites

#### jest

- describe/it blocks
- beforeEach/afterEach
- Mock functions

## Test Style Customization

### Naming Conventions

Modify the test naming pattern in the system prompt:

```text
Test names should follow the pattern:
test_{function_name}_{scenario_description}
```

### Assertion Style

Choose between different assertion styles:

```python
# Pytest style
assert result == expected

# unittest style
self.assertEqual(result, expected)

# Custom messages
assert result == expected, f"Expected {expected}, got {result}"
```

### Code Organization

Control test file organization:

```text
Group tests by:
1. Feature/component
2. Test type (unit/integration)
3. Functionality (happy path/edge cases)
```

## Coverage Configuration

### Setting Coverage Targets

Specify minimum coverage requirements:

```yaml
coverage:
  minimum_percentage: 80
  require_tests_for:
    - public_methods: true
    - private_methods: false
    - properties: true
```

### Gap Analysis

Configure what counts as a coverage gap:

```yaml
gaps:
  report_on:
    - untested_functions: true
    - partial_coverage: true
    - missing_edge_cases: true
  minimum_cases_per_function: 2
```

## Custom Assertions

### Adding Project-Specific Assertions

Create reusable custom assertions:

```python
# In conftest.py or test helpers
def assert_valid_user(user):
    assert 'id' in user
    assert 'username' in user
    assert 'email' in user
```

### Custom Validation Rules

Add domain-specific validation:

```python
validation_rules = {
    'user_data': [
        'check_username_format',
        'verify_email_domain',
        'validate_permissions'
    ]
}
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Generate Tests
on: [push, pull_request]

jobs:
  test-gen:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Generate Tests
        run: |
          ostruct \
            --task @prompts/task.j2 \
            --schema schemas/test_cases.json \
            --system-prompt @prompts/system.txt \
            --dir code=. \
            --ext py \
            --recursive
      - name: Run Generated Tests
        run: pytest
```

### Pre-commit Hooks

Add test generation to pre-commit:

```yaml
repos:
  - repo: local
    hooks:
      - id: generate-tests
        name: Generate Tests
        entry: bash run.sh
        language: system
        files: \.py$
```

## Advanced Features

### Mock Generation

Configure mock data generation:

```yaml
mocks:
  database:
    type: in_memory
    seed_data: test_data.json
  external_apis:
    type: mock_responses
    response_dir: test/responses
```

### Async Testing

Support for async code:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

### Parameterized Tests

Define test parameters:

```yaml
parameters:
  numeric_tests:
    - [0, 0, 0]
    - [1, 2, 3]
    - [-1, -2, -3]
  string_tests:
    - ["", "", ""]
    - ["a", "b", "ab"]
```
