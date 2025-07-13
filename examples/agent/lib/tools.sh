#!/usr/bin/env bash
# tools.sh – execution adapters for sandbox tools.
#
# Depends on path_utils.sh for safe_path & file_size.

# Enable strict mode for reliability
set -euo pipefail
IFS=$'\n\t'

# Enable trace mode if DEBUG is set
if [[ "${DEBUG:-false}" == "true" ]]; then
    set -x
fi

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "tools.sh: source this file, do not execute" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/path_utils.sh"
# path_utils.sh already sources config.sh, so FILE_SIZE_LIMIT and DOWNLOAD_SIZE_LIMIT
# are available here.

# Get the tools implementation directory
TOOLS_IMPL_DIR="$(dirname "${LIB_DIR}")/tools/impl"

# Tool execution functions - now delegate to individual implementations
execute_jq() {
    local filter="$1"; local input_file="${2:-}"
    "$TOOLS_IMPL_DIR/jq.sh" "$filter" "$input_file"
}

execute_grep() {
    local pattern="$1" file="$2"
    "$TOOLS_IMPL_DIR/grep.sh" "$pattern" "$file"
}

execute_sed() {
    local expr="$1" file="$2"
    "$TOOLS_IMPL_DIR/sed.sh" "$expr" "$file"
}

execute_awk() {
    local script="$1" file="$2"
    "$TOOLS_IMPL_DIR/awk.sh" "$script" "$file"
}

execute_curl() {
    local url="$1"
    "$TOOLS_IMPL_DIR/curl.sh" "$url"
}

execute_write_file() {
    local path="$1" content="$2"
    "$TOOLS_IMPL_DIR/write_file.sh" "$path" "$content"
}

execute_append_file() {
    local path="$1" content="$2"
    "$TOOLS_IMPL_DIR/append_file.sh" "$path" "$content"
}

execute_text_replace() {
    local file="$1" search="$2" replace="$3"
    "$TOOLS_IMPL_DIR/text_replace.sh" "$file" "$search" "$replace"
}

execute_read_file() {
    local path="$1"
    "$TOOLS_IMPL_DIR/read_file.sh" "$path"
}

execute_download_file() {
    local url="$1" path="$2"
    "$TOOLS_IMPL_DIR/download_file.sh" "$url" "$path"
}

# Dispatcher

tool_exec() {
    local tool="$1"; shift
    case "$tool" in
        jq)            execute_jq "$@" ;;
        grep)          execute_grep "$@" ;;
        sed)           execute_sed "$@" ;;
        awk)           execute_awk "$@" ;;
        curl)          execute_curl "$@" ;;
        write_file)    execute_write_file "$@" ;;
        append_file)   execute_append_file "$@" ;;
        text_replace)  execute_text_replace "$@" ;;
        read_file)     execute_read_file "$@" ;;
        download_file) execute_download_file "$@" ;;
        *) echo "Error: Unknown tool $tool"; return 127 ;;
    esac
}
export -f tool_exec
