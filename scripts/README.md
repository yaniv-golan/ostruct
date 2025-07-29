# ostruct Scripts Directory

This directory contains all automation scripts for the ostruct project, organized by function following industry best practices.

## Directory Structure

```
scripts/
├── README.md              # This overview documentation
├── build/                 # Build automation and release tools
│   ├── validate-release.py      # Release validation
│   └── README.md                # Build tools documentation
├── install/               # Installation utilities
│   └── dependencies/     # Reusable dependency installation utilities
│       ├── ensure_jq.sh         # JSON processor installation
│       └── ensure_mermaid.sh    # Mermaid CLI installation
│       # See docs/DEPENDENCY_UTILITIES.md for detailed usage
├── test/                  # Testing utilities organized by type
│   ├── unit/              # Unit tests for individual components
│   │   └── test-version-compare.sh
│   ├── integration/       # Integration tests for workflows
│   │   └── validate-install-script.sh
│   ├── docker/           # Containerized environment tests
│   │   └── test-install.sh
│   └── README.md         # Testing documentation
└── generated/            # Build artifacts (git-ignored)
```

## Quick Start

### For Developers - Build Scripts

```bash
# Run all tests
find scripts/test -name "*.sh" -executable -exec {} \;

# Validate release readiness
python3 scripts/build/validate-release.py

# Simulate CI environment locally (catch issues before CI)
./scripts/test-like-ci.sh
```

## Key Features

### 🏗️ **Build Automation** (`build/`)

- **Release Validation**: Comprehensive pre-release checks
- **CI/CD Integration**: Automated workflow integration

### 📦 **Installation Utilities** (`install/`)

- **Dependency Installation**: Centralized utilities for common tools (jq, Mermaid CLI)
- **Reusable Components**: DRY principle applied to dependency installation

### 🧪 **Comprehensive Testing** (`test/`)

- **Unit Tests**: Fast, focused component testing
- **Integration Tests**: Workflow and component interaction testing
- **Docker Tests**: Clean environment, end-to-end testing
- **CI Simulation**: `test-like-ci.sh` - Run full CI suite locally to catch environment-specific issues
- **Organized by Type**: Clear separation of test categories

## Development Workflow

### Making Changes

1. **Test**: Use scripts in `test/` to validate changes
2. **CI Simulation**: Run `./scripts/test-like-ci.sh` to catch environment-specific issues
3. **Validate**: Run `scripts/build/validate-release.py` before release

### Adding New Tests

1. **Choose Category**: unit/ integration/ or docker/
2. **Follow Naming**: `test-{component}.sh` or `validate-{feature}.sh`
3. **Use Standards**: Clear output, proper exit codes, documentation
4. **Integration**: Add to CI/CD workflows as appropriate

## Integration

### Makefile Targets

```bash
make check-version         # Show current version
make clean                 # Clean generated files
make test                  # Run project tests
```

### GitHub Actions

- **On Release**: Runs validation and integration tests
- **On PR**: Runs validation and integration tests
- **On Commit**: Runs unit tests and quick validation

## Best Practices Implemented

### 🏗️ **Industry Standards**

- **Separation of Concerns**: Build, install, test clearly separated
- **Documentation Strategy**: Context-specific docs co-located with code

### 📚 **GitHub Conventions**

- **Standard Directory Names**: Following common patterns (build/, test/, etc.)
- **Clear Hierarchy**: Logical grouping by function
- **Comprehensive Documentation**: README files at every level
- **CI/CD Integration**: Standard workflow patterns

### 🔧 **Software Engineering**

- **Single Responsibility**: Each script has one clear purpose
- **Error Handling**: Comprehensive error recovery and user feedback
- **Testing Strategy**: Unit, integration, and system testing

## Contributing

### For Build Tools

1. Maintain Python 3.10+ compatibility
2. Use only standard library for maximum portability
3. Provide clear error messages and exit codes
4. Update build documentation

### For Tests

1. Follow testing hierarchy (unit → integration → docker)
2. Use clear pass/fail indicators
3. Provide meaningful error messages
4. Keep tests fast and reliable

This organization provides a **scalable, maintainable foundation** for build automation and testing while following **industry best practices** for script organization.
