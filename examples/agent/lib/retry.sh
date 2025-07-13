#!/usr/bin/env bash
# retry.sh – generic retry/back-off helper
#
# Usage: with_retry <max_attempts> <delay1> [delay2 delay3 ...] -- cmd arg1 arg2
# Example:   with_retry 3 1 3 7 -- curl -fsSL http://example.com
# • Executes the command; if it succeeds (exit 0) returns immediately.
# • On failure, sleeps for the corresponding delay and retries, up to max_attempts.
# • If delay list is shorter than attempts, the last delay is reused.
# • Returns non-zero (last exit code) if all attempts fail.
#
# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

# Guards
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "retry.sh: source this file, do not execute" >&2
  exit 1
fi

with_retry() {
    local max_attempts=$1; shift
    local -a delays=()
    # collect delays until we see '--'
    while [[ "$1" != "--" ]]; do
        delays+=("$1"); shift
    done
    shift  # remove --
    local -a cmd=("$@")
    if [[ ${#cmd[@]} -eq 0 ]]; then
        echo "with_retry: missing command" >&2
        return 2
    fi

    local attempt=1 exit_code=0 delay
    while [[ $attempt -le $max_attempts ]]; do
        "${cmd[@]}"
        exit_code=$?
        if [[ $exit_code -eq 0 ]]; then
            return 0
        fi
        if [[ $attempt -lt $max_attempts ]]; then
            local idx=$((attempt-1))
            delay=${delays[$idx]:-${delays[-1]:-1}}
            if declare -F log_warn >/dev/null; then
                log_warn "Attempt $attempt/$max_attempts failed; retrying in ${delay}s..."
            fi
            sleep "$delay"
        fi
        attempt=$((attempt+1))
    done
    return $exit_code
}
export -f with_retry
