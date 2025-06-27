#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# Multi-agent debate with web search
ROUNDS=2
TOPIC=""

run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      run_test templates/main.j2 schemas/main.json \
        -V topic="AI safety regulations" \
        -V rounds=1 \
        --enable-tool web-search
      ;;
    "full")
      echo "🚀 Running full debate..."
      local topic_arg="${TOPIC:-$(cat data/sample_topic.txt)}"

      # Run the sophisticated multi-agent debate system
      echo "🎯 Using sophisticated multi-agent debate system..."
      bash run_debate.sh "$ROUNDS" "$topic_arg"
      echo "✅ Debate completed successfully"
      ;;
  esac
}

# Parse custom arguments
parse_args_with_getoptions "$@" <<'EOF'
  param   ROUNDS     --rounds                       -- "Number of debate rounds (default: 3)"
  param   TOPIC      --topic                        -- "Debate topic (required for full mode)"
EOF

execute_mode
