# Enhanced AIF with F-Node Support

This example implements a **rich, AIF-inspired argument graph extraction system** that captures formal argument schemes (F-nodes), enhanced metadata, and advanced argumentative structures while maintaining compatibility with standard AIF viewers.

## What is Enhanced AIF?

Enhanced AIF extends the core Argument Interchange Format (AIF) specification with:

1. **F-Node Support**: Formal argument schemes (schemeNodes array)
2. **Rich Metadata**: Location tracking, roles, strength indicators
3. **Advanced Relationships**: Expanded edge types for nuanced argument analysis
4. **Participant Modeling**: Enhanced locutions and participant structures
5. **Quality Validation**: Built-in metrics for extraction assessment

## Schema Enhancements

### 1. Scheme Nodes (F-Nodes)

**schemeNodes** array - Formal argument schemes

```json
{
  "schemeNodes": [
    {
      "schemeID": "S1",
      "schemeName": "Argument from Authority",
      "schemeGroup": "defeasible",
      "description": "Argument based on expert testimony",
      "criticalQuestions": [
        "Is the authority a legitimate expert?",
        "Is there agreement among experts?"
      ]
    }
  ]
}
```

**Supported Scheme Types**:

- **Deductive**: Modus Ponens, Modus Tollens, Hypothetical Syllogism
- **Defeasible**: Authority, Analogy, Causal, Practical Reasoning
- **Inductive**: Generalization, Statistical, Example
- **Abductive**: Best Explanation, Diagnostic

### 2. Enhanced Node Properties

**Core Extensions**:

```json
{
  "nodeID": "1",
  "text": "Climate scientists agree on warming",
  "type": "I",
  "category": "evidence",           // NEW: Semantic category
  "role": "supporting_evidence",    // NEW: Argumentative role
  "strength": 0.9,                 // NEW: Confidence level
  "schemeID": "S1",                // NEW: Links to scheme
  "section": "Introduction",        // NEW: Document structure
  "para": 2,                       // NEW: Paragraph number
  "offsetStart": 45,               // NEW: Character position
  "offsetEnd": 78                  // NEW: Character position
}
```

**Role Classifications**:

- `main_thesis`, `sub_thesis`, `supporting_claim`, `counter_claim`
- `evidence`, `example`, `analogy`, `assumption`, `background`
- `objection`, `rebuttal`, `concession`, `qualification`

### 3. Advanced Edge Types

**Extended Relationships**:

```json
{
  "edgeID": "1",
  "fromID": "1",
  "toID": "2",
  "relationshipType": "supports",   // Enhanced semantic types
  "weight": 0.8,                   // Relationship strength
  "formEdgeID": "S1"               // Links to scheme when applicable
}
```

**Relationship Types**:

- **supports**, **attacks**, **infers** (core AIF)
- **assumes**, **exemplifies**, **questions** (new)
- **references**, **asserts**, **relates** (new)

### 4. Enhanced Locutions

**Participant-Node Linking**:

```json
{
  "locutions": [
    {
      "locutionID": "L1",
      "participantID": "P1",
      "nodeID": "1",
      "timestamp": "2024-01-01T12:00:00Z",
      "section": "Introduction",     // NEW: Document location
      "sourceSentence": "Sentence 3" // NEW: Source reference
    }
  ],
  "participants": [
    {
      "participantID": "P1",
      "name": "Author",
      "role": "primary_author",      // NEW: Participant role
      "affiliation": "University"    // NEW: Institutional context
    }
  ]
}
```

## Quality Validation System

### Built-in Metrics

The enhanced system includes comprehensive quality validation:

```bash
# Run quality validation
./scripts/validate_extraction.sh output/result.json texts/source.txt
```

**Quality Benchmarks**:

- **Scheme Detection**: >80% of RA/CA nodes should have schemes
- **Location Tracking**: >70% of nodes should have section/paragraph info
- **Graph Connectivity**: No isolated nodes
- **Locution Completeness**: All I-nodes should have locutions
- **Hallucination Detection**: Monitor [Implied] content markers

### Extraction Density Guidelines

- **Simple texts**: 20-40 nodes per 1000 words
- **Academic papers**: 40-60 nodes per 1000 words
- **Complex arguments**: 60-80 nodes per 1000 words

## Model Requirements

### Recommended Models

- **GPT-4 Turbo**: Best overall performance
- **GPT-4o**: Excellent for complex schemes
- **Claude-3 Opus**: Strong logical reasoning

### Single-Prompt Approach

The enhanced system uses a single, comprehensive prompt with:

- **Self-verification rules** to reduce hallucination
- **Comprehensive extraction guidelines** for consistency
- **Quality benchmarks** built into the prompt
- **Scheme detection training** with examples

## Usage Examples

### Basic Extraction

```bash
# Extract argument graph from text
ostruct run templates/main.j2 schemas/main.json \
  -V argument_text="$(cat your_text.txt)" \
  > output/result.json

# Validate quality
./scripts/validate_extraction.sh output/result.json your_text.txt
```

### Testing Different Texts

```bash
# Test with pre-built examples
ostruct run templates/main.j2 schemas/main.json \
  -V argument_text="$(cat texts/authority_argument.txt)" \
  > output/authority_test.json

ostruct run templates/main.j2 schemas/main.json \
  -V argument_text="$(cat texts/causal_argument.txt)" \
  > output/causal_test.json
```

## Example Output Structure

```json
{
  "AIF": {
    "version": "1.0",
    "analyst": "Enhanced AIF Extractor",
    "created": "2024-01-01T12:00:00Z",
    "extensions": ["f-nodes-v1", "metadata-v1"]
  },
  "nodes": [
    {
      "nodeID": "1",
      "text": "Software testing prevents costly bugs",
      "type": "I",
      "category": "premise",
      "role": "supporting_claim",
      "strength": 0.9,
      "section": "Introduction",
      "para": 1,
      "offsetStart": 0,
      "offsetEnd": 35
    },
    {
      "nodeID": "2",
      "text": "Therefore, we should invest in testing",
      "type": "RA",
      "category": "inference",
      "schemeID": "S1",
      "para": 1,
      "offsetStart": 36,
      "offsetEnd": 74
    }
  ],
  "schemeNodes": [
    {
      "schemeID": "S1",
      "schemeName": "Practical Reasoning",
      "schemeGroup": "defeasible",
      "description": "Argument from consequences to action",
      "criticalQuestions": [
        "Are the consequences desirable?",
        "Are there alternative actions?"
      ]
    }
  ],
  "edges": [
    {
      "edgeID": "1",
      "fromID": "1",
      "toID": "2",
      "relationshipType": "supports",
      "weight": 0.9,
      "formEdgeID": "S1"
    }
  ],
  "locutions": [
    {
      "locutionID": "L1",
      "participantID": "P1",
      "nodeID": "1",
      "timestamp": "2024-01-01T12:00:00Z",
      "section": "Introduction"
    }
  ],
  "participants": [
    {
      "participantID": "P1",
      "name": "Author",
      "role": "primary_author"
    }
  ]
}
```

## Backward Compatibility

- **Standard AIF Tools**: Core structure (nodes, edges) remains compatible
- **AIFdb Integration**: Can import/export core AIF components
- **Graceful Degradation**: Enhanced features are additive, not breaking
- **Extension Mechanism**: Follows AIF's intended extensibility design

## File Structure

```
examples/analysis/argument-aif/
├── schemas/main.json           # Enhanced AIF schema
├── templates/main.j2           # Rich extraction prompt
├── scripts/validate_extraction.sh  # Quality validation
├── texts/                      # Test cases
│   ├── test_1page.txt         # Simple argument
│   ├── causal_argument.txt    # Causal reasoning
│   └── authority_argument.txt # Argument from authority
├── output/                     # Generated results
└── AIF_EXTENSIONS.md          # This documentation
```

## Quality Features

### Self-Verification

- **Grounding checks**: All text must come from source
- **Scheme validation**: SchemeIDs must reference existing schemes
- **Connectivity validation**: No isolated nodes
- **Role consistency**: Roles must match node types

### Anti-Hallucination

- **[Implied] markers** for inferred content
- **Source grounding** for all claims
- **Conservative extraction** approach
- **Validation benchmarks** in prompt

This enhanced AIF system provides research-grade argument graph extraction while maintaining practical usability and compatibility with existing AIF tools.
