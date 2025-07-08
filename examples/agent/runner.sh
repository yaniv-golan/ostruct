#!/bin/bash

# Sandboxed Agent Runner
# Provides safe, controlled execution of LLM-planned tasks using ostruct

set -euo pipefail

# Directory of this script (agent root)
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repository root (two levels up from agent dir)
REPO_ROOT="$(cd "$AGENT_DIR/../.." && pwd)"

# Canonical sub-paths (absolute)
TEMPLATES_DIR="$AGENT_DIR/templates"
SCHEMAS_DIR="$AGENT_DIR/schemas"
TOOLS_FILE="$AGENT_DIR/tools.json"

# Configuration
readonly MAX_TURNS=10
readonly MAX_OSTRUCT_CALLS=24
readonly LOG_DIR="$AGENT_DIR/logs"
readonly WORKDIR="workdir"

# Will be set inside init_run after RUN_ID is defined
WORKDIR_PATH=""
SANDBOX_PATH=""
CURRENT_STATE_FILE=""

# File size limits
FILE_SIZE_LIMIT=$((32 * 1024))  # 32KB limit for file operations
DOWNLOAD_SIZE_LIMIT=$((10 * 1024 * 1024))  # 10MB limit for downloads

# Global counters
OSTRUCT_CALL_COUNT=0
TURN_COUNT=0

# Runtime variables
RUN_ID=""
LOG_FILE=""

# Portable helper to get file size in bytes (GNU/Linux and macOS/BSD)
file_size() {
    if stat -c%s "$1" >/dev/null 2>&1; then
        stat -c%s "$1"
    else
        stat -f%z "$1"
    fi
}

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    # Write to log file only, not stdout
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    # Also echo to terminal for user feedback
    echo "[$timestamp] [$level] $message" >&2
}

# Error handling
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Generate schemas from templates
generate_schemas() {
    log "INFO" "Generating schemas from templates"

    # Extract tool names from tools.json as JSON array
    local tool_names
    tool_names=$(jq -r 'keys | @json' "$TOOLS_FILE")

    if [[ $? -ne 0 ]]; then
        error_exit "Failed to extract tool names from $TOOLS_FILE"
    fi

    # Generate state.schema.json from template
    if [[ -f "$SCHEMAS_DIR/state.schema.json.template" ]]; then
        sed "s/__TOOL_NAMES__/$tool_names/g" \
            "$SCHEMAS_DIR/state.schema.json.template" > "$SCHEMAS_DIR/state.schema.json"
        log "DEBUG" "Generated state.schema.json with tools: $tool_names"
    fi

    # Generate plan_step.schema.json from template
    if [[ -f "$SCHEMAS_DIR/plan_step.schema.json.template" ]]; then
        sed "s/__TOOL_NAMES__/$tool_names/g" \
            "$SCHEMAS_DIR/plan_step.schema.json.template" > "$SCHEMAS_DIR/plan_step.schema.json"
        log "DEBUG" "Generated plan_step.schema.json with tools: $tool_names"
    fi

    # Generate replanner_out.schema.json from template
    if [[ -f "$SCHEMAS_DIR/replanner_out.schema.json.template" ]]; then
        sed "s/__TOOL_NAMES__/$tool_names/g" \
            "$SCHEMAS_DIR/replanner_out.schema.json.template" > "$SCHEMAS_DIR/replanner_out.schema.json"
        log "DEBUG" "Generated replanner_out.schema.json with tools: $tool_names"
    fi
}

# Initialize run environment
init_run() {
    # Generate unique run ID
    RUN_ID=$(date '+%Y%m%d_%H%M%S')_$$

    # Create log directory
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/run_${RUN_ID}.log"

    log "INFO" "Starting run $RUN_ID"
    log "INFO" "Sandbox path: $SANDBOX_PATH"
    log "INFO" "Log file: $LOG_FILE"

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
    log "INFO" "Sandbox path: $SANDBOX_PATH"
    log "INFO" "Log file: $LOG_FILE"

    # Generate schemas from templates
    generate_schemas
}

# Safe path resolution - ensures paths are within sandbox
safe_path() {
    local input_path="$1"
    local resolved_path

    # Handle relative paths
    if [[ "$input_path" != /* ]]; then
        input_path="$SANDBOX_PATH/$input_path"
    fi

    # Resolve with realpath if available, fallback to readlink
    if command -v realpath >/dev/null 2>&1; then
        # -m allows missing files (GNU and BSD both support this)
        resolved_path=$(realpath -m "$input_path" 2>/dev/null)
        # If realpath -m fails, try without -m, then fallback to input path
        if [[ -z "$resolved_path" ]]; then
            resolved_path=$(realpath "$input_path" 2>/dev/null || echo "$input_path")
        fi
    else
        resolved_path=$(readlink -f "$input_path" 2>/dev/null || echo "$input_path")
    fi

    # Ensure path is within sandbox
    if [[ "$resolved_path" != "$SANDBOX_PATH"* ]]; then
        error_exit "Path escape attempt detected: $input_path -> $resolved_path"
    fi

    echo "$resolved_path"
}

# Ostruct call wrapper with retry logic
ostruct_call() {
    local template="$1"
    local schema="$2"
    shift 2
    local args=("$@")

    OSTRUCT_CALL_COUNT=$((OSTRUCT_CALL_COUNT + 1))

    if [[ $OSTRUCT_CALL_COUNT -gt $MAX_OSTRUCT_CALLS ]]; then
        error_exit "Maximum ostruct calls ($MAX_OSTRUCT_CALLS) exceeded"
    fi

    log "INFO" "Ostruct call $OSTRUCT_CALL_COUNT/$MAX_OSTRUCT_CALLS: $template"

    local attempt=1
    local max_attempts=3
    local backoff_delays=(1 3 7)

    while [[ $attempt -le $max_attempts ]]; do
        log "DEBUG" "Attempt $attempt/$max_attempts"

        # Create temporary file for ostruct output
        local temp_output=$(mktemp)
        local ostr_cmd=(poetry run ostruct run "${TEMPLATES_DIR}/$template" "${SCHEMAS_DIR}/$schema" --file tools "$TOOLS_FILE" --output-file "$temp_output" "${args[@]}")

        # Build shell-escaped command string for accurate logging
        local cmd_str=""
        printf -v cmd_str '%q ' "${ostr_cmd[@]}"
        log "DEBUG" "Running: ${cmd_str}(cwd: $REPO_ROOT)"

        # Run ostruct with stderr going to log file only
        if (cd "$REPO_ROOT" && "${ostr_cmd[@]}" 2>>"$LOG_FILE"); then
            # Return the clean JSON output from file
            cat "$temp_output"
            rm -f "$temp_output"
            log "INFO" "Ostruct call successful"
            return 0
        else
            local exit_code=$?
            rm -f "$temp_output"
            log "WARN" "Ostruct call failed (attempt $attempt/$max_attempts), exit code: $exit_code"

            if [[ $attempt -lt $max_attempts ]]; then
                local delay=${backoff_delays[$((attempt-1))]}
                log "INFO" "Retrying in ${delay}s..."
                sleep $delay
            fi
        fi

        attempt=$((attempt + 1))
    done

    error_exit "Ostruct call failed after $max_attempts attempts"
}

# Tool execution functions
execute_jq() {
    local filter="$1"
    local input_file="${2:-}"

    log "DEBUG" "Executing jq filter: $filter"

    if [[ -n "$input_file" ]]; then
        local safe_input=$(safe_path "$input_file")
        if [[ ! -f "$safe_input" ]]; then
            echo "Error: Input file not found: $input_file"
            return 1
        fi

        # Check file size
        if [[ $(file_size "$safe_input") -gt $FILE_SIZE_LIMIT ]]; then
            echo "Error: Input file too large (max ${FILE_SIZE_LIMIT} bytes)"
            return 1
        fi

        timeout 30s jq "$filter" "$safe_input" 2>&1 | head -c $FILE_SIZE_LIMIT
    else
        timeout 30s jq "$filter" 2>&1 | head -c $FILE_SIZE_LIMIT
    fi
}

execute_grep() {
    local pattern="$1"
    local file="$2"

    local safe_file=$(safe_path "$file")
    if [[ ! -f "$safe_file" ]]; then
        echo "Error: File not found: $file"
        return 1
    fi

    # Check file size
    if [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
        echo "Error: File too large (max ${FILE_SIZE_LIMIT} bytes)"
        return 1
    fi

    log "DEBUG" "Executing grep pattern: $pattern on $file"
    timeout 30s grep -n "$pattern" "$safe_file" 2>&1 | head -c $FILE_SIZE_LIMIT
}

execute_sed() {
    local expression="$1"
    local file="$2"

    local safe_file=$(safe_path "$file")
    if [[ ! -f "$safe_file" ]]; then
        echo "Error: File not found: $file"
        return 1
    fi

    # Check file size
    if [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
        echo "Error: File too large (max ${FILE_SIZE_LIMIT} bytes)"
        return 1
    fi

    log "DEBUG" "Executing sed expression: $expression on $file"
    timeout 30s sed -n "$expression" "$safe_file" 2>&1 | head -c $FILE_SIZE_LIMIT
}

execute_awk() {
    local script="$1"
    local file="$2"

    local safe_file=$(safe_path "$file")
    if [[ ! -f "$safe_file" ]]; then
        echo "Error: File not found: $file"
        return 1
    fi

    # Check file size
    if [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
        echo "Error: File too large (max ${FILE_SIZE_LIMIT} bytes)"
        return 1
    fi

    log "DEBUG" "Executing awk script: $script on $file"
    timeout 30s awk "$script" "$safe_file" 2>&1 | head -c $FILE_SIZE_LIMIT
}

execute_curl() {
    local url="$1"

    log "DEBUG" "Executing curl: $url"
    timeout 60s curl -s -L --max-filesize $DOWNLOAD_SIZE_LIMIT "$url" 2>&1 | head -c $DOWNLOAD_SIZE_LIMIT
}

execute_write_file() {
    local path="$1"
    local content="$2"

    local safe_file=$(safe_path "$path")

    # Check content size
    if [[ ${#content} -gt $FILE_SIZE_LIMIT ]]; then
        echo "Error: Content too large (max ${FILE_SIZE_LIMIT} bytes)"
        return 1
    fi

    # Create directory if needed
    mkdir -p "$(dirname "$safe_file")"

    log "DEBUG" "Writing to file: $path"
    echo "$content" > "$safe_file"
    echo "Successfully wrote ${#content} bytes to $path"
}

execute_append_file() {
    local path="$1"
    local content="$2"

    local safe_file=$(safe_path "$path")

    # Check total size after append
    local current_size=0
    if [[ -f "$safe_file" ]]; then
        current_size=$(file_size "$safe_file")
    fi

    local total_size=$((current_size + ${#content}))
    if [[ $total_size -gt $FILE_SIZE_LIMIT ]]; then
        echo "Error: Total file size would exceed limit (max ${FILE_SIZE_LIMIT} bytes)"
        return 1
    fi

    # Create directory if needed
    mkdir -p "$(dirname "$safe_file")"

    log "DEBUG" "Appending to file: $path"
    echo "$content" >> "$safe_file"
    echo "Successfully appended ${#content} bytes to $path (total: $total_size bytes)"
}

execute_text_replace() {
    local file="$1"
    local search="$2"
    local replace="$3"

    local safe_file=$(safe_path "$file")
    if [[ ! -f "$safe_file" ]]; then
        echo "Error: File not found: $file"
        return 1
    fi

    # Check file size
    if [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
        echo "Error: File too large (max ${FILE_SIZE_LIMIT} bytes)"
        return 1
    fi

    # Safety check for search pattern
    if [[ -z "$search" ]]; then
        echo "Error: Search pattern cannot be empty"
        return 1
    fi

    local temp_file="${safe_file}.tmp"
    local hit_count=0

    log "DEBUG" "Executing text replace in: $file"

    # Use sed to perform replacement and count hits
    if sed "s/${search}/${replace}/g" "$safe_file" > "$temp_file"; then
        # Count replacements
        hit_count=$(grep -o "$replace" "$temp_file" | wc -l)

        if [[ $hit_count -gt 1000 ]]; then
            rm -f "$temp_file"
            echo "Error: Too many replacements (max 1000, found $hit_count)"
            return 1
        fi

        # Atomic replacement
        mv "$temp_file" "$safe_file"
        echo "Successfully replaced $hit_count occurrences of '$search' with '$replace'"
    else
        rm -f "$temp_file"
        echo "Error: Text replacement failed"
        return 1
    fi
}

execute_read_file() {
    local path="$1"

    local safe_file=$(safe_path "$path")
    if [[ ! -f "$safe_file" ]]; then
        echo "Error: File not found: $path"
        return 1
    fi

    # Check file size
    if [[ $(file_size "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
        echo "Error: File too large (max ${FILE_SIZE_LIMIT} bytes)"
        return 1
    fi

    log "DEBUG" "Reading file: $path"
    cat "$safe_file"
}

execute_download_file() {
    local url="$1"
    local path="$2"

    local safe_file=$(safe_path "$path")

    # Create directory if needed
    mkdir -p "$(dirname "$safe_file")"

    log "DEBUG" "Downloading $url to $path"

    if timeout 60s curl -s -L --max-filesize $DOWNLOAD_SIZE_LIMIT -o "$safe_file" "$url"; then
        # Double-check actual file size
        if [[ -f "$safe_file" ]]; then
            local actual_size=$(file_size "$safe_file")
            if [[ $actual_size -gt $DOWNLOAD_SIZE_LIMIT ]]; then
                rm -f "$safe_file"
                echo "Error: Downloaded file exceeds size limit"
                return 1
            fi
            echo "Successfully downloaded ${actual_size} bytes to $path"
        else
            echo "Error: Download failed - no file created"
            return 1
        fi
    else
        echo "Error: Download failed"
        return 1
    fi
}

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

    # Parse step JSON
    local tool=$(echo "$step_json" | jq -r '.tool')
    local reasoning=$(echo "$step_json" | jq -r '.reasoning')

    log "INFO" "Executing step: $tool - $reasoning"

    local output=""
    local success=true

    # Skip steps missing or null tool
    if [[ -z "$tool" || "$tool" == "null" ]]; then
        log "WARN" "Skipping invalid step: missing tool"
        return 1
    fi

    case "$tool" in
        "jq")
            local filter=$(get_param "$step_json" "filter")
            local input=$(get_param "$step_json" "input")
            output=$(execute_jq "$filter" "$input")
            ;;
        "grep")
            local pattern=$(get_param "$step_json" "pattern")
            local file=$(get_param "$step_json" "file")
            output=$(execute_grep "$pattern" "$file")
            ;;
        "sed")
            local expression=$(get_param "$step_json" "expression")
            local file=$(get_param "$step_json" "file")
            output=$(execute_sed "$expression" "$file")
            ;;
        "awk")
            local script=$(get_param "$step_json" "script")
            local file=$(get_param "$step_json" "file")
            output=$(execute_awk "$script" "$file")
            ;;
        "curl")
            local url=$(get_param "$step_json" "url")
            output=$(execute_curl "$url")
            ;;
        "write_file")
            local path=$(get_param "$step_json" "path")
            local content=$(get_param "$step_json" "content")
            output=$(execute_write_file "$path" "$content")
            ;;
        "append_file")
            local path=$(get_param "$step_json" "path")
            local content=$(get_param "$step_json" "content")
            output=$(execute_append_file "$path" "$content")
            ;;
        "text_replace")
            local file=$(get_param "$step_json" "file")
            local search=$(get_param "$step_json" "search")
            local replace=$(get_param "$step_json" "replace")
            output=$(execute_text_replace "$file" "$search" "$replace")
            ;;
        "read_file")
            local path=$(get_param "$step_json" "path")
            output=$(execute_read_file "$path")
            ;;
        "download_file")
            local url=$(get_param "$step_json" "url")
            local path=$(get_param "$step_json" "path")
            output=$(execute_download_file "$url" "$path")
            ;;
        *)
            output="Error: Unknown tool: $tool"
            success=false
            ;;
    esac

    # Check if command failed
    if [[ $? -ne 0 ]]; then
        success=false
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

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

    # Initialize run environment
    init_run

    log "INFO" "Task: $task"
    log "INFO" "Max turns: $MAX_TURNS"
    log "INFO" "Max ostruct calls: $MAX_OSTRUCT_CALLS"

    # Step 1: Generate multiple candidate plans
    log "INFO" "Generating 3 candidate plans in parallel"

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
        [[ -s "$f" ]] || { log "WARN" "plan $f missing, skipping"; continue; }

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
        log "INFO" "Only one unique plan generated, using it directly"
        planner_output=$(cat "${unique_files[0]}")
    else
        # Build JSON array of candidates for selector
        plans_file="$SANDBOX_PATH/candidate_plans.json"
        jq -s '.' "${unique_files[@]}" > "$plans_file"

        # Call plan selector
        log "INFO" "Running plan selector on ${#unique_files[@]} candidates"
        selector_out=$(ostruct_call "plan_selector.j2" "plan_selector_out.schema.json" \
            -V "task=$task" \
            --file plans "$plans_file")

        if [[ $? -ne 0 ]]; then
            log "WARN" "Selector failed, using first plan"
            planner_output=$(cat "${unique_files[0]}")
        else
            # Extract winner and use selected plan
            winner_idx=$(echo "$selector_out" | jq -r '.winner_index // 0')
            comment=$(echo "$selector_out" | jq -r '.comment // "No comment"')

            # Validate index bounds
            if [[ $winner_idx -ge 0 && $winner_idx -lt ${#unique_files[@]} ]]; then
                log "INFO" "Selector chose plan index $winner_idx: $comment"
                planner_output=$(cat "${unique_files[$winner_idx]}")
            else
                log "WARN" "Invalid winner index $winner_idx, using first plan"
                planner_output=$(cat "${unique_files[0]}")
            fi
        fi
    fi

    if [[ -z "$planner_output" ]]; then
        error_exit "Failed to generate valid initial plan"
    fi

    # Save initial state
    echo "$planner_output" > "$CURRENT_STATE_FILE"
    log "INFO" "Initial state saved"

    # Step 2: Turn-based execution loop
    while true; do
        TURN_COUNT=$((TURN_COUNT + 1))
        log "INFO" "=== Turn $TURN_COUNT/$MAX_TURNS ==="

        # Load current state
        if [[ ! -f "$CURRENT_STATE_FILE" ]]; then
            error_exit "State file not found"
        fi

        local current_state=$(cat "$CURRENT_STATE_FILE")
        local completed=$(echo "$current_state" | jq -r '.completed')
        local current_turn=$(echo "$current_state" | jq -r '.current_turn')

        # Check if task is completed
        if [[ "$completed" == "true" ]]; then
            log "INFO" "Task completed!"
            local final_answer=$(echo "$current_state" | jq -r '.final_answer')
            echo "=== FINAL ANSWER ==="
            echo "$final_answer"
            echo "==================="
            break
        fi

        # Check if max turns reached
        if [[ $current_turn -gt $MAX_TURNS ]]; then
            log "ERROR" "Maximum turns reached without completion"
            break
        fi

        # Extract and execute next steps
        local next_steps=$(echo "$current_state" | jq -c '.next_steps[]?')
        # Bail if next_steps is empty (planner misbehaved)
        if [[ -z "$next_steps" ]]; then
            log "WARN" "Planner returned empty next_steps; calling replanner"
        else
            # Execute each step
            local step_results="[]"
            while IFS= read -r step; do
                if [[ -z "$step" ]]; then
                    continue
                fi
                # Skip literal empty object
                if [[ "$step" == "{}" ]]; then
                    log "WARN" "Skipping empty step object {}"
                    continue
                fi

                # Ensure step is valid JSON
                echo "$step" | jq empty 2>/dev/null || { log "WARN" "Skipping invalid step JSON"; continue; }

                log "INFO" "Executing step: $(echo "$step" | jq -r '.tool')"
                local result=$(execute_step "$step")

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
                    log "INFO" "Step completed successfully"
                else
                    log "WARN" "Step failed: $(echo "$result" | jq -r '.error')"
                fi
            done <<< "$next_steps"

            # Update state with execution results
            local updated_state=$(echo "$current_state" | jq \
                --argjson results "$step_results" \
                '.execution_history += $results')

            echo "$updated_state" > "$CURRENT_STATE_FILE"
        fi

        # Call replanner
        log "INFO" "Calling replanner"
        replanner_output=$(ostruct_call "replanner.j2" "replanner_out.schema.json" \
            -V "sandbox_path=$SANDBOX_PATH" \
            -V "max_turns=$MAX_TURNS" \
            --file current_state "$CURRENT_STATE_FILE")

        if [[ $? -ne 0 ]]; then
            error_exit "Replanner call failed"
        fi

        # ostruct_call now returns clean JSON via --output-file
        # Save updated state
        echo "$replanner_output" > "$CURRENT_STATE_FILE"

        # Log state diff
        local prev_state="$current_state"
        local new_state="$replanner_output"
        log "DEBUG" "State diff: $(echo "$prev_state" | jq -S . | diff -u - <(echo "$new_state" | jq -S .) || true)"

        # Check turn limit
        if [[ $TURN_COUNT -ge $MAX_TURNS ]]; then
            log "ERROR" "Maximum turns reached"
            break
        fi
    done

    # Step 3: Final cleanup and reporting
    log "INFO" "Execution completed"
    log "INFO" "Total turns: $TURN_COUNT"
    log "INFO" "Total ostruct calls: $OSTRUCT_CALL_COUNT"

    if [[ -f "$CURRENT_STATE_FILE" ]]; then
        local final_state=$(cat "$CURRENT_STATE_FILE")
        local completed=$(echo "$final_state" | jq -r '.completed')
        local error=$(echo "$final_state" | jq -r '.error // empty')

        if [[ "$completed" == "true" ]]; then
            log "INFO" "Task completed successfully"
        elif [[ -n "$error" ]]; then
            log "ERROR" "Task failed: $error"
        else
            log "WARN" "Task incomplete"
        fi
    fi

    log "INFO" "Run completed: $RUN_ID"
}

# Run main function
main "$@"
