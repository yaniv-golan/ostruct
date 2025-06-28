#!/usr/bin/env bash
# log4sh wrapper for ostruct examples
# Provides enterprise-grade logging with consistent API

# ── Get script directory for relative paths ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Configuration ──
LOG_LEVEL="${LOG_LEVEL:-INFO}"
LOG_DIR="${LOG_DIR:-log}"

# ── Source log4sh with proper initialization ──
if [[ -f "$SCRIPT_DIR/third_party/log4sh" ]]; then
  # Prevent auto-config file loading
  export LOG4SH_CONFIGURATION='none'
  . "$SCRIPT_DIR/third_party/log4sh"
else
  echo "❌ log4sh not found at $SCRIPT_DIR/third_party/log4sh" >&2
  echo "Run: curl -sSLo scripts/third_party/log4sh 'https://raw.githubusercontent.com/kward/log4sh/master/lib/log4sh'" >&2
  exit 1
fi

# ── Initialize log4sh properly ──
log4sh_resetConfiguration                      # Reset to clean slate
logger_setLevel "$LOG_LEVEL"                   # Set global log level

# ── Configure file appender ──
logger_addAppender file
appender_setType file FileAppender
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"
appender_file_setFile file "$LOG_FILE"
appender_setLayout file PatternLayout
appender_setPattern file "%d{yyyy-MM-dd HH:mm:ss} [%p] %m%n"
appender_activateOptions file

# ── Configure stderr (console) appender ──
logger_addAppender stderr
appender_setType stderr FileAppender
appender_file_setFile stderr STDERR
appender_setLayout stderr PatternLayout
if [[ -t 2 ]]; then
  # Terminal output - cleaner format
  appender_setPattern stderr "%d{HH:mm:ss} %p %m%n"
else
  # Non-terminal output (CI/pipes) - include brackets for clarity
  appender_setPattern stderr "%d{HH:mm:ss} [%p] %m%n"
fi
appender_activateOptions stderr

# ── Public API (log4sh native functions) ──
# logger_error, logger_warn, logger_info, logger_debug are provided by log4sh

# ── Convenience aliases ──
log_error() { logger_error "$@"; }
log_warn() { logger_warn "$@"; }
log_info() { logger_info "$@"; }
log_debug() { logger_debug "$@"; }

# ── Utility functions ──
log_start() {
  local script_name="${1:-$(basename "$0")}"
  logger_info "Starting $script_name"
  logger_info "Log file: $LOG_FILE"
  logger_info "Log level: $LOG_LEVEL"
}

log_finish() {
  local script_name="${1:-$(basename "$0")}"
  logger_info "Finished $script_name at $(date)"
}

log_command() {
  local description="$1"
  shift
  logger_info "Running: $description"
  logger_debug "Command: $*"

  # Create a temporary file for command output
  local temp_output=$(mktemp)

  if "$@" > "$temp_output" 2>&1; then
    # Command succeeded - log output at debug level
    while IFS= read -r line; do
      logger_debug "  $line"
    done < "$temp_output"
    logger_info "✅ $description completed"
    rm -f "$temp_output"
    return 0
  else
    local exit_code=$?
    # Command failed - log output at error level
    while IFS= read -r line; do
      logger_error "  $line"
    done < "$temp_output"
    logger_error "❌ $description failed with exit code $exit_code"
    rm -f "$temp_output"
    return $exit_code
  fi
}

# ── Export log file path for other scripts ──
export LOG_FILE
