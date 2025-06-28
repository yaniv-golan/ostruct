#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# Multi-tool data analysis
ANALYSIS_TYPE="comprehensive"

run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      run_test templates/main.j2 schemas/main.json \
        --file ci:sales_data data/test_small.csv \
        -V analysis_type="${ANALYSIS_TYPE:-basic}" \
        --enable-tool code-interpreter
      ;;
    "full")
      echo "🚀 Running full analysis..."
      run_ostruct templates/main.j2 schemas/main.json \
        --file ci:sales_data data/sales_data.csv \
        --file ci:customer_data data/customer_data.csv \
        --file fs:business_docs business_docs/ \
        -V analysis_type="$ANALYSIS_TYPE" \
        --enable-tool code-interpreter \
        --enable-tool file-search
      echo "✅ Analysis completed successfully"
      ;;
  esac
}

# Parse custom arguments
parse_args_with_getoptions "$@" <<'EOF'
  param   ANALYSIS_TYPE --analysis-type               -- "Type of analysis to perform (default: comprehensive)"
EOF

execute_mode
