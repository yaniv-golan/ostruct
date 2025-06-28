#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# Web search basics
TOPIC="AI developments"

run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      run_test templates/main.j2 schemas/main.json \
        -V question="What are the latest AI safety developments?" \
        --enable-tool web-search
      ;;
    "full")
      echo "🚀 Running full web search..."
      run_ostruct templates/main.j2 schemas/main.json \
        -V question="$TOPIC" \
        --enable-tool web-search
      echo "✅ Web search completed successfully"
      ;;
  esac
}

# Parse custom arguments
parse_args_with_getoptions "$@" <<'EOF'
  param   TOPIC  --topic                    -- "Research topic/question (default: AI developments)"
EOF

execute_mode
