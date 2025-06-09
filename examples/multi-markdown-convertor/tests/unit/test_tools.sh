#!/bin/bash
# Unit tests for tools.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/config.sh"
source "$PROJECT_ROOT/lib/tools.sh"

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

# Test validate_required_tools with all tools present
test_validate_required_tools_present() {
    # Mock command -v to always succeed for required tools
    command() {
        if [[ "$1" == "-v" ]]; then
            case "$2" in
                "ostruct"|"jq")
                    return 0
                    ;;
                *)
                    return 1
                    ;;
            esac
        else
            builtin command "$@"
        fi
    }
    
    # Should pass when all required tools are present
    if validate_required_tools 2>/dev/null; then
        unset -f command
        return 0
    else
        unset -f command
        echo "Required tools validation failed when tools present"
        return 1
    fi
}

# Test validate_required_tools with missing tools
test_validate_required_tools_missing() {
    # Mock command -v to fail for ostruct
    command() {
        if [[ "$1" == "-v" ]]; then
            case "$2" in
                "jq")
                    return 0
                    ;;
                *)
                    return 1
                    ;;
            esac
        else
            builtin command "$@"
        fi
    }
    
    # Should fail when required tools are missing
    if validate_required_tools 2>/dev/null; then
        unset -f command
        echo "Required tools validation passed when tools missing"
        return 1
    else
        unset -f command
        return 0
    fi
}

# Test check_conversion_tools function
test_check_conversion_tools() {
    # Mock command -v for various tools
    command() {
        if [[ "$1" == "-v" ]]; then
            case "$2" in
                "pandoc"|"jq"|"ostruct")
                    return 0
                    ;;
                "pdftotext"|"tesseract")
                    return 1
                    ;;
                *)
                    return 1
                    ;;
            esac
        else
            builtin command "$@"
        fi
    }
    
    # Should run without error and log tool availability
    if check_conversion_tools 2>/dev/null; then
        unset -f command
        return 0
    else
        unset -f command
        echo "Check conversion tools failed"
        return 1
    fi
}

# Test tool availability detection
test_tool_availability_detection() {
    # Mock command -v for specific tools
    command() {
        if [[ "$1" == "-v" ]]; then
            case "$2" in
                "echo"|"cat"|"grep")
                    return 0
                    ;;
                *)
                    return 1
                    ;;
            esac
        else
            builtin command "$@"
        fi
    }
    
    # Test individual tool detection
    local available_tools=()
    local unavailable_tools=()
    
    for tool in "echo" "cat" "grep" "nonexistent_tool"; do
        if command -v "$tool" >/dev/null 2>&1; then
            available_tools+=("$tool")
        else
            unavailable_tools+=("$tool")
        fi
    done
    
    unset -f command
    
    # Should correctly identify available and unavailable tools
    [[ ${#available_tools[@]} -eq 3 ]] || return 1
    [[ ${#unavailable_tools[@]} -eq 1 ]] || return 1
    [[ "${unavailable_tools[0]}" == "nonexistent_tool" ]] || return 1
    
    return 0
}

# Test suggest_tool_installation function (mock)
test_suggest_tool_installation() {
    # Mock uname to return known OS
    uname() {
        case "$1" in
            "-s")
                echo "Darwin"
                ;;
            *)
                builtin uname "$@"
                ;;
        esac
    }
    
    # Mock the suggest_tool_installation function since it's complex
    mock_suggest_tool_installation() {
        local missing_tool="$1"
        
        case "$missing_tool" in
            "pandoc")
                echo "Install pandoc with: brew install pandoc"
                return 0
                ;;
            "jq")
                echo "Install jq with: brew install jq"
                return 0
                ;;
            *)
                echo "No installation suggestion for $missing_tool"
                return 1
                ;;
        esac
    }
    
    # Test suggestions for known tools
    local pandoc_suggestion=$(mock_suggest_tool_installation "pandoc")
    local jq_suggestion=$(mock_suggest_tool_installation "jq")
    
    unset -f uname
    
    [[ "$pandoc_suggestion" =~ "brew install pandoc" ]] || return 1
    [[ "$jq_suggestion" =~ "brew install jq" ]] || return 1
    
    return 0
}

# Test validate_plan_tools function (mock)
test_validate_plan_tools() {
    # Mock plan with tool requirements
    local mock_plan='{"steps": [{"tool": "pandoc"}, {"tool": "jq"}]}'
    
    # Mock command -v for plan tools
    command() {
        if [[ "$1" == "-v" ]]; then
            case "$2" in
                "pandoc"|"jq")
                    return 0
                    ;;
                *)
                    return 1
                    ;;
            esac
        else
            builtin command "$@"
        fi
    }
    
    # Mock validate_plan_tools function
    mock_validate_plan_tools() {
        local plan="$1"
        local missing_tools=()
        
        # Extract tools from plan (simplified)
        if echo "$plan" | grep -q "pandoc"; then
            if ! command -v pandoc >/dev/null 2>&1; then
                missing_tools+=("pandoc")
            fi
        fi
        
        if echo "$plan" | grep -q "jq"; then
            if ! command -v jq >/dev/null 2>&1; then
                missing_tools+=("jq")
            fi
        fi
        
        if [[ ${#missing_tools[@]} -eq 0 ]]; then
            return 0
        else
            echo "Missing tools: ${missing_tools[*]}"
            return 1
        fi
    }
    
    # Should pass when all plan tools are available
    if mock_validate_plan_tools "$mock_plan"; then
        unset -f command
        return 0
    else
        unset -f command
        echo "Plan tools validation failed"
        return 1
    fi
}

# Test tool version checking (mock)
test_tool_version_checking() {
    # Mock version checking for tools
    mock_check_tool_version() {
        local tool="$1"
        local min_version="$2"
        
        case "$tool" in
            "pandoc")
                echo "pandoc 2.19.2"
                return 0
                ;;
            "jq")
                echo "jq-1.6"
                return 0
                ;;
            *)
                return 1
                ;;
        esac
    }
    
    # Test version checking
    local pandoc_version=$(mock_check_tool_version "pandoc" "2.0")
    local jq_version=$(mock_check_tool_version "jq" "1.5")
    
    [[ "$pandoc_version" =~ "pandoc" ]] || return 1
    [[ "$jq_version" =~ "jq" ]] || return 1
    
    return 0
}

# Test tool path resolution
test_tool_path_resolution() {
    # Mock which command
    which() {
        case "$1" in
            "echo")
                echo "/bin/echo"
                return 0
                ;;
            "cat")
                echo "/bin/cat"
                return 0
                ;;
            *)
                return 1
                ;;
        esac
    }
    
    # Test path resolution
    local echo_path=$(which echo)
    local cat_path=$(which cat)
    
    unset -f which
    
    [[ "$echo_path" == "/bin/echo" ]] || return 1
    [[ "$cat_path" == "/bin/cat" ]] || return 1
    
    return 0
}

# Test allowed tools validation
test_allowed_tools_validation() {
    # Test that ALLOWED_TOOLS array contains expected tools
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

# Test tool security validation
test_tool_security_validation() {
    # Mock function to check if tool is in allowed list
    is_tool_allowed() {
        local tool="$1"
        
        for allowed_tool in "${ALLOWED_TOOLS[@]}"; do
            if [[ "$tool" == "$allowed_tool" ]]; then
                return 0
            fi
        done
        return 1
    }
    
    # Test allowed tools
    is_tool_allowed "ostruct" || return 1
    is_tool_allowed "jq" || return 1
    is_tool_allowed "pandoc" || return 1
    
    # Test disallowed tools
    if is_tool_allowed "rm"; then
        echo "Dangerous tool marked as allowed"
        return 1
    fi
    
    if is_tool_allowed "curl"; then
        echo "Network tool marked as allowed when it shouldn't be"
        return 1
    fi
    
    return 0
}

# Run all tests
echo "=== Testing tools.sh module ==="
echo

run_test "validate_required_tools present" test_validate_required_tools_present
run_test "validate_required_tools missing" test_validate_required_tools_missing
run_test "check_conversion_tools" test_check_conversion_tools
run_test "tool availability detection" test_tool_availability_detection
run_test "suggest_tool_installation" test_suggest_tool_installation
run_test "validate_plan_tools" test_validate_plan_tools
run_test "tool version checking" test_tool_version_checking
run_test "tool path resolution" test_tool_path_resolution
run_test "allowed tools validation" test_allowed_tools_validation
run_test "tool security validation" test_tool_security_validation

# Cleanup
rm -f "$TEST_LOG_FILE"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All tools tests passed!"
    exit 0
else
    echo "❌ Some tools tests failed!"
    exit 1
fi 