# macOS Installation Script

This directory contains the macOS-specific installation components for ostruct.

## Quick Install

```bash
curl -sSL https://github.com/yaniv-golan/ostruct/releases/latest/download/install-macos.sh | bash
```

## Files

- `install.sh.template` - Template script with version placeholder
- `README.md` - This documentation

## What the Script Does

1. **Python Installation**: Automatically installs Python 3.10+ if not available
   - Tries Homebrew first (preferred method)
   - Falls back to official Python.org installer
   - Handles both Intel and Apple Silicon Macs

2. **Homebrew Setup**: Installs Homebrew if not present

3. **ostruct Installation**: Installs ostruct-cli via pip
   - Clears pip cache to ensure latest version
   - Uses fallback installation methods if needed
   - Verifies the installed version

4. **PATH Configuration**: Automatically configures shell PATH
   - Supports Bash, Zsh, and other shells
   - Adds Python user bin directory to PATH
   - Updates appropriate shell configuration file

## Features

- **Dry-run mode**: Test without making changes (`--dry-run`)
- **Smart Python detection**: Finds compatible Python installations
- **Architecture awareness**: Handles Intel and Apple Silicon Macs
- **Error recovery**: Multiple installation strategies
- **Version verification**: Ensures correct version is installed

## Development

The installation script is generated from `install.sh.template` during the build process. The template contains a `{{OSTRUCT_VERSION}}` placeholder that gets replaced with the actual version from `pyproject.toml`.

### Template Structure

The template includes:

- Version comparison functions
- Python installation logic
- PATH configuration
- Error handling and recovery
- Comprehensive logging and user feedback

### Testing

Use the dry-run mode to test without making changes:

```bash
./scripts/generated/install-macos.sh --dry-run
```

## Troubleshooting

### Common Issues

1. **Externally Managed Environment**: Recent Python installations may show this error
   - The script automatically uses `--user` flag to avoid this
   - Falls back to alternative installation methods

2. **PATH Issues**: Script automatically configures PATH
   - Restart terminal after installation
   - Or run: `source ~/.zshrc` (or appropriate shell config)

3. **Version Mismatch**: Script verifies correct version installation
   - Clears pip cache automatically
   - Uses multiple PyPI mirrors if needed

### Manual Installation

If the script fails, install manually:

```bash
# Ensure Python 3.10+
python3 --version

# Clear cache and install
python3 -m pip cache purge
python3 -m pip install --user --no-cache-dir --upgrade ostruct-cli

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify
ostruct --version
```

## Contributing

When modifying the macOS installation:

1. Edit `install.sh.template` (not the generated script)
2. Test with dry-run mode: `./scripts/generated/install-macos.sh --dry-run`
3. Use the validation scripts in `scripts/test/`
4. Run the build process: `make build-install-script`

The generated script is automatically created during the build process and should not be edited directly.
