# Build Automation Scripts

This directory contains build automation tools for the ostruct project.

## Scripts

### `validate-release.py`

Comprehensive release validation tool.

**Purpose**:

- Validates version consistency across files
- Checks pyproject.toml configuration
- Tests package building
- Validates dependency resolution
- Runs test suite
- Checks documentation builds
- Tests clean installation

**Usage**:

```bash
python3 scripts/build/validate-release.py
```

## Integration

### Makefile Targets

These scripts are integrated into the project Makefile:

```bash
make check-version         # Show current version
make clean                 # Clean generated files
```

### CI/CD Integration

The build scripts are automatically run during GitHub Actions workflows:

- **Pre-release**: `validate-release.py` ensures release readiness

### Development Workflow

1. **Make Changes**: Edit source code
2. **Test**: Use scripts in `scripts/test/` to validate
3. **Validate**: Run `scripts/build/validate-release.py` before release

## Dependencies

- **Python 3.10+**: Required for all build scripts
- **Standard Library**: Uses only built-in modules for maximum compatibility
- **Project Dependencies**: Validates against project's pyproject.toml

## File Structure

```
scripts/build/
├── README.md                  # This documentation
└── validate-release.py       # Release validation tool
```

## Contributing

When adding new build automation:

1. **Single Responsibility**: Each script should have one clear purpose
2. **Error Handling**: Provide clear error messages and exit codes
3. **Documentation**: Update this README and add docstrings
4. **Integration**: Add Makefile targets and CI integration as needed
5. **Testing**: Create corresponding test scripts in `scripts/test/`

### Standards

- Use Python 3.10+ type hints
- Follow PEP 8 style guidelines
- Provide clear command-line output
- Exit with appropriate status codes (0 = success, 1+ = error)
- Use pathlib for cross-platform file operations
