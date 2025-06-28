#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# Argument to AIF conversion
run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      run_test templates/main.j2 schemas/main.json \
        -V argument_text="Simple test argument for validation"
      ;;
    "full")
      echo "🚀 Running full example..."
      run_ostruct templates/main.j2 schemas/main.json \
        --file argument data/sample_argument.txt
      echo "✅ Example completed successfully"
      ;;
  esac
}

# Parse arguments (no custom arguments needed for this example)
parse_args_with_getoptions "$@" <<'EOF'
EOF

execute_mode
