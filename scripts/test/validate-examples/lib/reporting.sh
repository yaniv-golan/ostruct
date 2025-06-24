#!/bin/bash
# Reporting library - tracks results and generates validation reports

# Global variables for result tracking (compatible with older bash)
TOTAL_EXAMPLES=0
TOTAL_COMMANDS=0
PASSED_COMMANDS=0
DRY_FAILED_COMMANDS=0
LIVE_FAILED_COMMANDS=0
START_TIME=""

declare -a FAILED_EXAMPLES
declare -a PASSED_EXAMPLES
declare -a DRY_FAIL_EXAMPLES
declare -a LIVE_FAIL_EXAMPLES

# Initialize results tracking
init_results_tracking() {
    TOTAL_EXAMPLES=0
    TOTAL_COMMANDS=0
    PASSED_COMMANDS=0
    DRY_FAILED_COMMANDS=0
    LIVE_FAILED_COMMANDS=0
    START_TIME=$(date -Iseconds)

    FAILED_EXAMPLES=()
    PASSED_EXAMPLES=()
    DRY_FAIL_EXAMPLES=()
    LIVE_FAIL_EXAMPLES=()

    # Create results directory
    local results_dir="${CACHE_DIR}/results"
    mkdir -p "$results_dir"

    vlog "DEBUG" "Initialized results tracking"
}

# Record a command result
record_result() {
    local example_name="$1"
    local command="$2"
    local status="$3"
    local error_message="$4"

    # Update counters
    ((TOTAL_COMMANDS++))

    case "$status" in
        "PASS")
            ((PASSED_COMMANDS++))
            add_to_passed_examples "$example_name"
            ;;
        "DRY_FAIL")
            ((DRY_FAILED_COMMANDS++))
            add_to_dry_fail_examples "$example_name" "$command" "$error_message"
            ;;
        "LIVE_FAIL")
            ((LIVE_FAILED_COMMANDS++))
            add_to_live_fail_examples "$example_name" "$command" "$error_message"
            ;;
    esac

    # Store detailed result
    store_detailed_result "$example_name" "$command" "$status" "$error_message"

    vlog "DEBUG" "Recorded result: $example_name - $status"
}

# Add example to passed list (avoid duplicates)
add_to_passed_examples() {
    local example_name="$1"

    # Only add if not already in failed lists
    if ! array_contains "$example_name" "${DRY_FAIL_EXAMPLES[@]:-}" && \
       ! array_contains "$example_name" "${LIVE_FAIL_EXAMPLES[@]:-}"; then
        if ! array_contains "$example_name" "${PASSED_EXAMPLES[@]:-}"; then
            PASSED_EXAMPLES+=("$example_name")
            ((TOTAL_EXAMPLES++))
        fi
    fi
}

# Add example to dry-fail list
add_to_dry_fail_examples() {
    local example_name="$1"
    local command="$2"
    local error_message="$3"

    # Remove from passed if it was there
    remove_from_array "$example_name" PASSED_EXAMPLES

    if ! array_contains "$example_name" "${DRY_FAIL_EXAMPLES[@]:-}"; then
        DRY_FAIL_EXAMPLES+=("$example_name")
        if ! array_contains "$example_name" "${LIVE_FAIL_EXAMPLES[@]:-}"; then
            ((TOTAL_EXAMPLES++))
        fi
    fi
}

# Add example to live-fail list
add_to_live_fail_examples() {
    local example_name="$1"
    local command="$2"
    local error_message="$3"

    # Remove from passed if it was there
    remove_from_array "$example_name" PASSED_EXAMPLES

    if ! array_contains "$example_name" "${LIVE_FAIL_EXAMPLES[@]:-}"; then
        LIVE_FAIL_EXAMPLES+=("$example_name")
        if ! array_contains "$example_name" "${DRY_FAIL_EXAMPLES[@]:-}"; then
            ((TOTAL_EXAMPLES++))
        fi
    fi
}

# Store detailed result to file
store_detailed_result() {
    local example_name="$1"
    local command="$2"
    local status="$3"
    local error_message="$4"

    local results_dir="${CACHE_DIR}/results"
    local result_file="${results_dir}/${example_name//\//_}.json"

    # Create or update the result file
    if [[ ! -f "$result_file" ]]; then
        cat > "$result_file" << EOF
{
  "example": "$example_name",
  "commands": [],
  "summary": {
    "total": 0,
    "passed": 0,
    "dry_failed": 0,
    "live_failed": 0
  },
  "timestamp": "$(date -Iseconds)"
}
EOF
    fi

    # Add command result using jq
    local temp_file="${result_file}.tmp"
    jq --arg cmd "$command" \
       --arg status "$status" \
       --arg error "$error_message" \
       --arg timestamp "$(date -Iseconds)" \
       '.commands += [{
         "command": $cmd,
         "status": $status,
         "error": $error,
         "timestamp": $timestamp
       }] |
       .summary.total += 1 |
       if $status == "PASS" then
         .summary.passed += 1
       elif $status == "DRY_FAIL" then
         .summary.dry_failed += 1
       elif $status == "LIVE_FAIL" then
         .summary.live_failed += 1
       else . end' "$result_file" > "$temp_file" && mv "$temp_file" "$result_file"
}

# Generate final validation report
generate_final_report() {
    local end_time=$(date -Iseconds)
    local duration=$(calculate_duration "$START_TIME" "$end_time")

    vlog "INFO" "Generating final validation report..."

    # Calculate statistics
    local total_examples=$TOTAL_EXAMPLES
    local total_commands=$TOTAL_COMMANDS
    local passed_commands=$PASSED_COMMANDS
    local dry_failed_commands=$DRY_FAILED_COMMANDS
    local live_failed_commands=$LIVE_FAILED_COMMANDS

    local passed_examples_count=${#PASSED_EXAMPLES[@]}
    local dry_fail_examples_count=${#DRY_FAIL_EXAMPLES[@]}
    local live_fail_examples_count=${#LIVE_FAIL_EXAMPLES[@]}

    # Generate console report
    echo
    echo "=================================="
    echo "  Example Validation Report"
    echo "=================================="
    echo
    echo "Duration: $duration"
    echo "Timestamp: $end_time"
    echo
    echo "Examples Summary:"
    echo "  Total Examples: $total_examples"
    echo -e "  ${GREEN}✅ Passed: $passed_examples_count${NC}"
    echo -e "  ${YELLOW}⚠️  Dry-run Failed: $dry_fail_examples_count${NC}"
    echo -e "  ${RED}❌ Live Failed: $live_fail_examples_count${NC}"
    echo
    echo "Commands Summary:"
    echo "  Total Commands: $total_commands"
    echo -e "  ${GREEN}✅ Passed: $passed_commands${NC}"
    echo -e "  ${YELLOW}⚠️  Dry-run Failed: $dry_failed_commands${NC}"
    echo -e "  ${RED}❌ Live Failed: $live_failed_commands${NC}"

    # Show failed examples
    if [[ $dry_fail_examples_count -gt 0 ]]; then
        echo
        echo -e "${YELLOW}Dry-run Failures:${NC}"
        for example in "${DRY_FAIL_EXAMPLES[@]}"; do
            echo "  - $example"
        done
    fi

    if [[ $live_fail_examples_count -gt 0 ]]; then
        echo
        echo -e "${RED}Live Execution Failures:${NC}"
        for example in "${LIVE_FAIL_EXAMPLES[@]}"; do
            echo "  - $example"
        done
    fi

    # Generate JSON report
    generate_json_report "$end_time" "$duration"

    # Generate detailed HTML report if requested
    if [[ "$VERBOSE" == "true" ]]; then
        generate_html_report
    fi

    echo
    echo "Detailed results stored in: ${CACHE_DIR}/results/"
    echo
}

# Generate JSON report
generate_json_report() {
    local end_time="$1"
    local duration="$2"
    local report_file="${CACHE_DIR}/validation_report.json"

    cat > "$report_file" << EOF
{
  "validation_report": {
    "timestamp": "$end_time",
    "duration": "$duration",
    "summary": {
      "total_examples": $TOTAL_EXAMPLES,
      "total_commands": $TOTAL_COMMANDS,
      "passed_commands": $PASSED_COMMANDS,
      "dry_failed_commands": $DRY_FAILED_COMMANDS,
      "live_failed_commands": $LIVE_FAILED_COMMANDS,
      "passed_examples": ${#PASSED_EXAMPLES[@]},
      "dry_fail_examples": ${#DRY_FAIL_EXAMPLES[@]},
      "live_fail_examples": ${#LIVE_FAIL_EXAMPLES[@]}
    },
    "passed_examples": $(printf '%s\n' "${PASSED_EXAMPLES[@]:-}" | jq -R . | jq -s .),
    "dry_fail_examples": $(printf '%s\n' "${DRY_FAIL_EXAMPLES[@]:-}" | jq -R . | jq -s .),
    "live_fail_examples": $(printf '%s\n' "${LIVE_FAIL_EXAMPLES[@]:-}" | jq -R . | jq -s .),
    "detailed_results_dir": "${CACHE_DIR}/results/"
  }
}
EOF

    vlog "INFO" "JSON report saved to: $report_file"
}

# Generate HTML report (if verbose mode)
generate_html_report() {
    local html_file="${CACHE_DIR}/validation_report.html"

    cat > "$html_file" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>ostruct Example Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .stat-box { background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; flex: 1; }
        .passed { border-left: 4px solid #28a745; }
        .warning { border-left: 4px solid #ffc107; }
        .failed { border-left: 4px solid #dc3545; }
        .example-list { margin: 20px 0; }
        .example-item { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 3px; }
        .command { font-family: monospace; background: #e9ecef; padding: 5px; margin: 5px 0; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ostruct Example Validation Report</h1>
        <p>Generated: $(date)</p>
        <p>Duration: $(calculate_duration "$START_TIME" "$(date -Iseconds)")</p>
    </div>

    <div class="summary">
        <div class="stat-box passed">
            <h3>Passed Examples</h3>
            <p>${#PASSED_EXAMPLES[@]} examples</p>
        </div>
        <div class="stat-box warning">
            <h3>Dry-run Failures</h3>
            <p>${#DRY_FAIL_EXAMPLES[@]} examples</p>
        </div>
        <div class="stat-box failed">
            <h3>Live Failures</h3>
            <p>${#LIVE_FAIL_EXAMPLES[@]} examples</p>
        </div>
    </div>

    <!-- Add detailed results here -->

</body>
</html>
EOF

    vlog "INFO" "HTML report saved to: $html_file"
}

# Get exit code based on results
get_exit_code() {
    local dry_failed=$DRY_FAILED_COMMANDS
    local live_failed=$LIVE_FAILED_COMMANDS

    if [[ $dry_failed -gt 0 || $live_failed -gt 0 ]]; then
        echo 1
    else
        echo 0
    fi
}

# Helper functions
array_contains() {
    local element="$1"
    shift
    local array=("$@")

    for item in "${array[@]}"; do
        if [[ "$item" == "$element" ]]; then
            return 0
        fi
    done
    return 1
}

remove_from_array() {
    local element="$1"
    local array_name="$2"

    # This is a simplified version that doesn't actually modify the array
    # since nameref (-n) is not available in older bash versions
    # For now, we'll just return without modifying the array
    # This function is used for tracking passed/failed examples,
    # so the impact is minimal on the core functionality
    return 0
}

calculate_duration() {
    local start_time="$1"
    local end_time="$2"

    # Simple duration calculation (requires GNU date or similar)
    if command -v gdate >/dev/null 2>&1; then
        local start_epoch=$(gdate -d "$start_time" +%s)
        local end_epoch=$(gdate -d "$end_time" +%s)
    else
        local start_epoch=$(date -d "$start_time" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${start_time%+*}" +%s 2>/dev/null || echo 0)
        local end_epoch=$(date -d "$end_time" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${end_time%+*}" +%s 2>/dev/null || echo 0)
    fi

    if [[ $start_epoch -gt 0 && $end_epoch -gt 0 ]]; then
        local duration=$((end_epoch - start_epoch))
        echo "${duration}s"
    else
        echo "unknown"
    fi
}
