#!/bin/bash
# test_all.sh - Master test runner for all test suites

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_LOG_FILE="$PROJECT_ROOT/temp/test_all.log"

cd "$PROJECT_ROOT"

# Initialize test environment
mkdir -p "temp"
echo "=== Document Converter Complete Test Suite ===" | tee "$TEST_LOG_FILE"
echo "Started at $(date)" | tee -a "$TEST_LOG_FILE"
echo "" | tee -a "$TEST_LOG_FILE"

# Test suite counters
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

# Logging function
log_test() {
    echo "$1" | tee -a "$TEST_LOG_FILE"
}

# Run test suite function
run_test_suite() {
    local suite_name="$1"
    local script_path="$2"

    ((TOTAL_SUITES++))
    log_test "=== Running $suite_name ==="
    log_test ""

    local start_time=$(date +%s)

    if [[ -x "$script_path" ]]; then
        if "$script_path"; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log_test "✅ $suite_name PASSED (${duration}s)"
            ((PASSED_SUITES++))
        else
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log_test "❌ $suite_name FAILED (${duration}s)"
            ((FAILED_SUITES++))
        fi
    else
        log_test "❌ $suite_name SKIPPED - Script not found or not executable: $script_path"
        ((FAILED_SUITES++))
    fi

    log_test ""
}

# Parse command line arguments
RUN_UNIT=true
RUN_BASIC=true
RUN_INTEGRATION=true
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_UNIT=true
            RUN_BASIC=false
            RUN_INTEGRATION=false
            shift
            ;;
        --basic-only)
            RUN_UNIT=false
            RUN_BASIC=true
            RUN_INTEGRATION=false
            shift
            ;;
        --integration-only)
            RUN_UNIT=false
            RUN_BASIC=false
            RUN_INTEGRATION=true
            shift
            ;;
        --no-unit)
            RUN_UNIT=false
            shift
            ;;
        --no-basic)
            RUN_BASIC=false
            shift
            ;;
        --no-integration)
            RUN_INTEGRATION=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "  --unit-only        Run only unit tests"
            echo "  --basic-only       Run only basic tests"
            echo "  --integration-only Run only integration tests"
            echo "  --no-unit          Skip unit tests"
            echo "  --no-basic         Skip basic tests"
            echo "  --no-integration   Skip integration tests"
            echo "  --verbose          Enable verbose output"
            echo "  -h, --help         Show this help"
            echo ""
            echo "EXAMPLES:"
            echo "  $0                 # Run all test suites"
            echo "  $0 --unit-only    # Run only unit tests"
            echo "  $0 --no-integration # Run unit and basic tests only"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Show test plan
log_test "Test Plan:"
if [[ "$RUN_UNIT" == "true" ]]; then
    log_test "  ✓ Unit Tests"
fi
if [[ "$RUN_BASIC" == "true" ]]; then
    log_test "  ✓ Basic Tests"
fi
if [[ "$RUN_INTEGRATION" == "true" ]]; then
    log_test "  ✓ Integration Tests"
fi
log_test ""

# Run test suites in order
if [[ "$RUN_UNIT" == "true" ]]; then
    run_test_suite "Unit Tests" "scripts/test_unit.sh"
fi

if [[ "$RUN_BASIC" == "true" ]]; then
    run_test_suite "Basic Tests" "scripts/test_basic.sh"
fi

if [[ "$RUN_INTEGRATION" == "true" ]]; then
    run_test_suite "Integration Tests" "scripts/test_integration.sh"
fi

# Generate final report
log_test "=== Complete Test Suite Results ==="
log_test ""
log_test "Test Suites Run: $TOTAL_SUITES"
log_test "Passed: $PASSED_SUITES"
log_test "Failed: $FAILED_SUITES"

if [[ $TOTAL_SUITES -gt 0 ]]; then
    log_test "Success Rate: $(( (PASSED_SUITES * 100) / TOTAL_SUITES ))%"
else
    log_test "Success Rate: N/A (no tests run)"
fi

log_test ""

# Show individual test logs
log_test "Individual Test Logs:"
if [[ "$RUN_UNIT" == "true" ]] && [[ -f "temp/test_unit.log" ]]; then
    log_test "  - Unit Tests: temp/test_unit.log"
fi
if [[ "$RUN_BASIC" == "true" ]]; then
    log_test "  - Basic Tests: Check console output above"
fi
if [[ "$RUN_INTEGRATION" == "true" ]] && [[ -f "temp/test_integration.log" ]]; then
    log_test "  - Integration Tests: temp/test_integration.log"
fi

log_test "  - Complete Suite: temp/test_all.log"
log_test ""

# Final status
if [[ $FAILED_SUITES -eq 0 ]] && [[ $TOTAL_SUITES -gt 0 ]]; then
    log_test "🎉 All test suites passed!"
    log_test ""
    log_test "The document converter is ready for use!"
    exit 0
elif [[ $TOTAL_SUITES -eq 0 ]]; then
    log_test "⚠️  No test suites were run"
    log_test ""
    log_test "Use --help to see available options"
    exit 1
else
    log_test "❌ $FAILED_SUITES test suite(s) failed"
    log_test ""
    log_test "Check individual test logs for details"
    exit 1
fi
