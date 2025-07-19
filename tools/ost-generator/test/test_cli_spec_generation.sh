#!/bin/bash

# Test script for CLI specification generation (T2.1)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../src"
TEST_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing CLI Specification Generation (T2.1)${NC}"

# Function to run CLI spec generation test
run_cli_spec_test() {
    local test_name="$1"
    local expected_args="$2"

    echo -e "\n${YELLOW}Running CLI spec generation test: $test_name${NC}"

    # Check if prerequisite files exist
    local template_analysis_file="$TEST_DIR/analysis_${test_name}.json"
    local classification_file="$TEST_DIR/classification_${test_name}.json"
    local schema_analysis_file="$TEST_DIR/schema_analysis_${test_name}.json"
    local pattern_detection_file="$TEST_DIR/patterns_${test_name}.json"

    local missing_files=()

    if [[ ! -f "$template_analysis_file" ]]; then
        missing_files+=("$template_analysis_file")
    fi

    if [[ ! -f "$classification_file" ]]; then
        missing_files+=("$classification_file")
    fi

    if [[ ! -f "$schema_analysis_file" ]]; then
        missing_files+=("$schema_analysis_file")
    fi

    if [[ ! -f "$pattern_detection_file" ]]; then
        missing_files+=("$pattern_detection_file")
    fi

    if [[ ${#missing_files[@]} -gt 0 ]]; then
        echo -e "${RED}ERROR: Missing prerequisite files:${NC}"
        for file in "${missing_files[@]}"; do
            echo -e "${RED}  - $file${NC}"
        done
        echo "Please run Phase 1 tests first to generate analysis results"
        return 1
    fi

    # Read input JSON files
    local template_analysis
    local variable_classification
    local schema_analysis
    local pattern_detection

    template_analysis=$(cat "$template_analysis_file")
    variable_classification=$(cat "$classification_file")
    schema_analysis=$(cat "$schema_analysis_file")
    pattern_detection=$(cat "$pattern_detection_file")

    # Test dry-run first
    echo "Testing dry-run mode..."
    if ostruct run "$SRC_DIR/generate_cli_spec.j2" "$SRC_DIR/cli_spec_schema.json" \
        --var template_analysis="$template_analysis" \
        --var variable_classification="$variable_classification" \
        --var schema_analysis="$schema_analysis" \
        --var pattern_detection="$pattern_detection" \
        --dry-run > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dry-run passed${NC}"
    else
        echo -e "${RED}✗ Dry-run failed${NC}"
        return 1
    fi

    # Test live API call
    echo "Testing live API call..."
    local output_file="$TEST_DIR/cli_spec_${test_name}.json"
    if ostruct run "$SRC_DIR/generate_cli_spec.j2" "$SRC_DIR/cli_spec_schema.json" \
        --var template_analysis="$template_analysis" \
        --var variable_classification="$variable_classification" \
        --var schema_analysis="$schema_analysis" \
        --var pattern_detection="$pattern_detection" \
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
    local required_fields=("cli_specification" "usage_examples" "implementation_notes")
    for field in "${required_fields[@]}"; do
        if jq -e "has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Has required field: $field${NC}"
        else
            echo -e "${RED}✗ Missing required field: $field${NC}"
            return 1
        fi
    done

    # Check CLI specification structure
    local cli_spec_fields=("tool_name" "description" "arguments" "file_attachments" "tool_integrations")
    for field in "${cli_spec_fields[@]}"; do
        if jq -e ".cli_specification | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ CLI specification has field: $field${NC}"
        else
            echo -e "${RED}✗ CLI specification missing field: $field${NC}"
            return 1
        fi
    done

    # Check arguments count
    local args_count
    args_count=$(jq '.cli_specification.arguments | length' "$output_file")
    if [[ "$args_count" -ge "$expected_args" ]]; then
        echo -e "${GREEN}✓ Found $args_count arguments (expected >= $expected_args)${NC}"
    else
        echo -e "${RED}✗ Found $args_count arguments (expected >= $expected_args)${NC}"
        return 1
    fi

    # Check argument structure
    if [[ "$args_count" -gt 0 ]]; then
        local sample_arg
        sample_arg=$(jq '.cli_specification.arguments[0]' "$output_file")
        local arg_required_fields=("variable_name" "cli_flag" "argument_type" "required" "help_text")

        for field in "${arg_required_fields[@]}"; do
            if echo "$sample_arg" | jq -e "has(\"$field\")" > /dev/null; then
                echo -e "${GREEN}✓ Argument has required field: $field${NC}"
            else
                echo -e "${RED}✗ Argument missing required field: $field${NC}"
                return 1
            fi
        done
    fi

    # Check implementation notes structure
    local impl_fields=("complexity_assessment" "security_considerations" "validation_requirements")
    for field in "${impl_fields[@]}"; do
        if jq -e ".implementation_notes | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Implementation notes has field: $field${NC}"
        else
            echo -e "${RED}✗ Implementation notes missing field: $field${NC}"
            return 1
        fi
    done

    # Check usage examples
    local examples_count
    examples_count=$(jq '.usage_examples | length' "$output_file")
    if [[ "$examples_count" -gt 0 ]]; then
        echo -e "${GREEN}✓ Found $examples_count usage examples${NC}"
    else
        echo -e "${RED}✗ No usage examples found${NC}"
        return 1
    fi

    # Show sample output
    echo -e "\n${YELLOW}Tool name and description:${NC}"
    jq -C '.cli_specification | {tool_name, description}' "$output_file"

    echo -e "\n${YELLOW}Sample argument:${NC}"
    jq -C '.cli_specification.arguments[0]' "$output_file"

    echo -e "\n${YELLOW}Tool integrations:${NC}"
    jq -C '.cli_specification.tool_integrations' "$output_file"

    echo -e "\n${YELLOW}Sample usage example:${NC}"
    jq -C '.usage_examples[0]' "$output_file"

    echo -e "\n${YELLOW}Implementation notes:${NC}"
    jq -C '.implementation_notes' "$output_file"

    echo -e "${GREEN}✓ CLI specification generation test '$test_name' passed${NC}"
    return 0
}

# Main test execution
main() {
    local failed=0

    echo "Checking prerequisites..."

    # Check if Phase 1 analysis results exist
    local missing_phase1=()

    for test_type in "simple" "complex"; do
        for analysis_type in "analysis" "classification" "schema_analysis" "patterns"; do
            local file_path="$TEST_DIR/${analysis_type}_${test_type}.json"
            if [[ ! -f "$file_path" ]]; then
                missing_phase1+=("$file_path")
            fi
        done
    done

    if [[ ${#missing_phase1[@]} -gt 0 ]]; then
        echo -e "${YELLOW}Missing Phase 1 analysis files. Running Phase 1 tests...${NC}"

        if [[ -f "$TEST_DIR/test_phase1.sh" ]]; then
            if ! "$TEST_DIR/test_phase1.sh"; then
                echo -e "${RED}Phase 1 tests failed. Cannot proceed with CLI spec generation.${NC}"
                exit 1
            fi
        else
            echo -e "${RED}Phase 1 test script not found. Please run Phase 1 tests first.${NC}"
            exit 1
        fi
    fi

    # Run CLI specification generation tests
    echo -e "\n${YELLOW}Starting CLI specification generation tests...${NC}"

    # Test 1: Simple template CLI spec
    if ! run_cli_spec_test "simple" 3; then
        failed=1
    fi

    # Test 2: Complex template CLI spec
    if ! run_cli_spec_test "complex" 6; then
        failed=1
    fi

    # Summary
    echo -e "\n${YELLOW}CLI Specification Generation Test Summary:${NC}"
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}✓ All CLI specification generation tests passed${NC}"
        echo -e "${GREEN}✓ T2.1 implementation validated${NC}"
    else
        echo -e "${RED}✗ Some CLI specification generation tests failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
