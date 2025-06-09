#!/bin/bash
# Unit tests for utils.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_PERFORMANCE_LOG="/tmp/test_performance_log_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export PERFORMANCE_LOG_FILE="$TEST_PERFORMANCE_LOG"
export VERBOSE=false
export DEBUG=false
export ENABLE_PERFORMANCE_LOGGING=true

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/utils.sh"

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
    > "$TEST_PERFORMANCE_LOG"
    
    if $test_function; then
        echo "✅ PASSED: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAILED: $test_name"
        return 1
    fi
}

# Test profile_execution with successful command
test_profile_execution_success() {
    local operation="test_operation"
    
    # Run a simple command through profile_execution
    profile_execution "$operation" echo "test command"
    local exit_code=$?
    
    # Check exit code
    [[ $exit_code -eq 0 ]] || return 1
    
    # Check if performance log was created
    [[ -f "$TEST_PERFORMANCE_LOG" ]] || return 1
    
    # Check if log entry contains operation name
    if grep -q "$operation" "$TEST_PERFORMANCE_LOG"; then
        return 0
    else
        echo "Operation not found in performance log"
        return 1
    fi
}

# Test profile_execution with failing command
test_profile_execution_failure() {
    local operation="test_failure"
    
    # Run a failing command through profile_execution
    profile_execution "$operation" false
    local exit_code=$?
    
    # Check exit code (should be 1 from false command)
    [[ $exit_code -eq 1 ]] || return 1
    
    # Check if performance log contains the failure
    if grep -q "$operation" "$TEST_PERFORMANCE_LOG"; then
        # Check if exit code is recorded
        if grep -q ",1$" "$TEST_PERFORMANCE_LOG"; then
            return 0
        else
            echo "Exit code not recorded correctly"
            return 1
        fi
    else
        echo "Failed operation not found in performance log"
        return 1
    fi
}

# Test profile_execution with performance logging disabled
test_profile_execution_disabled() {
    export ENABLE_PERFORMANCE_LOGGING=false
    local operation="test_disabled"
    
    # Clear performance log
    > "$TEST_PERFORMANCE_LOG"
    
    # Run command
    profile_execution "$operation" echo "test"
    
    # Performance log should remain empty
    if [[ -s "$TEST_PERFORMANCE_LOG" ]]; then
        echo "Performance log written when disabled"
        return 1
    else
        return 0
    fi
}

# Test retry_command with successful command
test_retry_command_success() {
    local max_retries=3
    local retry_delay=1
    
    # Command that succeeds immediately
    retry_command $max_retries $retry_delay echo "success"
    local exit_code=$?
    
    [[ $exit_code -eq 0 ]] || return 1
    return 0
}

# Test retry_command with eventually successful command
test_retry_command_eventual_success() {
    local max_retries=3
    local retry_delay=1
    local attempt_file="/tmp/retry_attempt_$$"
    
    # Create a command that fails twice then succeeds
    cat > "/tmp/retry_test_$$" << 'EOF'
#!/bin/bash
attempt_file="$1"
if [[ ! -f "$attempt_file" ]]; then
    echo "1" > "$attempt_file"
    exit 1
elif [[ "$(cat "$attempt_file")" == "1" ]]; then
    echo "2" > "$attempt_file"
    exit 1
else
    exit 0
fi
EOF
    chmod +x "/tmp/retry_test_$$"
    
    # Run with retry
    retry_command $max_retries $retry_delay "/tmp/retry_test_$$" "$attempt_file"
    local exit_code=$?
    
    # Cleanup
    rm -f "/tmp/retry_test_$$" "$attempt_file"
    
    [[ $exit_code -eq 0 ]] || return 1
    return 0
}

# Test retry_command with persistent failure
test_retry_command_persistent_failure() {
    local max_retries=2
    local retry_delay=1
    
    # Command that always fails
    retry_command $max_retries $retry_delay false
    local exit_code=$?
    
    # Should fail after retries
    [[ $exit_code -eq 1 ]] || return 1
    return 0
}

# Test safe_execute with successful command
test_safe_execute_success() {
    local timeout=5
    local output
    
    # Run simple command
    output=$(safe_execute $timeout echo "safe test")
    local exit_code=$?
    
    [[ $exit_code -eq 0 ]] || return 1
    [[ "$output" =~ "safe test" ]] || return 1
    
    return 0
}

# Test safe_execute with timeout
test_safe_execute_timeout() {
    local timeout=2
    
    # Command that should timeout
    safe_execute $timeout sleep 5 >/dev/null 2>&1
    local exit_code=$?
    
    # Should timeout (exit code 124 from timeout command)
    [[ $exit_code -eq 124 ]] || return 1
    return 0
}

# Test safe_execute output logging
test_safe_execute_logging() {
    local timeout=5
    local test_message="logging test message"
    
    # Clear log file
    > "$TEST_LOG_FILE"
    
    # Run command that produces output
    safe_execute $timeout echo "$test_message" >/dev/null
    
    # Check if output was logged
    if grep -q "$test_message" "$TEST_LOG_FILE"; then
        return 0
    else
        echo "Output not found in log file"
        return 1
    fi
}

# Test performance log format
test_performance_log_format() {
    export ENABLE_PERFORMANCE_LOGGING=true
    local operation="format_test"
    
    # Clear performance log
    > "$TEST_PERFORMANCE_LOG"
    
    # Run operation
    profile_execution "$operation" echo "test"
    
    # Check log format: timestamp,operation,duration,exit_code
    local log_line=$(cat "$TEST_PERFORMANCE_LOG")
    
    # Should have 4 comma-separated fields
    local field_count=$(echo "$log_line" | tr ',' '\n' | wc -l)
    [[ $field_count -eq 4 ]] || return 1
    
    # Check if operation name is in the log
    [[ "$log_line" =~ "$operation" ]] || return 1
    
    # Check if exit code is 0
    [[ "$log_line" =~ ",0$" ]] || return 1
    
    return 0
}

# Test retry_command with custom parameters
test_retry_command_custom_params() {
    local max_retries=1
    local retry_delay=1
    
    # Should only try twice (initial + 1 retry)
    local attempt_count=0
    
    # Create a command that counts attempts
    cat > "/tmp/count_test_$$" << 'EOF'
#!/bin/bash
count_file="$1"
if [[ -f "$count_file" ]]; then
    count=$(cat "$count_file")
else
    count=0
fi
count=$((count + 1))
echo "$count" > "$count_file"
exit 1  # Always fail
EOF
    chmod +x "/tmp/count_test_$$"
    
    local count_file="/tmp/count_$$"
    
    # Run with retry (should fail)
    retry_command $max_retries $retry_delay "/tmp/count_test_$$" "$count_file"
    
    # Check attempt count
    local final_count=$(cat "$count_file" 2>/dev/null || echo "0")
    
    # Cleanup
    rm -f "/tmp/count_test_$$" "$count_file"
    
    # Should have tried exactly 2 times (initial + 1 retry)
    [[ "$final_count" == "2" ]] || return 1
    return 0
}

# Run all tests
echo "=== Testing utils.sh module ==="
echo

run_test "profile_execution success" test_profile_execution_success
run_test "profile_execution failure" test_profile_execution_failure
run_test "profile_execution disabled" test_profile_execution_disabled
run_test "retry_command success" test_retry_command_success
run_test "retry_command eventual success" test_retry_command_eventual_success
run_test "retry_command persistent failure" test_retry_command_persistent_failure
run_test "safe_execute success" test_safe_execute_success
run_test "safe_execute timeout" test_safe_execute_timeout
run_test "safe_execute logging" test_safe_execute_logging
run_test "performance log format" test_performance_log_format
run_test "retry_command custom parameters" test_retry_command_custom_params

# Cleanup
rm -f "$TEST_LOG_FILE" "$TEST_PERFORMANCE_LOG"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All utils tests passed!"
    exit 0
else
    echo "❌ Some utils tests failed!"
    exit 1
fi 