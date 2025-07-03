# Enhanced AIF: Natural Language → Rich Argument Graphs

> **Tools:** 🐍 Code Interpreter
> **Cost (approx.):** <$0.50 with gpt-4.1

## 1. Description

This example demonstrates converting natural language arguments into **enhanced AIF-compatible JSON** with F-node (formal argument scheme) support, rich metadata, and comprehensive quality validation. The enhanced AIF extends the standard Argument Interchange Format with formal argument schemes, location tracking, role assignments, and research-grade quality metrics.

## 2. Prerequisites

```bash
# No special dependencies required - uses built-in Code Interpreter
```

## 3. Quick Start

```bash
# Fast validation (no API calls)
./run.sh --test-dry-run

# Live API test (minimal cost)
./run.sh --test-live

# Full execution
./run.sh

# With custom model
./run.sh --model gpt-4o-mini
```

## 4. Files

| Path | Purpose |
|------|---------|
| `templates/main.j2` | Enhanced AIF extraction template with F-node support |
| `schemas/main.json` | Comprehensive AIF schema with metadata and schemes |
| `data/sample_argument.txt` | Sample argument for full extraction |
| `data/test_simple.txt` | Small test file for live API testing |
| `texts/*.txt` | Additional test cases (causal, authority, paradox arguments) |
| `scripts/validate_extraction.sh` | Quality validation and metrics script |
| `scripts/performance_monitor.sh` | Performance analysis and cost tracking |

## 5. Expected Output

The example generates enhanced AIF JSON with:

- **F-Node Support**: Formal argument schemes (Walton's argumentation schemes)
- **Rich Metadata**: Location tracking, roles, strength indicators
- **Advanced Relationships**: Expanded edge types (assumes, exemplifies, questions)
- **Quality Validation**: Built-in metrics and research-grade benchmarks

**Example Output Structure**:

```json
{
  "AIF": {"version": "1.0", "analyst": "AI Argument Graph Specialist"},
  "nodes": [/* I-nodes and RA-nodes with rich metadata */],
  "schemeNodes": [/* Formal argument schemes (F-nodes) */],
  "edges": [/* Advanced relationship types */],
  "locutions": [/* Source text mappings */],
  "participants": [/* Argument participants */]
}
```

## 6. Customization

- **Model Selection**: Use `--model gpt-4.1` for best performance (1M+ context)
- **Argument Types**: Test with different argument styles in `texts/` directory
- **Quality Thresholds**: Modify validation benchmarks in `scripts/validate_extraction.sh`
- **Output Format**: Results saved to `output/` directory with detailed metadata

## 7. Clean-Up

```bash
# Remove generated outputs (optional)
rm -rf output/*.json

# Clear performance logs (optional)
rm -f performance_log.txt
```

## Advanced Features

### Enhanced AIF Schema Features

**F-Node Support**: Formal argument schemes with critical questions

```json
{
  "schemeNodes": [{
    "schemeID": "S1",
    "schemeName": "Practical Reasoning",
    "description": "Arguing from goals to recommended actions",
    "criticalQuestions": ["Are there better alternatives?"]
  }]
}
```

**Rich Node Metadata**: Location tracking and semantic roles

```json
{
  "nodeID": "1",
  "category": "evidence",
  "role": "supporting_claim",
  "strength": 0.9,
  "section": "Introduction",
  "para": 2,
  "offsetStart": 45,
  "offsetEnd": 78
}
```

### Quality Validation System

The `validate_extraction.sh` script provides comprehensive metrics:

- **Scheme Coverage**: Percentage of RA/CA nodes with formal schemes
- **Location Tracking**: Metadata completeness for document structure
- **Graph Connectivity**: Detection of isolated nodes and quality issues
- **Performance Benchmarks**: Pass/fail criteria for research-grade output

### Supported Argument Types

- **Deductive**: Modus Ponens, Hypothetical Syllogism
- **Defeasible**: Authority, Analogy, Causal, Practical Reasoning
- **Inductive**: Generalization, Statistical Evidence
- **Abductive**: Best Explanation, Diagnostic Reasoning

### Model Performance

- **GPT-4.1**: Best overall (1M+ context, excellent F-node detection)
- **GPT-4o**: Strong performance for complex reasoning
- **GPT-4o-mini**: Cost-effective for simple arguments

**Quality Metrics** (tested with GPT-4.1):

- Scheme Detection: 95-100% coverage
- Metadata Completeness: 90-95%
- Graph Connectivity: 100% (no isolated nodes)
- Processing Cost: $0.18-0.42 per document
