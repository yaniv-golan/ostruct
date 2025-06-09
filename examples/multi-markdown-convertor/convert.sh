#!/bin/bash
# convert.sh - Document converter using ostruct as the brain
# Modular version with separated concerns

set -euo pipefail

# Script metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Initialize variables
INPUT_FILE=""
OUTPUT_FILE=""
AUTONOMOUS=false
ANALYZE_ONLY=false
DRY_RUN=false
VERBOSE=false
DEBUG=false
CHECK_TOOLS=false
ALLOW_EXTERNAL_TOOLS=false
INTERACTIVE_APPROVAL=false

# Configuration
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_ROOT/config/default.conf}"

# Directory setup - Force use of project temp directory
TEMP_DIR="$PROJECT_ROOT/temp"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/output}"
CACHE_DIR="${CACHE_DIR:-$TEMP_DIR/cache}"
LOG_DIR="$TEMP_DIR/logs"

# Create directories
mkdir -p "$TEMP_DIR" "$OUTPUT_DIR" "$CACHE_DIR" "$LOG_DIR"

# Log file setup
LOG_FILE="$LOG_DIR/convert_$(date +%Y%m%d_%H%M%S).log"
SECURITY_LOG_FILE="$LOG_DIR/security.log"
PERFORMANCE_LOG_FILE="$LOG_DIR/performance.log"
COMPLETED_STEPS_FILE="$TEMP_DIR/completed_steps.txt"

# Initialize log files
touch "$LOG_FILE" "$SECURITY_LOG_FILE" "$PERFORMANCE_LOG_FILE" "$COMPLETED_STEPS_FILE"

# Source all modules
source "${SCRIPT_DIR}/lib/common.sh"

# Main conversion function with explicit parameters
convert_document() {
    local input_file="$1"
    local output_file="$2"
    local dry_run="${3:-false}"
    local analyze_only="${4:-false}"
    local interactive_approval="${5:-false}"
    
    log_section "Document Conversion"
    log "Converting: $(basename "$input_file") -> $(basename "$output_file")"
    
    # Validate input
    [[ -f "$input_file" ]] || error_exit "Input file not found: $input_file"
    mkdir -p "$(dirname "$output_file")"
    
    # Handle dry-run
    if [[ "$dry_run" == "true" ]]; then
        perform_dry_run_analysis "$input_file" "$output_file"
        return 0
    fi
    
    # Step 1: Analyze
    local analysis
    analysis=$(analyze_document "$input_file") || error_exit "Analysis failed"
    
    if [[ "$analyze_only" == "true" ]]; then
        log "Analysis complete (analyze-only mode)"
        echo "$analysis" | jq .
        return 0
    fi
    
    # Step 2: Plan
    local plan
    plan=$(create_conversion_plan "$analysis" "$output_file") || error_exit "Planning failed"
    
    # Interactive plan approval
    if [[ "$interactive_approval" == "true" ]]; then
        while true; do
            display_plan "$plan" "Conversion Plan"
            get_plan_approval "plan"
            local approval_result=$?

            case $approval_result in
                0) break ;;  # Approved, continue
                1) error_exit "Plan execution cancelled by user" ;;  # Rejected
                2) continue ;;  # Show again
            esac
        done
    fi
    
    # Step 3: Execute
    if execute_conversion_plan "$plan" "$input_file" "$output_file" "$analysis"; then
        log "✅ Conversion completed successfully"
        
        # Step 4: Validate
        if validate_output "$output_file" "$analysis"; then
            log "✅ Output validation passed"
        else
            log "⚠️  Output validation failed, but conversion completed"
        fi
        return 0
    else
        error_exit "Conversion failed"
    fi
}

# Usage information
show_usage() {
    cat << EOF
Document Conversion System v$SCRIPT_VERSION

USAGE:
    $0 [OPTIONS] INPUT_FILE OUTPUT_FILE
    $0 [OPTIONS] --analyze-only INPUT_FILE
    $0 --check-tools

OPTIONS:
    --autonomous           Run without user prompts
    --analyze-only         Only analyze document, don't convert
    --dry-run             Show planned steps without executing
    --verbose             Enable verbose output
    --debug               Enable debug output
    --check-tools         Check availability of conversion tools
    --check-config        Validate configuration files
    --allow-external-tools Allow using external validation services (default: false)
    --interactive         Show plans for user approval before execution (default: false)
    --version             Show version information
    -h, --help            Show this help message

EXAMPLES:
    # Basic conversion
    $0 document.pdf document.md

    # Autonomous mode
    $0 --autonomous presentation.pptx slides.md

    # Analysis only
    $0 --analyze-only complex_report.docx

    # Dry run to see planned steps
    $0 --dry-run spreadsheet.xlsx data.md

ENVIRONMENT VARIABLES:
    MODEL_ANALYSIS     Model for document analysis (default: gpt-4o-mini)
    MODEL_PLANNING     Model for conversion planning (default: gpt-4o)
    MODEL_SAFETY       Model for safety checking (default: gpt-4o-mini)
    MODEL_VALIDATION   Model for output validation (default: gpt-4o-mini)
    DEBUG              Enable debug output (true/false)
    AUTONOMOUS         Run in autonomous mode (true/false)

For more information, see README.md
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --autonomous)
                AUTONOMOUS=true
                shift
                ;;
            --analyze-only)
                ANALYZE_ONLY=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --check-tools)
                CHECK_TOOLS=true
                shift
                ;;
            --allow-external-tools)
                ALLOW_EXTERNAL_TOOLS=true
                shift
                ;;
            --interactive)
                INTERACTIVE_APPROVAL=true
                shift
                ;;
            --version)
                echo "convert.sh version $SCRIPT_VERSION"
                exit 0
                ;;
            --check-config)
                load_configuration
                validate_configuration && echo "Configuration is valid" || echo "Configuration has errors"
                exit $?
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                error_exit "Unknown option: $1"
                ;;
            *)
                if [[ -z "$INPUT_FILE" ]]; then
                    INPUT_FILE="$1"
                elif [[ -z "$OUTPUT_FILE" ]] && [[ "$ANALYZE_ONLY" != "true" ]]; then
                    OUTPUT_FILE="$1"
                else
                    error_exit "Too many arguments"
                fi
                shift
                ;;
        esac
    done
}

# Main function (simplified)
main() {
    parse_arguments "$@"
    
    # Override with environment
    AUTONOMOUS="${AUTONOMOUS:-false}"
    DEBUG="${DEBUG:-false}"
    VERBOSE="${VERBOSE:-false}"
    
    # Initialize
    log_section "Document Conversion System v$SCRIPT_VERSION"
    log "Started at $(date)"
    
    # Load configuration
    load_configuration
    validate_configuration || error_exit "Invalid configuration"
    
    # Validate tools
    validate_required_tools
    
    # Handle special modes
    if [[ "$CHECK_TOOLS" == "true" ]]; then
        check_conversion_tools
        exit 0
    fi
    
    # Validate arguments
    [[ -z "$INPUT_FILE" ]] && show_usage && error_exit "Input file required"
    [[ "$ANALYZE_ONLY" != "true" ]] && [[ -z "$OUTPUT_FILE" ]] && \
        show_usage && error_exit "Output file required"
    
    # Convert paths to absolute
    INPUT_FILE=$(realpath "$INPUT_FILE")
    if [[ -n "$OUTPUT_FILE" ]]; then
        # Create absolute path for output file (may not exist yet)
        if [[ "$OUTPUT_FILE" = /* ]]; then
            # Already absolute
            OUTPUT_FILE="$OUTPUT_FILE"
        else
            # Make relative path absolute
            OUTPUT_FILE="$(pwd)/$OUTPUT_FILE"
        fi
    fi
    
    # Convert document
    convert_document "$INPUT_FILE" "$OUTPUT_FILE" "$DRY_RUN" "$ANALYZE_ONLY" "$INTERACTIVE_APPROVAL"
}

# Run main
main "$@" 