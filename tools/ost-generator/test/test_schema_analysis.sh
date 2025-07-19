#!/bin/bash

# Test script for schema analysis (T1.3)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../src"
TEST_DIR="$SCRIPT_DIR"
FIXTURES_DIR="$TEST_DIR/fixtures"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing Schema Analysis (T1.3)${NC}"

# Function to run schema analysis test
run_schema_analysis_test() {
    local test_name="$1"
    local schema_file="$2"
    local expected_fields="$3"

    echo -e "\n${YELLOW}Running schema analysis test: $test_name${NC}"

    # Check if schema file exists
    if [[ ! -f "$schema_file" ]]; then
        echo -e "${RED}ERROR: Schema file not found: $schema_file${NC}"
        return 1
    fi

    # Read schema JSON
    local schema_json
    schema_json=$(cat "$schema_file")

    # Test dry-run first
    echo "Testing dry-run mode..."
    if ostruct run "$SRC_DIR/analyze_schema.j2" "$SRC_DIR/schema_analysis_schema.json" \
        --var schema_json="$schema_json" \
        --dry-run > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dry-run passed${NC}"
    else
        echo -e "${RED}✗ Dry-run failed${NC}"
        return 1
    fi

    # Test live API call
    echo "Testing live API call..."
    local output_file="$TEST_DIR/schema_analysis_${test_name}.json"
    if ostruct run "$SRC_DIR/analyze_schema.j2" "$SRC_DIR/schema_analysis_schema.json" \
        --var schema_json="$schema_json" \
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
    local required_fields=("schema_structure" "field_analysis" "validation_rules" "output_guidance")
    for field in "${required_fields[@]}"; do
        if jq -e "has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Has required field: $field${NC}"
        else
            echo -e "${RED}✗ Missing required field: $field${NC}"
            return 1
        fi
    done

    # Check schema structure fields
    local structure_fields=("root_type" "required_fields" "optional_fields")
    for field in "${structure_fields[@]}"; do
        if jq -e ".schema_structure | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Schema structure has field: $field${NC}"
        else
            echo -e "${RED}✗ Schema structure missing field: $field${NC}"
            return 1
        fi
    done

    # Check field analysis count
    local field_count
    field_count=$(jq '.field_analysis | length' "$output_file")
    if [[ "$field_count" -ge "$expected_fields" ]]; then
        echo -e "${GREEN}✓ Found $field_count fields (expected >= $expected_fields)${NC}"
    else
        echo -e "${RED}✗ Found $field_count fields (expected >= $expected_fields)${NC}"
        return 1
    fi

    # Check validation rules structure
    local validation_fields=("has_strict_types" "complexity_score")
    for field in "${validation_fields[@]}"; do
        if jq -e ".validation_rules | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Validation rules has field: $field${NC}"
        else
            echo -e "${RED}✗ Validation rules missing field: $field${NC}"
            return 1
        fi
    done

    # Check output guidance structure
    local guidance_fields=("structured_output" "validation_level" "suggested_tools")
    for field in "${guidance_fields[@]}"; do
        if jq -e ".output_guidance | has(\"$field\")" "$output_file" > /dev/null; then
            echo -e "${GREEN}✓ Output guidance has field: $field${NC}"
        else
            echo -e "${RED}✗ Output guidance missing field: $field${NC}"
            return 1
        fi
    done

    # Show sample analysis
    echo -e "\n${YELLOW}Schema structure:${NC}"
    jq -C '.schema_structure' "$output_file"

    echo -e "\n${YELLOW}Sample field analysis:${NC}"
    jq -C '.field_analysis[0]' "$output_file"

    echo -e "\n${YELLOW}Validation rules:${NC}"
    jq -C '.validation_rules' "$output_file"

    echo -e "\n${YELLOW}Output guidance:${NC}"
    jq -C '.output_guidance' "$output_file"

    echo -e "${GREEN}✓ Schema analysis test '$test_name' passed${NC}"
    return 0
}

# Main test execution
main() {
    local failed=0

    echo "Starting schema analysis tests..."

    # Test 1: Simple schema
    if ! run_schema_analysis_test "simple" "$FIXTURES_DIR/simple_schema.json" 3; then
        failed=1
    fi

    # Test 2: Complex schema
    if ! run_schema_analysis_test "complex" "$FIXTURES_DIR/complex_schema.json" 8; then
        failed=1
    fi

    # Summary
    echo -e "\n${YELLOW}Schema Analysis Test Summary:${NC}"
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}✓ All schema analysis tests passed${NC}"
        echo -e "${GREEN}✓ T1.3 implementation validated${NC}"
    else
        echo -e "${RED}✗ Some schema analysis tests failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
