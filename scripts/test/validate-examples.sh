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
NC='\033[0m' # No Color

# Configuration
VERBOSE=false
FORCE_REFRESH=false
DRY_RUN_ONLY=false
SPECIFIC_EXAMPLE=""
TIMEOUT=300  # 5 minutes per command

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

    if ! ostruct --help-json > "$help_file" 2>/dev/null; then
        vlog "WARN" "Failed to capture ostruct --help-json, proceeding without syntax awareness"
        echo "{}" > "$help_file"
        return 1
    fi

    vlog "DEBUG" "ostruct help JSON captured to: $help_file"
    export OSTRUCT_HELP_JSON_FILE="$help_file"
    return 0
}

# Load library functions
source "${VALIDATE_DIR}/lib/discovery.sh"
source "${VALIDATE_DIR}/lib/extraction.sh"
source "${VALIDATE_DIR}/lib/execution.sh"
source "${VALIDATE_DIR}/lib/validation.sh"
source "${VALIDATE_DIR}/lib/reporting.sh"

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
    esac
}

cleanup() {
    vlog "INFO" "Cleaning up temporary files..."
    rm -rf "${TEMP_DIR}"/*
}

trap cleanup EXIT

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

    # Capture ostruct help JSON once for the entire run
    capture_ostruct_help

    vlog "INFO" "Starting example validation..."
    vlog "INFO" "Project root: ${PROJECT_ROOT}"
    vlog "INFO" "Examples directory: ${EXAMPLES_DIR}"
    vlog "INFO" "Cache directory: ${CACHE_DIR}"

    if [[ "$DRY_RUN_ONLY" == "true" ]]; then
        vlog "INFO" "Running in dry-run only mode"
    fi

    if [[ -n "$SPECIFIC_EXAMPLE" ]]; then
        vlog "INFO" "Validating specific example: ${SPECIFIC_EXAMPLE}"
    fi

    # Initialize results tracking
    init_results_tracking

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

    local total_files=$(echo "$readme_files" | wc -l)
    vlog "INFO" "Found ${total_files} README files to process"

    # Process each README file
    local processed=0
    while IFS= read -r readme_file; do
        ((processed++))
        vlog "INFO" "Processing ${processed}/${total_files}: ${readme_file#${PROJECT_ROOT}/}"

        # Parse README and extract commands (with caching)
        local commands_file=$(parse_readme_with_cache "$readme_file")

        if [[ -s "$commands_file" ]]; then
            # Execute commands from this README
            execute_commands_from_file "$commands_file" "$readme_file"
        else
            vlog "WARN" "No ostruct commands found in ${readme_file#${PROJECT_ROOT}/}"
        fi
    done <<< "$readme_files"

    # Generate final report
    vlog "INFO" "Generating validation report..."
    generate_final_report

    # Exit with appropriate code
    local exit_code=$(get_exit_code)
    if [[ $exit_code -eq 0 ]]; then
        vlog "SUCCESS" "All examples validated successfully!"
    else
        vlog "ERROR" "Some examples failed validation"
    fi

    exit $exit_code
}

# Run main function
main "$@"
