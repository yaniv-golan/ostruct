#!/bin/bash

# Test script for policy generation (T2.4)
# Tests the generate_policy.j2 template with combined analysis results

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Testing Policy Generation (T2.4) ==="

# Test with simple template
echo "Testing policy generation for simple template..."

# Use the existing combined analysis file
poetry run ostruct run \
  "$PROJECT_ROOT/src/generate_policy.j2" \
  "$PROJECT_ROOT/src/policy_generation_schema.json" \
  --file prompt:combined_analysis "$PROJECT_ROOT/test/input/simple_combined_analysis.json" \
  --output-file "$PROJECT_ROOT/test/simple_policy_generation.json"

# Validate output
if [ -f "$PROJECT_ROOT/test/simple_policy_generation.json" ]; then
  echo "✓ Simple policy generation output created"

  # Check JSON validity
  if jq empty "$PROJECT_ROOT/test/simple_policy_generation.json" 2>/dev/null; then
    echo "✓ Simple policy generation output is valid JSON"
  else
    echo "✗ Simple policy generation output is invalid JSON"
    exit 1
  fi

  # Check schema compliance
  if jq -e '.model_policy.default_model' "$PROJECT_ROOT/test/simple_policy_generation.json" >/dev/null; then
    echo "✓ Simple policy generation contains model policy"
  else
    echo "✗ Simple policy generation missing model policy"
    exit 1
  fi

  # Check for key sections
  for section in "tool_integration_policy" "security_policy" "global_arguments_policy" "error_handling_policy" "resource_management_policy"; do
    if jq -e ".$section" "$PROJECT_ROOT/test/simple_policy_generation.json" >/dev/null; then
      echo "✓ Simple policy generation contains $section"
    else
      echo "✗ Simple policy generation missing $section"
      exit 1
    fi
  done

  echo "  File size: $(wc -c < "$PROJECT_ROOT/test/simple_policy_generation.json") bytes"
else
  echo "✗ Simple policy generation output not created"
  exit 1
fi

# Test with complex template
echo
echo "Testing policy generation for complex template..."

# Use the existing combined analysis file
poetry run ostruct run \
  "$PROJECT_ROOT/src/generate_policy.j2" \
  "$PROJECT_ROOT/src/policy_generation_schema.json" \
  --file prompt:combined_analysis "$PROJECT_ROOT/test/input/complex_combined_analysis.json" \
  --output-file "$PROJECT_ROOT/test/complex_policy_generation.json"

# Validate output
if [ -f "$PROJECT_ROOT/test/complex_policy_generation.json" ]; then
  echo "✓ Complex policy generation output created"

  # Check JSON validity
  if jq empty "$PROJECT_ROOT/test/complex_policy_generation.json" 2>/dev/null; then
    echo "✓ Complex policy generation output is valid JSON"
  else
    echo "✗ Complex policy generation output is invalid JSON"
    exit 1
  fi

  # Check for advanced features
  if jq -e '.tool_integration_policy.enabled_tools[]' "$PROJECT_ROOT/test/complex_policy_generation.json" >/dev/null; then
    echo "✓ Complex policy generation contains enabled tools"
  else
    echo "✗ Complex policy generation missing enabled tools"
    exit 1
  fi

  # Check for security policies
  if jq -e '.security_policy.input_validation.strict_validation' "$PROJECT_ROOT/test/complex_policy_generation.json" >/dev/null; then
    echo "✓ Complex policy generation contains security validation"
  else
    echo "✗ Complex policy generation missing security validation"
    exit 1
  fi

  # Check for deployment scenarios
  if jq -e '.deployment_scenarios.production' "$PROJECT_ROOT/test/complex_policy_generation.json" >/dev/null; then
    echo "✓ Complex policy generation contains deployment scenarios"
  else
    echo "✗ Complex policy generation missing deployment scenarios"
    exit 1
  fi

  echo "  File size: $(wc -c < "$PROJECT_ROOT/test/complex_policy_generation.json") bytes"
else
  echo "✗ Complex policy generation output not created"
  exit 1
fi

echo
echo "=== Policy Generation Tests Complete ==="
echo "✓ All tests passed"
echo "Generated files:"
echo "  - $PROJECT_ROOT/test/simple_policy_generation.json"
echo "  - $PROJECT_ROOT/test/complex_policy_generation.json"
