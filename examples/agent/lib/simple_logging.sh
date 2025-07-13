#!/usr/bin/env bash
# simple_logging.sh - Modern logging library for ostruct agent
# Replaces log4sh with a minimal, strict-mode compatible implementation
#
# Environment Variables:
#   LOG_LEVEL    - Minimum log level (DEBUG, INFO, WARN, ERROR) [default: INFO]
#   LOG_FILE     - Log file path [default: none, stderr only]
#   LOG_COLORS   - Enable color output (true/false) [default: auto-detect]
#
# Functions:
#   log_debug, log_info, log_warn, log_error - Basic logging
#   log_start, log_finish, log_command - Process/command logging

# Guard against accidental execution
if [[ "${BASH_SOURCE[0]:-}" == "${0:-}" ]]; then
    echo "simple_logging.sh: source this file, do not execute" >&2
    exit 1
fi

# Enable strict mode for reliability (only if not already set)
if [[ ! "$-" =~ e ]]; then set -e; fi
if [[ ! "$-" =~ u ]]; then set -u; fi
if [[ ! "$-" =~ o.*pipefail ]]; then set -o pipefail; fi
IFS=$'\n\t'

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Log levels (higher number = more severe)
declare -A LOG_LEVELS=([DEBUG]=0 [INFO]=1 [WARN]=2 [ERROR]=3)

# Current log level
LOG_LEVEL=${LOG_LEVEL:-INFO}

# Log file (optional)
LOG_FILE=${LOG_FILE:-}

# Color support (auto-detect if not set)
if [[ -z "${LOG_COLORS:-}" ]]; then
    if [[ -t 2 ]]; then
        LOG_COLORS=true
    else
        LOG_COLORS=false
    fi
fi

# ANSI color codes
if [[ "$LOG_COLORS" == "true" ]]; then
    COLOR_DEBUG='\033[0;36m'    # Cyan
    COLOR_INFO='\033[0;32m'     # Green
    COLOR_WARN='\033[0;33m'     # Yellow
    COLOR_ERROR='\033[0;31m'    # Red
    COLOR_RESET='\033[0m'       # Reset
else
    COLOR_DEBUG=''
    COLOR_INFO=''
    COLOR_WARN=''
    COLOR_ERROR=''
    COLOR_RESET=''
fi

# Export color variables for child processes so that exported functions work correctly
export COLOR_DEBUG COLOR_INFO COLOR_WARN COLOR_ERROR COLOR_RESET

# -----------------------------------------------------------------------------
# Core logging functions
# -----------------------------------------------------------------------------

# Internal logging function
_log_at_level() {
    local level="$1"
    local message="$2"
    local color="$3"

    # Check if we should log at this level
    local level_num=${LOG_LEVELS[$level]:-1}
    local current_level_num=${LOG_LEVELS[$LOG_LEVEL]:-1}

    if [[ $level_num -lt $current_level_num ]]; then
        return 0
    fi

    # Format message
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local formatted_message="[${timestamp}] ${color}${level}${COLOR_RESET}: ${message}"

    # Output to stderr
    echo -e "$formatted_message" >&2

    # Output to log file if specified
    if [[ -n "$LOG_FILE" ]]; then
        # Strip colors for file output
        local file_message="[${timestamp}] ${level}: ${message}"
        echo "$file_message" >> "$LOG_FILE"
    fi
}

# Public logging functions
log_debug() {
    _log_at_level "DEBUG" "$*" "$COLOR_DEBUG"
}

log_info() {
    _log_at_level "INFO" "$*" "$COLOR_INFO"
}

log_warn() {
    _log_at_level "WARN" "$*" "$COLOR_WARN"
}

log_error() {
    _log_at_level "ERROR" "$*" "$COLOR_ERROR"
}

# -----------------------------------------------------------------------------
# Extended logging functions (for compatibility)
# -----------------------------------------------------------------------------

# Process start logging
log_start() {
    local process_name="$1"
    log_info "Starting $process_name"
}

# Process finish logging
log_finish() {
    local process_name="$1"
    local exit_code="${2:-0}"

    if [[ "$exit_code" -eq 0 ]]; then
        log_info "Finished $process_name successfully"
    else
        log_error "Finished $process_name with exit code $exit_code"
    fi
}

# Command logging
log_command() {
    local command="$1"
    log_debug "Executing: $command"
}

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

# Set log level dynamically
set_log_level() {
    local new_level="$1"

    if [[ -z "${LOG_LEVELS[$new_level]:-}" ]]; then
        log_error "Invalid log level: $new_level. Valid levels: ${!LOG_LEVELS[*]}"
        return 1
    fi

    LOG_LEVEL="$new_level"
    log_info "Log level set to $LOG_LEVEL"
}

# Check if a log level is enabled
is_log_level_enabled() {
    local level="$1"
    local level_num=${LOG_LEVELS[$level]:-1}
    local current_level_num=${LOG_LEVELS[$LOG_LEVEL]:-1}

    [[ $level_num -ge $current_level_num ]]
}

# Export all public functions
export -f log_debug log_info log_warn log_error
export -f log_start log_finish log_command
export -f set_log_level is_log_level_enabled
# Also export internal helper so that the exported log_* functions work in subshells
export -f _log_at_level
