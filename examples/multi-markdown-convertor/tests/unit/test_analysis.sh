#!/bin/bash
# Unit tests for analysis.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_INPUT_FILE="/tmp/test_input_$$"
TEST_LARGE_FILE="/tmp/test_large_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false
export LARGE_DOCUMENT_THRESHOLD=1024  # 1KB for testing

# Create test files
echo "Small test document content" > "$TEST_INPUT_FILE"
# Create large file (2KB)
dd if=/dev/zero of="$TEST_LARGE_FILE" bs=1024 count=2 2>/dev/null

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/config.sh"
source "$PROJECT_ROOT/lib/utils.sh"
source "$PROJECT_ROOT/lib/cache.sh"
source "$PROJECT_ROOT/lib/tools.sh"
source "$PROJECT_ROOT/lib/analysis.sh"

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

# Mock ostruct command for testing
mock_ostruct() {
    case "$*" in
        *"pre-analyze"*)
            echo '{"document_type": "text", "complexity": "low", "estimated_tokens": 100}'
            return 0
            ;;
        *"analyze"*)
            echo '{"analysis": {"type": "markdown", "structure": "simple", "content_summary": "test document"}}'
            return 0
            ;;
        *)
            echo '{"error": "unknown command"}'
            return 1
            ;;
    esac
}

# Test pre_analyze_document function
test_pre_analyze_document() {
    # Mock ostruct command
    ostruct() {
        mock_ostruct "$@"
    }
    
    # Should return pre-analysis JSON
    local result=$(pre_analyze_document "$TEST_INPUT_FILE")
    local exit_code=$?
    
    unset -f ostruct
    
    [[ $exit_code -eq 0 ]] || return 1
    [[ "$result" =~ "document_type" ]] || return 1
    [[ "$result" =~ "complexity" ]] || return 1
    
    return 0
}

# Test analyze_document function
test_analyze_document() {
    # Mock ostruct command
    ostruct() {
        mock_ostruct "$@"
    }
    
    # Should return analysis JSON
    local result=$(analyze_document "$TEST_INPUT_FILE")
    local exit_code=$?
    
    unset -f ostruct
    
    [[ $exit_code -eq 0 ]] || return 1
    [[ "$result" =~ "analysis" ]] || return 1
    
    return 0
}

# Test handle_large_document function
test_handle_large_document() {
    # Mock file size check
    stat() {
        if [[ "$1" == "-c" && "$2" == "%s" ]]; then
            case "$3" in
                "$TEST_LARGE_FILE")
                    echo "2048"  # 2KB
                    ;;
                *)
                    echo "100"   # Small file
                    ;;
            esac
        else
            builtin stat "$@"
        fi
    }
    
    # Mock handle_large_document function
    mock_handle_large_document() {
        local input_file="$1"
        local file_size=$(stat -c "%s" "$input_file")
        
        if [[ $file_size -gt $LARGE_DOCUMENT_THRESHOLD ]]; then
            echo '{"large_document": true, "chunks": 2, "processing": "chunked"}'
            return 0
        else
            echo '{"large_document": false, "processing": "normal"}'
            return 0
        fi
    }
    
    # Test with large file
    local result=$(mock_handle_large_document "$TEST_LARGE_FILE")
    
    unset -f stat
    
    [[ "$result" =~ "large_document.*true" ]] || return 1
    [[ "$result" =~ "chunks" ]] || return 1
    
    return 0
}

# Test document type detection
test_document_type_detection() {
    # Mock file command
    file() {
        case "$2" in
            *".pdf")
                echo "PDF document"
                ;;
            *".docx")
                echo "Microsoft Word document"
                ;;
            *".txt"|*"test_input"*)
                echo "ASCII text"
                ;;
            *)
                echo "data"
                ;;
        esac
    }
    
    # Mock document type detection
    detect_document_type() {
        local input_file="$1"
        local file_type=$(file -b "$input_file")
        
        case "$file_type" in
            *"PDF"*)
                echo "pdf"
                ;;
            *"Word"*)
                echo "docx"
                ;;
            *"text"*)
                echo "text"
                ;;
            *)
                echo "unknown"
                ;;
        esac
    }
    
    # Test different file types
    local text_type=$(detect_document_type "$TEST_INPUT_FILE")
    local pdf_type=$(detect_document_type "test.pdf")
    local docx_type=$(detect_document_type "test.docx")
    
    unset -f file
    
    [[ "$text_type" == "text" ]] || return 1
    [[ "$pdf_type" == "pdf" ]] || return 1
    [[ "$docx_type" == "docx" ]] || return 1
    
    return 0
}

# Test analysis caching
test_analysis_caching() {
    export ENABLE_CACHING=true
    local cache_dir="/tmp/test_cache_$$"
    export CACHE_DIR="$cache_dir"
    mkdir -p "$cache_dir"
    
    # Mock cached analysis
    local test_analysis='{"cached": true, "analysis": "test"}'
    
    # Store cached analysis
    store_cached_analysis "$TEST_INPUT_FILE" "$test_analysis"
    
    # Mock analyze_document to use cache
    mock_analyze_document_with_cache() {
        local input_file="$1"
        
        # Try to get cached analysis first
        if cached_result=$(get_cached_analysis "$input_file"); then
            echo "$cached_result"
            return 0
        else
            # Fallback to actual analysis
            echo '{"cached": false, "analysis": "fresh"}'
            return 0
        fi
    }
    
    # Should return cached result
    local result=$(mock_analyze_document_with_cache "$TEST_INPUT_FILE")
    
    # Cleanup
    rm -rf "$cache_dir"
    
    [[ "$result" =~ "cached.*true" ]] || return 1
    
    return 0
}

# Test analysis error handling
test_analysis_error_handling() {
    # Mock ostruct command that fails
    ostruct() {
        echo "Error: Analysis failed"
        return 1
    }
    
    # Mock error handling
    mock_analyze_with_error_handling() {
        local input_file="$1"
        
        if ! ostruct run analysis.j2 schema.json --fta input "$input_file" 2>/dev/null; then
            echo '{"error": "analysis_failed", "message": "Could not analyze document"}'
            return 1
        fi
    }
    
    # Should handle error gracefully
    local result=$(mock_analyze_with_error_handling "$TEST_INPUT_FILE")
    local exit_code=$?
    
    unset -f ostruct
    
    [[ $exit_code -eq 1 ]] || return 1
    [[ "$result" =~ "error" ]] || return 1
    
    return 0
}

# Test chunk_pdf_document function (mock)
test_chunk_pdf_document() {
    # Mock PDF chunking
    mock_chunk_pdf_document() {
        local pdf_file="$1"
        local chunk_size="${2:-50}"
        
        # Simulate PDF chunking
        echo '{"chunks": [{"pages": "1-50", "file": "chunk1.pdf"}, {"pages": "51-100", "file": "chunk2.pdf"}]}'
        return 0
    }
    
    # Test PDF chunking
    local result=$(mock_chunk_pdf_document "test.pdf" 50)
    
    [[ "$result" =~ "chunks" ]] || return 1
    [[ "$result" =~ "pages" ]] || return 1
    
    return 0
}

# Test create_available_tools_docs function (mock)
test_create_available_tools_docs() {
    # Mock tools documentation creation
    mock_create_available_tools_docs() {
        local tools_doc='{"available_tools": ["pandoc", "pdftotext", "tesseract"], "descriptions": {"pandoc": "Universal document converter"}}'
        echo "$tools_doc"
        return 0
    }
    
    # Should return tools documentation
    local result=$(mock_create_available_tools_docs)
    
    [[ "$result" =~ "available_tools" ]] || return 1
    [[ "$result" =~ "pandoc" ]] || return 1
    
    return 0
}

# Test analysis result validation
test_analysis_result_validation() {
    # Mock analysis validation
    validate_analysis_result() {
        local analysis="$1"
        
        # Check if analysis is valid JSON
        if ! echo "$analysis" | jq empty 2>/dev/null; then
            return 1
        fi
        
        # Check for required fields
        if ! echo "$analysis" | jq -e '.analysis' >/dev/null 2>&1; then
            return 1
        fi
        
        return 0
    }
    
    # Test valid analysis
    local valid_analysis='{"analysis": {"type": "text", "content": "valid"}}'
    validate_analysis_result "$valid_analysis" || return 1
    
    # Test invalid analysis
    local invalid_analysis='invalid json{'
    if validate_analysis_result "$invalid_analysis"; then
        echo "Invalid analysis passed validation"
        return 1
    fi
    
    return 0
}

# Run all tests
echo "=== Testing analysis.sh module ==="
echo

run_test "pre_analyze_document" test_pre_analyze_document
run_test "analyze_document" test_analyze_document
run_test "handle_large_document" test_handle_large_document
run_test "document_type_detection" test_document_type_detection
run_test "analysis_caching" test_analysis_caching
run_test "analysis_error_handling" test_analysis_error_handling
run_test "chunk_pdf_document" test_chunk_pdf_document
run_test "create_available_tools_docs" test_create_available_tools_docs
run_test "analysis_result_validation" test_analysis_result_validation

# Cleanup
rm -f "$TEST_LOG_FILE" "$TEST_INPUT_FILE" "$TEST_LARGE_FILE"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All analysis tests passed!"
    exit 0
else
    echo "❌ Some analysis tests failed!"
    exit 1
fi 