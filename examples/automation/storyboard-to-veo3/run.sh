#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

# Example-specific configuration
REQUIRES_JQ=true
REQUIRES_GUM=true

# Define run_ostruct function before importing standard runner
run_ostruct() {
    local model="${MODEL:-gpt-4.1}"
    local dry_flag="${DRY:-}"
    ostruct run "$@" -m "$model" $dry_flag
}

# Import standard example runner
source "$ROOT/scripts/examples/standard_runner.sh"

# Default values for custom arguments
STORYBOARD_FILE=""
OUTPUT_DIR="output"
SCENE_NUMBER=""

# Parse custom arguments
parse_args_with_getoptions "$@" <<'EOF'
  param   STORYBOARD_FILE --storyboard FILE      -- "Storyboard file to process (default: data/storyboard.txt)"
  param   OUTPUT_DIR      --output-dir DIR       -- "Output directory for generated files (default: output)"
  param   SCENE_NUMBER    --scene N              -- "Process specific scene number only"
EOF

# Set defaults based on mode if not provided
if [[ -z "$STORYBOARD_FILE" ]]; then
    case "$MODE" in
        "test-"*)
            STORYBOARD_FILE="data/test_storyboard.txt"
            ;;
        *)
            STORYBOARD_FILE="data/storyboard.txt"
            ;;
    esac
fi

if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="output"
fi

# Validate storyboard file exists
if [[ ! -f "$STORYBOARD_FILE" ]]; then
    echo "❌ Error: Storyboard file not found: $STORYBOARD_FILE" >&2
    echo "Available files:" >&2
    ls -la data/*.txt 2>/dev/null || echo "No .txt files found in data/" >&2
    exit 1
fi

# Helper functions
generate_master_json() {
    gum style --foreground 212 "🎭 Generating structured JSON from storyboard..."
    gum style --foreground 244 "   🤖 Processing with AI (this may take a moment)..."
    run_ostruct templates/storyboard_to_json.j2 schemas/master.json \
        --file storyboard "$STORYBOARD_FILE" \
        --output-file "$OUTPUT_DIR/master.json" \
        --progress none
    gum style --foreground 46 "✅ Master JSON created: $OUTPUT_DIR/master.json"
}

split_master_json() {
    gum style --foreground 212 "📁 Splitting master JSON into modular files..."
    bash scripts/split_master_json.sh "$OUTPUT_DIR/master.json" "$OUTPUT_DIR"
    gum style --foreground 46 "✅ Files split into $OUTPUT_DIR/assets/ and $OUTPUT_DIR/scenes/"
}

combine_scenes() {
    gum style --foreground 212 "🔗 Generating Veo3-ready JSON..."
    if [[ -n "$SCENE_NUMBER" ]]; then
        gum style --foreground 220 "Processing scene $SCENE_NUMBER only..."
        bash scripts/combine_scene.sh "$OUTPUT_DIR" "$SCENE_NUMBER" > "$OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.json"
        gum style --foreground 46 "✅ Veo3-ready JSON created: $OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.json"
    else
        gum style --foreground 220 "Processing all scenes..."
        bash scripts/combine_scene.sh "$OUTPUT_DIR" > "$OUTPUT_DIR/all_scenes_veo3.json"
        gum style --foreground 46 "✅ Veo3-ready JSON created: $OUTPUT_DIR/all_scenes_veo3.json"
    fi
}

generate_yaml_files() {
    gum style --foreground 212 "🔄 Generating corresponding YAML files..."
    
    # Check if yq is available
    if ! command -v yq &> /dev/null; then
        gum style --foreground 220 "⚠️ yq not found - skipping YAML generation"
        gum style --foreground 244 "   Install yq to enable YAML output: sudo apt-get install yq"
        return 0
    fi
    
    # Convert Veo3-ready JSON files to YAML
    if [[ -n "$SCENE_NUMBER" && -f "$OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.json" ]]; then
        bash scripts/json_to_yaml.sh "$OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.json" "$OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.yaml"
    fi
    
    if [[ -f "$OUTPUT_DIR/all_scenes_veo3.json" ]]; then
        bash scripts/json_to_yaml.sh "$OUTPUT_DIR/all_scenes_veo3.json" "$OUTPUT_DIR/all_scenes_veo3.yaml"
    fi
    
    # Convert individual scene files to YAML
    if [[ -d "$OUTPUT_DIR/scenes" ]]; then
        for scene_file in "$OUTPUT_DIR/scenes"/scene_*.json; do
            if [[ -f "$scene_file" ]]; then
                yaml_file="${scene_file%.json}.yaml"
                bash scripts/json_to_yaml.sh "$scene_file" "$yaml_file" 2>/dev/null || true
            fi
        done
    fi
    
    # Convert asset files to YAML
    if [[ -d "$OUTPUT_DIR/assets" ]]; then
        for asset_file in "$OUTPUT_DIR/assets"/*.json; do
            if [[ -f "$asset_file" ]]; then
                yaml_file="${asset_file%.json}.yaml"
                bash scripts/json_to_yaml.sh "$asset_file" "$yaml_file" 2>/dev/null || true
            fi
        done
    fi
    
    # Convert master.json to YAML
    if [[ -f "$OUTPUT_DIR/master.json" ]]; then
        bash scripts/json_to_yaml.sh "$OUTPUT_DIR/master.json" "$OUTPUT_DIR/master.yaml" 2>/dev/null || true
    fi
    
    gum style --foreground 46 "✅ YAML files generated successfully"
}

generate_html_viewer() {
    gum style --foreground 212 "🌐 Generating interactive HTML viewer..."

    local html_file="$OUTPUT_DIR/viewer.html"
    cat > "$html_file" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Storyboard to Veo3 - Interactive Viewer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section-title {
            font-size: 1.8em;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #4facfe;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .scene-list {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #4facfe;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        .scene-card {
            border-left-color: #e74c3c;
        }
        .asset-card {
            border-left-color: #27ae60;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .card-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #2c3e50;
            margin: 0;
        }
        .copy-btn {
            background: #4facfe;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: background 0.2s;
        }
        .copy-btn:hover {
            background: #3b8bfe;
        }
        .copy-btn:active {
            background: #2a7cfe;
        }
        .copy-btn.copied {
            background: #27ae60 !important;
        }
        .json-content {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
            line-height: 1.4;
            overflow-x: auto;
            white-space: pre;
            margin: 10px 0;
        }
        .duration {
            background: #e74c3c;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .kind {
            background: #27ae60;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .text {
            margin: 15px 0;
            padding: 15px;
            background: white;
            border-radius: 6px;
            font-size: 1.1em;
            line-height: 1.8;
            border: 1px solid #dee2e6;
        }
        .metadata {
            margin-top: 15px;
            padding: 12px;
            background: rgba(79, 172, 254, 0.1);
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        .assets-list {
            margin: 15px 0;
        }
        .asset-ref {
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 2px;
            font-size: 0.8em;
            text-decoration: none;
        }
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #27ae60;
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            font-weight: 500;
            opacity: 0;
            transform: translateY(-20px);
            transition: all 0.3s;
            z-index: 1000;
        }
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        .description {
            margin: 10px 0;
            color: #555;
            line-height: 1.6;
        }
        .traits {
            margin: 10px 0;
            font-style: italic;
            color: #666;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .summary-number {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .summary-label {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .format-toggle {
            margin-top: 20px;
            display: flex;
            justify-content: center;
            gap: 0;
            border-radius: 8px;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.2);
            padding: 4px;
        }
        .toggle-btn {
            background: transparent;
            color: white;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            transition: all 0.3s;
            border-radius: 4px;
        }
        .toggle-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        .toggle-btn.active {
            background: rgba(255, 255, 255, 0.3);
            font-weight: 600;
        }
        .format-content {
            display: none;
        }
        .format-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Storyboard to Veo3</h1>
            <p>Interactive Viewer - Ready for Video Generation</p>
            <div class="format-toggle">
                <button id="jsonBtn" class="toggle-btn active" onclick="switchFormat('json')">JSON</button>
                <button id="yamlBtn" class="toggle-btn" onclick="switchFormat('yaml')">YAML</button>
            </div>
        </div>

        <div class="content">
            <div id="summary" class="summary">
                <!-- Summary will be populated by JavaScript -->
            </div>

            <div class="section">
                <h2 class="section-title">
                    🎞️ Scenes
                </h2>
                <div id="scenes" class="scene-list">
                    <!-- Scenes will be populated by JavaScript -->
                </div>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        // Data will be inserted here by the shell script
        const jsonData = JSON_DATA_PLACEHOLDER;
        const yamlData = YAML_DATA_PLACEHOLDER;
        let currentFormat = 'json';
        let currentData = jsonData;

        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2000);
        }

        function switchFormat(format) {
            currentFormat = format;
            currentData = format === 'json' ? jsonData : yamlData;
            
            // Update button states
            document.getElementById('jsonBtn').classList.toggle('active', format === 'json');
            document.getElementById('yamlBtn').classList.toggle('active', format === 'yaml');
            
            // Re-render content
            renderScenes();
        }

        function copyToClipboard(text, button) {
            navigator.clipboard.writeText(text).then(() => {
                showToast('✅ Copied to clipboard!');
                const originalText = button.textContent;
                button.textContent = '✅ Copied!';
                button.classList.add('copied');
                setTimeout(() => {
                    button.textContent = originalText;
                    button.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                showToast('❌ Failed to copy');
                console.error('Failed to copy: ', err);
            });
        }

        function renderSummary() {
            const summaryDiv = document.getElementById('summary');
            const sceneCount = jsonData.length;
            const totalDuration = jsonData.reduce((sum, scene) => sum + scene.duration_seconds, 0);

            summaryDiv.innerHTML = `
                <div class="summary-card">
                    <div class="summary-number">${sceneCount}</div>
                    <div class="summary-label">Scenes Ready for Veo3</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">${totalDuration}s</div>
                    <div class="summary-label">Total Duration</div>
                </div>
            `;
        }

        function renderScenes() {
            const scenesDiv = document.getElementById('scenes');
            scenesDiv.innerHTML = jsonData.map((scene, index) => {
                const sceneContent = currentFormat === 'json' 
                    ? JSON.stringify(scene, null, 2)
                    : currentData[index] || 'YAML not available';
                const copyButtonText = currentFormat === 'json' ? '📋 Copy JSON' : '📋 Copy YAML';
                
                return `
                    <div class="card scene-card">
                        <div class="card-header">
                            <h3 class="card-title">Scene ${scene.id} (${scene.duration_seconds}s)</h3>
                            <button class="copy-btn" onclick="copySceneContent(${index})">
                                ${copyButtonText}
                            </button>
                        </div>
                        <div class="json-content">${sceneContent}</div>
                    </div>
                `;
            }).join('');
        }

        function copySceneContent(index) {
            const scene = jsonData[index];
            const content = currentFormat === 'json' 
                ? JSON.stringify(scene, null, 2)
                : currentData[index] || 'YAML not available';
            const button = event.target;
            copyToClipboard(content, button);
        }

        // Initialize the page
        renderSummary();
        renderScenes();
    </script>
</body>
</html>
EOF

    # Insert the actual data using a simpler approach
    if [[ -f "$OUTPUT_DIR/all_scenes_veo3.json" ]]; then
        # Convert the newline-separated JSON objects into a proper JSON array
        local json_scenes_data
        json_scenes_data=$(jq -s '.' "$OUTPUT_DIR/all_scenes_veo3.json")
        
        # Prepare YAML data array (individual YAML strings)
        local yaml_scenes_data="[]"
        if [[ -f "$OUTPUT_DIR/all_scenes_veo3.yaml" ]]; then
            # Convert JSON scenes to individual YAML strings for display
            yaml_scenes_data=$(python3 -c "
import json
import sys
try:
    import yaml
    # Read the JSON data and convert each scene to YAML string
    json_data = $json_scenes_data
    yaml_strings = []
    for scene in json_data:
        yaml_str = yaml.dump(scene, default_flow_style=False, allow_unicode=True)
        yaml_strings.append(yaml_str.strip())
    print(json.dumps(yaml_strings))
except ImportError:
    # yaml not available, return empty array
    print('[]')
except Exception as e:
    print('[]')
")
        fi
        
        # Replace the placeholders using string replacement
        python3 -c "
import sys
content = open('$html_file', 'r').read()
json_data = '''$json_scenes_data'''
yaml_data = '''$yaml_scenes_data'''
new_content = content.replace('JSON_DATA_PLACEHOLDER', json_data)
new_content = new_content.replace('YAML_DATA_PLACEHOLDER', yaml_data)
open('$html_file', 'w').write(new_content)
"
    else
        # Fallback to empty arrays
        python3 -c "
import sys
content = open('$html_file', 'r').read()
new_content = content.replace('JSON_DATA_PLACEHOLDER', '[]')
new_content = new_content.replace('YAML_DATA_PLACEHOLDER', '[]')
open('$html_file', 'w').write(new_content)
"
    fi

    gum style --foreground 46 "✅ Interactive HTML viewer created: $html_file"
    gum style --foreground 244 "   Open in browser to view scenes and copy to Veo3"
}

show_results() {
    gum style --margin "1 0" --foreground 255 "📋 Generated Files:"

    if [[ -f "$OUTPUT_DIR/master.json" ]]; then
        asset_count=$(jq '.assets | length' "$OUTPUT_DIR/master.json" 2>/dev/null || echo "0")
        scene_count=$(jq '.scenes | length' "$OUTPUT_DIR/master.json" 2>/dev/null || echo "0")
        gum style --foreground 244 "  🎬 Master JSON: $OUTPUT_DIR/master.json"
        gum style --foreground 244 "    📊 Contains: $asset_count assets, $scene_count scenes"
    fi

    if [[ -d "$OUTPUT_DIR/assets" ]]; then
        asset_file_count=$(ls -1 "$OUTPUT_DIR/assets"/*.json 2>/dev/null | wc -l || echo "0")
        gum style --foreground 244 "  🎭 Asset files: $OUTPUT_DIR/assets/ ($asset_file_count files)"
    fi

    if [[ -d "$OUTPUT_DIR/scenes" ]]; then
        scene_file_count=$(ls -1 "$OUTPUT_DIR/scenes"/*.json 2>/dev/null | wc -l || echo "0")
        gum style --foreground 244 "  🎞️ Scene files: $OUTPUT_DIR/scenes/ ($scene_file_count files)"
    fi

    if [[ -f "$OUTPUT_DIR/all_scenes_veo3.json" ]]; then
        gum style --foreground 244 "  🚀 Veo3-ready JSON: $OUTPUT_DIR/all_scenes_veo3.json"
    fi

    if [[ -f "$OUTPUT_DIR/all_scenes_veo3.yaml" ]]; then
        gum style --foreground 244 "  🚀 Veo3-ready YAML: $OUTPUT_DIR/all_scenes_veo3.yaml"
    fi

    if [[ -f "$OUTPUT_DIR/viewer.html" ]]; then
        gum style --foreground 33 "  🌐 Interactive viewer: $OUTPUT_DIR/viewer.html"
    fi

    if [[ -n "$SCENE_NUMBER" && -f "$OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.json" ]]; then
        gum style --foreground 244 "  🚀 Veo3-ready scene: $OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.json"
    fi

    if [[ -n "$SCENE_NUMBER" && -f "$OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.yaml" ]]; then
        gum style --foreground 244 "  🚀 Veo3-ready scene: $OUTPUT_DIR/scene_${SCENE_NUMBER}_veo3.yaml"
    fi

    gum style --margin "1 0" --foreground 220 "💡 Next steps:"
    gum style --foreground 244 "   • Open $OUTPUT_DIR/viewer.html in your browser"
    gum style --foreground 244 "   • Use copy buttons to paste scenes into Veo3"
    gum style --foreground 244 "   • Or use the JSON files with video generation APIs"
}

# Main execution modes
case "$MODE" in
    "test-dry")
        gum style --foreground 212 "🧪 Running dry-run validation..."
        gum style --foreground 220 "📄 Validating template and schema..."
        gum style --foreground 244 "   🤖 Validating with AI (this may take a moment)..."
        run_ostruct templates/storyboard_to_json.j2 schemas/master.json \
            --file storyboard "$STORYBOARD_FILE" \
            --dry-run \
            --progress none
        gum style --foreground 46 "✅ Dry-run validation passed"
        ;;

    "test-live")
        gum style --foreground 212 "🧪 Running live API test with minimal data..."
        mkdir -p "$OUTPUT_DIR"
        generate_master_json
        gum style --foreground 46 "✅ Live API test passed - basic JSON generation works"
        ;;

    "full")
        gum style --border normal --margin "1 2" --padding "1 2" \
            --border-foreground 212 --foreground 255 \
            "🚀 Running complete storyboard-to-Veo3 pipeline with OSTRUCT..."
        gum style --foreground 244 "📖 Input: $STORYBOARD_FILE"
        gum style --foreground 244 "📁 Output: $OUTPUT_DIR"

        # Create output directory
        mkdir -p "$OUTPUT_DIR"

        # Execute full pipeline
        generate_master_json
        split_master_json
        combine_scenes
        generate_yaml_files
        generate_html_viewer
        show_results

        gum style --border thick --margin "1 2" --padding "1 2" \
            --border-foreground 46 --foreground 46 \
            "✅ Pipeline completed successfully!"
        ;;
esac
