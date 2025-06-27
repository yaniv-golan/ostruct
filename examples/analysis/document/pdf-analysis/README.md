# Document Analysis

> **Tools:** 🐍 Code Interpreter · 📄 File Search
> **Cost (approx.):** <$0.10 with gpt-4.1

## 1. Description

This example demonstrates comprehensive document analysis using ostruct's multi-tool integration. It analyzes text documents (including PDF content) to extract key insights, assess document quality, identify themes and inconsistencies, and provide actionable recommendations. The analysis combines Code Interpreter for data processing with File Search for context discovery.

## 2. Prerequisites

```bash
# No special dependencies required - uses built-in tools
```

## 3. Quick Start

```bash
# Fast validation (no API calls)
./run.sh --test-dry-run

# Live API test (minimal cost)
./run.sh --test-live

# Full execution with sample documents
./run.sh

# Analyze specific document type
./run.sh --analysis-type detailed

# With custom model
./run.sh --model gpt-4o-mini
```

## 4. Files

| Path | Purpose |
|------|---------|
| `templates/main.j2` | Primary analysis template for comprehensive document review |
| `templates/document_analysis.j2` | Focused single-document analysis template |
| `templates/enhanced_analysis.j2` | Advanced analysis with cross-document comparison |
| `schemas/main.json` | Validates structured analysis output with insights and recommendations |
| `schemas/analysis_result.json` | Schema for individual document analysis results |
| `schemas/enhanced_result.json` | Schema for advanced multi-document analysis |
| `data/sample_business_doc.txt` | Sample business document for demonstration |
| `data/test_document.txt` | Small test file for quick validation |

## 5. Expected Output

The analysis produces structured JSON containing:

- **Document Summary**: Overview of all analyzed documents with key themes
- **Individual Document Analysis**: Detailed breakdown of each document including:
  - Content summary and key information extraction
  - Structure and quality assessment (clarity, completeness, consistency)
  - Quality scores (1-10 scale)
- **Cross-Document Analysis**: Common themes, inconsistencies, and relationships
- **Key Insights**: Prioritized insights with supporting evidence and implications
- **Recommendations**: Actionable recommendations with priority levels and rationales
- **Metadata**: Analysis statistics and confidence levels

Example output structure:

```json
{
  "document_summary": {
    "total_documents": 2,
    "overall_assessment": "Documents provide comprehensive coverage...",
    "key_themes": ["business requirements", "project specifications"]
  },
  "individual_documents": [...],
  "key_insights": [
    {
      "insight": "Documents lack specific success metrics",
      "importance": "high",
      "implications": "May lead to unclear project outcomes"
    }
  ],
  "recommendations": [
    {
      "recommendation": "Add quantifiable success criteria",
      "priority": "high",
      "rationale": "Enables better project tracking and evaluation"
    }
  ]
}
```

## 6. Customization

### Analysis Types

- `basic`: Quick overview and key points extraction
- `comprehensive` (default): Full analysis with quality assessment
- `detailed`: Enhanced analysis with cross-document comparison

### Input Options

- **Single Document**: Use `--file ci:documents data/your_doc.txt`
- **Multiple Documents**: Use `--file ci:documents data/` to analyze entire directory
- **With Context**: Add `--file fs:context docs/` for additional context via File Search

### Template Selection

```bash
# Use different analysis templates
ostruct run templates/document_analysis.j2 schemas/analysis_result.json --file ci:documents data/sample_business_doc.txt

# Enhanced cross-document analysis
ostruct run templates/enhanced_analysis.j2 schemas/enhanced_result.json --file ci:documents data/
```

### Custom Variables

```bash
# Specify analysis focus
./run.sh -V analysis_focus="financial metrics"

# Set quality thresholds
./run.sh -V min_quality_score=7
```

## 7. Use Cases

- **Business Document Review**: Analyze requirements, specifications, and reports
- **Content Quality Assessment**: Evaluate document clarity and completeness
- **Multi-Document Comparison**: Identify inconsistencies across related documents
- **Knowledge Extraction**: Extract key insights and actionable recommendations
- **Document Standardization**: Assess compliance with documentation standards

## 8. Clean-Up

```bash
# Remove generated analysis files
rm -rf downloads/
```

## 9. Advanced Usage

### Batch Analysis

```bash
# Analyze multiple document sets
for dir in docs/*/; do
  ./run.sh --file ci:documents "$dir" --output-file "analysis_$(basename "$dir").json"
done
```

### Integration with Other Tools

```bash
# Combine with file search for enhanced context
./run.sh --file ci:documents data/ --file fs:context knowledge_base/ --enable-tool file-search
```

### Custom Analysis Parameters

```bash
# Focus on specific aspects
./run.sh -V focus_areas='["compliance", "technical accuracy", "completeness"]'
```
