#!/bin/bash

# Test script for pattern detection (T1.4)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../src"
TEST_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing Pattern Detection (T1.4)${NC}"

# Function to run pattern detection test
run_pattern_detection_test() {
    local test_name="$1"
    local expected_patterns="$2"

    echo -e "\n${YELLOW}Running pattern detection test: $test_name${NC}"

    # Check if prerequisite files exist
    local template_analysis_file="$TEST_DIR/analysis_${test_name}.json"
    local classification_file="$TEST_DIR/classification_${test_name}.json"
    local schema_analysis_file="$TEST_DIR/schema_analysis_${test_name}.json"

    if [[ ! -f "$template_analysis_file" ]]; then
        echo -e "${RED}ERROR: Template analysis file not found: $template_analysis_file${NC}"
        echo "Please run previous tests first to generate analysis results"
        return 1
    fi

    if [[ ! -f "$classification_file" ]]; then
        echo -e "${RED}ERROR: Classification file not found: $classification_file${NC}"
        echo "Please run previous tests first to generate classification results"
        return 1
    fi

    if [[ ! -f "$schema_analysis_file" ]]; then
        echo -e "${RED}ERROR: Schema analysis file not found: $schema_analysis_file${NC}"
        echo "Please run previous tests first to generate schema analysis results"
        return 1
    fi

    # Read input JSON files
    local template_analysis
    local variable_classification
    local schema_analysis

    template_analysis=$(cat "$template_analysis_file")
    variable_classification=$(cat "$classification_file")
    schema_analysis=$(cat "$schema_analysis_file")

    # Test dry-run first
    echo "Testing dry-run mode..."
    if ostruct run "$SRC_DIR/detect_patterns.j2" "$SRC_DIR/pattern_detection_schema.json" \
        --var template_analysis="$template_analysis" \
        --var variable_classification="$variable_classification" \
        --var schema_analysis="$schema_analysis" \
        --dry-run > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dry-run passed${NC}"
    else
        echo -e "${RED}✗ Dry-run failed${NC}"
        return 1
    fi

    # Test live API call
    echo "Testing live API call..."
    local output_file="$TEST_DIR/patterns_${test_name}.json"
    if ostruct run "$SRC_DIR/detect_patterns.j2" "$SRC_DIR/pattern_detection_schema.json" \
        --var template_analysis="$template_analysis" \
        --var variable_classification="$variable_classification" \
        --var schema_analysis="$schema_analysis" \
        --output-file "$output_file"; then
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
    local required_fields=("file_patterns" "tool_hints" "security_patterns" "integration_patterns" "pattern_summary")
    for field in "${required_fields[@]}"; do
        if jq -e "has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Has required field: $field${NC}"
        else
            echo -e "${RED}✗ Missing required field: $field${NC}"
            return 1
        fi
    done

    # Check file patterns structure
    local file_pattern_fields=("file_attachments" "directory_operations")
    for field in "${file_pattern_fields[@]}"; do
        if jq -e ".file_patterns | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ File patterns has field: $field${NC}"
        else
            echo -e "${RED}✗ File patterns missing field: $field${NC}"
            return 1
        fi
    done

    # Check tool hints structure
    local tool_fields=("code_interpreter" "file_search" "web_search")
    for field in "${tool_fields[@]}"; do
        if jq -e ".tool_hints | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Tool hints has field: $field${NC}"
        else
            echo -e "${RED}✗ Tool hints missing field: $field${NC}"
            return 1
        fi
    done

    # Check security patterns structure
    local security_fields=("input_validation" "file_safety")
    for field in "${security_fields[@]}"; do
        if jq -e ".security_patterns | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Security patterns has field: $field${NC}"
        else
            echo -e "${RED}✗ Security patterns missing field: $field${NC}"
            return 1
        fi
    done

    # Check pattern summary structure
    local summary_fields=("complexity_score" "primary_patterns" "recommended_features")
    for field in "${summary_fields[@]}"; do
        if jq -e ".pattern_summary | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Pattern summary has field: $field${NC}"
        else
            echo -e "${RED}✗ Pattern summary missing field: $field${NC}"
            return 1
        fi
    done

    # Check if expected patterns were detected
    local primary_patterns_count
    primary_patterns_count=$(jq '.pattern_summary.primary_patterns | length' "$output_file")
    if [[ "$primary_patterns_count" -ge "$expected_patterns" ]]; then
        echo -e "${GREEN}✓ Found $primary_patterns_count primary patterns (expected >= $expected_patterns)${NC}"
    else
        echo -e "${RED}✗ Found $primary_patterns_count primary patterns (expected >= $expected_patterns)${NC}"
        return 1
    fi

    # Show sample analysis
    echo -e "\n${YELLOW}File patterns:${NC}"
    jq -C '.file_patterns' "$output_file"

    echo -e "\n${YELLOW}Tool hints:${NC}"
    jq -C '.tool_hints' "$output_file"

    echo -e "\n${YELLOW}Security patterns:${NC}"
    jq -C '.security_patterns' "$output_file"

    echo -e "\n${YELLOW}Pattern summary:${NC}"
    jq -C '.pattern_summary' "$output_file"

    echo -e "${GREEN}✓ Pattern detection test '$test_name' passed${NC}"
    return 0
}

# Main test execution
main() {
    local failed=0

    echo "Checking prerequisites..."

    # Check if previous analysis results exist
    local missing_files=()

    for test_type in "simple" "complex"; do
        for analysis_type in "analysis" "classification" "schema_analysis"; do
            local file_path="$TEST_DIR/${analysis_type}_${test_type}.json"
            if [[ ! -f "$file_path" ]]; then
                missing_files+=("$file_path")
            fi
        done
    done

    if [[ ${#missing_files[@]} -gt 0 ]]; then
        echo -e "${YELLOW}Missing prerequisite files. Running previous tests...${NC}"

        # Run previous tests to generate required files
        if [[ -f "$TEST_DIR/test_analysis.sh" ]]; then
            echo "Running template analysis test..."
            if ! "$TEST_DIR/test_analysis.sh"; then
                echo -e "${RED}Template analysis test failed${NC}"
                exit 1
            fi
        fi

        if [[ -f "$TEST_DIR/test_classification.sh" ]]; then
            echo "Running classification test..."
            if ! "$TEST_DIR/test_classification.sh"; then
                echo -e "${RED}Classification test failed${NC}"
                exit 1
            fi
        fi

        if [[ -f "$TEST_DIR/test_schema_analysis.sh" ]]; then
            echo "Running schema analysis test..."
            if ! "$TEST_DIR/test_schema_analysis.sh"; then
                echo -e "${RED}Schema analysis test failed${NC}"
                exit 1
            fi
        fi
    fi

    # Run pattern detection tests
    echo -e "\n${YELLOW}Starting pattern detection tests...${NC}"

    # Test 1: Simple template patterns
    if ! run_pattern_detection_test "simple" 2; then
        failed=1
    fi

    # Test 2: Complex template patterns
    if ! run_pattern_detection_test "complex" 4; then
        failed=1
    fi

    # Summary
    echo -e "\n${YELLOW}Pattern Detection Test Summary:${NC}"
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}✓ All pattern detection tests passed${NC}"
        echo -e "${GREEN}✓ T1.4 implementation validated${NC}"
    else
        echo -e "${RED}✗ Some pattern detection tests failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
