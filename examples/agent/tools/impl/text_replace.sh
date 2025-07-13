#!/usr/bin/env bash
# text_replace.sh - Text replacement tool implementation
#
# Usage: text_replace.sh <file> <search> <replace>
# Returns: Success message with replacement count

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="text_replace"
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB_DIR="$AGENT_DIR/lib"

# Load dependencies
# shellcheck source=/dev/null
source "$LIB_DIR/tool_validation.sh"

# Setup cleanup
setup_tool_cleanup "$TOOL_NAME"

# Main execution function
main() {
    local file="$1"
    local search="$2"
    local replace="$3"

    # Validate required parameters
    if [[ -z "$file" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'file' is missing or empty"
        return 1
    fi
    if [[ -z "$search" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'search' is missing or empty"
        return 1
    fi
    if [[ -z "$replace" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'replace' is missing or empty"
        return 1
    fi

    # Validate search pattern is not empty
    if [[ -z "$search" ]]; then
        format_error_json "$TOOL_NAME" "empty_search" "Search pattern cannot be empty"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "file: $file, search: $search, replace: $replace"

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

    # Validate file is writable
    if ! validate_file_writable "$TOOL_NAME" "$safe_file" "file"; then
        return 1
    fi

    # Create temporary file for processing
    local tmp_file="${safe_file}.tmp"

    # Perform replacement using sed
    if ! sed "s/${search}/${replace}/g" "$safe_file" > "$tmp_file"; then
        rm -f "$tmp_file"
        format_error_json "$TOOL_NAME" "replacement_failed" "Failed to perform text replacement"
        return 1
    fi

    # Count replacements by comparing with original
    local hit_count
    if ! hit_count=$(grep -o "$replace" "$tmp_file" | wc -l); then
        hit_count=0
    fi

    # Validate replacement count doesn't exceed limit
    if (( hit_count > 1000 )); then
        rm -f "$tmp_file"
        format_error_json "$TOOL_NAME" "too_many_replacements" "Too many replacements: $hit_count > 1000"
        return 1
    fi

    # Replace original file with modified version
    if ! mv "$tmp_file" "$safe_file"; then
        rm -f "$tmp_file"
        format_error_json "$TOOL_NAME" "file_update_failed" "Failed to update file: $file"
        return 1
    fi

    echo "Successfully replaced $hit_count occurrences in $file"
    log_tool_operation "$TOOL_NAME" "execute" "success" "replaced $hit_count occurrences"
    return 0
}

# Parameter validation
if [[ $# -lt 3 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <file> <search> <replace>"
    exit 1
fi

# Execute main function
main "$@"
