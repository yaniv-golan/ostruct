#!/bin/bash
# Extraction library - uses ostruct + LLM for intelligent command extraction from README files

# Extract ostruct commands from a README file using LLM
extract_ostruct_commands() {
    local readme_file="$1"
    local example_dir="$(dirname "$readme_file")"

    if [[ ! -f "$readme_file" ]]; then
        vlog "ERROR" "README file does not exist: $readme_file" >&2
        return 1
    fi

    vlog "DEBUG" "Using LLM to extract commands from: ${readme_file#${PROJECT_ROOT}/}" >&2

    # Prepare relative paths for the template
    local relative_example_dir="${example_dir#${PROJECT_ROOT}/}"

    # Create temporary output file for the extraction results
    local extraction_output="${TEMP_DIR}/extraction_$$.json"

    # Use ostruct to extract commands with LLM (using gpt-4.1 for better accuracy)
    local extraction_command="poetry run ostruct run ${VALIDATE_DIR}/templates/extract_commands.j2 ${VALIDATE_DIR}/schemas/extracted_commands.json"
    extraction_command+=" --file readme_content ${readme_file}"
    extraction_command+=" --var example_directory=${relative_example_dir}"
    extraction_command+=" --var readme_file=${readme_file#${PROJECT_ROOT}/}"
    extraction_command+=" --model gpt-4.1"
    extraction_command+=" --progress none"
    extraction_command+=" --output-file ${extraction_output}"

    vlog "DEBUG" "Extraction command: $extraction_command" >&2

    # Execute the extraction
    if ! eval "$extraction_command" >/dev/null 2>&1; then
        vlog "ERROR" "Failed to extract commands from ${readme_file#${PROJECT_ROOT}/}" >&2
        return 1
    fi

    # Check if extraction produced results
    if [[ ! -f "$extraction_output" ]]; then
        vlog "ERROR" "No extraction output produced for ${readme_file#${PROJECT_ROOT}/}" >&2
        return 1
    fi

    # Parse the JSON output and extract executable commands
    local commands
    commands=$(extract_executable_commands_from_json "$extraction_output" "$example_dir")

    # Clean up temporary file
    rm -f "$extraction_output"

    if [[ -n "$commands" ]]; then
        echo "$commands"
    fi
}

# Extract executable commands from the LLM's JSON output
extract_executable_commands_from_json() {
    local json_file="$1"
    local example_dir="$2"

    if [[ ! -f "$json_file" ]]; then
        vlog "DEBUG" "No JSON file to parse: $json_file" >&2
        return 1
    fi

    # Use jq to extract executable commands and format them for execution
    local commands
    commands=$(jq -r '
        .commands[]?
        | select(.type == "executable")
        | "cd \"\(.working_directory)\" && \(.command)"
    ' "$json_file" 2>/dev/null)

    if [[ -n "$commands" ]]; then
        vlog "DEBUG" "Extracted $(echo "$commands" | wc -l) executable commands" >&2
        echo "$commands"
    else
        vlog "DEBUG" "No executable commands found in JSON output" >&2
    fi
}

# Validate that extracted commands have required dependencies
validate_extracted_commands() {
    local commands="$1"
    local example_dir="$2"

    local valid_commands=""
    local command_count=0
    local valid_count=0

    while IFS= read -r command; do
        if [[ -z "$command" ]]; then
            continue
        fi

        ((command_count++))

        if validate_command_dependencies "$command" "$example_dir"; then
            valid_commands+="$command"$'\n'
            ((valid_count++))
        else
            vlog "WARN" "Command has missing dependencies: $command" >&2
        fi
    done <<< "$commands"

    vlog "DEBUG" "Validated $valid_count/$command_count commands" >&2

    if [[ -n "$valid_commands" ]]; then
        echo "$valid_commands" | head -n -1  # Remove trailing newline
    fi
}

# Validate that a command has all required files (enhanced version)
validate_command_dependencies() {
    local command="$1"
    local example_dir="$2"

    # Extract potential file paths from the command
    # Look for common file extensions that ostruct uses
    local file_patterns="[^[:space:]]*\.\(j2\|json\|yaml\|yml\|txt\|md\|py\|sh\)"
    local files
    files=$(echo "$command" | grep -o "$file_patterns" | sort -u)

    local missing_files=""
    while IFS= read -r file; do
        if [[ -n "$file" ]]; then
            # Try different path resolutions
            local file_exists=false

            # Check absolute path
            if [[ -f "$file" ]]; then
                file_exists=true
            # Check relative to example directory
            elif [[ -f "${example_dir}/${file}" ]]; then
                file_exists=true
            # Check relative to project root
            elif [[ -f "${PROJECT_ROOT}/${file}" ]]; then
                file_exists=true
            fi

            if [[ "$file_exists" == "false" ]]; then
                missing_files+="$file "
            fi
        fi
    done <<< "$files"

    if [[ -n "$missing_files" ]]; then
        vlog "DEBUG" "Missing files for command: $missing_files" >&2
        return 1
    fi

    return 0
}

# Get detailed extraction results for debugging
get_extraction_details() {
    local readme_file="$1"
    local extraction_output="${TEMP_DIR}/extraction_details_$$.json"

    # Run extraction again but keep the full JSON output
    local extraction_command="poetry run ostruct run ${VALIDATE_DIR}/templates/extract_commands.j2 ${VALIDATE_DIR}/schemas/extracted_commands.json"
    extraction_command+=" --file readme_content ${readme_file}"
    extraction_command+=" --var example_directory=$(dirname "$readme_file")"
    extraction_command+=" --model gpt-4.1"
    extraction_command+=" --progress none"
    extraction_command+=" --output-file ${extraction_output}"

    if eval "$extraction_command" >/dev/null 2>&1 && [[ -f "$extraction_output" ]]; then
        cat "$extraction_output"
        rm -f "$extraction_output"
    else
        echo '{"error": "Failed to extract details"}'
    fi
}

# Test the extraction system with a simple example
test_extraction() {
    local readme_file="$1"

    vlog "INFO" "Testing extraction on: ${readme_file#${PROJECT_ROOT}/}" >&2

    # Test basic extraction
    local commands
    commands=$(extract_ostruct_commands "$readme_file")

    if [[ -n "$commands" ]]; then
        vlog "INFO" "Successfully extracted commands:" >&2
        echo "$commands" | while IFS= read -r cmd; do
            vlog "INFO" "  - $cmd" >&2
        done
    else
        vlog "WARN" "No commands extracted" >&2

        # Show detailed extraction results for debugging
        vlog "DEBUG" "Detailed extraction results:" >&2
        get_extraction_details "$readme_file" | jq . 2>/dev/null || echo "Failed to get extraction details"
    fi
}
