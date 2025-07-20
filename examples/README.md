# Ostruct Examples

This directory contains practical examples demonstrating ostruct's capabilities across different domains and use cases.

## Available Examples

### Tools Integration

- **[code-interpreter-basics](tools/code-interpreter-basics/)** - CSV analysis and data visualization
- **[file-search-basics](tools/file-search-basics/)** - Document Q&A with file search
- **[web-search-basics](tools/web-search-basics/)** - Web search with current information retrieval

### Document Analysis

- **[pdf-analysis](analysis/document/pdf-analysis/)** - Multi-tool PDF document analysis
- **[pdf-semantic-diff](analysis/document/pdf-semantic-diff/)** - Semantic comparison of PDF documents
- **[pitch-distiller](analysis/document/pitch-distiller/)** - Two-pass pitch deck analysis with PDF support

### Data Analysis

- **[multi-tool](analysis/data/multi-tool/)** - Comprehensive business data analysis
- **[argument-aif](analysis/argument-aif/)** - Argument Interchange Format (AIF) analysis pipeline

### Automation & Workflows

- **[storyboard-to-veo3](automation/storyboard-to-veo3/)** - Transform storyboards into Veo3-ready video generation JSON

### Integration

- **[multi-agent-debate](integration/multi-agent-debate/)** - Multi-agent debate system

### Security & Utilities

- **[vulnerability-scan](security/vulnerability-scan/)** - Security vulnerability scanning
- **[etymology](utilities/etymology/)** - Word etymology analysis

## Running Examples

Each example provides a standardized interface via `make`:

```bash
# Quick validation (no API calls)
make test-dry

# Minimal live test
make test-live

# Run with default settings
make run

# Clean up generated files
make clean

# Show available targets
make help
```

## Contributing Examples

When creating or modifying examples, please follow the [Examples Standard](../docs/source/contribute/examples_standard.rst) which defines the required interface and structure. This ensures consistency while preserving implementation flexibility.

## Example Structure

Examples can use any internal structure but must provide the standardized `make` targets. Common patterns include:

- **Simple**: Direct ostruct calls with templates and schemas
- **Multi-pass**: Sequential processing with intermediate outputs
- **Pipeline**: Complex workflows with multiple tools and post-processing

See individual example directories for specific usage instructions and implementation details.
