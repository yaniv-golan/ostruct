# Dependency Installation Utilities

This directory contains reusable dependency installation scripts that can be sourced by examples and other scripts throughout the project.

## Available Utilities

### Core Tools

- `ensure_jq.sh` - JSON processor installation and verification
- `ensure_mermaid.sh` - Mermaid CLI installation and verification

### Usage Pattern

All utilities follow the same interface:

```bash
# Source the utility (preferred method)
source "$(dirname "$0")/../../scripts/install/dependencies/ensure_jq.sh"

# Or call directly
"$(dirname "$0")/../../scripts/install/dependencies/ensure_jq.sh"
```

### Return Codes

- `0` - Tool is available and ready to use
- `1` - Installation failed, tool not available

### Environment Variables

- `OSTRUCT_SKIP_AUTO_INSTALL` - Set to skip automatic installation attempts
- `OSTRUCT_PREFER_DOCKER` - Prefer Docker-based tools when available

## Adding New Utilities

When adding new dependency utilities:

1. Follow the naming convention: `ensure_<toolname>.sh`
2. Include comprehensive platform support
3. Provide multiple installation strategies
4. Add graceful fallbacks (Docker, manual instructions)
5. Update this README with the new utility
6. Test across platforms (Linux, macOS, Windows/WSL)

## Integration Examples

### In Example Scripts

```bash
#!/usr/bin/env bash
set -euo pipefail

# Get script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source required dependencies
source "$SCRIPT_DIR/../../scripts/install/dependencies/ensure_jq.sh"
source "$SCRIPT_DIR/../../scripts/install/dependencies/ensure_mermaid.sh"

# Your script logic here...
```

### In CI/CD Workflows

```yaml
- name: Install dependencies
  run: |
    source scripts/install/dependencies/ensure_jq.sh
    source scripts/install/dependencies/ensure_mermaid.sh
```

## Design Principles

### Cross-Platform Compatibility

- Detect OS and architecture automatically
- Use appropriate package managers per platform
- Provide manual installation instructions as fallback

### Multiple Installation Strategies

1. **System Package Manager** (apt, yum, brew, etc.)
2. **Direct Binary Download** (GitHub releases, official sites)
3. **Container-based** (Docker wrappers)
4. **Manual Instructions** (when automation fails)

### Error Handling

- Clear error messages with actionable instructions
- Graceful degradation when possible
- Proper exit codes for automation

### Security Considerations

- Verify checksums when downloading binaries
- Use HTTPS for all downloads
- Minimal privilege requirements
- No automatic sudo without user consent
