#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# Default issue type
ISSUE_TYPE="all"

# Parse custom arguments
parse_args_with_getoptions "$@" <<'EOF'
  param   ISSUE_TYPE --issue-type                   -- "Type of issue to demonstrate (default: all)"
EOF

# Troubleshooting cookbook example
run_example() {
  case "$MODE" in
    "test-dry")
      echo "🧪 Running troubleshooting validation (dry-run mode)..."

      case "$ISSUE_TYPE" in
        "syntax")
          echo "🔹 Testing syntax error detection..."
          echo "⚠️ This SHOULD fail (demonstrating broken syntax):"
          run_ostruct templates/broken_syntax.j2 schemas/main.json --dry-run || echo "✅ Correctly detected syntax errors"
          echo "🔹 Testing syntax fixes..."
          run_ostruct templates/fixed_syntax.j2 schemas/main.json --dry-run -V user_name='TestUser'
          ;;
        "all"|*)
          echo "🔹 Testing broken syntax (should fail)..."
          run_ostruct templates/broken_syntax.j2 schemas/main.json --dry-run || echo "✅ Correctly detected syntax errors"
          echo "🔹 Testing fixed syntax..."
          run_ostruct templates/fixed_syntax.j2 schemas/main.json --dry-run -V user_name='TestUser'
          ;;
      esac

      echo "✅ Troubleshooting validation completed"
      ;;
    "test-live")
      echo "🧪 Running troubleshooting validation (live mode)..."
      echo "🔹 Note: Template-only example - no API calls made"

      case "$ISSUE_TYPE" in
        "syntax")
          echo "🔹 Testing syntax error detection..."
          echo "⚠️ This SHOULD fail (demonstrating broken syntax):"
          run_ostruct templates/broken_syntax.j2 schemas/main.json --dry-run || echo "✅ Correctly detected syntax errors"
          echo "🔹 Testing syntax fixes..."
          run_ostruct templates/fixed_syntax.j2 schemas/main.json --dry-run -V user_name='TestUser'
          ;;
        "all"|*)
          echo "🔹 Testing broken syntax (should fail)..."
          run_ostruct templates/broken_syntax.j2 schemas/main.json --dry-run || echo "✅ Correctly detected syntax errors"
          echo "🔹 Testing fixed syntax..."
          run_ostruct templates/fixed_syntax.j2 schemas/main.json --dry-run -V user_name='TestUser'
          ;;
      esac

      echo "✅ Troubleshooting validation completed (no API cost for template-only examples)"
      ;;

    "full")
      echo "🚀 Running full troubleshooting cookbook..."

      echo "🔹 Demonstrating broken→fixed patterns..."
      echo ""
      echo "=== BROKEN SYNTAX (will show errors) ==="
      run_ostruct templates/broken_syntax.j2 schemas/main.json \
        --dry-run || echo "✅ Correctly identified syntax issues"

      echo ""
      echo "=== FIXED SYNTAX (should work) ==="
      run_ostruct templates/fixed_syntax.j2 schemas/main.json \
        --dry-run -V user_name='TestUser'

      echo "✅ Troubleshooting cookbook completed successfully"
      ;;
  esac
}

execute_mode
