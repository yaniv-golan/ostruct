# ostruct Example Validation System

This directory contains a comprehensive validation system for testing all examples in the `examples/` directory. The system automatically discovers README files, extracts ostruct commands, and validates them using a two-phase approach: dry-run first, then live execution.

## Dependencies

The validation system automatically manages its dependencies:

- **jq** - Required for JSON processing and report generation
- **timeout** - Used for command execution timeouts (usually pre-installed)
- **ostruct** - The main tool being validated (must be in PATH)

### Automatic Dependency Installation

The system includes automatic dependency management using `scripts/install/dependencies/ensure_jq.sh`:

- **Multi-platform support**: Linux (apt, yum, dnf, apk, pacman), macOS (brew, port)
- **Fallback strategies**: Package manager → binary download → Docker wrapper
- **Environment controls**: Set `OSTRUCT_SKIP_AUTO_INSTALL=1` to disable auto-install
- **Manual instructions**: Provides clear installation steps if auto-install fails

If you encounter dependency issues, you can:

```bash
# Check if jq is available
command -v jq

# Manually run the dependency installer
source scripts/install/dependencies/ensure_jq.sh

# Skip auto-install and handle manually
OSTRUCT_SKIP_AUTO_INSTALL=1 ./scripts/test/validate-examples.sh
```

## Quick Start

```bash
# Validate all examples (dependencies auto-installed)
./scripts/test/validate-examples.sh

# Validate with verbose output
./scripts/test/validate-examples.sh -v

# Validate specific example
./scripts/test/validate-examples.sh -e code-quality/code-review

# Only run dry-run validation
./scripts/test/validate-examples.sh -d

# Force refresh cache and validate
./scripts/test/validate-examples.sh -f
```

## How It Works

### 1. Discovery Phase

- Recursively scans `examples/` directory for README files
- Caches parsing results based on file modification times
- Only re-parses changed README files

### 2. LLM-Powered Command Extraction

**🔥 Dogfooding Approach**: The system uses **ostruct itself** with an LLM to intelligently extract commands from README files, making it more accurate and maintainable than regex-based parsing.

- **Intelligent Analysis**: Uses a Jinja2 template (`templates/extract_commands.j2`) to instruct an LLM to analyze README content
- **Smart Parsing**: Handles complex multi-line commands with backslash continuation
- **Context Understanding**: Distinguishes between executable commands and reference examples
- **Path Resolution**: Automatically resolves relative file paths based on example directory structure
- **Structured Output**: Returns JSON with normalized commands, dependencies, and metadata

#### How LLM Extraction Works

1. **Template Rendering**: Each README is processed through `extract_commands.j2` template
2. **LLM Analysis**: OpenAI model analyzes the README content and identifies ostruct commands
3. **Smart Categorization**: Commands are classified as "executable" or "reference"
4. **Normalization**: Multi-line commands are combined, paths are resolved
5. **Validation**: Dependencies and file requirements are identified
6. **Caching**: Results are cached based on README modification time

This approach is far superior to regex parsing because it understands context, handles complex formatting, and adapts to different README styles automatically.

### 3. Two-Phase Execution

#### Phase 1: Dry-Run Validation

- Adds `--dry-run` flag to every command
- Tests template rendering, schema validation, file dependencies
- Validates cost estimation and configuration
- **No API calls made** - fast and safe

#### Phase 2: Live Execution

- Only runs if dry-run passes
- Tests actual API integration
- Validates real output generation
- Checks for meaningful results

### 4. Intelligent Validation

- **Dry-run**: Expects cost info, validation messages, no errors
- **Live**: Expects meaningful output, structured data, API success
- Categorizes failures: API keys, model availability, dependencies, etc.

## Command Line Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable verbose output and detailed logging |
| `-f, --force-refresh` | Force refresh of cached README parsing results |
| `-d, --dry-run-only` | Only run dry-run validation, skip live execution |
| `-e, --example PATH` | Validate specific example (relative to examples/) |
| `-t, --timeout SECONDS` | Timeout for each command (default: 300) |
| `-h, --help` | Show help message |

## Output and Reporting

### Console Output

- Real-time progress with colored status indicators
- Summary statistics for examples and commands
- Lists of failed examples by category

### Detailed Reports

- **JSON Report**: `cache/validation_report.json` - Machine-readable results
- **HTML Report**: `cache/validation_report.html` - Human-readable (verbose mode)
- **Individual Results**: `cache/results/*.json` - Per-example detailed results
- **Execution Details**: `cache/execution_details/*.json` - Command outputs

### Example Output

```
==================================
  Example Validation Report
==================================

Duration: 45s
Timestamp: 2024-01-15T10:30:00Z

Examples Summary:
  Total Examples: 23
  ✅ Passed: 18
  ⚠️  Dry-run Failed: 3
  ❌ Live Failed: 2

Commands Summary:
  Total Commands: 67
  ✅ Passed: 58
  ⚠️  Dry-run Failed: 5
  ❌ Live Failed: 4
```

## Caching System

The validation system includes intelligent caching to avoid re-parsing unchanged README files:

- **Cache Location**: `cache/` directory
- **Cache Invalidation**: Based on README file modification time
- **Cache Contents**:
  - Parsed commands from each README
  - Execution results and details
  - Validation metadata

### Cache Management

```bash
# Force refresh all cached results
./scripts/test/validate-examples.sh -f

# Clear cache manually
rm -rf scripts/test/validate-examples/cache/*
```

## Configuration

The system can be configured via `config.yaml`:

- **Execution settings**: Timeouts, parallel execution, retries
- **Validation rules**: Strictness, output validation
- **Filtering**: Skip/include patterns for examples and commands
- **API settings**: Required/optional API keys
- **Output options**: Report formats, verbosity

## Integration with Release Process

This script is designed for pre-release validation:

1. **Add to Release Checklist**: Include validation step in `RELEASE_CHECKLIST.md`
2. **CI Integration**: Can be integrated into GitHub Actions
3. **API Key Management**: Supports both required and optional API keys
4. **Failure Categorization**: Distinguishes between different failure types

### Typical Release Workflow

```bash
# 1. Validate all examples
./scripts/test/validate-examples.sh

# 2. Fix any dry-run failures (template/config issues)
# ... fix issues ...

# 3. Set up API keys for live testing
export OPENAI_API_KEY="your-key"

# 4. Run live validation
./scripts/test/validate-examples.sh

# 5. Review results and fix any live failures
# ... fix API/model issues ...

# 6. Final validation
./scripts/test/validate-examples.sh -v
```

## Failure Categories

The system categorizes failures to help with debugging:

- **DRY_FAIL**: Template syntax, missing files, schema errors
- **LIVE_FAIL**: API authentication, model availability, network issues
- **API_KEY_MISSING**: Missing or invalid API keys
- **MODEL_UNAVAILABLE**: Requested model not available
- **MISSING_DEPENDENCIES**: Required files not found
- **EXECUTION_ERROR**: Other runtime errors

## Directory Structure

```
scripts/test/validate-examples/
├── lib/
│   ├── discovery.sh      # README discovery and caching
│   ├── extraction.sh     # LLM-powered command extraction
│   ├── execution.sh      # Two-phase command execution
│   ├── validation.sh     # Output validation logic
│   └── reporting.sh      # Results tracking and reporting
├── templates/
│   └── extract_commands.j2  # LLM prompt template for command extraction
├── schemas/
│   └── extracted_commands.json  # JSON schema for extraction output
├── cache/                # Cached results and reports
├── temp/                 # Temporary execution directories
├── config.yaml          # Configuration settings
└── README.md            # This file
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure script is executable: `chmod +x scripts/test/validate-examples.sh`
2. **Missing Dependencies**: Install required tools: `jq`, `timeout`
3. **API Key Issues**: Set required environment variables
4. **Cache Issues**: Use `-f` flag to force refresh

### Debug Mode

```bash
# Enable verbose logging
./scripts/test/validate-examples.sh -v

# Check specific example
./scripts/test/validate-examples.sh -v -e your-example

# Only dry-run for faster debugging
./scripts/test/validate-examples.sh -d -v -e your-example
```

### Manual Testing

```bash
# Test LLM-powered command extraction directly
ostruct run templates/extract_commands.j2 schemas/extracted_commands.json \
  --file readme_content examples/your-example/README.md \
  --var example_directory=examples/your-example \
  --var readme_file=examples/your-example/README.md

# Test extraction via library function
source scripts/test/validate-examples/lib/extraction.sh
extract_ostruct_commands examples/your-example/README.md

# Test single command
cd examples/your-example
ostruct your-template.j2 your-schema.json --dry-run
```

## Contributing

When adding new examples or modifying existing ones:

1. **Test Locally**: Run validation on your changes
2. **Update Documentation**: Ensure README accurately describes usage
3. **Check Dependencies**: Verify all required files are present
4. **Validate Commands**: Test both dry-run and live execution

The validation system will automatically discover and test new examples when added to the `examples/` directory.
