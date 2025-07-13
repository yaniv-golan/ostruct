#!/usr/bin/env bash
# jq.sh - JSON filtering and transformation tool implementation
#
# Usage: jq.sh <filter> [input_file]
# Returns: JSON output or error

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="jq"
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB_DIR="$AGENT_DIR/lib"

# Load dependencies
# shellcheck source=/dev/null
source "$LIB_DIR/tool_validation.sh"

# Setup cleanup
setup_tool_cleanup "$TOOL_NAME"

# Main execution function
main() {
    local filter="$1"
    local input_file="${2:-}"

    # Validate required parameters
    if [[ -z "$filter" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'filter' is missing or empty"
        return 1
    fi

    # Validate filter is not empty
    if [[ -z "$filter" ]]; then
        format_error_json "$TOOL_NAME" "empty_filter" "Filter expression cannot be empty"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "filter: $filter, input: ${input_file:-stdin}"

    # Handle input file validation if provided
    if [[ -n "$input_file" ]]; then
        # Use safe_path from path_utils.sh
        local safe_input
        if ! safe_input=$(safe_path "$input_file"); then
            format_error_json "$TOOL_NAME" "path_validation_failed" "Invalid input file path: $input_file"
            return 1
        fi

        # Validate file exists and is readable
        if ! validate_file_exists "$TOOL_NAME" "$safe_input" "input"; then
            return 1
        fi

        # Validate file size
        if ! validate_file_size "$TOOL_NAME" "$safe_input" "$FILE_SIZE_LIMIT" "input"; then
            return 1
        fi

        # Execute jq with input file
        if ! timeout 30s jq "$filter" "$safe_input" 2>&1 | head -c "$FILE_SIZE_LIMIT"; then
            local exit_code=$?
            case $exit_code in
                124)
                    format_error_json "$TOOL_NAME" "timeout" "Operation timed out after 30 seconds"
                    ;;
                4)
                    format_error_json "$TOOL_NAME" "null_input" "Input is null or empty"
                    ;;
                5)
                    format_error_json "$TOOL_NAME" "invalid_filter" "Invalid jq filter expression: $filter"
                    ;;
                *)
                    format_error_json "$TOOL_NAME" "execution_failed" "jq execution failed with exit code $exit_code"
                    ;;
            esac
            log_tool_operation "$TOOL_NAME" "execute" "error" "exit_code: $exit_code"
            return 1
        fi
    else
        # Execute jq with stdin
        if ! timeout 30s jq "$filter" 2>&1 | head -c "$FILE_SIZE_LIMIT"; then
            local exit_code=$?
            case $exit_code in
                124)
                    format_error_json "$TOOL_NAME" "timeout" "Operation timed out after 30 seconds"
                    ;;
                4)
                    format_error_json "$TOOL_NAME" "null_input" "Input is null or empty"
                    ;;
                5)
                    format_error_json "$TOOL_NAME" "invalid_filter" "Invalid jq filter expression: $filter"
                    ;;
                *)
                    format_error_json "$TOOL_NAME" "execution_failed" "jq execution failed with exit code $exit_code"
                    ;;
            esac
            log_tool_operation "$TOOL_NAME" "execute" "error" "exit_code: $exit_code"
            return 1
        fi
    fi

    log_tool_operation "$TOOL_NAME" "execute" "success" "filter applied successfully"
    return 0
}

# Parameter validation
if [[ $# -lt 1 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <filter> [input_file]"
    exit 1
fi

# Execute main function
main "$@"
