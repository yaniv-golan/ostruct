#!/usr/bin/env bash
# write_file.sh - File writing tool implementation
#
# Usage: write_file.sh <path> <content>
# Returns: Success message with file info

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="write_file"
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
    local content="$2"

    # Validate required parameters
    if [[ -z "$path" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'path' is missing or empty"
        return 1
    fi
    if [[ -z "$content" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'content' is missing or empty"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "path: $path, content_length: ${#content}"

    # Validate content size
    if (( ${#content} > FILE_SIZE_LIMIT )); then
        format_error_json "$TOOL_NAME" "content_too_large" "Content too large: ${#content} bytes > $FILE_SIZE_LIMIT bytes"
        return 1
    fi

    # Use safe_path from path_utils.sh
    local safe_file
    if ! safe_file=$(safe_path "$path"); then
        format_error_json "$TOOL_NAME" "path_validation_failed" "Invalid file path: $path"
        return 1
    fi

    # Validate file/directory is writable
    if ! validate_file_writable "$TOOL_NAME" "$safe_file" "path"; then
        return 1
    fi

    # Create directory if it doesn't exist
    local dir_path
    dir_path="$(dirname "$safe_file")"
    if [[ ! -d "$dir_path" ]]; then
        if ! mkdir -p "$dir_path"; then
            format_error_json "$TOOL_NAME" "directory_creation_failed" "Failed to create directory: $dir_path"
            return 1
        fi
    fi

    # Write content to file
    if ! echo "$content" > "$safe_file"; then
        format_error_json "$TOOL_NAME" "write_failed" "Failed to write to file: $path"
        return 1
    fi

    # Update temporal constraints if helper is available
    if declare -F update_temporal_constraints >/dev/null; then
        update_temporal_constraints "file_created" "$path"
    fi

    local bytes_written=${#content}
    echo "Successfully wrote $bytes_written bytes to $path"
    log_tool_operation "$TOOL_NAME" "execute" "success" "wrote $bytes_written bytes to $path"
    return 0
}

# Parameter validation
if [[ $# -lt 2 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <path> <content>"
    exit 1
fi

# Execute main function
main "$@"
