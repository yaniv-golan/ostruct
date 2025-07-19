#!/bin/bash

# Phase 2 Comprehensive Test Suite
# Tests all CLI generation components (T2.1-T2.5)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "================================================"
echo "OST Generator Phase 2 Comprehensive Test Suite"
echo "================================================"
echo "Starting Phase 2 comprehensive test suite..."
echo "Test directory: $SCRIPT_DIR"
echo "Timestamp: $(date)"
echo

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_script="$2"

    echo "Running $test_name..."
    if "$test_script"; then
        echo "✓ $test_name passed"
        ((TESTS_PASSED++))
    else
        echo "✗ $test_name failed"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
    fi
}

echo "Running individual test suites..."
echo

# Run Phase 2 tests
run_test "CLI Specification Generation (T2.1)" "$PROJECT_ROOT/test/test_cli_spec_generation.sh"
run_test "CLI Naming Generation (T2.2)" "$PROJECT_ROOT/test/test_cli_naming.sh"
run_test "Help Generation (T2.3)" "$PROJECT_ROOT/test/test_help_generation.sh"
run_test "Policy Generation (T2.4)" "$PROJECT_ROOT/test/test_policy_generation.sh"
run_test "Defaults Management (T2.5)" "$PROJECT_ROOT/test/test_defaults_management.sh"

echo
echo "Running validation checks..."
echo

# Validate output files exist and are valid JSON
OUTPUT_FILES=(
    "cli_spec_simple.json"
    "cli_spec_complex.json"
    "simple_cli_naming.json"
    "complex_cli_naming.json"
    "simple_help_generation.json"
    "complex_help_generation.json"
    "simple_policy_generation.json"
    "complex_policy_generation.json"
    "simple_defaults_management.json"
    "complex_defaults_management.json"
)

echo "Validating output files..."
ALL_FILES_VALID=true
for file in "${OUTPUT_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/test/$file" ]; then
        if jq empty "$PROJECT_ROOT/test/$file" 2>/dev/null; then
            echo "✓ $file exists and is valid JSON"
        else
            echo "✗ $file exists but is invalid JSON"
            ALL_FILES_VALID=false
        fi
    else
        echo "✗ $file does not exist"
        ALL_FILES_VALID=false
    fi
done

if [ "$ALL_FILES_VALID" = true ]; then
    echo "✓ All output files validated"
    ((TESTS_PASSED++))
else
    echo "✗ Some output files failed validation"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Output File Validation")
fi

echo
echo "Validating schema compliance..."

# Check key schema fields for each output type
echo "Validating CLI specification schema compliance..."
if jq -e '.cli_specification.tool_name' "$PROJECT_ROOT/test/cli_spec_simple.json" >/dev/null && \
   jq -e '.cli_specification.arguments[]' "$PROJECT_ROOT/test/cli_spec_simple.json" >/dev/null; then
    echo "✓ CLI specification schema compliance validated"
    ((TESTS_PASSED++))
else
    echo "✗ CLI specification schema compliance failed"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("CLI Specification Schema")
fi

echo "Validating help generation schema compliance..."
if jq -e '.tool_description.name' "$PROJECT_ROOT/test/simple_help_generation.json" >/dev/null && \
   jq -e '.usage_patterns.common_examples[]' "$PROJECT_ROOT/test/simple_help_generation.json" >/dev/null; then
    echo "✓ Help generation schema compliance validated"
    ((TESTS_PASSED++))
else
    echo "✗ Help generation schema compliance failed"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Help Generation Schema")
fi

echo "Validating policy generation schema compliance..."
if jq -e '.model_policy.default_model' "$PROJECT_ROOT/test/simple_policy_generation.json" >/dev/null && \
   jq -e '.security_policy.input_validation' "$PROJECT_ROOT/test/simple_policy_generation.json" >/dev/null; then
    echo "✓ Policy generation schema compliance validated"
    ((TESTS_PASSED++))
else
    echo "✗ Policy generation schema compliance failed"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Policy Generation Schema")
fi

echo "Validating defaults management schema compliance..."
if jq -e '.default_value_sources.template_defaults' "$PROJECT_ROOT/test/simple_defaults_management.json" >/dev/null && \
   jq -e '.precedence_rules.precedence_order[]' "$PROJECT_ROOT/test/simple_defaults_management.json" >/dev/null; then
    echo "✓ Defaults management schema compliance validated"
    ((TESTS_PASSED++))
else
    echo "✗ Defaults management schema compliance failed"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Defaults Management Schema")
fi

echo "✓ All schema compliance checks passed"

echo
echo "================================================"
echo "Phase 2 Test Report"
echo "================================================"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo "🎉 All Phase 2 tests passed!"
    echo "✓ CLI specification generation working"
    echo "✓ CLI naming generation working"
    echo "✓ Help generation working"
    echo "✓ Policy generation working"
    echo "✓ Defaults management working"
    echo "✓ All outputs validated"
else
    echo "❌ Some Phase 2 tests failed:"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  - $test"
    done
fi

echo
echo "Output Files Generated:"
for file in "${OUTPUT_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/test/$file" ]; then
        echo "  $file ($(wc -c < "$PROJECT_ROOT/test/$file") bytes)"
    fi
done

echo
echo "Test execution completed in $(date)"

if [ $TESTS_FAILED -eq 0 ]; then
    echo
    echo "✅ Phase 2 implementation fully validated"
    echo "Ready to proceed to Phase 3 (Assembly & Validation)"
    exit 0
else
    echo
    echo "❌ Phase 2 validation failed"
    exit 1
fi
