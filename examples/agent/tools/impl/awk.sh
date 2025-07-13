#!/usr/bin/env bash
# awk.sh - Field and line processing tool implementation
#
# Usage: awk.sh <script> <file>
# Returns: Processed output

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="awk"
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB_DIR="$AGENT_DIR/lib"

# Load dependencies
# shellcheck source=/dev/null
source "$LIB_DIR/tool_validation.sh"

# Setup cleanup
setup_tool_cleanup "$TOOL_NAME"

# Main execution function
main() {
    local script="$1"
    local file="$2"

    # Validate required parameters
    if [[ -z "$script" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'script' is missing or empty"
        return 1
    fi
    if [[ -z "$file" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'file' is missing or empty"
        return 1
    fi

    # Validate script is not empty
    if [[ -z "$script" ]]; then
        format_error_json "$TOOL_NAME" "empty_script" "AWK script cannot be empty"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "script: $script, file: $file"

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

    # Execute awk with timeout and output limit
    if ! timeout 30s awk "$script" "$safe_file" 2>&1 | head -c "$FILE_SIZE_LIMIT"; then
        local exit_code=$?
        case $exit_code in
            124)
                format_error_json "$TOOL_NAME" "timeout" "Operation timed out after 30 seconds"
                ;;
            1)
                format_error_json "$TOOL_NAME" "invalid_script" "Invalid AWK script: $script"
                ;;
            2)
                format_error_json "$TOOL_NAME" "file_error" "Error reading file: $file"
                ;;
            *)
                format_error_json "$TOOL_NAME" "execution_failed" "awk execution failed with exit code $exit_code"
                ;;
        esac
        log_tool_operation "$TOOL_NAME" "execute" "error" "exit_code: $exit_code"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "success" "field processing completed"
    return 0
}

# Parameter validation
if [[ $# -lt 2 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <script> <file>"
    exit 1
fi

# Execute main function
main "$@"
