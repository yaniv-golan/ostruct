# ostruct-cli Examples

This directory contains practical examples demonstrating various use cases for the `ostruct` CLI with both traditional usage and enhanced multi-tool integration. Each example is self-contained and includes all necessary files to run it.

## Prerequisites

- Python 3.10 or higher
- `ostruct-cli` installed (`pip install ostruct-cli`)
- OpenAI API key set in environment (`OPENAI_API_KEY`)

## Multi-Tool Integration

All examples support the enhanced CLI with multi-tool capabilities:

- **Traditional Usage**: All existing commands work exactly as before
- **Multi-Tool Usage**: Examples demonstrate Code Interpreter, File Search, Web Search, and MCP integration
- **Explicit File Routing**: Optimized performance through `-ft`, `-fc`, `-fs` flags
- **Configuration System**: YAML-based configuration for persistent settings

### File Routing Syntax Reference

Each file routing option supports three syntaxes:

**Template Files** (available in template context only):

```bash
-ft config.yaml                    # Auto-naming → config_yaml variable
-ft app_config config.yaml         # Two-arg syntax → app_config variable
--fta app_config config.yaml       # Two-arg alias → app_config variable (best tab completion)
```

**Important**: Access file content with `{{ variable.content }}`, not `{{ variable }}`.
Example: `{{ config_yaml.content }}` or `{{ app_config.content }}`

**Code Interpreter Files** (uploaded for execution + available in template):

```bash
-fc data.csv                       # Auto-naming → data_csv variable
-fc dataset data.csv               # Two-arg syntax → dataset variable
--fca dataset data.csv             # Two-arg alias → dataset variable (best tab completion)
```

**File Search Files** (uploaded to vector store + available in template):

```bash
-fs docs.pdf                       # Auto-naming → docs_pdf variable
-fs manual docs.pdf                # Two-arg syntax → manual variable
--fsa manual docs.pdf              # Two-arg alias → manual variable (best tab completion)
```

**Usage Recommendations**:

- **Auto-naming**: Best for quick, one-off analysis
- **Two-arg syntax**: Compact and supports shell tab completion for file paths
- **Two-arg alias**: Best for reusable templates with stable variable names and full tab completion

## Directory Structure

### Document Analysis Examples

- [pdf-semantic-diff](document-analysis/pdf-semantic-diff/): **Advanced PDF comparison with Code Interpreter integration** - Semantic document analysis with change categorization (added, deleted, reworded, changed_in_meaning)
- [doc-example-validator](document-analysis/doc-example-validator/): **Automated documentation example testing with File Search integration** - Extracts and validates all code examples from project documentation, generates AI agent-compatible task lists
- [iterative-fact-extraction](document-analysis/iterative-fact-extraction/): **Production-ready pipeline for extracting factual statements from document sets** - Multi-phase pipeline with Code Interpreter, File Search, and iterative refinement using JSON Patch operations

### Infrastructure Examples

- [ci-cd-automation](infrastructure/ci-cd-automation/): **Enhanced CI/CD automation with multi-tool integration** - GitHub Actions, GitLab CI, Jenkins workflows with cost controls and error handling
- [pipeline-validator](infrastructure/pipeline-validator/): CI/CD pipeline validation
- [iac-validator](infrastructure/iac-validator/): Infrastructure as Code validation
- [license-audit](infrastructure/license-audit/): Dependency license auditing

### Optimization Examples

- [prompt-optimization](optimization/prompt-optimization/): **Cost and performance optimization techniques** - Smart template design with 50-70% token reduction through tool-specific routing

### Data Analysis Examples

- [multi-tool-analysis](data-analysis/multi-tool-analysis/): **Comprehensive multi-tool analysis patterns** - Code Interpreter + File Search + MCP integration for complex data workflows

### Research & Information Examples

- [web-search](web-search/): **Real-time information retrieval with web search integration** - Current events analysis, technology updates, market research with live data and source citations

### Security Examples

- [vulnerability-scan](security/vulnerability-scan/): **Three-approach automated security vulnerability scanning** - Static Analysis ($0.18), Code Interpreter ($0.18), and Hybrid Analysis ($0.20) with comprehensive directory-based project analysis
- [pii-scanner](security/pii-scanner/): GDPR/PII data leak detection
- [multi-repo-scan](security/multi-repo-scan/): Multi-repository security analysis
- [sast-processor](security/sast-processor/): SAST results processing

### Code Quality Examples

- [code-review](code-quality/code-review/): Automated code review
- [clone-detection](code-quality/clone-detection/): Code clone detection
- [todo-extractor](code-quality/todo-extractor/): Project-wide TODO extraction

### Testing Examples

- [test-generator](testing/test-generator/): Test case generation
- [failure-analysis](testing/failure-analysis/): Test failure root cause analysis
- [api-testing](testing/api-testing/): API testing with OpenAPI

### Data Processing Examples

- [log-analyzer](data-processing/log-analyzer/): Log file analysis
- [stream-processor](data-processing/stream-processor/): Streaming text analysis
- [table-extractor](data-processing/table-extractor/): Table data extraction
- [pipeline-config](data-processing/pipeline-config/): Data pipeline configuration

### Schema Validation Examples

- [config-validator](schema-validation/config-validator/): JSON/YAML config validation
- [proto-validator](schema-validation/proto-validator/): Protocol Buffer validation

### Release Management Examples

- [release-notes](release-management/release-notes/): Automated release notes generation

## Example Structure

Each example follows this structure:

```
example-name/
├── README.md           # Description, usage, and expected output
├── prompts/           # AI prompts
│   ├── system.txt     # AI's role and expertise
│   └── task.j2        # Task template
├── schemas/           # Output structure
│   └── result.json    # Schema definition
└── examples/          # Example inputs
    └── basic/         # Basic examples
```

## Running Examples

1. Clone this repository:

   ```bash
   git clone https://github.com/yaniv-golan/ostruct.git
   cd ostruct/examples
   ```

2. Set your OpenAI API key:

   ```bash
   export OPENAI_API_KEY='your-api-key'
   ```

3. Navigate to any example directory:

   ```bash
   cd document-analysis/pdf-semantic-diff
   # or
   cd infrastructure/ci-cd-automation
   # or
   cd optimization/prompt-optimization
   # or
   cd data-analysis/multi-tool-analysis
   ```

4. Run examples using either traditional or multi-tool syntax:

   ### Traditional Usage (Unchanged)

   ```bash
   # Traditional file processing
   ostruct run prompts/task.j2 schemas/result.json -f target=examples/basic/app.py

   # Traditional directory processing
   ostruct run prompts/task.j2 schemas/result.json -d source=examples/basic/
   ```

   ### Multi-Tool Usage

   ```bash
   # Code analysis with Code Interpreter
   ostruct run prompts/task.j2 schemas/result.json -fc examples/basic/app.py

   # Documentation search with File Search
   ostruct run prompts/task.j2 schemas/result.json -ds examples/basic/ -ft config.yaml

   # Multi-tool combination
   ostruct run prompts/task.j2 schemas/result.json \
     -fc source_code/ \
     -fs documentation/ \
     -ft configuration.yaml

   # With configuration
   ostruct --config ostruct.yaml run prompts/task.j2 schemas/result.json -fc data/
   ```

   ### MCP Server Integration

   ```bash
   # Connect to external services
   ostruct run prompts/task.j2 schemas/result.json \
     -fc local_data.csv \
     --mcp-server api@https://api.example.com/mcp
   ```

## Contributing

Feel free to contribute additional examples! Please follow these guidelines:

1. Create a new directory under the appropriate category
2. Include all necessary files (schema, templates, sample data)
3. Add a comprehensive README.md with clear CLI usage examples
4. Ensure the example is self-contained and runnable
5. Add appropriate security checks and error handling

## Usage

See each example's README.md for specific usage instructions and CLI commands.
