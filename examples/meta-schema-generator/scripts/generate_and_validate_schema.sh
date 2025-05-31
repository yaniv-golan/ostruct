#!/bin/bash

# Meta-Schema Generator for ostruct
# Generates and validates JSON schemas from user prompt templates

set -euo pipefail

# Default configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_OSTRUCT_CMD="ostruct"
DEFAULT_VALIDATOR_CMD="ajv"
MAX_RETRIES=3
TEMP_DIR=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] TARGET_TEMPLATE

Generate and validate a JSON schema from a user prompt template using ostruct.

ARGUMENTS:
    TARGET_TEMPLATE     Path to the user's Jinja2 template file

OPTIONS:
    -o, --output FILE          Output file for the final validated schema (default: stdout)
    -s, --ostruct-cmd CMD      Path to ostruct executable (default: ostruct)
    -v, --validator-cmd CMD    JSON Schema validator command (default: ajv)
    -r, --max-retries NUM      Maximum refinement retries (default: 3)
    -t, --temp-dir DIR         Temporary directory for intermediate files
    -h, --help                 Show this help message

EXAMPLES:
    $0 my_template.j2
    $0 -o schema.json -r 5 templates/user_template.j2
    $0 --ostruct-cmd ./bin/ostruct --validator-cmd jsonschema templates/extract.j2

PREREQUISITES:
    - ostruct must be installed and accessible
    - A JSON Schema validator CLI (ajv-cli recommended: npm install -g ajv-cli)
    - jq for JSON processing

For more information, see the README.md in the examples/meta-schema-generator/ directory.
EOF
}

# Function to cleanup temp files
cleanup() {
    if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
        rm -rf "${TEMP_DIR}"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Function to validate prerequisites
check_prerequisites() {
    local missing_deps=()

    # Check ostruct - prefer poetry if available in project directory
    if command -v poetry &> /dev/null && [[ -f "pyproject.toml" ]]; then
        OSTRUCT_CMD="poetry run ostruct"
        print_status "$YELLOW" "Using poetry run ostruct from project directory"
    elif ! command -v "${OSTRUCT_CMD}" &> /dev/null; then
        missing_deps+=("ostruct (${OSTRUCT_CMD})")
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    # Check validator
    if ! command -v "${VALIDATOR_CMD}" &> /dev/null; then
        missing_deps+=("JSON Schema validator (${VALIDATOR_CMD})")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_status "$RED" "Error: Missing required dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        echo
        echo "📋 Installation Instructions:"
        echo "  jq:       brew install jq (macOS) | apt install jq (Ubuntu) | yum install jq (RHEL)"
        echo "  ajv-cli:  npm install -g ajv-cli"
        echo "  jsonschema: pip install jsonschema (alternative validator)"
        echo "  ostruct:  poetry install (development) | pip install ostruct-cli"
        echo
        echo "For detailed instructions, see: examples/meta-schema-generator/README.md"
        exit 1
    fi
}

# Function to calculate SHA256 hash of a file
calculate_hash() {
    local file=$1
    if command -v sha256sum &> /dev/null; then
        sha256sum "$file" | cut -d' ' -f1
    elif command -v shasum &> /dev/null; then
        shasum -a 256 "$file" | cut -d' ' -f1
    else
        print_status "$RED" "Error: No SHA256 utility found (sha256sum or shasum)"
        echo "These utilities are usually pre-installed. If missing:"
        echo "  Linux: sudo apt install coreutils"
        echo "  macOS: Should be pre-installed with shasum"
        echo "  Windows: Use WSL or Git Bash"
        exit 1
    fi
}

# Function to invoke ostruct for schema generation
generate_schema() {
    local target_template=$1
    local prompt_template=$2
    local output_schema=$3
    local temp_output=$4
    local additional_vars=$5

    print_status "$BLUE" "Generating schema using ostruct..."

    # Build ostruct command
    if [[ "${OSTRUCT_CMD}" == "poetry run ostruct" ]]; then
        local cmd=(
            poetry run ostruct run
            "${prompt_template}"
            "${output_schema}"
            --fta user_template "${target_template}"
        )
    else
        local cmd=(
            "${OSTRUCT_CMD}" run
            "${prompt_template}"
            "${output_schema}"
            --fta user_template "${target_template}"
        )
    fi

    # Add any additional variables
    if [[ -n "${additional_vars}" ]]; then
        # Split additional_vars by space and add each as a parameter
        read -ra VARS <<< "${additional_vars}"
        for var in "${VARS[@]}"; do
            cmd+=(-ft "${var}")
        done
    fi

    cmd+=(--output-file "${temp_output}")

    print_status "$YELLOW" "Running: ${cmd[*]}"

    if ! "${cmd[@]}"; then
        print_status "$RED" "Error: ostruct command failed"
        return 1
    fi

    if [[ ! -f "${temp_output}" ]]; then
        print_status "$RED" "Error: ostruct did not create output file"
        return 1
    fi

    print_status "$GREEN" "Schema generation completed"
    return 0
}

# Function to extract schema from ostruct output
extract_schema() {
    local ostruct_output=$1
    local schema_file=$2

    print_status "$BLUE" "Extracting schema from ostruct output..."

    # Check if the output file contains valid JSON
    if ! jq empty "${ostruct_output}" 2>/dev/null; then
        print_status "$RED" "Error: ostruct output is not valid JSON"
        return 1
    fi

    # Extract the generated_schema field and unescape it
    if ! jq -r '.generated_schema' "${ostruct_output}" | jq . > "${schema_file}" 2>/dev/null; then
        print_status "$RED" "Error: Failed to extract or parse generated_schema field"
        return 1
    fi

    print_status "$GREEN" "Schema extracted successfully"
    return 0
}

# Function to validate schema
validate_schema() {
    local schema_file=$1
    local validation_output=$2

    print_status "$BLUE" "Validating schema..."

    # Try different validator commands based on what's available
    case "${VALIDATOR_CMD}" in
        ajv|ajv-cli)
            if ajv compile -s "${schema_file}" 2>&1 | tee "${validation_output}"; then
                print_status "$GREEN" "Schema validation passed"
                return 0
            else
                print_status "$YELLOW" "Schema validation failed"
                return 1
            fi
            ;;
        jsonschema)
            if python3 -m jsonschema "${schema_file}" 2>&1 | tee "${validation_output}"; then
                print_status "$GREEN" "Schema validation passed"
                return 0
            else
                print_status "$YELLOW" "Schema validation failed"
                return 1
            fi
            ;;
        *)
            # Generic approach - just try to parse as JSON
            if jq empty "${schema_file}" 2>&1 | tee "${validation_output}"; then
                print_status "$GREEN" "Schema is valid JSON (basic validation)"
                return 0
            else
                print_status "$YELLOW" "Schema validation failed (JSON parse error)"
                return 1
            fi
            ;;
    esac
}

# Function to check schema quality and decide if refinement is needed
should_refine_schema() {
    local ostruct_output=$1
    local validation_output=$2

    # Check if JSON schema validation failed
    if [[ ! -f "${validation_output}" ]] || grep -q "error\|failed\|invalid" "${validation_output}" 2>/dev/null; then
        echo "Schema validation failed" > "${validation_output}.reason"
        return 0
    fi

    # Check confidence score and quality metrics from ostruct output
    if [[ -f "${ostruct_output}" ]]; then
        local confidence_score
        confidence_score=$(jq -r '.schema_quality_assessment.confidence_score // 1.0' "${ostruct_output}" 2>/dev/null)

        local has_warnings
        has_warnings=$(jq -r '.schema_quality_assessment.ambiguity_warnings | length > 0' "${ostruct_output}" 2>/dev/null)

        local empty_properties
        empty_properties=$(jq -r '.generated_schema' "${ostruct_output}" 2>/dev/null | jq -r 'fromjson | .properties | length == 0' 2>/dev/null)

        # Trigger refinement if confidence is low (< 0.7)
        if [[ "${confidence_score}" != "null" ]] && (( $(echo "${confidence_score} < 0.7" | bc -l 2>/dev/null || echo "0") )); then
            echo "Low confidence score: ${confidence_score}" > "${validation_output}.reason"
            print_status "$YELLOW" "Low confidence score (${confidence_score}), triggering refinement"
            return 0
        fi

        # Trigger refinement if schema has no properties (likely too generic)
        if [[ "${empty_properties}" == "true" ]]; then
            echo "Generated schema has no properties - too generic" > "${validation_output}.reason"
            print_status "$YELLOW" "Schema too generic (no properties), triggering refinement"
            return 0
        fi

        # Trigger refinement if there are quality warnings
        if [[ "${has_warnings}" == "true" ]]; then
            local warnings
            warnings=$(jq -r '.schema_quality_assessment.ambiguity_warnings | join("; ")' "${ostruct_output}" 2>/dev/null)
            echo "Quality warnings: ${warnings}" > "${validation_output}.reason"
            print_status "$YELLOW" "Quality warnings detected, triggering refinement"
            return 0
        fi
    fi

    return 1
}

# Function to refine schema based on validation errors
refine_schema() {
    local target_template=$1
    local flawed_schema=$2
    local validation_errors=$3
    local temp_output=$4

    print_status "$BLUE" "Refining schema based on validation errors..."

    # Create temporary files for the refinement inputs
    local flawed_schema_content
    flawed_schema_content=$(cat "${flawed_schema}")
    local validation_errors_content
    validation_errors_content=$(cat "${validation_errors}")

    # Build refinement command
    if [[ "${OSTRUCT_CMD}" == "poetry run ostruct" ]]; then
        local cmd=(
            poetry run ostruct run
            "${BASE_DIR}/prompts/refine_schema_from_feedback.j2"
            "${BASE_DIR}/schemas/schema_generator_output.json"
            --fta user_template "${target_template}"
            -V "flawed_schema=${flawed_schema_content}"
            -V "validation_errors=${validation_errors_content}"
            --output-file "${temp_output}"
        )
    else
        local cmd=(
            "${OSTRUCT_CMD}" run
            "${BASE_DIR}/prompts/refine_schema_from_feedback.j2"
            "${BASE_DIR}/schemas/schema_generator_output.json"
            --fta user_template "${target_template}"
            -V "flawed_schema=${flawed_schema_content}"
            -V "validation_errors=${validation_errors_content}"
            --output-file "${temp_output}"
        )
    fi

    print_status "$YELLOW" "Running refinement: ${cmd[*]}"

    if ! "${cmd[@]}"; then
        print_status "$RED" "Error: Schema refinement failed"
        return 1
    fi

    if [[ ! -f "${temp_output}" ]]; then
        print_status "$RED" "Error: Refinement did not create output file"
        return 1
    fi

    print_status "$GREEN" "Schema refinement completed"
    return 0
}

# Main function
main() {
    # Parse command line arguments
    local target_template=""
    local output_file=""
    OSTRUCT_CMD="$DEFAULT_OSTRUCT_CMD"
    VALIDATOR_CMD="$DEFAULT_VALIDATOR_CMD"
    local max_retries=$MAX_RETRIES
    local temp_dir_override=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -o|--output)
                output_file="$2"
                shift 2
                ;;
            -s|--ostruct-cmd)
                OSTRUCT_CMD="$2"
                shift 2
                ;;
            -v|--validator-cmd)
                VALIDATOR_CMD="$2"
                shift 2
                ;;
            -r|--max-retries)
                max_retries="$2"
                shift 2
                ;;
            -t|--temp-dir)
                temp_dir_override="$2"
                shift 2
                ;;
            -*)
                print_status "$RED" "Error: Unknown option $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "$target_template" ]]; then
                    target_template="$1"
                else
                    print_status "$RED" "Error: Multiple target templates specified"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Validate arguments
    if [[ -z "$target_template" ]]; then
        print_status "$RED" "Error: TARGET_TEMPLATE is required"
        show_usage
        exit 1
    fi

    if [[ ! -f "$target_template" ]]; then
        print_status "$RED" "Error: Target template file not found: $target_template"
        exit 1
    fi

    # Check prerequisites
    check_prerequisites

    # Set up temporary directory
    if [[ -n "$temp_dir_override" ]]; then
        TEMP_DIR="$temp_dir_override"
        mkdir -p "$TEMP_DIR"
    else
        TEMP_DIR=$(mktemp -d)
    fi

    # File paths
    local temp_ostruct_output="${TEMP_DIR}/ostruct_output.json"
    local temp_schema="${TEMP_DIR}/extracted_schema.json"
    local temp_validation="${TEMP_DIR}/validation_output.txt"
    local final_schema="${TEMP_DIR}/final_schema.json"

    print_status "$GREEN" "Starting schema generation for: $target_template"
    print_status "$BLUE" "Using temporary directory: $TEMP_DIR"

    # Main generation and validation loop
    local retry_count=0
    local success=false

    while [[ $retry_count -le $max_retries ]]; do
        if [[ $retry_count -eq 0 ]]; then
            # Initial generation
            print_status "$BLUE" "=== Initial Schema Generation (Attempt 1) ==="

            if generate_schema \
                "$target_template" \
                "${BASE_DIR}/prompts/generate_schema_from_template.j2" \
                "${BASE_DIR}/schemas/schema_generator_output.json" \
                "$temp_ostruct_output" \
                ""; then

                if extract_schema "$temp_ostruct_output" "$temp_schema"; then
                    if validate_schema "$temp_schema" "$temp_validation"; then
                        # Even if validation passes, check if refinement is needed for quality
                        if should_refine_schema "$temp_ostruct_output" "$temp_validation"; then
                            print_status "$BLUE" "Schema validation passed but quality improvements needed"
                        else
                            cp "$temp_schema" "$final_schema"
                            success=true
                            break
                        fi
                    fi
                fi
            fi
        else
            # Refinement iteration
            print_status "$BLUE" "=== Schema Refinement (Attempt $((retry_count + 1))) ==="

            if refine_schema \
                "$target_template" \
                "$temp_schema" \
                "$temp_validation" \
                "$temp_ostruct_output"; then

                if extract_schema "$temp_ostruct_output" "$temp_schema"; then
                    if validate_schema "$temp_schema" "$temp_validation"; then
                        cp "$temp_schema" "$final_schema"
                        success=true
                        break
                    fi
                fi
            fi
        fi

        retry_count=$((retry_count + 1))

        if [[ $retry_count -le $max_retries ]]; then
            print_status "$YELLOW" "Validation failed, attempting refinement..."
        fi
    done

    # Output results
    if [[ "$success" == "true" ]]; then
        print_status "$GREEN" "✓ Schema generation completed successfully!"

        if [[ -n "$output_file" ]]; then
            cp "$final_schema" "$output_file"
            print_status "$GREEN" "Final schema written to: $output_file"
        else
            print_status "$BLUE" "Final schema:"
            cat "$final_schema"
        fi

        exit 0
    else
        print_status "$RED" "✗ Schema generation failed after $max_retries retries"
        print_status "$RED" "Last validation errors:"
        cat "$temp_validation"

        if [[ -n "$output_file" ]]; then
            cp "$temp_schema" "$output_file"
            print_status "$YELLOW" "Last generated schema (invalid) written to: $output_file"
        fi

        exit 1
    fi
}

# Run main function with all arguments
main "$@"
