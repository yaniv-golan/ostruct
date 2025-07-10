#!/bin/bash

# Sandboxed Agent Runner
# Provides safe, controlled execution of LLM-planned tasks using ostruct

set -euo pipefail

# Directory of this script (agent root)
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repository root (two levels up from agent dir)
REPO_ROOT="$(cd "$AGENT_DIR/../.." && pwd)"

# Resolve ostruct executable once to avoid repeated Poetry startup overhead
OSTRUCT_BIN="$(cd "$REPO_ROOT" && poetry run which ostruct 2>/dev/null)"
if [[ -z "$OSTRUCT_BIN" ]]; then
    echo "Error: Unable to locate ostruct executable via poetry" >&2
    exit 1
fi

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
TASK=""
CURRENT_STATE=""

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

# Critic system functions
build_critic_input() {
    local step="$1"
    local turn="$2"

    # Truncate last observation to 1000 chars
    local last_obs_trunc=""
    if [[ -f "$SANDBOX_PATH/.last_observation" ]]; then
        last_obs_trunc=$(head -c 1000 "$SANDBOX_PATH/.last_observation")
    fi

    # Get plan remainder (first 3 steps)
    local plan_tail
    plan_tail=$(echo "$CURRENT_STATE" | jq '.next_steps[0:3]')

    # Get execution history tail (last 3 items)
    local hist_tail
    hist_tail=$(echo "$CURRENT_STATE" | jq '.execution_history[-3:]')

    # Get tool spec from tools.json
    local tool_name
    tool_name=$(echo "$step" | jq -r '.tool')
    local tool_spec
    tool_spec=$(jq --arg tool "$tool_name" \
        '.[$tool] // {"name": $tool, "description": "Unknown tool", "limits": {}}' \
        "$TOOLS_FILE")

    # Build comprehensive input
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

get_temporal_constraints() {
    local temporal_file="$SANDBOX_PATH/.temporal_constraints.json"
    if [[ -f "$temporal_file" ]]; then
        cat "$temporal_file"
    else
        echo '{"files_created":[],"files_expected":[],"deadline_turns":null}'
    fi
}

get_failure_patterns() {
    local patterns_file="$SANDBOX_PATH/.failure_patterns.json"
    if [[ -f "$patterns_file" ]]; then
        cat "$patterns_file"
    else
        echo '{"repeated_tool_failures":{},"stuck_iterations":false}'
    fi
}

get_safety_constraints() {
    echo '["no_file_ops_outside_sandbox","no_network_internal_ips","max_file_size_32kb"]'
}

update_temporal_constraints() {
    local action="$1"
    local file_path="$2"
    local temporal_file="$SANDBOX_PATH/.temporal_constraints.json"

    local temporal
    temporal=$(get_temporal_constraints)

    case "$action" in
        "file_created")
            temporal=$(echo "$temporal" | \
                jq --arg file "$file_path" '.files_created += [$file]')
            ;;
        "set_expected")
            temporal=$(echo "$temporal" | \
                jq --arg file "$file_path" '.files_expected += [$file]')
            ;;
        "set_deadline")
            local deadline="$file_path"  # Reuse param for deadline
            temporal=$(echo "$temporal" | \
                jq --arg deadline "$deadline" '.deadline_turns = ($deadline | tonumber)')
            ;;
    esac

    echo "$temporal" > "$temporal_file"
}

update_failure_patterns() {
    local tool="$1"
    local success="$2"
    local turn="$3"
    local patterns_file="$SANDBOX_PATH/.failure_patterns.json"

    local patterns
    patterns=$(get_failure_patterns)

    if [[ "$success" == "false" ]]; then
        # Increment failure count for tool
        patterns=$(echo "$patterns" | \
            jq --arg tool "$tool" \
            '.repeated_tool_failures[$tool] = (.repeated_tool_failures[$tool] // 0) + 1')
    fi

    # Check for stuck iterations (simple heuristic)
    if [[ -f "$SANDBOX_PATH/.prev_progress" ]]; then
        local prev_progress
        prev_progress=$(cat "$SANDBOX_PATH/.prev_progress")
        local current_progress
        current_progress=$(echo "$CURRENT_STATE" | jq '.execution_history | length')

        if [[ "$current_progress" == "$prev_progress" ]]; then
            patterns=$(echo "$patterns" | jq '.stuck_iterations = true')
        fi
    fi

    echo "$patterns" > "$patterns_file"

    # Update progress tracking
    echo "$CURRENT_STATE" | jq '.execution_history | length' > "$SANDBOX_PATH/.prev_progress"
}

record_critic_intervention() {
    local step_json="$1"
    local critic_out="$2"

    local intervention_file="$SANDBOX_PATH/.critic_interventions.jsonl"
    local intervention_entry
    intervention_entry=$(jq -n \
        --argjson turn "$TURN_COUNT" \
        --argjson step "$step_json" \
        --argjson critic_out "$critic_out" \
        '{turn: $turn, step: $step, critic_response: $critic_out, timestamp: (now | todate)}')

    echo "$intervention_entry" >> "$intervention_file"
}

# Generate a fingerprint for a step to detect identical patterns
generate_step_fingerprint() {
    local step_json="$1"

    # Create a normalized fingerprint that captures the essence of the step
    # Include tool, key parameters, but exclude reasoning/timestamps
    local fingerprint
    fingerprint=$(echo "$step_json" | jq -c '{
        tool: .tool,
        parameters: (.parameters | sort_by(.name) | map({name, value}))
    }' | shasum -a 256 | cut -d' ' -f1)

    echo "$fingerprint"
}

# Record a blocked step in the block history
record_blocked_step() {
    local step_json="$1"
    local critic_score="$2"
    local block_reason="$3"

    local block_history_file="$SANDBOX_PATH/.block_history.jsonl"
    local fingerprint
    fingerprint=$(generate_step_fingerprint "$step_json")

    # Check if this fingerprint already exists
    local existing_count=0
    if [[ -f "$block_history_file" ]]; then
        existing_count=$(grep -c "\"fingerprint\":\"$fingerprint\"" "$block_history_file" 2>/dev/null || echo "0")
        # Ensure it's a valid number (strip any whitespace/newlines)
        existing_count=$(echo "$existing_count" | tr -d '\n\r' | grep -E '^[0-9]+$' || echo "0")
    fi

    local block_entry
    block_entry=$(jq -n \
        --argjson turn "$TURN_COUNT" \
        --arg fingerprint "$fingerprint" \
        --argjson step "$step_json" \
        --argjson score "$critic_score" \
        --arg reason "$block_reason" \
        --argjson count "$((existing_count + 1))" \
        '{
            turn: $turn,
            fingerprint: $fingerprint,
            step: $step,
            critic_score: $score,
            block_reason: $reason,
            repeat_count: $count,
            timestamp: (now | todate)
        }')

    echo "$block_entry" >> "$block_history_file"

    if [[ $existing_count -gt 0 ]]; then
        log "WARN" "Blocked step fingerprint $fingerprint seen $((existing_count + 1)) times"
    fi
}

# Check if a step has been blocked before
is_step_previously_blocked() {
    local step_json="$1"
    local block_history_file="$SANDBOX_PATH/.block_history.jsonl"

    if [[ ! -f "$block_history_file" ]]; then
        return 1  # Not blocked (file doesn't exist)
    fi

    local fingerprint
    fingerprint=$(generate_step_fingerprint "$step_json")

    # Check if this fingerprint exists in block history
    if grep -q "\"fingerprint\":\"$fingerprint\"" "$block_history_file"; then
        # Get the repeat count for this fingerprint
        local repeat_count
        repeat_count=$(grep "\"fingerprint\":\"$fingerprint\"" "$block_history_file" | tail -1 | jq -r '.repeat_count')

        log "DEBUG" "Step fingerprint $fingerprint previously blocked $repeat_count times"
        return 0  # Previously blocked
    fi

    return 1  # Not previously blocked
}

# Get block history summary for replanner context
get_block_history_summary() {
    local block_history_file="$SANDBOX_PATH/.block_history.jsonl"

    if [[ ! -f "$block_history_file" ]]; then
        echo "[]"
        return
    fi

    # Get recent blocked patterns (last 10) with repeat counts
    local summary
    summary=$(tail -10 "$block_history_file" | jq -s 'map({
        fingerprint,
        tool: .step.tool,
        parameters: .step.parameters,
        block_reason,
        repeat_count,
        turn
    }) | group_by(.fingerprint) | map({
        fingerprint: .[0].fingerprint,
        tool: .[0].tool,
        parameters: .[0].parameters,
        block_reason: .[0].block_reason,
        total_repeats: (map(.repeat_count) | max),
        first_seen_turn: (map(.turn) | min),
        last_seen_turn: (map(.turn) | max)
    }) | sort_by(.total_repeats) | reverse')

    echo "$summary"
}

# Extract heuristic provides/requires from step JSON
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
                # text_replace both requires and provides the same file
                requires=$(jq -n --arg file "$file" '[$file]')
                provides=$(jq -n --arg file "$file" '[$file]')
            fi
            ;;
    esac

    # Add synthetic dependencies for pipes/stdout (future enhancement)
    # For now, keep it simple with file-based dependencies

    echo "$step_json" | jq --argjson provides "$provides" --argjson requires "$requires" \
        '. + {provides: $provides, requires: $requires}'
}

# Kahn topological sort implementation
kahn_sort() {
    # Create a temporary Python script for sorting (reads from stdin)
    local temp_script="$AGENT_DIR/.kahn_sort.py"

    # Write the Python script to a temporary file
    cat > "$temp_script" << 'EOF'
import json
import sys
from collections import defaultdict, deque

def kahn_sort(steps):
    """
    Kahn's algorithm for topological sorting
    Returns (sorted_steps, has_cycle)
    """
    # Build graph and in-degree count
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    nodes = {}

    # Initialize all nodes
    for i, step in enumerate(steps):
        node_id = f"step_{i}"
        nodes[node_id] = step
        in_degree[node_id] = 0

    # Build edges based on provides/requires
    for i, step in enumerate(steps):
        step_id = f"step_{i}"
        provides = step.get('provides', [])

        for j, other_step in enumerate(steps):
            if i == j:
                continue
            other_id = f"step_{j}"
            requires = other_step.get('requires', [])

            # If this step provides something that other step requires
            for provided in provides:
                if provided in requires:
                    graph[step_id].append(other_id)
                    in_degree[other_id] += 1

    # Kahn's algorithm
    queue = deque([node for node in nodes.keys() if in_degree[node] == 0])
    result = []

    while queue:
        current = queue.popleft()
        result.append(nodes[current])

        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Check for cycles
    has_cycle = len(result) != len(steps)

    return result, has_cycle

# Read input
try:
    steps = json.load(sys.stdin)
    if not steps:
        print(json.dumps({"error": None, "steps": []}))
        sys.exit(0)

    sorted_steps, has_cycle = kahn_sort(steps)

    if has_cycle:
        print(json.dumps({"error": "cycle_detected", "steps": []}))
    else:
        print(json.dumps({"error": None, "steps": sorted_steps}))
except json.JSONDecodeError as e:
    print(json.dumps({"error": "json_decode_error", "steps": []}), file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(json.dumps({"error": str(e), "steps": []}), file=sys.stderr)
    sys.exit(1)
EOF

    # Run the Python script
    python3 "$temp_script"

    # Clean up the temporary script
    rm -f "$temp_script"
}

# Sort steps using DAG
sort_steps_dag() {
    local steps_json="$1"

    log "DEBUG" "DAG sorting steps based on dependencies"

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

    log "DEBUG" "DAG sorting processed $step_count steps"
    log "DEBUG" "Tagged steps: $tagged_steps"

    # Run Kahn sort
    local sort_result
    sort_result=$(echo "$tagged_steps" | kahn_sort 2>&1)

    log "DEBUG" "Kahn sort result: $sort_result"

    local error
    error=$(echo "$sort_result" | jq -r '.error // empty' 2>/dev/null || echo "parse_error")

    log "DEBUG" "Kahn sort error: $error"

    if [[ "$error" == "cycle_detected" ]]; then
        log "ERROR" "Cycle detected in DAG, aborting turn"
        # Return empty array to trigger replanner
        echo "[]"
        return 1
    fi

    local sorted_steps
    sorted_steps=$(echo "$sort_result" | jq -c '.steps')

    log "DEBUG" "Extracted sorted steps: $sorted_steps"
    log "INFO" "DAG sort completed successfully"
    echo "$sorted_steps"
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

    # Check if --output-file is already specified in args
    local output_file=""
    local filtered_args=()
    local i=0
    while [[ $i -lt ${#args[@]} ]]; do
        if [[ "${args[$i]}" == "--output-file" ]]; then
            output_file="${args[$((i+1))]}"
            i=$((i+2))  # Skip both --output-file and its value
        else
            filtered_args+=("${args[$i]}")
            i=$((i+1))
        fi
    done

    local attempt=1
    local max_attempts=3
    local backoff_delays=(1 3 7)

    while [[ $attempt -le $max_attempts ]]; do
        log "DEBUG" "Attempt $attempt/$max_attempts"

        # Use provided output file or create temporary one
        local temp_output
        local cleanup_temp=false

        if [[ -n "$output_file" ]]; then
            temp_output="$output_file"
            log "DEBUG" "Using provided output file: $temp_output"
        else
            temp_output=$(mktemp 2>/dev/null)
            if [[ $? -ne 0 ]] || [[ -z "$temp_output" ]]; then
                log "ERROR" "Failed to create temporary file"
                return 1
            fi
            cleanup_temp=true
            log "DEBUG" "Created temporary output file: $temp_output"
        fi

        # Use cached ostruct executable to skip Poetry startup
        local ostr_cmd=("$OSTRUCT_BIN" run "${TEMPLATES_DIR}/$template" "${SCHEMAS_DIR}/$schema" --file tools "$TOOLS_FILE" --output-file "$temp_output" "${filtered_args[@]}")

        # Build simple command string for logging (avoid complex quoting)
        local cmd_str="poetry run ostruct run $template $schema --file tools [tools.json] --output-file [output] [args...]"
        log "DEBUG" "Running: ${cmd_str} (cwd: $REPO_ROOT)"

        # Run ostruct with all output properly redirected
        local exit_code=0
        (cd "$REPO_ROOT" && "${ostr_cmd[@]}" 2>>"$LOG_FILE") || exit_code=$?

        if [[ $exit_code -eq 0 ]]; then
            # Verify output file exists and has content
            if [[ -f "$temp_output" ]] && [[ -s "$temp_output" ]]; then
                # Return the clean JSON output from file
                cat "$temp_output"

                # Clean up temporary file only if we created it
                if [[ "$cleanup_temp" == "true" ]]; then
                    rm -f "$temp_output"
                fi

                log "INFO" "Ostruct call successful"
                return 0
            else
                log "WARN" "Ostruct completed but output file is empty or missing"
                exit_code=1
            fi
        fi

        # Clean up temp file on failure (only if we created it)
        if [[ "$cleanup_temp" == "true" ]]; then
            rm -f "$temp_output"
        fi

        log "WARN" "Ostruct call failed (attempt $attempt/$max_attempts), exit code: $exit_code"

        if [[ $attempt -lt $max_attempts ]]; then
            local delay=${backoff_delays[$((attempt-1))]}
            log "INFO" "Retrying in ${delay}s..."
            sleep $delay
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

    # Update temporal constraints
    update_temporal_constraints "file_created" "$path"

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

    # Update temporal constraints if file was created
    if [[ $current_size -eq 0 ]]; then
        update_temporal_constraints "file_created" "$path"
    fi

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

    # Check if critic is enabled (default: true)
    if [[ "${CRITIC_ENABLED:-true}" == "true" ]]; then
        # Build critic input
        local critic_input
        critic_input=$(build_critic_input "$step_json" "$TURN_COUNT")

        # Save critic input to temporary file
        local critic_input_file="$SANDBOX_PATH/.critic_input_${TURN_COUNT}.json"
        echo "$critic_input" > "$critic_input_file"

        # Call critic
        log "DEBUG" "Calling critic for step validation"
        local critic_out
        critic_out=$(ostruct_call "critic.j2" "critic_out.schema.json" \
            --file critic_input "$critic_input_file")

        if [[ $? -ne 0 ]]; then
            log "ERROR" "Critic call failed, proceeding without validation"
        else
            # Parse critic response
            local ok score comment
            ok=$(echo "$critic_out" | jq -r '.ok')
            score=$(echo "$critic_out" | jq -r '.score')
            comment=$(echo "$critic_out" | jq -r '.comment')

            log "CRITIC" "Score: $score, OK: $ok, Comment: $comment"

            # Apply blocking logic
            if [[ "$ok" == "false" ]] || (( score <= 2 )); then
                log "CRITIC" "BLOCKING step execution (score=$score)"

                # Apply patch if available
                local patch_len
                patch_len=$(echo "$critic_out" | jq '.patch | length')

                if (( patch_len > 0 )); then
                    log "CRITIC" "Applying $patch_len patch steps"
                    local patch
                    patch=$(echo "$critic_out" | jq '.patch')

                    # Prepend patch to next_steps in current state
                    CURRENT_STATE=$(echo "$CURRENT_STATE" | \
                        jq --argjson patch "$patch" '.next_steps = ($patch + .next_steps)')

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
                log "WARN" "Critic warning: $comment"
            fi
        fi

        # Clean up temporary file
        rm -f "$critic_input_file"
    fi

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
        CURRENT_STATE="$current_state"  # Make available globally for critic
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
        local next_steps_array=$(echo "$current_state" | jq -c '.next_steps')
        local next_steps=$(echo "$current_state" | jq -c '.next_steps[]?')
        # Bail if next_steps is empty (planner misbehaved)
        if [[ -z "$next_steps" ]]; then
            log "WARN" "Planner returned empty next_steps; calling replanner"
        else
            # Sort steps using DAG if enabled
            local sorted_next_steps_array
            sorted_next_steps_array=$(sort_steps_dag "$next_steps_array")

            if [[ $? -ne 0 ]]; then
                # If DAG sort failed, proceed with original next_steps
                log "WARN" "DAG sort failed, proceeding with original next_steps"
                sorted_next_steps_array="$next_steps_array"
            fi

            log "DEBUG" "sorted_next_steps_array: $sorted_next_steps_array"

            # Convert back to individual steps for execution
            local sorted_next_steps=$(echo "$sorted_next_steps_array" | jq -c '.[]?')
            log "DEBUG" "After jq conversion: $sorted_next_steps"

            # Execute each step
            local step_results="[]"
            local attempted_count=0  # count every step we process (executed or skipped)
            local created_paths="[]"
            local modified_paths="[]"
            log "DEBUG" "Starting step execution loop with sorted_next_steps: $sorted_next_steps"
            while IFS= read -r step; do
                log "DEBUG" "Processing step: $step"
                if [[ -z "$step" ]]; then
                    log "DEBUG" "Skipping empty step"
                    continue
                fi
                # Skip literal empty object
                if [[ "$step" == "{}" ]]; then
                    log "WARN" "Skipping empty step object {}"
                    continue
                fi

                # Ensure step is valid JSON
                echo "$step" | jq empty 2>/dev/null || { log "WARN" "Skipping invalid step JSON"; continue; }

                # Check if step has been previously blocked
                if is_step_previously_blocked "$step"; then
                    log "WARN" "Skipping previously blocked step: $(echo "$step" | jq -r '.tool')"
                    # Count it as attempted so slicing drops it
                    attempted_count=$((attempted_count + 1))
                    continue
                fi

                attempted_count=$((attempted_count + 1))
                log "INFO" "Executing step: $(echo "$step" | jq -r '.tool')"
                local result=$(execute_step "$step")

                # Check if step was blocked by critic
                local blocked_by_critic=$(echo "$result" | jq -r '.blocked_by_critic // false')
                if [[ "$blocked_by_critic" == "true" ]]; then
                    log "DEBUG" "Step blocked by critic"
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
                    log "INFO" "Step completed successfully"
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
                    log "WARN" "Step failed: $(echo "$result" | jq -r '.error')"
                fi
            done <<< "$sorted_next_steps"

            # Reload latest state (may include critic patches) and merge execution results
            local base_state=$(cat "$CURRENT_STATE_FILE")
            local updated_state=$(echo "$base_state" | jq \
                --argjson results "$step_results" \
                --argjson attempted "$attempted_count" \
                --argjson created "$created_paths" \
                --argjson modified "$modified_paths" \
                '.execution_history += $results | .next_steps = (.next_steps[$attempted:]) | .current_turn += 1 | .files_created += $created | .files_modified += $modified')

            echo "$updated_state" > "$CURRENT_STATE_FILE"

            # If critic injected new next_steps (patches) we already have work to do.
            # Skip replanner this turn – immediately continue execution loop.
            local pending_count
            pending_count=$(echo "$updated_state" | jq '.next_steps | length')
            if [[ $pending_count -gt 0 ]]; then
                log "INFO" "Skipping replanner – ${pending_count} pending step(s) from critic patch.";
                continue
            fi
        fi

        # Call replanner
        log "INFO" "Calling replanner"

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
