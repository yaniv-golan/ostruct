#!/bin/bash
# test_basic.sh - Basic functionality tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_INPUTS_DIR="$PROJECT_ROOT/risk_elimination_tests/test-inputs"

cd "$PROJECT_ROOT"

echo "=== Document Converter Basic Tests ==="
echo ""

# Check if test inputs exist
if [[ ! -d "$TEST_INPUTS_DIR" ]]; then
    echo "❌ Test inputs directory not found: $TEST_INPUTS_DIR"
    echo "Please ensure test documents are available"
    exit 1
fi

# Test 1: Tool availability check
echo "Test 1: Tool availability check"
if ./convert.sh --check-tools; then
    echo "✅ Tool check passed"
else
    echo "⚠️  Some tools missing, but continuing tests"
fi
echo ""

# Test 2: Help functionality
echo "Test 2: Help functionality"
if ./convert.sh --help >/dev/null; then
    echo "✅ Help command works"
else
    echo "❌ Help command failed"
    exit 1
fi
echo ""

# Test 3: Analysis only (dry test)
echo "Test 3: Analysis only test"
TEST_FILE="$TEST_INPUTS_DIR/f1040.pdf"
if [[ -f "$TEST_FILE" ]]; then
    echo "Testing analysis of: $(basename "$TEST_FILE")"
    if ./convert.sh --analyze-only "$TEST_FILE" >/dev/null 2>&1; then
        echo "✅ Analysis test passed"
    else
        echo "❌ Analysis test failed"
        exit 1
    fi
else
    echo "⚠️  Test file not found: $TEST_FILE"
fi
echo ""

# Test 4: Dry run test
echo "Test 4: Dry run test"
if [[ -f "$TEST_FILE" ]]; then
    echo "Testing dry run of: $(basename "$TEST_FILE")"
    if ./convert.sh --dry-run "$TEST_FILE" "output/test.md" >/dev/null 2>&1; then
        echo "✅ Dry run test passed"
    else
        echo "❌ Dry run test failed"
        exit 1
    fi
else
    echo "⚠️  Test file not found: $TEST_FILE"
fi
echo ""

# Test 5: Configuration loading
echo "Test 5: Configuration loading"
if [[ -f "config/default.conf" ]]; then
    echo "✅ Default configuration found"
else
    echo "❌ Default configuration missing"
    exit 1
fi
echo ""

# Test 6: Directory structure
echo "Test 6: Directory structure"
required_dirs=("prompts" "schemas" "tools" "config" "scripts")
for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "✅ $dir/ directory exists"
    else
        echo "❌ $dir/ directory missing"
        exit 1
    fi
done
echo ""

# Test 7: Required files
echo "Test 7: Required files"
required_files=(
    "prompts/analyze.j2"
    "prompts/plan.j2"
    "prompts/safety_check.j2"
    "prompts/validate.j2"
    "schemas/analysis.json"
    "schemas/plan.json"
    "schemas/safety.json"
    "schemas/validation.json"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        exit 1
    fi
done
echo ""

# Test 8: JSON schema validation
echo "Test 8: JSON schema validation"
for schema in schemas/*.json; do
    if jq empty "$schema" 2>/dev/null; then
        echo "✅ $(basename "$schema") is valid JSON"
    else
        echo "❌ $(basename "$schema") has invalid JSON"
        exit 1
    fi
done
echo ""

# Test 9: Script permissions
echo "Test 9: Script permissions"
scripts=("convert.sh" "scripts/check_tools.sh" "scripts/cleanup.sh")
for script in "${scripts[@]}"; do
    if [[ -x "$script" ]]; then
        echo "✅ $script is executable"
    else
        echo "❌ $script is not executable"
        exit 1
    fi
done
echo ""

echo "=== All Basic Tests Passed! ==="
echo ""
echo "Next steps:"
echo "1. Run './convert.sh --check-tools' to verify tool availability"
echo "2. Try a real conversion: './convert.sh test_file.pdf output.md'"
echo "3. Check logs in temp/logs/ for detailed information"
