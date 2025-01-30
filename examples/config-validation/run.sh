#!/bin/bash

# Configuration Validation Runner Script
# This script uses the OpenAI Structured CLI to validate configuration files

set -e

# Default values
CONFIG_DIR=""
ENVIRONMENT=""
CROSS_ENV_CHECK=false
STRICT_MODE=false
OUTPUT_FILE=""
IGNORE_PATTERNS=""
SERVICE_NAME=""

# Function to print usage
print_usage() {
    echo "Usage: $0 [OPTIONS] CONFIG_DIR"
    echo
    echo "Validate configuration files using OpenAI Structured CLI"
    echo
    echo "Options:"
    echo "  -e, --env ENV          Target environment (dev, prod, etc.)"
    echo "  -c, --cross-env-check  Enable cross-environment validation"
    echo "  -s, --strict           Enable strict mode (fail on warnings)"
    echo "  -o, --output FILE      Write results to file"
    echo "  -i, --ignore PATTERN   Ignore patterns (comma-separated)"
    echo "  -n, --name SERVICE     Service name (default: derived from directory)"
    echo "  -h, --help             Show this help message"
    echo
    echo "Example:"
    echo "  $0 --env prod --cross-env-check ./configs"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -c|--cross-env-check)
            CROSS_ENV_CHECK=true
            shift
            ;;
        -s|--strict)
            STRICT_MODE=true
            shift
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -i|--ignore)
            IGNORE_PATTERNS="$2"
            shift 2
            ;;
        -n|--name)
            SERVICE_NAME="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            if [[ -z "$CONFIG_DIR" ]]; then
                CONFIG_DIR="$1"
            else
                echo "Error: Unexpected argument '$1'"
                print_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "$CONFIG_DIR" ]]; then
    echo "Error: CONFIG_DIR is required"
    print_usage
    exit 1
fi

# Get absolute paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [[ -d "$CONFIG_DIR" ]]; then
    CONFIG_DIR="$(cd "$CONFIG_DIR" && pwd)"
    # Make the path relative to the script directory (macOS compatible)
    CONFIG_DIR="${CONFIG_DIR#$SCRIPT_DIR/}"  # Remove script dir prefix
else
    echo "Error: Directory '$CONFIG_DIR' does not exist"
    exit 1
fi

# If service name not provided, try to derive it from directory name
if [[ -z "$SERVICE_NAME" ]]; then
    SERVICE_NAME=$(basename "$CONFIG_DIR")
fi

# Build the ostruct command
CMD="ostruct"
CMD+=" --task @prompts/task.j2"
CMD+=" --schema schemas/validation_result.json"
CMD+=" --system-prompt @prompts/system.txt"
CMD+=" --dir configs=$CONFIG_DIR"
CMD+=" --dir-recursive"
CMD+=" --dir-ext yaml,yml,json"
CMD+=" --var service_name=$SERVICE_NAME"
CMD+=" --var strict_mode=false"
CMD+=" --var ignore_patterns=[]"

# Add optional parameters
if [[ -n "$ENVIRONMENT" ]]; then
    CMD+=" --var environment=$ENVIRONMENT"
fi

if [[ "$CROSS_ENV_CHECK" == true ]]; then
    CMD+=" --var cross_env_check=true"
fi

if [[ "$STRICT_MODE" == true ]]; then
    CMD+=" --var strict_mode=true"
fi

if [[ -n "$IGNORE_PATTERNS" ]]; then
    # Convert comma-separated list to JSON array
    PATTERNS_JSON="[$(echo "$IGNORE_PATTERNS" | sed 's/,/","/g' | sed 's/.*/"&"/')"
    CMD+=" --var ignore_patterns=$PATTERNS_JSON"
fi

# Run the validation
echo "Running validation..."
echo "Config directory: $CONFIG_DIR"
echo "Service name: $SERVICE_NAME"
echo "Command: $CMD"

if [[ -n "$OUTPUT_FILE" ]]; then
    echo "Output will be written to: $OUTPUT_FILE"
    $CMD > "$OUTPUT_FILE"
else
    $CMD
fi

# Check exit code
EXIT_CODE=$?
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "Validation completed successfully"
else
    echo "Validation failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi 