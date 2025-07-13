#!/usr/bin/env bash
# tool_validation.sh – common validation functions for tool implementations
#
# Provides standardized validation, error handling, and output formatting
# for all tool implementations in tools/impl/
#
# Functions:
#   validate_required_params    – check required parameters are present
#   validate_file_exists        – check file exists and is readable
#   validate_file_writable      – check file/directory is writable
#   validate_file_size          – check file size within limits
#   validate_url                – basic URL validation
#   format_error_json           – standardized JSON error output
#   format_success_json         – standardized JSON success output
#   log_tool_operation          – log tool execution with context

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Guard against accidental execution
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "tool_validation.sh: source this file, do not execute" >&2
    exit 1
fi

# Load dependencies
# shellcheck source=/dev/null
source "${LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/config.sh"
# shellcheck source=/dev/null
source "${LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/path_utils.sh"
# shellcheck source=/dev/null
source "${LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/simple_logging.sh"
# shellcheck source=/dev/null
source "${LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/json_utils.sh"

# -----------------------------------------------------------------------------
# Parameter validation
# -----------------------------------------------------------------------------

# Validate required parameters are present and non-empty
validate_required_params() {
    local tool_name="$1"
    shift
    local -a required_params=("$@")

    for param in "${required_params[@]}"; do
        # Use indirect expansion with default to avoid unbound variable error
        local param_value="${!param:-}"
        if [[ -z "$param_value" ]]; then
            format_error_json "$tool_name" "missing_parameter" "Required parameter '$param' is missing or empty"
            return 1
        fi
    done
    return 0
}

# Validate file exists and is readable
validate_file_exists() {
    local tool_name="$1"
    local file_path="$2"
    local param_name="${3:-file}"

    if [[ ! -f "$file_path" ]]; then
        format_error_json "$tool_name" "file_not_found" "File not found: $file_path (parameter: $param_name)"
        return 1
    fi

    if [[ ! -r "$file_path" ]]; then
        format_error_json "$tool_name" "file_not_readable" "File not readable: $file_path (parameter: $param_name)"
        return 1
    fi

    return 0
}

# Validate file/directory is writable
validate_file_writable() {
    local tool_name="$1"
    local file_path="$2"
    local param_name="${3:-path}"

    local dir_path
    if [[ -f "$file_path" ]]; then
        # File exists, check if writable
        if [[ ! -w "$file_path" ]]; then
            format_error_json "$tool_name" "file_not_writable" "File not writable: $file_path (parameter: $param_name)"
            return 1
        fi
    else
        # File doesn't exist, check if directory is writable
        dir_path="$(dirname "$file_path")"
        if [[ ! -d "$dir_path" ]]; then
            # Try to create directory
            if ! mkdir -p "$dir_path" 2>/dev/null; then
                format_error_json "$tool_name" "directory_not_creatable" "Cannot create directory: $dir_path (parameter: $param_name)"
                return 1
            fi
        fi

        if [[ ! -w "$dir_path" ]]; then
            format_error_json "$tool_name" "directory_not_writable" "Directory not writable: $dir_path (parameter: $param_name)"
            return 1
        fi
    fi

    return 0
}

# Validate file size within limits
validate_file_size() {
    local tool_name="$1"
    local file_path="$2"
    local max_size="$3"
    local param_name="${4:-file}"

    if [[ ! -f "$file_path" ]]; then
        format_error_json "$tool_name" "file_not_found" "File not found: $file_path (parameter: $param_name)"
        return 1
    fi

    local actual_size
    actual_size=$(file_size "$file_path")

    if [[ $actual_size -gt $max_size ]]; then
        format_error_json "$tool_name" "file_too_large" "File too large: $actual_size bytes > $max_size bytes (parameter: $param_name)"
        return 1
    fi

    return 0
}

# Basic URL validation
validate_url() {
    local tool_name="$1"
    local url="$2"
    local param_name="${3:-url}"

    # Basic URL pattern check
    if [[ ! "$url" =~ ^https?:// ]]; then
        format_error_json "$tool_name" "invalid_url" "Invalid URL format: $url (parameter: $param_name)"
        return 1
    fi

    # Check for potentially dangerous URLs
    if [[ "$url" =~ ^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.) ]]; then
        format_error_json "$tool_name" "unsafe_url" "Unsafe URL (internal/private address): $url (parameter: $param_name)"
        return 1
    fi

    return 0
}

# -----------------------------------------------------------------------------
# Output formatting
# -----------------------------------------------------------------------------

# Format standardized JSON error output
format_error_json() {
    local tool_name="$1"
    local error_code="$2"
    local error_message="$3"
    local additional_info="${4:-}"

    format_validation_error "$tool_name" "$error_code" "$error_message" "$additional_info"
}

# Format standardized JSON success output
format_success_json() {
    local tool_name="$1"
    local success_message="$2"
    local result_data="${3:-}"

    format_validation_success "$tool_name" "$success_message" "$result_data"
}

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

# Log tool operation with context
log_tool_operation() {
    local tool_name="$1"
    local operation="$2"
    local status="$3"
    local details="${4:-}"

    local log_message="Tool: $tool_name, Operation: $operation, Status: $status"
    if [[ -n "$details" ]]; then
        log_message="$log_message, Details: $details"
    fi

    case "$status" in
        "success")
            if declare -F log_info >/dev/null; then
                log_info "$log_message"
            fi
            ;;
        "error"|"failed")
            if declare -F log_error >/dev/null; then
                log_error "$log_message"
            fi
            ;;
        "warning")
            if declare -F log_warn >/dev/null; then
                log_warn "$log_message"
            fi
            ;;
        *)
            if declare -F log_debug >/dev/null; then
                log_debug "$log_message"
            fi
            ;;
    esac
}

# -----------------------------------------------------------------------------
# Exit trap for cleanup
# -----------------------------------------------------------------------------

# Set up cleanup trap for tools
setup_tool_cleanup() {
    local tool_name="$1"
    local cleanup_function="${2:-}"

    # Build the trap command so that `tool_name` is expanded **now** (while it is still in scope)
    local generic_cleanup="rm -f /tmp/tool_${tool_name}_*"

    if [[ -n "$cleanup_function" ]]; then
        # Combine the caller-provided cleanup with the generic cleanup in a single trap
        trap "${cleanup_function}; ${generic_cleanup}" EXIT
    else
        trap "${generic_cleanup}" EXIT
    fi
}

# Export all functions
export -f validate_required_params validate_file_exists validate_file_writable
export -f validate_file_size validate_url format_error_json format_success_json
export -f log_tool_operation setup_tool_cleanup
