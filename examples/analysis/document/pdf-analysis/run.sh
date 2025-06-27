#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# Document analysis
ANALYSIS_TYPE="comprehensive"

run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      run_test templates/main.j2 schemas/main.json \
        --file ci:documents data/test_document.txt \
        -V analysis_type="basic" \
        --enable-tool code-interpreter
      ;;
    "full")
      echo "🚀 Running full document analysis..."
      run_ostruct templates/main.j2 schemas/main.json \
        --file ci:documents data/ \
        --file fs:context docs/ \
        -V analysis_type="$ANALYSIS_TYPE" \
        --enable-tool code-interpreter \
        --enable-tool file-search
      echo "✅ Document analysis completed successfully"
      ;;
  esac
}

# Parse custom arguments
parse_args_with_getoptions "$@" <<'EOF'
  param   ANALYSIS_TYPE  --analysis-type                    -- "Document analysis type (default: comprehensive)"
EOF

execute_mode
