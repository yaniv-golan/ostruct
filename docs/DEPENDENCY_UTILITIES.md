# Dependency Installation Utilities

Centralized utilities for installing common tools across examples.

## Problem

Utility scripts like `ensure_jq.sh` were duplicated across examples, causing maintenance overhead and inconsistency.

## Solution

Centralized dependency installation utilities in `scripts/install/dependencies/` that can be sourced by any example.

## Directory Structure

```
scripts/install/dependencies/
├── README.md              # Usage documentation
├── ensure_jq.sh          # JSON processor installation
└── ensure_mermaid.sh     # Mermaid CLI installation
```

## Usage

### In Scripts

```bash
#!/usr/bin/env bash
set -euo pipefail

# Source required dependencies
source "$(dirname "$0")/../../scripts/install/dependencies/ensure_jq.sh"
source "$(dirname "$0")/../../scripts/install/dependencies/ensure_mermaid.sh"

# Your script logic here...
```

### Return Codes

- `0`: Tool is available
- `1`: Installation failed

### Environment Variables

- `OSTRUCT_SKIP_AUTO_INSTALL`: Skip automatic installation
- `OSTRUCT_PREFER_DOCKER`: Prefer Docker-based tools

## Installation Strategies

Each utility tries multiple approaches:

1. Check if tool already exists
2. System package manager (apt, yum, brew, etc.)
3. Direct binary download
4. Docker wrapper
5. Manual instructions

## Testing

```bash
# Test utilities
make test-dependencies

# Test without installing
OSTRUCT_SKIP_AUTO_INSTALL=1 scripts/install/dependencies/ensure_jq.sh
```

## Adding New Utilities

1. Create `scripts/install/dependencies/ensure_newtool.sh`
2. Follow existing patterns for error handling and logging
3. Add tests to `scripts/test/unit/test-dependency-utilities.sh`
4. Update this documentation
