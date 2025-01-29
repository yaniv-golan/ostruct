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
├── run.sh             # Runner script
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

   ```bash
   # Using bash directly (no executable permission needed)
   bash run.sh path/to/your/code
   ```

2. **With Specific Framework**:

   ```bash
   bash run.sh --framework pytest path/to/your/code
   ```

3. **Generate Missing Tests Only**:

   ```bash
   bash run.sh --mode missing path/to/your/code
   ```

## Customization

See `docs/customization.md` for detailed instructions on:

- Supporting additional test frameworks
- Customizing test generation style
- Adding custom assertions
- Integrating with CI/CD

## Schema

The test generation results follow a structured schema defined in `schemas/test_cases.json`. See `docs/schema.md` for:

- Complete schema documentation
- Test case structure
- Framework-specific outputs

## Integration

### GitHub Actions

```yaml
- name: Generate Tests
  run: |
    ostruct \
      --task @prompts/task.j2 \
      --schema schemas/test_cases.json \
      --system-prompt @prompts/system.txt \
      --dir code=. \
      --dir-ext py \
      --dir-recursive \
      --var framework=pytest
```

### GitLab CI

```yaml
test_generation:
  script:
    - ostruct --task @prompts/task.j2 --schema schemas/test_cases.json --system-prompt @prompts/system.txt --dir code=. --dir-ext py --dir-recursive
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

## Prerequisites

- OpenAI Structured CLI installed
- OpenAI API key configured
- Python code to test (for Python examples)

## Limitations

- Complex mocking scenarios may need manual refinement
- Some edge cases might require human review
- Framework-specific features may vary
