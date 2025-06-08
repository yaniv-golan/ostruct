#!/bin/bash
# cleanup.sh - Clean up temporary files and caches

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load configuration
CONFIG_FILE="$PROJECT_ROOT/config/default.conf"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

TEMP_DIR="${TEMP_DIR:-$PROJECT_ROOT/temp}"
CACHE_DIR="${CACHE_DIR:-$TEMP_DIR/cache}"

# Parse arguments
CLEAN_CACHE=false
CLEAN_LOGS=false
CLEAN_ALL=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --cache)
            CLEAN_CACHE=true
            shift
            ;;
        --logs)
            CLEAN_LOGS=true
            shift
            ;;
        --all)
            CLEAN_ALL=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "  --cache    Clean cache files"
            echo "  --logs     Clean log files"
            echo "  --all      Clean everything"
            echo "  --force    Don't ask for confirmation"
            echo "  -h, --help Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# If no specific options, default to cache
if [[ "$CLEAN_CACHE" == "false" ]] && [[ "$CLEAN_LOGS" == "false" ]] && [[ "$CLEAN_ALL" == "false" ]]; then
    CLEAN_CACHE=true
fi

echo "=== Document Converter Cleanup ==="
echo ""

# Show what will be cleaned
if [[ "$CLEAN_ALL" == "true" ]]; then
    echo "Will clean:"
    echo "  - Cache files in $CACHE_DIR"
    echo "  - Log files in $TEMP_DIR/logs"
    echo "  - Temporary chunks in $TEMP_DIR/chunks_*"
    echo "  - Completed steps files"
elif [[ "$CLEAN_CACHE" == "true" ]]; then
    echo "Will clean cache files in $CACHE_DIR"
fi

if [[ "$CLEAN_LOGS" == "true" ]]; then
    echo "Will clean log files in $TEMP_DIR/logs"
fi

echo ""

# Confirmation
if [[ "$FORCE" != "true" ]]; then
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

# Clean cache
if [[ "$CLEAN_CACHE" == "true" ]] || [[ "$CLEAN_ALL" == "true" ]]; then
    if [[ -d "$CACHE_DIR" ]]; then
        echo "Cleaning cache directory..."
        rm -rf "$CACHE_DIR"/*
        echo "✅ Cache cleaned"
    else
        echo "Cache directory not found"
    fi
fi

# Clean logs
if [[ "$CLEAN_LOGS" == "true" ]] || [[ "$CLEAN_ALL" == "true" ]]; then
    if [[ -d "$TEMP_DIR/logs" ]]; then
        echo "Cleaning log files..."
        rm -f "$TEMP_DIR/logs"/*
        echo "✅ Logs cleaned"
    else
        echo "Log directory not found"
    fi
fi

# Clean other temp files
if [[ "$CLEAN_ALL" == "true" ]]; then
    echo "Cleaning temporary files..."

    # Remove chunk directories
    rm -rf "$TEMP_DIR"/chunks_*

    # Remove completed steps files
    rm -f "$TEMP_DIR"/completed_steps.txt

    # Remove filtered tools directories
    rm -rf "$TEMP_DIR"/filtered_tools

    echo "✅ Temporary files cleaned"
fi

echo ""
echo "Cleanup completed!"

# Show disk space saved (if possible)
if command -v du >/dev/null 2>&1; then
    echo "Current temp directory size: $(du -sh "$TEMP_DIR" 2>/dev/null | cut -f1 || echo "unknown")"
fi
