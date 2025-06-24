#!/bin/bash
# Execution library - handles two-phase command execution (dry-run then live)

# Import color definitions if not already defined
if [[ -z "${RED:-}" ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    MAGENTA='\033[0;35m'
    NC='\033[0m' # No Color
fi

# Execute all commands from a commands file
execute_commands_from_file() {
    local commands_file="$1"
    local readme_file="$2"
    local example_name="${readme_file#${EXAMPLES_DIR}/}"
    example_name="${example_name%/README.md}"

    if [[ ! -f "$commands_file" || ! -s "$commands_file" ]]; then
        vlog "DEBUG" "No commands to execute for: $example_name"
        return 0
    fi

    # Read all lines into an array to avoid file descriptor issues
    local commands_array=()
    while IFS= read -r line; do
        commands_array+=("$line")
    done < "$commands_file"

    # Count actual commands (excluding empty lines and comments)
    local total_commands=0
    for line in "${commands_array[@]}"; do
        if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
            ((total_commands++))
        fi
    done

    vlog "PROGRESS" "Found ${total_commands} commands to validate"

    local command_count=0
    local success_count=0
    local dry_fail_count=0
    local live_fail_count=0
    local placeholder_count=0

    # Temporarily disable exit-on-error for command execution
    set +e

    vlog "DEBUG" "Read ${#commands_array[@]} lines from commands file"

    # Process each command
    for line in "${commands_array[@]}"; do
        vlog "DEBUG" "Processing line: '$line'"
        if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
            vlog "DEBUG" "Skipping empty or comment line"
            continue
        fi

        ((command_count++))

        # Show command progress with a smaller separator
        echo -e "\n${BLUE}───── Command ${command_count}/${total_commands} ─────${NC}" >&2

        # Parse command type and actual command
        local command_type=""
        local command=""

        if [[ "$line" =~ ^EXECUTABLE: ]]; then
            command_type="EXECUTABLE"
            command="${line#EXECUTABLE:}"
        elif [[ "$line" =~ ^PLACEHOLDER: ]]; then
            command_type="PLACEHOLDER"
            command="${line#PLACEHOLDER:}"
        else
            # Legacy format - assume executable
            command_type="EXECUTABLE"
            command="$line"
        fi

        # Display the command being processed (truncate if too long)
        local display_command="$command"
        if [[ ${#display_command} -gt 80 ]]; then
            display_command="${display_command:0:77}..."
        fi
        vlog "INFO" "Command: ${display_command}"

        # Handle different command types
        case "$command_type" in
            "EXECUTABLE")
                # Execute two-phase validation for executable commands
                vlog "DEBUG" "About to execute two-phase validation for command $command_count"
                local result=$(execute_two_phase_validation "$command" "$example_name")
                vlog "DEBUG" "Two-phase validation returned: $result"

                case "$result" in
                    "PASS")
                        ((success_count++))
                        record_result "$example_name" "$command" "PASS" ""
                        if [[ "$DRY_RUN_ONLY" == "true" ]]; then
                            vlog "SUCCESS" "✅ Command passed dry-run validation"
                        else
                            vlog "SUCCESS" "✅ Command passed both dry-run and live execution"
                        fi
                        ;;
                    "DRY_FAIL")
                        ((dry_fail_count++))
                        record_result "$example_name" "$command" "DRY_FAIL" "Dry-run validation failed"
                        vlog "ERROR" "❌ Command failed dry-run validation"
                        ;;
                    "LIVE_FAIL")
                        ((live_fail_count++))
                        record_result "$example_name" "$command" "LIVE_FAIL" "Live execution failed"
                        vlog "ERROR" "❌ Command failed live execution (dry-run passed)"
                        ;;
                    *)
                        vlog "ERROR" "Unknown result from two-phase validation: $result"
                        ;;
                esac
                ;;
            "PLACEHOLDER")
                # Validate syntax only for placeholder commands
                ((placeholder_count++))
                vlog "INFO" "📋 Placeholder command - validating syntax only"

                if validate_placeholder_command_syntax "$command" "$example_name"; then
                    ((success_count++))
                    record_result "$example_name" "$command" "SYNTAX_VALID" "Placeholder command syntax validated"
                    vlog "SUCCESS" "✅ Placeholder command syntax is valid"
                else
                    ((dry_fail_count++))
                    record_result "$example_name" "$command" "SYNTAX_ERROR" "Placeholder command syntax invalid"
                    vlog "ERROR" "❌ Placeholder command syntax is invalid"
                fi
                ;;
        esac

        vlog "DEBUG" "Completed processing command $command_count, continuing to next"

    done

    # Re-enable exit-on-error
    set -e

    # Show summary for this example
    echo -e "\n${CYAN}── Example Summary ──${NC}" >&2
    if [[ $command_count -gt 0 ]]; then
        echo -e "${CYAN}Total commands: ${command_count}${NC}" >&2
        echo -e "${GREEN}✅ Passed: ${success_count}${NC}" >&2
        if [[ $placeholder_count -gt 0 ]]; then
            echo -e "${BLUE}📋 Placeholders: ${placeholder_count} (syntax validated only)${NC}" >&2
        fi
        if [[ $dry_fail_count -gt 0 ]]; then
            echo -e "${YELLOW}⚠️  Failed validation: ${dry_fail_count}${NC}" >&2
        fi
        if [[ $live_fail_count -gt 0 ]]; then
            echo -e "${RED}❌ Failed execution: ${live_fail_count}${NC}" >&2
        fi

        if [[ $dry_fail_count -gt 0 || $live_fail_count -gt 0 ]]; then
            if [[ "${SKIP_ERROR_ANALYSIS:-false}" != "true" ]]; then
                echo -e "${YELLOW}⏱️  Note: Error analysis was performed for failed commands${NC}" >&2
            fi
        fi
    fi
}

# Execute two-phase validation for a single command
execute_two_phase_validation() {
    local command="$1"
    local example_name="$2"

    # Phase 1: Dry-run validation
    vlog "DEBUG" "Phase 1 - Dry-run validation for: $example_name"

    local wrapped_command=$(wrap_ostruct_with_poetry "$command")
    local dry_run_command=$(add_dry_run_flag "$wrapped_command")
    local dry_run_result=$(execute_single_command "$dry_run_command" "$example_name" "dry-run")

    if [[ "$dry_run_result" != "SUCCESS" ]]; then
        vlog "ERROR" "Dry-run failed for $example_name: $command"

        # Analyze the error using LLM for better categorization (unless disabled)
        if [[ "${SKIP_ERROR_ANALYSIS:-false}" != "true" ]]; then
            analyze_command_failure "$command" "$example_name" "dry-run" || true  # Don't let analysis failure break the loop
        fi

        return_execution_result "DRY_FAIL"
        return
    fi

    vlog "SUCCESS" "Dry-run passed for: $example_name"

    # Phase 2: Live execution (only if not in dry-run-only mode)
    if [[ "$DRY_RUN_ONLY" == "true" ]]; then
        vlog "INFO" "Skipping live execution (dry-run-only mode)"
        return_execution_result "PASS"
        return
    fi

    vlog "DEBUG" "Phase 2 - Live execution for: $example_name"

    local wrapped_command=$(wrap_ostruct_with_poetry "$command")
    local live_result=$(execute_single_command "$wrapped_command" "$example_name" "live")

    if [[ "$live_result" != "SUCCESS" ]]; then
        vlog "ERROR" "Live execution failed for $example_name: $command"

        # Analyze the error using LLM for better categorization (unless disabled)
        if [[ "${SKIP_ERROR_ANALYSIS:-false}" != "true" ]]; then
            analyze_command_failure "$command" "$example_name" "live" || true  # Don't let analysis failure break the loop
        fi

        return_execution_result "LIVE_FAIL"
        return
    fi

    vlog "SUCCESS" "Live execution passed for: $example_name"
    return_execution_result "PASS"
}

# Wrap ostruct commands with poetry run for reliable execution
wrap_ostruct_with_poetry() {
    local command="$1"

    # Replace 'ostruct ' with 'poetry run ostruct ' in the command
    # This handles cases like: cd "examples/..." && ostruct run ...
    echo "$command" | sed 's/\bostruct /poetry run ostruct /g'
}

# Add --dry-run flag to a command
add_dry_run_flag() {
    local command="$1"

    # Check if --dry-run is already present
    if [[ "$command" =~ --dry-run ]]; then
        echo "$command"
        return
    fi

    # Add --dry-run before any output redirection or pipes
    if [[ "$command" =~ [[:space:]]+(\>|\>\>|\|) ]]; then
        echo "$command" | sed 's/\([[:space:]]\+\)\(>\|>>\||\)/\1--dry-run \2/'
    else
        echo "$command --dry-run"
    fi
}

# Execute a single command with timeout and error handling
execute_single_command() {
    local command="$1"
    local example_name="$2"
    local phase="$3"  # "dry-run" or "live"

    # Create temporary directory for this execution
    local exec_temp_dir="${TEMP_DIR}/${example_name//\//_}_${phase}_$$"
    mkdir -p "$exec_temp_dir"

    # Prepare output files
    local stdout_file="${exec_temp_dir}/stdout"
    local stderr_file="${exec_temp_dir}/stderr"
    local exit_code_file="${exec_temp_dir}/exit_code"

    vlog "DEBUG" "Executing ($phase): $command"

    # Execute command with timeout
    (
        # Set up execution environment
        export OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS=1
        export OSTRUCT_LOG_LEVEL=ERROR  # Reduce noise in output

        # Execute the command (already wrapped with poetry at higher level)
        timeout "$TIMEOUT" bash -c "$command" > "$stdout_file" 2> "$stderr_file"
        echo $? > "$exit_code_file"
    ) &

    local exec_pid=$!
    wait $exec_pid
    local wait_result=$?

    # Read results
    local exit_code=1
    if [[ -f "$exit_code_file" ]]; then
        exit_code=$(cat "$exit_code_file")
    fi

    local stdout_content=""
    if [[ -f "$stdout_file" ]]; then
        stdout_content=$(cat "$stdout_file")
    fi

    local stderr_content=""
    if [[ -f "$stderr_file" ]]; then
        stderr_content=$(cat "$stderr_file")
    fi

    # Check for timeout
    if [[ $wait_result -eq 124 ]]; then
        vlog "ERROR" "Command timed out after ${TIMEOUT}s: $command"
        cleanup_exec_temp_dir "$exec_temp_dir"
        echo "TIMEOUT"
        return
    fi

    # Validate execution result
    local validation_result=$(validate_command_output "$exit_code" "$stdout_content" "$stderr_content" "$phase" "$command")

    # Log output if verbose or if there was an error
    if [[ "$VERBOSE" == "true" || "$validation_result" != "SUCCESS" ]]; then
        vlog "DEBUG" "Exit code: $exit_code"
        if [[ -n "$stdout_content" ]]; then
            vlog "DEBUG" "STDOUT: $stdout_content"
        fi
        if [[ -n "$stderr_content" ]]; then
            vlog "DEBUG" "STDERR: $stderr_content"
        fi
    fi

    # Store execution details for reporting
    store_execution_details "$example_name" "$command" "$phase" "$exit_code" "$stdout_content" "$stderr_content"

    cleanup_exec_temp_dir "$exec_temp_dir"

    # Return the validation result
    echo "$validation_result"
}

# Store execution details for later reporting
store_execution_details() {
    local example_name="$1"
    local command="$2"
    local phase="$3"
    local exit_code="$4"
    local stdout_content="$5"
    local stderr_content="$6"

    local details_dir="${CACHE_DIR}/execution_details"
    mkdir -p "$details_dir"

    local details_file="${details_dir}/${example_name//\//_}_${phase}.json"

    # Use jq to properly escape all strings
    jq -n \
        --arg example "$example_name" \
        --arg command "$command" \
        --arg phase "$phase" \
        --argjson exit_code "$exit_code" \
        --arg stdout "$stdout_content" \
        --arg stderr "$stderr_content" \
        --arg timestamp "$(date -Iseconds)" \
        '{
            "example": $example,
            "command": $command,
            "phase": $phase,
            "exit_code": $exit_code,
            "stdout": $stdout,
            "stderr": $stderr,
            "timestamp": $timestamp
        }' > "$details_file"
}

# Clean up temporary execution directory
cleanup_exec_temp_dir() {
    local exec_temp_dir="$1"
    if [[ -d "$exec_temp_dir" ]]; then
        rm -rf "$exec_temp_dir"
    fi
}

# Return execution result (helper function)
return_execution_result() {
    echo "$1"
}

# Analyze command failure using LLM for intelligent error categorization
analyze_command_failure() {
    local command="$1"
    local example_name="$2"
    local phase="$3"  # "dry-run" or "live"

    # Find the execution details file
    local details_dir="${CACHE_DIR}/execution_details"
    local details_file="${details_dir}/${example_name//\//_}_${phase}.json"

    if [[ ! -f "$details_file" ]]; then
        vlog "WARN" "No execution details found for error analysis: $details_file"
        return 1
    fi

    # Extract error information from execution details
    local exit_code stderr_content
    exit_code=$(jq -r '.exit_code' "$details_file" 2>/dev/null || echo "1")
    stderr_content=$(jq -r '.stderr' "$details_file" 2>/dev/null || echo "")

    # If stderr is empty, also include stdout (sometimes errors go there)
    if [[ -z "$stderr_content" ]]; then
        local stdout_content
        stdout_content=$(jq -r '.stdout' "$details_file" 2>/dev/null || echo "")
        stderr_content="$stdout_content"
    fi

    # Create temporary error output file for analysis
    local error_output_file="${TEMP_DIR}/error_output_${example_name//\//_}_${phase}_$$.txt"
    echo "$stderr_content" > "$error_output_file"

    # Create analysis output file
    local analysis_output="${TEMP_DIR}/error_analysis_${example_name//\//_}_${phase}_$$.json"

    vlog "INFO" "🔍 Analyzing error for: $example_name ($phase) - this may take 10-20 seconds..."

    # Use ostruct to analyze the failure with LLM
    local analysis_command="poetry run ostruct run ${VALIDATE_DIR}/templates/analyze_error.j2 ${VALIDATE_DIR}/schemas/error_analysis.json"
    analysis_command+=" --file error_output $error_output_file"
    analysis_command+=" --var command=\"$command\""
    analysis_command+=" --var exit_code=\"$exit_code\""
    analysis_command+=" --model gpt-4.1"
    analysis_command+=" --progress none"
    analysis_command+=" --output-file $analysis_output"

    # Add ostruct help JSON for syntax awareness if available
    if [[ -n "${OSTRUCT_HELP_JSON_FILE:-}" && -f "${OSTRUCT_HELP_JSON_FILE}" ]]; then
        analysis_command+=" --file ostruct_help ${OSTRUCT_HELP_JSON_FILE}"
        vlog "DEBUG" "Including ostruct syntax reference for error analysis"
    fi

    # Execute the analysis (use dry-run to avoid API costs if not needed)
    if eval "$analysis_command --dry-run" >/dev/null 2>&1; then
        # Dry-run successful, now do live analysis
        if eval "$analysis_command" >/dev/null 2>&1 && [[ -f "$analysis_output" ]]; then
            # Extract and display analysis results
            local category root_cause primary_solution
            category=$(jq -r '.category' "$analysis_output" 2>/dev/null || echo "UNKNOWN_ERROR")
            root_cause=$(jq -r '.root_cause' "$analysis_output" 2>/dev/null || echo "Failed to analyze error")
            primary_solution=$(jq -r '.solutions[] | select(.priority=="primary" or .priority=="high") | .solution' "$analysis_output" 2>/dev/null | head -1)

            # Enhanced error reporting
            vlog "ERROR" "[$category] $root_cause"
            if [[ -n "$primary_solution" ]]; then
                vlog "INFO" "💡 Solution: $primary_solution"
            fi

            # Store analysis results for reporting
            local analysis_dir="${CACHE_DIR}/error_analysis"
            mkdir -p "$analysis_dir"
            cp "$analysis_output" "${analysis_dir}/${example_name//\//_}_${phase}.json"

            vlog "DEBUG" "Error analysis completed for: $example_name ($phase)"
        else
            vlog "DEBUG" "Failed to complete error analysis for: $example_name ($phase)"
        fi
    else
        vlog "DEBUG" "Error analysis template validation failed for: $example_name ($phase)"
    fi

    # Clean up temporary files
    rm -f "$error_output_file" "$analysis_output"
}
