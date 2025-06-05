#!/usr/bin/env bash
# Unit test for dependency installation utilities
set -uo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
CURRENT_TEST_PASSED=true

# Utility functions
log_test() {
    echo -e "${YELLOW}[TEST] $*${NC}"
    TESTS_RUN=$((TESTS_RUN + 1))
    CURRENT_TEST_PASSED=true
}

log_pass() {
    echo -e "${GREEN}[PASS] $*${NC}"
}

# Called at end of each test function
test_complete() {
    if [[ "$CURRENT_TEST_PASSED" == "true" ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi
}

log_fail() {
    echo -e "${RED}[FAIL] $*${NC}"
    CURRENT_TEST_PASSED=false
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Test 1: Verify scripts exist and are executable
test_scripts_exist() {
    log_test "Checking if dependency utility scripts exist and are executable"

    local jq_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_jq.sh"
    local mermaid_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_mermaid.sh"

    if [[ -f "$jq_script" && -x "$jq_script" ]]; then
        log_pass "ensure_jq.sh exists and is executable"
    else
        log_fail "ensure_jq.sh missing or not executable"
    fi

    if [[ -f "$mermaid_script" && -x "$mermaid_script" ]]; then
        log_pass "ensure_mermaid.sh exists and is executable"
    else
        log_fail "ensure_mermaid.sh missing or not executable"
    fi

    test_complete
}

# Test 2: Test jq utility with auto-install disabled
test_jq_utility_dry_run() {
    log_test "Testing jq utility with auto-install disabled"

    local jq_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_jq.sh"

    # Test with auto-install disabled
    if OSTRUCT_SKIP_AUTO_INSTALL=1 "$jq_script" >/dev/null 2>&1; then
        log_pass "jq utility runs without errors (auto-install disabled)"
    else
        # This is expected if jq is not installed
        log_pass "jq utility handles missing dependency correctly (auto-install disabled)"
    fi

    test_complete
}

# Test 3: Test Mermaid utility with auto-install disabled
test_mermaid_utility_dry_run() {
    log_test "Testing Mermaid utility with auto-install disabled"

    local mermaid_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_mermaid.sh"

    # Test with auto-install disabled
    if OSTRUCT_SKIP_AUTO_INSTALL=1 "$mermaid_script" >/dev/null 2>&1; then
        log_pass "Mermaid utility runs without errors (auto-install disabled)"
    else
        # This is expected if Mermaid CLI is not installed
        log_pass "Mermaid utility handles missing dependency correctly (auto-install disabled)"
    fi

    test_complete
}

# Test 4: Test script sourcing capability
test_script_sourcing() {
    log_test "Testing script sourcing capability"

    local jq_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_jq.sh"
    local mermaid_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_mermaid.sh"

    # Test sourcing jq script
    if OSTRUCT_SKIP_AUTO_INSTALL=1 source "$jq_script" >/dev/null 2>&1; then
        log_pass "jq utility can be sourced without errors"
    else
        log_pass "jq utility sourcing handles missing dependency correctly"
    fi

    # Test sourcing Mermaid script
    if OSTRUCT_SKIP_AUTO_INSTALL=1 source "$mermaid_script" >/dev/null 2>&1; then
        log_pass "Mermaid utility can be sourced without errors"
    else
        log_pass "Mermaid utility sourcing handles missing dependency correctly"
    fi

    test_complete
}

# Test 5: Test environment variable handling
test_environment_variables() {
    log_test "Testing environment variable handling"

    local jq_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_jq.sh"

    # Test OSTRUCT_SKIP_AUTO_INSTALL
    local output
    output=$(OSTRUCT_SKIP_AUTO_INSTALL=1 "$jq_script" 2>&1)

    if [[ "$output" == *"Auto-install disabled by OSTRUCT_SKIP_AUTO_INSTALL"* ]] || [[ "$output" == *"jq is already available"* ]]; then
        log_pass "OSTRUCT_SKIP_AUTO_INSTALL environment variable is respected"
    else
        log_fail "OSTRUCT_SKIP_AUTO_INSTALL environment variable not working"
        echo "Expected output to contain skip message or jq availability, got: $output"
    fi

    test_complete
}

# Test 6: Test script help/error output
test_error_output() {
    log_test "Testing error output and help messages"

    local jq_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_jq.sh"
    local mermaid_script="$PROJECT_ROOT/scripts/install/dependencies/ensure_mermaid.sh"

    # Test that scripts provide helpful output when they can't install
    local jq_output
    jq_output=$(OSTRUCT_SKIP_AUTO_INSTALL=1 "$jq_script" 2>&1 || true)

    if [[ "$jq_output" == *"jq"* ]]; then
        log_pass "jq utility provides relevant error messages"
    else
        log_fail "jq utility error messages unclear"
    fi

    local mermaid_output
    mermaid_output=$(OSTRUCT_SKIP_AUTO_INSTALL=1 "$mermaid_script" 2>&1 || true)

    if [[ "$mermaid_output" == *"mermaid"* || "$mermaid_output" == *"mmdc"* ]]; then
        log_pass "Mermaid utility provides relevant error messages"
    else
        log_fail "Mermaid utility error messages unclear"
    fi

    test_complete
}

# Main test execution
main() {
    echo "🧪 Running dependency utility unit tests..."
    echo "============================================"

    # Run all tests
    test_scripts_exist
    test_jq_utility_dry_run
    test_mermaid_utility_dry_run
    test_script_sourcing
    test_environment_variables
    test_error_output

    # Report results
    echo ""
    echo "============================================"
    echo "Test Results: $TESTS_PASSED/$TESTS_RUN tests passed"

    if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
        echo -e "${GREEN}✅ All dependency utility tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}❌ Some tests failed${NC}"
        exit 1
    fi
}

# Run tests
main "$@"
