# Natural Language → AIF (Argument Interchange Format)

This example demonstrates converting natural language arguments into **AIFdb-compatible JSON** format.

## What is AIF?

The **Argument Interchange Format (AIF)** is a standard for representing argument structures in a machine-readable format. It consists of:

- **Nodes**: Information (I), Rule Application (RA), Conflict Application (CA), Preference Application (PA)
- **Edges**: Directed connections between nodes
- **AIFdb Format**: A specific JSON schema used by AIF tools and applications

## Key Features

✅ **AIFdb Compatible**: Generates JSON that follows AIFdb standards
✅ **AIF Extensions**: Enhanced visualization attributes while maintaining full compatibility
✅ **OpenAI Structured Output**: Uses simplified schema for reliable generation
✅ **Real Text Extraction**: Extracts actual claims from input text, not placeholders
✅ **Visual Diagrams**: Color-coded Mermaid diagrams with automatic SVG generation
✅ **Multiple Output Formats**: Console display, JSON files, and visual diagrams

## Files

- `prompt.j2` - Jinja2 template for AIF graph extraction with AIFdb specification and AIF extensions
- `schema.json` - JSON Schema for AIFdb-compatible format with AIF visualization extensions
- `texts/` - Sample argumentative texts for analysis
- `scripts/` - Visualization and utility scripts
  - `run_with_visualization.sh` - Generate AIF JSON + Mermaid diagram + SVG
  - `aif2mermaid.sh` - Convert AIF JSON to color-coded Mermaid diagram with extension support
- `output/` - Generated files (AIF JSON, Mermaid diagrams, SVG images)
- `Makefile` - Convenience commands for running examples
- `AIF_EXTENSIONS.md` - Documentation for AIF visualization extensions

## Usage

### Basic Usage

```bash
# Generate AIF analysis with color-coded Mermaid visualization (default: Paradox of the Court)
make run

# Generate AIF analysis with visualization for specific text
make run TEXT=aint_i_a_woman_by.txt

# Console output only (original behavior)
make console

# Generate AIF + Mermaid + SVG for all texts
make generate-all

# Generate AIF file only (no visualization)
make generate

# Generate AIF files only for all texts (no visualization)
make generate-all-json
```

### Direct ostruct Usage

```bash
# Console output
ostruct run prompt.j2 schema.json --file argument_text texts/paradox_of_the_court.txt

# Save to file
ostruct run prompt.j2 schema.json --file argument_text texts/paradox_of_the_court.txt --output-file output/paradox_of_the_court.aif.json

# Generate with visualization
./scripts/run_with_visualization.sh texts/paradox_of_the_court.txt
```

### Available Texts

- **paradox_of_the_court.txt** - Classic logical paradox by Protagoras and Euathlus
- **aint_i_a_woman_by.txt** - Sojourner Truth's famous speech (1851)
- **yes_virgina_there_is_a_santa_claus.txt** - Francis Pharcellus Church's editorial (1897)
- **a_letter_to_a_royal_academy_about_farting.txt** - Benjamin Franklin's satirical essay (1781)

## Visualization Features

### Enhanced Visual Features

#### Color-Coded Node Types

The Mermaid diagrams use distinct colors and icons for different AIF node types and semantic categories:

**Core AIF Types:**

- 💬 **Information nodes (I)**: Blue - Contains claims, premises, and conclusions
- ✅ **Rule Application nodes (RA)**: Green - Represents inference rules and logical connections
- ⚔️ **Conflict Application nodes (CA)**: Pink - Shows contradictions and conflicts
- ⭐ **Preference Application nodes (PA)**: Orange - Indicates preferences between arguments
- 🔗 **Meta-Argument nodes (MA)**: Purple - Arguments about arguments

**AIF Extension Categories:**

- 💬 **Premise nodes**: Light blue - Supporting evidence and premises
- 💬 **Evidence nodes**: Light green - Factual evidence and data
- 🎯 **Conclusion nodes**: Dark green - Final conclusions and outcomes
- ⚔️ **Conflict nodes**: Pink - Conflicting information and contradictions

#### Smart Edge Styling & Labels

Edges are automatically color-coded and labeled based on the relationship type:

- `-.->|"supports"|` - **Dotted lines**: Information supporting reasoning nodes
- `==>|"infers"|` - **Thick arrows**: Reasoning nodes inferring conclusions
- `-.->|"conflicts"|` - **Dotted lines**: Information creating conflicts
- `==>|"attacks"|` - **Thick arrows**: Conflicts attacking claims
- `-->|"relates"|` - **Solid lines**: General relationships between information

#### Compact Design with AIF Extensions

- **Smaller fonts (11px)** for better space utilization
- **Smart text display**: Uses `displayName` from AIF extensions (max 60 chars) or truncated text
- **Semantic edge labels** that explain the relationship type
- **Enhanced categorization**: Uses AIF extension categories for more precise styling

### Output Files

When using visualization mode, the following files are generated in `output/`:

- `{text_name}.aif.json` - AIFdb-compatible JSON structure
- `{text_name}.mmd` - Mermaid diagram source code
- `{text_name}.svg` - Rendered SVG diagram (if Mermaid CLI available)

### Dependencies

The visualization scripts automatically install required dependencies:

- **jq** - JSON processing (via `scripts/install/dependencies/ensure_jq.sh`)
- **Mermaid CLI** - Diagram rendering (via `scripts/install/dependencies/ensure_mermaid.sh`)

If automatic installation fails, manual installation instructions are provided.

## Technical Implementation

### Schema Requirements

The schema follows OpenAI's structured output requirements:

- All properties must be in `required` arrays
- No advanced JSON Schema features (`oneOf`, `anyOf`, `$ref`, etc.)
- Simple type definitions only
- No optional fields (use empty strings instead)

### Output Format

Generated JSON includes core AIF structure with optional visualization extensions:

```json
{
  "AIF": {
    "version": "1.0",
    "analyst": "AI Assistant",
    "created": "2024-01-01T00:00:00Z",
    "extensions": ["visualization-v1.0"]
  },
  "nodes": [
    {
      "nodeID": "1",
      "text": "Full argument text...",
      "type": "I",
      "timestamp": "2024-01-01T00:00:00Z",
      "displayName": "Short display text",
      "category": "premise",
      "strength": 0.9
    }
  ],
  "edges": [
    {
      "edgeID": "1",
      "fromID": "1",
      "toID": "2",
      "formEdgeID": "",
      "relationshipType": "supports"
    }
  ],
  "locutions": [],
  "participants": []
}
```

See `AIF_EXTENSIONS.md` for complete documentation of the extension attributes.

## Example Output

The Paradox of the Court generates an argument graph showing:

- **Protagoras' Argument**: Euathlus must pay regardless of case outcome
- **Euathlus' Counter-Argument**: He owes nothing regardless of case outcome
- **Conflict Node**: Representing the logical contradiction between both arguments

This demonstrates how AIF can represent complex argumentative structures with competing reasoning patterns.
