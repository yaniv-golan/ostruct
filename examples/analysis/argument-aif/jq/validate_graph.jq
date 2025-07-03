# jq/validate_graph.jq
# Validation utilities for graph consistency checking

# Check for node ID uniqueness
def check_node_uniqueness:
  .nodes | group_by(.id) | map(select(length > 1)) |
  if length > 0 then
    {error: "Duplicate node IDs found", duplicates: map(.[0].id)}
  else
    {status: "Node IDs are unique"}
  end;

# Check edge validity (all edges reference existing nodes)
def check_edge_validity:
  (.nodes | map(.id)) as $node_ids |
  (.edges // [] | map(select(.source as $src | .target as $tgt |
    ($node_ids | index($src) | not) or ($node_ids | index($tgt) | not)))) as $invalid_edges |
  if ($invalid_edges | length) > 0 then
    {error: "Invalid edges found", invalid_edges: $invalid_edges}
  else
    {status: "All edges are valid"}
  end;

# Detect circular references
def detect_circular_references:
  (.edges // []) as $edges |
  (.nodes | map(.id)) as $node_ids |
  # Simple cycle detection - check for immediate bidirectional edges
  ($edges | group_by(.source) | map(select(length > 1))) as $potential_cycles |
  if ($potential_cycles | length) > 0 then
    {warning: "Potential circular references detected", cycles: $potential_cycles}
  else
    {status: "No obvious circular references"}
  end;

# Find orphaned nodes (nodes with no relationships)
def find_orphaned_nodes:
  (.edges // []) as $edges |
  (.nodes | map(.id)) as $node_ids |
  ($edges | map(.source, .target) | unique) as $connected_nodes |
  ($node_ids - $connected_nodes) as $orphaned |
  if ($orphaned | length) > 0 then
    {warning: "Orphaned nodes found", orphaned_nodes: $orphaned}
  else
    {status: "All nodes are connected"}
  end;

# Main validation function
def validate_graph:
  {
    node_uniqueness: check_node_uniqueness,
    edge_validity: check_edge_validity,
    circular_references: detect_circular_references,
    orphaned_nodes: find_orphaned_nodes,
    summary: {
      total_nodes: (.nodes | length),
      total_edges: (.edges // [] | length),
      node_types: (.nodes | map(select(.type != null) | .type) | group_by(.) | map({key: .[0], value: length}) | from_entries),
      edge_types: (.edges // [] | map(select(.type != null) | .type) | group_by(.) | map({key: .[0], value: length}) | from_entries)
    }
  };

validate_graph
