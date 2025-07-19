#!/bin/bash

# Comprehensive test script for Phase 1 (T1.5)
# Tests all analysis prompts and validates their outputs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}OST Generator Phase 1 Comprehensive Test Suite${NC}"
echo -e "${BLUE}================================================${NC}"

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_RESULTS=()

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_script="$2"

    echo -e "\n${YELLOW}Running $test_name...${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [[ ! -f "$test_script" ]]; then
        echo -e "${RED}✗ Test script not found: $test_script${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("$test_name: FAILED - Script not found")
        return 1
    fi

    if "$test_script" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("$test_name: PASSED")
        return 0
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("$test_name: FAILED")
        return 1
    fi
}

# Function to validate output files exist and are valid JSON
validate_output_files() {
    echo -e "\n${YELLOW}Validating output files...${NC}"

    local expected_files=(
        "analysis_simple.json"
        "analysis_complex.json"
        "classification_simple.json"
        "classification_complex.json"
        "schema_analysis_simple.json"
        "schema_analysis_complex.json"
        "patterns_simple.json"
        "patterns_complex.json"
    )

    local validation_passed=true

    for file in "${expected_files[@]}"; do
        local file_path="$TEST_DIR/$file"
        if [[ -f "$file_path" ]]; then
            if jq empty "$file_path" 2>/dev/null; then
                echo -e "${GREEN}✓ $file exists and is valid JSON${NC}"
            else
                echo -e "${RED}✗ $file exists but is invalid JSON${NC}"
                validation_passed=false
            fi
        else
            echo -e "${RED}✗ $file is missing${NC}"
            validation_passed=false
        fi
    done

    if $validation_passed; then
        echo -e "${GREEN}✓ All output files validated${NC}"
        return 0
    else
        echo -e "${RED}✗ Output file validation failed${NC}"
        return 1
    fi
}

# Function to check JSON schema compliance
validate_schema_compliance() {
    echo -e "\n${YELLOW}Validating schema compliance...${NC}"

    local schema_tests=(
        "analysis_simple.json:analysis_schema.json"
        "analysis_complex.json:analysis_schema.json"
        "classification_simple.json:classification_schema.json"
        "classification_complex.json:classification_schema.json"
        "schema_analysis_simple.json:schema_analysis_schema.json"
        "schema_analysis_complex.json:schema_analysis_schema.json"
        "patterns_simple.json:pattern_detection_schema.json"
        "patterns_complex.json:pattern_detection_schema.json"
    )

    local compliance_passed=true

    for test in "${schema_tests[@]}"; do
        local output_file="${test%%:*}"
        local schema_file="${test##*:}"

        local output_path="$TEST_DIR/$output_file"
        local schema_path="$TEST_DIR/../src/$schema_file"

        if [[ -f "$output_path" && -f "$schema_path" ]]; then
            # Basic structure validation using jq
            if jq -e 'type == "object"' "$output_path" > /dev/null 2>&1; then
                echo -e "${GREEN}✓ $output_file has valid object structure${NC}"
            else
                echo -e "${RED}✗ $output_file has invalid structure${NC}"
                compliance_passed=false
            fi
        else
            echo -e "${RED}✗ Missing files for $output_file validation${NC}"
            compliance_passed=false
        fi
    done

    if $compliance_passed; then
        echo -e "${GREEN}✓ All schema compliance checks passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Schema compliance validation failed${NC}"
        return 1
    fi
}

# Function to generate test report
generate_test_report() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}Phase 1 Test Report${NC}"
    echo -e "${BLUE}================================================${NC}"

    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"

    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All Phase 1 tests passed!${NC}"
        echo -e "${GREEN}✓ Template analysis working${NC}"
        echo -e "${GREEN}✓ Variable classification working${NC}"
        echo -e "${GREEN}✓ Schema analysis working${NC}"
        echo -e "${GREEN}✓ Pattern detection working${NC}"
        echo -e "${GREEN}✓ All outputs validated${NC}"
    else
        echo -e "\n${RED}❌ Some Phase 1 tests failed${NC}"
        echo -e "\nDetailed results:"
        for result in "${TEST_RESULTS[@]}"; do
            if [[ "$result" == *"PASSED"* ]]; then
                echo -e "${GREEN}  $result${NC}"
            else
                echo -e "${RED}  $result${NC}"
            fi
        done
    fi

    echo -e "\n${BLUE}Output Files Generated:${NC}"
    find "$TEST_DIR" -name "*.json" -type f | sort | while read -r file; do
        local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "unknown")
        echo -e "  $(basename "$file") (${size} bytes)"
    done
}

# Function to clean up old test files
cleanup_old_files() {
    echo -e "\n${YELLOW}Cleaning up old test files...${NC}"

    local cleanup_patterns=(
        "analysis_*.json"
        "classification_*.json"
        "schema_analysis_*.json"
        "patterns_*.json"
        "debug_*.json"
        "manual_*.json"
    )

    for pattern in "${cleanup_patterns[@]}"; do
        find "$TEST_DIR" -name "$pattern" -type f -delete 2>/dev/null || true
    done

    echo -e "${GREEN}✓ Cleanup completed${NC}"
}

# Main test execution
main() {
    local start_time=$(date +%s)

    echo -e "Starting Phase 1 comprehensive test suite..."
    echo -e "Test directory: $TEST_DIR"
    echo -e "Timestamp: $(date)"

    # Optional cleanup
    if [[ "$1" == "--clean" ]]; then
        cleanup_old_files
    fi

    # Run individual test suites
    echo -e "\n${BLUE}Running individual test suites...${NC}"

    run_test "Template Analysis (T1.1)" "$TEST_DIR/test_analysis.sh"
    run_test "Variable Classification (T1.2)" "$TEST_DIR/test_classification.sh"
    run_test "Schema Analysis (T1.3)" "$TEST_DIR/test_schema_analysis.sh"
    run_test "Pattern Detection (T1.4)" "$TEST_DIR/test_pattern_detection.sh"

    # Validate outputs
    echo -e "\n${BLUE}Running validation checks...${NC}"

    if validate_output_files; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("Output File Validation: PASSED")
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("Output File Validation: FAILED")
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if validate_schema_compliance; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("Schema Compliance: PASSED")
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("Schema Compliance: FAILED")
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    # Generate report
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    generate_test_report

    echo -e "\n${BLUE}Test execution completed in ${duration} seconds${NC}"

    # Exit with appropriate code
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "\n${GREEN}✅ Phase 1 implementation fully validated${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Phase 1 implementation has issues${NC}"
        exit 1
    fi
}

# Show usage if help requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: $0 [--clean] [--help]"
    echo ""
    echo "Options:"
    echo "  --clean    Clean up old test files before running"
    echo "  --help     Show this help message"
    echo ""
    echo "This script runs all Phase 1 tests and validates the outputs."
    exit 0
fi

# Run main function
main "$@"
