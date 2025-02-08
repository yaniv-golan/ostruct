#!/bin/bash

# Default values
CODE_PATH="."
OUTPUT_FILE=""
EXTENSIONS="py,js,ts,java,cpp,go,rb"

# Help message
show_help() {
    echo "Usage: $0 [OPTIONS] [PATH]"
    echo
    echo "Run automated code review on specified directory"
    echo
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -o, --output FILE    Write results to FILE (default: stdout)"
    echo "  -e, --ext LIST       Comma-separated list of file extensions to process"
    echo "                       (default: $EXTENSIONS)"
    echo
    echo "Example:"
    echo "  $0 --ext py,js --output review.json ./src"
}

# Check for OpenAI API key
check_api_key() {
    if [ -z "${OPENAI_API_KEY}" ]; then
        echo "Error: OPENAI_API_KEY environment variable is not set"
        echo "Please set your OpenAI API key:"
        echo "export OPENAI_API_KEY='your-api-key'"
        return 1
    fi
    return 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -e|--ext)
            EXTENSIONS="$2"
            shift 2
            ;;
        *)
            CODE_PATH="$1"
            shift
            ;;
    esac
done

# Validate requirements
if ! check_api_key; then
    exit 1
fi

# Validate code path
if [ ! -d "$CODE_PATH" ]; then
    echo "Error: Directory '$CODE_PATH' does not exist"
    exit 1
fi

# Build the command
CMD="ostruct --task-file prompts/task.j2 --schema-file schemas/code_review.json --system-prompt-file prompts/system.txt --dir code=$CODE_PATH --dir-ext $EXTENSIONS --dir-recursive"

# Add output file if specified
if [ -n "$OUTPUT_FILE" ]; then
    CMD="$CMD --output-file $OUTPUT_FILE"
fi

# Run the command
echo "Running code review..."
echo "Directory: $CODE_PATH"
echo "Extensions: $EXTENSIONS"
if [ -n "$OUTPUT_FILE" ]; then
    echo "Output: $OUTPUT_FILE"
fi
echo
echo "Executing command:"
echo "$CMD"
echo

eval "$CMD"
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "Error: Code review failed with exit code $exit_code"
    exit $exit_code
fi
