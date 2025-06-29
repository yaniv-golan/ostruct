#!/usr/bin/env bash
# Generate AIF JSON and create Mermaid visualization
set -euo pipefail

# Parse arguments
TEXT_FILE="${1:-texts/paradox_of_the_court.txt}"
OUTPUT_PREFIX="${2:-$(basename "$TEXT_FILE" .txt)}"
MODEL="${3:-gpt-4o}"
shift 3 2>/dev/null || shift $# # Remove first 3 args, or all if less than 3
OSTRUCT_ARGS="$@" # Remaining arguments passed to ostruct

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$(dirname "$SCRIPT_DIR")"

# Ensure dependencies are available
source "$SCRIPT_DIR/../../../../scripts/install/dependencies/ensure_jq.sh"
source "$SCRIPT_DIR/../../../../scripts/install/dependencies/ensure_mermaid.sh"

# Determine output directory based on input file location
if [[ "$TEXT_FILE" = /* ]]; then
    # Absolute path - use same directory as input file
    OUTPUT_DIR="$(dirname "$TEXT_FILE")"
else
    # Relative path - use example output directory
    OUTPUT_DIR="$EXAMPLE_DIR/output"
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate AIF JSON
echo "🔍 Analyzing argument structure in $TEXT_FILE..."
echo "🤖 Using model: $MODEL"
AIF_FILE="$OUTPUT_DIR/${OUTPUT_PREFIX}.aif.json"

cd "$EXAMPLE_DIR"
if ostruct run templates/main.j2 schemas/main.json --file argument_text "$TEXT_FILE" --model "$MODEL" --output-file "$AIF_FILE" $OSTRUCT_ARGS; then
    echo "✅ AIF JSON generated: $AIF_FILE"
else
    echo "❌ Failed to generate AIF JSON"
    exit 1
fi

# Extract title from text file for diagram
TITLE="$(basename "$TEXT_FILE" .txt | tr '_' ' ' | sed 's/\b\w/\U&/g')"

# Generate Mermaid diagram
echo "🎨 Creating interactive Mermaid diagram..."
MERMAID_FILE="$OUTPUT_DIR/${OUTPUT_PREFIX}.mmd"
"$SCRIPT_DIR/aif2mermaid.sh" "$AIF_FILE" "$TITLE" > "$MERMAID_FILE"
echo "✅ Mermaid diagram generated: $MERMAID_FILE"

# Generate SVG if Mermaid CLI is available
SVG_FILE="$OUTPUT_DIR/${OUTPUT_PREFIX}.svg"
if command -v mmdc >/dev/null 2>&1; then
    echo "🖼️  Generating SVG diagram..."
    if mmdc -i "$MERMAID_FILE" -o "$SVG_FILE"; then
        echo "✅ SVG diagram generated: $SVG_FILE"
    else
        echo "⚠️  SVG generation failed, but Mermaid source is available"
    fi
else
    echo "⚠️  Mermaid CLI not available, SVG generation skipped"
    echo "   You can generate SVG manually with:"
    echo "   mmdc -i $MERMAID_FILE -o $SVG_FILE"
fi

# Display summary
echo ""
echo "📊 AIF Analysis Complete!"
echo "========================="
echo "📄 Input text: $TEXT_FILE"
echo "🤖 Model used: $MODEL"
echo "📋 AIF JSON: $AIF_FILE"
echo "🎨 Mermaid diagram: $MERMAID_FILE"
if [[ -f "$SVG_FILE" ]]; then
    echo "🖼️  SVG diagram: $SVG_FILE"
fi

# Show node statistics
echo ""
echo "📈 Argument Structure:"
echo "====================="
jq -r '
  "💬 Information nodes (I): " + ([.nodes[] | select(.type == "I")] | length | tostring) +
  "\n✅ Rule Application nodes (RA): " + ([.nodes[] | select(.type == "RA")] | length | tostring) +
  "\n⚔️  Conflict Application nodes (CA): " + ([.nodes[] | select(.type == "CA")] | length | tostring) +
  "\n⭐ Preference Application nodes (PA): " + ([.nodes[] | select(.type == "PA")] | length | tostring) +
  "\n🔗 Meta-Argument nodes (MA): " + ([.nodes[] | select(.type == "MA")] | length | tostring) +
  "\n🔗 Total edges: " + (.edges | length | tostring)
' "$AIF_FILE"

echo ""
echo "🔍 To view the interactive diagram:"
if [[ -f "$SVG_FILE" ]]; then
    echo "   Static SVG: open $SVG_FILE"
    echo "   Interactive: Copy $MERMAID_FILE content to https://mermaid.live/"
    echo "   💡 Click any node in mermaid.live to see full text!"
else
    echo "   Copy the Mermaid code from $MERMAID_FILE"
    echo "   Paste it into: https://mermaid.live/"
    echo "   💡 Click any node to see the complete argument text!"
fi
