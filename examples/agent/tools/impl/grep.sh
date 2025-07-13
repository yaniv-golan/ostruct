#!/usr/bin/env bash
# grep.sh - Pattern search tool implementation
#
# Usage: grep.sh <pattern> <file>
# Returns: Search results with line numbers

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="grep"
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB_DIR="$AGENT_DIR/lib"

# Load dependencies
# shellcheck source=/dev/null
source "$LIB_DIR/tool_validation.sh"

# Setup cleanup
setup_tool_cleanup "$TOOL_NAME"

# Main execution function
main() {
    local pattern="$1"
    local file="$2"

    # Validate required parameters manually
    if [[ -z "$pattern" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'pattern' is missing or empty"
        return 1
    fi
    if [[ -z "$file" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'file' is missing or empty"
        return 1
    fi

    # Validate pattern is not empty
    if [[ -z "$pattern" ]]; then
        format_error_json "$TOOL_NAME" "empty_pattern" "Search pattern cannot be empty"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "pattern: $pattern, file: $file"

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

    # Parse pattern for options (handle patterns starting with -)
    local -a opts=()
    local search_pattern="$pattern"

    # If pattern starts with -, treat it as options + pattern
    if [[ "$pattern" == -* ]]; then
        # Split pattern into parts
        local -a parts
        IFS=' ' read -ra parts <<< "$pattern"

        # Collect options until we find the actual pattern
        for part in "${parts[@]}"; do
            if [[ "$part" == -* ]]; then
                opts+=("$part")
            else
                search_pattern="$part"
                break
            fi
        done
    fi

    # Execute grep with timeout and output limit
    if ! timeout 30s grep -n "${opts[@]}" "$search_pattern" "$safe_file" 2>&1 | head -c "$FILE_SIZE_LIMIT"; then
        local exit_code=$?
        case $exit_code in
            124)
                format_error_json "$TOOL_NAME" "timeout" "Operation timed out after 30 seconds"
                ;;
            1)
                # grep returns 1 when no matches found - this is normal
                echo "No matches found for pattern: $search_pattern"
                log_tool_operation "$TOOL_NAME" "execute" "success" "no matches found"
                return 0
                ;;
            2)
                format_error_json "$TOOL_NAME" "invalid_pattern" "Invalid search pattern: $search_pattern"
                ;;
            *)
                format_error_json "$TOOL_NAME" "execution_failed" "grep execution failed with exit code $exit_code"
                ;;
        esac

        if [[ $exit_code -ne 1 ]]; then
            log_tool_operation "$TOOL_NAME" "execute" "error" "exit_code: $exit_code"
            return 1
        fi
    fi

    log_tool_operation "$TOOL_NAME" "execute" "success" "pattern search completed"
    return 0
}

# Parameter validation
if [[ $# -lt 2 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <pattern> <file>"
    exit 1
fi

# Execute main function
main "$@"
