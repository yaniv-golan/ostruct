#!/bin/bash

# Sandboxed Agent Runner
# Provides safe, controlled execution of LLM-planned tasks using ostruct

set -euo pipefail

# Configuration
readonly MAX_TURNS=10
readonly MAX_OSTRUCT_CALLS=20
readonly LOG_DIR="logs"
readonly WORKDIR="workdir"
readonly FILE_SIZE_LIMIT=32768  # 32KB
readonly DOWNLOAD_SIZE_LIMIT=10485760  # 10MB

# Global counters
OSTRUCT_CALL_COUNT=0
TURN_COUNT=0

# Runtime variables
RUN_ID=""
SANDBOX_PATH=""
CURRENT_STATE_FILE=""
LOG_FILE=""

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Initialize run environment
init_run() {
    # Generate unique run ID
    RUN_ID=$(date '+%Y%m%d_%H%M%S')_$$
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/run_${RUN_ID}.log"
    
    # Create work directory
    mkdir -p "$WORKDIR"
    
    # Create sandbox for this run
    SANDBOX_PATH="$WORKDIR/sandbox_${RUN_ID}"
    mkdir -p "$SANDBOX_PATH"
    
    # State file
    CURRENT_STATE_FILE="$SANDBOX_PATH/.agent_state.json"
    
    log "INFO" "Starting run $RUN_ID"
    log "INFO" "Sandbox path: $SANDBOX_PATH"
    log "INFO" "Log file: $LOG_FILE"
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
        resolved_path=$(realpath -m "$input_path")
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
        
        if ostruct -t "$template" -s "$schema" "${args[@]}" 2>>"$LOG_FILE"; then
            log "INFO" "Ostruct call successful"
            return 0
        else
            local exit_code=$?
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
        if [[ $(stat -c%s "$safe_input") -gt $FILE_SIZE_LIMIT ]]; then
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
    if [[ $(stat -c%s "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
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
    if [[ $(stat -c%s "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
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
    if [[ $(stat -c%s "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
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
        current_size=$(stat -c%s "$safe_file")
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
    if [[ $(stat -c%s "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
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
    if [[ $(stat -c%s "$safe_file") -gt $FILE_SIZE_LIMIT ]]; then
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
            local actual_size=$(stat -c%s "$safe_file")
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
    
    case "$tool" in
        "jq")
            local filter=$(echo "$step_json" | jq -r '.filter')
            local input=$(echo "$step_json" | jq -r '.input // empty')
            output=$(execute_jq "$filter" "$input")
            ;;
        "grep")
            local pattern=$(echo "$step_json" | jq -r '.pattern')
            local file=$(echo "$step_json" | jq -r '.file')
            output=$(execute_grep "$pattern" "$file")
            ;;
        "sed")
            local expression=$(echo "$step_json" | jq -r '.expression')
            local file=$(echo "$step_json" | jq -r '.file')
            output=$(execute_sed "$expression" "$file")
            ;;
        "awk")
            local script=$(echo "$step_json" | jq -r '.script')
            local file=$(echo "$step_json" | jq -r '.file')
            output=$(execute_awk "$script" "$file")
            ;;
        "curl")
            local url=$(echo "$step_json" | jq -r '.url')
            output=$(execute_curl "$url")
            ;;
        "write_file")
            local path=$(echo "$step_json" | jq -r '.path')
            local content=$(echo "$step_json" | jq -r '.content')
            output=$(execute_write_file "$path" "$content")
            ;;
        "append_file")
            local path=$(echo "$step_json" | jq -r '.path')
            local content=$(echo "$step_json" | jq -r '.content')
            output=$(execute_append_file "$path" "$content")
            ;;
        "text_replace")
            local file=$(echo "$step_json" | jq -r '.file')
            local search=$(echo "$step_json" | jq -r '.search')
            local replace=$(echo "$step_json" | jq -r '.replace')
            output=$(execute_text_replace "$file" "$search" "$replace")
            ;;
        "read_file")
            local path=$(echo "$step_json" | jq -r '.path')
            output=$(execute_read_file "$path")
            ;;
        "download_file")
            local url=$(echo "$step_json" | jq -r '.url')
            local path=$(echo "$step_json" | jq -r '.path')
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
    
    # Step 1: Initial planner call
    log "INFO" "Calling initial planner"
    local planner_output
    planner_output=$(ostruct_call "templates/planner.j2" "schemas/state.schema.json" \
        -V "task=$task" \
        -V "sandbox_path=$SANDBOX_PATH" \
        -V "max_turns=$MAX_TURNS" \
        -J "tools=@tools.json")
    
    if [[ $? -ne 0 ]]; then
        error_exit "Initial planner call failed"
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
        local next_steps=$(echo "$current_state" | jq -r '.next_steps[]')
        if [[ -z "$next_steps" ]]; then
            log "WARN" "No next steps found, calling replanner"
        else
            # Execute each step
            local step_results="[]"
            while IFS= read -r step; do
                if [[ -n "$step" ]]; then
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
        local replanner_output
        replanner_output=$(ostruct_call "templates/replanner.j2" "schemas/replanner_out.schema.json" \
            -V "sandbox_path=$SANDBOX_PATH" \
            -V "max_turns=$MAX_TURNS" \
            -J "tools=@tools.json" \
            -J "current_state=@$CURRENT_STATE_FILE")
        
        if [[ $? -ne 0 ]]; then
            error_exit "Replanner call failed"
        fi
        
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