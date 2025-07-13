#!/usr/bin/env bash
# download_file.sh - File download tool implementation
#
# Usage: download_file.sh <url> <path>
# Returns: Success message with download info

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="download_file"
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB_DIR="$AGENT_DIR/lib"

# Load dependencies
# shellcheck source=/dev/null
source "$LIB_DIR/tool_validation.sh"

# Setup cleanup
setup_tool_cleanup "$TOOL_NAME"

# Main execution function
main() {
    local url="$1"
    local path="$2"

    # Validate required parameters
    if [[ -z "$url" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'url' is missing or empty"
        return 1
    fi
    if [[ -z "$path" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'path' is missing or empty"
        return 1
    fi

    # Validate URL format and safety
    if ! validate_url "$TOOL_NAME" "$url" "url"; then
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "url: $url, path: $path"

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

    # Download file with curl
    if ! curl -s -L --max-filesize "$DOWNLOAD_SIZE_LIMIT" -o "$safe_file" "$url"; then
        local exit_code=$?
        case $exit_code in
            3)
                format_error_json "$TOOL_NAME" "invalid_url" "Invalid URL format: $url"
                ;;
            6)
                format_error_json "$TOOL_NAME" "dns_resolution_failed" "Could not resolve host: $url"
                ;;
            7)
                format_error_json "$TOOL_NAME" "connection_failed" "Failed to connect to host: $url"
                ;;
            22)
                format_error_json "$TOOL_NAME" "http_error" "HTTP error occurred (4xx/5xx status code)"
                ;;
            23)
                format_error_json "$TOOL_NAME" "write_error" "Error writing downloaded data to file"
                ;;
            28)
                format_error_json "$TOOL_NAME" "timeout" "Operation timed out"
                ;;
            35)
                format_error_json "$TOOL_NAME" "ssl_error" "SSL/TLS handshake failed"
                ;;
            63)
                format_error_json "$TOOL_NAME" "file_too_large" "File exceeds maximum download size limit"
                ;;
            *)
                format_error_json "$TOOL_NAME" "download_failed" "Download failed with exit code $exit_code"
                ;;
        esac
        log_tool_operation "$TOOL_NAME" "execute" "error" "exit_code: $exit_code"
        return 1
    fi

    # Verify file was created and get its size
    if [[ -f "$safe_file" ]]; then
        local actual_size
        actual_size=$(file_size "$safe_file")

        # Double-check size limit
        if (( actual_size > DOWNLOAD_SIZE_LIMIT )); then
            rm -f "$safe_file"
            format_error_json "$TOOL_NAME" "file_too_large" "Downloaded file exceeds size limit: $actual_size bytes > $DOWNLOAD_SIZE_LIMIT bytes"
            return 1
        fi

        echo "Successfully downloaded $actual_size bytes to $path"
        log_tool_operation "$TOOL_NAME" "execute" "success" "downloaded $actual_size bytes to $path"
        return 0
    else
        format_error_json "$TOOL_NAME" "download_failed" "Download failed - no file created"
        return 1
    fi
}

# Parameter validation
if [[ $# -lt 2 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <url> <path>"
    exit 1
fi

# Execute main function
main "$@"
