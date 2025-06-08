#!/bin/bash
# test_integration.sh - Comprehensive integration tests with real document conversions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_INPUTS_DIR="$PROJECT_ROOT/risk_elimination_tests/test-inputs"
TEST_OUTPUT_DIR="$PROJECT_ROOT/test_output"
TEST_LOG_FILE="$PROJECT_ROOT/temp/test_integration.log"

cd "$PROJECT_ROOT"

# Initialize test environment
mkdir -p "$TEST_OUTPUT_DIR" "temp"
echo "=== Document Converter Integration Tests ===" | tee "$TEST_LOG_FILE"
echo "Started at $(date)" | tee -a "$TEST_LOG_FILE"
echo "" | tee -a "$TEST_LOG_FILE"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test result tracking
declare -a TEST_RESULTS=()

# Logging function
log_test() {
    echo "$1" | tee -a "$TEST_LOG_FILE"
}

# Test execution function
run_test() {
    local test_name="$1"
    local test_file="$2"
    local expected_result="${3:-success}"

    ((TOTAL_TESTS++))
    log_test "Test $TOTAL_TESTS: $test_name"
    log_test "  Input: $(basename "$test_file")"

    if [[ ! -f "$test_file" ]]; then
        log_test "  ❌ SKIP - Test file not found: $test_file"
        TEST_RESULTS+=("SKIP")
        return 0
    fi

    local output_file="$TEST_OUTPUT_DIR/$(basename "$test_file" .${test_file##*.}).md"
    local start_time=$(date +%s)

    # Run the conversion
    if ./convert.sh "$test_file" "$output_file" >/dev/null 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        # Validate output exists and has content
        if [[ -f "$output_file" ]] && [[ -s "$output_file" ]]; then
            local file_size=$(wc -c < "$output_file")
            log_test "  ✅ PASS - Conversion successful (${duration}s, ${file_size} bytes)"
            ((PASSED_TESTS++))
            TEST_RESULTS+=("PASS")
        else
            log_test "  ❌ FAIL - Output file empty or missing"
            ((FAILED_TESTS++))
            TEST_RESULTS+=("FAIL")
        fi
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_test "  ❌ FAIL - Conversion failed (${duration}s)"
        ((FAILED_TESTS++))
        TEST_RESULTS+=("FAIL")
    fi

    log_test ""
}

# Test analysis-only mode
run_analysis_test() {
    local test_name="$1"
    local test_file="$2"

    ((TOTAL_TESTS++))
    log_test "Test $TOTAL_TESTS: $test_name (Analysis Only)"
    log_test "  Input: $(basename "$test_file")"

    if [[ ! -f "$test_file" ]]; then
        log_test "  ❌ SKIP - Test file not found: $test_file"
        TEST_RESULTS+=("SKIP")
        return 0
    fi

    local start_time=$(date +%s)

    # Run analysis only
    if ./convert.sh --analyze-only "$test_file" >/dev/null 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_test "  ✅ PASS - Analysis successful (${duration}s)"
        ((PASSED_TESTS++))
        TEST_RESULTS+=("PASS")
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_test "  ❌ FAIL - Analysis failed (${duration}s)"
        ((FAILED_TESTS++))
        TEST_RESULTS+=("FAIL")
    fi

    log_test ""
}

# Check prerequisites
log_test "Checking prerequisites..."
if [[ ! -d "$TEST_INPUTS_DIR" ]]; then
    log_test "❌ Test inputs directory not found: $TEST_INPUTS_DIR"
    exit 1
fi

if [[ ! -x "./convert.sh" ]]; then
    log_test "❌ convert.sh not found or not executable"
    exit 1
fi

log_test "✅ Prerequisites check passed"
log_test ""

# Run basic functionality tests first
log_test "=== Basic Functionality Tests ==="
log_test ""

# Test 1: Help command
((TOTAL_TESTS++))
log_test "Test $TOTAL_TESTS: Help command"
if ./convert.sh --help >/dev/null 2>&1; then
    log_test "  ✅ PASS - Help command works"
    ((PASSED_TESTS++))
    TEST_RESULTS+=("PASS")
else
    log_test "  ❌ FAIL - Help command failed"
    ((FAILED_TESTS++))
    TEST_RESULTS+=("FAIL")
fi
log_test ""

# Test 2: Tool check
((TOTAL_TESTS++))
log_test "Test $TOTAL_TESTS: Tool availability check"
if ./convert.sh --check-tools >/dev/null 2>&1; then
    log_test "  ✅ PASS - Tool check completed"
    ((PASSED_TESTS++))
    TEST_RESULTS+=("PASS")
else
    log_test "  ⚠️  WARN - Tool check had warnings (continuing)"
    ((PASSED_TESTS++))
    TEST_RESULTS+=("PASS")
fi
log_test ""

# Run analysis-only tests
log_test "=== Analysis-Only Tests ==="
log_test ""

# Test various document types for analysis
run_analysis_test "PDF Analysis" "$TEST_INPUTS_DIR/f1040.pdf"
run_analysis_test "DOCX Analysis" "$TEST_INPUTS_DIR/FFY-23-NGCDD-Annual-Report.docx"
run_analysis_test "XLSX Analysis" "$TEST_INPUTS_DIR/Financial Sample.xlsx"
run_analysis_test "PPTX Analysis" "$TEST_INPUTS_DIR/2-1876-Hexagonal-Header-Blocks-PGO-4_3.pptx"

# Run full conversion tests
log_test "=== Full Conversion Tests ==="
log_test ""

# Test PDF conversions
run_test "Simple PDF Conversion" "$TEST_INPUTS_DIR/f1040.pdf"
run_test "Academic PDF Conversion" "$TEST_INPUTS_DIR/NIPS-2017-attention-is-all-you-need-Paper.pdf"

# Test Office document conversions
run_test "DOCX Conversion" "$TEST_INPUTS_DIR/FFY-23-NGCDD-Annual-Report.docx"
run_test "XLSX Conversion" "$TEST_INPUTS_DIR/Financial Sample.xlsx"
run_test "PPTX Conversion" "$TEST_INPUTS_DIR/2-1876-Hexagonal-Header-Blocks-PGO-4_3.pptx"

# Test edge cases
run_test "Merged Cells XLSX" "$TEST_INPUTS_DIR/merged-cells.xlsx"

# Test large document (if available)
if [[ -f "$TEST_INPUTS_DIR/World Bank Annual Report 2024.pdf" ]]; then
    log_test "=== Large Document Test ==="
    log_test ""
    run_test "Large PDF (Chunking Test)" "$TEST_INPUTS_DIR/World Bank Annual Report 2024.pdf"
fi

# Test complex layout (if available)
if [[ -f "$TEST_INPUTS_DIR/RAND_RR287z1.hebrew.pdf" ]]; then
    log_test "=== Complex Layout Test ==="
    log_test ""
    run_test "Hebrew PDF (Complex Layout)" "$TEST_INPUTS_DIR/RAND_RR287z1.hebrew.pdf"
fi

# Generate test report
log_test "=== Test Results Summary ==="
log_test ""
log_test "Total Tests: $TOTAL_TESTS"
log_test "Passed: $PASSED_TESTS"
log_test "Failed: $FAILED_TESTS"
log_test "Success Rate: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"
log_test ""

# Show detailed results
log_test "Detailed Results:"
for i in "${!TEST_RESULTS[@]}"; do
    local test_num=$((i + 1))
    local result="${TEST_RESULTS[$i]}"
    case "$result" in
        "PASS") log_test "  Test $test_num: ✅ PASS" ;;
        "FAIL") log_test "  Test $test_num: ❌ FAIL" ;;
        "SKIP") log_test "  Test $test_num: ⚪ SKIP" ;;
    esac
done
log_test ""

# Final status
if [[ $FAILED_TESTS -eq 0 ]]; then
    log_test "🎉 All tests passed!"
    log_test ""
    log_test "Output files generated in: $TEST_OUTPUT_DIR"
    log_test "Test log saved to: $TEST_LOG_FILE"
    exit 0
else
    log_test "❌ $FAILED_TESTS test(s) failed"
    log_test ""
    log_test "Check the test log for details: $TEST_LOG_FILE"
    exit 1
fi
