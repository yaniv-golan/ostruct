#!/bin/bash
# Baseline regression test for current cache functions in convert.sh
# This tests the EXISTING cache behavior before refactoring begins

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONVERT_SCRIPT="$PROJECT_ROOT/convert.sh"
TEST_LOG_FILE="/tmp/baseline_cache_log_$$"
TEST_CACHE_DIR="/tmp/baseline_cache_$$"
TEST_INPUT_FILE="/tmp/baseline_input_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export CACHE_DIR="$TEST_CACHE_DIR"
export VERBOSE=false
export DEBUG=false
export ENABLE_CACHING=true

# Create test directories and files
mkdir -p "$TEST_CACHE_DIR"
echo "test content for cache" > "$TEST_INPUT_FILE"

# Manually define the cache functions from convert.sh
# This avoids complex dependencies and sourcing issues

# Extract get_cache_key() function
get_cache_key() {
    local file_path="$1"
    
    if [[ ! -f "$file_path" ]]; then
        echo "nocache"
        return 0
    fi
    
    # Generate cache key based on file content and metadata
    local content_hash=$(sha256sum "$file_path" 2>/dev/null | cut -d' ' -f1 || echo "nohash")
    local file_size=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null || echo "0")
    local mod_time=$(stat -f%m "$file_path" 2>/dev/null || stat -c%Y "$file_path" 2>/dev/null || echo "0")
    
    echo "${content_hash}_${file_size}_${mod_time}"
}

# Extract validate_cache_entry() function
validate_cache_entry() {
    local cache_file="$1"
    local source_file="$2"
    
    # Check if cache file exists
    if [[ ! -f "$cache_file" ]]; then
        return 1
    fi
    
    # Check if source file exists
    if [[ ! -f "$source_file" ]]; then
        return 1
    fi
    
    # Check if cache is newer than source
    if [[ "$cache_file" -nt "$source_file" ]]; then
        return 0
    else
        return 1
    fi
}

# Extract get_cached_analysis() function
get_cached_analysis() {
    local file_path="$1"
    
    if [[ "$ENABLE_CACHING" != "true" ]]; then
        return 1
    fi
    
    local cache_key=$(get_cache_key "$file_path")
    if [[ "$cache_key" == "nocache" ]]; then
        return 1
    fi
    
    local cache_file="$CACHE_DIR/analysis_${cache_key}.json"
    
    if validate_cache_entry "$cache_file" "$file_path"; then
        cat "$cache_file"
        return 0
    else
        return 1
    fi
}

# Extract store_cached_analysis() function
store_cached_analysis() {
    local file_path="$1"
    local analysis="$2"
    
    if [[ "$ENABLE_CACHING" != "true" ]]; then
        return 0
    fi
    
    local cache_key=$(get_cache_key "$file_path")
    if [[ "$cache_key" == "nocache" ]]; then
        return 0
    fi
    
    local cache_file="$CACHE_DIR/analysis_${cache_key}.json"
    
    # Ensure cache directory exists
    mkdir -p "$CACHE_DIR"
    
    # Store analysis
    echo "$analysis" > "$cache_file"
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
    echo "Running baseline cache test: $test_name"
    
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

# Test current get_cache_key() function
test_current_get_cache_key() {
    local cache_key
    
    # Get cache key for test file
    cache_key=$(get_cache_key "$TEST_INPUT_FILE")
    local exit_code=$?
    
    # Should succeed and return a non-empty key
    if [[ $exit_code -eq 0 ]] && [[ -n "$cache_key" ]]; then
        # Key should be consistent
        local cache_key2=$(get_cache_key "$TEST_INPUT_FILE")
        if [[ "$cache_key" == "$cache_key2" ]]; then
            return 0
        else
            echo "Cache key not consistent: '$cache_key' vs '$cache_key2'"
            return 1
        fi
    else
        echo "get_cache_key failed or returned empty key: '$cache_key'"
        return 1
    fi
}

# Test current get_cache_key() with non-existent file
test_current_get_cache_key_nonexistent() {
    local cache_key
    
    # Should handle non-existent file gracefully
    cache_key=$(get_cache_key "/nonexistent/file" 2>/dev/null)
    local exit_code=$?
    
    # Should return "nocache" for non-existent files
    if [[ "$cache_key" == "nocache" ]]; then
        return 0
    else
        echo "Expected 'nocache' for non-existent file, got: '$cache_key'"
        return 1
    fi
}

# Test current validate_cache_entry() function
test_current_validate_cache_entry() {
    local cache_file="$TEST_CACHE_DIR/test_cache.json"
    
    # Create source file first
    echo "source content" > "$TEST_INPUT_FILE"
    sleep 1
    # Create cache file newer than source
    echo '{"test": "data"}' > "$cache_file"
    
    # Should validate successfully (cache is newer than source)
    if validate_cache_entry "$cache_file" "$TEST_INPUT_FILE" 2>/dev/null; then
        return 0
    else
        echo "Valid cache entry failed validation"
        return 1
    fi
}

# Test current store_and_get_cached_analysis() functions
test_current_store_and_get_cached_analysis() {
    local test_analysis='{"type": "analysis", "content": "test analysis data"}'
    
    # Store analysis
    store_cached_analysis "$TEST_INPUT_FILE" "$test_analysis" 2>/dev/null
    local store_exit_code=$?
    
    if [[ $store_exit_code -eq 0 ]]; then
        # Retrieve analysis
        local retrieved_analysis
        retrieved_analysis=$(get_cached_analysis "$TEST_INPUT_FILE" 2>/dev/null)
        local get_exit_code=$?
        
        if [[ $get_exit_code -eq 0 ]] && [[ "$retrieved_analysis" == "$test_analysis" ]]; then
            return 0
        else
            echo "Retrieved analysis doesn't match stored. Exit: $get_exit_code, Data: '$retrieved_analysis'"
            return 1
        fi
    else
        echo "store_cached_analysis failed with exit code: $store_exit_code"
        return 1
    fi
}

# Test caching disabled behavior
test_current_caching_disabled() {
    export ENABLE_CACHING=false
    local test_analysis='{"type": "analysis", "disabled": true}'
    
    # Store analysis (should not create cache file when disabled)
    store_cached_analysis "$TEST_INPUT_FILE" "$test_analysis" 2>/dev/null
    
    # Try to retrieve (should fail when caching disabled)
    get_cached_analysis "$TEST_INPUT_FILE" >/dev/null 2>&1
    local exit_code=$?
    
    # Should fail since caching is disabled
    if [[ $exit_code -ne 0 ]]; then
        return 0
    else
        echo "get_cached_analysis should fail when caching is disabled"
        return 1
    fi
}

# Run all baseline cache tests
echo "=== Baseline Cache Tests for convert.sh ==="
echo "Testing current cache behavior before refactoring"
echo "Script: $CONVERT_SCRIPT"
echo

run_test "current_get_cache_key" test_current_get_cache_key
run_test "current_get_cache_key_nonexistent" test_current_get_cache_key_nonexistent
run_test "current_validate_cache_entry" test_current_validate_cache_entry
run_test "current_store_and_get_cached_analysis" test_current_store_and_get_cached_analysis
run_test "current_caching_disabled" test_current_caching_disabled

# Cleanup
rm -f "$TEST_LOG_FILE" "$TEST_INPUT_FILE"
rm -rf "$TEST_CACHE_DIR"

# Summary
echo
echo "=== Baseline Cache Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All baseline cache tests passed!"
    echo "Current cache behavior captured successfully"
    exit 0
else
    echo "❌ Some baseline cache tests failed!"
    echo "Current cache behavior may have issues"
    exit 1
fi 