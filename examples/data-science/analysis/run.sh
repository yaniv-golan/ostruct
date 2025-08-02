#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# Simple single-template example
run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      run_test templates/main.j2 schemas/main.json \
        --file ci:sales data/test_tiny.csv \
        --enable-tool code-interpreter \
        --ci-download
      ;;
    "full")
      echo "🚀 Running full example..."
      run_ostruct templates/main.j2 schemas/main.json \
        --file ci:sales data/sample.csv \
        --enable-tool code-interpreter \
        --ci-download
      echo "✅ Example completed successfully"
      ;;
  esac
}

# Parse standard arguments and execute
parse_standard_args "$@"
execute_mode
