#!/usr/bin/env bash
# Convert AIF JSON to color-coded Mermaid diagram with Enhanced AIF F-node support
set -euo pipefail

AIF_FILE="$1"
TITLE="${2:-Enhanced AIF Argument Graph}"

# Ensure jq is available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../../../scripts/install/dependencies/ensure_jq.sh"

# Generate enhanced statistics
echo "📊 Enhanced Extraction Quality Metrics:"
echo "========================================"
jq -r '
  "📋 Scheme Usage:" +
  "\n  Unique schemes: " + ([.schemeNodes[]?.schemeID] | unique | length | tostring) +
  "\n  RA/CA with schemes: " + ([.nodes[] | select(.schemeID and (.type == "RA" or .type == "CA"))] | length | tostring) +
  "\n  RA/CA without schemes: " + ([.nodes[] | select(.type == "RA" or .type == "CA") | select(.schemeID | not)] | length | tostring) +
  "\n\n📍 Location Coverage:" +
  "\n  Nodes with section: " + ([.nodes[] | select(.section)] | length | tostring) +
  "\n  Nodes with paragraph: " + ([.nodes[] | select(.para)] | length | tostring) +
  "\n  Nodes with offsets: " + ([.nodes[] | select(.offsetStart)] | length | tostring) +
  "\n\n📈 Node Distribution:" +
  "\n  I-nodes: " + ([.nodes[] | select(.type == "I")] | length | tostring) +
  "\n  RA-nodes: " + ([.nodes[] | select(.type == "RA")] | length | tostring) +
  "\n  CA-nodes: " + ([.nodes[] | select(.type == "CA")] | length | tostring) +
  "\n  PA-nodes: " + ([.nodes[] | select(.type == "PA")] | length | tostring) +
  "\n  MA-nodes: " + ([.nodes[] | select(.type == "MA")] | length | tostring) +
  "\n\n⚠️  Potential Issues:" +
  "\n  Isolated nodes: " + (
    [.nodes[] | .nodeID] as $all_nodes |
    [.edges[] | .fromID, .toID] as $connected |
    [$all_nodes[] | select(. as $n | $connected | index($n) | not)] | length | tostring
  ) +
  "\n  [Implied] content: " + ([.nodes[] | select(.text | contains("[Implied]"))] | length | tostring) +
  "\n  Missing locutions: " + (
    [.nodes[] | select(.type == "I") | .nodeID] as $i_nodes |
    [.locutions[] | .nodeID] as $locution_nodes |
    [$i_nodes[] | select(. as $n | $locution_nodes | index($n) | not)] | length | tostring
  )
' "$AIF_FILE"

echo ""
echo "🎨 Generating Enhanced Mermaid Visualization..."
echo "=============================================="

jq -r --arg title "$TITLE" '
  . as $root |

  # Create lookup tables for node types and edge relationships
  (.nodes | map({(.nodeID): .type}) | add) as $node_types |

  (["graph TD"] +
  ["    subgraph \"📋 " + $title + "\""] +

  # Generate scheme nodes as special subgraph if any exist
  (if (.schemeNodes | length) > 0 then
    ["    subgraph schemes[\"🔬 Formal Argument Schemes\"]"] +
    [.schemeNodes[] |
      "    " + .schemeID + "[\"📋 " + .schemeName + "\"]:::schemeNode"
    ] +
    ["    end"] +
    [""]
  else [] end) +

  # Generate regular nodes with enhanced AIF extension support
  [.nodes[] |
    # Use displayName from AIF extension if available, otherwise create short version
    (.displayName // (.text | .[0:60] + (if (.text | length) > 60 then "..." else "" end))) as $display_text |

    # Use category and role from enhanced AIF extension for better icons
    (.category // .type) as $node_category |
    (.role // "none") as $node_role |

    # Enhanced icon selection based on category, role, and type
    (if ($node_role == "main_thesis") then "🎯 "
     elif ($node_role == "sub_thesis") then "🔹 "
     elif ($node_category == "premise" or $node_category == "evidence" or .type == "I") then "💬 "
     elif ($node_category == "inference" or .type == "RA") then "✅ "
     elif ($node_category == "conflict" or .type == "CA") then "⚔️ "
     elif ($node_category == "preference" or .type == "PA") then "⭐ "
     elif ($node_category == "assumption" or .type == "MA") then "🔗 "
     elif ($node_category == "conclusion") then "🎯 "
     elif ($node_category == "statistic") then "📊 "
     elif ($node_category == "methodology") then "🔬 "
     elif ($node_category == "definition") then "📖 "
     elif ($node_category == "limitation") then "⚠️ "
     else "❓ " end) as $icon |

    # Add strength indicator if available
    (.strength // null) as $strength |
    ($strength | if . then " (" + (. * 100 | floor | tostring) + "%)" else "" end) as $strength_display |

    "    " + .nodeID + "[\"" + $icon +
    ($display_text | gsub("\""; "\\\"")) + $strength_display + "\"]"
  ] +

  # Generate scheme reference edges (dotted purple lines from RA/CA to their schemes)
  [.nodes[] | select(.schemeID) |
    "    " + .nodeID + " -.->|\"uses\"| " + .schemeID
  ] +

  # Generate regular edges with enhanced relationshipType support
  [.edges[] |
    # Use relationshipType from enhanced AIF extension
    (.relationshipType //
     # Fallback: determine edge type based on source and target node types
     (($node_types[.fromID] // "unknown") as $from_type |
      ($node_types[.toID] // "unknown") as $to_type |
      if ($from_type == "I" and $to_type == "RA") then "supports"
      elif ($from_type == "I" and $to_type == "CA") then "conflicts"
      elif ($from_type == "RA" and $to_type == "I") then "infers"
      elif ($from_type == "CA" and $to_type == "I") then "attacks"
      else "relates" end)
    ) as $relationship |

    # Enhanced edge styling for new relationship types
    if ($relationship == "supports") then
      "    " + .fromID + " -.->|\"supports\"| " + .toID
    elif ($relationship == "conflicts") then
      "    " + .fromID + " -.->|\"conflicts\"| " + .toID
    elif ($relationship == "infers") then
      "    " + .fromID + " ==>|\"infers\"| " + .toID
    elif ($relationship == "attacks") then
      "    " + .fromID + " ==>|\"attacks\"| " + .toID
    elif ($relationship == "assumes") then
      "    " + .fromID + " -.->|\"assumes\"| " + .toID
    elif ($relationship == "exemplifies") then
      "    " + .fromID + " -.->|\"example\"| " + .toID
    elif ($relationship == "questions") then
      "    " + .fromID + " -.->|\"questions\"| " + .toID
    elif ($relationship == "references") then
      "    " + .fromID + " -->|\"ref\"| " + .toID
    elif ($relationship == "asserts") then
      "    " + .fromID + " ==>|\"asserts\"| " + .toID
    elif ($relationship == "relates") then
      "    " + .fromID + " -->|\"relates\"| " + .toID
    else
      "    " + .fromID + " -->|\"" + $relationship + "\"| " + .toID
    end
  ] +

  ["    end"] +
  [""] +
  ["    %% Enhanced Styling with F-node Support"] +
  ["    classDef infoNode fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef ruleNode fill:#e8f5e8,stroke:#4caf50,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef conflictNode fill:#fce4ec,stroke:#e91e63,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef prefNode fill:#fff3e0,stroke:#ff9800,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef maNode fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef conclusionNode fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px,color:#000,font-size:11px"] +
  ["    classDef premiseNode fill:#e1f5fe,stroke:#0277bd,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef evidenceNode fill:#f1f8e9,stroke:#558b2f,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef statisticNode fill:#fff8e1,stroke:#f57c00,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef methodologyNode fill:#e0f2f1,stroke:#00695c,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef definitionNode fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef limitationNode fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef mainThesisNode fill:#e8f5e8,stroke:#1b5e20,stroke-width:4px,color:#000,font-size:12px"] +
  ["    classDef subThesisNode fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px,color:#000,font-size:11px"] +
  ["    classDef schemeNode fill:#f0e6ff,stroke:#8b5cf6,stroke-width:2px,color:#000,font-size:11px"] +
  ["    classDef defaultNode fill:#f5f5f5,stroke:#757575,stroke-width:2px,color:#000,font-size:11px"] +

  # Apply enhanced styles to nodes based on role and category
  [.nodes[] |
    (.category // .type) as $node_category |
    (.role // "none") as $node_role |
    if ($node_role == "main_thesis") then
      "    class " + .nodeID + " mainThesisNode"
    elif ($node_role == "sub_thesis") then
      "    class " + .nodeID + " subThesisNode"
    elif ($node_category == "conclusion") then
      "    class " + .nodeID + " conclusionNode"
    elif ($node_category == "premise") then
      "    class " + .nodeID + " premiseNode"
    elif ($node_category == "evidence") then
      "    class " + .nodeID + " evidenceNode"
    elif ($node_category == "statistic") then
      "    class " + .nodeID + " statisticNode"
    elif ($node_category == "methodology") then
      "    class " + .nodeID + " methodologyNode"
    elif ($node_category == "definition") then
      "    class " + .nodeID + " definitionNode"
    elif ($node_category == "limitation") then
      "    class " + .nodeID + " limitationNode"
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

  # Apply scheme node styling
  [.schemeNodes[] |
    "    class " + .schemeID + " schemeNode"
  ] +

  [""] +
  ["    %% Enhanced clickable nodes with metadata tooltips"] +
  # Enhanced click events with scheme information
  [.nodes[] |
    "    click " + .nodeID + " \"" +
    (.text | gsub("\""; "\\\"") | gsub("\n"; " ")) +
    "\" _blank"
  ] +

  # Add scheme node click events
  [.schemeNodes[] |
    "    click " + .schemeID + " \"" +
    .schemeName +
    "\" _blank"
  ] +

  [""] +
  ["    %% Enhanced metadata for reference"] +
  # Add enhanced comments with full metadata
  [.nodes[] |
    "    %% Node " + .nodeID + " (" + .type + "): " +
    (.text | gsub("\n"; " ")) +
    " [Role: " + (.role // "none") +
    ", Category: " + (.category // "none") +
    ", Scheme: " + (.schemeID // "none") + "]"
  ] +

  # Add scheme metadata comments
  [.schemeNodes[] |
    "    %% Scheme " + .schemeID + ": " + .schemeName +
    " (" + (.schemeGroup // "unknown") + ")"
  ]
  )[]
' "$AIF_FILE"
