#!/bin/bash

# Test script for variable classification (T1.2)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../src"
TEST_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing Variable Classification (T1.2)${NC}"

# Function to run classification test
run_classification_test() {
    local test_name="$1"
    local analysis_file="$2"
    local expected_vars="$3"

    echo -e "\n${YELLOW}Running classification test: $test_name${NC}"

    # Check if analysis file exists
    if [[ ! -f "$analysis_file" ]]; then
        echo -e "${RED}ERROR: Analysis file not found: $analysis_file${NC}"
        echo "Please run test_analysis.sh first to generate analysis results"
        return 1
    fi

    # Read analysis JSON
    local analysis_json
    analysis_json=$(cat "$analysis_file")

    # Test dry-run first
    echo "Testing dry-run mode..."
    if ostruct run "$SRC_DIR/classify_variables.j2" "$SRC_DIR/classification_schema.json" \
        --var analysis_json="$analysis_json" \
        --dry-run > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dry-run passed${NC}"
    else
        echo -e "${RED}✗ Dry-run failed${NC}"
        return 1
    fi

    # Test live API call
    echo "Testing live API call..."
    local output_file="$TEST_DIR/classification_${test_name}.json"
    if ostruct run "$SRC_DIR/classify_variables.j2" "$SRC_DIR/classification_schema.json" \
        --var analysis_json="$analysis_json" \
        --output-file "$output_file" 2>/dev/null; then
        echo -e "${GREEN}✓ Live API call succeeded${NC}"
    else
        echo -e "${RED}✗ Live API call failed${NC}"
        return 1
    fi

    # Validate JSON structure
    if jq empty "$output_file" 2>/dev/null; then
        echo -e "${GREEN}✓ Valid JSON output${NC}"
    else
        echo -e "${RED}✗ Invalid JSON output${NC}"
        return 1
    fi

    # Check required fields
    local required_fields=("classified_variables" "classification_summary")
    for field in "${required_fields[@]}"; do
        if jq -e "has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Has required field: $field${NC}"
        else
            echo -e "${RED}✗ Missing required field: $field${NC}"
            return 1
        fi
    done

    # Check variable count
    local var_count
    var_count=$(jq '.classified_variables | length' "$output_file")
    if [[ "$var_count" -ge "$expected_vars" ]]; then
        echo -e "${GREEN}✓ Found $var_count variables (expected >= $expected_vars)${NC}"
    else
        echo -e "${RED}✗ Found $var_count variables (expected >= $expected_vars)${NC}"
        return 1
    fi

    # Check variable structure
    local sample_var
    sample_var=$(jq '.classified_variables[0]' "$output_file")
    local var_required_fields=("name" "type" "confidence" "usage_context" "cli_suggestion")

    for field in "${var_required_fields[@]}"; do
        if echo "$sample_var" | jq -e "has(\"$field\")" > /dev/null; then
            echo -e "${GREEN}✓ Variable has required field: $field${NC}"
        else
            echo -e "${RED}✗ Variable missing required field: $field${NC}"
            return 1
        fi
    done

    # Check CLI suggestion structure
    local cli_suggestion
    cli_suggestion=$(echo "$sample_var" | jq '.cli_suggestion')
    local cli_required_fields=("flag" "argument_type" "required")

    for field in "${cli_required_fields[@]}"; do
        if echo "$cli_suggestion" | jq -e "has(\"$field\")" > /dev/null; then
            echo -e "${GREEN}✓ CLI suggestion has required field: $field${NC}"
        else
            echo -e "${RED}✗ CLI suggestion missing required field: $field${NC}"
            return 1
        fi
    done

    # Show sample classification
    echo -e "\n${YELLOW}Sample classification:${NC}"
    echo "$sample_var" | jq -C '.'

    echo -e "\n${YELLOW}Classification summary:${NC}"
    jq -C '.classification_summary' "$output_file"

    echo -e "${GREEN}✓ Classification test '$test_name' passed${NC}"
    return 0
}

# Main test execution
main() {
    local failed=0

    echo "Checking prerequisites..."

    # Check if analysis results exist
    if [[ ! -f "$TEST_DIR/analysis_simple.json" ]]; then
        echo -e "${YELLOW}Analysis results not found. Running analysis test first...${NC}"
        if ! "$TEST_DIR/test_analysis.sh"; then
            echo -e "${RED}Analysis test failed. Cannot proceed with classification test.${NC}"
            exit 1
        fi

        # Copy analysis results to expected locations
        if [[ -f "/tmp/simple_analysis.json" ]]; then
            cp "/tmp/simple_analysis.json" "$TEST_DIR/analysis_simple.json"
        fi
        if [[ -f "/tmp/complex_analysis.json" ]]; then
            cp "/tmp/complex_analysis.json" "$TEST_DIR/analysis_complex.json"
        fi
    fi

    # Run classification tests
    echo -e "\n${YELLOW}Starting classification tests...${NC}"

    # Test 1: Simple template
    if ! run_classification_test "simple" "$TEST_DIR/analysis_simple.json" 2; then
        failed=1
    fi

    # Test 2: Complex template (if analysis exists)
    if [[ -f "$TEST_DIR/analysis_complex.json" ]]; then
        if ! run_classification_test "complex" "$TEST_DIR/analysis_complex.json" 5; then
            failed=1
        fi
    fi

    # Summary
    echo -e "\n${YELLOW}Classification Test Summary:${NC}"
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}✓ All classification tests passed${NC}"
        echo -e "${GREEN}✓ T1.2 implementation validated${NC}"
    else
        echo -e "${RED}✗ Some classification tests failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
