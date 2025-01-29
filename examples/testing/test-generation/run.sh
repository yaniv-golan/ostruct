#!/bin/bash

# Default values
CODE_PATH="."
OUTPUT_FILE=""
FRAMEWORK="pytest"
MODE="all"  # all or missing

# Help message
show_help() {
    echo "Usage: $0 [OPTIONS] PATH"
    echo
    echo "Generate tests for Python code in specified directory"
    echo
    echo "Options:"
    echo "  -h, --help             Show this help message"
    echo "  -o, --output FILE      Write results to FILE (default: stdout)"
    echo "  -f, --framework NAME   Testing framework to use (default: pytest)"
    echo "                         Supported: pytest, unittest"
    echo "  -m, --mode MODE        Generation mode: all or missing (default: all)"
    echo
    echo "Examples:"
    echo "  $0 ./src                                # Basic usage"
    echo "  $0 --framework pytest --mode missing .  # Generate missing pytest tests"
    echo "  $0 --output tests.json ./src           # Save output to file"
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
        -f|--framework)
            FRAMEWORK="$2"
            shift 2
            ;;
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -*)
            echo "Error: Unknown option $1"
            show_help
            exit 1
            ;;
        *)
            if [ -z "$CODE_PATH" ] || [ "$CODE_PATH" = "." ]; then
                CODE_PATH="$1"
            else
                echo "Error: Multiple paths specified"
                show_help
                exit 1
            fi
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

# Validate framework
case $FRAMEWORK in
    pytest|unittest)
        ;;
    *)
        echo "Error: Unsupported framework '$FRAMEWORK'"
        echo "Supported frameworks: pytest, unittest"
        exit 1
        ;;
esac

# Validate mode
case $MODE in
    all|missing)
        ;;
    *)
        echo "Error: Invalid mode '$MODE'"
        echo "Supported modes: all, missing"
        exit 1
        ;;
esac

# Build the command
CMD="ostruct"
CMD="$CMD --task @prompts/task.j2"
CMD="$CMD --schema schemas/test_cases.json"
CMD="$CMD --system-prompt @prompts/system.txt"
CMD="$CMD --dir code=$CODE_PATH"
CMD="$CMD --dir-ext py"
CMD="$CMD --dir-recursive"
CMD="$CMD --var framework=$FRAMEWORK"
CMD="$CMD --var mode=$MODE"

# Add output file if specified
if [ -n "$OUTPUT_FILE" ]; then
    CMD="$CMD --output-file $OUTPUT_FILE"
fi

# Run the command
echo "Generating tests..."
echo "Directory: $CODE_PATH"
echo "Framework: $FRAMEWORK"
echo "Mode: $MODE"
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
    echo "Error: Test generation failed with exit code $exit_code"
    exit $exit_code
fi 