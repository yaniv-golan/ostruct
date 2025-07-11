#!/bin/bash

# Sandboxed Agent Runner
# Provides safe, controlled execution of LLM-planned tasks using ostruct

set -euo pipefail

# Directory of this script (agent root)
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repository root (two levels up from agent dir)
REPO_ROOT="$(cd "$AGENT_DIR/../.." && pwd)"

# -----------------------------------------------------------------------------
# Detect ostruct path *before* sourcing log4sh (which overrides `which`)
# -----------------------------------------------------------------------------
# We use `command -v` inside a subshell to avoid any shell alias/function shadow.
# Using Poetry ensures we pick up the virtual-env executable.

OSTRUCT_BIN="$(cd "$REPO_ROOT" && poetry run bash -c 'command -v ostruct' 2>/dev/null)"
if [[ -z "$OSTRUCT_BIN" ]]; then
    echo "Error: Unable to locate ostruct executable via poetry" >&2
    exit 1
fi

# -----------------------------------------------------------------------------
# Shared logging setup – replace ad-hoc logging with scripts/logging.sh
# -----------------------------------------------------------------------------
LOG_DIR="$AGENT_DIR/logs"            # reuse agent-specific log folder
LOG_LEVEL=${LOG_LEVEL:-INFO}          # allow override via env
# Library directory
LIB_DIR="$AGENT_DIR/lib"
# Load central configuration constants
# shellcheck source=/dev/null
source "$LIB_DIR/config.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/retry.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/ostruct_cli.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/tools.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/ai_helpers.sh"
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/logging.sh"
log_start "runner.sh"

# Load verifier helpers
if [[ -f "$AGENT_DIR/verify.sh" ]]; then
    # shellcheck source=/dev/null
    source "$AGENT_DIR/verify.sh"
else
    echo "Error: verify.sh not found in $AGENT_DIR" >&2
    exit 1
fi

# Canonical sub-paths (absolute)
TEMPLATES_DIR="$AGENT_DIR/templates"
SCHEMAS_DIR="$AGENT_DIR/schemas"
TOOLS_FILE="$AGENT_DIR/tools.json"

# Constants now provided by config.sh (MAX_TURNS, MAX_OSTRUCT_CALLS, WORKDIR)
# Will be set inside init_run after RUN_ID is defined
WORKDIR_PATH=""
SANDBOX_PATH=""
CURRENT_STATE_FILE=""

# Global counters
OSTRUCT_CALL_COUNT=0
TURN_COUNT=0

# Runtime variables
RUN_ID=""
TASK=""
CURRENT_STATE=""

# Error handling helper
error_exit() {
    log_error "$1"
    exit 1
}

# ----------------------------------------------------------------------------
# extract_dependencies – heuristically determine provides/requires for a step
# ----------------------------------------------------------------------------
extract_dependencies() {
    local step_json="$1"
    local tool=$(echo "$step_json" | jq -r '.tool')
    local provides="[]"
    local requires="[]"

    case "$tool" in
        "write_file"|"append_file")
            local path=$(get_param "$step_json" "path")
            if [[ -n "$path" ]]; then
                provides=$(jq -n --arg path "$path" '[$path]')
            fi
            ;;
        "read_file"|"grep"|"sed"|"awk")
            local file=$(get_param "$step_json" "file")
            if [[ -n "$file" ]]; then
                requires=$(jq -n --arg file "$file" '[$file]')
            fi
            ;;
        "download_file")
            local path=$(get_param "$step_json" "path")
            if [[ -n "$path" ]]; then
                provides=$(jq -n --arg path "$path" '[$path]')
            fi
            ;;
        "text_replace")
            local file=$(get_param "$step_json" "file")
            if [[ -n "$file" ]]; then
                requires=$(jq -n --arg file "$file" '[$file]')
                provides=$(jq -n --arg file "$file" '[$file]')
            fi
            ;;
    esac

    echo "$step_json" | jq --argjson provides "$provides" --argjson requires "$requires" \
        '. + {provides: $provides, requires: $requires}'
}

# generate_schemas now provided by lib/ostruct_cli.sh

# Initialize run environment
init_run() {
    # Generate unique run ID
    RUN_ID=$(date '+%Y%m%d_%H%M%S')_$$

    # Ensure log directory exists (logging.sh already created LOG_FILE)
    mkdir -p "$LOG_DIR"

    log_info "Starting run $RUN_ID"
    log_info "Sandbox path: $SANDBOX_PATH"
    log_info "Log file: $LOG_FILE"

    # Ensure workdir path is absolute
    WORKDIR_PATH="$AGENT_DIR/$WORKDIR"

    # Create base workdir directory once
    mkdir -p "$WORKDIR_PATH"

    # Create sandbox for this run
    SANDBOX_PATH="$WORKDIR_PATH/sandbox_${RUN_ID}"
    mkdir -p "$SANDBOX_PATH"

    # State file
    CURRENT_STATE_FILE="$SANDBOX_PATH/.agent_state.json"

    # Log sandbox info after paths are ready
    log_info "Sandbox path: $SANDBOX_PATH"
    log_info "Log file: $LOG_FILE"

    # Generate schemas from templates
    generate_schemas
}

# Sort steps using DAG (calls lib/dag_sort.py)
sort_steps_dag() {
    local steps_json="$1"

    log_debug "DAG sorting steps based on dependencies"

    # Extract dependencies for each step
    local tagged_steps="[]"
    local step_count=0
    while IFS= read -r step; do
        if [[ -z "$step" || "$step" == "{}" ]]; then
            continue
        fi

        step_count=$((step_count + 1))
        local tagged_step
        tagged_step=$(extract_dependencies "$step")
        tagged_steps=$(echo "$tagged_steps" | jq -c ". + [$tagged_step]")
    done <<< "$(echo "$steps_json" | jq -c '.[]?')"

    log_debug "DAG sorting processed $step_count steps"
    log_debug "Tagged steps: $tagged_steps"

    # Run python sorter
    local sort_result
    sort_result=$(echo "$tagged_steps" | python3 "$LIB_DIR/dag_sort.py" 2>&1)

    log_debug "Kahn sort result: $sort_result"

    local error
    error=$(echo "$sort_result" | jq -r '.error // empty' 2>/dev/null || echo "parse_error")

    log_debug "Kahn sort error: $error"

    if [[ "$error" == "cycle_detected" ]]; then
        log_error "Cycle detected in DAG, aborting turn"
        # Return empty array to trigger replanner
        echo "[]"
        return 1
    fi

    local sorted_steps
    sorted_steps=$(echo "$sort_result" | jq -c '.steps')

    log_debug "Extracted sorted steps: $sorted_steps"
    log_info "DAG sort completed successfully"
    echo "$sorted_steps"
}

# ostruct_call now provided by lib/ostruct_cli.sh

# Helper function to extract parameter value by name
get_param() {
    local step_json="$1"
    local param_name="$2"
    echo "$step_json" | jq -r ".parameters[] | select(.name == \"$param_name\") | .value"
}

# Execute a single step
execute_step() {
    local step_json="$1"
    local start_time=$(date +%s)

    # Normalize any file-path parameters so the critic always sees sandbox-relative paths
    step_json=$(echo "$step_json" | jq '(.parameters) |= map(
        if (.name=="path" or .name=="file" or .name=="output") and (.value|test("^(/|\\./)")|not)
        then .value = ("./" + .value) else . end)')

    # Parse normalized step JSON
    local tool=$(echo "$step_json" | jq -r '.tool')
    local reasoning=$(echo "$step_json" | jq -r '.reasoning')

    log_info "Executing step: $tool - $reasoning"

    # Check if critic is enabled (default: true)
    if [[ "${CRITIC_ENABLED:-true}" == "true" ]]; then
        # Build critic input
        local critic_input
        critic_input=$(build_critic_input "$step_json" "$TURN_COUNT")

        # Save critic input to temporary file
        local critic_input_file="$SANDBOX_PATH/.critic_input_${TURN_COUNT}.json"
        echo "$critic_input" > "$critic_input_file"

        # Call critic
        log_debug "Calling critic for step validation"
        local critic_out
        critic_out=$(ostruct_call "critic.j2" "critic_out.schema.json" \
            --file critic_input "$critic_input_file")

        if [[ $? -ne 0 ]]; then
            log_error "Critic call failed, proceeding without validation"
        else
            # Parse critic response
            local ok score comment
            ok=$(echo "$critic_out" | jq -r '.ok')
            score=$(echo "$critic_out" | jq -r '.score')
            comment=$(echo "$critic_out" | jq -r '.comment')

            log_info "Score: $score, OK: $ok, Comment: $comment"

            # Apply blocking logic
            if [[ "$ok" == "false" ]] || (( score <= 2 )); then
                log_info "BLOCKING step execution (score=$score)"

                # Apply patch if available
                local patch_len
                patch_len=$(echo "$critic_out" | jq '.patch | length')

                if (( patch_len > 0 )); then
                    log_info "Applying $patch_len patch steps"

                    # Extract raw patch array from critic_out
                    local patch
                    patch=$(echo "$critic_out" | jq '.patch')

                    # -----------------------------------------------------
                    # Drop the blocked step itself from next_steps so it is
                    # not attempted again on the next turn.
                    # -----------------------------------------------------
                    CURRENT_STATE=$(echo "$CURRENT_STATE" | jq '.next_steps |= .[1:]')

                    # -----------------------------------------------------------------
                    #   Filter out any patch steps that match a previously blocked
                    #   fingerprint so we don\'t re-queue the exact same failing step.
                    # -----------------------------------------------------------------
                    local filtered_patch="[]"
                    # Iterate over patch steps one-by-one
                    while IFS= read -r patch_step; do
                        # skip empty lines (safety)
                        [[ -z "$patch_step" ]] && continue

                        # Skip patch steps that have been blocked before OR already appear in next_steps
                        if is_step_previously_blocked "$patch_step"; then
                            log_debug "Omitting patch step already blocked by critic"
                            continue
                        fi

                        # Skip if identical step is already queued in next_steps
                        if echo "$CURRENT_STATE" | jq -e --argjson s "$patch_step" 'any(.next_steps[]?; . == $s)' >/dev/null; then
                            log_debug "Omitting duplicate patch step already in plan"
                            continue
                        fi

                        # Append to filtered_patch
                        filtered_patch=$(echo "$filtered_patch" | \
                            jq --argjson step "$patch_step" '. + [$step]')
                    done < <(echo "$patch" | jq -c '.[]')

                    # Only prepend if there are remaining (unique) patch steps
                    local filtered_len
                    filtered_len=$(echo "$filtered_patch" | jq 'length')
                    if (( filtered_len > 0 )); then
                        CURRENT_STATE=$(echo "$CURRENT_STATE" | \
                            jq --argjson patch "$filtered_patch" '.next_steps = ($patch + .next_steps)')
                    else
                        log_debug "All critic patch steps were previously blocked; none queued"
                    fi

                    # Save updated state
                    echo "$CURRENT_STATE" > "$CURRENT_STATE_FILE"
                fi

                # Record critic intervention
                record_critic_intervention "$step_json" "$critic_out"

                # Record blocked step in history
                record_blocked_step "$step_json" "$score" "$comment"

                # Return blocked result
                local result_json
                result_json=$(jq -n \
                    --arg comment "$comment" \
                    --argjson score "$score" \
                    --argjson duration "0" \
                    '{success: false, error: ("Critic blocked: " + $comment), critic_score: $score, duration: $duration, blocked_by_critic: true}')
                echo "$result_json"
                return 2  # Special return code for critic block
            fi

            # Score 3: warn but proceed
            if (( score == 3 )); then
                log_warn "Critic warning: $comment"
            fi
        fi

        # Clean up temporary file
        rm -f "$critic_input_file"
    fi

    local output=""
    local success=true

    # Skip steps missing or null tool
    if [[ -z "$tool" || "$tool" == "null" ]]; then
        log_warn "Skipping invalid step: missing tool"
        return 1
    fi

    # Dispatch to library
    case "$tool" in jq|grep|sed|awk|curl|write_file|append_file|text_replace|read_file|download_file)
        # Build positional args array from parameters order
        local -a targs=()
        while IFS= read -r p; do targs+=("$(jq -r '.value' <<<"$p")"); done < <(echo "$step_json" | jq -c '.parameters[]')
        output=$(tool_exec "$tool" "${targs[@]}")
        ;;
        *)
        output="Error: Unknown tool: $tool"; success=false ;;
    esac

    # Check if command failed
    if [[ $? -ne 0 ]]; then
        success=false
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Update failure patterns
    update_failure_patterns "$tool" "$success" "$TURN_COUNT"

    # Create result JSON
    local result_json
    if [[ "$success" == "true" ]]; then
        result_json=$(jq -n --arg output "$output" --argjson duration "$duration" \
            '{success: true, output: $output, duration: $duration}')
    else
        result_json=$(jq -n --arg error "$output" --argjson duration "$duration" \
            '{success: false, error: $error, duration: $duration}')
    fi

    echo "$result_json"
}

# Main execution function
main() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: $0 <task_description>"
        echo "Example: $0 'Download and analyze the latest weather data'"
        exit 1
    fi

    local task="$1"
    TASK="$task"  # Make task available globally for critic

    # Initialize run environment
    init_run

    log_info "Task: $task"
    log_info "Max turns: $MAX_TURNS"
    log_info "Max ostruct calls: $MAX_OSTRUCT_CALLS"

    # Step 1: Generate multiple candidate plans
    log_info "Generating 3 candidate plans in parallel"

    # Function to launch one planner with diversity
    gen_plan() {
        local idx="$1"
        local tmp="$SANDBOX_PATH/plan_${idx}.json"
        # Add diversity via temperature and random token
        OSTRUCT_MODEL_PARAMS='{"temperature":0.9}' \
        ostruct_call "planner.j2" "state.schema.json" \
            -V "task=$task" \
            -V "sandbox_path=$SANDBOX_PATH" \
            -V "max_turns=$MAX_TURNS" \
            -V "diversity_token=$(uuidgen | head -c 8)" \
            --output-file "$tmp" \
            --file plan_schema "$SCHEMAS_DIR/plan_step.schema.json" &
        echo $!  # return PID
    }

    # Launch 3 planners in parallel
    pids=(); plan_files=()
    for i in 0 1 2; do
        gen_plan "$i"
        pids[$i]=$!
        plan_files[$i]="$SANDBOX_PATH/plan_${i}.json"
    done

    # Wait for all planners to complete
    for pid in "${pids[@]}"; do
        wait "$pid"
    done

    # Check for valid plan files and deduplicate
    unique_files=()
    # Use associative array for deduplication (requires bash 4+)
    if [[ ${BASH_VERSION%%.*} -ge 4 ]]; then
        declare -A seen
    else
        # Fallback for older bash - use a different approach
        seen_sigs=""
    fi
    for f in "${plan_files[@]}"; do
        # Skip missing or empty files
        [[ -s "$f" ]] || { log_warn "plan $f missing, skipping"; continue; }

        # Create signature for deduplication
        sig=$(jq -S . "$f" 2>/dev/null | sha256sum | cut -d' ' -f1)
        if [[ -n "$sig" ]]; then
            if [[ ${BASH_VERSION%%.*} -ge 4 ]]; then
                # Use associative array
                if [[ -z "${seen[$sig]+x}" ]]; then
                    seen[$sig]=1
                    unique_files+=("$f")
                fi
            else
                # Fallback: check if signature already in string
                if [[ "$seen_sigs" != *"$sig"* ]]; then
                    seen_sigs="$seen_sigs $sig"
                    unique_files+=("$f")
                fi
            fi
        fi
    done

    # Ensure we have at least one valid plan
    if [[ ${#unique_files[@]} -eq 0 ]]; then
        error_exit "No valid plans generated"
    fi

    # If only one unique plan, use it directly
    if [[ ${#unique_files[@]} -eq 1 ]]; then
        log_info "Only one unique plan generated, using it directly"
        planner_output=$(cat "${unique_files[0]}")
    else
        # Build JSON array of candidates for selector
        plans_file="$SANDBOX_PATH/candidate_plans.json"
        jq -s '.' "${unique_files[@]}" > "$plans_file"

        # Call plan selector
        log_info "Running plan selector on ${#unique_files[@]} candidates"
        selector_out=$(ostruct_call "plan_selector.j2" "plan_selector_out.schema.json" \
            -V "task=$task" \
            --file plans "$plans_file")

        if [[ $? -ne 0 ]]; then
            log_warn "Selector failed, using first plan"
            planner_output=$(cat "${unique_files[0]}")
        else
            # Extract winner and use selected plan
            winner_idx=$(echo "$selector_out" | jq -r '.winner_index // 0')
            comment=$(echo "$selector_out" | jq -r '.comment // "No comment"')

            # Validate index bounds
            if [[ $winner_idx -ge 0 && $winner_idx -lt ${#unique_files[@]} ]]; then
                log_info "Selector chose plan index $winner_idx: $comment"
                planner_output=$(cat "${unique_files[$winner_idx]}")
            else
                log_warn "Invalid winner index $winner_idx, using first plan"
                planner_output=$(cat "${unique_files[0]}")
            fi
        fi
    fi

    if [[ -z "$planner_output" ]]; then
        error_exit "Failed to generate valid initial plan"
    fi

    # Save initial state
    echo "$planner_output" > "$CURRENT_STATE_FILE"
    log_info "Initial state saved"

    # Step 2: Turn-based execution loop
    while true; do
        TURN_COUNT=$((TURN_COUNT + 1))
        log_info "=== Turn $TURN_COUNT/$MAX_TURNS ==="

        # Load current state
        if [[ ! -f "$CURRENT_STATE_FILE" ]]; then
            error_exit "State file not found"
        fi

        local current_state=$(cat "$CURRENT_STATE_FILE")
        CURRENT_STATE="$current_state"  # Make available globally for critic
        local completed=$(echo "$current_state" | jq -r '.completed')
        local current_turn=$(echo "$current_state" | jq -r '.current_turn')

        # Check if task is completed
        if [[ "$completed" == "true" ]]; then
            log_info "Task completed!"
            local final_answer=$(echo "$current_state" | jq -r '.final_answer')
            echo "=== FINAL ANSWER ==="
            echo "$final_answer"
            echo "==================="
            break
        fi

        # Check if max turns reached
        if [[ $current_turn -gt $MAX_TURNS ]]; then
            log_error "Maximum turns reached without completion"
            break
        fi

        # Extract and execute next steps
        local next_steps_array=$(echo "$current_state" | jq -c '.next_steps')
        local next_steps=$(echo "$current_state" | jq -c '.next_steps[]?')
        # Bail if next_steps is empty (planner misbehaved)
        if [[ -z "$next_steps" ]]; then
            log_warn "Planner returned empty next_steps; calling replanner"
        else
            # Sort steps using DAG if enabled
            local sorted_next_steps_array
            sorted_next_steps_array=$(sort_steps_dag "$next_steps_array")

            if [[ $? -ne 0 ]]; then
                # If DAG sort failed, proceed with original next_steps
                log_warn "DAG sort failed, proceeding with original next_steps"
                sorted_next_steps_array="$next_steps_array"
            fi

            log_debug "sorted_next_steps_array: $sorted_next_steps_array"

            # Convert back to individual steps for execution
            local sorted_next_steps=$(echo "$sorted_next_steps_array" | jq -c '.[]?')
            log_debug "After jq conversion: $sorted_next_steps"

            # Execute each step
            local step_results="[]"
            local attempted_count=0  # count every step we process (executed or skipped)
            local succ_count=0
            local fail_count=0
            local created_paths="[]"
            local modified_paths="[]"
            log_debug "Starting step execution loop with sorted_next_steps: $sorted_next_steps"
            while IFS= read -r step; do
                log_debug "Processing step: $step"
                if [[ -z "$step" ]]; then
                    log_debug "Skipping empty step"
                    continue
                fi
                # Skip literal empty object
                if [[ "$step" == "{}" ]]; then
                    log_warn "Skipping empty step object {}"
                    continue
                fi

                # Ensure step is valid JSON
                echo "$step" | jq empty 2>/dev/null || { log_warn "Skipping invalid step JSON"; continue; }

                # Check if step has been previously blocked
                if is_step_previously_blocked "$step"; then
                    log_warn "Skipping previously blocked step: $(echo "$step" | jq -r '.tool')"
                    # Count it as attempted so slicing drops it
                    attempted_count=$((attempted_count + 1))
                    continue
                fi

                attempted_count=$((attempted_count + 1))
                log_info "Executing step: $(echo "$step" | jq -r '.tool')"
                local result=$(execute_step "$step")

                # Check if step was blocked by critic
                local blocked_by_critic=$(echo "$result" | jq -r '.blocked_by_critic // false')
                if [[ "$blocked_by_critic" == "true" ]]; then
                    log_debug "Step blocked by critic"
                    # Do not decrement attempted_count; slicing will drop it
                fi

                # Add step and result to history
                local history_entry=$(jq -n \
                    --argjson turn "$current_turn" \
                    --argjson step "$step" \
                    --argjson result "$result" \
                    '{turn: $turn, step: $step, result: $result}')

                step_results=$(echo "$step_results" | jq ". + [$history_entry]")

                # Log step result
                local success=$(echo "$result" | jq -r '.success')
                if [[ "$success" == "true" ]]; then
                    log_info "Step completed successfully"
                    succ_count=$((succ_count + 1))
                    # Extract tool name once for tracking
                    local step_tool
                    step_tool=$(echo "$step" | jq -r '.tool')
                    # Track file operations for state
                    case "$step_tool" in
                        "write_file"|"download_file")
                            local tgt
                            tgt=$(get_param "$step" "path")
                            if [[ -n "$tgt" && "$tgt" != "null" ]]; then
                                created_paths=$(echo "$created_paths" | jq --arg p "$tgt" '. + [$p]')
                            fi
                            ;;
                        "append_file"|"text_replace")
                            local tgt
                            tgt=$(get_param "$step" "path")
                            if [[ -z "$tgt" || "$tgt" == "null" ]]; then
                                tgt=$(get_param "$step" "file")
                            fi
                            if [[ -n "$tgt" && "$tgt" != "null" ]]; then
                                modified_paths=$(echo "$modified_paths" | jq --arg p "$tgt" '. + [$p]')
                            fi
                            ;;
                    esac
                else
                    log_warn "Step failed: $(echo "$result" | jq -r '.error')"
                    fail_count=$((fail_count + 1))
                fi
            done <<< "$sorted_next_steps"

            # Reload latest state (may include critic patches) and merge execution results
            local base_state=$(cat "$CURRENT_STATE_FILE")
            local updated_state=$(echo "$base_state" | jq \
                --argjson results "$step_results" \
                --argjson attempted "$attempted_count" \
                --argjson created "$created_paths" \
                --argjson modified "$modified_paths" \
                --argjson succ "$succ_count" \
                --argjson fail "$fail_count" '
                .execution_history += $results
                | .next_steps = (.next_steps[$attempted:])
                | .current_turn += 1
                | .files_created += $created
                | .files_modified += $modified
                | .metrics = (.metrics // {})
                | .metrics.successful_steps = (.metrics.successful_steps // 0) + $succ
                | .metrics.failed_steps   = (.metrics.failed_steps   // 0) + $fail
                | .last_successful_step_turn = (if $succ > 0 then .current_turn else (.last_successful_step_turn // .current_turn) end)
            ')

            # ---------------------------------------------------------------------------
            # Goal-based completion check using verify_success helper
            # ---------------------------------------------------------------------------
            if [[ $(echo "$updated_state" | jq '.next_steps | length') -eq 0 ]]; then
                criteria_json=$(echo "$updated_state" | jq -c '.success_criteria // null')

                if verify_success "$SANDBOX_PATH" "$criteria_json"; then
                    log_info "verify_success passed — marking task complete"
                    updated_state=$(echo "$updated_state" | jq '.completed = true | .final_answer = "Task finished successfully"')
                else
                    rc=$?
                    case $rc in
                        1|3)
                            log_debug "verify_success unmet or malformed (rc=$rc); keeping run active"
                            ;; # continue looping
                        2)
                            log_warn "verify_success unknown primitive; falling back to conservative heuristic"
                            if [[ $(echo "$updated_state" | jq '.files_created | length') -gt 0 ]]; then
                                updated_state=$(echo "$updated_state" | jq '.completed = true | .final_answer = "Task finished successfully"')
                            fi
                            ;;
                        *)
                            log_error "verify_success fatal error (rc=$rc); leaving state unchanged"
                            ;;
                    esac
                fi
            fi

            echo "$updated_state" > "$CURRENT_STATE_FILE"

            # If critic injected new next_steps (patches) we already have work to do.
            # Skip replanner this turn – immediately continue execution loop.
            local pending_count
            pending_count=$(echo "$updated_state" | jq '.next_steps | length')
            if [[ $pending_count -gt 0 ]]; then
                log_info "Skipping replanner – ${pending_count} pending step(s) from critic patch.";
                continue
            fi
        fi

        # Call replanner
        log_info "Calling replanner"

        # Get block history summary for replanner context
        local block_history_summary
        block_history_summary=$(get_block_history_summary)
        local block_history_file="$SANDBOX_PATH/.block_history_summary.json"
        echo "$block_history_summary" > "$block_history_file"

        replanner_output=$(ostruct_call "replanner.j2" "replanner_out.schema.json" \
            -V "sandbox_path=$SANDBOX_PATH" \
            -V "max_turns=$MAX_TURNS" \
            --file current_state "$CURRENT_STATE_FILE" \
            --file block_history "$block_history_file")

        if [[ $? -ne 0 ]]; then
            error_exit "Replanner call failed"
        fi

        # ostruct_call now returns clean JSON via --output-file
        # Save updated state
        echo "$replanner_output" > "$CURRENT_STATE_FILE"

        # Log state diff
        local prev_state="$current_state"
        local new_state="$replanner_output"
        log_debug "State diff: $(echo "$prev_state" | jq -S . | diff -u - <(echo "$new_state" | jq -S .) || true)"

        # Check turn limit
        if [[ $TURN_COUNT -ge $MAX_TURNS ]]; then
            log_error "Maximum turns reached"
            break
        fi
    done

    # Step 3: Final cleanup and reporting
    log_info "Execution completed"
    log_info "Total turns: $TURN_COUNT"
    log_info "Total ostruct calls: $OSTRUCT_CALL_COUNT"

    if [[ -f "$CURRENT_STATE_FILE" ]]; then
        local final_state=$(cat "$CURRENT_STATE_FILE")
        local completed=$(echo "$final_state" | jq -r '.completed')
        local error=$(echo "$final_state" | jq -r '.error // empty')

        if [[ "$completed" == "true" ]]; then
            log_info "Task completed successfully"
        elif [[ -n "$error" ]]; then
            log_error "Task failed: $error"
        else
            log_warn "Task incomplete"
        fi
    fi

    log_info "Run completed: $RUN_ID"
}

# Run main function
main "$@"
