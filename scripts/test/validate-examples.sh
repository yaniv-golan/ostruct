#!/bin/bash
set -euo pipefail

# Example Validation Script for ostruct
# Validates all examples in the examples/ directory by running dry-run first, then live execution
# Caches parsed README results to avoid re-parsing unchanged files

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VALIDATE_DIR="${SCRIPT_DIR}/validate-examples"
CACHE_DIR="${VALIDATE_DIR}/cache"
TEMP_DIR="${VALIDATE_DIR}/temp"
EXAMPLES_DIR="${PROJECT_ROOT}/examples"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
VERBOSE=false
FORCE_REFRESH=false
DRY_RUN_ONLY=false
SPECIFIC_EXAMPLE=""
TIMEOUT=300  # 5 minutes per command
SKIP_ERROR_ANALYSIS=false  # Skip LLM error analysis for speed

# Ensure dependencies are available
ensure_dependencies() {
    # Ensure jq is available (required for JSON processing)
    local jq_installer="${SCRIPT_DIR}/../install/dependencies/ensure_jq.sh"
    if [[ -f "$jq_installer" ]]; then
        if ! source "$jq_installer"; then
            vlog "ERROR" "Failed to ensure jq dependency. Please install jq manually."
            exit 1
        fi
    else
        # Fallback check if ensure_jq.sh is not available
        if ! command -v jq >/dev/null 2>&1; then
            vlog "ERROR" "jq is required but not installed. Please install jq and try again."
            vlog "ERROR" "Installation: https://jqlang.github.io/jq/download/"
            exit 1
        fi
    fi
}

# Capture ostruct help JSON once for the entire run
capture_ostruct_help() {
    local help_file="${CACHE_DIR}/ostruct_help.json"

    vlog "DEBUG" "Capturing ostruct --help-json for syntax awareness"

    # Try direct ostruct first, then poetry run ostruct
    if command -v ostruct >/dev/null 2>&1 && ostruct --help-json > "$help_file" 2>/dev/null; then
        vlog "DEBUG" "ostruct help JSON captured to: $help_file"
        export OSTRUCT_HELP_JSON_FILE="$help_file"
        return 0
    elif command -v poetry >/dev/null 2>&1 && poetry run ostruct --help-json > "$help_file" 2>/dev/null; then
        vlog "DEBUG" "ostruct help JSON captured via poetry to: $help_file"
        export OSTRUCT_HELP_JSON_FILE="$help_file"
        return 0
    else
        vlog "WARN" "Failed to capture ostruct --help-json, proceeding without syntax awareness"
        echo "{}" > "$help_file"
        export OSTRUCT_HELP_JSON_FILE="$help_file"
        return 1
    fi
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Validate all examples in the examples/ directory by running ostruct commands
found in README files. Uses two-phase validation: dry-run first, then live execution.

OPTIONS:
    -v, --verbose           Enable verbose output
    -f, --force-refresh     Force refresh of cached README parsing results
    -d, --dry-run-only      Only run dry-run validation, skip live execution
    -e, --example PATH      Validate specific example (relative to examples/)
    -t, --timeout SECONDS  Timeout for each command (default: 300)
    -s, --skip-error-analysis  Skip LLM error analysis for faster validation
    -h, --help              Show this help message

EXAMPLES:
    $0                                    # Validate all examples
    $0 -v                                # Verbose validation of all examples
    $0 -e code-quality/code-review       # Validate specific example
    $0 -d                                # Only dry-run validation
    $0 -f                                # Force refresh cache and validate all

EOF
}

vlog() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        "INFO")  echo -e "${BLUE}[INFO]${NC}  ${timestamp} ${message}" >&2 ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC}  ${timestamp} ${message}" >&2 ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} ${timestamp} ${message}" >&2 ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} ${message}" >&2 ;;
        "DEBUG") [[ "$VERBOSE" == "true" ]] && echo -e "[DEBUG] ${timestamp} ${message}" >&2 ;;
        "PROGRESS") echo -e "${CYAN}[PROGRESS]${NC} ${timestamp} ${message}" >&2 ;;
    esac
    return 0
}

cleanup() {
    vlog "INFO" "Cleaning up temporary files..."
    rm -rf "${TEMP_DIR}"/*
}

trap cleanup EXIT

# Load library functions AFTER vlog is defined
source "${VALIDATE_DIR}/lib/discovery.sh"
source "${VALIDATE_DIR}/lib/extraction.sh"
source "${VALIDATE_DIR}/lib/execution.sh"
source "${VALIDATE_DIR}/lib/validation.sh"
source "${VALIDATE_DIR}/lib/reporting.sh"

main() {
    # Ensure all dependencies are available before starting
    ensure_dependencies

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -f|--force-refresh)
                FORCE_REFRESH=true
                shift
                ;;
            -d|--dry-run-only)
                DRY_RUN_ONLY=true
                shift
                ;;
            -e|--example)
                SPECIFIC_EXAMPLE="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -s|--skip-error-analysis)
                SKIP_ERROR_ANALYSIS=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                usage
                exit 1
                ;;
        esac
    done

    # Ensure required directories exist
    mkdir -p "${CACHE_DIR}" "${TEMP_DIR}"

    # Force refresh: clear entire cache directory
    if [[ "$FORCE_REFRESH" == "true" ]]; then
        vlog "INFO" "Force refresh: clearing entire cache directory..."
        rm -rf "${CACHE_DIR}"/*
        vlog "DEBUG" "Cache directory cleared: ${CACHE_DIR}"
    fi

    # Capture ostruct help JSON once for the entire run
    capture_ostruct_help || true

    vlog "INFO" "Starting example validation..."
    vlog "INFO" "Project root: ${PROJECT_ROOT}"
    vlog "INFO" "Examples directory: ${EXAMPLES_DIR}"
    vlog "INFO" "Cache directory: ${CACHE_DIR}"

    if [[ "$DRY_RUN_ONLY" == "true" ]]; then
        vlog "INFO" "Running in dry-run only mode"
    fi

    if [[ "$SKIP_ERROR_ANALYSIS" == "true" ]]; then
        vlog "INFO" "Skipping LLM error analysis for speed"
    fi

    if [[ "$FORCE_REFRESH" == "true" ]]; then
        vlog "INFO" "Force refresh enabled - ignoring all cached results"
    fi

    if [[ -n "$SPECIFIC_EXAMPLE" ]]; then
        vlog "INFO" "Validating specific example: ${SPECIFIC_EXAMPLE}"
    fi

    # Initialize results tracking
    init_results_tracking
    vlog "DEBUG" "Returned from init_results_tracking"

    # Discover and parse README files
    vlog "INFO" "Discovering README files..."
    local readme_files
    if [[ -n "$SPECIFIC_EXAMPLE" ]]; then
        readme_files=$(discover_readme_files "${EXAMPLES_DIR}/${SPECIFIC_EXAMPLE}")
    else
        readme_files=$(discover_readme_files "${EXAMPLES_DIR}")
    fi

    if [[ -z "$readme_files" ]]; then
        vlog "ERROR" "No README files found"
        exit 1
    fi

    local total_files=$(echo "$readme_files" | wc -l | tr -d ' ')
    vlog "INFO" "Found ${total_files} README files to process"

    # Show a visual separator for the validation process
    echo -e "\n${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n" >&2

    # Process each README file
    local processed=0
    # Convert newline-separated string to array to avoid stdin issues
    local readme_array=()
    while IFS= read -r readme_file; do
        readme_array+=("$readme_file")
    done <<< "$readme_files"

    # Process using array to avoid stdin consumption issues
    for readme_file in "${readme_array[@]}"; do
        ((processed++))

        # Extract example name for cleaner display
        local example_name="${readme_file#${EXAMPLES_DIR}/}"
        example_name="${example_name%/README.md}"

        # Show progress with visual separator
        echo -e "\n${CYAN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}" >&2
        echo -e "${CYAN}║${NC} ${MAGENTA}Example ${processed}/${total_files}:${NC} ${GREEN}${example_name}${NC}" >&2
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n" >&2

        # Parse README and extract commands (with caching)
        local commands_file=$(parse_readme_with_cache "$readme_file")

        if [[ -s "$commands_file" ]]; then
            # Execute commands from this README
            execute_commands_from_file "$commands_file" "$readme_file"
        else
            vlog "WARN" "No ostruct commands found in ${readme_file#${PROJECT_ROOT}/}"
        fi

        vlog "DEBUG" "Finished processing example $processed of $total_files"
    done

    # Final visual separator
    echo -e "\n${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n" >&2

    vlog "DEBUG" "Finished processing all $processed examples"

    # Generate final report
    vlog "INFO" "Generating validation report..."
    generate_final_report

    # Exit with appropriate code
    local exit_code=$(get_exit_code)
    if [[ $exit_code -eq 0 ]]; then
        vlog "SUCCESS" "All examples validated successfully!"
    else
        vlog "ERROR" "Some examples failed validation"

        # Show note about error analysis time if it was performed
        if [[ "${SKIP_ERROR_ANALYSIS:-false}" != "true" ]] && [[ $DRY_FAILED_COMMANDS -gt 0 || $LIVE_FAILED_COMMANDS -gt 0 ]]; then
            echo >&2
            vlog "INFO" "💡 Note: Error analysis adds ~15-20 seconds per failed command."
            vlog "INFO" "   Use -s/--skip-error-analysis for faster validation without detailed error analysis."
        fi
    fi

    exit $exit_code
}

# Run main function
main "$@"
