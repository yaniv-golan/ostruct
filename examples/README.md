# ostruct-cli Examples

This directory contains practical examples demonstrating various use cases for the `ostruct` CLI. Each example is self-contained and includes all necessary files to run it.

## Prerequisites

- Python 3.10 or higher
- `ostruct-cli` installed (`pip install ostruct-cli`)
- OpenAI API key set in environment (`OPENAI_API_KEY`)

## Directory Structure

### Security Examples

- [vulnerability-scan](security/vulnerability-scan/): Automated security vulnerability scanning
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

### Infrastructure Examples

- [pipeline-validator](infrastructure/pipeline-validator/): CI/CD pipeline validation
- [iac-validator](infrastructure/iac-validator/): Infrastructure as Code validation
- [license-audit](infrastructure/license-audit/): Dependency license auditing

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
   cd security/vulnerability-scan
   ```

4. Run the example using the CLI commands shown in the example's README.md file.

## Contributing

Feel free to contribute additional examples! Please follow these guidelines:

1. Create a new directory under the appropriate category
2. Include all necessary files (schema, templates, sample data)
3. Add a comprehensive README.md with clear CLI usage examples
4. Ensure the example is self-contained and runnable
5. Add appropriate security checks and error handling

## Usage

See each example's README.md for specific usage instructions and CLI commands.
