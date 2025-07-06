# jq/merge_nodes.jq
# Merge multiple node arrays into a single deduplicated array

def merge_nodes:
  # Flatten all node arrays
  [.[] | .nodes // []] | flatten |
  # Group by node ID
  group_by(.id) |
  # Merge duplicate nodes, keeping latest data
  map(reduce .[] as $item ({}; . * $item)) |
  # Sort by ID for consistency
  sort_by(.id);

# Main processing
{
  "nodes": merge_nodes,
  "metadata": {
    "merged_at": now | todate,
    "total_nodes": (merge_nodes | length)
  }
}
