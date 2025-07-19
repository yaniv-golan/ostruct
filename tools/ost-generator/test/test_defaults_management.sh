#!/bin/bash

# Test script for defaults management (T2.5)
# Tests the manage_defaults.j2 template with all combined analysis results

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Testing Defaults Management (T2.5) ==="

# Test with simple template
echo "Testing defaults management for simple template..."

# Create combined analysis with policy generation
jq -n \
  --argjson template_analysis "$(cat "$PROJECT_ROOT/test/analysis_simple.json")" \
  --argjson variable_classification "$(cat "$PROJECT_ROOT/test/classification_simple.json")" \
  --argjson schema_analysis "$(cat "$PROJECT_ROOT/test/schema_analysis_simple.json")" \
  --argjson pattern_detection "$(cat "$PROJECT_ROOT/test/patterns_simple.json")" \
  --argjson cli_specification "$(cat "$PROJECT_ROOT/test/cli_spec_simple.json")" \
  --argjson cli_naming "$(cat "$PROJECT_ROOT/test/simple_cli_naming.json")" \
  --argjson policy_generation "$(cat "$PROJECT_ROOT/test/simple_policy_generation.json")" \
  '{
    template_analysis: $template_analysis,
    variable_classification: $variable_classification,
    schema_analysis: $schema_analysis,
    pattern_detection: $pattern_detection,
    cli_specification: $cli_specification,
    cli_naming: $cli_naming,
    policy_generation: $policy_generation
  }' > "$PROJECT_ROOT/test/input/simple_full_analysis.json"

# Generate defaults management
poetry run ostruct run \
  "$PROJECT_ROOT/src/manage_defaults.j2" \
  "$PROJECT_ROOT/src/defaults_management_schema.json" \
  --file prompt:combined_analysis "$PROJECT_ROOT/test/input/simple_full_analysis.json" \
  --output-file "$PROJECT_ROOT/test/simple_defaults_management.json"

# Validate output
if [ -f "$PROJECT_ROOT/test/simple_defaults_management.json" ]; then
  echo "✓ Simple defaults management output created"

  # Check JSON validity
  if jq empty "$PROJECT_ROOT/test/simple_defaults_management.json" 2>/dev/null; then
    echo "✓ Simple defaults management output is valid JSON"
  else
    echo "✗ Simple defaults management output is invalid JSON"
    exit 1
  fi

  # Check schema compliance
  if jq -e '.default_value_sources.template_defaults' "$PROJECT_ROOT/test/simple_defaults_management.json" >/dev/null; then
    echo "✓ Simple defaults management contains template defaults"
  else
    echo "✗ Simple defaults management missing template defaults"
    exit 1
  fi

  # Check for key sections
  for section in "precedence_rules" "environment_variable_integration" "configuration_file_handling" "runtime_override_mechanisms" "validation_and_conflict_resolution"; do
    if jq -e ".$section" "$PROJECT_ROOT/test/simple_defaults_management.json" >/dev/null; then
      echo "✓ Simple defaults management contains $section"
    else
      echo "✗ Simple defaults management missing $section"
      exit 1
    fi
  done

  echo "  File size: $(wc -c < "$PROJECT_ROOT/test/simple_defaults_management.json") bytes"
else
  echo "✗ Simple defaults management output not created"
  exit 1
fi

# Test with complex template
echo
echo "Testing defaults management for complex template..."

# Create combined analysis with policy generation
jq -n \
  --argjson template_analysis "$(cat "$PROJECT_ROOT/test/analysis_complex.json")" \
  --argjson variable_classification "$(cat "$PROJECT_ROOT/test/classification_complex.json")" \
  --argjson schema_analysis "$(cat "$PROJECT_ROOT/test/schema_analysis_complex.json")" \
  --argjson pattern_detection "$(cat "$PROJECT_ROOT/test/patterns_complex.json")" \
  --argjson cli_specification "$(cat "$PROJECT_ROOT/test/cli_spec_complex.json")" \
  --argjson cli_naming "$(cat "$PROJECT_ROOT/test/complex_cli_naming.json")" \
  --argjson policy_generation "$(cat "$PROJECT_ROOT/test/complex_policy_generation.json")" \
  '{
    template_analysis: $template_analysis,
    variable_classification: $variable_classification,
    schema_analysis: $schema_analysis,
    pattern_detection: $pattern_detection,
    cli_specification: $cli_specification,
    cli_naming: $cli_naming,
    policy_generation: $policy_generation
  }' > "$PROJECT_ROOT/test/input/complex_full_analysis.json"

# Generate defaults management
poetry run ostruct run \
  "$PROJECT_ROOT/src/manage_defaults.j2" \
  "$PROJECT_ROOT/src/defaults_management_schema.json" \
  --file prompt:combined_analysis "$PROJECT_ROOT/test/input/complex_full_analysis.json" \
  --output-file "$PROJECT_ROOT/test/complex_defaults_management.json"

# Validate output
if [ -f "$PROJECT_ROOT/test/complex_defaults_management.json" ]; then
  echo "✓ Complex defaults management output created"

  # Check JSON validity
  if jq empty "$PROJECT_ROOT/test/complex_defaults_management.json" 2>/dev/null; then
    echo "✓ Complex defaults management output is valid JSON"
  else
    echo "✗ Complex defaults management output is invalid JSON"
    exit 1
  fi

  # Check for advanced features
  if jq -e '.precedence_rules.precedence_order[]' "$PROJECT_ROOT/test/complex_defaults_management.json" >/dev/null; then
    echo "✓ Complex defaults management contains precedence order"
  else
    echo "✗ Complex defaults management missing precedence order"
    exit 1
  fi

  # Check for environment variable integration
  if jq -e '.environment_variable_integration.naming_convention' "$PROJECT_ROOT/test/complex_defaults_management.json" >/dev/null; then
    echo "✓ Complex defaults management contains environment variable integration"
  else
    echo "✗ Complex defaults management missing environment variable integration"
    exit 1
  fi

  # Check for debugging capabilities
  if jq -e '.debugging_and_troubleshooting.debug_modes' "$PROJECT_ROOT/test/complex_defaults_management.json" >/dev/null; then
    echo "✓ Complex defaults management contains debugging capabilities"
  else
    echo "✗ Complex defaults management missing debugging capabilities"
    exit 1
  fi

  echo "  File size: $(wc -c < "$PROJECT_ROOT/test/complex_defaults_management.json") bytes"
else
  echo "✗ Complex defaults management output not created"
  exit 1
fi

echo
echo "=== Defaults Management Tests Complete ==="
echo "✓ All tests passed"
echo "Generated files:"
echo "  - $PROJECT_ROOT/test/simple_defaults_management.json"
echo "  - $PROJECT_ROOT/test/complex_defaults_management.json"
