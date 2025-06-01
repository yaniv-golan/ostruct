# PDF Semantic Diff Analysis

This example demonstrates ostruct's ability to perform complex document analysis using Code Interpreter integration. The system extracts text from two PDF files, performs semantic comparison, and outputs structured JSON results.

## 🔒 Security & Data Privacy Notice

**⚠️ IMPORTANT**: This example uses Code Interpreter (`-fc`) features that **upload your PDF files to OpenAI's services** for processing.

**Before using with your documents:**

- **Review data sensitivity** - Do not upload confidential, proprietary, or sensitive documents
- **Consider document content** - PDFs may contain personal information, business secrets, or legal details
- **Check data governance policies** - Verify your organization allows document uploads to external services

**For detailed information about data handling and security best practices**, see the [Security Overview](../../docs/source/security/overview.rst) documentation.

## Overview

- **Input**: Two PDF files (old and new versions)
- **Processing**: Code Interpreter extracts text and performs semantic analysis
- **Output**: Structured JSON with categorized changes
- **Tools Used**: Code Interpreter for PDF processing and text analysis

## Quick Start

```bash
# Navigate to example directory
cd examples/enhanced/pdf-semantic-diff

# Run the analysis
ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json \
  -fc old_pdf test_data/contracts/v1.pdf \
  -fc new_pdf test_data/contracts/v2.pdf \
  --model gpt-4o --temperature 0
```

## Features

- **Multi-tool Integration**: Demonstrates file routing to Code Interpreter
- **Semantic Analysis**: Identifies meaningful changes beyond textual differences
- **Structured Output**: JSON schema validation ensures consistent results
- **Change Categorization**: Classifies changes as added, deleted, reworded, or changed_in_meaning
- **Comprehensive Testing**: Includes validation scripts and expected outputs

## Usage

### Enhanced Usage (Recommended)

The enhanced approach uses explicit file routing to ensure PDFs are processed by Code Interpreter:

```bash
ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json \
  -fc old_pdf path/to/old_document.pdf \
  -fc new_pdf path/to/new_document.pdf \
  --model gpt-4o \
  --temperature 0 \
  --output-file results.json
```

### Command-Line Options

- `-fc old_pdf <file>`: Route old PDF to Code Interpreter as `old_pdf` variable
- `-fc new_pdf <file>`: Route new PDF to Code Interpreter as `new_pdf` variable
- `--model gpt-4o`: Recommended model for best results
- `--temperature 0`: Ensures consistent, deterministic output
- `--output-file <file>`: Save results to specified JSON file

### Using the Test Data

```bash
# Run with provided sample contracts
./scripts/run_example.sh

# Validate output
python scripts/validate_output.py output.json

# Dry run (validation only)
ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json \
  -fc old_pdf test_data/contracts/v1.pdf \
  -fc new_pdf test_data/contracts/v2.pdf \
  --dry-run
```

## Output Format

The analysis produces a JSON object with the following structure:

```json
{
  "changes": [
    {
      "type": "added|deleted|reworded|changed_in_meaning",
      "description": "Brief description of the change",
      "old_snippet": "text from old version or null",
      "new_snippet": "text from new version or null"
    }
  ]
}
```

### Change Types

- **added**: Content appears only in the new version
- **deleted**: Content appears only in the old version
- **reworded**: Same meaning expressed differently
- **changed_in_meaning**: Semantic content has been altered

### Example Output

```json
{
  "changes": [
    {
      "type": "changed_in_meaning",
      "description": "Payment amount increased from $5,000 to $7,500",
      "old_snippet": "Payment of $5,000",
      "new_snippet": "Payment of $7,500"
    },
    {
      "type": "added",
      "description": "TypeScript specification added to frontend requirements",
      "old_snippet": null,
      "new_snippet": "React and TypeScript"
    }
  ]
}
```

## Technical Details

### How It Works

1. **File Routing**: PDFs are routed to Code Interpreter using `--fca` flags with explicit naming
2. **Text Extraction**: Python libraries (pdfplumber, PyPDF2) extract selectable text
3. **Semantic Analysis**: LLM compares texts and identifies meaningful differences
4. **Categorization**: Changes are classified into four semantic types
5. **JSON Output**: Results are formatted according to the provided schema

### Template Structure

The Jinja2 template (`prompts/pdf_semantic_diff.j2`) includes:

- **YAML Frontmatter**: System instructions for the LLM
- **Step-by-step Process**: Clear instructions for PDF extraction and analysis
- **Error Handling**: Guidance for common PDF processing issues
- **Output Format**: Explicit JSON structure requirements
- **Variable Access**: Uses `{{ old_pdf.name }}` and `{{ new_pdf.name }}` with explicit file naming

### Schema Design

The JSON schema (`schemas/semantic_diff.schema.json`) enforces:

- **Required Fields**: All changes must have type, description, and snippets
- **String Constraints**: Length limits for descriptions (≤150 chars) and snippets (≤250 chars)
- **Enum Validation**: Change types restricted to four valid options
- **Strict Mode**: `additionalProperties: false` prevents extra fields

## File Structure

```
examples/enhanced/pdf-semantic-diff/
├── README.md                          # This documentation
├── prompts/
│   └── pdf_semantic_diff.j2          # Main template with instructions
├── schemas/
│   └── semantic_diff.schema.json     # JSON schema for output validation
├── test_data/
│   ├── contracts/
│   │   ├── v1.pdf                    # Original contract sample
│   │   └── v2.pdf                    # Modified contract sample
│   ├── expected_output.json          # Expected analysis results
│   └── expected_changes.md           # Human-readable change documentation
└── scripts/
    ├── run_example.sh                # Full execution script
    ├── dry_run.sh                    # Template validation script
    └── validate_output.py            # Output validation script
```

## Requirements

- **ostruct**: v0.7.0 or later
- **OpenAI API**: Access required for gpt-4o model
- **Python Libraries**: pdfplumber, PyPDF2, or pymupdf (installed automatically by Code Interpreter)
- **Optional**: jsonschema for validation script

## Usage

### Basic Execution

```bash
# Run the complete analysis
./scripts/run_example.sh

# Or run manually with explicit file naming
ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json \
  --fca old_pdf test_data/contracts/v1.pdf \
  --fca new_pdf test_data/contracts/v2.pdf \
  --model gpt-4o \
  --output-file output.json
```

### Dry Run Testing

```bash
# Test template rendering without API calls
./scripts/dry_run.sh

# Or run manually
ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json \
  --fca old_pdf test_data/contracts/v1.pdf \
  --fca new_pdf test_data/contracts/v2.pdf \
  --dry-run
```

### Key Features

- **Explicit File Naming**: Uses `--fca old_pdf` and `--fca new_pdf` for predictable variable names
- **Template Variables**: Access files via `{{ old_pdf.name }}`, `{{ old_pdf.content }}`, etc.
- **Code Interpreter Integration**: Files are uploaded for Python-based PDF processing
- **Structured Output**: JSON results validated against schema

## Troubleshooting

### Common Issues

**Template Variable Errors**

- Ensure you use `--fca old_pdf` and `--fca new_pdf` (not auto-naming with `-fc`)
- Template expects exactly these variable names: `old_pdf` and `new_pdf`
- Check that file paths are correct and files exist

**PDF Extraction Failures**

- Ensure PDFs contain selectable text (not image-based)
- Try different PDF libraries if extraction fails
- Check file permissions and accessibility

**Schema Validation Errors**

- Verify JSON output is properly formatted
- Check that all required fields are present
- Ensure string lengths are within limits

**Inconsistent Results**

- Use `--temperature 0` for deterministic output
- Ensure model has sufficient context window
- Consider using gpt-4o for best performance

### Model Recommendations

- **Primary**: gpt-4o (best balance of capability and cost)
- **Alternative**: gpt-4o-32k (for very large documents)
- **Budget**: gpt-4o-mini (may have reduced accuracy)

### Performance Considerations

- **File Size**: Larger PDFs may require more processing time
- **Complexity**: Documents with complex layouts may need manual review
- **API Limits**: Consider rate limiting for batch processing

## Integration Examples

### Batch Processing

```bash
# Process multiple document pairs
for old_file in old_docs/*.pdf; do
  new_file="new_docs/$(basename "$old_file")"
  output_file="results/$(basename "$old_file" .pdf)_diff.json"

  ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json \
    --fca old_pdf "$old_file" \
    --fca new_pdf "$new_file" \
    --output-file "$output_file"
done
```

### Custom Workflows

```bash
# Generate diff and immediately validate
ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json \
  --fca old_pdf contract_v1.pdf \
  --fca new_pdf contract_v2.pdf \
  --output-file diff.json && \
python scripts/validate_output.py diff.json
```

## Related Examples

- **Multi-tool Analysis**: Demonstrates similar file routing patterns
- **Data Processing**: Shows structured output validation
- **Document Analysis**: Related document processing workflows

## Contributing

When modifying this example:

1. **Test Changes**: Run validation scripts after modifications
2. **Update Documentation**: Keep README synchronized with implementation
3. **Schema Compliance**: Ensure outputs validate against the schema
4. **Follow Patterns**: Maintain consistency with other examples

## License

This example is part of the ostruct project and follows the same licensing terms.
