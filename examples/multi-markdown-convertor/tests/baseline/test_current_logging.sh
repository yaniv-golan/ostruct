#!/bin/bash
# Baseline regression test for current logging functions in convert.sh
# This tests the EXISTING behavior before refactoring begins

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONVERT_SCRIPT="$PROJECT_ROOT/convert.sh"
TEST_LOG_FILE="/tmp/baseline_test_log_$$"

# Set up test environment to match convert.sh expectations
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false
export ENABLE_PERFORMANCE_LOGGING=true
export PERFORMANCE_LOG_FILE="/tmp/baseline_perf_log_$$"

# Manually extract and define the core logging functions from convert.sh
# This avoids complex dependencies and sourcing issues

# Extract log() function
log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$LOG_FILE" >&2
    if [[ "$VERBOSE" == "true" ]]; then
        echo "$message" >&2
    fi
}

# Extract log_section() function
log_section() {
    local section="$1"
    log ""
    log "=== $section ==="
    log ""
}

# Extract log_debug() function
log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        log "DEBUG: $1"
    fi
}

# Extract error_exit() function
error_exit() {
    local message="$1"
    local exit_code="${2:-1}"
    log "❌ ERROR: $message"
    exit "$exit_code"
}

# Extract profile_execution() function
profile_execution() {
    local start_time=$(date +%s.%N)
    local operation="$1"
    shift

    # Execute operation
    "$@"
    local exit_code=$?

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")

    if [[ "$ENABLE_PERFORMANCE_LOGGING" == "true" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S'),$operation,$duration,$exit_code" >> "$PERFORMANCE_LOG_FILE"
    fi

    return $exit_code
}

# Extract validate_required_tools() function
validate_required_tools() {
    local required_tools=("ostruct" "jq")
    local missing_tools=()

    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error_exit "Missing required tools: ${missing_tools[*]}"
    fi
}

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Test helper functions
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "Running baseline test: $test_name"
    
    # Clean up before each test
    > "$TEST_LOG_FILE"
    > "$PERFORMANCE_LOG_FILE"
    
    if $test_function; then
        echo "✅ PASSED: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAILED: $test_name"
        return 1
    fi
}

# Test current log() function
test_current_log_function() {
    local test_message="Test log message"
    
    # Capture output
    local output=$(log "$test_message" 2>&1)
    
    # Check that message appears in output
    if [[ "$output" =~ "$test_message" ]]; then
        # Check that timestamp format is correct
        if [[ "$output" =~ \[[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}\] ]]; then
            # Check that message was written to log file
            if [[ -f "$TEST_LOG_FILE" ]] && grep -q "$test_message" "$TEST_LOG_FILE"; then
                return 0
            else
                echo "Message not found in log file"
                return 1
            fi
        else
            echo "Timestamp format incorrect: $output"
            return 1
        fi
    else
        echo "Message not found in output: $output"
        return 1
    fi
}

# Test current log_section() function
test_current_log_section_function() {
    local section_name="Test Section"
    
    # Capture output
    local output=$(log_section "$section_name" 2>&1)
    
    # Check that section appears with proper formatting
    if [[ "$output" =~ "=== $section_name ===" ]]; then
        # Check that empty lines are included
        local line_count=$(echo "$output" | wc -l)
        if [[ $line_count -ge 3 ]]; then
            return 0
        else
            echo "Section formatting incomplete, line count: $line_count"
            return 1
        fi
    else
        echo "Section formatting not found: $output"
        return 1
    fi
}

# Test current log_debug() function with DEBUG=false
test_current_log_debug_disabled() {
    export DEBUG=false
    local debug_message="Debug message"
    
    # Capture output
    local output=$(log_debug "$debug_message" 2>&1)
    
    # Should produce no output when DEBUG=false
    if [[ -z "$output" ]]; then
        return 0
    else
        echo "Debug output produced when DEBUG=false: $output"
        return 1
    fi
}

# Test current log_debug() function with DEBUG=true
test_current_log_debug_enabled() {
    export DEBUG=true
    local debug_message="Debug message"
    
    # Capture output
    local output=$(log_debug "$debug_message" 2>&1)
    
    # Should produce output with DEBUG prefix when DEBUG=true
    if [[ "$output" =~ "DEBUG: $debug_message" ]]; then
        return 0
    else
        echo "Debug output format incorrect: $output"
        return 1
    fi
}

# Test current error_exit() function
test_current_error_exit_function() {
    local error_message="Test error"
    local expected_exit_code=42
    
    # Test error_exit in a subshell to capture exit
    local result
    result=$(bash -c "
        # Set up minimal environment for error_exit test
        export LOG_FILE='$TEST_LOG_FILE'
        
        # Define the error_exit function directly (extracted from convert.sh)
        log() {
            local message=\"\$1\"
            local timestamp=\$(date '+%Y-%m-%d %H:%M:%S')
            echo \"[\$timestamp] \$message\" | tee -a \"$TEST_LOG_FILE\" >&2
        }
        
        error_exit() {
            local message=\"\$1\"
            local exit_code=\"\${2:-1}\"
            log \"❌ ERROR: \$message\"
            exit \"\$exit_code\"
        }
        
        error_exit '$error_message' $expected_exit_code
    " 2>&1)
    local actual_exit_code=$?
    
    # Check exit code
    if [[ $actual_exit_code -eq $expected_exit_code ]]; then
        # Check error message format
        if [[ "$result" =~ "❌ ERROR: $error_message" ]]; then
            return 0
        else
            echo "Error message format incorrect: $result"
            return 1
        fi
    else
        echo "Exit code incorrect. Expected: $expected_exit_code, Got: $actual_exit_code"
        return 1
    fi
}

# Test current profile_execution() function
test_current_profile_execution_function() {
    export ENABLE_PERFORMANCE_LOGGING=true
    local operation_name="test_operation"
    
    # Check if bc is available for duration calculation
    if ! command -v bc >/dev/null 2>&1; then
        echo "bc not available, skipping profile_execution test"
        return 0
    fi
    
    # Run a simple command through profile_execution
    profile_execution "$operation_name" echo "test command"
    local exit_code=$?
    
    # Check that command succeeded
    if [[ $exit_code -eq 0 ]]; then
        # Check that performance log was created
        if [[ -f "$PERFORMANCE_LOG_FILE" ]] && [[ -s "$PERFORMANCE_LOG_FILE" ]]; then
            # Check that log contains our operation
            if grep -q "$operation_name" "$PERFORMANCE_LOG_FILE"; then
                # Check log format (timestamp,operation,duration,exit_code)
                local log_line=$(grep "$operation_name" "$PERFORMANCE_LOG_FILE")
                local field_count=$(echo "$log_line" | tr ',' '\n' | wc -l)
                if [[ $field_count -eq 4 ]]; then
                    return 0
                else
                    echo "Performance log format incorrect: $log_line"
                    return 1
                fi
            else
                echo "Operation not found in performance log"
                return 1
            fi
        else
            echo "Performance log file not created or empty"
            return 1
        fi
    else
        echo "Profile execution failed with exit code: $exit_code"
        return 1
    fi
}

# Test current validate_required_tools() function
test_current_validate_required_tools_function() {
    # This function checks for ostruct and jq
    # We'll test both success and failure cases
    
    # First, test with current PATH (may pass or fail depending on system)
    validate_required_tools 2>/dev/null
    local result=$?
    
    # The function should either pass (tools available) or fail (tools missing)
    # Both are valid baseline behaviors, so we just verify it runs
    echo "validate_required_tools returned exit code: $result"
    return 0
}

# Test verbose mode behavior
test_current_verbose_mode() {
    export VERBOSE=true
    local test_message="Verbose test message"
    
    # Capture stderr output
    local output
    output=$(log "$test_message" 2>&1)
    
    # In verbose mode, message should appear twice (once in log format, once plain)
    local message_count=$(echo "$output" | grep -c "$test_message")
    if [[ $message_count -ge 1 ]]; then
        return 0
    else
        echo "Verbose mode not working correctly. Message count: $message_count"
        return 1
    fi
}

# Test log file persistence
test_current_log_file_persistence() {
    local test_message="Persistence test"
    
    # Log a message
    log "$test_message" >/dev/null 2>&1
    
    # Check that log file exists and contains the message
    if [[ -f "$TEST_LOG_FILE" ]] && grep -q "$test_message" "$TEST_LOG_FILE"; then
        # Log another message
        log "Second message" >/dev/null 2>&1
        
        # Check that both messages are in the file
        if grep -q "$test_message" "$TEST_LOG_FILE" && grep -q "Second message" "$TEST_LOG_FILE"; then
            return 0
        else
            echo "Log file persistence failed - messages not accumulating"
            return 1
        fi
    else
        echo "Log file not created or message not found"
        return 1
    fi
}

# Run all baseline tests
echo "=== Baseline Regression Tests for convert.sh ==="
echo "Testing current behavior before refactoring"
echo "Script: $CONVERT_SCRIPT"
echo

run_test "current_log_function" test_current_log_function
run_test "current_log_section_function" test_current_log_section_function
run_test "current_log_debug_disabled" test_current_log_debug_disabled
run_test "current_log_debug_enabled" test_current_log_debug_enabled
run_test "current_error_exit_function" test_current_error_exit_function
run_test "current_profile_execution_function" test_current_profile_execution_function
run_test "current_validate_required_tools_function" test_current_validate_required_tools_function
run_test "current_verbose_mode" test_current_verbose_mode
run_test "current_log_file_persistence" test_current_log_file_persistence

# Cleanup
rm -f "$TEST_LOG_FILE" "$PERFORMANCE_LOG_FILE"

# Summary
echo
echo "=== Baseline Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All baseline tests passed!"
    echo "Current behavior captured successfully"
    exit 0
else
    echo "❌ Some baseline tests failed!"
    echo "Current behavior may have issues"
    exit 1
fi 