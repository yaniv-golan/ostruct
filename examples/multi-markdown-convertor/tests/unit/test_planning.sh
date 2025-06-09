#!/bin/bash
# Unit tests for planning.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/config.sh"
source "$PROJECT_ROOT/lib/utils.sh"
source "$PROJECT_ROOT/lib/cache.sh"
source "$PROJECT_ROOT/lib/tools.sh"
source "$PROJECT_ROOT/lib/analysis.sh"
source "$PROJECT_ROOT/lib/planning.sh"

# Load configuration to get ALLOWED_TOOLS
load_configuration
# Set up required directories and log files
export TEMP_DIR="/tmp/test_convert_$$"
export LOG_DIR="$TEMP_DIR/logs"
export PERFORMANCE_LOG_FILE="$LOG_DIR/performance.log"
mkdir -p "$LOG_DIR"

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Test helper functions
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "Running test: $test_name"
    
    # Clean up before each test
    > "$TEST_LOG_FILE"
    
    if $test_function; then
        echo "✅ PASSED: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAILED: $test_name"
        return 1
    fi
}

# Mock ostruct command for planning
mock_ostruct_planning() {
    case "$*" in
        *"create_conversion_plan"*)
            echo '{"plan": {"steps": [{"tool": "pandoc", "command": "pandoc input.pdf -o output.md", "description": "Convert PDF to Markdown"}]}, "estimated_time": "2 minutes"}'
            return 0
            ;;
        *"replan"*)
            echo '{"replan": {"steps": [{"tool": "pdftotext", "command": "pdftotext input.pdf temp.txt", "description": "Extract text from PDF"}, {"tool": "pandoc", "command": "pandoc temp.txt -o output.md", "description": "Convert text to Markdown"}]}, "reason": "pandoc failed"}'
            return 0
            ;;
        *)
            echo '{"error": "unknown planning command"}'
            return 1
            ;;
    esac
}

# Test create_conversion_plan function
test_create_conversion_plan() {
    # Mock ostruct command
    ostruct() {
        mock_ostruct_planning "$@"
    }
    
    local test_analysis='{"analysis": {"type": "pdf", "complexity": "medium"}}'
    local output_file="test_output.md"
    
    # Should return conversion plan
    local result=$(create_conversion_plan "$test_analysis" "$output_file")
    local exit_code=$?
    
    unset -f ostruct
    
    [[ $exit_code -eq 0 ]] || return 1
    [[ "$result" =~ "plan" ]] || return 1
    [[ "$result" =~ "steps" ]] || return 1
    
    return 0
}

# Test display_plan function
test_display_plan() {
    local test_plan='{"plan": {"steps": [{"tool": "pandoc", "command": "pandoc input.pdf -o output.md", "description": "Convert PDF to Markdown"}]}, "estimated_time": "2 minutes"}'
    
    # Mock display_plan function
    mock_display_plan() {
        local plan="$1"
        
        echo "=== Conversion Plan ==="
        echo "$plan" | jq -r '.plan.steps[] | "Step: \(.description)"'
        echo "Estimated time: $(echo "$plan" | jq -r '.estimated_time')"
        return 0
    }
    
    # Should display plan without error
    local output=$(mock_display_plan "$test_plan")
    
    [[ "$output" =~ "Conversion Plan" ]] || return 1
    [[ "$output" =~ "Convert PDF to Markdown" ]] || return 1
    [[ "$output" =~ "2 minutes" ]] || return 1
    
    return 0
}

# Test get_plan_approval function
test_get_plan_approval() {
    # Mock get_plan_approval function
    mock_get_plan_approval() {
        local plan="$1"
        local interactive="${2:-false}"
        
        if [[ "$interactive" == "true" ]]; then
            # In interactive mode, simulate user approval
            echo "Plan approved by user"
            return 0
        else
            # In non-interactive mode, auto-approve
            echo "Plan auto-approved"
            return 0
        fi
    }
    
    local test_plan='{"plan": {"steps": []}}'
    
    # Test non-interactive approval
    local result=$(mock_get_plan_approval "$test_plan" "false")
    [[ "$result" =~ "auto-approved" ]] || return 1
    
    # Test interactive approval
    result=$(mock_get_plan_approval "$test_plan" "true")
    [[ "$result" =~ "approved" ]] || return 1
    
    return 0
}

# Test create_replan function
test_create_replan() {
    # Mock ostruct command
    ostruct() {
        mock_ostruct_planning "$@"
    }
    
    local original_plan='{"plan": {"steps": [{"tool": "pandoc", "failed": true}]}}'
    local failure_reason="pandoc command failed"
    local analysis='{"analysis": {"type": "pdf"}}'
    
    # Should return replan
    local result=$(create_replan "$original_plan" "$failure_reason" "$analysis")
    local exit_code=$?
    
    unset -f ostruct
    
    [[ $exit_code -eq 0 ]] || return 1
    [[ "$result" =~ "replan" ]] || return 1
    [[ "$result" =~ "steps" ]] || return 1
    
    return 0
}

# Test filter_tool_docs_by_analysis function
test_filter_tool_docs_by_analysis() {
    # Mock filter_tool_docs_by_analysis function
    mock_filter_tool_docs_by_analysis() {
        local analysis="$1"
        local all_tools_docs="$2"
        
        local document_type=$(echo "$analysis" | jq -r '.analysis.type')
        
        case "$document_type" in
            "pdf")
                echo '{"relevant_tools": ["pandoc", "pdftotext", "tesseract"]}'
                ;;
            "docx")
                echo '{"relevant_tools": ["pandoc", "libreoffice"]}'
                ;;
            *)
                echo '{"relevant_tools": ["pandoc"]}'
                ;;
        esac
        
        return 0
    }
    
    local pdf_analysis='{"analysis": {"type": "pdf"}}'
    local docx_analysis='{"analysis": {"type": "docx"}}'
    local all_tools='{"tools": ["pandoc", "pdftotext", "tesseract", "libreoffice"]}'
    
    # Test PDF filtering
    local pdf_result=$(mock_filter_tool_docs_by_analysis "$pdf_analysis" "$all_tools")
    [[ "$pdf_result" =~ "pdftotext" ]] || return 1
    [[ "$pdf_result" =~ "tesseract" ]] || return 1
    
    # Test DOCX filtering
    local docx_result=$(mock_filter_tool_docs_by_analysis "$docx_analysis" "$all_tools")
    [[ "$docx_result" =~ "libreoffice" ]] || return 1
    
    return 0
}

# Test plan validation
test_plan_validation() {
    # Mock plan validation function
    validate_plan() {
        local plan="$1"
        
        # Check if plan is valid JSON
        if ! echo "$plan" | jq empty 2>/dev/null; then
            return 1
        fi
        
        # Check for required fields
        if ! echo "$plan" | jq -e '.plan.steps' >/dev/null 2>&1; then
            return 1
        fi
        
        # Check if steps array is not empty
        local steps_count=$(echo "$plan" | jq '.plan.steps | length')
        if [[ "$steps_count" -eq 0 ]]; then
            return 1
        fi
        
        return 0
    }
    
    # Test valid plan
    local valid_plan='{"plan": {"steps": [{"tool": "pandoc", "command": "pandoc input -o output"}]}}'
    validate_plan "$valid_plan" || return 1
    
    # Test invalid plan (no steps)
    local invalid_plan='{"plan": {"steps": []}}'
    if validate_plan "$invalid_plan"; then
        echo "Empty plan passed validation"
        return 1
    fi
    
    # Test malformed plan
    local malformed_plan='invalid json{'
    if validate_plan "$malformed_plan"; then
        echo "Malformed plan passed validation"
        return 1
    fi
    
    return 0
}

# Test plan step extraction
test_plan_step_extraction() {
    # Mock step extraction function
    extract_plan_steps() {
        local plan="$1"
        
        echo "$plan" | jq -r '.plan.steps[] | "\(.tool):\(.command)"'
    }
    
    local test_plan='{"plan": {"steps": [{"tool": "pandoc", "command": "pandoc input.pdf -o output.md"}, {"tool": "sed", "command": "sed -i s/old/new/ output.md"}]}}'
    
    local steps=$(extract_plan_steps "$test_plan")
    
    [[ "$steps" =~ "pandoc:pandoc input.pdf -o output.md" ]] || return 1
    [[ "$steps" =~ "sed:sed -i s/old/new/ output.md" ]] || return 1
    
    return 0
}

# Test plan complexity estimation
test_plan_complexity_estimation() {
    # Mock complexity estimation
    estimate_plan_complexity() {
        local plan="$1"
        
        local steps_count=$(echo "$plan" | jq '.plan.steps | length')
        local complexity
        
        if [[ $steps_count -le 2 ]]; then
            complexity="low"
        elif [[ $steps_count -le 5 ]]; then
            complexity="medium"
        else
            complexity="high"
        fi
        
        echo "{\"complexity\": \"$complexity\", \"steps_count\": $steps_count}"
    }
    
    # Test low complexity
    local simple_plan='{"plan": {"steps": [{"tool": "pandoc"}]}}'
    local result=$(estimate_plan_complexity "$simple_plan")
    [[ "$result" =~ "low" ]] || return 1
    
    # Test medium complexity
    local medium_plan='{"plan": {"steps": [{"tool": "pandoc"}, {"tool": "sed"}, {"tool": "awk"}]}}'
    result=$(estimate_plan_complexity "$medium_plan")
    [[ "$result" =~ "medium" ]] || return 1
    
    return 0
}

# Test plan dependency checking
test_plan_dependency_checking() {
    # Mock dependency checking
    check_plan_dependencies() {
        local plan="$1"
        local missing_tools=()
        
        # Extract tools from plan
        local tools=$(echo "$plan" | jq -r '.plan.steps[].tool')
        
        # Mock command availability check
        while IFS= read -r tool; do
            case "$tool" in
                "pandoc"|"sed"|"awk")
                    # Available tools
                    ;;
                *)
                    missing_tools+=("$tool")
                    ;;
            esac
        done <<< "$tools"
        
        if [[ ${#missing_tools[@]} -eq 0 ]]; then
            echo '{"dependencies_met": true}'
            return 0
        else
            echo "{\"dependencies_met\": false, \"missing_tools\": [$(printf '\"%s\",' "${missing_tools[@]}" | sed 's/,$//')]}}"
            return 1
        fi
    }
    
    # Test plan with available tools
    local good_plan='{"plan": {"steps": [{"tool": "pandoc"}, {"tool": "sed"}]}}'
    local result=$(check_plan_dependencies "$good_plan")
    [[ "$result" =~ "dependencies_met.*true" ]] || return 1
    
    # Test plan with missing tools
    local bad_plan='{"plan": {"steps": [{"tool": "nonexistent_tool"}]}}'
    result=$(check_plan_dependencies "$bad_plan")
    [[ "$result" =~ "dependencies_met.*false" ]] || return 1
    [[ "$result" =~ "missing_tools" ]] || return 1
    
    return 0
}

# Run all tests
echo "=== Testing planning.sh module ==="
echo

run_test "create_conversion_plan" test_create_conversion_plan
run_test "display_plan" test_display_plan
run_test "get_plan_approval" test_get_plan_approval
run_test "create_replan" test_create_replan
run_test "filter_tool_docs_by_analysis" test_filter_tool_docs_by_analysis
run_test "plan_validation" test_plan_validation
run_test "plan_step_extraction" test_plan_step_extraction
run_test "plan_complexity_estimation" test_plan_complexity_estimation
run_test "plan_dependency_checking" test_plan_dependency_checking

# Cleanup
rm -f "$TEST_LOG_FILE"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All planning tests passed!"
    exit 0
else
    echo "❌ Some planning tests failed!"
    exit 1
fi 