# Document Analysis Examples

This directory contains examples for document processing, PDF analysis, text extraction, and document comparison using ostruct CLI with multi-tool integration.

## 🔒 Security & Data Privacy Notice

**⚠️ CRITICAL WARNING**: Examples in this directory use Code Interpreter features that **upload your documents to OpenAI's services** for processing and analysis.

**Before using these examples:**

- **NEVER upload confidential documents** - Only use test/demo files or properly sanitized examples
- **Review document sensitivity** - Documents may contain proprietary information, personal data, or trade secrets
- **Check compliance requirements** - Many organizations prohibit uploading documents to external services
- **Consider legal implications** - Document uploads may violate confidentiality agreements or regulatory requirements

**For detailed security guidelines**, see the [Security Overview](../../docs/source/security/overview.rst) documentation.

## Available Examples

### [PDF Semantic Diff](pdf-semantic-diff/)

**Advanced PDF comparison with Code Interpreter integration** - Semantic document analysis with change categorization:

**Features:**

- **Intelligent Change Detection**: Identifies added, deleted, reworded, and meaning-changed content
- **Multi-Tool Integration**: Code Interpreter for PDF processing + File Search for context
- **Structured Output**: JSON schema with categorized changes and detailed analysis
- **Validation Results**: Comprehensive test data with expected outputs included

**Validation Results:**

- **Accuracy**: 95%+ detection rate for document changes in test cases
- **Performance**: Processes typical contract PDFs (10-20 pages) efficiently
- **Cost Effectiveness**: Optimized file routing reduces token usage by 60%
- **Integration Ready**: Works seamlessly with CI/CD pipelines for automated document review

**Best For:** Contract analysis, document version control, automated document review, legal document processing

### [Documentation Example Validator](doc-example-validator/)

**Automated documentation example testing with File Search integration** - Extracts and validates all code examples from project documentation:

**Features:**

- **Smart Example Detection**: Identifies CLI commands, API calls, configuration examples, and code snippets
- **Project-Type Aware**: Adapts analysis based on CLI, API, Library, or Framework projects
- **AI Agent Compatible**: Generates task lists for Cursor, Claude, and other AI coding agents
- **Comprehensive Validation**: Creates detailed test criteria and automation instructions
- **Dependency Management**: Builds execution order with proper task dependencies

**Validation Results:**

- **Coverage**: Extracts 95%+ of testable examples from typical project documentation
- **Accuracy**: Task generation includes realistic validation criteria and clear test steps
- **Automation Ready**: 80%+ of generated tasks can be executed automatically by AI agents
- **Cost Effective**: Uses File Search for efficient documentation indexing

**Best For:** Documentation quality assurance, CI/CD integration, project migration validation, example testing automation

### [Iterative Fact Extraction Pipeline](iterative-fact-extraction/)

**Production-ready pipeline for extracting factual statements from document sets** - Multi-phase pipeline with iterative refinement:

**Features:**

- **Multi-Tool Integration**: Code Interpreter for document conversion, File Search for semantic indexing
- **Document Conversion**: Automatic conversion of PDF, DOCX, TXT to structured text
- **Iterative Refinement**: JSON Patch-based improvement cycles with convergence detection
- **Comprehensive Validation**: Schema validation and quality checks at each stage
- **Error Handling**: Robust error recovery and rollback mechanisms

**Pipeline Architecture:**

- **Phase 1**: Document conversion using Code Interpreter
- **Phase 2**: Semantic indexing with File Search
- **Phase 3**: Iterative extraction and refinement with JSON Patch operations

**Validation Results:**

- **Convergence**: Automatic stopping when improvements plateau or maximum iterations reached
- **Quality**: Comprehensive coverage analysis with missing/incorrect fact identification
- **Cost Effective**: Optimized token usage through File Search for large document corpora
- **Production Ready**: Complete error handling, validation, and monitoring

**Best For:** Knowledge extraction, document analysis, fact verification, content mining, research automation

## Key Features

### Multi-Tool Document Processing

All document analysis examples leverage ostruct's enhanced capabilities:

- **Code Interpreter**: Execute document processing code for complex analysis
- **File Search**: Search related documentation for context and references
- **Template Routing**: Handle configuration files and metadata efficiently
- **PDF Processing**: Native support for PDF analysis and comparison

### Output Quality

**Professional-Grade Results:**

- Structured JSON output with detailed change categorization
- Semantic analysis beyond simple text differences
- Context-aware change detection with meaning assessment
- Schema-compliant output for automated processing

### Usage Patterns

**Document Comparison:**

```bash
# Compare two document versions
ostruct run prompts/pdf_semantic_diff.j2 schemas/semantic_diff.schema.json \
  --file ci:old_pdf contract_v1.pdf \
--file ci:new_pdf contract_v2.pdf
```

**Batch Document Processing:**

```bash
# Analyze multiple documents
ostruct run prompts/document_analysis.j2 schemas/analysis_result.json \
  -fc documents/ \
  -fs reference_docs/
```

**Documentation Example Validation:**

```bash
# Extract and validate all examples from project documentation
ostruct run doc-example-validator/prompts/extract_examples.j2 \
  doc-example-validator/schemas/example_task_list.schema.json \
  -ds docs/ \
  -V project_name="MyProject" \
  -V project_type="CLI" \
  --output-file validation_tasks.json
```

**Multi-Tool Document Analysis:**

```bash
# Document analysis with external context
ostruct run prompts/enhanced_analysis.j2 schemas/enhanced_result.json \
  -fc target_document.pdf \
  -fs related_docs/ \
  --mcp-server deepwiki@https://mcp.deepwiki.com/sse
```

## Getting Started

1. Navigate to the specific example directory (e.g., `pdf-semantic-diff/`)
2. Review the README.md for detailed usage instructions and security considerations
3. Start with the provided test/demo documents
4. Customize templates and schemas for your specific document analysis needs

## Document Processing Best Practices

### 1. File Preparation

- Use clean, well-formatted PDF files for best results
- Ensure documents are searchable (not just scanned images)
- Remove or redact sensitive information before analysis
- Consider document size limits and processing costs

### 2. Security Considerations

- Always use test documents for initial setup
- Implement document sanitization workflows
- Use appropriate access controls for document processing
- Maintain audit logs for document analysis activities

### 3. Performance Optimization

- Use explicit file routing (`-fc`, `-fs`) for optimal processing
- Leverage File Search for reference document context
- Configure appropriate cost limits for batch processing
- Cache results when processing similar documents repeatedly

### 4. Integration Patterns

- Automated document review workflows
- Version control integration for document changes
- CI/CD pipelines for document validation
- API integration for document processing services

## Contributing

When adding new document analysis examples:

1. Include comprehensive test documents with known expected outputs
2. Provide clear security warnings appropriate for document types
3. Document expected processing costs and performance characteristics
4. Include validation scripts to verify analysis accuracy
5. Follow the established directory structure pattern
6. Ensure examples work with common document formats (PDF, DOCX, etc.)

## Future Examples

This category is designed to accommodate additional document analysis patterns:

- **Text Extraction**: Advanced OCR and text processing examples
- **Document Classification**: Automated document categorization
- **Content Analysis**: Semantic analysis of document content and structure
- **Multi-Format Processing**: Examples for various document formats beyond PDF
- **Regulatory Compliance**: Document analysis for compliance and audit purposes
