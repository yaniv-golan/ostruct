#!/bin/bash

# Two-Pass Pitch Deck Analysis Script
# Pass 1: Extract core data using File Search + structured output
# Pass 2: Add taxonomy classification using core data + taxonomy reference

set -e

# Configuration
DECK_FILE="${1:-data/sample_pitch.txt}"
OUTPUT_DIR="output"
TEMP_DIR="temp"

# Create output directories
mkdir -p "$OUTPUT_DIR" "$TEMP_DIR"

echo "🔍 Starting two-pass pitch deck analysis..."
echo "📄 Input file: $DECK_FILE"

# Pass 1: Extract core data
echo ""
echo "🚀 Pass 1: Extracting core company data..."
ostruct run templates/pass1_core.j2 schemas/pass1_core.json \
    --enable-tool file-search \
    --file fs:deck "$DECK_FILE" \
    > "$TEMP_DIR/pass1_core.json"

if [ $? -eq 0 ]; then
    echo "✅ Pass 1 completed successfully"
    echo "📊 Core data extracted to: $TEMP_DIR/pass1_core.json"
else
    echo "❌ Pass 1 failed"
    exit 1
fi

# Pass 2: Add taxonomy classification
echo ""
echo "🎯 Pass 2: Adding industry taxonomy classification..."
ostruct run templates/pass2_taxonomy.j2 schemas/pass2_taxonomy_simple.json \
    --enable-tool file-search \
    --file fs:taxonomy reference/taxonomy.md \
    --json-var core_data="$(cat "$TEMP_DIR/pass1_core.json")" \
    > "$TEMP_DIR/pass2_taxonomy.json"

if [ $? -eq 0 ]; then
    echo "✅ Pass 2 completed successfully"
    echo "📊 Taxonomy classification added to: $TEMP_DIR/pass2_taxonomy.json"
else
    echo "❌ Pass 2 failed"
    exit 1
fi

# Merge results
echo ""
echo "🔗 Merging results..."
jq -s '.[0] + {"industry_classification": .[1]}' \
    "$TEMP_DIR/pass1_core.json" \
    "$TEMP_DIR/pass2_taxonomy.json" \
    > "$OUTPUT_DIR/final_result.json"

echo "✅ Results merged successfully"
echo "📄 Final result saved to: $OUTPUT_DIR/final_result.json"

# Display summary
echo ""
echo "🎉 Two-pass analysis completed!"
echo "📁 Files created:"
echo "  - $TEMP_DIR/pass1_core.json (core data)"
echo "  - $TEMP_DIR/pass2_taxonomy.json (taxonomy classification)"
echo "  - $OUTPUT_DIR/final_result.json (merged final result)"
echo ""
echo "🔍 Preview of final result:"
echo "----------------------------------------"
cat "$OUTPUT_DIR/final_result.json" | head -20
echo "----------------------------------------"
echo "(truncated - see full file at $OUTPUT_DIR/final_result.json)"
