#!/bin/bash
# PDF Semantic Diff Example Runner

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔍 Running PDF Semantic Diff Analysis..."
echo "📁 Example directory: $EXAMPLE_DIR"

# Check if PDFs exist
if [[ ! -f "$EXAMPLE_DIR/test_data/contracts/v1.pdf" ]]; then
    echo "❌ Error: v1.pdf not found"
    echo "💡 Run: cd test_data && python generate_pdfs.py"
    exit 1
fi

if [[ ! -f "$EXAMPLE_DIR/test_data/contracts/v2.pdf" ]]; then
    echo "❌ Error: v2.pdf not found"
    echo "💡 Run: cd test_data && python generate_pdfs.py"
    exit 1
fi

# Check if ostruct is available
if ! command -v ostruct &> /dev/null; then
    echo "❌ Error: ostruct command not found"
    echo "💡 Please install ostruct or ensure it's in your PATH"
    exit 1
fi

# Run ostruct with explicit file routing
echo "🚀 Executing ostruct..."
ostruct run \
    "$EXAMPLE_DIR/prompts/pdf_semantic_diff.j2" \
    "$EXAMPLE_DIR/schemas/semantic_diff.schema.json" \
    --file ci:old_pdf "$EXAMPLE_DIR/test_data/contracts/v1.pdf" \
--file ci:new_pdf "$EXAMPLE_DIR/test_data/contracts/v2.pdf" \
    --model gpt-4o \
    --temperature 0 \
    --output-file "$EXAMPLE_DIR/output.json"

echo "✅ Analysis complete!"
echo "📄 Output saved to: $EXAMPLE_DIR/output.json"

# Validate output if validation script exists
if [[ -f "$SCRIPT_DIR/validate_output.py" ]]; then
    echo "🔍 Validating output..."
    if python3 "$SCRIPT_DIR/validate_output.py" "$EXAMPLE_DIR/output.json"; then
        echo "🎉 Example completed successfully!"
    else
        echo "⚠️  Validation failed - check output quality"
        exit 1
    fi
else
    echo "⚠️  Validation script not found, skipping validation"
fi

echo ""
echo "📊 Results Summary:"
echo "   Input files: v1.pdf, v2.pdf"
echo "   Output file: output.json"
echo "   Validation: $([ -f "$SCRIPT_DIR/validate_output.py" ] && echo "✅ Passed" || echo "⚠️  Skipped")"
