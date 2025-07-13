#!/usr/bin/env bash
# curl.sh - HTTP download tool implementation
#
# Usage: curl.sh <url>
# Returns: Downloaded content

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Tool configuration
TOOL_NAME="curl"
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

    # Validate required parameters
    if [[ -z "$url" ]]; then
        format_error_json "$TOOL_NAME" "missing_parameter" "Required parameter 'url' is missing or empty"
        return 1
    fi

    # Validate URL format and safety
    if ! validate_url "$TOOL_NAME" "$url" "url"; then
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "starting" "url: $url"

    # Execute curl with timeout and size limit
    if ! timeout 60s curl -s -L --max-filesize "$DOWNLOAD_SIZE_LIMIT" "$url" 2>&1 | head -c "$DOWNLOAD_SIZE_LIMIT"; then
        local exit_code=$?
        case $exit_code in
            124)
                format_error_json "$TOOL_NAME" "timeout" "Operation timed out after 60 seconds"
                ;;
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
                format_error_json "$TOOL_NAME" "write_error" "Error writing received data"
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
                format_error_json "$TOOL_NAME" "execution_failed" "curl execution failed with exit code $exit_code"
                ;;
        esac
        log_tool_operation "$TOOL_NAME" "execute" "error" "exit_code: $exit_code"
        return 1
    fi

    log_tool_operation "$TOOL_NAME" "execute" "success" "download completed"
    return 0
}

# Parameter validation
if [[ $# -lt 1 ]]; then
    format_error_json "$TOOL_NAME" "missing_parameters" "Usage: $0 <url>"
    exit 1
fi

# Execute main function
main "$@"
