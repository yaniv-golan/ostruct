#!/bin/bash

# Test script for help generation (T2.3)
# Tests the generate_help.j2 template with analysis results

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Testing Help Generation (T2.3) ==="

# Test with simple template
echo "Testing help generation for simple template..."

# Combine all analysis results for simple template
jq -n \
  --argjson template_analysis "$(cat "$PROJECT_ROOT/test/analysis_simple.json")" \
  --argjson variable_classification "$(cat "$PROJECT_ROOT/test/classification_simple.json")" \
  --argjson schema_analysis "$(cat "$PROJECT_ROOT/test/schema_analysis_simple.json")" \
  --argjson pattern_detection "$(cat "$PROJECT_ROOT/test/patterns_simple.json")" \
  --argjson cli_specification "$(cat "$PROJECT_ROOT/test/cli_spec_simple.json")" \
  --argjson cli_naming "$(cat "$PROJECT_ROOT/test/simple_cli_naming.json")" \
  '{
    template_analysis: $template_analysis,
    variable_classification: $variable_classification,
    schema_analysis: $schema_analysis,
    pattern_detection: $pattern_detection,
    cli_specification: $cli_specification,
    cli_naming: $cli_naming
  }' > "$PROJECT_ROOT/test/input/simple_combined_analysis.json"

# Generate help documentation
poetry run ostruct run \
  "$PROJECT_ROOT/src/generate_help.j2" \
  "$PROJECT_ROOT/src/help_generation_schema.json" \
  --file prompt:combined_analysis "$PROJECT_ROOT/test/input/simple_combined_analysis.json" \
  --output-file "$PROJECT_ROOT/test/simple_help_generation.json"

# Validate output
if [ -f "$PROJECT_ROOT/test/simple_help_generation.json" ]; then
  echo "✓ Simple help generation output created"

  # Check JSON validity
  if jq empty "$PROJECT_ROOT/test/simple_help_generation.json" 2>/dev/null; then
    echo "✓ Simple help generation output is valid JSON"
  else
    echo "✗ Simple help generation output is invalid JSON"
    exit 1
  fi

  # Check schema compliance
  if jq -e '.tool_description.name' "$PROJECT_ROOT/test/simple_help_generation.json" >/dev/null; then
    echo "✓ Simple help generation contains tool description"
  else
    echo "✗ Simple help generation missing tool description"
    exit 1
  fi

  # Check for key sections
  for section in "usage_patterns" "argument_documentation" "file_routing" "tool_integration" "security_considerations" "troubleshooting"; do
    if jq -e ".$section" "$PROJECT_ROOT/test/simple_help_generation.json" >/dev/null; then
      echo "✓ Simple help generation contains $section"
    else
      echo "✗ Simple help generation missing $section"
      exit 1
    fi
  done

  echo "  File size: $(wc -c < "$PROJECT_ROOT/test/simple_help_generation.json") bytes"
else
  echo "✗ Simple help generation output not created"
  exit 1
fi

# Test with complex template
echo
echo "Testing help generation for complex template..."

# Combine all analysis results for complex template
jq -n \
  --argjson template_analysis "$(cat "$PROJECT_ROOT/test/analysis_complex.json")" \
  --argjson variable_classification "$(cat "$PROJECT_ROOT/test/classification_complex.json")" \
  --argjson schema_analysis "$(cat "$PROJECT_ROOT/test/schema_analysis_complex.json")" \
  --argjson pattern_detection "$(cat "$PROJECT_ROOT/test/patterns_complex.json")" \
  --argjson cli_specification "$(cat "$PROJECT_ROOT/test/cli_spec_complex.json")" \
  --argjson cli_naming "$(cat "$PROJECT_ROOT/test/complex_cli_naming.json")" \
  '{
    template_analysis: $template_analysis,
    variable_classification: $variable_classification,
    schema_analysis: $schema_analysis,
    pattern_detection: $pattern_detection,
    cli_specification: $cli_specification,
    cli_naming: $cli_naming
  }' > "$PROJECT_ROOT/test/input/complex_combined_analysis.json"

# Generate help documentation
poetry run ostruct run \
  "$PROJECT_ROOT/src/generate_help.j2" \
  "$PROJECT_ROOT/src/help_generation_schema.json" \
  --file prompt:combined_analysis "$PROJECT_ROOT/test/input/complex_combined_analysis.json" \
  --output-file "$PROJECT_ROOT/test/complex_help_generation.json"

# Validate output
if [ -f "$PROJECT_ROOT/test/complex_help_generation.json" ]; then
  echo "✓ Complex help generation output created"

  # Check JSON validity
  if jq empty "$PROJECT_ROOT/test/complex_help_generation.json" 2>/dev/null; then
    echo "✓ Complex help generation output is valid JSON"
  else
    echo "✗ Complex help generation output is invalid JSON"
    exit 1
  fi

  # Check for advanced features
  if jq -e '.usage_patterns.advanced_examples' "$PROJECT_ROOT/test/complex_help_generation.json" >/dev/null; then
    echo "✓ Complex help generation contains advanced examples"
  else
    echo "✗ Complex help generation missing advanced examples"
    exit 1
  fi

  # Check for file routing examples
  if jq -e '.file_routing.code_interpreter_files.examples' "$PROJECT_ROOT/test/complex_help_generation.json" >/dev/null; then
    echo "✓ Complex help generation contains file routing examples"
  else
    echo "✗ Complex help generation missing file routing examples"
    exit 1
  fi

  echo "  File size: $(wc -c < "$PROJECT_ROOT/test/complex_help_generation.json") bytes"
else
  echo "✗ Complex help generation output not created"
  exit 1
fi

echo
echo "=== Help Generation Tests Complete ==="
echo "✓ All tests passed"
echo "Generated files:"
echo "  - $PROJECT_ROOT/test/simple_help_generation.json"
echo "  - $PROJECT_ROOT/test/complex_help_generation.json"
