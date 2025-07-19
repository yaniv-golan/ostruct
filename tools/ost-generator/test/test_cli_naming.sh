#!/bin/bash

# Test script for CLI naming generation (T2.2)
# Tests the generate_names.j2 template with CLI specification results

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Testing CLI Naming Generation (T2.2) ==="

# Test with simple template
echo "Testing CLI naming generation for simple template..."

# Generate CLI naming
poetry run ostruct run \
  "$PROJECT_ROOT/src/generate_names.j2" \
  "$PROJECT_ROOT/src/cli_naming_schema.json" \
  --file prompt:cli_specification "$PROJECT_ROOT/test/cli_spec_simple.json" \
  --output-file "$PROJECT_ROOT/test/simple_cli_naming.json"

# Validate output
if [ -f "$PROJECT_ROOT/test/simple_cli_naming.json" ]; then
  echo "✓ Simple CLI naming output created"

  # Check JSON validity
  if jq empty "$PROJECT_ROOT/test/simple_cli_naming.json" 2>/dev/null; then
    echo "✓ Simple CLI naming output is valid JSON"
  else
    echo "✗ Simple CLI naming output is invalid JSON"
    exit 1
  fi

  # Check schema compliance
  if jq -e '.naming_results.tool_name.validated' "$PROJECT_ROOT/test/simple_cli_naming.json" >/dev/null; then
    echo "✓ Simple CLI naming contains tool name analysis"
  else
    echo "✗ Simple CLI naming missing tool name analysis"
    exit 1
  fi

  # Check for key sections
  for section in "naming_results" "naming_conventions" "quality_metrics" "recommendations"; do
    if jq -e ".$section" "$PROJECT_ROOT/test/simple_cli_naming.json" >/dev/null; then
      echo "✓ Simple CLI naming contains $section"
    else
      echo "✗ Simple CLI naming missing $section"
      exit 1
    fi
  done

  echo "  File size: $(wc -c < "$PROJECT_ROOT/test/simple_cli_naming.json") bytes"
else
  echo "✗ Simple CLI naming output not created"
  exit 1
fi

# Test with complex template
echo
echo "Testing CLI naming generation for complex template..."

# Generate CLI naming
poetry run ostruct run \
  "$PROJECT_ROOT/src/generate_names.j2" \
  "$PROJECT_ROOT/src/cli_naming_schema.json" \
  --file prompt:cli_specification "$PROJECT_ROOT/test/cli_spec_complex.json" \
  --output-file "$PROJECT_ROOT/test/complex_cli_naming.json"

# Validate output
if [ -f "$PROJECT_ROOT/test/complex_cli_naming.json" ]; then
  echo "✓ Complex CLI naming output created"

  # Check JSON validity
  if jq empty "$PROJECT_ROOT/test/complex_cli_naming.json" 2>/dev/null; then
    echo "✓ Complex CLI naming output is valid JSON"
  else
    echo "✗ Complex CLI naming output is invalid JSON"
    exit 1
  fi

  # Check for conflict resolution
  if jq -e '.naming_conventions.conflict_resolution_strategy' "$PROJECT_ROOT/test/complex_cli_naming.json" >/dev/null; then
    echo "✓ Complex CLI naming contains conflict resolution"
  else
    echo "✗ Complex CLI naming missing conflict resolution"
    exit 1
  fi

  # Check quality metrics
  if jq -e '.quality_metrics.naming_consistency' "$PROJECT_ROOT/test/complex_cli_naming.json" >/dev/null; then
    echo "✓ Complex CLI naming contains quality metrics"
  else
    echo "✗ Complex CLI naming missing quality metrics"
    exit 1
  fi

  echo "  File size: $(wc -c < "$PROJECT_ROOT/test/complex_cli_naming.json") bytes"
else
  echo "✗ Complex CLI naming output not created"
  exit 1
fi

echo
echo "=== CLI Naming Generation Tests Complete ==="
echo "✓ All tests passed"
echo "Generated files:"
echo "  - $PROJECT_ROOT/test/simple_cli_naming.json"
echo "  - $PROJECT_ROOT/test/complex_cli_naming.json"
