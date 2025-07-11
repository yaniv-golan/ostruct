#!/usr/bin/env bash
# ai_helpers.sh – utilities for critic, temporal/failure tracking, and block history.
#
# All helpers rely on the following globals supplied by the caller:
#   TASK, TURN_COUNT, CURRENT_STATE, SANDBOX_PATH, MAX_TURNS, LIB_DIR
# They are intentionally pure-data (jq-based) operations so they are easy to unit-test.
#
# Guard against accidental execution
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "ai_helpers.sh: source this file, do not execute" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/config.sh"

# -----------------------------------------------------------------------------
# build_critic_input – assemble rich JSON for the Critic LLM
# -----------------------------------------------------------------------------
# Usage: build_critic_input <step_json> <turn>
# Returns JSON to stdout.
# -----------------------------------------------------------------------------
build_critic_input() {
    local step="$1" turn="$2"

    # Truncate last observation to 1000 chars (if present)
    local last_obs_trunc=""
    if [[ -f "$SANDBOX_PATH/.last_observation" ]]; then
        last_obs_trunc=$(head -c 1000 "$SANDBOX_PATH/.last_observation")
    fi

    # Plan remainder (first 3 steps)
    local plan_tail hist_tail tool_name tool_spec
    plan_tail=$(echo "$CURRENT_STATE" | jq '.next_steps[0:3]')
    hist_tail=$(echo "$CURRENT_STATE" | jq '.execution_history[-3:]')

    tool_name=$(echo "$step" | jq -r '.tool')
    tool_spec=$(jq --arg tool "$tool_name" \
        '.[$tool] // {name: $tool, description: "Unknown tool", limits: {}}' \
        "$TOOLS_FILE")

    jq -n \
        --arg task "$TASK" \
        --argjson candidate_step "$step" \
        --arg turn "$turn" \
        --arg max_turns "$MAX_TURNS" \
        --arg last_observation "$last_obs_trunc" \
        --argjson plan_remainder "$plan_tail" \
        --argjson execution_history_tail "$hist_tail" \
        --argjson tool_spec "$tool_spec" \
        --arg sandbox_path "$SANDBOX_PATH" \
        --argjson temporal_constraints "$(get_temporal_constraints)" \
        --argjson failure_patterns "$(get_failure_patterns)" \
        --argjson safety_constraints "$(get_safety_constraints)" \
        '{
            task: $task,
            candidate_step: $candidate_step,
            turn: ($turn | tonumber),
            max_turns: ($max_turns | tonumber),
            last_observation: $last_observation,
            plan_remainder: $plan_remainder,
            execution_history_tail: $execution_history_tail,
            tool_spec: $tool_spec,
            sandbox_path: $sandbox_path,
            temporal_constraints: $temporal_constraints,
            failure_patterns: $failure_patterns,
            safety_constraints: $safety_constraints
        }'
}
export -f build_critic_input

# -----------------------------------------------------------------------------
# Temporal constraints helpers
# -----------------------------------------------------------------------------
get_temporal_constraints() {
    local f="$SANDBOX_PATH/.temporal_constraints.json"
    if [[ -f "$f" ]]; then cat "$f"; else echo '{"files_created":[],"files_expected":[],"deadline_turns":null}'; fi
}
export -f get_temporal_constraints

update_temporal_constraints() {
    local action="$1" file_path="$2"
    local f="$SANDBOX_PATH/.temporal_constraints.json"
    local temporal
    temporal=$(get_temporal_constraints)

    case "$action" in
        "add_file")   temporal=$(echo "$temporal" | jq --arg p "$file_path" '.files_created += [$p]') ;;
        "expect_file") temporal=$(echo "$temporal" | jq --arg p "$file_path" '.files_expected += [$p]') ;;
        "set_deadline") temporal=$(echo "$temporal" | jq --arg deadline "$file_path" '.deadline_turns = ($deadline | tonumber)') ;;
    esac

    echo "$temporal" > "$f"
}
export -f update_temporal_constraints

# -----------------------------------------------------------------------------
# Failure pattern tracking
# -----------------------------------------------------------------------------
get_failure_patterns() {
    local f="$SANDBOX_PATH/.failure_patterns.json"
    if [[ -f "$f" ]]; then cat "$f"; else echo '{"repeated_tool_failures":{},"stuck_iterations":false}'; fi
}
export -f get_failure_patterns

update_failure_patterns() {
    local tool="$1" success="$2" turn="$3"
    local f="$SANDBOX_PATH/.failure_patterns.json" patterns
    patterns=$(get_failure_patterns)

    if [[ "$success" == "false" ]]; then
        patterns=$(echo "$patterns" | jq --arg tool "$tool" '.repeated_tool_failures[$tool] = (.repeated_tool_failures[$tool] // 0) + 1')
    fi

    # Simple stuck-iteration heuristic
    if [[ -f "$SANDBOX_PATH/.prev_progress" ]]; then
        local prev_current
        prev_current=$(cat "$SANDBOX_PATH/.prev_progress")
        local now_current
        now_current=$(echo "$CURRENT_STATE" | jq '.execution_history | length')
        if [[ "$now_current" == "$prev_current" ]]; then
            patterns=$(echo "$patterns" | jq '.stuck_iterations = true')
        fi
    fi

    echo "$patterns" > "$f"
    echo "$CURRENT_STATE" | jq '.execution_history | length' > "$SANDBOX_PATH/.prev_progress"
}
export -f update_failure_patterns

# -----------------------------------------------------------------------------
# Safety constraints (static for now)
# -----------------------------------------------------------------------------
get_safety_constraints() { echo '["no_file_ops_outside_sandbox","no_network_internal_ips","max_file_size_32kb"]'; }
export -f get_safety_constraints

# -----------------------------------------------------------------------------
# Critic / block-history helpers
# -----------------------------------------------------------------------------
record_critic_intervention() {
    local step_json="$1" critic_out="$2" f="$SANDBOX_PATH/.critic_interventions.jsonl"
    jq -n --argjson turn "$TURN_COUNT" --argjson step "$step_json" --argjson critic_out "$critic_out" '{turn: $turn, step: $step, critic_response: $critic_out, timestamp: (now | todate)}' >> "$f"
}
export -f record_critic_intervention

generate_step_fingerprint() {
    local step_json="$1"
    echo "$step_json" | jq -c '{tool, parameters: (.parameters | sort_by(.name) | map({name, value}))}' | shasum -a 256 | cut -d' ' -f1
}
export -f generate_step_fingerprint

record_blocked_step() {
    local step_json="$1" critic_score="$2" block_reason="$3" f="$SANDBOX_PATH/.block_history.jsonl" fingerprint existing_count block_entry
    fingerprint=$(generate_step_fingerprint "$step_json")
    existing_count=0
    if [[ -f "$f" ]]; then
        existing_count=$(grep -c "\"fingerprint\":\"$fingerprint\"" "$f" 2>/dev/null || echo 0)
        existing_count=$(echo "$existing_count" | tr -d '\n\r' | grep -E '^[0-9]+$' || echo 0)
    fi
    block_entry=$(jq -n --argjson turn "$TURN_COUNT" --arg fingerprint "$fingerprint" --argjson step "$step_json" --argjson score "$critic_score" --arg reason "$block_reason" --argjson count "$((existing_count+1))" '{turn:$turn,fingerprint:$fingerprint,step:$step,critic_score:$score,block_reason:$reason,repeat_count:$count,timestamp:(now|todate)}')
    echo "$block_entry" >> "$f"
}
export -f record_blocked_step

is_step_previously_blocked() {
    local step_json="$1" f="$SANDBOX_PATH/.block_history.jsonl"
    [[ -f "$f" ]] || return 1
    local fingerprint
    fingerprint=$(generate_step_fingerprint "$step_json")
    grep -q "\"fingerprint\":\"$fingerprint\"" "$f"
}
export -f is_step_previously_blocked

get_block_history_summary() {
    local f="$SANDBOX_PATH/.block_history.jsonl"
    [[ -f "$f" ]] || { echo "[]"; return; }
    tail -10 "$f" | jq -s 'map({fingerprint, tool: .step.tool, parameters: .step.parameters, block_reason, repeat_count, turn}) | group_by(.fingerprint) | map({fingerprint: .[0].fingerprint, tool: .[0].tool, parameters: .[0].parameters, block_reason: .[0].block_reason, total_repeats: (map(.repeat_count)|max), first_seen_turn: (map(.turn)|min), last_seen_turn: (map(.turn)|max)}) | sort_by(.total_repeats) | reverse'
}
export -f get_block_history_summary
