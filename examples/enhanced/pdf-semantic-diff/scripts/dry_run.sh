#!/bin/bash

# PDF Semantic Diff - Dry Run Script
# Tests template rendering and validation without API calls

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATE_FILE="$PROJECT_DIR/prompts/pdf_semantic_diff.j2"
SCHEMA_FILE="$PROJECT_DIR/schemas/semantic_diff.schema.json"

# PDF files for testing
OLD_PDF="$PROJECT_DIR/test_data/contracts/v1.pdf"
NEW_PDF="$PROJECT_DIR/test_data/contracts/v2.pdf"

echo "🧪 PDF Semantic Diff - Dry Run Test"
echo "=================================="
echo

# Verify files exist
echo "📋 Checking prerequisites..."
for file in "$TEMPLATE_FILE" "$SCHEMA_FILE" "$OLD_PDF" "$NEW_PDF"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done
echo "✅ All required files found"
echo

# Note about current status
echo "📝 Note: This template uses {{ old_pdf.name }} syntax which requires"
echo "   the FileInfoList.name property fix in ostruct v0.8.0."
echo "   For current ostruct versions, use {{ old_pdf[0].name }} as a workaround."
echo

# Run dry run test with explicit file routing
echo "🔍 Running template dry run with explicit file naming..."
echo "Command: ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json --fca old_pdf test_data/contracts/v1.pdf --fca new_pdf test_data/contracts/v2.pdf --dry-run"
echo

if ostruct run "$TEMPLATE_FILE" "$SCHEMA_FILE" \
    --fca old_pdf "$OLD_PDF" \
    --fca new_pdf "$NEW_PDF" \
    --dry-run; then
    echo
    echo "✅ Dry run completed successfully!"
    echo "🎯 Template syntax is working correctly with explicit file naming"
else
    echo
    echo "❌ Dry run failed - check template syntax or file paths"
    echo "🔧 Ensure the template variables match the file aliases (old_pdf, new_pdf)"
    echo "📋 Check that all required files exist and are accessible"
fi

echo
echo "🏁 Dry run test completed" 