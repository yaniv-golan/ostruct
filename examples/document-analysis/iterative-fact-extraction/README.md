# Iterative Fact Extraction Pipeline

This example demonstrates a production-ready pipeline for extracting factual statements from document sets using ostruct's multi-tool integration. The system performs iterative refinement through semantic analysis and JSON Patch operations to improve fact coverage and accuracy.

## 🔒 Security & Data Privacy Notice

Please be aware of the following when using `ostruct` with different file routing options:

* **File Uploads to OpenAI Tools**:
  * Flags like `--file ci:`, `--dir ci:` (for Code Interpreter) and `--file fs:`, `--dir fs:` (for File Search) **will upload your files** to OpenAI's services for processing.
  * Ensure you understand OpenAI's data usage policies before using these options with sensitive data.

* **Template-Only Access & Prompt Content**:
  * Flags like `-ft`, `--fta`, `-dt`, `--dta` (and legacy `-f`, `-d`) are designed for template-only access and **do not directly upload files to Code Interpreter or File Search services.**
  * **However, if your Jinja2 template includes the content of these files (e.g., using `{{ my_file.content }}`), that file content WILL become part of the prompt sent to the main OpenAI Chat Completions API.**
  * For large files or sensitive data that should not be part of the main prompt, even if used with `-ft`, avoid rendering their full content in the template or use redaction techniques.

For detailed information about data handling and security best practices, see the [Security Overview](../../../docs/source/security/overview.rst) documentation.

## Overview

* **Input**: Document sets (PDF, DOCX, TXT, etc.)
* **Processing**: Multi-phase pipeline with Code Interpreter, File Search, and iterative refinement
* **Output**: Structured JSON with extracted facts and metadata
* **Tools Used**: Code Interpreter for document conversion, File Search for semantic indexing, iterative refinement with JSON Patch

## Quick Start

```bash
# Navigate to example directory
cd examples/document-analysis/iterative-fact-extraction

# Place documents in input directory
cp your_document_1.pdf your_document_2.pdf your_document_3.pptx input_docs/

# Run the complete pipeline
./extract_facts.sh input_docs/

# View results (if jq is installed)
jq '.extracted_facts | length' input_docs_facts.json

# Or view results without jq
cat input_docs_facts.json
```

## Features

* **Multi-Tool Integration**: Demonstrates Code Interpreter, File Search, and template-based processing
* **Document Conversion**: Automatic conversion of various document formats to text
* **Semantic Indexing**: File Search integration for document corpus analysis
* **Iterative Refinement**: JSON Patch-based improvement cycles
* **Convergence Detection**: Automatic stopping when improvements plateau
* **Comprehensive Validation**: Schema validation and quality checks at each stage
* **Error Handling**: Robust error recovery and rollback mechanisms

## Pipeline Architecture

### Phase 1: Document Conversion

* Uses Code Interpreter to convert PDF, DOCX, and other formats to structured text

* Preserves document metadata and structure
* Validates conversion quality

### Phase 2: Semantic Indexing

* Uploads converted documents to File Search for semantic analysis

* Prepares corpus for fact extraction queries
* Validates document corpus size and quality

### Phase 3: Iterative Extraction and Refinement

* **Initial Extraction**: Uses File Search to extract facts from document corpus

* **Coverage Analysis**: Evaluates extracted facts against source documents
* **Patch Generation**: Creates JSON Patch operations to improve coverage
* **Patch Application**: Applies improvements with error handling and rollback
* **Convergence Detection**: Stops when improvements plateau or maximum iterations reached

## Usage

### Simple Usage (Recommended)

Use the simple `extract_facts.sh` script for easy fact extraction:

```bash
# Extract facts from a folder (creates folder_name_facts.json)
./extract_facts.sh /path/to/documents/

# Extract facts with custom output name
./extract_facts.sh /path/to/documents/ my_analysis

# Show help
./extract_facts.sh --help
```

**Examples:**

```bash
# Using the included test data
./extract_facts.sh input_docs/
# → Creates: input_docs_facts.json and input_docs_facts_intermediate/

# Custom analysis name
./extract_facts.sh ~/company_docs/ quarterly_report
# → Creates: quarterly_report.json and quarterly_report_intermediate/
```

**Parameters:**

* `input_folder`: Directory containing documents in supported formats (txt, pdf, docx, etc.)
* `output_name`: Optional name for final JSON output (default: `<folder_name>_facts.json`)

**Output Structure:**

* **Final output**: `{name}.json` - Contains all extracted facts
* **Intermediate files**: `{name}_intermediate/` - Contains iteration history, patches, and convergence reports

### Development and Testing

```bash
# Test with sample data
./extract_facts.sh test_data/sample_docs/ test_run

# Cost estimation before processing
./extract_facts.sh --estimate ~/my_documents/

# Validate templates and schemas (built into extract_facts.sh)
./extract_facts.sh --help
```

## Configuration

### Pipeline Configuration

The `extract_facts.sh` script uses built-in configuration:

```bash
MAX_ITERATIONS=5           # Maximum refinement iterations
MIN_IMPROVEMENT=0.1        # Minimum coverage improvement threshold
CONVERGENCE_THRESHOLD=0.95 # Target coverage score
```

These can be modified by editing the script directly. The pipeline automatically:

* Creates intermediate directories for each run
* Generates comprehensive documentation (README.md)
* Provides cost estimation with `--estimate` flag
* Handles all file routing and validation

## Output Format

### Final Extraction Results

```json
{
  "extracted_facts": [
    {
      "id": "fact_001",
      "text": "The company was founded in 2019",
      "source": "company_history.pdf",
      "confidence": 0.95,
      "category": "organization"
    }
  ]
}
```

### Convergence Report

```json
{
  "convergence": {
    "final_iteration": 3,
    "reason": "low_improvement",
    "total_iterations": 4
  },
  "iterations": [
    {
      "iteration": 0,
      "facts_count": 25,
      "coverage_score": 0.72
    }
  ]
}
```

## Technical Details

### Schema Design

All schemas use object-root format compatible with OpenAI Responses API:

* **Extract Schema**: Validates fact structure with required fields (id, text, source)
* **Assessment Schema**: Validates coverage analysis with missing/incorrect fact identification
* **Patch Schema**: Validates RFC-6902 JSON Patch operations
* **Conversion Schema**: Validates document conversion output

### Template Structure

Templates use verified file variable access patterns:

* **Document Conversion**: `{{ input_document.content }}` for file content access
* **Fact Extraction**: `{{ text_files }}` for File Search directory routing
* **Coverage Analysis**: Combines current facts and source documents
* **Patch Generation**: Uses assessment results to create improvement operations

### Convergence Detection

Multiple criteria prevent infinite loops:

* **Empty Patches**: No improvement operations generated
* **Low Improvement**: Coverage score improvement below threshold
* **Maximum Iterations**: Hard limit on refinement cycles
* **High Coverage**: Target coverage score achieved

## File Structure

```
examples/document-analysis/iterative-fact-extraction/
├── README.md                          # This documentation
├── extract_facts.sh                   # Main extraction script
├── prompts/
│   ├── convert.j2                     # Document conversion template
│   ├── extract.j2                     # Fact extraction template
│   ├── assess.j2                      # Coverage analysis template
│   └── patch.j2                       # Patch generation template
├── schemas/
│   ├── convert_schema.json            # Document conversion schema
│   ├── extract_schema.json            # Fact extraction schema
│   ├── assessment_schema.json         # Coverage analysis schema
│   └── patch_schema.json              # JSON Patch schema
├── test_data/
│   └── sample_docs/                   # Sample input documents
└── {output_name}_intermediate/        # Generated per run (with README.md)
    ├── converted/                     # Document conversion results
    ├── corpus/                        # Files prepared for File Search
    ├── extracted_v{N}.json            # Facts from each iteration
    ├── assessment_v{N}.json           # Coverage analysis per iteration
    ├── patch_v{N}.json                # Improvement patches per iteration
    ├── convergence_report.json        # Final pipeline metrics
    └── README.md                      # Auto-generated documentation
```

## Requirements

* **ostruct**: v0.7.0 or later with multi-tool support
* **OpenAI API**: Access required for gpt-4o model
* **System Tools**: bash shell, jq (for JSON processing)
* **Environment**: OPENAI_API_KEY must be set

### Installing jq

The `extract_facts.sh` script requires `jq` for JSON processing:

```bash
# Install jq on macOS
brew install jq

# Install jq on Ubuntu/Debian
sudo apt-get install jq

# Install jq on CentOS/RHEL/Fedora
sudo yum install jq  # or: sudo dnf install jq

# Install jq on Windows (with Chocolatey)
choco install jq

# For other systems, see: https://jqlang.github.io/jq/download/
```

## Cost Estimation

Typical costs for document processing:

* **Small corpus** (5 docs, 50KB total): ~$0.50-1.00
* **Medium corpus** (20 docs, 200KB total): ~$2.00-4.00
* **Large corpus** (100 docs, 1MB total): ~$10.00-20.00

Costs depend on:

* Document size and complexity
* Number of refinement iterations
* Model selection (gpt-4o vs gpt-4o-mini)

Use the built-in cost estimation feature:

```bash
./extract_facts.sh --estimate ~/my_documents/
```

This provides detailed cost breakdowns for each template and total estimated costs per iteration.

## Performance Optimization

### Token Usage Optimization

* Use File Search for large document corpora to avoid prompt size limits
* Leverage Code Interpreter for document conversion to reduce manual processing
* Implement convergence detection to minimize unnecessary iterations

### Processing Efficiency

* Parallel document conversion where possible
* Incremental fact extraction with patch-based updates
* Comprehensive validation to prevent reprocessing

### Quality Improvements

* Adjust convergence thresholds based on use case requirements
* Customize fact categories for domain-specific extraction
* Implement custom validation rules for fact quality

## Troubleshooting

### Common Issues

**Document Conversion Failures**:

```bash
# Check document format support
python scripts/validate_conversion.py text_output/

# Manual conversion fallback
ostruct run prompts/convert.j2 schemas/convert_schema.json \
  --file ci:input_document problematic_doc.pdf --dry-run
```

**Schema Validation Errors**:

```bash
# Validate all schemas
ostruct run prompts/extract.j2 schemas/extract_schema.json --dry-run

# Check object-root format (with jq)
jq '.type' schemas/*.json  # Should all return "object"

# Or check manually (without jq)
grep '"type"' schemas/*.json
```

**Convergence Issues**:

```bash
# Check iteration progress (with jq)
jq '.convergence' {output_name}_intermediate/convergence_report.json

# Or view full report (without jq)
cat {output_name}_intermediate/convergence_report.json

# The extract_facts.sh script shows progress automatically
```

## Contributing

To extend this example:

1. **Custom Fact Categories**: Modify extraction templates and schemas
2. **Additional Document Types**: Extend conversion templates
3. **Custom Convergence Criteria**: Modify convergence detection logic
4. **Integration with External Systems**: Add MCP server connections

## Related Examples

* [PDF Semantic Diff](../pdf-semantic-diff/): Document comparison techniques
* [Doc Example Validator](../doc-example-validator/): Documentation analysis patterns
* [Multi-Tool Analysis](../../data-analysis/multi-tool-analysis/): Advanced multi-tool integration

## License

This example is part of the ostruct project and follows the same license terms.
