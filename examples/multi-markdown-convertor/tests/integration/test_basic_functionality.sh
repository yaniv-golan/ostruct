#!/bin/bash
# Integration tests for basic convert.sh functionality

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONVERT_SCRIPT="$PROJECT_ROOT/convert_new.sh"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_INPUT_FILE="/tmp/test_input_$$"
TEST_OUTPUT_FILE="/tmp/test_output_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false

# Create test input file
cat > "$TEST_INPUT_FILE" << 'EOF'
# Test Document

This is a test document for integration testing.

## Section 1

Some content here.

## Section 2

More content here.

- List item 1
- List item 2
- List item 3

### Subsection

Final content.
EOF

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Test helper functions
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "Running integration test: $test_name"
    
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

# Test script existence and executability
test_script_exists() {
    if [[ -f "$CONVERT_SCRIPT" ]]; then
        if [[ -x "$CONVERT_SCRIPT" ]]; then
            echo "Convert script exists and is executable"
            return 0
        else
            echo "Convert script exists but is not executable"
            return 1
        fi
    else
        echo "Convert script does not exist at: $CONVERT_SCRIPT"
        return 1
    fi
}

# Test help display
test_help_display() {
    local help_output
    
    # Test --help flag
    if help_output=$(bash "$CONVERT_SCRIPT" --help 2>&1); then
        if [[ "$help_output" =~ "USAGE:" ]] && [[ "$help_output" =~ "convert_new.sh" ]]; then
            echo "Help display working correctly"
            return 0
        else
            echo "Help output format incorrect"
            return 1
        fi
    else
        echo "Help command failed"
        return 1
    fi
}

# Test version display
test_version_display() {
    local version_output
    
    # Test --version flag
    if version_output=$(bash "$CONVERT_SCRIPT" --version 2>&1); then
        if [[ "$version_output" =~ "convert.sh" ]] && [[ "$version_output" =~ "version" ]]; then
            echo "Version display working correctly"
            return 0
        else
            echo "Version output format incorrect"
            return 1
        fi
    else
        echo "Version command failed"
        return 1
    fi
}

# Test tool checking functionality
test_tool_checking() {
    local check_output
    
    # Test --check-tools flag
    if check_output=$(bash "$CONVERT_SCRIPT" --check-tools 2>&1); then
        if [[ "$check_output" =~ "Checking" ]] || [[ "$check_output" =~ "Tools" ]] || [[ "$check_output" =~ "Tool Availability Check" ]]; then
            echo "Tool checking working correctly"
            return 0
        else
            echo "Tool checking output unexpected: $check_output"
            return 1
        fi
    else
        echo "Tool checking command failed"
        return 1
    fi
}

# Test dry run mode
test_dry_run_mode() {
    local dry_run_output
    
    # Test --dry-run flag with input file
    if dry_run_output=$(bash "$CONVERT_SCRIPT" --dry-run "$TEST_INPUT_FILE" "$TEST_OUTPUT_FILE" 2>&1); then
        if [[ "$dry_run_output" =~ "Dry run" ]] || [[ "$dry_run_output" =~ "would" ]]; then
            echo "Dry run mode working correctly"
            # Ensure no output file was created in dry run
            if [[ ! -f "$TEST_OUTPUT_FILE" ]]; then
                return 0
            else
                echo "Dry run created output file (should not happen)"
                return 1
            fi
        else
            echo "Dry run output unexpected: $dry_run_output"
            return 1
        fi
    else
        echo "Dry run command failed"
        return 1
    fi
}

# Test invalid arguments handling
test_invalid_arguments() {
    local error_output
    
    # Test with invalid flag
    if error_output=$(bash "$CONVERT_SCRIPT" --invalid-flag 2>&1); then
        local exit_code=$?
        if [[ $exit_code -ne 0 ]]; then
            echo "Invalid arguments correctly rejected"
            return 0
        else
            echo "Invalid arguments not rejected (exit code: $exit_code)"
            return 1
        fi
    else
        echo "Invalid arguments test failed unexpectedly"
        return 1
    fi
}

# Test missing input file handling
test_missing_input_file() {
    local error_output
    
    # Test with non-existent input file
    if error_output=$(bash "$CONVERT_SCRIPT" "/nonexistent/file.txt" "$TEST_OUTPUT_FILE" 2>&1); then
        local exit_code=$?
        if [[ $exit_code -ne 0 ]]; then
            echo "Missing input file correctly handled"
            return 0
        else
            echo "Missing input file not handled (exit code: $exit_code)"
            return 1
        fi
    else
        echo "Missing input file test failed unexpectedly"
        return 1
    fi
}

# Test configuration loading
test_configuration_loading() {
    local config_output
    
    # Test configuration validation (should not fail)
    if config_output=$(bash "$CONVERT_SCRIPT" --check-config 2>&1); then
        echo "Configuration loading working correctly"
        return 0
    else
        local exit_code=$?
        echo "Configuration loading failed (exit code: $exit_code)"
        echo "Output: $config_output"
        return 1
    fi
}

# Test logging functionality
test_logging_functionality() {
    local test_log="/tmp/integration_test_log_$$"
    
    # Run command with custom log file
    export LOG_FILE="$test_log"
    
    if bash "$CONVERT_SCRIPT" --help >/dev/null 2>&1; then
        # Check if log file was created and contains entries
        if [[ -f "$test_log" ]] && [[ -s "$test_log" ]]; then
            echo "Logging functionality working correctly"
            rm -f "$test_log"
            return 0
        else
            echo "Log file not created or empty"
            rm -f "$test_log"
            return 1
        fi
    else
        echo "Command failed during logging test"
        rm -f "$test_log"
        return 1
    fi
}

# Test verbose mode
test_verbose_mode() {
    local verbose_output
    
    # Test --verbose flag
    if verbose_output=$(bash "$CONVERT_SCRIPT" --verbose --help 2>&1); then
        # Verbose mode should produce more output
        local line_count=$(echo "$verbose_output" | wc -l)
        if [[ $line_count -gt 5 ]]; then
            echo "Verbose mode working correctly"
            return 0
        else
            echo "Verbose mode not producing enough output"
            return 1
        fi
    else
        echo "Verbose mode test failed"
        return 1
    fi
}

# Test debug mode
test_debug_mode() {
    local debug_output
    
    # Test --debug flag
    if debug_output=$(bash "$CONVERT_SCRIPT" --debug --help 2>&1); then
        # Debug mode should include debug information
        if [[ "$debug_output" =~ "DEBUG" ]] || [[ $(echo "$debug_output" | wc -l) -gt 10 ]]; then
            echo "Debug mode working correctly"
            return 0
        else
            echo "Debug mode not producing debug output"
            return 1
        fi
    else
        echo "Debug mode test failed"
        return 1
    fi
}

# Test basic module loading
test_module_loading() {
    # Test that the script can load its modules without error
    local load_test_script="/tmp/load_test_$$"
    
    cat > "$load_test_script" << 'EOF'
#!/bin/bash
set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Try to source the common module loader
if [[ -f "$PROJECT_ROOT/lib/common.sh" ]]; then
    source "$PROJECT_ROOT/lib/common.sh"
    echo "Module loading successful"
    exit 0
else
    echo "Common module not found"
    exit 1
fi
EOF
    
    chmod +x "$load_test_script"
    
    if bash "$load_test_script"; then
        rm -f "$load_test_script"
        echo "Module loading working correctly"
        return 0
    else
        rm -f "$load_test_script"
        echo "Module loading failed"
        return 1
    fi
}

# Test error handling
test_error_handling() {
    local error_output
    
    # Test with insufficient arguments
    if error_output=$(bash "$CONVERT_SCRIPT" 2>&1); then
        local exit_code=$?
        if [[ $exit_code -ne 0 ]] && [[ "$error_output" =~ "Usage" || "$error_output" =~ "Error" ]]; then
            echo "Error handling working correctly"
            return 0
        else
            echo "Error handling not working (exit code: $exit_code)"
            return 1
        fi
    else
        echo "Error handling test failed unexpectedly"
        return 1
    fi
}

# Test signal handling
test_signal_handling() {
    # Start convert script in background and send SIGTERM
    local test_pid
    
    # Run a long-running command in background
    bash "$CONVERT_SCRIPT" --help >/dev/null 2>&1 &
    test_pid=$!
    
    # Give it a moment to start
    sleep 1
    
    # Send SIGTERM
    if kill -TERM "$test_pid" 2>/dev/null; then
        # Wait for process to exit
        wait "$test_pid" 2>/dev/null || true
        echo "Signal handling working correctly"
        return 0
    else
        echo "Signal handling test failed"
        return 1
    fi
}

# Run all integration tests
echo "=== Integration Tests for convert.sh ==="
echo "Testing script: $CONVERT_SCRIPT"
echo

run_test "script_exists" test_script_exists
run_test "help_display" test_help_display
run_test "version_display" test_version_display
run_test "tool_checking" test_tool_checking
run_test "dry_run_mode" test_dry_run_mode
run_test "invalid_arguments" test_invalid_arguments
run_test "missing_input_file" test_missing_input_file
run_test "configuration_loading" test_configuration_loading
run_test "logging_functionality" test_logging_functionality
run_test "verbose_mode" test_verbose_mode
run_test "debug_mode" test_debug_mode
run_test "module_loading" test_module_loading
run_test "error_handling" test_error_handling
run_test "signal_handling" test_signal_handling

# Cleanup
rm -f "$TEST_LOG_FILE" "$TEST_INPUT_FILE" "$TEST_OUTPUT_FILE"

# Summary
echo
echo "=== Integration Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All integration tests passed!"
    exit 0
else
    echo "❌ Some integration tests failed!"
    exit 1
fi
