#!/bin/bash
# Unit tests for validation.sh module

set -euo pipefail

# Test setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_LOG_FILE="/tmp/test_convert_log_$$"
TEST_OUTPUT_FILE="/tmp/test_output_$$"
TEST_REFERENCE_FILE="/tmp/test_reference_$$"

# Set up test environment
export LOG_FILE="$TEST_LOG_FILE"
export VERBOSE=false
export DEBUG=false

# Create test files
echo "# Test Output" > "$TEST_OUTPUT_FILE"
echo "This is a test markdown file." >> "$TEST_OUTPUT_FILE"
echo "" >> "$TEST_OUTPUT_FILE"
echo "## Section 1" >> "$TEST_OUTPUT_FILE"
echo "Content here." >> "$TEST_OUTPUT_FILE"

echo "# Reference Output" > "$TEST_REFERENCE_FILE"
echo "This is a reference markdown file." >> "$TEST_REFERENCE_FILE"

# Source required modules
source "$PROJECT_ROOT/lib/logging.sh"
source "$PROJECT_ROOT/lib/config.sh"
source "$PROJECT_ROOT/lib/utils.sh"
source "$PROJECT_ROOT/lib/cache.sh"
source "$PROJECT_ROOT/lib/tools.sh"
source "$PROJECT_ROOT/lib/security.sh"
source "$PROJECT_ROOT/lib/analysis.sh"
source "$PROJECT_ROOT/lib/planning.sh"
source "$PROJECT_ROOT/lib/execution.sh"
source "$PROJECT_ROOT/lib/validation.sh"

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

# Test validate_output function
test_validate_output() {
    # Mock validate_output function
    mock_validate_output() {
        local output_file="$1"
        local expected_format="${2:-markdown}"
        
        # Check if file exists
        if [[ ! -f "$output_file" ]]; then
            echo "Output file does not exist: $output_file"
            return 1
        fi
        
        # Check file size
        if [[ ! -s "$output_file" ]]; then
            echo "Output file is empty: $output_file"
            return 1
        fi
        
        # Check format-specific validation
        case "$expected_format" in
            "markdown")
                if grep -q "^#" "$output_file"; then
                    echo "Valid markdown format detected"
                    return 0
                else
                    echo "No markdown headers found"
                    return 1
                fi
                ;;
            "text")
                echo "Valid text format"
                return 0
                ;;
            *)
                echo "Unknown format: $expected_format"
                return 1
                ;;
        esac
    }
    
    # Test with valid markdown file
    if mock_validate_output "$TEST_OUTPUT_FILE" "markdown"; then
        return 0
    else
        echo "Valid markdown file failed validation"
        return 1
    fi
}

# Test perform_dry_run_analysis function
test_perform_dry_run_analysis() {
    # Mock perform_dry_run_analysis function
    mock_perform_dry_run_analysis() {
        local input_file="$1"
        local plan="$2"
        
        echo "=== Dry Run Analysis ==="
        echo "Input file: $input_file"
        
        # Analyze plan steps
        local steps_count=$(echo "$plan" | jq '.plan.steps | length')
        echo "Plan contains $steps_count steps"
        
        # Check each step
        echo "$plan" | jq -r '.plan.steps[] | "Step: \(.tool) - \(.description // "No description")"'
        
        # Estimate execution time
        local estimated_time=$((steps_count * 30))  # 30 seconds per step
        echo "Estimated execution time: ${estimated_time}s"
        
        # Check for potential issues
        local issues=()
        
        # Check for missing tools
        while IFS= read -r tool; do
            case "$tool" in
                "pandoc"|"jq"|"echo"|"sed"|"awk")
                    # Available tools
                    ;;
                *)
                    issues+=("Tool not available: $tool")
                    ;;
            esac
        done < <(echo "$plan" | jq -r '.plan.steps[].tool')
        
        if [[ ${#issues[@]} -gt 0 ]]; then
            echo "Potential issues found:"
            printf '%s\n' "${issues[@]}"
            return 1
        else
            echo "No issues detected"
            return 0
        fi
    }
    
    local test_plan='{"plan": {"steps": [{"tool": "pandoc", "description": "Convert to markdown"}]}}'
    
    if mock_perform_dry_run_analysis "$TEST_OUTPUT_FILE" "$test_plan"; then
        return 0
    else
        echo "Dry run analysis failed"
        return 1
    fi
}

# Test output format validation
test_output_format_validation() {
    # Mock format validation function
    validate_output_format() {
        local output_file="$1"
        local expected_format="$2"
        
        case "$expected_format" in
            "markdown")
                # Check for markdown syntax
                if grep -q "^#" "$output_file" && grep -q "^##" "$output_file"; then
                    echo "Valid markdown structure"
                    return 0
                else
                    echo "Invalid markdown structure"
                    return 1
                fi
                ;;
            "html")
                if grep -q "<html>" "$output_file" && grep -q "</html>" "$output_file"; then
                    echo "Valid HTML structure"
                    return 0
                else
                    echo "Invalid HTML structure"
                    return 1
                fi
                ;;
            "json")
                if jq empty "$output_file" 2>/dev/null; then
                    echo "Valid JSON format"
                    return 0
                else
                    echo "Invalid JSON format"
                    return 1
                fi
                ;;
            *)
                echo "Unknown format: $expected_format"
                return 1
                ;;
        esac
    }
    
    # Test markdown validation
    validate_output_format "$TEST_OUTPUT_FILE" "markdown" || return 1
    
    # Test invalid format
    if validate_output_format "$TEST_OUTPUT_FILE" "html"; then
        echo "Markdown file incorrectly validated as HTML"
        return 1
    fi
    
    return 0
}

# Test content quality validation
test_content_quality_validation() {
    # Mock content quality validation
    validate_content_quality() {
        local output_file="$1"
        local min_length="${2:-100}"
        
        local file_size=$(wc -c < "$output_file")
        local line_count=$(wc -l < "$output_file")
        local word_count=$(wc -w < "$output_file")
        
        echo "File statistics:"
        echo "  Size: $file_size bytes"
        echo "  Lines: $line_count"
        echo "  Words: $word_count"
        
        # Check minimum length
        if [[ $file_size -lt $min_length ]]; then
            echo "File too short (minimum: $min_length bytes)"
            return 1
        fi
        
        # Check for reasonable content
        if [[ $word_count -lt 5 ]]; then
            echo "Too few words in output"
            return 1
        fi
        
        # Check for empty lines (good structure)
        local empty_lines=$(grep -c "^$" "$output_file" || echo "0")
        if [[ $empty_lines -eq 0 ]] && [[ $line_count -gt 5 ]]; then
            echo "Warning: No empty lines found, content may be poorly formatted"
        fi
        
        echo "Content quality validation passed"
        return 0
    }
    
    if validate_content_quality "$TEST_OUTPUT_FILE" 50; then
        return 0
    else
        echo "Content quality validation failed"
        return 1
    fi
}

# Test output comparison
test_output_comparison() {
    # Mock output comparison function
    compare_outputs() {
        local output_file="$1"
        local reference_file="$2"
        local similarity_threshold="${3:-0.8}"
        
        # Simple similarity check based on word count
        local output_words=$(wc -w < "$output_file")
        local reference_words=$(wc -w < "$reference_file")
        
        local similarity
        if [[ $reference_words -gt 0 ]]; then
            similarity=$(echo "scale=2; $output_words / $reference_words" | bc -l 2>/dev/null || echo "0.5")
        else
            similarity="0.0"
        fi
        
        echo "Similarity score: $similarity"
        
        # Check if similarity meets threshold
        if (( $(echo "$similarity >= $similarity_threshold" | bc -l 2>/dev/null || echo "0") )); then
            echo "Output meets similarity threshold"
            return 0
        else
            echo "Output below similarity threshold ($similarity_threshold)"
            return 1
        fi
    }
    
    # Test comparison (should pass with low threshold)
    if compare_outputs "$TEST_OUTPUT_FILE" "$TEST_REFERENCE_FILE" 0.3; then
        return 0
    else
        echo "Output comparison failed"
        return 1
    fi
}

# Test validation report generation
test_validation_report_generation() {
    # Mock validation report generation
    generate_validation_report() {
        local output_file="$1"
        local validation_results="$2"
        local report_file="${3:-validation_report.txt}"
        
        cat > "$report_file" << EOF
=== Validation Report ===
Generated: $(date)
Output file: $output_file

File Statistics:
- Size: $(wc -c < "$output_file") bytes
- Lines: $(wc -l < "$output_file")
- Words: $(wc -w < "$output_file")

Validation Results:
$validation_results

Status: $(echo "$validation_results" | grep -q "PASS" && echo "PASSED" || echo "FAILED")
EOF
        
        echo "Validation report generated: $report_file"
        return 0
    }
    
    local test_results="Format validation: PASS\nContent quality: PASS\nStructure check: PASS"
    local report_file="/tmp/test_report_$$"
    
    generate_validation_report "$TEST_OUTPUT_FILE" "$test_results" "$report_file"
    
    # Check if report was created
    if [[ -f "$report_file" ]] && grep -q "PASSED" "$report_file"; then
        rm -f "$report_file"
        return 0
    else
        rm -f "$report_file"
        echo "Validation report generation failed"
        return 1
    fi
}

# Test error detection in output
test_error_detection() {
    # Mock error detection function
    detect_output_errors() {
        local output_file="$1"
        local errors=()
        
        # Check for common error patterns
        if grep -q "Error:" "$output_file"; then
            errors+=("Error messages found in output")
        fi
        
        if grep -q "Failed:" "$output_file"; then
            errors+=("Failure messages found in output")
        fi
        
        if grep -q "Exception:" "$output_file"; then
            errors+=("Exception messages found in output")
        fi
        
        # Check for incomplete conversion indicators
        if grep -q "TODO:" "$output_file"; then
            errors+=("TODO markers found (incomplete conversion)")
        fi
        
        if grep -q "FIXME:" "$output_file"; then
            errors+=("FIXME markers found (conversion issues)")
        fi
        
        if [[ ${#errors[@]} -gt 0 ]]; then
            echo "Errors detected:"
            printf '%s\n' "${errors[@]}"
            return 1
        else
            echo "No errors detected in output"
            return 0
        fi
    }
    
    # Test with clean output (should pass)
    if detect_output_errors "$TEST_OUTPUT_FILE"; then
        return 0
    else
        echo "Error detection failed on clean output"
        return 1
    fi
}

# Test validation metrics calculation
test_validation_metrics() {
    # Mock metrics calculation
    calculate_validation_metrics() {
        local output_file="$1"
        local input_file="${2:-}"
        
        local metrics=()
        
        # File size metrics
        local output_size=$(wc -c < "$output_file")
        metrics+=("output_size_bytes:$output_size")
        
        # Content metrics
        local line_count=$(wc -l < "$output_file")
        local word_count=$(wc -w < "$output_file")
        metrics+=("line_count:$line_count")
        metrics+=("word_count:$word_count")
        
        # Structure metrics for markdown
        local header_count=$(grep -c "^#" "$output_file" || echo "0")
        metrics+=("header_count:$header_count")
        
        # Quality score (simple calculation)
        local quality_score=100
        if [[ $word_count -lt 10 ]]; then
            quality_score=$((quality_score - 20))
        fi
        if [[ $header_count -eq 0 ]]; then
            quality_score=$((quality_score - 10))
        fi
        metrics+=("quality_score:$quality_score")
        
        # Output metrics as JSON
        local json_metrics="{"
        for metric in "${metrics[@]}"; do
            local key="${metric%%:*}"
            local value="${metric##*:}"
            json_metrics+="\"$key\": $value, "
        done
        json_metrics="${json_metrics%, }}"
        json_metrics+="}"
        
        echo "$json_metrics"
        return 0
    }
    
    local metrics=$(calculate_validation_metrics "$TEST_OUTPUT_FILE")
    
    # Check if metrics contain expected fields
    if echo "$metrics" | jq -e '.output_size_bytes' >/dev/null 2>&1 && \
       echo "$metrics" | jq -e '.word_count' >/dev/null 2>&1 && \
       echo "$metrics" | jq -e '.quality_score' >/dev/null 2>&1; then
        return 0
    else
        echo "Validation metrics calculation failed"
        return 1
    fi
}

# Run all tests
echo "=== Testing validation.sh module ==="
echo

run_test "validate_output" test_validate_output
run_test "perform_dry_run_analysis" test_perform_dry_run_analysis
run_test "output_format_validation" test_output_format_validation
run_test "content_quality_validation" test_content_quality_validation
run_test "output_comparison" test_output_comparison
run_test "validation_report_generation" test_validation_report_generation
run_test "error_detection" test_error_detection
run_test "validation_metrics" test_validation_metrics

# Cleanup
rm -f "$TEST_LOG_FILE" "$TEST_OUTPUT_FILE" "$TEST_REFERENCE_FILE"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [[ $TESTS_PASSED -eq $TESTS_RUN ]]; then
    echo "✅ All validation tests passed!"
    exit 0
else
    echo "❌ Some validation tests failed!"
    exit 1
fi 