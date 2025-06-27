#!/usr/bin/env bash
set -euo pipefail

# Template & Schema Analyzer - Meta-tool for analyzing ostruct templates and schemas
# Uses gpt-4.1 with web search to provide comprehensive analysis

# Get tool directory
TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source logging (adjust path to project root)
ROOT="$(cd "$TOOL_DIR/../.." && pwd)"
# Set LOG_DIR to current working directory for meta-tools
export LOG_DIR="$(pwd)/log"
source "$ROOT/scripts/logging.sh"

# Show help if requested
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat << EOF
Usage: $0 [OPTIONS] [TEMPLATE_FILE] [SCHEMA_FILE]

Analyze ostruct templates and schemas for issues, optimization opportunities, and best practices compliance.

ARGUMENTS:
    TEMPLATE_FILE      Optional: Analyze specific template file
    SCHEMA_FILE        Optional: Analyze specific schema file
                      (If no files specified, analyzes demo files)

OPTIONS:
    --verbose          Enable verbose logging (INFO level)
    --debug            Enable debug logging (DEBUG level)
    --help, -h         Show this help message

EXAMPLES:
    $0                                    # Analyze demo template and schema
    $0 my_template.j2                    # Analyze specific template
    $0 my_template.j2 my_schema.json     # Analyze template and schema pair
         $0 --verbose                         # Enable verbose logging
     $0 --debug                           # Enable debug logging

DESCRIPTION:
    This meta-tool analyzes ostruct templates and schemas using gpt-4.1 to identify:
    - Syntax issues and undefined variables
    - Security risks and performance problems
    - OpenAI structured outputs compliance
    - ostruct-specific optimization opportunities (file_ref, safe_get, filters)
    - Best practices and code quality issues

    Results include actionable recommendations for improvement.

OUTPUT:
    Analysis results are written to both console and log files in ./log/ directory (current working directory).
    An interactive HTML report is generated and automatically opened in your browser.

EOF
  exit 0
fi

# Parse arguments
VERBOSE=false
DEBUG=false
TEMPLATE_FILE=""
SCHEMA_FILE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --verbose)
      VERBOSE=true
      export LOG_LEVEL=INFO
      shift
      ;;
    --debug)
      DEBUG=true
      export LOG_LEVEL=DEBUG
      shift
      ;;
    -*)
      echo "Unknown option: $1" >&2
      echo "Use --help for usage information" >&2
      exit 1
      ;;
    *)
      if [[ -z "$TEMPLATE_FILE" ]]; then
        TEMPLATE_FILE="$1"
      elif [[ -z "$SCHEMA_FILE" ]]; then
        SCHEMA_FILE="$1"
      else
        echo "Too many arguments. Use --help for usage information" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

# Set defaults if no files specified
if [[ -z "$TEMPLATE_FILE" ]]; then
  TEMPLATE_FILE="$TOOL_DIR/test/demo_template.j2"
fi

# Function to run ostruct with hardcoded model
run_analyzer() {
  local template_content="$1"
  local template_file="$2"
  local schema_content="$3"
  local schema_file="$4"
  local output_file="$5"

  ostruct run "$TOOL_DIR/src/analyzer.j2" "$TOOL_DIR/src/analysis_output.json" \
    --model gpt-4.1 \
    --temperature 0.1 \
    --enable-tool web-search \
    --output-file "$output_file" \
    ${template_content:+-V template_content="$template_content"} \
    ${template_file:+-V template_file="$template_file"} \
    ${schema_content:+-V schema_content="$schema_content"} \
    ${schema_file:+-V schema_file="$schema_file"}
}

# Main execution
main() {
  log_start "Template & Schema Analyzer"

  # Validate files exist
  if [[ ! -f "$TEMPLATE_FILE" ]]; then
    log_error "Template file not found: $TEMPLATE_FILE"
    exit 1
  fi

  # Create output directory if it doesn't exist
  mkdir -p "$(pwd)/analysis_output"

  # Generate timestamped output file
  local timestamp=$(date +%Y%m%d_%H%M%S)
  local analysis_output="$(pwd)/analysis_output/analysis_${timestamp}.json"

  # Analyze template
  log_info "Analyzing template: $TEMPLATE_FILE"
  log_command "Template analysis" \
    run_analyzer "$(cat "$TEMPLATE_FILE")" "$(basename "$TEMPLATE_FILE")" "" "" "$analysis_output"

  # Analyze schema if provided
  if [[ -n "$SCHEMA_FILE" ]]; then
    if [[ ! -f "$SCHEMA_FILE" ]]; then
      log_error "Schema file not found: $SCHEMA_FILE"
      exit 1
    fi

    log_info "Analyzing schema: $SCHEMA_FILE"
    log_command "Schema analysis" \
      run_analyzer "" "" "$(cat "$SCHEMA_FILE")" "$(basename "$SCHEMA_FILE")" "$analysis_output"
  elif [[ -f "$TOOL_DIR/test/demo_schema.json" ]]; then
    log_info "Analyzing demo schema"
    log_command "Demo schema analysis" \
      run_analyzer "" "" "$(cat "$TOOL_DIR/test/demo_schema.json")" "demo_schema.json" "$analysis_output"
  fi

  # Generate HTML report
  if [[ -f "$analysis_output" ]]; then
    local html_output="$(pwd)/analysis_output/analysis_report_${timestamp}.html"
    log_info "Generating HTML report"
    log_command "HTML report generation" \
      "$TOOL_DIR/scripts/json2html.sh" "$analysis_output" "$html_output"

    # Open HTML report in browser
    if command -v open &> /dev/null; then
      log_info "Opening HTML report in browser"
      open "$html_output"
    elif command -v xdg-open &> /dev/null; then
      log_info "Opening HTML report in browser"
      xdg-open "$html_output"
    else
      log_info "HTML report generated: $html_output"
      log_info "Please open the file manually in your browser"
    fi
  else
    log_error "Analysis output file not found: $analysis_output"
  fi

  log_finish "Template & Schema Analyzer"
}

# Run main function
main "$@"
