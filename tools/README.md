# ostruct Meta-Tools

This directory contains **meta-tools** - development tools that use ostruct internally to help with ostruct development, debugging, and optimization.

## 🔧 Available Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| [`template-analyzer/`](template-analyzer/) | Comprehensive analysis of ostruct templates and schemas for issues, best practices, and OpenAI compliance | `./template-analyzer/run.sh --help` |
| [`schema-generator/`](schema-generator/) | Automatically generate OpenAI-compliant JSON schemas from ostruct templates | `./schema-generator/run.sh --help` |

## 🚀 Quick Start

Each meta-tool is self-contained with its own `run.sh` script:

```bash
# Get help for any tool
./template-analyzer/run.sh --help
./schema-generator/run.sh --help

# Run analysis on your files
./template-analyzer/run.sh my_template.j2 my_schema.json
./schema-generator/run.sh my_template.j2

# Enable detailed logging
./template-analyzer/run.sh --verbose my_template.j2
./schema-generator/run.sh --debug my_template.j2
```

## 🛠️ Tool Features

### Template Analyzer

- **Comprehensive Analysis**: Syntax, security, performance, and best practices
- **OpenAI Compliance**: Real-time checking against current OpenAI structured output requirements
- **Interactive Reports**: HTML reports with filtering and detailed recommendations
- **ostruct Optimization**: Specialized analysis of ostruct-specific functions and filters
- **Cross-Analysis**: Template-schema alignment verification

### Schema Generator

- **Automated Generation**: AI-powered schema creation from template analysis
- **OpenAI Compliance**: Ensures compatibility with OpenAI's Structured Outputs requirements
- **Iterative Refinement**: Automatically improves schemas based on validation feedback
- **Multiple Validators**: Supports ajv-cli, jsonschema, and custom validators
- **Quality Assessment**: Provides confidence scores and improvement suggestions

## 📁 Tool Structure

Each meta-tool follows this general structure:

```
tools/tool-name/
├── README.md           # Tool documentation
├── run.sh              # Main interface script
├── src/                # ostruct templates and prompts
├── schemas/            # JSON schema definitions
├── test/               # Test/demo files
├── scripts/            # Helper scripts (optional)
└── log/                # Runtime logs
```

## 🔧 Development Standards

### Required Interface

All meta-tools must support:

- `./run.sh --help` - Show usage and options
- `./run.sh --verbose` - Enable verbose logging
- `./run.sh --debug` - Enable debug logging

### Documentation

- **README.md** - Purpose, installation, usage, troubleshooting
- **--help output** - Command-line interface documentation
- **Clear error messages** - Self-documenting behavior

### Dependencies

- **Automatic Setup**: Tools should auto-install dependencies when possible (e.g., `ensure_jq.sh`)
- **Clear Requirements**: Document any manual installation steps
- **Graceful Degradation**: Handle missing dependencies with helpful error messages

## 🔄 Adding New Meta-Tools

1. **Create tool directory**: `tools/my-new-tool/`
2. **Implement `run.sh`** with standard interface (`--help`, `--verbose`, `--debug`)
3. **Add comprehensive `README.md`** with installation and usage instructions
4. **Include test files** in `test/` directory
5. **Update this README** to list the new tool
6. **Test thoroughly** with various inputs and edge cases

## 🎯 Usage in Development Workflows

### Template Development

```bash
# Generate schema from template
./schema-generator/run.sh my_template.j2

# Analyze template for issues
./template-analyzer/run.sh my_template.j2 my_schema.json

# View interactive HTML report (auto-opens in browser)
```

### CI/CD Integration

```bash
# Add to your CI pipeline
cd tools/template-analyzer
./run.sh --verbose src/templates/*.j2

# Check exit codes for automation
if [ $? -eq 0 ]; then
  echo "✅ Template analysis passed"
else
  echo "❌ Template analysis failed"
  exit 1
fi
```

### Code Review Process

- Use template analyzer HTML reports for sharing analysis results
- Include schema generation in PR workflows
- Automate compliance checking with OpenAI requirements

## 🔗 Integration Points

These meta-tools integrate with the broader ostruct ecosystem:

- **ostruct CLI**: All tools use ostruct internally for AI processing
- **Documentation**: Referenced in main ostruct docs for template debugging and schema creation
- **Examples**: Generated schemas and analysis reports can be used in example development

This creates a complete development toolkit where meta-tools help build and maintain high-quality ostruct workflows.
