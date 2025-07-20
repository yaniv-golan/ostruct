# Storyboard to Veo3 Pipeline

> **Tools:** ⚡ None (template-only) · 🔧 JSON Processing (jq)
> **Cost (approx.):** <$0.10 with gpt-4o-mini, <$0.50 with gpt-4

## 1. Description

Converts free-text storyboards into structured JSON prompts optimized for Google's Veo 3 video generation. The pipeline extracts reusable assets (characters, locations, props) and individual scenes, then provides tools to generate Veo3-ready JSON with inlined asset references. Perfect for consistent video generation where characters and settings need to remain uniform across scenes.

## 2. Prerequisites

```bash
# JSON processing (automatically checked by run.sh)
./scripts/ensure_jq.sh
```

## 3. Quick Start

```bash
# Fast validation (no API calls)
./run.sh --test-dry-run

# Live API test (minimal cost)
./run.sh --test-live

# Full execution with sample storyboard
./run.sh

# Process custom storyboard
./run.sh --storyboard my_story.txt

# Generate specific scene only
./run.sh --scene 3

# Custom output directory
./run.sh --output-dir my_output
```

## 4. Files

| Path | Purpose |
|------|---------|
| `templates/storyboard_to_json.j2` | Converts free-text storyboard to structured JSON with assets and scenes |
| `schemas/master.json` | Validates structured output containing assets array and scenes array |
| `scripts/split_master_json.sh` | Splits master JSON into individual asset and scene files |
| `scripts/combine_scene.sh` | Combines scenes with asset references into Veo3-ready JSON |
| `data/storyboard.txt` | Sample adventure storyboard with 8 scenes |
| `data/test_storyboard.txt` | Minimal 2-scene storyboard for testing |

## 5. Pipeline Workflow

```
Free-text storyboard → ostruct → Master JSON → Split → Veo3-ready JSON
```

1. **Input**: Natural language storyboard describing scenes, characters, and settings
2. **Structure**: AI extracts reusable assets and breaks story into ≤8 second scenes
3. **Split**: Helper scripts separate assets and scenes into modular files
4. **Combine**: Generate final JSON with asset references resolved for video generation

## 6. Expected Output

### Master JSON Structure
```json
{
  "assets": [
    {
      "id": "elena-rodriguez",
      "kind": "character",
      "name": "Dr. Elena Rodriguez",
      "description": "Marine biologist with curly brown hair and wire-rim glasses"
    }
  ],
  "scenes": [
    {
      "id": 1,
      "duration_seconds": 6,
      "text": "Dr. Elena hurries down the rain-soaked pier at dawn",
      "assets": [{"asset_id": "elena-rodriguez"}]
    }
  ]
}
```

### Veo3-Ready Output
```json
{
  "id": 1,
  "duration_seconds": 6,
  "text": "Dr. Elena hurries down the rain-soaked pier at dawn",
  "assets": [
    {
      "id": "elena-rodriguez",
      "kind": "character",
      "name": "Dr. Elena Rodriguez",
      "description": "Marine biologist with curly brown hair and wire-rim glasses"
    }
  ]
}
```

## 7. Customization

### Asset Types
Modify the schema to add new asset categories:
- Add to `kind` enum in `schemas/master.json`
- Update template instructions in `storyboard_to_json.j2`

### Scene Metadata
Add custom fields like camera angles or style notes:
```json
"metadata": {
  "camera": "handheld follow",
  "style": "cinematic",
  "lighting": "golden hour"
}
```

### Multi-format Output
Extend `combine_scene.sh` to generate different video API formats:
```bash
# Generate for different platforms
./combine_scene.sh output 1 > scene1_veo3.json
python convert_to_runway.py scene1_veo3.json > scene1_runway.json
```

## 8. Integration Examples

### With Veo 3 Flow UI
```bash
# Generate scene-by-scene
./run.sh --scene 1
# Copy output/scene_1_veo3.json content to Veo 3 interface
```

### With Vertex AI API
```python
import json

# Load generated JSON
with open('output/scene_001_veo3.json') as f:
    veo_prompt = json.load(f)

# Submit to Vertex AI Video Generation
video_response = vertex_client.generate_video(
    prompt=veo_prompt['text'],
    duration=veo_prompt['duration_seconds']
)
```

### Batch Processing
```bash
# Process multiple storyboards
for story in stories/*.txt; do
    ./run.sh --storyboard "$story" --output-dir "output/$(basename "$story" .txt)"
done
```

## 9. Clean-Up

```bash
# Remove generated files
rm -rf output/
```

Generated files are safely contained in the `output/` directory and can be removed entirely.
