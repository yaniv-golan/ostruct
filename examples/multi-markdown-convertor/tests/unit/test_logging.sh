#!/bin/bash
# Unit tests for logging.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_VERBOSE=false
TEST_DEBUG=false

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE="$TEST_VERBOSE"
export DEBUG="$TEST_DEBUG"

# Source the logging module
source "$PROJECT_ROOT/lib/logging.sh"

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Test helper functions
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "Running test: $test_name"
    
    # Clean up log file before each test
    > "$TEST_LOG_FILE"
    
    if $test_function; then
        echo "✅ PASSED: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAILED: $test_name"
        return 1
    fi
}

# Test log function
test_log() {
    local test_message="Test log message"
    local output
    
    # Capture stderr output
    output=$(log "$test_message" 2>&1)
    
    # Check if message appears in output
    if [[ "$output" =~ "$test_message" ]]; then
        # Check if message was written to log file
        if grep -q "$test_message" "$TEST_LOG_FILE"; then
            return 0
        else
            echo "Message not found in log file"
            return 1
        fi
    else
        echo "Message not found in output"
        return 1
    fi
}

# Test log_section function
test_log_section() {
    local section_title="Test Section"
    local output
    
    output=$(log_section "$section_title" 2>&1)
    
    # Check if section formatting is correct
    if [[ "$output" =~ "=== $section_title ===" ]]; then
        return 0
    else
        echo "Section formatting incorrect"
        return 1
    fi
}

# Test log_debug with DEBUG=false
test_log_debug_disabled() {
    export DEBUG=false
    local debug_message="Debug message"
    local output
    
    output=$(log_debug "$debug_message" 2>&1)
    
    # Should produce no output when DEBUG=false
    if [[ -z "$output" ]]; then
        return 0
    else
        echo "Debug message appeared when DEBUG=false"
        return 1
    fi
}

# Test log_debug with DEBUG=true
test_log_debug_enabled() {
    export DEBUG=true
    local debug_message="Debug message"
    local output
    
    output=$(log_debug "$debug_message" 2>&1)
    
    # Should contain DEBUG prefix and message
    if [[ "$output" =~ "DEBUG: $debug_message" ]]; then
        return 0
    else
        echo "Debug message format incorrect"
        return 1
    fi
}

# Test error_exit function (in subshell to avoid exiting test)
test_error_exit() {
    local error_message="Test error"
    local exit_code=42
    local result
    
    # Run in subshell to capture exit
    (error_exit "$error_message" $exit_code) 2>/dev/null
    result=$?
    
    # Should exit with specified code
    if [[ $result -eq $exit_code ]]; then
        return 0
    else
        echo "Exit code incorrect: expected $exit_code, got $result"
        return 1
    fi
}

# Test timestamp format in log
test_log_timestamp() {
    local test_message="Timestamp test"
    local output
    
    output=$(log "$test_message" 2>&1)
    
    # Check for timestamp format [YYYY-MM-DD HH:MM:SS]
    if [[ "$output" =~ \[[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}\] ]]; then
        return 0
    else
        echo "Timestamp format incorrect"
        return 1
    fi
}

# Test verbose mode
test_verbose_mode() {
    export VERBOSE=true
    local test_message="Verbose test"
    local output
    
    output=$(log "$test_message" 2>&1)
    
    # In verbose mode, message should appear in stderr
    if [[ "$output" =~ "$test_message" ]]; then
        return 0
    else
        echo "Verbose output not working"
        return 1
    fi
}

# Run all tests
echo "=== Testing logging.sh module ==="
echo

run_test "log function basic functionality" test_log
run_test "log_section formatting" test_log_section
run_test "log_debug disabled" test_log_debug_disabled
run_test "log_debug enabled" test_log_debug_enabled
run_test "error_exit function" test_error_exit
run_test "log timestamp format" test_log_timestamp
run_test "verbose mode" test_verbose_mode

# Cleanup
rm -f "$TEST_LOG_FILE"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All logging tests passed!"
    exit 0
else
    echo "❌ Some logging tests failed!"
    exit 1
fi
