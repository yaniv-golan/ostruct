# AIF Argument Graph Pipeline

A complete pipeline for converting scientific documents into richly populated AIF (Argument Interchange Format) argument graphs.

## Overview

This pipeline processes any long scientific document (Markdown, TXT, or pre-OCR-converted PDF) through 6 specialized passes to create a comprehensive argument graph with:

- Structured argument node extraction
- Relationship identification and validation
- Cross-document linking
- Consistency checking
- Semantic embedding analysis

## Quick Start

```bash
# Navigate to the AIF pipeline
cd examples/analysis/argument-aif/

# Process a document
./pipeline.sh path/to/your/document.md

# Results will be in output_<timestamp>/
```

## Pipeline Stages

1. **Outline Extraction**: Document structure analysis and sectioning
2. **Section Processing**: AIF node extraction from individual sections
3. **Graph Synthesis**: Unification of section-level extractions
4. **Global Linking**: Cross-document relationship identification
5. **Consistency Check**: Validation and quality assessment
6. **Embedding Analysis**: Semantic similarity and clustering

## Output Files

- `outline.json`: Document structure and sections
- `extract_*.json`: Per-section argument extractions
- `synthesized_graph.json`: Unified argument graph
- `linked_graph.json`: Graph with global relationships
- `final_graph.json`: Validated and consistent final graph
- `embeddings.json`: Semantic analysis results

## Requirements

- ostruct CLI tool
- jq (JSON processor)
- Standard Unix utilities (wc, split, etc.)

## Configuration

The pipeline automatically calculates processing parameters based on document size:

- Target nodes: ~3 per page + 40 base
- Chunk size: Configurable via `AIF_LINES_PER_CHUNK` environment variable
- Temperature settings optimized for each pass

### Environment Variables

- `AIF_LINES_PER_CHUNK`: Lines per chunk for fallback processing (default: 1000)
- `AIF_MIN_NODES`: Minimum nodes per section (default: 3)
- `AIF_NODES_PER_100W`: Node scaling factor per 100 words (default: 2.5)

## Resume Capability

The pipeline supports resuming from interrupted runs:

```bash
# Resume from existing output directory
./pipeline.sh document.md output_1234567890
```

The pipeline automatically detects completed passes and skips them, making debugging and re-runs efficient.

## Architecture

### Templates (`templates/`)

- `01_outline.j2`: Document structure extraction
- `02_extract_section.j2`: AIF node extraction from sections
- `03_synthesise_graph.j2`: Graph synthesis and consolidation
- `04_link_global.j2`: Cross-document relationship identification
- `05_consistency_check.j2`: Final validation and quality assessment
- `embed_cosine.j2`: Semantic embedding analysis

### Schemas (`schemas/`)

- `outline.json`: Document outline structure
- `extraction.json`: Section-level node extraction
- `rich_aif.json`: Complete argument graph format
- `embedding_pairs.json`: Embedding vectors and clustering

### Utilities (`jq/`)

- `merge_nodes.jq`: Node deduplication and merging
- `renumber_patch.jq`: Sequential ID renumbering
- `validate_graph.jq`: Graph consistency validation

## AIF Node Types

The pipeline extracts and processes these AIF node types:

- **I-nodes (Information)**: Factual claims, data, observations
- **CA-nodes (Conflict Application)**: Direct contradictions or conflicts
- **RA-nodes (Rule Application)**: Logical rules, principles, methodologies
- **MA-nodes (Multiple Application)**: Complex multi-premise arguments
- **TA-nodes (Transition Application)**: Bridging arguments, transitions
- **YA-nodes (Yet Another Application)**: Supporting evidence, examples

## Relationship Types

- **supports**: Node A provides evidence for Node B
- **attacks**: Node A contradicts or undermines Node B
- **conflicts**: Node A and Node B are mutually exclusive
- **relates**: General semantic relationship

## Quality Metrics

The pipeline provides comprehensive quality assessment:

- **Structural Validation**: Node ID uniqueness, edge validity
- **Logical Consistency**: Contradiction detection, support chain validation
- **Completeness**: Coverage analysis, orphaned node detection
- **Connectivity**: Graph connectedness, argument density

## Customization

### Modifying Templates

Templates use Jinja2 syntax and can be customized for different extraction strategies:

```jinja2
# Example: Custom node extraction criteria
{% if section_complexity > 7 %}
Aim for {{ section_complexity * 2 }} nodes in this complex section.
{% else %}
Extract 3-5 key argument nodes from this section.
{% endif %}
```

### Adjusting Schemas

Schemas follow OpenAI structured output requirements and can be extended:

```json
{
  "custom_analysis": {
    "type": "object",
    "properties": {
      "domain_specific_score": {"type": "number"}
    }
  }
}
```

### Custom Processing Logic

JQ utilities can be modified for specific processing needs:

```jq
# Example: Custom node filtering
def filter_high_confidence:
  .nodes | map(select(.confidence > 0.8));
```

## Troubleshooting

### Empty Outline

If the outline extraction fails, the pipeline automatically falls back to UTF-8 safe content chunking:

```bash
# Manual chunking parameters
export AIF_LINES_PER_CHUNK=500  # Smaller chunks for complex documents
```

### Processing Errors

Check individual pass outputs for debugging:

```bash
# Examine specific pass output
jq '.' output_*/extract_section_001.json
```

### Performance Issues

Adjust processing parameters for large documents:

```bash
# Optimize for large documents
export AIF_MIN_NODES=5
export AIF_NODES_PER_100W=1.5
```

### Memory Limitations

The pipeline handles large documents by:

- Using file-based input for large JSON data
- Externalizing embedding vectors to separate files
- Implementing streaming processing where possible

## Examples

### Basic Usage

```bash
# Process a research paper
./pipeline.sh papers/climate_change_analysis.md

# Check results
ls -la output_*/
jq '.metadata.statistics' output_*/final_graph.json
```

### Advanced Usage

```bash
# Custom processing parameters
export AIF_LINES_PER_CHUNK=2000
export AIF_MIN_NODES=8

# Process with custom settings
./pipeline.sh documents/complex_analysis.txt

# Resume if interrupted
./pipeline.sh documents/complex_analysis.txt output_1234567890
```

### Validation

```bash
# Validate graph structure
jq -f jq/validate_graph.jq output_*/final_graph.json

# Check embedding analysis
jq '.clusters | length' output_*/embeddings.json
```

## Integration

### With Visualization Tools

The output format is compatible with standard graph visualization tools:

```python
import json
import networkx as nx

# Load graph
with open('output_*/final_graph.json') as f:
    graph_data = json.load(f)

# Convert to NetworkX
G = nx.DiGraph()
for node in graph_data['nodes']:
    G.add_node(node['id'], **node)
for edge in graph_data['edges']:
    G.add_edge(edge['source'], edge['target'], **edge)
```

### With Analysis Frameworks

```python
# Example: Argument strength analysis
def analyze_argument_strength(graph_data):
    nodes = {n['id']: n for n in graph_data['nodes']}
    edges = graph_data['edges']

    for edge in edges:
        if edge['type'] == 'supports':
            strength = edge['strength'] * nodes[edge['source']]['confidence']
            print(f"Argument strength: {strength:.2f}")
```

## Performance Characteristics

- **Small documents** (1-5 pages): ~30 seconds
- **Medium documents** (5-20 pages): ~2-5 minutes
- **Large documents** (20+ pages): ~5-15 minutes

Performance scales primarily with document complexity and argument density rather than raw size.

## Contributing

To contribute improvements:

1. Test changes with existing example documents
2. Validate schema compatibility with OpenAI structured outputs
3. Ensure JQ utilities handle edge cases
4. Update documentation and examples

## License

This pipeline is part of the ostruct project and follows the same licensing terms.
