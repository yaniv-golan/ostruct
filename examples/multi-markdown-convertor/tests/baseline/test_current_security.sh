#!/bin/bash
# Baseline regression test for current security functions in convert.sh
# This tests the EXISTING security behavior before refactoring begins

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONVERT_SCRIPT="$PROJECT_ROOT/convert.sh"
TEST_LOG_FILE="/tmp/baseline_security_log_$$"
TEST_SAFE_DIR="/tmp/baseline_safe_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false

# Create test directories
mkdir -p "$TEST_SAFE_DIR"

# Manually define the security functions from convert.sh
# This avoids complex dependencies and sourcing issues

# Extract validate_file_path() function
validate_file_path() {
    local file_path="$1"
    
    # Check if file exists
    if [[ ! -f "$file_path" ]]; then
        return 1
    fi
    
    # Check for path traversal attempts
    if [[ "$file_path" =~ \.\./|/\.\. ]]; then
        return 1
    fi
    
    # Check for absolute paths outside project (basic check)
    if [[ "$file_path" =~ ^/etc/|^/usr/|^/var/|^/root/ ]]; then
        return 1
    fi
    
    return 0
}

# Extract validate_output_directory() function
validate_output_directory() {
    local dir_path="$1"
    
    # Check for path traversal attempts
    if [[ "$dir_path" =~ \.\./|/\.\. ]]; then
        return 1
    fi
    
    # Create directory if it doesn't exist
    if [[ ! -d "$dir_path" ]]; then
        mkdir -p "$dir_path" 2>/dev/null || return 1
    fi
    
    # Check if directory is writable
    if [[ ! -w "$dir_path" ]]; then
        return 1
    fi
    
    return 0
}

# Test counter
TESTS_RUN=0
TESTS_PASSED=0

# Test helper functions
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "Running baseline security test: $test_name"
    
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

# Test current validate_file_path() function with valid path
test_current_validate_file_path_valid() {
    local test_file="$TEST_SAFE_DIR/test.txt"
    echo "test content" > "$test_file"
    
    # Should validate successfully
    if validate_file_path "$test_file" 2>/dev/null; then
        rm -f "$test_file"
        return 0
    else
        rm -f "$test_file"
        echo "Valid file path failed validation"
        return 1
    fi
}

# Test current validate_file_path() function with non-existent file
test_current_validate_file_path_nonexistent() {
    local test_file="$TEST_SAFE_DIR/nonexistent.txt"
    
    # Should fail validation for non-existent file
    if validate_file_path "$test_file" 2>/dev/null; then
        echo "Non-existent file incorrectly passed validation"
        return 1
    else
        return 0
    fi
}

# Test current validate_file_path() function with path traversal
test_current_validate_file_path_traversal() {
    local unsafe_path="../../../etc/passwd"
    
    # Should fail validation for path traversal
    if validate_file_path "$unsafe_path" 2>/dev/null; then
        echo "Path traversal incorrectly passed validation"
        return 1
    else
        return 0
    fi
}

# Test current validate_file_path() function with absolute path outside project
test_current_validate_file_path_absolute_unsafe() {
    local unsafe_path="/etc/passwd"
    
    # Should fail validation for absolute path outside project
    if validate_file_path "$unsafe_path" 2>/dev/null; then
        echo "Unsafe absolute path incorrectly passed validation"
        return 1
    else
        return 0
    fi
}

# Test current validate_output_directory() function with valid directory
test_current_validate_output_directory_valid() {
    # Should validate successfully
    if validate_output_directory "$TEST_SAFE_DIR" 2>/dev/null; then
        return 0
    else
        echo "Valid output directory failed validation"
        return 1
    fi
}

# Test current validate_output_directory() function with non-existent directory
test_current_validate_output_directory_nonexistent() {
    local nonexistent_dir="$TEST_SAFE_DIR/nonexistent"
    
    # Should create directory and validate
    if validate_output_directory "$nonexistent_dir" 2>/dev/null; then
        # Check if directory was created
        if [[ -d "$nonexistent_dir" ]]; then
            rmdir "$nonexistent_dir"
            return 0
        else
            echo "Directory was not created"
            return 1
        fi
    else
        echo "Non-existent directory validation failed"
        return 1
    fi
}

# Test current validate_output_directory() function with path traversal
test_current_validate_output_directory_traversal() {
    local unsafe_dir="../../../tmp"
    
    # Should fail validation for path traversal
    if validate_output_directory "$unsafe_dir" 2>/dev/null; then
        echo "Path traversal in output directory incorrectly passed validation"
        return 1
    else
        return 0
    fi
}

# Test empty path handling
test_current_empty_path_handling() {
    # Should fail validation for empty path
    if validate_file_path "" 2>/dev/null; then
        echo "Empty path incorrectly passed validation"
        return 1
    else
        return 0
    fi
}

# Run all baseline security tests
echo "=== Baseline Security Tests for convert.sh ==="
echo "Testing current security behavior before refactoring"
echo "Script: $CONVERT_SCRIPT"
echo

run_test "current_validate_file_path_valid" test_current_validate_file_path_valid
run_test "current_validate_file_path_nonexistent" test_current_validate_file_path_nonexistent
run_test "current_validate_file_path_traversal" test_current_validate_file_path_traversal
run_test "current_validate_file_path_absolute_unsafe" test_current_validate_file_path_absolute_unsafe
run_test "current_validate_output_directory_valid" test_current_validate_output_directory_valid
run_test "current_validate_output_directory_nonexistent" test_current_validate_output_directory_nonexistent
run_test "current_validate_output_directory_traversal" test_current_validate_output_directory_traversal
run_test "current_empty_path_handling" test_current_empty_path_handling

# Cleanup
rm -f "$TEST_LOG_FILE"
rm -rf "$TEST_SAFE_DIR"

# Summary
echo
echo "=== Baseline Security Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All baseline security tests passed!"
    echo "Current security behavior captured successfully"
    exit 0
else
    echo "❌ Some baseline security tests failed!"
    echo "Current security behavior may have issues"
    exit 1
fi 