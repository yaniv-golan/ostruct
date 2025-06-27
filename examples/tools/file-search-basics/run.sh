#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# File search example with multiple documents
run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      run_test templates/main.j2 schemas/main.json \
        --file fs:policies data/test_doc.txt \
        --enable-tool file-search
      ;;
    "full")
      echo "🚀 Running full example..."
      run_ostruct templates/main.j2 schemas/main.json \
        --file fs:policies data/company_policy.txt \
        --file fs:policies data/employee_handbook.txt \
        --enable-tool file-search
      echo "✅ Example completed successfully"
      ;;
  esac
}

# Parse standard arguments and execute
parse_standard_args "$@"
execute_mode
