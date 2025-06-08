#!/bin/bash
# Insert content at specific location in a file
# Usage: insert_content.sh <target_file> <content_file> --after "pattern" | --before "pattern" | --line N

set -euo pipefail

# Function to display usage
usage() {
    cat << EOF
Usage: $0 <target_file> <content_file> [options]

Options:
  --after "pattern"   Insert content after the first line matching pattern
  --before "pattern"  Insert content before the first line matching pattern
  --line N           Insert content at line number N
  --append           Append content at the end (default)

Examples:
  $0 document.md table.md --after "## Section 2"
  $0 document.md image.md --line 50
EOF
    exit 1
}

# Check minimum arguments
if [[ $# -lt 2 ]]; then
    usage
fi

TARGET_FILE="$1"
CONTENT_FILE="$2"
shift 2

# Validate files
if [[ ! -f "$TARGET_FILE" ]]; then
    echo "Error: Target file not found: $TARGET_FILE"
    exit 1
fi

if [[ ! -f "$CONTENT_FILE" ]]; then
    echo "Error: Content file not found: $CONTENT_FILE"
    exit 1
fi

# Default mode is append
MODE="append"
PATTERN=""
LINE_NUM=""

# Parse options
while [[ $# -gt 0 ]]; then
    case "$1" in
        --after)
            MODE="after"
            PATTERN="$2"
            shift 2
            ;;
        --before)
            MODE="before"
            PATTERN="$2"
            shift 2
            ;;
        --line)
            MODE="line"
            LINE_NUM="$2"
            shift 2
            ;;
        --append)
            MODE="append"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Create temporary file
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Perform insertion based on mode
case "$MODE" in
    after)
        if grep -q "$PATTERN" "$TARGET_FILE"; then
            # Find line number of pattern
            LINE=$(grep -n "$PATTERN" "$TARGET_FILE" | head -1 | cut -d: -f1)
            # Insert after that line
            head -n "$LINE" "$TARGET_FILE" > "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            cat "$CONTENT_FILE" >> "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            tail -n +$((LINE + 1)) "$TARGET_FILE" >> "$TEMP_FILE"
            echo "Inserted content after line $LINE matching: $PATTERN"
        else
            echo "Warning: Pattern not found, appending at end: $PATTERN"
            cp "$TARGET_FILE" "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            cat "$CONTENT_FILE" >> "$TEMP_FILE"
        fi
        ;;

    before)
        if grep -q "$PATTERN" "$TARGET_FILE"; then
            # Find line number of pattern
            LINE=$(grep -n "$PATTERN" "$TARGET_FILE" | head -1 | cut -d: -f1)
            # Insert before that line
            head -n $((LINE - 1)) "$TARGET_FILE" > "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            cat "$CONTENT_FILE" >> "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            tail -n +$LINE "$TARGET_FILE" >> "$TEMP_FILE"
            echo "Inserted content before line $LINE matching: $PATTERN"
        else
            echo "Warning: Pattern not found, appending at end: $PATTERN"
            cp "$TARGET_FILE" "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            cat "$CONTENT_FILE" >> "$TEMP_FILE"
        fi
        ;;

    line)
        TOTAL_LINES=$(wc -l < "$TARGET_FILE")
        if [[ $LINE_NUM -le 0 ]] || [[ $LINE_NUM -gt $((TOTAL_LINES + 1)) ]]; then
            echo "Error: Line number $LINE_NUM is out of range (1-$((TOTAL_LINES + 1)))"
            exit 1
        fi

        if [[ $LINE_NUM -eq 1 ]]; then
            # Insert at beginning
            cat "$CONTENT_FILE" > "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            cat "$TARGET_FILE" >> "$TEMP_FILE"
        elif [[ $LINE_NUM -gt $TOTAL_LINES ]]; then
            # Append at end
            cp "$TARGET_FILE" "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            cat "$CONTENT_FILE" >> "$TEMP_FILE"
        else
            # Insert at specific line
            head -n $((LINE_NUM - 1)) "$TARGET_FILE" > "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            cat "$CONTENT_FILE" >> "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
            tail -n +$LINE_NUM "$TARGET_FILE" >> "$TEMP_FILE"
        fi
        echo "Inserted content at line $LINE_NUM"
        ;;

    append)
        cp "$TARGET_FILE" "$TEMP_FILE"
        echo "" >> "$TEMP_FILE"
        cat "$CONTENT_FILE" >> "$TEMP_FILE"
        echo "Appended content at end of file"
        ;;
esac

# Replace original file
mv "$TEMP_FILE" "$TARGET_FILE"
echo "Successfully updated: $TARGET_FILE"
