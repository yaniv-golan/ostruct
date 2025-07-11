#!/usr/bin/env bash
# ostruct_cli.sh – helpers for invoking ostruct templates safely.
#
# Exports:
#   detect_ostruct_bin        – locates the ostruct executable via Poetry
#   generate_schemas          – template→schema generator (requires env vars)
#   ostruct_call              – run ostruct with retry & output capture
#
# Required ENV variables (must be set by caller):
#   REPO_ROOT         – repo root directory (for poetry run context)
#   AGENT_DIR         – agent directory
#   TEMPLATES_DIR     – dir containing Jinja2 templates
#   SCHEMAS_DIR       – dir containing JSON schemas
#   TOOLS_FILE        – path to tools.json
#
# Optional ENV:
#   LOG_FILE          – path to aggregate log output
#   SANDBOX_PATH      – used only for logging context
#
# Dependencies: path_utils.sh, retry.sh, log_* helpers

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "ostruct_cli.sh: source this file, do not execute" >&2
  exit 1
fi

# ------------------------------------------------------------
# detect_ostruct_bin – sets OSTRUCT_BIN env if unset
# ------------------------------------------------------------

detect_ostruct_bin() {
    if [[ -n "$OSTRUCT_BIN" && -x "$OSTRUCT_BIN" ]]; then
        return 0
    fi
    if [[ -z "$REPO_ROOT" ]]; then
        echo "detect_ostruct_bin: REPO_ROOT not set" >&2; return 1
    fi
    local bin
    bin=$(cd "$REPO_ROOT" && poetry run bash -c 'command -v ostruct' 2>/dev/null) || true
    if [[ -z "$bin" ]]; then
        echo "ostruct executable not found via poetry" >&2
        return 1
    fi
    export OSTRUCT_BIN="$bin"
}

# ------------------------------------------------------------
# generate_schemas – fills __TOOL_NAMES__ placeholders
# ------------------------------------------------------------

generate_schemas() {
    detect_ostruct_bin || return 1
    if [[ -z "$SCHEMAS_DIR" || -z "$TOOLS_FILE" ]]; then
        log_error "generate_schemas: missing SCHEMAS_DIR or TOOLS_FILE"; return 1
    fi
    local tool_names
    tool_names=$(jq -r 'keys | @json' "$TOOLS_FILE") || { log_error "Failed to parse tools.json"; return 1; }

    for tpl in state plan_step replanner_out; do
        local src="$SCHEMAS_DIR/${tpl}.schema.json.template"
        local dst="$SCHEMAS_DIR/${tpl}.schema.json"
        [[ -f "$src" ]] || continue
        sed "s/__TOOL_NAMES__/$tool_names/g" "$src" > "$dst"
        log_debug "Generated ${tpl}.schema.json with tools list"
    done
}

# ------------------------------------------------------------
# ostruct_call – wrapper with retry using with_retry helper
# ------------------------------------------------------------
# Usage: ostruct_call TEMPLATE SCHEMA [extra args...]
#   • returns JSON output to stdout or exits 1.
# ------------------------------------------------------------

ostruct_call() {
    local template="$1"; local schema="$2"; shift 2
    local args=("$@")

    detect_ostruct_bin || return 1

    # Respect global counters if defined
    if [[ -n "$MAX_OSTRUCT_CALLS" ]]; then
        : $((OSTRUCT_CALL_COUNT++))
        if (( OSTRUCT_CALL_COUNT > MAX_OSTRUCT_CALLS )); then
            log_error "Maximum ostruct calls ($MAX_OSTRUCT_CALLS) exceeded"; return 1
        fi
    fi

    # Extract optional --output-file from args to reuse across retries
    local output_file=""; local -a filtered=(); local i=0
    while [[ $i -lt ${#args[@]} ]]; do
        if [[ "${args[$i]}" == "--output-file" ]]; then
            output_file="${args[$((i+1))]}"; i=$((i+2))
        else
            filtered+=("${args[$i]}"); i=$((i+1))
        fi
    done

    # Add verbosity flags based on agent's log level
    local -a verbosity_flags=()
    case "${LOG_LEVEL:-INFO}" in
        DEBUG)
            verbosity_flags+=("--debug")
            ;;
        VERBOSE)
            verbosity_flags+=("--verbose")
            ;;
        *)
            # Default: use --progress none to suppress progress output
            verbosity_flags+=("--progress" "none")
            ;;
    esac

    # Add template debugging if requested
    if [[ "${OSTRUCT_TEMPLATE_DEBUG:-}" == "true" ]]; then
        verbosity_flags+=("--template-debug" "all")
    fi

    run_once() {
        local tmp cleanup=false
        if [[ -n "$output_file" ]]; then
            tmp="$output_file"
        else
            tmp=$(mktemp) || { log_error "mktemp failed"; return 1; }
            cleanup=true
        fi

        local cmd=("$OSTRUCT_BIN" run "${TEMPLATES_DIR}/$template" "${SCHEMAS_DIR}/$schema" --file tools "$TOOLS_FILE" --output-file "$tmp" "${verbosity_flags[@]}" "${filtered[@]}")

        # When using --output-file, ostruct shouldn't output JSON to stdout
        # but it might still output progress/status messages, so redirect appropriately
        if [[ "${LOG_LEVEL:-INFO}" == "DEBUG" ]]; then
            # In debug mode, let ostruct output go to console and log
            (cd "$REPO_ROOT" && "${cmd[@]}" 2>&1 | tee -a "$LOG_FILE") || return 1
        else
            # In normal mode, send all output to log file only
            (cd "$REPO_ROOT" && "${cmd[@]}" >>"$LOG_FILE" 2>&1) || return 1
        fi

        [[ -s "$tmp" ]] || return 1

        # Only output to stdout if no --output-file was provided
        # This prevents JSON from being displayed when using --output-file
        if [[ -z "$output_file" ]]; then
            cat "$tmp"
        fi

        $cleanup && rm -f "$tmp"
        return 0
    }

    with_retry 3 1 3 7 -- run_once || { log_error "ostruct_call failed"; return 1; }
}
export -f detect_ostruct_bin generate_schemas ostruct_call
