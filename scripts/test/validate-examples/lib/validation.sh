#!/bin/bash
# Validation library - validates command outputs and determines success/failure

# Validate command output based on exit code, stdout, and stderr
validate_command_output() {
    local exit_code="$1"
    local stdout_content="$2"
    local stderr_content="$3"
    local phase="$4"  # "dry-run" or "live"

    vlog "DEBUG" "Validating $phase output: exit_code=$exit_code"

    # Check exit code first
    if [[ $exit_code -ne 0 ]]; then
        vlog "DEBUG" "Command failed with exit code: $exit_code"
        return_validation_result "FAILED"
        return
    fi

    # Check for error indicators in stderr
    if contains_error_indicators "$stderr_content"; then
        vlog "DEBUG" "Error indicators found in stderr"
        return_validation_result "FAILED"
        return
    fi

    # Phase-specific validation
    case "$phase" in
        "dry-run")
            validate_dry_run_output "$stdout_content" "$stderr_content"
            ;;
        "live")
            validate_live_output "$stdout_content" "$stderr_content"
            ;;
        *)
            vlog "ERROR" "Unknown validation phase: $phase"
            return_validation_result "FAILED"
            ;;
    esac
}

# Validate dry-run specific output
validate_dry_run_output() {
    local stdout_content="$1"
    local stderr_content="$2"

    # Dry-run should show cost estimates and validation messages
    local has_cost_info=false
    local has_validation_info=false

    # Check for cost estimation patterns
    if echo "$stdout_content" | grep -qi -E "(cost|token|price|\$[0-9])" || \
       echo "$stderr_content" | grep -qi -E "(cost|token|price|\$[0-9])"; then
        has_cost_info=true
        vlog "DEBUG" "Found cost information in dry-run output"
    fi

    # Check for validation/processing patterns
    if echo "$stdout_content" | grep -qi -E "(processing|validating|template|schema|dry.?run)" || \
       echo "$stderr_content" | grep -qi -E "(processing|validating|template|schema|dry.?run)"; then
        has_validation_info=true
        vlog "DEBUG" "Found validation information in dry-run output"
    fi

    # Dry-run should not generate actual API calls
    if echo "$stdout_content" | grep -qi -E "(api.?call|openai|response|completion)" && \
       ! echo "$stdout_content" | grep -qi "dry.?run"; then
        vlog "WARN" "Dry-run appears to have made actual API calls"
    fi

    # For dry-run, we're more lenient - just need successful exit code and no errors
    return_validation_result "SUCCESS"
}

# Validate live execution output
validate_live_output() {
    local stdout_content="$1"
    local stderr_content="$2"

    # Live execution should show actual results
    local has_meaningful_output=false
    local has_structured_output=false

    # Check for meaningful output (not just empty or minimal)
    if [[ -n "$stdout_content" ]] && [[ ${#stdout_content} -gt 10 ]]; then
        has_meaningful_output=true
        vlog "DEBUG" "Found meaningful output in live execution"
    fi

    # Check for structured output (JSON, YAML, etc.)
    if echo "$stdout_content" | grep -q -E '^\s*\{.*\}\s*$' || \
       echo "$stdout_content" | jq . >/dev/null 2>&1; then
        has_structured_output=true
        vlog "DEBUG" "Found structured JSON output"
    elif echo "$stdout_content" | grep -qi -E "(---|\w+:)" && \
         echo "$stdout_content" | grep -v -E "^[[:space:]]*#"; then
        has_structured_output=true
        vlog "DEBUG" "Found structured YAML-like output"
    fi

    # Check for API success indicators
    local has_api_success=false
    if echo "$stdout_content" | grep -qi -E "(generated|completed|success)" || \
       echo "$stderr_content" | grep -qi -E "(generated|completed|success)"; then
        has_api_success=true
        vlog "DEBUG" "Found API success indicators"
    fi

    # Live execution validation is stricter
    if [[ "$has_meaningful_output" == "true" ]]; then
        return_validation_result "SUCCESS"
    else
        vlog "DEBUG" "Live execution produced minimal or no output"
        return_validation_result "FAILED"
    fi
}

# Check if content contains error indicators
contains_error_indicators() {
    local content="$1"

    # Common error patterns
    local error_patterns=(
        "error:"
        "ERROR:"
        "Error:"
        "exception"
        "Exception"
        "EXCEPTION"
        "failed"
        "Failed"
        "FAILED"
        "invalid"
        "Invalid"
        "INVALID"
        "not found"
        "Not found"
        "NOT FOUND"
        "permission denied"
        "Permission denied"
        "PERMISSION DENIED"
        "access denied"
        "Access denied"
        "ACCESS DENIED"
        "timeout"
        "Timeout"
        "TIMEOUT"
        "connection refused"
        "Connection refused"
        "CONNECTION REFUSED"
        "authentication failed"
        "Authentication failed"
        "AUTHENTICATION FAILED"
        "api key"
        "API key"
        "API KEY"
        "unauthorized"
        "Unauthorized"
        "UNAUTHORIZED"
        "forbidden"
        "Forbidden"
        "FORBIDDEN"
        "bad request"
        "Bad request"
        "BAD REQUEST"
        "internal server error"
        "Internal server error"
        "INTERNAL SERVER ERROR"
        "service unavailable"
        "Service unavailable"
        "SERVICE UNAVAILABLE"
        "rate limit"
        "Rate limit"
        "RATE LIMIT"
        "quota exceeded"
        "Quota exceeded"
        "QUOTA EXCEEDED"
        "traceback"
        "Traceback"
        "TRACEBACK"
        "stack trace"
        "Stack trace"
        "STACK TRACE"
    )

    for pattern in "${error_patterns[@]}"; do
        if echo "$content" | grep -q "$pattern"; then
            vlog "DEBUG" "Found error indicator: $pattern"
            return 0
        fi
    done

    return 1
}

# Check if output indicates API key issues
has_api_key_issues() {
    local content="$1"

    local api_key_patterns=(
        "api.?key.*missing"
        "api.?key.*not.*found"
        "api.?key.*invalid"
        "api.?key.*required"
        "authentication.*failed"
        "unauthorized"
        "401"
        "403"
        "OPENAI_API_KEY"
        "ANTHROPIC_API_KEY"
        "PERPLEXITY_API_KEY"
    )

    for pattern in "${api_key_patterns[@]}"; do
        if echo "$content" | grep -qi "$pattern"; then
            return 0
        fi
    done

    return 1
}

# Check if output indicates model availability issues
has_model_issues() {
    local content="$1"

    local model_patterns=(
        "model.*not.*found"
        "model.*not.*available"
        "model.*not.*supported"
        "invalid.*model"
        "unknown.*model"
        "model.*does.*not.*exist"
    )

    for pattern in "${model_patterns[@]}"; do
        if echo "$content" | grep -qi "$pattern"; then
            return 0
        fi
    done

    return 1
}

# Check if output indicates file/dependency issues
has_dependency_issues() {
    local content="$1"

    local dependency_patterns=(
        "file.*not.*found"
        "no.*such.*file"
        "cannot.*find.*file"
        "missing.*file"
        "template.*not.*found"
        "schema.*not.*found"
        "directory.*not.*found"
        "no.*such.*directory"
    )

    for pattern in "${dependency_patterns[@]}"; do
        if echo "$content" | grep -qi "$pattern"; then
            return 0
        fi
    done

    return 1
}

# Categorize failure type based on output
categorize_failure() {
    local stdout_content="$1"
    local stderr_content="$2"
    local all_content="$stdout_content $stderr_content"

    if has_api_key_issues "$all_content"; then
        echo "API_KEY_MISSING"
    elif has_model_issues "$all_content"; then
        echo "MODEL_UNAVAILABLE"
    elif has_dependency_issues "$all_content"; then
        echo "MISSING_DEPENDENCIES"
    elif contains_error_indicators "$all_content"; then
        echo "EXECUTION_ERROR"
    else
        echo "UNKNOWN_FAILURE"
    fi
}

# Return validation result (helper function)
return_validation_result() {
    echo "$1"
}
