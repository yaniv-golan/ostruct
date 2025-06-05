# ostruct Scripts Directory

This directory contains all automation scripts for the ostruct project, organized by function following industry best practices.

## Directory Structure

```
scripts/
├── README.md              # This overview documentation
├── build/                 # Build automation and release tools
│   ├── build-install-script.py  # Generate installation scripts
│   ├── validate-release.py      # Release validation
│   └── README.md                # Build tools documentation
├── install/               # Installation scripts by platform
│   ├── macos/
│   │   ├── install.sh.template  # macOS installation template
│   │   └── README.md            # macOS-specific documentation
│   └── dependencies/     # Reusable dependency installation utilities
│       ├── ensure_jq.sh         # JSON processor installation
│       ├── ensure_mermaid.sh    # Mermaid CLI installation
│       └── README.md            # Dependency utilities documentation
├── test/                  # Testing utilities organized by type
│   ├── unit/              # Unit tests for individual components
│   │   └── test-version-compare.sh
│   ├── integration/       # Integration tests for workflows
│   │   └── validate-install-script.sh
│   ├── docker/           # Containerized environment tests
│   │   └── test-install.sh
│   └── README.md         # Testing documentation
└── generated/            # Build artifacts (git-ignored)
    └── install-macos.sh  # Generated installation script
```

## Quick Start

### For Users - Install ostruct

```bash
# macOS one-line installer
curl -sSL https://raw.githubusercontent.com/yaniv-golan/ostruct/main/scripts/generated/install-macos.sh | bash
```

### For Developers - Build Scripts

```bash
# Generate installation scripts
make build-install-script

# Run all tests
find scripts/test -name "*.sh" -executable -exec {} \;

# Validate release readiness
python3 scripts/build/validate-release.py
```

## Key Features

### 🏗️ **Build Automation** (`build/`)

- **Dynamic Version Management**: Automatically extracts version from `pyproject.toml`
- **Template System**: Generates scripts from templates with placeholders
- **Release Validation**: Comprehensive pre-release checks
- **CI/CD Integration**: Automated workflow integration

### 📦 **Platform-Specific Installation** (`install/`)

- **macOS Support**: Complete automated setup for macOS (Intel + Apple Silicon)
- **Dependency Installation**: Centralized utilities for common tools (jq, Mermaid CLI)
- **Extensible**: Structure ready for Windows, Linux support
- **Smart Detection**: Automatically handles Python, Homebrew, PATH configuration
- **Error Recovery**: Multiple installation strategies with fallbacks
- **Reusable Components**: DRY principle applied to dependency installation

### 🧪 **Comprehensive Testing** (`test/`)

- **Unit Tests**: Fast, focused component testing
- **Integration Tests**: Workflow and component interaction testing
- **Docker Tests**: Clean environment, end-to-end testing
- **Organized by Type**: Clear separation of test categories

### ⚙️ **Dynamic Version System**

- **No Manual Updates**: Version automatically extracted from `pyproject.toml`
- **Template-Based**: Single source of truth for version information
- **Build-Time Generation**: Scripts generated during build process
- **Version Verification**: Installation scripts verify correct version

## Development Workflow

### Making Changes

1. **Edit Templates**: Modify `install/*/install.sh.template` (not generated scripts)
2. **Build**: Run `make build-install-script` to generate final scripts
3. **Test**: Use scripts in `test/` to validate changes
4. **Validate**: Run `scripts/build/validate-release.py` before release

### Adding New Platforms

1. **Create Platform Directory**: `install/{platform}/`
2. **Add Template**: `install.sh.template` with platform-specific logic
3. **Update Build Script**: Add platform to `build/build-install-script.py`
4. **Add Tests**: Create platform-specific tests in `test/`
5. **Document**: Add platform README and update main docs

### Adding New Tests

1. **Choose Category**: unit/ integration/ or docker/
2. **Follow Naming**: `test-{component}.sh` or `validate-{feature}.sh`
3. **Use Standards**: Clear output, proper exit codes, documentation
4. **Integration**: Add to CI/CD workflows as appropriate

## Integration

### Makefile Targets

```bash
make build-install-script  # Generate installation scripts
make check-version         # Show current version
make clean                 # Clean generated files
make test                  # Run project tests
```

### GitHub Actions

- **On Release**: Automatically generates installation scripts
- **On PR**: Runs validation and integration tests
- **On Commit**: Runs unit tests and quick validation

### Git Integration

- **Generated files**: Automatically ignored in `.gitignore`
- **Templates tracked**: Source templates are version controlled
- **Build artifacts**: Generated scripts excluded from repository

## Best Practices Implemented

### 🏗️ **Industry Standards**

- **Separation of Concerns**: Build, install, test clearly separated
- **Platform Organization**: Ready for multi-platform support
- **Documentation Strategy**: Context-specific docs co-located with code
- **Template Pattern**: Clean separation of logic and configuration

### 📚 **GitHub Conventions**

- **Standard Directory Names**: Following common patterns (build/, test/, etc.)
- **Clear Hierarchy**: Logical grouping by function
- **Comprehensive Documentation**: README files at every level
- **CI/CD Integration**: Standard workflow patterns

### 🔧 **Software Engineering**

- **Single Responsibility**: Each script has one clear purpose
- **Dependency Injection**: Version information injected at build time
- **Error Handling**: Comprehensive error recovery and user feedback
- **Testing Strategy**: Unit, integration, and system testing

## Contributing

### For Installation Scripts

1. Edit templates in `install/{platform}/`
2. Test with dry-run mode and validation scripts
3. Update platform-specific documentation
4. Ensure cross-platform compatibility where possible

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

This organization provides a **scalable, maintainable foundation** for supporting multiple platforms while following **industry best practices** for script organization and automation.
