#!/bin/bash
# Comprehensive baseline test runner for convert.sh
# This captures the current behavior before any refactoring begins

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASELINE_DIR="$SCRIPT_DIR/baseline"

# Ensure baseline directory exists
if [[ ! -d "$BASELINE_DIR" ]]; then
    echo -e "${RED}❌ Baseline test directory not found: $BASELINE_DIR${NC}"
    exit 1
fi

# Test tracking
TOTAL_SUITES=0
PASSED_SUITES=0
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_SUITES=()

# Helper functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_section() {
    echo -e "${YELLOW}--- $1 ---${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Run a single baseline test suite
run_baseline_suite() {
    local suite_name="$1"
    local suite_script="$2"
    
    TOTAL_SUITES=$((TOTAL_SUITES + 1))
    
    print_section "Running $suite_name"
    
    if [[ ! -f "$suite_script" ]]; then
        print_error "Test suite not found: $suite_script"
        FAILED_SUITES+=("$suite_name (not found)")
        return 1
    fi
    
    if [[ ! -x "$suite_script" ]]; then
        print_info "Making $suite_name executable"
        chmod +x "$suite_script"
    fi
    
    # Run the test suite and capture output
    local output
    local exit_code
    
    output=$("$suite_script" 2>&1)
    exit_code=$?
    
    # Parse test results from output
    local suite_tests_run=0
    local suite_tests_passed=0
    
    if [[ "$output" =~ Tests\ run:\ ([0-9]+) ]]; then
        suite_tests_run="${BASH_REMATCH[1]}"
    fi
    
    if [[ "$output" =~ Tests\ passed:\ ([0-9]+) ]]; then
        suite_tests_passed="${BASH_REMATCH[1]}"
    fi
    
    # Update totals
    TOTAL_TESTS=$((TOTAL_TESTS + suite_tests_run))
    PASSED_TESTS=$((PASSED_TESTS + suite_tests_passed))
    
    if [[ $exit_code -eq 0 ]]; then
        PASSED_SUITES=$((PASSED_SUITES + 1))
        print_success "$suite_name completed successfully ($suite_tests_passed/$suite_tests_run tests passed)"
    else
        FAILED_SUITES+=("$suite_name")
        print_error "$suite_name failed ($suite_tests_passed/$suite_tests_run tests passed)"
        
        # Show failed test output for debugging
        echo -e "${YELLOW}Output from failed suite:${NC}"
        echo "$output" | tail -20
        echo
    fi
    
    return $exit_code
}

# Validate convert.sh exists
validate_convert_script() {
    local convert_script="$PROJECT_ROOT/convert.sh"
    
    if [[ ! -f "$convert_script" ]]; then
        print_error "convert.sh not found at: $convert_script"
        return 1
    fi
    
    if [[ ! -r "$convert_script" ]]; then
        print_error "convert.sh is not readable: $convert_script"
        return 1
    fi
    
    print_success "convert.sh found and readable"
    return 0
}

# Check for required tools
check_baseline_requirements() {
    local missing_tools=()
    
    # Check for basic tools needed by baseline tests
    local required_tools=("bash" "grep" "sed" "awk" "date" "bc")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools for baseline tests: ${missing_tools[*]}"
        return 1
    fi
    
    print_success "All required tools available"
    return 0
}

# Main execution
main() {
    print_header "Baseline Regression Tests for convert.sh"
    echo "This captures current behavior before refactoring begins"
    echo "Project: $PROJECT_ROOT"
    echo "Baseline tests: $BASELINE_DIR"
    echo
    
    # Validate environment
    print_section "Environment Validation"
    
    if ! validate_convert_script; then
        exit 1
    fi
    
    if ! check_baseline_requirements; then
        exit 1
    fi
    
    echo
    
    # Discover and run baseline test suites
    print_section "Discovering Baseline Test Suites"
    
    local test_suites=()
    
    # Find all baseline test scripts
    while IFS= read -r -d '' test_file; do
        if [[ -f "$test_file" ]] && [[ "$test_file" =~ test_current_.*\.sh$ ]]; then
            local suite_name=$(basename "$test_file" .sh)
            suite_name=${suite_name#test_current_}
            test_suites+=("$suite_name:$test_file")
        fi
    done < <(find "$BASELINE_DIR" -name "test_current_*.sh" -print0)
    
    if [[ ${#test_suites[@]} -eq 0 ]]; then
        print_error "No baseline test suites found in $BASELINE_DIR"
        exit 1
    fi
    
    print_info "Found ${#test_suites[@]} baseline test suites"
    for suite_info in "${test_suites[@]}"; do
        local suite_name="${suite_info%%:*}"
        echo "  - $suite_name"
    done
    echo
    
    # Run all baseline test suites
    print_section "Executing Baseline Test Suites"
    
    local start_time=$(date +%s)
    
    for suite_info in "${test_suites[@]}"; do
        local suite_name="${suite_info%%:*}"
        local suite_script="${suite_info##*:}"
        
        run_baseline_suite "$suite_name" "$suite_script"
        echo
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Final summary
    print_header "Baseline Test Summary"
    
    echo "Execution time: ${duration}s"
    echo "Test suites: $PASSED_SUITES/$TOTAL_SUITES passed"
    echo "Individual tests: $PASSED_TESTS/$TOTAL_TESTS passed"
    echo
    
    if [[ ${#FAILED_SUITES[@]} -gt 0 ]]; then
        print_error "Failed test suites:"
        for failed_suite in "${FAILED_SUITES[@]}"; do
            echo "  - $failed_suite"
        done
        echo
    fi
    
    if [[ $PASSED_SUITES -eq $TOTAL_SUITES ]]; then
        print_success "All baseline tests passed!"
        print_success "Current behavior successfully captured"
        echo
        print_info "You can now proceed with refactoring knowing that:"
        echo "  1. Current behavior is documented"
        echo "  2. Regression tests are in place"
        echo "  3. Any changes can be validated against this baseline"
        exit 0
    else
        print_error "Some baseline tests failed!"
        print_error "Current behavior may have issues that need investigation"
        echo
        print_info "Before proceeding with refactoring:"
        echo "  1. Investigate and fix failing baseline tests"
        echo "  2. Ensure current behavior is stable"
        echo "  3. Re-run baseline tests until all pass"
        exit 1
    fi
}

# Handle script interruption
cleanup() {
    echo
    print_info "Baseline test execution interrupted"
    exit 130
}

trap cleanup INT TERM

# Execute main function
main "$@" 