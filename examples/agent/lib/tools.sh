#!/usr/bin/env bash
# tools.sh – execution adapters for sandbox tools.
#
# Depends on path_utils.sh for safe_path & file_size.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "tools.sh: source this file, do not execute" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/path_utils.sh"

execute_jq() {
    local filter="$1"; local input_file="${2:-}"
    log_debug "Executing jq filter: $filter"
    if [[ -n "$input_file" ]]; then
        local safe_input; safe_input=$(safe_path "$input_file") || return 1
        [[ ! -f "$safe_input" ]] && { echo "Error: Input file not found: $input_file"; return 1; }
        [[ $(file_size "$safe_input") -gt $FILE_SIZE_LIMIT ]] && { echo "Error: Input file too large"; return 1; }
        timeout 30s jq "$filter" "$safe_input" 2>&1 | head -c $FILE_SIZE_LIMIT
    else
        timeout 30s jq "$filter" 2>&1 | head -c $FILE_SIZE_LIMIT
    fi
}

execute_grep() {
    local pattern="$1" file="$2"
    local safe_file; safe_file=$(safe_path "$file") || return 1
    [[ ! -f "$safe_file" ]] && { echo "Error: File not found: $file"; return 1; }
    [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]] && { echo "Error: File too large"; return 1; }
    local -a opts=(); local search_pattern="$pattern"
    if [[ "$pattern" == -* ]]; then
        # shellcheck disable=SC2206
        local parts=( $pattern )
        for part in "${parts[@]}"; do [[ "$part" == -* ]] && opts+=("$part") || search_pattern="$part"; done
    fi
    timeout 30s grep -n "${opts[@]}" "$search_pattern" "$safe_file" 2>&1 | head -c $FILE_SIZE_LIMIT
}

execute_sed() {
    local expr="$1" file="$2"
    local safe_file; safe_file=$(safe_path "$file") || return 1
    [[ ! -f "$safe_file" ]] && { echo "Error: File not found: $file"; return 1; }
    [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]] && { echo "Error: File too large"; return 1; }
    timeout 30s sed -n "$expr" "$safe_file" 2>&1 | head -c $FILE_SIZE_LIMIT
}

execute_awk() {
    local script="$1" file="$2"
    local safe_file; safe_file=$(safe_path "$file") || return 1
    [[ ! -f "$safe_file" ]] && { echo "Error: File not found: $file"; return 1; }
    [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]] && { echo "Error: File too large"; return 1; }
    timeout 30s awk "$script" "$safe_file" 2>&1 | head -c $FILE_SIZE_LIMIT
}

execute_curl() {
    local url="$1"
    timeout 60s curl -s -L --max-filesize $DOWNLOAD_SIZE_LIMIT "$url" 2>&1 | head -c $DOWNLOAD_SIZE_LIMIT
}

execute_write_file() {
    local path="$1" content="$2"; local safe_file; safe_file=$(safe_path "$path") || return 1
    (( ${#content} > FILE_SIZE_LIMIT )) && { echo "Error: Content too large"; return 1; }
    mkdir -p "$(dirname "$safe_file")"; echo "$content" > "$safe_file"; echo "Successfully wrote ${#content} bytes to $path"
}

execute_append_file() {
    local path="$1" content="$2"; local safe_file; safe_file=$(safe_path "$path") || return 1
    local current=0; [[ -f "$safe_file" ]] && current=$(file_size "$safe_file")
    (( current + ${#content} > FILE_SIZE_LIMIT )) && { echo "Error: Total file size would exceed limit"; return 1; }
    mkdir -p "$(dirname "$safe_file")"; echo "$content" >> "$safe_file"; echo "Successfully appended ${#content} bytes";
}

execute_text_replace() {
    local file="$1" search="$2" replace="$3"; local safe_file; safe_file=$(safe_path "$file") || return 1
    [[ ! -f "$safe_file" ]] && { echo "Error: File not found"; return 1; }
    [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]] && { echo "Error: File too large"; return 1; }
    [[ -z "$search" ]] && { echo "Error: search pattern empty"; return 1; }
    local tmp="${safe_file}.tmp"; sed "s/${search}/${replace}/g" "$safe_file" > "$tmp" || { rm -f "$tmp"; return 1; }
    mv "$tmp" "$safe_file"; echo "Replacement done"
}

execute_read_file() {
    local path="$1"; local safe_file; safe_file=$(safe_path "$path") || return 1
    [[ ! -f "$safe_file" ]] && { echo "Error: File not found"; return 1; }
    [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]] && { echo "Error: File too large"; return 1; }
    cat "$safe_file"
}

execute_download_file() {
    local url="$1" path="$2"; local safe_file; safe_file=$(safe_path "$path") || return 1
    mkdir -p "$(dirname "$safe_file")"; curl -s -L --max-filesize $DOWNLOAD_SIZE_LIMIT -o "$safe_file" "$url" || return 1
    echo "Downloaded to $path"
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
