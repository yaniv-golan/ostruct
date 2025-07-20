#!/usr/bin/env bash
# split_master_json.sh - Split master JSON into individual asset and scene files
# Usage: split_master_json.sh MASTER_JSON OUTPUT_DIR

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 MASTER_JSON OUTPUT_DIR" >&2
    echo "Example: $0 output/master.json output" >&2
    exit 1
fi

master="$1"
output_dir="$2"

# Validate input file exists
if [[ ! -f "$master" ]]; then
    echo "❌ Error: Master JSON file not found: $master" >&2
    exit 1
fi

# Validate JSON structure
if ! jq empty "$master" 2>/dev/null; then
    echo "❌ Error: Invalid JSON in master file: $master" >&2
    exit 1
fi

# Create output directories
mkdir -p "$output_dir/assets" "$output_dir/scenes"
echo "📁 Created output directories in $output_dir"

# Extract and save assets
echo "🎭 Processing assets..."
asset_count=0
if jq -e '.assets | length > 0' "$master" > /dev/null; then
    while IFS= read -r asset; do
        asset_id=$(echo "$asset" | jq -r '.id')
        if [[ -z "$asset_id" || "$asset_id" == "null" ]]; then
            echo "⚠️ Warning: Asset missing ID, skipping" >&2
            continue
        fi

        # Validate asset_id is safe for filename
        if [[ ! "$asset_id" =~ ^[a-z0-9-]+$ ]]; then
            echo "❌ Error: Invalid asset ID '$asset_id' - must be kebab-case" >&2
            exit 1
        fi

        echo "$asset" | jq '.' > "$output_dir/assets/${asset_id}.json"
        echo "  📄 Created $asset_id.json"
        asset_count=$((asset_count + 1))
    done < <(jq -c '.assets[]' "$master")
else
    echo "⚠️ No assets found in master JSON"
fi

# Extract and save scenes
echo "🎬 Processing scenes..."
scene_count=0
if jq -e '.scenes | length > 0' "$master" > /dev/null; then
    while IFS= read -r scene; do
        scene_id=$(echo "$scene" | jq -r '.id')
        if [[ -z "$scene_id" || "$scene_id" == "null" ]]; then
            echo "⚠️ Warning: Scene missing ID, skipping" >&2
            continue
        fi

        # Validate scene_id is numeric
        if [[ ! "$scene_id" =~ ^[0-9]+$ ]]; then
            echo "❌ Error: Scene ID must be numeric, got: $scene_id" >&2
            exit 1
        fi

        # Zero-pad scene number for proper sorting
        printf -v padded_id "%03d" "$scene_id"
        echo "$scene" | jq '.' | sed 's/"dollar_ref"/"$ref"/g' > "$output_dir/scenes/scene_${padded_id}.json"
        echo "  🎞️ Created scene_${padded_id}.json"
        scene_count=$((scene_count + 1))
    done < <(jq -c '.scenes[]' "$master")
else
    echo "⚠️ No scenes found in master JSON"
fi

echo "✅ Split complete: $asset_count assets, $scene_count scenes"
