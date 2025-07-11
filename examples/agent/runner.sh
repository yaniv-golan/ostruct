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
source "$LIB_DIR/ui_helpers.sh"
# shellcheck source=/dev/null
source "$REPO_ROOT/scripts/logging.sh"

# Configure logging for cleaner UI
if [[ "${LOG_LEVEL:-INFO}" == "INFO" && "${AGENT_UI_DISABLE:-false}" != "true" ]]; then
    # In normal operation with UI enabled, only show warnings and errors on console
    # Full logging still goes to file (already configured by scripts/logging.sh)

    # Just adjust the stderr appender level to WARN for cleaner UI
    appender_setLevel stderr WARN
    appender_activateOptions stderr

    log_info "UI mode: Console shows warnings/errors only, full logging to: $LOG_FILE"
elif [[ "${LOG_LEVEL:-INFO}" == "VERBOSE" ]]; then
    # Verbose mode - show info and above
    appender_setLevel stderr INFO
    appender_activateOptions stderr
    log_info "Verbose mode: Detailed logging to console and file: $LOG_FILE"
else
    # Debug/verbose mode - show everything (default configuration)
    log_info "Debug mode: Full logging to console and file: $LOG_FILE"
fi

# Template debugging configuration
# Set OSTRUCT_TEMPLATE_DEBUG=true to enable detailed template debugging
# Useful when troubleshooting template rendering issues, variable substitution,
# or understanding how templates are processed before being sent to the LLM
if [[ "${OSTRUCT_TEMPLATE_DEBUG:-false}" == "true" ]]; then
    log_info "Template debugging enabled - ostruct will show detailed template processing"
fi

log_start "runner.sh"

# Initialize UI system
ui_init

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

# Sort steps using DAG (native tsort implementation)
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

    if [[ $step_count -eq 0 ]]; then
        echo '{"error": null, "steps": []}'
        return 0
    fi

    # Generate edges: for each pair, if intersection(provides_i, requires_j) add 'step_i step_j'
    local edges
    edges=$(echo "$tagged_steps" | jq -r '
        . as $steps |
        length as $n |
        [range(0;$n) as $i | range(0;$n) as $j |
        if $i != $j and ([$steps[$i].provides[] | select(. as $p | $steps[$j].requires | index($p) != null)] | length > 0)
        then "step_\($i) step_\($j)"
        else empty end]
        | .[]'
    )

    # Run tsort
    local sorted_nodes cycle_detected=0
    sorted_nodes=$(echo "$edges" | tsort 2>/dev/null) || cycle_detected=1

    # Check for cycle (tsort outputs partial if cycle)
    local node_count
    node_count=$(echo "$tagged_steps" | jq 'length')
    local output_count
    output_count=$(echo "$sorted_nodes" | wc -l | tr -d ' ')
    if [[ $cycle_detected -ne 0 || $output_count -ne $node_count ]]; then
        log_error "Cycle detected in DAG, aborting turn"
        echo '{"error": "cycle_detected", "steps": []}'
        return 1
    fi

    # Map sorted nodes back to steps (extract index from step_N)
    local sorted_steps
    sorted_steps=$(echo "$tagged_steps" | jq --arg sorted "$sorted_nodes" '
        [ $sorted | split("\n")[] | select(. != "") | ltrimstr("step_") | tonumber ] as $order |
        [ .[$order[]] ]
    ')

    log_debug "Sorted steps: $sorted_steps"
    log_info "DAG sort completed successfully"
    echo '{"error": null, "steps": '"$sorted_steps"'}'
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
        local critic_output_file="$SANDBOX_PATH/.critic_output_${TURN_COUNT}.json"
        if ostruct_call "critic.j2" "critic_out.schema.json" \
            --file critic_input "$critic_input_file" \
            --output-file "$critic_output_file"; then
            critic_out=$(cat "$critic_output_file")
        else
            critic_out=""
        fi

        if [[ $? -ne 0 ]]; then
            ui_step_warning "Critic Evaluation" "Critic call failed, proceeding without validation"
            log_error "Critic call failed, proceeding without validation"
        else
            # Parse critic response
            local ok score comment
            ok=$(echo "$critic_out" | jq -r '.ok')
            score=$(echo "$critic_out" | jq -r '.score')
            comment=$(echo "$critic_out" | jq -r '.comment')

            log_info "Score: $score, OK: $ok, Comment: $comment"

            # Display critic feedback with appropriate UI
            if [[ "$ok" == "false" ]] || (( score <= 2 )); then
                ui_critic_feedback "$score" "$comment" "blocked"
            elif (( score == 3 )); then
                ui_critic_feedback "$score" "$comment" "warning"
            else
                ui_critic_feedback "$score" "$comment" "approved"
            fi

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

# Display the selected plan in human-readable format
display_selected_plan() {
    local plan_json="$1"

    echo ""
    echo "📋 Selected Plan Details:"
    echo ""

    # Extract and display basic info
    local task=$(echo "$plan_json" | jq -r '.task // "No task description"')
    local max_turns=$(echo "$plan_json" | jq -r '.max_turns // "Unknown"')
    local step_count=$(echo "$plan_json" | jq -r '.next_steps | length')

    echo "  Task: $task"
    echo "  Max turns: $max_turns"
    echo "  Steps planned: $step_count"
    echo ""

    # Display each step in detail
    local step_num=1
    while IFS= read -r step; do
        if [[ -n "$step" && "$step" != "null" ]]; then
            local tool=$(echo "$step" | jq -r '.tool // "unknown"')
            local reasoning=$(echo "$step" | jq -r '.reasoning // "No reasoning provided"')

            echo "  Step $step_num: $tool"
            echo "    Reasoning: $reasoning"

            # Display parameters
            local param_count=$(echo "$step" | jq -r '.parameters | length')
            if [[ $param_count -gt 0 ]]; then
                echo "    Parameters:"
                while IFS= read -r param; do
                    if [[ -n "$param" && "$param" != "null" ]]; then
                        local name=$(echo "$param" | jq -r '.name // "unknown"')
                        local value=$(echo "$param" | jq -r '.value // "unknown"')
                        echo "      $name: $value"
                    fi
                done < <(echo "$step" | jq -c '.parameters[]?')
            fi
            echo ""

            step_num=$((step_num + 1))
        fi
    done < <(echo "$plan_json" | jq -c '.next_steps[]?')
}

# Main execution function
main() {
    # Default number of candidate plans
    local NUM_PLANS=3

    # ----------------------------------------------
    # Parse optional CLI flags before task argument
    # Supported flags:
    #   -n, --num-plans <N>   Number of plans to generate (default 3)
    #   -h, --help           Show usage
    # ----------------------------------------------
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n|--num-plans)
                if [[ -z "$2" || "$2" =~ ^- ]]; then
                    echo "Error: --num-plans requires an integer argument" >&2
                    exit 1
                fi
                NUM_PLANS="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: $0 [-n NUM_PLANS] <task_description>"
                echo "Example: $0 -n 2 'Download and analyze the latest weather data'"
                return 0
                ;;
            --)
                shift
                break
                ;;
            *)
                # First non-flag argument is the task description
                break
                ;;
        esac
    done

    if [[ $# -eq 0 ]]; then
        echo "Usage: $0 [-n NUM_PLANS] <task_description>" >&2
        exit 1
    fi

    local task="$1"
    TASK="$task"  # Make task available globally for critic

    # Initialize run environment
    init_run

    # Display task header
    ui_header "🤖 Ostruct Agent Starting" "Sandboxed execution environment ready"
    ui_status "Task" "$task"
    ui_status "Run ID" "$RUN_ID"
    ui_status "Max turns" "$MAX_TURNS"
    ui_status "Max ostruct calls" "$MAX_OSTRUCT_CALLS"
    ui_status "Sandbox" "$SANDBOX_PATH"

    log_info "Task: $task"
    log_info "Max turns: $MAX_TURNS"
    log_info "Max ostruct calls: $MAX_OSTRUCT_CALLS"

    # Step 1: Generate multiple candidate plans
    ui_planning_phase "Creating Plan" "Creating ${NUM_PLANS} alternative plans"
    log_info "Generating ${NUM_PLANS} candidate plans in parallel"

    # Function to launch one planner with diversity
    gen_plan() {
        local idx="$1"
        local tmp="$SANDBOX_PATH/plan_${idx}.json"
        ui_plan_status "$((idx + 1))" "generating"
        # Add diversity via temperature and random token
        OSTRUCT_MODEL_PARAMS='{"temperature":0.9}' \
        ostruct_call "planner.j2" "state.schema.json" \
            -V "task=$task" \
            -V "sandbox_path=$SANDBOX_PATH" \
            -V "max_turns=$MAX_TURNS" \
            -V "diversity_token=$(uuidgen | head -c 8)" \
            --output-file "$tmp" \
            --file plan_schema "$SCHEMAS_DIR/plan_step.schema.json" &
        # Return PID for process management
        echo $!
    }

    # Launch planners in parallel as per NUM_PLANS
    pids=(); plan_files=()
    for ((i=0; i<NUM_PLANS; i++)); do
        pids[$i]=$(gen_plan "$i")
        plan_files[$i]="$SANDBOX_PATH/plan_${i}.json"
    done

    # Wait for all planners to complete and show progress
    local completed_count=0
    local failed_count=0
    local duplicate_count=0

    for i in "${!pids[@]}"; do
        local pid="${pids[$i]}"
        local file="${plan_files[$i]}"

        if wait "$pid"; then
            # Simple success status without shallow details
            if [[ -f "$file" && -s "$file" ]] && jq empty "$file" 2>/dev/null; then
                ui_plan_status "$((i + 1))" "completed"
                ((completed_count++))
                log_info "Plan $((i + 1)) generated successfully"
            else
                ui_plan_status "$((i + 1))" "failed" "Invalid or empty output"
                ((failed_count++))
                log_warn "Plan $((i + 1)) generated invalid output"
            fi
        else
            ui_plan_status "$((i + 1))" "failed" "Planner process failed"
            ((failed_count++))
            log_warn "Plan $((i + 1)) generation failed"
        fi
    done

    # Check for valid plan files and deduplicate
    unique_files=()
    seen_hashes=""  # Simple string to track seen hashes
    for i in "${!plan_files[@]}"; do
        local file="${plan_files[$i]}"
        if [[ -f "$file" && -s "$file" ]]; then
            # Check if file is valid JSON
            if jq empty "$file" 2>/dev/null; then
                # Generate hash for deduplication
                local hash=$(jq -S '.' "$file" | shasum -a 256 | cut -d' ' -f1)
                if [[ "$seen_hashes" != *"$hash"* ]]; then
                    unique_files+=("$file")
                    seen_hashes="$seen_hashes $hash"
                    log_info "Valid plan file: $file"
                else
                    ui_plan_status "$((i + 1))" "duplicate"
                    ((duplicate_count++))
                    ((completed_count--))  # Adjust completed count
                    log_info "Duplicate plan detected, skipping: $file"
                fi
            else
                ui_plan_status "$((i + 1))" "failed" "Invalid JSON output"
                ((failed_count++))
                ((completed_count--))  # Adjust completed count
                log_warn "Invalid JSON in plan file: $file"
            fi
        else
            if [[ $failed_count -eq 0 ]]; then
                # Only mark as failed if we haven't already counted this failure
                ui_plan_status "$((i + 1))" "failed" "No output file generated"
                ((failed_count++))
                ((completed_count--))  # Adjust completed count
            fi
            log_warn "Plan file missing or empty: $file"
        fi
    done

    # Show summary
    ui_plan_summary "${NUM_PLANS}" "$completed_count" "$failed_count" "$duplicate_count"

    local planner_output=""
    if [[ ${#unique_files[@]} -eq 0 ]]; then
        ui_step_error "Plan Generation" "All planners failed to generate valid plans"
        error_exit "All planners failed to generate valid plans"
    elif [[ ${#unique_files[@]} -eq 1 ]]; then
        ui_step_success "Plan Generation" "Using single valid plan"
        log_info "Using single valid plan"
        planner_output=$(cat "${unique_files[0]}")
    else
        # Build JSON array of candidates for selector
        plans_file="$SANDBOX_PATH/candidate_plans.json"
        jq -s '.' "${unique_files[@]}" > "$plans_file"

        # Call plan selector
        ui_planning_phase "Selecting Best Plan" "Evaluating ${#unique_files[@]} candidate plans"
        log_info "Running plan selector on ${#unique_files[@]} candidates"

        local selector_output_file="$SANDBOX_PATH/selector_output.json"
        if ostruct_call "plan_selector.j2" "plan_selector_out.schema.json" \
            -V "task=$task" \
            --file plans "$plans_file" \
            --output-file "$selector_output_file"; then
            selector_out=$(cat "$selector_output_file")
        else
            selector_out=""
        fi

        if [[ $? -ne 0 ]]; then
            ui_step_warning "Plan Selection" "Selector failed, using first plan"
            log_warn "Selector failed, using first plan"
            planner_output=$(cat "${unique_files[0]}")
        else
            # Extract winner and use selected plan
            winner_idx=$(echo "$selector_out" | jq -r '.winner_index // 0')
            comment=$(echo "$selector_out" | jq -r '.comment // "No comment"')

            # Validate index bounds
            if [[ $winner_idx -ge 0 && $winner_idx -lt ${#unique_files[@]} ]]; then
                # Show full reasoning without truncation
                ui_step_success "Plan Selection" "Selected plan $((winner_idx + 1))"
                if [[ -n "$comment" && "$comment" != "No comment" ]]; then
                    echo "  Reasoning: $comment"
                fi
                log_info "Selector chose plan index $winner_idx: $comment"
                planner_output=$(cat "${unique_files[$winner_idx]}")

                # Display the full selected plan in human-readable format
                display_selected_plan "$planner_output"
            else
                ui_step_warning "Plan Selection" "Invalid winner index $winner_idx, using first plan"
                log_warn "Invalid winner index $winner_idx, using first plan"
                planner_output=$(cat "${unique_files[0]}")

                # Display the full selected plan in human-readable format
                display_selected_plan "$planner_output"
            fi
        fi
    fi

    if [[ -z "$planner_output" ]]; then
        ui_step_error "Plan Generation" "Failed to generate valid initial plan"
        error_exit "Failed to generate valid initial plan"
    fi

    # Save initial state
    echo "$planner_output" > "$CURRENT_STATE_FILE"
    ui_step_success "Plan Initialization" "Initial state saved and ready for execution"
    log_info "Initial state saved"

    # Step 2: Turn-based execution loop
    ui_header "🔄 Executing" "Beginning turn-based task execution"
    while true; do
        TURN_COUNT=$((TURN_COUNT + 1))

        # Load current state
        if [[ ! -f "$CURRENT_STATE_FILE" ]]; then
            error_exit "State file not found"
        fi

        local current_state=$(cat "$CURRENT_STATE_FILE")
        CURRENT_STATE="$current_state"  # Make available globally for critic
        local completed=$(echo "$current_state" | jq -r '.completed')
        local current_turn=$(echo "$current_state" | jq -r '.current_turn')

        # Display turn header
        ui_turn_header "$TURN_COUNT" "$MAX_TURNS"
        log_info "=== Turn $TURN_COUNT/$MAX_TURNS ==="

        # Check if task is completed
        if [[ "$completed" == "true" ]]; then
            local final_answer=$(echo "$current_state" | jq -r '.final_answer')
            ui_final_result "true" "Task Completed Successfully" "$final_answer"
            log_info "Task completed!"
            echo "=== FINAL ANSWER ==="
            echo "$final_answer"
            echo "==================="
            break
        fi

        # Check if max turns reached
        if [[ $current_turn -gt $MAX_TURNS ]]; then
            ui_final_result "false" "Maximum Turns Reached" "Task incomplete after $MAX_TURNS turns"
            log_error "Maximum turns reached without completion"
            break
        fi

        # Extract and execute next steps
        local next_steps_array=$(echo "$current_state" | jq -c '.next_steps')
        local next_steps=$(echo "$current_state" | jq -c '.next_steps[]?')
        # Bail if next_steps is empty (planner misbehaved)
        if [[ -z "$next_steps" ]]; then
            ui_step_warning "Planning" "No next steps available, calling replanner"
            log_warn "Planner returned empty next_steps; calling replanner"
        else
            # Sort steps using DAG if enabled
            local sorted_next_steps_array
            ui_step_start "Dependency Analysis" "0" "0" "Analyzing step dependencies"
            sorted_next_steps_array=$(sort_steps_dag "$next_steps_array")

            if [[ $? -ne 0 ]]; then
                # If DAG sort failed, proceed with original next_steps
                ui_step_warning "Dependency Analysis" "DAG sort failed, proceeding with original order"
                log_warn "DAG sort failed, proceeding with original next_steps"
                sorted_next_steps_array="$next_steps_array"
            else
                # Extract steps from the JSON response
                sorted_next_steps_array=$(echo "$sorted_next_steps_array" | jq '.steps')
                ui_step_success "Dependency Analysis" "Steps sorted and ready for execution"
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
            local total_steps=$(echo "$sorted_next_steps_array" | jq 'length')

            ui_status "Step Execution" "Processing $total_steps steps in this turn"
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
                    local tool_name=$(echo "$step" | jq -r '.tool')
                    ui_step_warning "Step $((attempted_count + 1))/$total_steps" "Skipping previously blocked step: $tool_name"
                    log_warn "Skipping previously blocked step: $(echo "$step" | jq -r '.tool')"
                    # Count it as attempted so slicing drops it
                    attempted_count=$((attempted_count + 1))
                    continue
                fi

                attempted_count=$((attempted_count + 1))
                local tool_name=$(echo "$step" | jq -r '.tool')
                local reasoning=$(echo "$step" | jq -r '.reasoning')

                ui_step_start "$tool_name" "$attempted_count" "$total_steps" "$reasoning"
                log_info "Executing step: $(echo "$step" | jq -r '.tool')"
                local result=$(execute_step "$step")

                # Check if step was blocked by critic
                local blocked_by_critic=$(echo "$result" | jq -r '.blocked_by_critic // false')
                if [[ "$blocked_by_critic" == "true" ]]; then
                    local critic_score=$(echo "$result" | jq -r '.critic_score // 0')
                    local error_msg=$(echo "$result" | jq -r '.error // "Unknown error"')
                    ui_step_error "$tool_name" "Blocked by critic (score: $critic_score) - $error_msg"
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
                local duration=$(echo "$result" | jq -r '.duration // 0')
                if [[ "$success" == "true" ]]; then
                    local output=$(echo "$result" | jq -r '.output // ""')
                    ui_step_success "$tool_name" "$output" "$duration"
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
                    local error_msg=$(echo "$result" | jq -r '.error // "Unknown error"')
                    ui_step_error "$tool_name" "$error_msg"
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
        ui_planning_phase "Replanning" "Analyzing current state and generating next steps"
        log_info "Calling replanner"

        # Get block history summary for replanner context
        local block_history_summary
        block_history_summary=$(get_block_history_summary)
        local block_history_file="$SANDBOX_PATH/.block_history_summary.json"
        echo "$block_history_summary" > "$block_history_file"

        local replanner_output_file="$SANDBOX_PATH/replanner_output.json"
        if ostruct_call "replanner.j2" "replanner_out.schema.json" \
            -V "sandbox_path=$SANDBOX_PATH" \
            -V "max_turns=$MAX_TURNS" \
            --file current_state "$CURRENT_STATE_FILE" \
            --file block_history "$block_history_file" \
            --output-file "$replanner_output_file"; then
            replanner_output=$(cat "$replanner_output_file")
        else
            ui_step_error "Replanning" "Replanner call failed"
            error_exit "Replanner call failed"
        fi

        # ostruct_call now returns clean JSON via --output-file
        # Save updated state
        echo "$replanner_output" > "$CURRENT_STATE_FILE"
        ui_step_success "Replanning" "State updated with new plan"

        # Log state diff
        local prev_state="$current_state"
        local new_state="$replanner_output"
        log_debug "State diff: $(echo "$prev_state" | jq -S . | diff -u - <(echo "$new_state" | jq -S .) || true)"

        # Check turn limit
        if [[ $TURN_COUNT -ge $MAX_TURNS ]]; then
            ui_final_result "false" "Maximum Turns Reached" "Task incomplete after $MAX_TURNS turns"
            log_error "Maximum turns reached"
            break
        fi
    done

    # Step 3: Final cleanup and reporting
    ui_header "📊 Execution Summary" "Final results and statistics"
    ui_status "Total turns" "$TURN_COUNT"
    ui_status "Total ostruct calls" "$OSTRUCT_CALL_COUNT"
    ui_status "Sandbox location" "$SANDBOX_PATH"

    log_info "Execution completed"
    log_info "Total turns: $TURN_COUNT"
    log_info "Total ostruct calls: $OSTRUCT_CALL_COUNT"

    if [[ -f "$CURRENT_STATE_FILE" ]]; then
        local final_state=$(cat "$CURRENT_STATE_FILE")
        local completed=$(echo "$final_state" | jq -r '.completed')
        local error=$(echo "$final_state" | jq -r '.error // empty')

        if [[ "$completed" == "true" ]]; then
            ui_final_result "true" "Task Completed Successfully" "All objectives achieved"
            log_info "Task completed successfully"
        elif [[ -n "$error" ]]; then
            ui_final_result "false" "Task Failed" "$error"
            log_error "Task failed: $error"
        else
            ui_final_result "false" "Task Incomplete" "Task did not complete within the allowed turns"
            log_warn "Task incomplete"
        fi
    fi

    ui_status "Run completed" "$RUN_ID"
    log_info "Run completed: $RUN_ID"
}

# Run main function
main "$@"
