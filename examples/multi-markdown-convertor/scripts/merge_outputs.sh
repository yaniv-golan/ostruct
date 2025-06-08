#!/bin/bash
# Merge text and media outputs into final markdown document
# Usage: merge_outputs.sh <text_file> <media_dir> <output_file>

set -euo pipefail

# Check arguments
if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <text_file> <media_dir> <output_file>"
    exit 1
fi

TEXT_FILE="$1"
MEDIA_DIR="$2"
OUTPUT_FILE="$3"

# Validate inputs
if [[ ! -f "$TEXT_FILE" ]]; then
    echo "Error: Text file not found: $TEXT_FILE"
    exit 1
fi

# Create output directory if needed
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Start with the text content
cp "$TEXT_FILE" "$OUTPUT_FILE"

# Check if media directory exists and has images
if [[ -d "$MEDIA_DIR" ]]; then
    # Find all image files
    IMAGE_COUNT=$(find "$MEDIA_DIR" -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.gif" -o -iname "*.bmp" -o -iname "*.tiff" -o -iname "*.tif" -o -iname "*.svg" \) | wc -l)

    if [[ $IMAGE_COUNT -gt 0 ]]; then
        echo "Found $IMAGE_COUNT images to merge"

        # Append images section at the end
        echo -e "\n\n## Extracted Images\n" >> "$OUTPUT_FILE"

        # Add each image with markdown syntax
        find "$MEDIA_DIR" -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.gif" -o -iname "*.bmp" -o -iname "*.tiff" -o -iname "*.tif" -o -iname "*.svg" \) | sort | while read -r image; do
            image_name=$(basename "$image")
            echo "![${image_name%.*}]($image)" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
        done
    else
        echo "No images found in $MEDIA_DIR"
    fi
else
    echo "Media directory not found: $MEDIA_DIR (continuing with text only)"
fi

echo "Successfully merged content to: $OUTPUT_FILE"
