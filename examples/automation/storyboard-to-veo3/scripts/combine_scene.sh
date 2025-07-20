#!/usr/bin/env bash
# combine_scene.sh - Combine scene with referenced assets into Veo3-ready JSON
# Usage: combine_scene.sh OUTPUT_DIR [SCENE_ID]

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 OUTPUT_DIR [SCENE_ID]" >&2
    echo "  OUTPUT_DIR: Directory containing assets/ and scenes/ subdirectories" >&2
    echo "  SCENE_ID:   Optional scene number (if omitted, processes all scenes)" >&2
    echo "Examples:" >&2
    echo "  $0 output        # Process all scenes" >&2
    echo "  $0 output 2      # Process only scene 2" >&2
    exit 1
fi

output_dir="$1"
specific_scene="${2:-}"

assets_dir="$output_dir/assets"
scenes_dir="$output_dir/scenes"

# Validate directory structure
if [[ ! -d "$assets_dir" ]]; then
    echo "❌ Error: Assets directory not found: $assets_dir" >&2
    exit 1
fi

if [[ ! -d "$scenes_dir" ]]; then
    echo "❌ Error: Scenes directory not found: $scenes_dir" >&2
    exit 1
fi

# Function to combine a single scene with its assets
combine_single_scene() {
    local scene_file="$1"
    local scene_basename
    scene_basename=$(basename "$scene_file")

    if [[ ! -f "$scene_file" ]]; then
        echo "❌ Error: Scene file not found: $scene_file" >&2
        return 1
    fi

    echo "🔗 Processing $scene_basename..." >&2

    # Extract asset references from scene
    if ! jq -e '.assets' "$scene_file" > /dev/null 2>&1; then
        echo "⚠️ Warning: No assets array found in $scene_basename" >&2
        jq '.' "$scene_file"
        return 0
    fi

    # Get list of asset files referenced by this scene (look for $ref format)
    local asset_refs
    asset_refs=($(jq -r '.assets[]."$ref" // empty' "$scene_file" 2>/dev/null))

    if [[ ${#asset_refs[@]} -eq 0 ]]; then
        echo "⚠️ Warning: No valid asset references found in $scene_basename" >&2
        jq '.' "$scene_file"
        return 0
    fi

    # Build array of asset file paths
    local asset_files=()
    for asset_ref in "${asset_refs[@]}"; do
        local asset_file="$assets_dir/${asset_ref}"
        if [[ ! -f "$asset_file" ]]; then
            echo "❌ Error: Referenced asset file not found: $asset_file" >&2
            return 1
        fi
        asset_files+=("$asset_file")
    done

    # Combine scene with resolved assets using jq, then convert dollar_ref to $ref
    # Strategy: Start with scene, then add resolved assets array
    if [[ ${#asset_files[@]} -gt 0 ]]; then
        # Use jq to merge scene with assets
        # First argument is the scene, remaining are asset files
        jq -s '
            .[0] as $scene |
            .[1:] as $assets |
            $scene | .assets = $assets
        ' "$scene_file" "${asset_files[@]}" | sed 's/"dollar_ref"/"$ref"/g'
    else
        # No assets to merge, just return scene with dollar_ref converted
        jq '.' "$scene_file" | sed 's/"dollar_ref"/"$ref"/g'
    fi
}

# Main execution logic
if [[ -n "$specific_scene" ]]; then
    # Process single scene
    printf -v padded_scene "%03d" "$specific_scene"
    scene_file="$scenes_dir/scene_${padded_scene}.json"
    combine_single_scene "$scene_file"
else
    # Process all scenes
    echo "🎬 Processing all scenes in $scenes_dir" >&2
    for scene_file in "$scenes_dir"/scene_*.json; do
        if [[ ! -f "$scene_file" ]]; then
            echo "⚠️ No scene files found in $scenes_dir" >&2
            exit 1
        fi

        combine_single_scene "$scene_file"
        echo  # Add blank line between scenes for readability
    done
fi
