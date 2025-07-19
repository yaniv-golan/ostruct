#!/bin/bash

# Test script for Phase 3 components (T3.1-T3.5)
# Tests assembly, front-matter generation, template processing, validation, and quality assessment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================"
echo "OST Generator Phase 3 Comprehensive Test Suite"
echo "================================================"
echo "Starting Phase 3 comprehensive test suite..."
echo "Test directory: $PROJECT_ROOT/test"
echo "Timestamp: $(date)"
echo

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_script="$2"

    echo "Running $test_name..."
    if "$test_script"; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
    fi
}

# Individual test functions
test_assembly() {
    echo -e "${BLUE}=== Testing OST Assembly (T3.1) ===${NC}"

    # Test with simple template
    echo "Testing OST assembly for simple template..."

    # Create test input by combining all Phase 2 outputs
    local assembly_input="$PROJECT_ROOT/test/assembly_input_simple.json"
    cat > "$assembly_input" << EOF
{
    "template_content": "{{ input_text }}\\n{% if format == 'json' %}JSON output{% endif %}",
    "schema_content": "{\\"type\\": \\"object\\", \\"properties\\": {\\"result\\": {\\"type\\": \\"string\\"}}}",
    "cli_specification": $(cat "$PROJECT_ROOT/test/cli_spec_simple.json"),
    "cli_naming": $(cat "$PROJECT_ROOT/test/simple_cli_naming.json"),
    "help_documentation": $(cat "$PROJECT_ROOT/test/simple_help_generation.json"),
    "policy_configuration": $(cat "$PROJECT_ROOT/test/simple_policy_generation.json"),
    "defaults_management": $(cat "$PROJECT_ROOT/test/simple_defaults_management.json")
}
EOF

    # Generate assembly
    poetry run ostruct run \
        "$PROJECT_ROOT/src/assemble_ost.j2" \
        "$PROJECT_ROOT/src/assembly_schema.json" \
        --file prompt:input "$assembly_input" \
        --output-file "$PROJECT_ROOT/test/simple_assembly.json"

    # Validate output
    if [ -f "$PROJECT_ROOT/test/simple_assembly.json" ]; then
        echo -e "${GREEN}✓ Simple assembly output created${NC}"

        # Check JSON validity
        if jq empty "$PROJECT_ROOT/test/simple_assembly.json" 2>/dev/null; then
            echo -e "${GREEN}✓ Simple assembly output is valid JSON${NC}"
        else
            echo -e "${RED}✗ Simple assembly output is invalid JSON${NC}"
            return 1
        fi

        # Check for required fields
        if jq -e '.ost_file_content' "$PROJECT_ROOT/test/simple_assembly.json" >/dev/null; then
            echo -e "${GREEN}✓ Simple assembly contains OST file content${NC}"
        else
            echo -e "${RED}✗ Simple assembly missing OST file content${NC}"
            return 1
        fi

        # Check for metadata
        if jq -e '.assembly_metadata' "$PROJECT_ROOT/test/simple_assembly.json" >/dev/null; then
            echo -e "${GREEN}✓ Simple assembly contains metadata${NC}"
        else
            echo -e "${RED}✗ Simple assembly missing metadata${NC}"
            return 1
        fi

        echo "  File size: $(wc -c < "$PROJECT_ROOT/test/simple_assembly.json") bytes"
    else
        echo -e "${RED}✗ Simple assembly output not created${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ OST Assembly test passed${NC}"
    return 0
}

test_frontmatter() {
    echo -e "${BLUE}=== Testing Front-matter Generation (T3.2) ===${NC}"

    # Test with simple template
    echo "Testing front-matter generation for simple template..."

    # Create test input by combining Phase 2 outputs
    local frontmatter_input="$PROJECT_ROOT/test/frontmatter_input_simple.json"
    cat > "$frontmatter_input" << EOF
{
    "cli_specification": $(cat "$PROJECT_ROOT/test/cli_spec_simple.json"),
    "cli_naming": $(cat "$PROJECT_ROOT/test/simple_cli_naming.json"),
    "help_documentation": $(cat "$PROJECT_ROOT/test/simple_help_generation.json"),
    "policy_configuration": $(cat "$PROJECT_ROOT/test/simple_policy_generation.json"),
    "defaults_management": $(cat "$PROJECT_ROOT/test/simple_defaults_management.json")
}
EOF

    # Generate front-matter
    poetry run ostruct run \
        "$PROJECT_ROOT/src/build_frontmatter.j2" \
        "$PROJECT_ROOT/src/frontmatter_schema.json" \
        --file prompt:input "$frontmatter_input" \
        --output-file "$PROJECT_ROOT/test/simple_frontmatter.json"

    # Validate output
    if [ -f "$PROJECT_ROOT/test/simple_frontmatter.json" ]; then
        echo -e "${GREEN}✓ Simple front-matter output created${NC}"

        # Check JSON validity
        if jq empty "$PROJECT_ROOT/test/simple_frontmatter.json" 2>/dev/null; then
            echo -e "${GREEN}✓ Simple front-matter output is valid JSON${NC}"
        else
            echo -e "${RED}✗ Simple front-matter output is invalid JSON${NC}"
            return 1
        fi

        # Check for required fields
        if jq -e '.yaml_frontmatter' "$PROJECT_ROOT/test/simple_frontmatter.json" >/dev/null; then
            echo -e "${GREEN}✓ Simple front-matter contains YAML content${NC}"
        else
            echo -e "${RED}✗ Simple front-matter missing YAML content${NC}"
            return 1
        fi

        # Check for structure
        if jq -e '.frontmatter_structure' "$PROJECT_ROOT/test/simple_frontmatter.json" >/dev/null; then
            echo -e "${GREEN}✓ Simple front-matter contains structure${NC}"
        else
            echo -e "${RED}✗ Simple front-matter missing structure${NC}"
            return 1
        fi

        echo "  File size: $(wc -c < "$PROJECT_ROOT/test/simple_frontmatter.json") bytes"
    else
        echo -e "${RED}✗ Simple front-matter output not created${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Front-matter Generation test passed${NC}"
    return 0
}

test_body_processing() {
    echo -e "${BLUE}=== Testing Template Body Processing (T3.3) ===${NC}"

    # Test with simple template
    echo "Testing template body processing for simple template..."

    # Create test input
    local body_input="$PROJECT_ROOT/test/body_input_simple.json"
    cat > "$body_input" << EOF
{
    "template_content": "{{ input_text }}\\n{% if format == 'json' %}JSON output{% endif %}",
    "template_analysis": $(cat "$PROJECT_ROOT/test/template_analysis_simple.json"),
    "variable_classification": $(cat "$PROJECT_ROOT/test/variable_classification_simple.json"),
    "cli_specification": $(cat "$PROJECT_ROOT/test/cli_spec_simple.json"),
    "cli_naming": $(cat "$PROJECT_ROOT/test/simple_cli_naming.json")
}
EOF

    # Generate processed body
    poetry run ostruct run \
        "$PROJECT_ROOT/src/process_body.j2" \
        "$PROJECT_ROOT/src/body_processing_schema.json" \
        --file prompt:input "$body_input" \
        --output-file "$PROJECT_ROOT/test/simple_body_processing.json"

    # Validate output
    if [ -f "$PROJECT_ROOT/test/simple_body_processing.json" ]; then
        echo -e "${GREEN}✓ Simple body processing output created${NC}"

        # Check JSON validity
        if jq empty "$PROJECT_ROOT/test/simple_body_processing.json" 2>/dev/null; then
            echo -e "${GREEN}✓ Simple body processing output is valid JSON${NC}"
        else
            echo -e "${RED}✗ Simple body processing output is invalid JSON${NC}"
            return 1
        fi

        # Check for required fields
        if jq -e '.enhanced_template_body' "$PROJECT_ROOT/test/simple_body_processing.json" >/dev/null; then
            echo -e "${GREEN}✓ Simple body processing contains enhanced template${NC}"
        else
            echo -e "${RED}✗ Simple body processing missing enhanced template${NC}"
            return 1
        fi

        echo "  File size: $(wc -c < "$PROJECT_ROOT/test/simple_body_processing.json") bytes"
    else
        echo -e "${RED}✗ Simple body processing output not created${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Template Body Processing test passed${NC}"
    return 0
}

test_validation() {
    echo -e "${BLUE}=== Testing OST Validation (T3.4) ===${NC}"

    # Create a simple test OST file
    local test_ost="$PROJECT_ROOT/test/test_simple.ost"
    cat > "$test_ost" << 'EOF'
---
name: test-tool
description: "A test tool for validation"
version: "1.0.0"
author: "OST Generator"

arguments:
  - name: input
    type: string
    required: true
    help: "Input text to process"

tools:
  code_interpreter: false
  file_search: false
  web_search: false

model:
  default: "gpt-4-turbo"
  allowed: ["gpt-4-turbo", "gpt-4"]

security:
  validate_inputs: true
  sanitize_outputs: true
  file_access: restricted
---

{# Test template #}
{{ input }}
EOF

    # Test the validation script
    if bash "$PROJECT_ROOT/src/validate_ost.sh" "$test_ost"; then
        echo -e "${GREEN}✓ OST validation script works correctly${NC}"
    else
        echo -e "${RED}✗ OST validation script failed${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ OST Validation test passed${NC}"
    return 0
}

test_quality_assessment() {
    echo -e "${BLUE}=== Testing Quality Assessment (T3.5) ===${NC}"

    # Test with simple template
    echo "Testing quality assessment for simple template..."

    # Create test input
    local quality_input="$PROJECT_ROOT/test/quality_input_simple.json"
    cat > "$quality_input" << EOF
{
    "ost_file_content": "---\\nname: test-tool\\ndescription: Test tool\\nversion: 1.0.0\\n---\\n{{ input }}",
    "assembly_metadata": {"tool_name": "test-tool", "version": "1.0.0"},
    "frontmatter_structure": {"metadata": {"name": "test-tool"}},
    "template_processing_results": {"enhanced_template_body": "{{ input }}"},
    "original_template": "{{ input }}",
    "original_schema": "{\\"type\\": \\"object\\"}"
}
EOF

    # Generate quality assessment
    poetry run ostruct run \
        "$PROJECT_ROOT/src/assess_quality.j2" \
        "$PROJECT_ROOT/src/quality_assessment_schema.json" \
        --file prompt:input "$quality_input" \
        --output-file "$PROJECT_ROOT/test/simple_quality_assessment.json"

    # Validate output
    if [ -f "$PROJECT_ROOT/test/simple_quality_assessment.json" ]; then
        echo -e "${GREEN}✓ Simple quality assessment output created${NC}"

        # Check JSON validity
        if jq empty "$PROJECT_ROOT/test/simple_quality_assessment.json" 2>/dev/null; then
            echo -e "${GREEN}✓ Simple quality assessment output is valid JSON${NC}"
        else
            echo -e "${RED}✗ Simple quality assessment output is invalid JSON${NC}"
            return 1
        fi

        # Check for required fields
        if jq -e '.overall_assessment' "$PROJECT_ROOT/test/simple_quality_assessment.json" >/dev/null; then
            echo -e "${GREEN}✓ Simple quality assessment contains overall assessment${NC}"
        else
            echo -e "${RED}✗ Simple quality assessment missing overall assessment${NC}"
            return 1
        fi

        echo "  File size: $(wc -c < "$PROJECT_ROOT/test/simple_quality_assessment.json") bytes"
    else
        echo -e "${RED}✗ Simple quality assessment output not created${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Quality Assessment test passed${NC}"
    return 0
}

# Run all Phase 3 tests
echo "Running individual test suites..."
echo

# Run Phase 3 tests
run_test "OST Assembly (T3.1)" test_assembly
run_test "Front-matter Generation (T3.2)" test_frontmatter
run_test "Template Body Processing (T3.3)" test_body_processing
run_test "OST Validation (T3.4)" test_validation
run_test "Quality Assessment (T3.5)" test_quality_assessment

echo
echo "================================================"
echo "Phase 3 Test Report"
echo "================================================"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All Phase 3 tests passed!${NC}"
    echo -e "${GREEN}✓ OST assembly working${NC}"
    echo -e "${GREEN}✓ Front-matter generation working${NC}"
    echo -e "${GREEN}✓ Template body processing working${NC}"
    echo -e "${GREEN}✓ OST validation working${NC}"
    echo -e "${GREEN}✓ Quality assessment working${NC}"
    echo
    echo "Output Files Generated:"
    for file in "$PROJECT_ROOT/test"/*.json; do
        if [[ -f "$file" && "$(basename "$file")" =~ ^(simple_assembly|simple_frontmatter|simple_body_processing|simple_quality_assessment)\.json$ ]]; then
            echo "  $(basename "$file") ($(wc -c < "$file" | tr -d ' ') bytes)"
        fi
    done
    echo
    echo "Test execution completed in $(date)"
    echo
    echo -e "${GREEN}✅ Phase 3 implementation fully validated${NC}"
    echo -e "${GREEN}Ready to proceed to Phase 4 (Orchestration & Polish)${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}  - $test${NC}"
    done
    exit 1
fi
