#!/usr/bin/env bash
# Convert debate_init.json to Mermaid text
set -euo pipefail
TRANSCRIPT="$1"
TOPIC="${2:-Debate Topic}"

jq -r --arg topic "$TOPIC" '
  . as $root |
  (["graph TD"] +
  ["    T0[\"📋 TOPIC: " + $topic + "\"]"] +
  [.turns[] |
    "    T" + (.round|tostring) +
    "[\"" + (.agent|ascii_upcase) + ": " +
    (.response|gsub("\"";"\\\"")|.[0:60]) + "…\"]"
  ] +
  ["    T0 --> T1"] +
  ["    T0 --> T2"] +
  [.turns[] as $t |
    ($t.supports[]? | select(. != $t.round and . > 0 and . <= ($root.turns | length)) |
      "    T" + (.|tostring) + " -->|\"🤝 supports\"| T" + ($t.round|tostring)),
    ($t.attacks[]? | select(. != $t.round and . > 0 and . <= ($root.turns | length)) |
      "    T" + (.|tostring) + " -.->|\"⚔️ attacks\"| T" + ($t.round|tostring))
  ] +
  [""] +
  ["    %% Styling"] +
  ["    classDef topicNode fill:#fff3e0,stroke:#ff9800,stroke-width:3px,color:#000"] +
  ["    classDef proNode fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000"] +
  ["    classDef conNode fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000"] +
  ["    class T0 topicNode"] +
  [.turns[] | select(.agent == "pro") |
    "    class T" + (.round|tostring) + " proNode"] +
  [.turns[] | select(.agent == "con") |
    "    class T" + (.round|tostring) + " conNode"]
  )[]
' "$TRANSCRIPT"
