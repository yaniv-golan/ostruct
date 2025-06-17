# Test Generation Customization Guide

This guide explains how to customize the test generation process to match your project's needs.

## Test Framework Support

### Adding a New Framework

To add support for a new testing framework:

1. Update the template in `prompts/task.j2` to handle the new framework:

   ```jinja2
   {% if framework == "your_framework" %}
   // Your framework-specific test patterns
   {% else %}
   // Default patterns
   {% endif %}
   ```

2. Add framework-specific patterns to the system prompt in `prompts/system.txt`:

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

Specify minimum coverage requirements in your command:

```bash
ostruct run prompts/task.j2 schemas/test_cases.json \
  --dir code path/to/your/code \
  --recursive \
  --sys-file prompts/system.txt \
  -V framework=pytest \
  -V min_coverage=80
```

### Gap Analysis

Configure what counts as a coverage gap:

```bash
ostruct run prompts/task.j2 schemas/test_cases.json \
  --dir code path/to/your/code \
  --recursive \
  --sys-file prompts/system.txt \
  -V framework=pytest \
  -V min_cases_per_function=2 \
  -V analyze_private_methods=false
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
          ostruct run prompts/task.j2 schemas/test_cases.json \
            --dir code . \
            --recursive \
            --sys-file prompts/system.txt \
            -V framework=pytest
      - name: Run Generated Tests
        run: pytest
```

### Pre-commit Configuration

Add test generation to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: generate-tests
        name: Generate Tests
        entry: ostruct run prompts/task.j2 schemas/test_cases.json --dir code . --recursive --sys-file prompts/system.txt -V framework=pytest
        language: python
        files: \.py$
```

## Advanced Features

### Mock Generation

Configure mock data generation:

```bash
ostruct run prompts/task.j2 schemas/test_cases.json \
  --dir code path/to/your/code \
  --recursive \
  --sys-file prompts/system.txt \
  -V framework=pytest \
  -V mock_config='{"database": "in_memory", "apis": "mock_responses"}'
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

```python
@pytest.mark.parametrize("input,expected", [
    (0, 0),
    (1, 1),
    (-1, 1)
])
def test_abs(input, expected):
    assert abs(input) == expected
```
