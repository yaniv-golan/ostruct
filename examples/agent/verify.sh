#!/usr/bin/env bash
# verify.sh - lightweight goal verifier helpers for the agent runner
#
# Exit-code contract for verify_success:
#   0  – every criterion passed
#   1  – criteria present but at least one failed
#   2  – unknown primitive type (fallback allowed)
#   3  – malformed JSON (fallback allowed)
# >=128 – fatal runtime/IO errors

# ---------------------------------------------------------------------------
# Internal: resolve path relative to sandbox, re-use runner's safe_path if set
# ---------------------------------------------------------------------------
_safe_path_local() {
    local p="$1"
    # If runner already defined safe_path, delegate
    if declare -F safe_path >/dev/null; then
        safe_path "$p"
        return
    fi
    # Minimal fallback: ensure path stays inside current working dir.
    case "$p" in
        /*) printf "%s" "$p";;
        ./*) printf "%s" "$p";;
        *)   printf "./%s" "$p";;
    esac
}

# ---------------------------------------------------------------------------
# verify_success <sandbox_path> <criteria_json>
# ---------------------------------------------------------------------------
verify_success() {
    local sandbox="$1"
    local criteria_json="$2"

    # Missing or null → nothing to check (treat as unmet, runner will fallback)
    if [[ -z "$criteria_json" ]] || [[ "$criteria_json" == "null" ]]; then
        return 1
    fi

    # Ensure valid JSON array
    if ! jq -e 'type=="array"' <<<"$criteria_json" >/dev/null 2>&1; then
        return 3
    fi

    local all_ok=0
    while IFS= read -r crit; do
        local type path substr key value
        type=$(jq -r '.type' <<<"$crit" 2>/dev/null || echo '')
        case "$type" in
            file_exists)
                path=$(_safe_path_local "$(jq -r '.path' <<<"$crit")") || return 128
                if [[ ! -f "$path" ]]; then all_ok=1; fi
                ;;
            file_contains)
                path=$(_safe_path_local "$(jq -r '.path' <<<"$crit")") || return 128
                substr="$(jq -r '.substr' <<<"$crit")"
                # substr length guard (128 bytes)
                if (( ${#substr} > 128 )); then return 3; fi
                if ! grep -qF -- "$substr" "$path" 2>/dev/null; then all_ok=1; fi
                ;;
            json_key_equals)
                path=$(_safe_path_local "$(jq -r '.path' <<<"$crit")") || return 128
                key="$(jq -r '.key' <<<"$crit")"
                value="$(jq -r '.value' <<<"$crit")"
                if ! jq -e --arg k "$key" --arg v "$value" 'getpath([$k]) == $v' "$path" >/dev/null 2>&1; then
                    all_ok=1
                fi
                ;;
            *)
                return 2  # unknown primitive
                ;;
        esac
    done < <(jq -c '.[]' <<<"$criteria_json")

    return $all_ok
}

# eof
