#!/usr/bin/env bash
# Path utilities for agent scripts.
#
# Provides:
#   FILE_SIZE_LIMIT          – max bytes for normal file operations (default 32 KiB)
#   DOWNLOAD_SIZE_LIMIT      – max bytes for downloads (default 10 MiB)
#   file_size <path>         – echo size in bytes (cross-platform)
#   safe_path  <path>        – resolve path inside SANDBOX_PATH and echo result
#
# Requirements:
#   • Caller must export SANDBOX_PATH (absolute sandbox directory)
#   • Optionally exports log_error / error_exit for logging; otherwise prints to stderr.
#
# Guard against accidental execution
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "path_utils.sh: source this file, do not execute" >&2
    exit 1
fi

readonly FILE_SIZE_LIMIT=$((32 * 1024))           # 32 KiB
readonly DOWNLOAD_SIZE_LIMIT=$((10 * 1024 * 1024)) # 10 MiB

# ----------------------------------------------------------------------------
# file_size – portable stat wrapper (GNU / BSD)
# ----------------------------------------------------------------------------
file_size() {
    local _f="$1"
    if [[ ! -e "$_f" ]]; then
        echo 0
        return 1
    fi
    if stat -c%s "$_f" >/dev/null 2>&1; then
        stat -c%s "$_f"
    else
        stat -f%z "$_f"
    fi
}
export -f file_size

# ----------------------------------------------------------------------------
# safe_path – resolve path relative to sandbox and forbid escapes
# ----------------------------------------------------------------------------
# Usage: safe_path <input_path> ; echoes resolved path or exits 1.
# Relies on global SANDBOX_PATH; if unset → error.
# ----------------------------------------------------------------------------
_safe_path_error() {
    local msg="$1";
    if declare -F log_error >/dev/null; then
        log_error "$msg"
    fi
    echo "$msg" >&2
}

safe_path() {
    local input_path="$1"
    local sandbox="$SANDBOX_PATH"
    if [[ -z "$sandbox" ]]; then
        _safe_path_error "safe_path: SANDBOX_PATH not set"
        return 1
    fi

    # Prepend sandbox for relative paths
    if [[ "$input_path" != /* ]]; then
        input_path="$sandbox/$input_path"
    fi

    local resolved
    if command -v realpath >/dev/null 2>&1; then
        resolved=$(realpath -m "$input_path" 2>/dev/null || true)
        [[ -z "$resolved" ]] && resolved=$(realpath "$input_path" 2>/dev/null || true)
    else
        resolved=$(readlink -f "$input_path" 2>/dev/null || true)
    fi

    [[ -z "$resolved" ]] && resolved="$input_path"

    if [[ "$resolved" != "$sandbox"* ]]; then
        _safe_path_error "Path escape attempt: $input_path -> $resolved"
        return 1
    fi

    echo "$resolved"
}
export -f safe_path
