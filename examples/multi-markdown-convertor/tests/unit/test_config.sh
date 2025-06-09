#!/bin/bash
# Unit tests for config.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_CONFIG_FILE="/tmp/test_config_$$"
TEST_LOCAL_CONFIG_FILE="/tmp/test_local_config_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/config.sh"

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
    rm -f "$TEST_CONFIG_FILE" "$TEST_LOCAL_CONFIG_FILE"
    
    if $test_function; then
        echo "✅ PASSED: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "❌ FAILED: $test_name"
        return 1
    fi
}

# Test default configuration values
test_default_config_values() {
    # Check that default values are set
    [[ -n "${DEFAULT_MODEL_ANALYSIS:-}" ]] || return 1
    [[ -n "${DEFAULT_MODEL_PLANNING:-}" ]] || return 1
    [[ -n "${DEFAULT_MODEL_SAFETY:-}" ]] || return 1
    [[ -n "${DEFAULT_MODEL_VALIDATION:-}" ]] || return 1
    [[ -n "${DEFAULT_TIMEOUT:-}" ]] || return 1
    [[ -n "${MAX_RETRIES:-}" ]] || return 1
    [[ -n "${MAX_REPLANS:-}" ]] || return 1
    [[ -n "${ENABLE_CACHING:-}" ]] || return 1
    
    # Check specific default values
    [[ "${DEFAULT_MODEL_ANALYSIS}" == "gpt-4o-mini" ]] || return 1
    [[ "${DEFAULT_MODEL_PLANNING}" == "gpt-4o" ]] || return 1
    [[ "${DEFAULT_TIMEOUT}" == "300" ]] || return 1
    [[ "${MAX_RETRIES}" == "2" ]] || return 1
    [[ "${ENABLE_CACHING}" == "true" ]] || return 1
    
    return 0
}

# Test configuration validation with valid config
test_validate_configuration_valid() {
    # Set valid configuration
    export DEFAULT_MODEL_ANALYSIS="gpt-4o-mini"
    export DEFAULT_MODEL_PLANNING="gpt-4o"
    export DEFAULT_TIMEOUT="300"
    export MAX_RETRIES="3"
    export MAX_REPLANS="2"
    export ENABLE_CACHING="true"
    
    # Should pass validation
    if validate_configuration; then
        return 0
    else
        echo "Valid configuration failed validation"
        return 1
    fi
}

# Test configuration validation with invalid timeout
test_validate_configuration_invalid_timeout() {
    # Set invalid timeout
    export DEFAULT_TIMEOUT="not_a_number"
    
    # Should fail validation
    if validate_configuration 2>/dev/null; then
        echo "Invalid timeout passed validation"
        return 1
    else
        return 0
    fi
}

# Test configuration validation with invalid boolean
test_validate_configuration_invalid_boolean() {
    # Set invalid boolean value
    export ENABLE_CACHING="maybe"
    
    # Should fail validation
    if validate_configuration 2>/dev/null; then
        echo "Invalid boolean passed validation"
        return 1
    else
        return 0
    fi
}

# Test configuration validation with missing required field
test_validate_configuration_missing_field() {
    # Unset required field
    unset DEFAULT_MODEL_ANALYSIS
    
    # Should fail validation
    if validate_configuration 2>/dev/null; then
        echo "Missing field passed validation"
        return 1
    else
        return 0
    fi
}

# Test load_configuration with config file
test_load_configuration_with_file() {
    # Create test config file
    cat > "$TEST_CONFIG_FILE" << 'EOF'
DEFAULT_MODEL_ANALYSIS="test-model"
DEFAULT_TIMEOUT="600"
ENABLE_CACHING="false"
EOF
    
    # Load configuration
    load_configuration "$TEST_CONFIG_FILE"
    
    # Check if values were loaded
    [[ "${DEFAULT_MODEL_ANALYSIS}" == "test-model" ]] || return 1
    [[ "${DEFAULT_TIMEOUT}" == "600" ]] || return 1
    [[ "${ENABLE_CACHING}" == "false" ]] || return 1
    
    return 0
}

# Test load_configuration with local override
test_load_configuration_with_local_override() {
    # Create main config file
    cat > "$TEST_CONFIG_FILE" << 'EOF'
DEFAULT_MODEL_ANALYSIS="main-model"
DEFAULT_TIMEOUT="300"
EOF
    
    # Create local config file with override
    cat > "$TEST_LOCAL_CONFIG_FILE" << 'EOF'
DEFAULT_MODEL_ANALYSIS="local-model"
EOF
    
    # Mock PROJECT_ROOT to point to test directory
    local original_project_root="$PROJECT_ROOT"
    export PROJECT_ROOT="$(dirname "$TEST_CONFIG_FILE")"
    
    # Create config directory structure
    mkdir -p "$PROJECT_ROOT/config"
    cp "$TEST_CONFIG_FILE" "$PROJECT_ROOT/config/default.conf"
    cp "$TEST_LOCAL_CONFIG_FILE" "$PROJECT_ROOT/config/local.conf"
    
    # Load configuration
    load_configuration
    
    # Check if local override took effect
    [[ "${DEFAULT_MODEL_ANALYSIS}" == "local-model" ]] || {
        export PROJECT_ROOT="$original_project_root"
        return 1
    }
    [[ "${DEFAULT_TIMEOUT}" == "300" ]] || {
        export PROJECT_ROOT="$original_project_root"
        return 1
    }
    
    # Cleanup
    rm -rf "$PROJECT_ROOT/config"
    export PROJECT_ROOT="$original_project_root"
    
    return 0
}

# Test allowed tools array
test_allowed_tools_array() {
    # Check that ALLOWED_TOOLS array is populated
    [[ ${#ALLOWED_TOOLS[@]} -gt 0 ]] || return 1
    
    # Check for some expected tools
    local found_ostruct=false
    local found_jq=false
    local found_pandoc=false
    
    for tool in "${ALLOWED_TOOLS[@]}"; do
        case "$tool" in
            "ostruct") found_ostruct=true ;;
            "jq") found_jq=true ;;
            "pandoc") found_pandoc=true ;;
        esac
    done
    
    [[ "$found_ostruct" == true ]] || return 1
    [[ "$found_jq" == true ]] || return 1
    [[ "$found_pandoc" == true ]] || return 1
    
    return 0
}

# Test configuration with non-existent file
test_load_configuration_nonexistent_file() {
    # Try to load non-existent file (should not fail)
    if load_configuration "/nonexistent/config/file"; then
        return 0
    else
        echo "Loading non-existent config file failed"
        return 1
    fi
}

# Test numeric validation
test_validate_numeric_fields() {
    # Test valid numeric values
    export MAX_RETRIES="5"
    export MAX_REPLANS="3"
    export DEFAULT_TIMEOUT="600"
    
    if validate_configuration; then
        return 0
    else
        echo "Valid numeric values failed validation"
        return 1
    fi
}

# Run all tests
echo "=== Testing config.sh module ==="
echo

run_test "default configuration values" test_default_config_values
run_test "validate valid configuration" test_validate_configuration_valid
run_test "validate invalid timeout" test_validate_configuration_invalid_timeout
run_test "validate invalid boolean" test_validate_configuration_invalid_boolean
run_test "validate missing field" test_validate_configuration_missing_field
run_test "load configuration from file" test_load_configuration_with_file
run_test "load configuration with local override" test_load_configuration_with_local_override
run_test "allowed tools array" test_allowed_tools_array
run_test "load nonexistent configuration file" test_load_configuration_nonexistent_file
run_test "validate numeric fields" test_validate_numeric_fields

# Cleanup
rm -f "$TEST_LOG_FILE" "$TEST_CONFIG_FILE" "$TEST_LOCAL_CONFIG_FILE"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All config tests passed!"
    exit 0
else
    echo "❌ Some config tests failed!"
    exit 1
fi 
# Load configuration
load_configuration
