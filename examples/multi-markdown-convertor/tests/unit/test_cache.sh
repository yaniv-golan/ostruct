#!/bin/bash
# Unit tests for cache.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_CACHE_DIR="/tmp/test_cache_$$"
TEST_INPUT_FILE="/tmp/test_input_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export CACHE_DIR="$TEST_CACHE_DIR"
export VERBOSE=false
export DEBUG=false
export ENABLE_CACHING=true

# Create test directories and files
mkdir -p "$TEST_CACHE_DIR"
echo "test content" > "$TEST_INPUT_FILE"

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/cache.sh"

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
    rm -f "$TEST_CACHE_DIR"/*
    
    if $test_function; then
        echo "✅ PASSED: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAILED: $test_name"
        return 1
    fi
}

# Test get_cache_key function
test_get_cache_key() {
    local cache_key
    
    # Get cache key for test file
    cache_key=$(get_cache_key "$TEST_INPUT_FILE")
    
    # Should return a non-empty string
    [[ -n "$cache_key" ]] || return 1
    
    # Should be consistent (same file = same key)
    local cache_key2=$(get_cache_key "$TEST_INPUT_FILE")
    [[ "$cache_key" == "$cache_key2" ]] || return 1
    
    # Should be different for different files
    echo "different content" > "/tmp/test_input2_$$"
    local cache_key3=$(get_cache_key "/tmp/test_input2_$$")
    [[ "$cache_key" != "$cache_key3" ]] || {
        rm -f "/tmp/test_input2_$$"
        return 1
    }
    
    rm -f "/tmp/test_input2_$$"
    return 0
}

# Test get_cache_key with non-existent file
test_get_cache_key_nonexistent() {
    local cache_key
    
    # Should handle non-existent file gracefully
    cache_key=$(get_cache_key "/nonexistent/file")
    
    # Should return "nocache" for non-existent files
    [[ "$cache_key" == "nocache" ]] || return 1
    return 0
}

# Test validate_cache_entry with valid cache
test_validate_cache_entry_valid() {
    local cache_file="$TEST_CACHE_DIR/test_cache.json"
    
    # Create a valid cache file newer than source
    echo '{"test": "data"}' > "$cache_file"
    sleep 1  # Ensure cache is newer
    touch "$TEST_INPUT_FILE"
    
    # Should validate successfully
    if validate_cache_entry "$cache_file" "$TEST_INPUT_FILE"; then
        return 0
    else
        echo "Valid cache entry failed validation"
        return 1
    fi
}

# Test validate_cache_entry with non-existent cache
test_validate_cache_entry_nonexistent() {
    local cache_file="$TEST_CACHE_DIR/nonexistent_cache.json"
    
    # Should fail validation for non-existent cache
    if validate_cache_entry "$cache_file" "$TEST_INPUT_FILE"; then
        echo "Non-existent cache passed validation"
        return 1
    else
        return 0
    fi
}

# Test validate_cache_entry with expired cache
test_validate_cache_entry_expired() {
    local cache_file="$TEST_CACHE_DIR/expired_cache.json"
    
    # Create cache file
    echo '{"test": "data"}' > "$cache_file"
    sleep 1
    # Update source file to be newer
    touch "$TEST_INPUT_FILE"
    
    # Should fail validation for expired cache
    if validate_cache_entry "$cache_file" "$TEST_INPUT_FILE"; then
        echo "Expired cache passed validation"
        return 1
    else
        return 0
    fi
}

# Test validate_cache_entry with corrupted JSON
test_validate_cache_entry_corrupted() {
    local cache_file="$TEST_CACHE_DIR/corrupted_analysis.json"
    
    # Create corrupted JSON cache
    echo 'invalid json{' > "$cache_file"
    
    # Should fail validation and remove corrupted cache
    if validate_cache_entry "$cache_file" "$TEST_INPUT_FILE"; then
        echo "Corrupted cache passed validation"
        return 1
    else
        # Cache file should be removed
        if [[ -f "$cache_file" ]]; then
            echo "Corrupted cache file not removed"
            return 1
        else
            return 0
        fi
    fi
}

# Test store_cached_analysis and get_cached_analysis
test_store_and_get_cached_analysis() {
    local test_analysis='{"type": "analysis", "content": "test analysis data"}'
    
    # Store analysis
    store_cached_analysis "$TEST_INPUT_FILE" "$test_analysis"
    
    # Retrieve analysis
    local retrieved_analysis
    retrieved_analysis=$(get_cached_analysis "$TEST_INPUT_FILE")
    local exit_code=$?
    
    # Should succeed
    [[ $exit_code -eq 0 ]] || return 1
    
    # Should match stored data
    [[ "$retrieved_analysis" == "$test_analysis" ]] || return 1
    
    return 0
}

# Test get_cached_analysis with no cache
test_get_cached_analysis_no_cache() {
    # Try to get analysis for file with no cache
    get_cached_analysis "$TEST_INPUT_FILE" >/dev/null 2>&1
    local exit_code=$?
    
    # Should fail (return 1)
    [[ $exit_code -eq 1 ]] || return 1
    return 0
}

# Test caching disabled
test_caching_disabled() {
    export ENABLE_CACHING=false
    local test_analysis='{"type": "analysis", "disabled": true}'
    
    # Store analysis (should not create cache file)
    store_cached_analysis "$TEST_INPUT_FILE" "$test_analysis"
    
    # Try to retrieve (should fail)
    get_cached_analysis "$TEST_INPUT_FILE" >/dev/null 2>&1
    local exit_code=$?
    
    # Should fail since caching is disabled
    [[ $exit_code -eq 1 ]] || return 1
    return 0
}

# Test generic cache functions
test_generic_cache_functions() {
    export ENABLE_CACHING=true
    local cache_type="test_type"
    local cache_key="test_key"
    local test_data='{"generic": "cache test"}'
    
    # Store generic data
    store_cached_data "$cache_type" "$cache_key" "$test_data"
    
    # Retrieve generic data
    local retrieved_data
    retrieved_data=$(get_cached_data "$cache_type" "$cache_key")
    local exit_code=$?
    
    # Should succeed
    [[ $exit_code -eq 0 ]] || return 1
    
    # Should match stored data
    [[ "$retrieved_data" == "$test_data" ]] || return 1
    
    return 0
}

# Test generic cache with non-existent data
test_generic_cache_nonexistent() {
    # Try to get non-existent cached data
    get_cached_data "nonexistent_type" "nonexistent_key" >/dev/null 2>&1
    local exit_code=$?
    
    # Should fail
    [[ $exit_code -eq 1 ]] || return 1
    return 0
}

# Test cache key consistency
test_cache_key_consistency() {
    # Create two identical files
    echo "identical content" > "/tmp/file1_$$"
    echo "identical content" > "/tmp/file2_$$"
    
    # Should have same cache key
    local key1=$(get_cache_key "/tmp/file1_$$")
    local key2=$(get_cache_key "/tmp/file2_$$")
    
    # Cleanup
    rm -f "/tmp/file1_$$" "/tmp/file2_$$"
    
    [[ "$key1" == "$key2" ]] || return 1
    return 0
}

# Test cache file naming
test_cache_file_naming() {
    local test_analysis='{"naming": "test"}'
    
    # Store analysis
    store_cached_analysis "$TEST_INPUT_FILE" "$test_analysis"
    
    # Check if cache file was created with correct naming
    local cache_key=$(get_cache_key "$TEST_INPUT_FILE")
    local expected_cache_file="$TEST_CACHE_DIR/analysis_${cache_key}.json"
    
    [[ -f "$expected_cache_file" ]] || return 1
    
    # Check content
    local content=$(cat "$expected_cache_file")
    [[ "$content" == "$test_analysis" ]] || return 1
    
    return 0
}

# Run all tests
echo "=== Testing cache.sh module ==="
echo

run_test "get_cache_key basic functionality" test_get_cache_key
run_test "get_cache_key with nonexistent file" test_get_cache_key_nonexistent
run_test "validate_cache_entry valid cache" test_validate_cache_entry_valid
run_test "validate_cache_entry nonexistent cache" test_validate_cache_entry_nonexistent
run_test "validate_cache_entry expired cache" test_validate_cache_entry_expired
run_test "validate_cache_entry corrupted JSON" test_validate_cache_entry_corrupted
run_test "store and get cached analysis" test_store_and_get_cached_analysis
run_test "get_cached_analysis no cache" test_get_cached_analysis_no_cache
run_test "caching disabled" test_caching_disabled
run_test "generic cache functions" test_generic_cache_functions
run_test "generic cache nonexistent" test_generic_cache_nonexistent
run_test "cache key consistency" test_cache_key_consistency
run_test "cache file naming" test_cache_file_naming

# Cleanup
rm -f "$TEST_LOG_FILE" "$TEST_INPUT_FILE"
rm -rf "$TEST_CACHE_DIR"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All cache tests passed!"
    exit 0
else
    echo "❌ Some cache tests failed!"
    exit 1
fi 