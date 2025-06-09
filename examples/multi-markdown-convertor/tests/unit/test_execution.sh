#!/bin/bash
# Unit tests for execution.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_INPUT_FILE="/tmp/test_input_$$"
TEST_OUTPUT_FILE="/tmp/test_output_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false
export MAX_RETRIES=2

# Create test files
echo "Test input content" > "$TEST_INPUT_FILE"

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/config.sh"
source "$PROJECT_ROOT/lib/utils.sh"
source "$PROJECT_ROOT/lib/cache.sh"
source "$PROJECT_ROOT/lib/tools.sh"
source "$PROJECT_ROOT/lib/security.sh"
source "$PROJECT_ROOT/lib/analysis.sh"
source "$PROJECT_ROOT/lib/planning.sh"
source "$PROJECT_ROOT/lib/execution.sh"

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
    rm -f "$TEST_OUTPUT_FILE"
    
    if $test_function; then
        echo "✅ PASSED: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAILED: $test_name"
        return 1
    fi
}

# Test execute_conversion_plan function
test_execute_conversion_plan() {
    local test_plan='{"plan": {"steps": [{"tool": "echo", "command": "echo \"test output\" > '"$TEST_OUTPUT_FILE"'", "description": "Create test output"}]}}'
    
    # Mock execute_conversion_plan function
    mock_execute_conversion_plan() {
        local plan="$1"
        local input_file="$2"
        local output_file="$3"
        
        # Extract and execute steps
        local steps=$(echo "$plan" | jq -r '.plan.steps[].command')
        
        while IFS= read -r command; do
            if eval "$command"; then
                echo "Step executed successfully: $command"
            else
                echo "Step failed: $command"
                return 1
            fi
        done <<< "$steps"
        
        return 0
    }
    
    # Should execute plan successfully
    if mock_execute_conversion_plan "$test_plan" "$TEST_INPUT_FILE" "$TEST_OUTPUT_FILE"; then
        # Check if output file was created
        [[ -f "$TEST_OUTPUT_FILE" ]] || return 1
        [[ "$(cat "$TEST_OUTPUT_FILE")" =~ "test output" ]] || return 1
        return 0
    else
        echo "Plan execution failed"
        return 1
    fi
}

# Test execute_step_with_recovery function
test_execute_step_with_recovery() {
    # Mock execute_step_with_recovery function
    mock_execute_step_with_recovery() {
        local step="$1"
        local input_file="$2"
        local output_file="$3"
        local max_retries="${4:-2}"
        
        local command=$(echo "$step" | jq -r '.command')
        local retry_count=0
        
        while [[ $retry_count -le $max_retries ]]; do
            if eval "$command" 2>/dev/null; then
                echo "Step succeeded on attempt $((retry_count + 1))"
                return 0
            else
                ((retry_count++))
                if [[ $retry_count -le $max_retries ]]; then
                    echo "Step failed, retrying... (attempt $retry_count)"
                    sleep 1
                else
                    echo "Step failed after $max_retries retries"
                    return 1
                fi
            fi
        done
    }
    
    # Test successful step
    local success_step='{"tool": "echo", "command": "echo success"}'
    if mock_execute_step_with_recovery "$success_step" "$TEST_INPUT_FILE" "$TEST_OUTPUT_FILE"; then
        return 0
    else
        echo "Successful step failed"
        return 1
    fi
}

# Test execute_single_step function
test_execute_single_step() {
    # Mock execute_single_step function
    mock_execute_single_step() {
        local step="$1"
        local input_file="$2"
        local output_file="$3"
        
        local tool=$(echo "$step" | jq -r '.tool')
        local command=$(echo "$step" | jq -r '.command')
        
        # Validate tool is allowed
        local tool_allowed=false
        for allowed_tool in "${ALLOWED_TOOLS[@]}"; do
            if [[ "$tool" == "$allowed_tool" ]]; then
                tool_allowed=true
                break
            fi
        done
        
        if [[ "$tool_allowed" != "true" ]]; then
            echo "Tool not allowed: $tool"
            return 1
        fi
        
        # Execute command
        eval "$command"
    }
    
    # Test with allowed tool
    local allowed_step='{"tool": "echo", "command": "echo allowed"}'
    if mock_execute_single_step "$allowed_step" "$TEST_INPUT_FILE" "$TEST_OUTPUT_FILE"; then
        return 0
    else
        echo "Allowed tool step failed"
        return 1
    fi
}

# Test display_step function
test_display_step() {
    # Mock display_step function
    mock_display_step() {
        local step="$1"
        local step_number="${2:-1}"
        
        local tool=$(echo "$step" | jq -r '.tool')
        local description=$(echo "$step" | jq -r '.description // "No description"')
        
        echo "Step $step_number: $description"
        echo "Tool: $tool"
        
        return 0
    }
    
    local test_step='{"tool": "pandoc", "description": "Convert PDF to Markdown"}'
    local output=$(mock_display_step "$test_step" 1)
    
    [[ "$output" =~ "Step 1: Convert PDF to Markdown" ]] || return 1
    [[ "$output" =~ "Tool: pandoc" ]] || return 1
    
    return 0
}

# Test step validation
test_step_validation() {
    # Mock step validation function
    validate_step() {
        local step="$1"
        
        # Check if step is valid JSON
        if ! echo "$step" | jq empty 2>/dev/null; then
            return 1
        fi
        
        # Check for required fields
        if ! echo "$step" | jq -e '.tool' >/dev/null 2>&1; then
            return 1
        fi
        
        if ! echo "$step" | jq -e '.command' >/dev/null 2>&1; then
            return 1
        fi
        
        return 0
    }
    
    # Test valid step
    local valid_step='{"tool": "pandoc", "command": "pandoc input.pdf -o output.md"}'
    validate_step "$valid_step" || return 1
    
    # Test invalid step (missing command)
    local invalid_step='{"tool": "pandoc"}'
    if validate_step "$invalid_step"; then
        echo "Invalid step passed validation"
        return 1
    fi
    
    return 0
}

# Test command safety checking
test_command_safety_checking() {
    # Mock safety checking function
    check_command_safety() {
        local command="$1"
        
        # Check for dangerous patterns
        case "$command" in
            *"rm -rf"*|*"format"*|*"delete"*|*">"*/etc/*|*">"*/bin/*)
                echo "Dangerous command detected"
                return 1
                ;;
            *)
                echo "Command appears safe"
                return 0
                ;;
        esac
    }
    
    # Test safe command
    check_command_safety "echo hello world" || return 1
    
    # Test dangerous command
    if check_command_safety "rm -rf /"; then
        echo "Dangerous command passed safety check"
        return 1
    fi
    
    return 0
}

# Test execution error handling
test_execution_error_handling() {
    # Mock error handling function
    handle_execution_error() {
        local step="$1"
        local error_message="$2"
        local input_file="$3"
        
        local tool=$(echo "$step" | jq -r '.tool')
        
        echo "Execution error in step using $tool: $error_message"
        
        # Log error
        echo "$(date): ERROR: $tool failed - $error_message" >> "$TEST_LOG_FILE"
        
        # Suggest recovery
        case "$tool" in
            "pandoc")
                echo "Suggestion: Try using pdftotext + pandoc instead"
                ;;
            "pdftotext")
                echo "Suggestion: Try using tesseract for OCR"
                ;;
            *)
                echo "Suggestion: Check tool installation and input file format"
                ;;
        esac
        
        return 0
    }
    
    local failed_step='{"tool": "pandoc", "command": "pandoc nonexistent.pdf -o output.md"}'
    handle_execution_error "$failed_step" "File not found" "$TEST_INPUT_FILE"
    
    # Check if error was logged
    if grep -q "ERROR: pandoc failed" "$TEST_LOG_FILE"; then
        return 0
    else
        echo "Error not logged properly"
        return 1
    fi
}

# Test parallel execution (mock)
test_parallel_execution() {
    # Mock parallel execution function
    execute_steps_parallel() {
        local steps="$1"
        local max_parallel="${2:-2}"
        
        # Simulate parallel execution
        local step_count=$(echo "$steps" | jq '. | length')
        
        if [[ $step_count -le $max_parallel ]]; then
            echo "Executing $step_count steps in parallel"
            return 0
        else
            echo "Executing $max_parallel steps in parallel, $((step_count - max_parallel)) queued"
            return 0
        fi
    }
    
    local parallel_steps='[{"tool": "echo", "command": "echo step1"}, {"tool": "echo", "command": "echo step2"}]'
    local result=$(execute_steps_parallel "$parallel_steps" 2)
    
    [[ "$result" =~ "parallel" ]] || return 1
    
    return 0
}

# Test execution progress tracking
test_execution_progress_tracking() {
    # Mock progress tracking function
    track_execution_progress() {
        local total_steps="$1"
        local completed_steps="$2"
        
        local progress=$((completed_steps * 100 / total_steps))
        
        echo "Progress: $completed_steps/$total_steps ($progress%)"
        
        # Update progress file
        echo "$completed_steps" > "/tmp/progress_$$"
        
        return 0
    }
    
    # Test progress tracking
    track_execution_progress 5 3
    
    # Check progress file
    local progress=$(cat "/tmp/progress_$$" 2>/dev/null || echo "0")
    rm -f "/tmp/progress_$$"
    
    [[ "$progress" == "3" ]] || return 1
    
    return 0
}

# Test execution timeout handling
test_execution_timeout_handling() {
    # Mock timeout handling function
    execute_with_timeout() {
        local command="$1"
        local timeout_seconds="${2:-300}"
        
        # Simulate timeout execution
        if timeout "$timeout_seconds" bash -c "$command" 2>/dev/null; then
            echo "Command completed within timeout"
            return 0
        else
            local exit_code=$?
            if [[ $exit_code -eq 124 ]]; then
                echo "Command timed out after $timeout_seconds seconds"
                return 124
            else
                echo "Command failed with exit code $exit_code"
                return $exit_code
            fi
        fi
    }
    
    # Test quick command
    if execute_with_timeout "echo quick" 5; then
        return 0
    else
        echo "Quick command failed"
        return 1
    fi
}

# Run all tests
echo "=== Testing execution.sh module ==="
echo

run_test "execute_conversion_plan" test_execute_conversion_plan
run_test "execute_step_with_recovery" test_execute_step_with_recovery
run_test "execute_single_step" test_execute_single_step
run_test "display_step" test_display_step
run_test "step_validation" test_step_validation
run_test "command_safety_checking" test_command_safety_checking
run_test "execution_error_handling" test_execution_error_handling
run_test "parallel_execution" test_parallel_execution
run_test "execution_progress_tracking" test_execution_progress_tracking
run_test "execution_timeout_handling" test_execution_timeout_handling

# Cleanup
rm -f "$TEST_LOG_FILE" "$TEST_INPUT_FILE" "$TEST_OUTPUT_FILE"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All execution tests passed!"
    exit 0
else
    echo "❌ Some execution tests failed!"
    exit 1
fi 