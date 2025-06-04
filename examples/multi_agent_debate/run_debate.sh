#!/usr/bin/env bash
# Usage: ./run_debate.sh [rounds] [topic]
#   rounds: Number of debate rounds (default: 2)
#   topic:  Debate topic (default: read from topic.txt)
set -euo pipefail

# Show help if requested
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Multi-Agent Evidence-Seeking Debate"
  echo ""
  echo "Usage: $0 [rounds] [topic]"
  echo ""
  echo "Arguments:"
  echo "  rounds    Number of debate rounds (default: 2)"
  echo "  topic     Debate topic (default: read from topic.txt)"
  echo ""
  echo "Examples:"
  echo "  $0                                    # 2 rounds, topic from topic.txt"
  echo "  $0 3                                  # 3 rounds, topic from topic.txt"
  echo "  $0 2 \"AI should be regulated\"         # 2 rounds, custom topic"
  echo "  $0 4 \"Climate change is urgent\"       # 4 rounds, custom topic"
  echo ""
  echo "Output files are generated in the output/ directory:"
  echo "  • debate_detailed.html - Interactive detailed view"
  echo "  • debate_overview.svg - Clean argument flow diagram"
  echo "  • summary.json - Judge analysis and verdict"
  echo "  • debate_init.json - Full debate transcript"
  echo ""
  echo "Dependencies (jq, Mermaid CLI) are auto-installed if missing."
  exit 0
fi

# Parse arguments
ROUNDS=${1:-2}
TOPIC_ARG=${2:-}

DIR="$(cd "$(dirname "$0")" && pwd)"
TRANSCRIPT="$DIR/output/debate_init.json"

# Always use quiet mode for cleaner output
PROGRESS_FLAG="--progress-level none"

# Ensure output directory exists
mkdir -p "$DIR/output"

# Ensure required tools are available
source "$DIR/scripts/ensure_jq.sh"

# Determine topic source
if [ -n "$TOPIC_ARG" ]; then
  TOPIC="$TOPIC_ARG"
  echo "Using topic from command line argument"
else
  TOPIC="$(cat "$DIR/topic.txt")"
  echo "Using topic from topic.txt"
fi

echo "🎯 MULTI-AGENT DEBATE SYSTEM"
echo "=============================="
echo "Topic: $TOPIC"
echo "Rounds: $ROUNDS ($(($ROUNDS * 2)) total turns)"
echo "Web search: Enabled (up to 2 searches per turn)"
echo ""

# fresh start - create initial empty transcript
echo '{"topic": "", "turns": []}' > "$TRANSCRIPT"

for (( r=1; r<=ROUNDS; r++ )); do
  echo "🔵 Round $r – PRO side arguing..."
  bash "$DIR/scripts/run_round.sh" pro "$r" "$TOPIC"

  # Show PRO argument details
  echo ""
  echo "   📍 PRO Position: $(jq -r '.turns[-1].stance' "$TRANSCRIPT")"
  echo "   💭 Argument:"
  jq -r '.turns[-1].response' "$TRANSCRIPT" | fold -w 80 -s | sed 's/^/      /'
  echo ""
  if [ "$(jq -r '.turns[-1].research_used' "$TRANSCRIPT")" = "true" ]; then
    echo "   📚 Citations:"
    jq -r '.turns[-1].citations[]? | "• " + .title + " (" + .url + ")"' "$TRANSCRIPT" | sed 's/^/      /'
    echo ""
  fi

  echo "🔴 Round $r – CON side responding..."
  bash "$DIR/scripts/run_round.sh" con "$r" "$TOPIC"

  # Show CON argument details
  echo ""
  echo "   📍 CON Position: $(jq -r '.turns[-1].stance' "$TRANSCRIPT")"
  echo "   💭 Argument:"
  jq -r '.turns[-1].response' "$TRANSCRIPT" | fold -w 80 -s | sed 's/^/      /'
  echo ""
  if [ "$(jq -r '.turns[-1].research_used' "$TRANSCRIPT")" = "true" ]; then
    echo "   📚 Citations:"
    jq -r '.turns[-1].citations[]? | "• " + .title + " (" + .url + ")"' "$TRANSCRIPT" | sed 's/^/      /'
    echo ""
  fi
  if [ "$(jq -r '.turns[-1].attacks | length' "$TRANSCRIPT")" -gt 0 ]; then
    echo "   ⚔️  Attacks $(jq -r '.turns[-1].attacks | length' "$TRANSCRIPT") previous arguments:"
    jq -r '.turns[-1].attacks[] | "→ Attacking turn " + (. + 1 | tostring)' "$TRANSCRIPT" | sed 's/^/      /'
    echo ""
  fi
done

echo "⚖️  JUDGING PHASE"
echo "=================="
echo "Impartial AI judge analyzing $(jq '.turns | length' "$TRANSCRIPT") turns..."
ostruct run "$DIR/prompts/summary.j2" "$DIR/schemas/summary.json" \
  -V topic="$TOPIC" \
  --fta transcript "$TRANSCRIPT" \
  $PROGRESS_FLAG \
  > "$DIR/output/summary.json"

# Show results
WINNER=$(jq -r '.winning_side | ascii_upcase' "$DIR/output/summary.json")
VERDICT=$(jq -r '.verdict' "$DIR/output/summary.json")
STRONGEST=$(jq -r '.strongest_point' "$DIR/output/summary.json")

echo ""
echo "🏆 DEBATE RESULTS"
echo "=================="
echo "🥇 Winner: $WINNER"
echo ""
echo "💪 Strongest argument:"
echo "   $STRONGEST"
echo ""
echo "📋 Judge's reasoning:"
echo "   $VERDICT"
echo ""

# ---- render visualizations ----
echo "📊 GENERATING VISUALIZATIONS"
echo "============================="

# Generate overview SVG diagram first
echo "Creating overview diagram..."
# Try to generate Mermaid diagram with timeout
if command -v mmdc >/dev/null 2>&1; then
  echo "Using installed Mermaid CLI..."
  "$DIR/scripts/json2mermaid.sh" "$TRANSCRIPT" "$TOPIC" | mmdc -i - -o "$DIR/output/debate_overview.svg"
elif command -v npx >/dev/null 2>&1; then
  echo "Installing Mermaid CLI via npx..."
  if timeout 30 npx --yes @mermaid-js/mermaid-cli mmdc --version >/dev/null 2>&1; then
    "$DIR/scripts/json2mermaid.sh" "$TRANSCRIPT" "$TOPIC" | npx --yes @mermaid-js/mermaid-cli mmdc -i - -o "$DIR/output/debate_overview.svg"
  else
    echo "⚠️  Mermaid installation timed out, skipping overview diagram"
    echo "   You can manually generate it later with:"
    echo "   ./json2mermaid.sh debate_init.json | npx @mermaid-js/mermaid-cli mmdc -i - -o debate_overview.svg"
  fi
else
  echo "⚠️  Node.js/npx not available, skipping overview diagram"
  echo "   Install Node.js and run: ./json2mermaid.sh debate_init.json | npx @mermaid-js/mermaid-cli mmdc -i - -o debate_overview.svg"
fi

# Generate detailed HTML view (after SVG so it can embed it)
echo "Creating detailed HTML view..."
"$DIR/scripts/json2html.sh" "$TRANSCRIPT" "$DIR/output/debate_detailed.html" "$DIR/output/summary.json" "$DIR/output/debate_overview.svg"

echo ""
echo "✅ DEBATE COMPLETE!"
echo "==================="
echo "📁 Files generated:"
echo "   • output/debate_detailed.html - Interactive detailed view with full arguments"
if [ -f "$DIR/output/debate_overview.svg" ]; then
  echo "   • output/debate_overview.svg - Clean argument flow diagram"
fi
echo "   • output/summary.json - Complete judge analysis"
echo "   • output/debate_init.json - Full debate transcript"
echo ""
echo "🖼️  To view the results:"
echo "   📄 Detailed view: open output/debate_detailed.html"
if [ -f "$DIR/output/debate_overview.svg" ]; then
  echo "   📊 Overview diagram: open output/debate_overview.svg"
fi
echo ""
echo "📖 To read the raw analysis:"
echo "   cat output/summary.json | jq ."
