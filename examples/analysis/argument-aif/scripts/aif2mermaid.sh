#!/usr/bin/env bash
# Convert AIF JSON to color-coded Mermaid diagram with AIF Extension support
set -euo pipefail

AIF_FILE="$1"
TITLE="${2:-AIF Argument Graph}"

# Ensure jq is available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../../../scripts/install/dependencies/ensure_jq.sh"

jq -r --arg title "$TITLE" '
  . as $root |

  # Create lookup tables for node types and edge relationships
  (.nodes | map({(.nodeID): .type}) | add) as $node_types |

  (["graph TD"] +
  ["    subgraph \"📋 " + $title + "\""] +

  # Generate nodes with AIF extension support - use displayName if available, otherwise truncate text
  [.nodes[] |
    # Use displayName from AIF extension if available, otherwise create short version
    (.displayName // (.text | .[0:60] + (if (.text | length) > 60 then "..." else "" end))) as $display_text |

    # Use category from AIF extension for enhanced icons
    (.category // .type) as $node_category |

    # Select icon based on category or type
    (if ($node_category == "premise" or $node_category == "evidence" or .type == "I") then "💬 "
     elif ($node_category == "inference" or .type == "RA") then "✅ "
     elif ($node_category == "conflict" or .type == "CA") then "⚔️ "
     elif ($node_category == "preference" or .type == "PA") then "⭐ "
     elif ($node_category == "assumption" or .type == "MA") then "🔗 "
     elif ($node_category == "conclusion") then "🎯 "
     else "❓ " end) as $icon |

    "    " + .nodeID + "[\"" + $icon +
    ($display_text | gsub("\""; "\\\"")) + "\"]"
  ] +

  # Generate edges with AIF extension relationshipType support
  [.edges[] |
    # Use relationshipType from AIF extension if available
    (.relationshipType //
     # Fallback: determine edge type based on source and target node types
     (($node_types[.fromID] // "unknown") as $from_type |
      ($node_types[.toID] // "unknown") as $to_type |
      if ($from_type == "I" and $to_type == "RA") then "supports"
      elif ($from_type == "I" and $to_type == "CA") then "conflicts"
      elif ($from_type == "RA" and $to_type == "I") then "infers"
      elif ($from_type == "CA" and $to_type == "I") then "attacks"
      elif ($from_type == "I" and $to_type == "I") then "relates"
      elif ($from_type == "PA" and $to_type == "I") then "prefers"
      elif ($from_type == "I" and $to_type == "PA") then "evaluated"
      else "relates" end)
    ) as $relationship |

    # Create edge with appropriate styling and label based on relationship type
    if ($relationship == "supports") then
      "    " + .fromID + " -.->|\"supports\"| " + .toID
    elif ($relationship == "conflicts") then
      "    " + .fromID + " -.->|\"conflicts\"| " + .toID
    elif ($relationship == "infers") then
      "    " + .fromID + " ==>|\"infers\"| " + .toID
    elif ($relationship == "attacks") then
      "    " + .fromID + " ==>|\"attacks\"| " + .toID
    elif ($relationship == "prefers") then
      "    " + .fromID + " ==>|\"prefers\"| " + .toID
    elif ($relationship == "relates") then
      "    " + .fromID + " -->|\"relates\"| " + .toID
    else
      "    " + .fromID + " -->|\"" + $relationship + "\"| " + .toID
    end
  ] +

  ["    end"] +
  [""] +
  ["    %% Enhanced Styling with AIF Extension Support"] +
  ["    classDef infoNode fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef ruleNode fill:#e8f5e8,stroke:#4caf50,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef conflictNode fill:#fce4ec,stroke:#e91e63,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef prefNode fill:#fff3e0,stroke:#ff9800,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef maNode fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef conclusionNode fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px,color:#000,font-size:11px"] +
  ["    classDef premiseNode fill:#e1f5fe,stroke:#0277bd,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef evidenceNode fill:#f1f8e9,stroke:#558b2f,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef defaultNode fill:#f5f5f5,stroke:#757575,stroke-width:2px,color:#000,font-size:11px"] +

  # Apply styles to nodes based on AIF extension category or fallback to type
  [.nodes[] |
    (.category // .type) as $node_category |
    if ($node_category == "conclusion") then
      "    class " + .nodeID + " conclusionNode"
    elif ($node_category == "premise") then
      "    class " + .nodeID + " premiseNode"
    elif ($node_category == "evidence") then
      "    class " + .nodeID + " evidenceNode"
    elif ($node_category == "inference" or .type == "RA") then
      "    class " + .nodeID + " ruleNode"
    elif ($node_category == "conflict" or .type == "CA") then
      "    class " + .nodeID + " conflictNode"
    elif ($node_category == "preference" or .type == "PA") then
      "    class " + .nodeID + " prefNode"
    elif ($node_category == "assumption" or .type == "MA") then
      "    class " + .nodeID + " maNode"
    elif (.type == "I") then
      "    class " + .nodeID + " infoNode"
    else
      "    class " + .nodeID + " defaultNode"
    end
  ] +

  [""] +
  ["    %% Clickable nodes show full text (works in mermaid.live)"] +
  # Add click events that work in mermaid.live and other interactive environments
  [.nodes[] |
    "    click " + .nodeID + " \"" + (.text | gsub("\""; "\\\"") | gsub("\n"; " ")) + "\" _blank"
  ] +
  [""] +
  ["    %% Full text for each node (for reference)"] +
  # Add comments with full text for reference
  [.nodes[] |
    "    %% Node " + .nodeID + ": " + (.text | gsub("\n"; " "))
  ]
  )[]
' "$AIF_FILE"
