#!/usr/bin/env bash
# json_to_yaml.sh - Convert JSON files to YAML format
# Usage: json_to_yaml.sh INPUT_JSON OUTPUT_YAML

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 INPUT_JSON OUTPUT_YAML" >&2
    echo "  INPUT_JSON:  Input JSON file path" >&2
    echo "  OUTPUT_YAML: Output YAML file path" >&2
    exit 1
fi

input_json="$1"
output_yaml="$2"

# Check if input file exists
if [[ ! -f "$input_json" ]]; then
    echo "❌ Error: Input JSON file not found: $input_json" >&2
    exit 1
fi

# Check if yq is available
if ! command -v yq &> /dev/null; then
    echo "❌ Error: yq is not installed. Please install yq to convert JSON to YAML." >&2
    echo "   Install with: sudo apt-get install yq" >&2
    exit 1
fi

# Convert JSON to YAML
echo "🔄 Converting $input_json to $output_yaml..." >&2
yq eval '.' "$input_json" --output-format=yaml > "$output_yaml"
echo "✅ YAML file created: $output_yaml" >&2