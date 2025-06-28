#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# Etymology analysis example
run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      run_test templates/main.j2 schemas/main.json \
        -V word="${WORD:-automobile}" \
        --sys-file templates/system.txt
      ;;
    "full")
      echo "🚀 Running full example..."
      run_ostruct templates/main.j2 schemas/main.json \
        -V word="${WORD:-automobile}" \
        --sys-file templates/system.txt
      echo "✅ Example completed successfully"
      ;;
  esac
}

# Parse arguments with custom word option
WORD="automobile"
parse_args_with_getoptions "$@" <<'EOF'
  param   WORD       --word                         -- "Word to analyze (default: automobile)"
EOF

execute_mode
