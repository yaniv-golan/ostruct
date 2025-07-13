#!/usr/bin/env bash
# json_utils.sh – centralized, safe JSON builders for agent system
#
# Provides helper functions to build result objects without risking
# jq parse errors from unescaped control characters or invalid
# numeric literals.  All user / tool output is base64-encoded.
#
# Functions:
#   json_success OUTPUT [DURATION] – build success object
#   json_error   ERROR  [DURATION] – build error object
#
# The resulting schema is:
#   {
#     "success": <bool>,
#     "output_b64"|"error_b64": <base64 string>,
#     "duration": <number>
#   }
# Down-stream code can decode with: `printf %s "$output_b64" | base64 -d`.

set -euo pipefail
IFS=$'\n\t'

# Export DEBUG safeguards for set -u environments
export DEBUG=${DEBUG:-false}

# Ensure we are sourced, not executed directly
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "json_utils.sh: source this file, do not execute" >&2
    exit 1
fi

# ---------------- internal helpers ----------------------------
# Encode arbitrary text to a single-line base64 string (no newlines)
_to_b64() {
    local _text="$1"
    # macOS base64 lacks -w; pipe through tr to strip newlines
    printf '%s' "$_text" | base64 | tr -d '\n'
}

# Validate numeric input, default to 0 if invalid/empty
_validate_number() {
    local _num="${1:-}"
    if [[ "$_num" =~ ^[0-9]+$ ]]; then
        printf '%s' "$_num"
    else
        printf '0'
    fi
}

# ---------------- public API ----------------------------------
json_success() {
    local output="${1:-}"
    local duration="$(_validate_number "${2:-0}")"

    # Remove control chars for a safe inline preview copy
    local output_sanitized
    output_sanitized=$(printf '%s' "$output" | tr -d '\000-\037')
    jq -n \
        --arg output "$output_sanitized" \
        --arg output_b64 "$(_to_b64 "$output")" \
        --argjson duration "$duration" \
        '{"success": true, "output": $output, "output_b64": $output_b64, "duration": $duration}'
}

json_error() {
    local error_msg="${1:-Unknown error}"
    local duration="$(_validate_number "${2:-0}")"

    local err_sanitized
    err_sanitized=$(printf '%s' "$error_msg" | tr -d '\000-\037')
    jq -n \
        --arg error "$err_sanitized" \
        --arg error_b64 "$(_to_b64 "$error_msg")" \
        --argjson duration "$duration" \
        '{"success": false, "error": $error, "error_b64": $error_b64, "duration": $duration}'
}

# ---------------- validation specifics ------------------------
# format_validation_success TOOL MESSAGE [RESULT]
# Returns:
#   {
#     "success": true,
#     "message": <message>,
#     "tool": <tool>,
#     "timestamp": <iso8601>,
#     "result": <optional result>  # if provided
#   }
format_validation_success() {
    local tool="$1" message="$2" result="${3:-}"
    local timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    jq -n \
        --arg tool "$tool" \
        --arg message "$message" \
        --arg timestamp "$timestamp" \
        --arg result "$result" \
        '{"success": true, "message": $message, "tool": $tool, "timestamp": $timestamp} | if $result != "" then .result = $result else . end'
}

# format_validation_error TOOL CODE MESSAGE [ADDITIONAL_INFO]
# Returns:
#   {
#     "success": false,
#     "error": {
#       "code": <code>,
#       "message": <message>,
#       "tool": <tool>,
#       "timestamp": <iso8601>,
#       "additional_info": <optional info>
#     }
#   }
format_validation_error() {
    local tool="$1" code="$2" message="$3" info="${4:-}"
    local timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    jq -n \
        --arg tool "$tool" \
        --arg code "$code" \
        --arg message "$message" \
        --arg timestamp "$timestamp" \
        --arg info "$info" \
        '{"success": false, "error": {"code": $code, "message": $message, "tool": $tool, "timestamp": $timestamp}} | if $info != "" then .error.additional_info = $info else . end'
}

export -f json_success json_error format_validation_success format_validation_error
