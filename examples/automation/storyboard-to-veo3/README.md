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

## 7. Improving Output Quality

### Iterative Asset Refinement Workflow

If needed, asset descriptions can be refined after the initial run:

```bash
# 1. Generate initial structure
./run.sh

# 2. Review generated assets
ls output/assets/                    # See all extracted assets
cat output/assets/character_*.json   # Review character descriptions

# 3. Edit asset descriptions for better video results
nano output/assets/character_elena-rodriguez.json

# 4. Regenerate scenes with improved assets
./scripts/combine_scene.sh output 1  # Scene 1 with updated assets
./scripts/combine_scene.sh output 2  # Scene 2 with updated assets

# 5. Repeat until satisfied with asset quality
```

### Asset Description Best Practices

**Characters - Be Specific:**
```json
// ❌ Generic (poor video results)
{
  "description": "A scientist"
}

// ✅ Detailed (better video results)
{
  "description": "Dr. Elena Rodriguez, 35, marine biologist with shoulder-length curly brown hair, wire-rim glasses, olive skin, wearing a weathered navy field jacket over khaki pants, confident posture"
}
```

**Locations - Add Atmosphere:**
```json
// ❌ Basic
{
  "description": "A pier"
}

// ✅ Cinematic
{
  "description": "Weathered wooden pier extending into gray ocean waters at dawn, rain-slicked planks reflecting pale yellow streetlights, fog rolling in from the horizon, seagulls calling in the distance"
}
```

**Props - Include Context:**
```json
// ❌ Minimal
{
  "description": "A boat"
}

// ✅ Contextual
{
  "description": "Small white research vessel 'Nereid' with blue hull stripe, diving equipment on deck, GPS antenna, anchored 50 meters from shore, gently rocking in choppy waters"
}
```

### Advanced Customization

#### Adding New Asset Types
Modify the schema to support additional categories:
```bash
# Edit schema
nano schemas/master.json  # Add to "kind" enum: "vehicle", "weapon", "costume"

# Update template
nano templates/storyboard_to_json.j2  # Add instructions for new types
```

#### Scene Metadata
Enhance scenes with video generation hints:
```json
{
  "id": 1,
  "text": "Dr. Elena hurries down the pier",
  "metadata": {
    "camera": "handheld follow shot",
    "style": "cinematic thriller",
    "lighting": "golden hour",
    "mood": "urgent"
  }
}
```

#### Multi-format Output
Generate for different video platforms:
```bash
# Veo 3 format (default)
./scripts/combine_scene.sh output 1 > scene1_veo3.json

# Convert to other formats (requires custom scripts)
python scripts/convert_to_runway.py scene1_veo3.json
python scripts/convert_to_pika.py scene1_veo3.json
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
