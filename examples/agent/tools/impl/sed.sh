#!/usr/bin/env bash
# sed.sh - Line extraction tool implementation
#
# Usage: sed.sh <expression> <file>
# Returns: Extracted lines

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="sed"
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB_DIR="$AGENT_DIR/lib"

# Load dependencies
# shellcheck source=/dev/null
source "$LIB_DIR/tool_validation.sh"

# Setup cleanup
setup_tool_cleanup "$TOOL_NAME"

# Main execution function
main() {
    local expression="$1"
    local file="$2"

    # Validate required parameters
    if [[ -z "$expression" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'expression' is missing or empty"
        return 1
    fi
    if [[ -z "$file" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'file' is missing or empty"
        return 1
    fi

    # Validate expression is not empty
    if [[ -z "$expression" ]]; then
        format_error_json "$TOOL_NAME" "empty_expression" "Sed expression cannot be empty"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "expression: $expression, file: $file"

    # Use safe_path from path_utils.sh
    local safe_file
    if ! safe_file=$(safe_path "$file"); then
        format_error_json "$TOOL_NAME" "path_validation_failed" "Invalid file path: $file"
        return 1
    fi

    # Validate file exists and is readable
    if ! validate_file_exists "$TOOL_NAME" "$safe_file" "file"; then
        return 1
    fi

    # Validate file size
    if ! validate_file_size "$TOOL_NAME" "$safe_file" "$FILE_SIZE_LIMIT" "file"; then
        return 1
    fi

    # Execute sed with timeout and output limit (read-only mode with -n)
    if ! timeout 30s sed -n "$expression" "$safe_file" 2>&1 | head -c "$FILE_SIZE_LIMIT"; then
        local exit_code=$?
        case $exit_code in
            124)
                format_error_json "$TOOL_NAME" "timeout" "Operation timed out after 30 seconds"
                ;;
            1)
                format_error_json "$TOOL_NAME" "invalid_expression" "Invalid sed expression: $expression"
                ;;
            2)
                format_error_json "$TOOL_NAME" "file_error" "Error reading file: $file"
                ;;
            *)
                format_error_json "$TOOL_NAME" "execution_failed" "sed execution failed with exit code $exit_code"
                ;;
        esac
        log_tool_operation "$TOOL_NAME" "execute" "error" "exit_code: $exit_code"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "success" "line extraction completed"
    return 0
}

# Parameter validation
if [[ $# -lt 2 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <expression> <file>"
    exit 1
fi

# Execute main function
main "$@"
