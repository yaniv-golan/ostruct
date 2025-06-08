#!/bin/bash
# test_unit.sh - Unit tests for individual functions and components

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_LOG_FILE="$PROJECT_ROOT/temp/test_unit.log"

cd "$PROJECT_ROOT"

# Initialize test environment
mkdir -p "temp"
echo "=== Document Converter Unit Tests ===" | tee "$TEST_LOG_FILE"
echo "Started at $(date)" | tee -a "$TEST_LOG_FILE"
echo "" | tee -a "$TEST_LOG_FILE"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging function
log_test() {
    echo "$1" | tee -a "$TEST_LOG_FILE"
}

# Test assertion function
assert_equals() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    ((TOTAL_TESTS++))
    if [[ "$expected" == "$actual" ]]; then
        log_test "✅ PASS: $test_name"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $test_name"
        log_test "  Expected: '$expected'"
        log_test "  Actual: '$actual'"
        ((FAILED_TESTS++))
    fi
}

# Test file existence
assert_file_exists() {
    local file_path="$1"
    local test_name="$2"

    ((TOTAL_TESTS++))
    if [[ -f "$file_path" ]]; then
        log_test "✅ PASS: $test_name"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $test_name - File not found: $file_path"
        ((FAILED_TESTS++))
    fi
}

# Test directory existence
assert_dir_exists() {
    local dir_path="$1"
    local test_name="$2"

    ((TOTAL_TESTS++))
    if [[ -d "$dir_path" ]]; then
        log_test "✅ PASS: $test_name"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $test_name - Directory not found: $dir_path"
        ((FAILED_TESTS++))
    fi
}

# Test command success
assert_command_success() {
    local command="$1"
    local test_name="$2"

    ((TOTAL_TESTS++))
    if eval "$command" >/dev/null 2>&1; then
        log_test "✅ PASS: $test_name"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $test_name - Command failed: $command"
        ((FAILED_TESTS++))
    fi
}

# Test JSON validity
assert_valid_json() {
    local json_file="$1"
    local test_name="$2"

    ((TOTAL_TESTS++))
    if jq empty "$json_file" 2>/dev/null; then
        log_test "✅ PASS: $test_name"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $test_name - Invalid JSON: $json_file"
        ((FAILED_TESTS++))
    fi
}

log_test "=== Configuration Tests ==="
log_test ""

# Test 1: Configuration file structure
assert_file_exists "config/default.conf" "Default configuration exists"
assert_file_exists "config/development.conf" "Development configuration exists"
assert_file_exists "config/production.conf" "Production configuration exists"
assert_file_exists "config/testing.conf" "Testing configuration exists"

# Test 2: Configuration loading
log_test ""
log_test "Testing configuration loading..."
source "config/default.conf"
assert_equals "gpt-4o-mini" "$DEFAULT_MODEL_ANALYSIS" "Default analysis model setting"
assert_equals "gpt-4o" "$DEFAULT_MODEL_PLANNING" "Default planning model setting"
assert_equals "true" "$ENABLE_CACHING" "Default caching setting"

log_test ""
log_test "=== Schema Validation Tests ==="
log_test ""

# Test 3: JSON Schema validation
assert_valid_json "schemas/analysis.json" "Analysis schema is valid JSON"
assert_valid_json "schemas/plan.json" "Plan schema is valid JSON"
assert_valid_json "schemas/safety.json" "Safety schema is valid JSON"
assert_valid_json "schemas/validation.json" "Validation schema is valid JSON"

# Test 4: Schema structure validation
log_test ""
log_test "Testing schema structure..."

# Check if schemas have required OpenAI structured output fields
for schema in schemas/*.json; do
    schema_name=$(basename "$schema" .json)
    ((TOTAL_TESTS++))

    if jq -e '.type == "object" and .properties and .required' "$schema" >/dev/null 2>&1; then
        log_test "✅ PASS: $schema_name schema has required OpenAI structure"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $schema_name schema missing required OpenAI structure"
        ((FAILED_TESTS++))
    fi
done

log_test ""
log_test "=== Template Tests ==="
log_test ""

# Test 5: Template file existence
assert_file_exists "prompts/analyze.j2" "Analysis template exists"
assert_file_exists "prompts/plan.j2" "Planning template exists"
assert_file_exists "prompts/replan.j2" "Replanning template exists"
assert_file_exists "prompts/safety_check.j2" "Safety check template exists"
assert_file_exists "prompts/validate.j2" "Validation template exists"

# Test 6: Template syntax validation (basic check)
log_test ""
log_test "Testing template syntax..."
for template in prompts/*.j2; do
    template_name=$(basename "$template" .j2)
    ((TOTAL_TESTS++))

    # Check for basic Jinja2 syntax elements
    if grep -q "{{" "$template" && grep -q "}}" "$template"; then
        log_test "✅ PASS: $template_name template has Jinja2 syntax"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $template_name template missing Jinja2 syntax"
        ((FAILED_TESTS++))
    fi
done

log_test ""
log_test "=== Tool Documentation Tests ==="
log_test ""

# Test 7: Tool documentation existence
assert_dir_exists "tools" "Tools directory exists"

# Check for key tool documentation
tool_docs=("pandoc.md" "pdftotext.md" "tesseract.md" "markitdown.md" "libreoffice.md")
for tool_doc in "${tool_docs[@]}"; do
    assert_file_exists "tools/$tool_doc" "Tool documentation: $tool_doc"
done

# Test 8: Tool documentation format
log_test ""
log_test "Testing tool documentation format..."
for tool_file in tools/*.md; do
    tool_name=$(basename "$tool_file" .md)
    ((TOTAL_TESTS++))

    # Check for YAML frontmatter
    if head -1 "$tool_file" | grep -q "^---$"; then
        log_test "✅ PASS: $tool_name has YAML frontmatter"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $tool_name missing YAML frontmatter"
        ((FAILED_TESTS++))
    fi
done

log_test ""
log_test "=== Script Tests ==="
log_test ""

# Test 9: Script executability
scripts=("convert.sh" "scripts/check_tools.sh" "scripts/cleanup.sh" "scripts/test_basic.sh")
for script in "${scripts[@]}"; do
    ((TOTAL_TESTS++))
    if [[ -x "$script" ]]; then
        log_test "✅ PASS: $script is executable"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $script is not executable"
        ((FAILED_TESTS++))
    fi
done

# Test 10: Script help functionality
log_test ""
log_test "Testing script help functionality..."
assert_command_success "./convert.sh --help" "convert.sh help command"
assert_command_success "./scripts/check_tools.sh" "check_tools.sh execution"
assert_command_success "./scripts/cleanup.sh --help" "cleanup.sh help command"

log_test ""
log_test "=== Directory Structure Tests ==="
log_test ""

# Test 11: Required directories
required_dirs=("prompts" "schemas" "tools" "config" "scripts" "temp" "output")
for dir in "${required_dirs[@]}"; do
    assert_dir_exists "$dir" "Required directory: $dir"
done

# Test 12: Directory permissions
log_test ""
log_test "Testing directory permissions..."
for dir in "temp" "output"; do
    ((TOTAL_TESTS++))
    if [[ -w "$dir" ]]; then
        log_test "✅ PASS: $dir is writable"
        ((PASSED_TESTS++))
    else
        log_test "❌ FAIL: $dir is not writable"
        ((FAILED_TESTS++))
    fi
done

log_test ""
log_test "=== Function Tests ==="
log_test ""

# Test 13: Source convert.sh functions (without executing main)
log_test "Testing function definitions..."

# Create a test script that sources convert.sh functions
cat > temp/test_functions.sh << 'EOF'
#!/bin/bash
set -euo pipefail

# Source the convert.sh script but prevent main execution
SKIP_MAIN=true

# Mock some variables to prevent errors
PROJECT_ROOT="$(pwd)"
TEMP_DIR="$PROJECT_ROOT/temp"
CACHE_DIR="$TEMP_DIR/cache"
LOG_FILE="$TEMP_DIR/test.log"
COMPLETED_STEPS_FILE="$TEMP_DIR/completed_steps.txt"

# Source the functions (skip main execution)
source convert.sh 2>/dev/null || true

# Test if key functions are defined
functions_to_test=(
    "validate_configuration"
    "check_dependencies"
    "validate_plan_dependencies"
    "validate_plan_tools"
    "get_cached_analysis"
    "profile_execution"
    "safety_check"
)

for func in "${functions_to_test[@]}"; do
    if declare -f "$func" >/dev/null 2>&1; then
        echo "✅ Function $func is defined"
    else
        echo "❌ Function $func is not defined"
        exit 1
    fi
done
EOF

chmod +x temp/test_functions.sh
assert_command_success "./temp/test_functions.sh" "Function definitions test"

# Generate test report
log_test ""
log_test "=== Unit Test Results Summary ==="
log_test ""
log_test "Total Tests: $TOTAL_TESTS"
log_test "Passed: $PASSED_TESTS"
log_test "Failed: $FAILED_TESTS"
log_test "Success Rate: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"
log_test ""

# Final status
if [[ $FAILED_TESTS -eq 0 ]]; then
    log_test "🎉 All unit tests passed!"
    log_test ""
    log_test "Test log saved to: $TEST_LOG_FILE"
    exit 0
else
    log_test "❌ $FAILED_TESTS unit test(s) failed"
    log_test ""
    log_test "Check the test log for details: $TEST_LOG_FILE"
    exit 1
fi
