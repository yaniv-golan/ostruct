#!/usr/bin/env bash
# read_file.sh - File reading tool implementation
#
# Usage: read_file.sh <path>
# Returns: File contents

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="read_file"
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB_DIR="$AGENT_DIR/lib"

# Load dependencies
# shellcheck source=/dev/null
source "$LIB_DIR/tool_validation.sh"

# Setup cleanup
setup_tool_cleanup "$TOOL_NAME"

# Main execution function
main() {
    local path="$1"

    # Validate required parameters
    if [[ -z "$path" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'path' is missing or empty"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "path: $path"

    # Use safe_path from path_utils.sh
    local safe_file
    if ! safe_file=$(safe_path "$path"); then
        format_error_json "$TOOL_NAME" "path_validation_failed" "Invalid file path: $path"
        return 1
    fi

    # Validate file exists and is readable
    if ! validate_file_exists "$TOOL_NAME" "$safe_file" "path"; then
        return 1
    fi

    # Validate file size
    if ! validate_file_size "$TOOL_NAME" "$safe_file" "$FILE_SIZE_LIMIT" "path"; then
        return 1
    fi

    # Read file contents
    if ! cat "$safe_file"; then
        format_error_json "$TOOL_NAME" "read_failed" "Failed to read file: $path"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "success" "file read successfully"
    return 0
}

# Parameter validation
if [[ $# -lt 1 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <path>"
    exit 1
fi

# Execute main function
main "$@"
