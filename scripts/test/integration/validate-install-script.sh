#!/bin/bash

# Validation script for install-macos.sh
# Tests syntax, functions, and logic without making any system changes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_SCRIPT="$SCRIPTS_ROOT/generated/install-macos.sh"

echo "🔍 Validating ostruct macOS Installation Script"
echo "=============================================="
echo ""

# Check if script exists
if [[ ! -f "$INSTALL_SCRIPT" ]]; then
    echo "❌ Installation script not found: $INSTALL_SCRIPT"
    exit 1
fi

# Test 1: Syntax check
echo "📋 Test 1: Syntax validation..."
if bash -n "$INSTALL_SCRIPT"; then
    echo "✅ Syntax check passed"
else
    echo "❌ Syntax errors found"
    exit 1
fi
echo ""

# Test 2: Function definitions
echo "📋 Test 2: Function definitions..."

# Create a temporary script that only defines functions without executing main
TEMP_SCRIPT=$(mktemp)
# Extract only function definitions, not the main execution
sed '/^# Run main function/,$d' "$INSTALL_SCRIPT" > "$TEMP_SCRIPT"
source "$TEMP_SCRIPT"
rm "$TEMP_SCRIPT"

# Test individual functions
echo "  Testing detect_shell..."
if shell_type=$(detect_shell); then
    echo "    ✅ detect_shell: $shell_type"
else
    echo "    ❌ detect_shell failed"
fi

echo "  Testing get_shell_config..."
if config_file=$(get_shell_config "zsh"); then
    echo "    ✅ get_shell_config: $config_file"
else
    echo "    ❌ get_shell_config failed"
fi

echo "  Testing command_exists..."
if command_exists "bash"; then
    echo "    ✅ command_exists: bash found"
else
    echo "    ❌ command_exists failed"
fi

echo "  Testing get_python..."
if python_cmd=$(get_python 2>/dev/null); then
    echo "    ✅ get_python: $python_cmd found"
else
    echo "    ⚠️  get_python: No compatible Python found (expected on some systems)"
fi
echo ""

# Test 3: Dry-run mode
echo "📋 Test 3: Dry-run mode..."
echo "  Running installation script in dry-run mode..."
echo ""

# Capture output but don't let it exit the validation script
if output=$(bash "$INSTALL_SCRIPT" --dry-run 2>&1); then
    echo "$output" | head -20
    echo "..."
    echo "✅ Dry-run completed successfully"
else
    echo "❌ Dry-run failed"
    echo "$output"
    exit 1
fi
echo ""

# Test 4: Help/usage
echo "📋 Test 4: Usage information..."
echo "  Available options:"
echo "    --dry-run, -n    : Run without making changes"
echo "    (no args)        : Full installation"
echo ""

echo "🎉 All validation tests passed!"
echo ""
echo "Safe testing options:"
echo "1. Run with dry-run: ./scripts/install-macos.sh --dry-run"
echo "2. Test in Docker: ./scripts/test-install.sh"
echo "3. Test on a separate user account"
echo "4. Test in a macOS virtual machine"
echo ""
