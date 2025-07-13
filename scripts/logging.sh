#!/usr/bin/env bash
# Modern logging wrapper for ostruct examples
# Replaces log4sh with shared simple_logging.sh for better reliability and strict mode compatibility

# ── Get script directory for relative paths ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# ── Configuration ──
LOG_LEVEL="${LOG_LEVEL:-INFO}"
LOG_DIR="${LOG_DIR:-logs}"

# ── Source simple_logging.sh ──
SIMPLE_LOGGING_PATH="$SCRIPT_DIR/../lib/simple_logging.sh"
if [[ -f "$SIMPLE_LOGGING_PATH" ]]; then
    # Set up log file before sourcing
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"
    export LOG_FILE
    export LOG_LEVEL
    export LOG_COLORS="${LOG_COLORS:-auto}"

    # Enable strict mode after environment setup
    set -euo pipefail
    IFS=$'\n\t'

    source "$SIMPLE_LOGGING_PATH"
else
    echo "❌ simple_logging.sh not found at $SIMPLE_LOGGING_PATH" >&2
    echo "Available paths:" >&2
    find "$SCRIPT_DIR/.." -name "simple_logging.sh" -type f 2>/dev/null || echo "No simple_logging.sh found" >&2
    exit 1
fi

# ── Backward compatibility aliases for log4sh API ──
logger_error() { log_error "$@"; }
logger_warn() { log_warn "$@"; }
logger_info() { log_info "$@"; }
logger_debug() { log_debug "$@"; }

# ── Enhanced utility functions ──
log_start() {
    local script_name="${1:-$(basename "$0")}"
    log_info "Starting $script_name"
    log_info "Log file: $LOG_FILE"
    log_info "Log level: $LOG_LEVEL"
}

log_finish() {
    local script_name="${1:-$(basename "$0")}"
    local exit_code="${2:-0}"
    if [[ "$exit_code" -eq 0 ]]; then
        log_info "Finished $script_name successfully at $(date)"
    else
        log_error "Finished $script_name with exit code $exit_code at $(date)"
    fi
}

log_command() {
    local description="$1"
    shift
    log_info "Running: $description"
    log_debug "Command: $*"

    # Create a temporary file for command output
    local temp_output=$(mktemp)

    if "$@" > "$temp_output" 2>&1; then
        # Command succeeded - log output at debug level
        while IFS= read -r line; do
            log_debug "  $line"
        done < "$temp_output"
        log_info "✅ $description completed"
        rm -f "$temp_output"
        return 0
    else
        local exit_code=$?
        # Command failed - log output at error level
        while IFS= read -r line; do
            log_error "  $line"
        done < "$temp_output"
        log_error "❌ $description failed with exit code $exit_code"
        rm -f "$temp_output"
        return $exit_code
    fi
}

# ── Additional compatibility functions for log4sh migration ──
logger_setLevel() {
    set_log_level "$1"
}

# Stub functions for log4sh appender functions (no-op for compatibility)
logger_addAppender() { :; }
appender_setType() { :; }
appender_setLayout() { :; }
appender_setPattern() { :; }
appender_activateOptions() { :; }
appender_file_setFile() { :; }
appender_setLevel() { :; }
log4sh_resetConfiguration() { :; }

# ── Export log file path for other scripts ──
export LOG_FILE

# ── Log successful initialization ──
log_debug "Logging system initialized with simple_logging.sh"
log_debug "Log directory: $LOG_DIR"
log_debug "Log file: $LOG_FILE"
