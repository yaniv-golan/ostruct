# Build Automation Scripts

This directory contains build automation tools for the ostruct project.

## Scripts

### `build-install-script.py`

Generates the macOS installation script from template with the current version.

**Purpose**:

- Extracts version from `pyproject.toml`
- Replaces `{{OSTRUCT_VERSION}}` placeholder in template
- Generates final installation script in `scripts/generated/`

**Usage**:

```bash
# Via Makefile (recommended)
make build-install-script

# Direct execution
python3 scripts/build/build-install-script.py
```

**Input**: `scripts/install/macos/install.sh.template`
**Output**: `scripts/generated/install-macos.sh`

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
make build-install-script  # Generate installation script
make check-version         # Show current version
make clean                 # Clean generated files
```

### CI/CD Integration

The build scripts are automatically run during GitHub Actions workflows:

- **On Release**: `build-install-script.py` generates the installation script
- **Pre-release**: `validate-release.py` ensures release readiness

### Development Workflow

1. **Make Changes**: Edit templates or source code
2. **Build**: Run `make build-install-script` to generate artifacts
3. **Test**: Use scripts in `scripts/test/` to validate
4. **Validate**: Run `scripts/build/validate-release.py` before release

## Dependencies

- **Python 3.10+**: Required for all build scripts
- **Standard Library**: Uses only built-in modules for maximum compatibility
- **Project Dependencies**: Validates against project's pyproject.toml

## File Structure

```
scripts/build/
├── README.md                  # This documentation
├── build-install-script.py   # Installation script generator
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
