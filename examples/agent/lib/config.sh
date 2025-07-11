#!/usr/bin/env bash
# config.sh – centralised configuration constants for agent scripts.
#
# Source this file to populate sensible defaults.  Each constant can be
# overridden by exporting the variable *before* sourcing this file.
# Guard against accidental execution
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "config.sh: source this file, do not execute" >&2
  exit 1
fi

# ----------------------------
# File-handling limits
# ----------------------------
: "${FILE_SIZE_LIMIT:=$((32 * 1024))}"           # 32 KiB
: "${DOWNLOAD_SIZE_LIMIT:=$((10 * 1024 * 1024))}" # 10 MiB

# ----------------------------
# Runner behaviour
# ----------------------------
: "${MAX_TURNS:=10}"
: "${MAX_OSTRUCT_CALLS:=24}"
: "${WORKDIR:=workdir}"

# ----------------------------
# Retry defaults (used by with_retry/ostruct_call)
# ----------------------------
: "${RETRY_ATTEMPTS:=3}"
# Space-separated delay list (seconds) parsed by caller
: "${RETRY_DELAYS:='1 3 7'}"

# ----------------------------
# Export and lock immutables
# ----------------------------
readonly FILE_SIZE_LIMIT DOWNLOAD_SIZE_LIMIT MAX_TURNS MAX_OSTRUCT_CALLS WORKDIR
export FILE_SIZE_LIMIT DOWNLOAD_SIZE_LIMIT MAX_TURNS MAX_OSTRUCT_CALLS WORKDIR \
       RETRY_ATTEMPTS RETRY_DELAYS
