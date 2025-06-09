#!/bin/bash
# Unit tests for security.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_TEMP_DIR="/tmp/test_temp_$$"
TEST_OUTPUT_DIR="/tmp/test_output_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false
export TEMP_DIR="$TEST_TEMP_DIR"
export OUTPUT_DIR="$TEST_OUTPUT_DIR"

# Create test directories
mkdir -p "$TEST_TEMP_DIR" "$TEST_OUTPUT_DIR"

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/config.sh"
source "$PROJECT_ROOT/lib/cache.sh"
source "$PROJECT_ROOT/lib/security.sh"

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

# Test validate_file_path with valid project path
test_validate_file_path_valid_project() {
    local test_file="$PROJECT_ROOT/test_file.txt"
    echo "test content" > "$test_file"
    
    # Should pass validation for project files
    if validate_file_path "$test_file"; then
        rm -f "$test_file"
        return 0
    else
        rm -f "$test_file"
        echo "Valid project path failed validation"
        return 1
    fi
}

# Test validate_file_path with valid temp path
test_validate_file_path_valid_temp() {
    local test_file="$TEST_TEMP_DIR/test_file.txt"
    echo "test content" > "$test_file"
    
    # Should pass validation for temp files
    if validate_file_path "$test_file"; then
        return 0
    else
        echo "Valid temp path failed validation"
        return 1
    fi
}

# Test validate_file_path with valid output path
test_validate_file_path_valid_output() {
    local test_file="$TEST_OUTPUT_DIR/test_file.txt"
    echo "test content" > "$test_file"
    
    # Should pass validation for output files
    if validate_file_path "$test_file"; then
        return 0
    else
        echo "Valid output path failed validation"
        return 1
    fi
}

# Test validate_file_path with invalid path
test_validate_file_path_invalid() {
    local test_file="/etc/passwd"
    
    # Should fail validation for system files
    if validate_file_path "$test_file" 2>/dev/null; then
        echo "Invalid path passed validation"
        return 1
    else
        return 0
    fi
}

# Test validate_file_path with non-existent file
test_validate_file_path_nonexistent() {
    local test_file="/nonexistent/path/file.txt"
    
    # Should fail validation for non-existent paths
    if validate_file_path "$test_file" 2>/dev/null; then
        echo "Non-existent path passed validation"
        return 1
    else
        return 0
    fi
}

# Test validate_output_directory with valid directory
test_validate_output_directory_valid() {
    # Should pass for existing output directory
    if validate_output_directory "$TEST_OUTPUT_DIR"; then
        return 0
    else
        echo "Valid output directory failed validation"
        return 1
    fi
}

# Test validate_output_directory with non-existent directory
test_validate_output_directory_nonexistent() {
    local nonexistent_dir="/tmp/nonexistent_output_$$"
    
    # Should create directory if it doesn't exist
    if validate_output_directory "$nonexistent_dir"; then
        # Check if directory was created
        if [[ -d "$nonexistent_dir" ]]; then
            rmdir "$nonexistent_dir"
            return 0
        else
            echo "Directory not created"
            return 1
        fi
    else
        echo "Failed to validate/create output directory"
        return 1
    fi
}

# Test validate_output_directory with invalid permissions
test_validate_output_directory_invalid_permissions() {
    # Try to create directory in read-only location (should fail gracefully)
    if validate_output_directory "/root/test_output" 2>/dev/null; then
        echo "Invalid permissions passed validation"
        return 1
    else
        return 0
    fi
}

# Mock safety_check function for testing (since it requires ostruct)
mock_safety_check() {
    local command="$1"
    local context="$2"
    
    # Simple mock: reject dangerous commands
    case "$command" in
        *"rm -rf /"*|*"format"*|*"delete"*)
            echo "MALICIOUS"
            return 1
            ;;
        *)
            echo "SAFE"
            return 0
            ;;
    esac
}

# Test safety_check with safe command
test_safety_check_safe_command() {
    local safe_command="echo 'hello world'"
    local context="test context"
    
    # Mock the safety check
    local result=$(mock_safety_check "$safe_command" "$context")
    
    if [[ "$result" == "SAFE" ]]; then
        return 0
    else
        echo "Safe command marked as unsafe"
        return 1
    fi
}

# Test safety_check with malicious command
test_safety_check_malicious_command() {
    local malicious_command="rm -rf /"
    local context="test context"
    
    # Mock the safety check
    local result=$(mock_safety_check "$malicious_command" "$context")
    
    if [[ "$result" == "MALICIOUS" ]]; then
        return 0
    else
        echo "Malicious command marked as safe"
        return 1
    fi
}

# Test path traversal prevention
test_path_traversal_prevention() {
    local traversal_path="$PROJECT_ROOT/../../../etc/passwd"
    
    # Should fail validation for path traversal attempts
    if validate_file_path "$traversal_path" 2>/dev/null; then
        echo "Path traversal attempt passed validation"
        return 1
    else
        return 0
    fi
}

# Test symlink handling
test_symlink_handling() {
    local target_file="/etc/passwd"
    local symlink_file="$TEST_TEMP_DIR/symlink_test"
    
    # Create symlink to system file
    ln -s "$target_file" "$symlink_file" 2>/dev/null || {
        echo "Could not create symlink, skipping test"
        return 0
    }
    
    # Should fail validation for symlinks to unauthorized files
    if validate_file_path "$symlink_file" 2>/dev/null; then
        rm -f "$symlink_file"
        echo "Symlink to unauthorized file passed validation"
        return 1
    else
        rm -f "$symlink_file"
        return 0
    fi
}

# Test directory creation with proper permissions
test_directory_creation_permissions() {
    local test_dir="$TEST_OUTPUT_DIR/subdir/nested"
    
    # Should create nested directories
    if validate_output_directory "$test_dir"; then
        # Check if directory exists and has proper permissions
        if [[ -d "$test_dir" ]] && [[ -w "$test_dir" ]]; then
            return 0
        else
            echo "Directory not created with proper permissions"
            return 1
        fi
    else
        echo "Failed to create nested directory"
        return 1
    fi
}

# Test file path normalization
test_file_path_normalization() {
    local unnormalized_path="$PROJECT_ROOT/./test/../test_file.txt"
    echo "test content" > "$PROJECT_ROOT/test_file.txt"
    
    # Should handle path normalization correctly
    if validate_file_path "$unnormalized_path"; then
        rm -f "$PROJECT_ROOT/test_file.txt"
        return 0
    else
        rm -f "$PROJECT_ROOT/test_file.txt"
        echo "Path normalization failed"
        return 1
    fi
}

# Test security logging
test_security_logging() {
    local invalid_path="/etc/passwd"
    
    # Clear log
    > "$TEST_LOG_FILE"
    
    # Try invalid path (should log security violation)
    validate_file_path "$invalid_path" 2>/dev/null
    
    # Check if security violation was logged
    if grep -q "SECURITY:" "$TEST_LOG_FILE"; then
        return 0
    else
        echo "Security violation not logged"
        return 1
    fi
}

# Run all tests
echo "=== Testing security.sh module ==="
echo

run_test "validate_file_path valid project" test_validate_file_path_valid_project
run_test "validate_file_path valid temp" test_validate_file_path_valid_temp
run_test "validate_file_path valid output" test_validate_file_path_valid_output
run_test "validate_file_path invalid" test_validate_file_path_invalid
run_test "validate_file_path nonexistent" test_validate_file_path_nonexistent
run_test "validate_output_directory valid" test_validate_output_directory_valid
run_test "validate_output_directory nonexistent" test_validate_output_directory_nonexistent
run_test "validate_output_directory invalid permissions" test_validate_output_directory_invalid_permissions
run_test "safety_check safe command" test_safety_check_safe_command
run_test "safety_check malicious command" test_safety_check_malicious_command
run_test "path traversal prevention" test_path_traversal_prevention
run_test "symlink handling" test_symlink_handling
run_test "directory creation permissions" test_directory_creation_permissions
run_test "file path normalization" test_file_path_normalization
run_test "security logging" test_security_logging

# Cleanup
rm -f "$TEST_LOG_FILE"
rm -rf "$TEST_TEMP_DIR" "$TEST_OUTPUT_DIR"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All security tests passed!"
    exit 0
else
    echo "❌ Some security tests failed!"
    exit 1
fi 