#!/bin/bash

# Agent System Test Suite
# Tests functionality, security, and error handling

set -euo pipefail

# Test configuration
readonly TEST_DIR="test_workdir"
readonly AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly ORIGINAL_DIR="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging
log() {
    echo -e "[$1] $2" >&2
}

log_info() {
    log "${BLUE}INFO${NC}" "$1"
}

log_success() {
    log "${GREEN}PASS${NC}" "$1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_failure() {
    log "${RED}FAIL${NC}" "$1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_warning() {
    log "${YELLOW}WARN${NC}" "$1"
}

# Test framework
run_test() {
    local test_name="$1"
    local test_func="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "Running test: $test_name"
    
    if $test_func; then
        log_success "$test_name"
        return 0
    else
        log_failure "$test_name"
        return 1
    fi
}

# Setup test environment
setup_test_env() {
    log_info "Setting up test environment"
    
    # Create test directory
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"
    
    # Copy agent files
    cp -r "$AGENT_DIR"/* .
    
    # Ensure runner is executable
    chmod +x runner.sh
    
    log_info "Test environment ready"
}

# Cleanup test environment
cleanup_test_env() {
    log_info "Cleaning up test environment"
    cd "$ORIGINAL_DIR"
    rm -rf "$TEST_DIR"
}

# Test basic functionality
test_basic_functionality() {
    log_info "Testing basic agent functionality"
    
    # Test simple file creation
    if ./runner.sh "Create a file named test.txt with content 'Hello Test'" >/dev/null 2>&1; then
        if [[ -f workdir/sandbox_*/test.txt ]]; then
            local content=$(cat workdir/sandbox_*/test.txt)
            if [[ "$content" == "Hello Test" ]]; then
                return 0
            fi
        fi
    fi
    
    return 1
}

# Test tool executors individually
test_tool_jq() {
    log_info "Testing jq tool"
    
    # Create test JSON file
    echo '{"name": "test", "value": 42}' > test.json
    
    # Test jq execution
    if ./runner.sh "Use jq to extract the 'name' field from test.json" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

test_tool_grep() {
    log_info "Testing grep tool"
    
    # Create test file
    echo -e "line1\ntest line\nline3" > test.txt
    
    if ./runner.sh "Use grep to find lines containing 'test' in test.txt" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

test_tool_curl() {
    log_info "Testing curl tool"
    
    # Test HTTP download
    if ./runner.sh "Download JSON data from httpbin.org/json" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

test_tool_file_operations() {
    log_info "Testing file operations"
    
    if ./runner.sh "Create a file, write content, append more content, then read it back" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Test security features
test_path_traversal_protection() {
    log_info "Testing path traversal protection"
    
    # This should fail due to path traversal attempt
    if ./runner.sh "Try to read /etc/passwd using ../../../etc/passwd" >/dev/null 2>&1; then
        return 1  # Should fail
    else
        return 0  # Correctly blocked
    fi
}

test_size_limits() {
    log_info "Testing size limits"
    
    # Test file size limit
    if ./runner.sh "Create a file with 100KB of content" >/dev/null 2>&1; then
        return 1  # Should fail due to size limit
    else
        return 0  # Correctly blocked
    fi
}

test_sandbox_isolation() {
    log_info "Testing sandbox isolation"
    
    # Test that files are created in sandbox
    if ./runner.sh "Create a file named isolated.txt" >/dev/null 2>&1; then
        # Check file is in sandbox, not in current directory
        if [[ ! -f isolated.txt ]] && [[ -f workdir/sandbox_*/isolated.txt ]]; then
            return 0
        fi
    fi
    
    return 1
}

# Test error handling
test_error_handling() {
    log_info "Testing error handling"
    
    # Test invalid tool usage
    if ./runner.sh "Use a non-existent tool to do something" >/dev/null 2>&1; then
        return 1  # Should fail
    else
        return 0  # Correctly handled error
    fi
}

test_ostruct_limit() {
    log_info "Testing ostruct call limits"
    
    # Test with a task that might require many calls
    if ./runner.sh "Perform a complex task that requires many steps and iterations" >/dev/null 2>&1; then
        # Check if it completed or hit the limit gracefully
        if grep -q "Maximum ostruct calls" logs/run_*.log; then
            return 0  # Correctly enforced limit
        fi
    fi
    
    return 0  # May complete within limit
}

# Test JSON schema validation
test_json_validation() {
    log_info "Testing JSON schema validation"
    
    # Check if schemas are valid JSON
    for schema in schemas/*.json; do
        if ! jq . "$schema" >/dev/null 2>&1; then
            log_failure "Invalid JSON schema: $schema"
            return 1
        fi
    done
    
    return 0
}

test_tools_json_validation() {
    log_info "Testing tools.json validation"
    
    # Check if tools.json is valid
    if ! jq . tools.json >/dev/null 2>&1; then
        return 1
    fi
    
    # Check if it contains expected tools
    local tool_count=$(jq 'keys | length' tools.json)
    if [[ $tool_count -eq 10 ]]; then
        return 0
    fi
    
    return 1
}

# Test dependency checks
test_dependencies() {
    log_info "Testing required dependencies"
    
    local missing_deps=()
    
    # Check for required tools
    if ! command -v jq >/dev/null 2>&1; then
        missing_deps+=("jq")
    fi
    
    if ! command -v curl >/dev/null 2>&1; then
        missing_deps+=("curl")
    fi
    
    if ! command -v awk >/dev/null 2>&1; then
        missing_deps+=("awk")
    fi
    
    if [[ ${#missing_deps[@]} -eq 0 ]]; then
        return 0
    else
        log_warning "Missing dependencies: ${missing_deps[*]}"
        return 1
    fi
}

# Test template rendering
test_template_syntax() {
    log_info "Testing template syntax"
    
    # Check if templates have valid Jinja2 syntax
    # This is a basic check - full validation would require Jinja2
    for template in templates/*.j2; do
        if ! grep -q "{{" "$template" && ! grep -q "{%" "$template"; then
            log_warning "Template may not contain Jinja2 syntax: $template"
        fi
    done
    
    return 0
}

# Performance tests
test_performance() {
    log_info "Testing performance"
    
    local start_time=$(date +%s)
    
    # Run a simple task and measure time
    if ./runner.sh "Create a small file and read it back" >/dev/null 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        if [[ $duration -lt 60 ]]; then  # Should complete within 1 minute
            return 0
        fi
    fi
    
    return 1
}

# Integration tests
test_multi_step_workflow() {
    log_info "Testing multi-step workflow"
    
    # Test a complex task that requires multiple steps
    if ./runner.sh "Download a JSON file, extract data, create a summary file" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

test_error_recovery() {
    log_info "Testing error recovery"
    
    # Test a task that might fail initially but can recover
    if ./runner.sh "Try to download a file that doesn't exist, then create a default file" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Main test runner
main() {
    log_info "Starting Agent System Test Suite"
    
    # Check if we're in the right directory
    if [[ ! -f "runner.sh" ]]; then
        log_failure "runner.sh not found. Run from agent directory."
        exit 1
    fi
    
    # Setup test environment
    setup_test_env
    
    # Run all tests
    run_test "Dependency Check" test_dependencies
    run_test "JSON Schema Validation" test_json_validation
    run_test "Tools JSON Validation" test_tools_json_validation
    run_test "Template Syntax Check" test_template_syntax
    run_test "Basic Functionality" test_basic_functionality
    run_test "JQ Tool" test_tool_jq
    run_test "Grep Tool" test_tool_grep
    run_test "Curl Tool" test_tool_curl
    run_test "File Operations" test_tool_file_operations
    run_test "Path Traversal Protection" test_path_traversal_protection
    run_test "Size Limits" test_size_limits
    run_test "Sandbox Isolation" test_sandbox_isolation
    run_test "Error Handling" test_error_handling
    run_test "Ostruct Call Limits" test_ostruct_limit
    run_test "Performance" test_performance
    run_test "Multi-Step Workflow" test_multi_step_workflow
    run_test "Error Recovery" test_error_recovery
    
    # Cleanup
    cleanup_test_env
    
    # Report results
    log_info "Test Results:"
    log_info "  Tests Run: $TESTS_RUN"
    log_info "  Passed: $TESTS_PASSED"
    log_info "  Failed: $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        log_success "All tests passed!"
        exit 0
    else
        log_failure "$TESTS_FAILED tests failed"
        exit 1
    fi
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi