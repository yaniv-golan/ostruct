#!/usr/bin/env bash
# Usage: run_round.sh pro|con <round> <topic>
set -euo pipefail
AGENT=$1
ROUND=$2
TOPIC=$3

DIR="$(cd "$(dirname "$0")/.." && pwd)"
TRANSCRIPT="$DIR/output/debate_init.json"

# Map AGENT to correct prompt filename
case "$AGENT" in
  pro)
    PROMPT="$DIR/templates/pro_side.j2"
    ;;
  con)
    PROMPT="$DIR/templates/con_side.j2"
    ;;
  *)
    echo "Unknown agent: $AGENT" >&2
    exit 1
    ;;
esac
SCHEMA="$DIR/schemas/turn.json"

# Calculate turn number (unique for each turn)
TURN_COUNT=$(jq '.turns | length' "$TRANSCRIPT")
TURN_NUMBER=$((TURN_COUNT + 1))

# Run ostruct in quiet mode
ostruct run "$PROMPT" "$SCHEMA" \
  --model gpt-4.1 \
  --enable-tool web-search \
  --progress none \
  -V topic="$TOPIC" \
  -V next_round="$TURN_NUMBER" \
      --file transcript "$TRANSCRIPT" \
> "$DIR/new_turn.json"

# Merge the new turn into the transcript
jq --slurpfile new_turn "$DIR/new_turn.json" '.turns += $new_turn' "$TRANSCRIPT" > "$DIR/.tmp" && mv "$DIR/.tmp" "$TRANSCRIPT"
rm -f "$DIR/new_turn.json"
