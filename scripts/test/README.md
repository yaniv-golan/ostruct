# Test Scripts

This directory contains testing utilities for the ostruct scripts and installation processes.

## Organization

### `unit/` - Unit Tests

Small, focused tests for individual functions or components.

- `test-version-compare.sh` - Tests version comparison logic

### `integration/` - Integration Tests

Tests that verify components work together correctly.

### `docker/` - Containerized Tests

Tests that run in isolated Docker environments.

## Running Tests

### Individual Test Categories

```bash
# Run unit tests
./scripts/test/unit/test-version-compare.sh

# Run integration tests
# (No integration tests currently available)

# Run Docker tests
# (No Docker tests currently available)

# (No example validation currently available)
```

### All Tests

```bash
# Run all test categories
find scripts/test -name "*.sh" -executable -exec {} \;
```

## Test Types

### Unit Tests (`unit/`)

**Purpose**: Test individual functions in isolation
**Scope**: Single function or small component
**Speed**: Fast (< 1 second)
**Dependencies**: Minimal, self-contained

**Example**: Testing version comparison logic without full installation

### Integration Tests (`integration/`)

**Purpose**: Test component interactions
**Scope**: Multiple components working together
**Speed**: Medium (1-10 seconds)
**Dependencies**: May require system tools

**Example**: Testing component interactions and workflows

### Docker Tests (`docker/`)

**Purpose**: Test in clean, isolated environments
**Scope**: Full system behavior
**Speed**: Slow (30+ seconds)
**Dependencies**: Docker runtime

**Example**: Testing in isolated environments

## Test Standards

### Naming Convention

- Unit tests: `test-{component}.sh`
- Integration tests: `validate-{feature}.sh`
- Docker tests: `test-{scenario}.sh`

### Exit Codes

- `0` - All tests passed
- `1` - Test failures
- `2` - Test setup/environment errors

### Output Format

- Clear pass/fail indicators (✅/❌)
- Descriptive test names
- Summary of results
- Error details for failures

### Test Structure

```bash
#!/bin/bash
echo "Testing {component}..."
echo ""

# Test 1: Description
if test_condition; then
    echo "✅ Test 1: PASS"
else
    echo "❌ Test 1: FAIL"
fi

echo ""
echo "Test summary: X/Y passed"
```

## Adding New Tests

### For New Features

1. **Start with unit tests** for core logic
2. **Add integration tests** for component interaction
3. **Add Docker tests** for end-to-end validation

### For Bug Fixes

1. **Create failing test** that reproduces the bug
2. **Fix the bug**
3. **Verify test now passes**

### Guidelines

- **One concern per test script**
- **Clear, descriptive test names**
- **Comprehensive error messages**
- **Fast feedback for common cases**
- **Thorough coverage for edge cases**

## Continuous Integration

Tests are run automatically in GitHub Actions:

- **Unit tests**: Run on every commit
- **Integration tests**: Run on pull requests
- **Docker tests**: Run on release preparation

### Local Development

Run tests before committing:

```bash
# Quick validation
make test-unit

# Full validation
make test-all
```

## Dependencies

### System Requirements

- **Bash 4.0+**: For test script execution
- **Docker**: For containerized tests (optional)
- **Core utilities**: grep, sed, curl, etc.

### Project Dependencies

- Tests should work with project as installed
- Use same dependencies as main codebase
- Avoid test-specific external dependencies

## Troubleshooting

### Common Issues

1. **Permission errors**: Ensure test scripts are executable

   ```bash
   chmod +x scripts/test/**/*.sh
   ```

2. **Docker not available**: Skip Docker tests in CI without Docker

   ```bash
   if ! command -v docker >/dev/null; then
       echo "Skipping Docker tests - Docker not available"
       exit 0
   fi
   ```

3. **Slow tests**: Use timeouts and early exits

   ```bash
   timeout 30s test_command || echo "Test timed out"
   ```

## Best Practices

- **Fast feedback**: Unit tests should complete quickly
- **Reliable**: Tests should not be flaky or environment-dependent
- **Isolated**: Tests should not affect each other
- **Comprehensive**: Cover happy path and error cases
- **Maintainable**: Keep tests simple and focused
