#!/usr/bin/env bash
# append_file.sh - File appending tool implementation
#
# Usage: append_file.sh <path> <content>
# Returns: Success message with file info

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="append_file"
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

    # Use safe_path from path_utils.sh
    local safe_file
    if ! safe_file=$(safe_path "$path"); then
        format_error_json "$TOOL_NAME" "path_validation_failed" "Invalid file path: $path"
        return 1
    fi

    # Check current file size if file exists
    local current_size=0
    if [[ -f "$safe_file" ]]; then
        current_size=$(file_size "$safe_file")
    fi

    # Validate total size would not exceed limit
    if (( current_size + ${#content} > FILE_SIZE_LIMIT )); then
        format_error_json "$TOOL_NAME" "file_too_large" "Total file size would exceed limit: $((current_size + ${#content})) bytes > $FILE_SIZE_LIMIT bytes"
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

    # Append content to file
    if ! echo "$content" >> "$safe_file"; then
        format_error_json "$TOOL_NAME" "append_failed" "Failed to append to file: $path"
        return 1
    fi

    # Update temporal constraints if helper is available and file was newly created
    if [[ $current_size -eq 0 ]] && declare -F update_temporal_constraints >/dev/null; then
        update_temporal_constraints "file_created" "$path"
    fi

    local bytes_appended=${#content}
    echo "Successfully appended $bytes_appended bytes to $path"
    log_tool_operation "$TOOL_NAME" "execute" "success" "appended $bytes_appended bytes to $path"
    return 0
}

# Parameter validation
if [[ $# -lt 2 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <path> <content>"
    exit 1
fi

# Execute main function
main "$@"
