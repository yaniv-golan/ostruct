# jq/renumber_patch.jq
# Renumber node IDs to ensure sequential numbering

def renumber_nodes:
  . as $input |
  # Create ID mapping
  (.nodes | to_entries | map({key: .value.id, value: (.key + 1 | tostring)})) as $id_map |
  # Apply renumbering
  {
    "nodes": (.nodes | map(.id = ($id_map | from_entries)[.id])),
    "edges": (.edges // [] | map(
      .source = ($id_map | from_entries)[.source] |
      .target = ($id_map | from_entries)[.target]
    ))
  };

renumber_nodes
