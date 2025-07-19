#!/bin/bash

# Test script for template analysis
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$SCRIPT_DIR"
SRC_DIR="$TOOL_DIR/src"

echo "🧪 Testing OST Generator Template Analysis"
echo "=========================================="

# Check if we have an API key for real testing
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "⚠️  No OPENAI_API_KEY found - using dry-run mode only"
  DRY_RUN="--dry-run"
else
  echo "✅ OPENAI_API_KEY found - running live tests"
  DRY_RUN=""
fi

# Test 1: Simple template analysis
echo "Test 1: Simple template analysis"
echo "---------------------------------"

if ostruct run "$SRC_DIR/analyze_template.j2" "$SRC_DIR/analysis_schema.json" \
  --file template_content "$TEST_DIR/fixtures/simple_template.j2" \
  $DRY_RUN --output-file /tmp/simple_analysis.json; then
  echo "✅ Simple template analysis succeeded"

  if [[ -n "$DRY_RUN" ]]; then
    echo "ℹ️  Dry-run mode - skipping JSON validation"
  else
    # Validate JSON structure
    if jq empty /tmp/simple_analysis.json 2>/dev/null; then
      echo "✅ Output is valid JSON"

      # Check for required fields
      if jq -e '.variables' /tmp/simple_analysis.json >/dev/null; then
        echo "✅ Variables field present"
      else
        echo "❌ Variables field missing"
        exit 1
      fi

      if jq -e '.complexity_score' /tmp/simple_analysis.json >/dev/null; then
        echo "✅ Complexity score present"
      else
        echo "❌ Complexity score missing"
        exit 1
      fi

    else
      echo "❌ Output is not valid JSON"
      echo "Output content:"
      cat /tmp/simple_analysis.json
      exit 1
    fi
  fi
else
  echo "❌ Simple template analysis failed"
  exit 1
fi

echo ""

# Test 2: Complex template analysis
echo "Test 2: Complex template analysis"
echo "---------------------------------"

if ostruct run "$SRC_DIR/analyze_template.j2" "$SRC_DIR/analysis_schema.json" \
  --file template_content "$TEST_DIR/fixtures/complex_template.j2" \
  $DRY_RUN --output-file /tmp/complex_analysis.json; then
  echo "✅ Complex template analysis succeeded"

  if [[ -n "$DRY_RUN" ]]; then
    echo "ℹ️  Dry-run mode - skipping JSON validation"
  else
    # Validate JSON structure
    if jq empty /tmp/complex_analysis.json 2>/dev/null; then
      echo "✅ Output is valid JSON"

      # Check for file patterns
      if jq -e '.file_patterns | length > 0' /tmp/complex_analysis.json >/dev/null; then
        echo "✅ File patterns detected"
      else
        echo "⚠️  No file patterns detected (expected for complex template)"
      fi

      # Check complexity score
      complexity=$(jq -r '.complexity_score' /tmp/complex_analysis.json)
      if (( $(echo "$complexity > 0.5" | bc -l) )); then
        echo "✅ Complex template has high complexity score: $complexity"
      else
        echo "⚠️  Complex template has low complexity score: $complexity"
      fi

    else
      echo "❌ Output is not valid JSON"
      echo "Output content:"
      cat /tmp/complex_analysis.json
      exit 1
    fi
  fi
else
  echo "❌ Complex template analysis failed"
  exit 1
fi

echo ""
echo "🎉 All tests passed!"

if [[ -z "$DRY_RUN" ]]; then
  echo ""
  echo "Sample outputs:"
  echo "Simple template variables:"
  jq -r '.variables[] | "- \(.name) (\(.type))"' /tmp/simple_analysis.json
  echo ""
  echo "Complex template file patterns:"
  jq -r '.file_patterns[] | "- \(.variable_name): \(.pattern_type) → \(.routing_hint)"' /tmp/complex_analysis.json
fi
