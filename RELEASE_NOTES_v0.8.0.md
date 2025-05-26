# ostruct v0.8.0 Release Notes

🎉 **Major Release**: Multi-Tool Integration & OpenAI Responses API

---

## Executive Summary

ostruct v0.8.0 represents a major evolution, transforming from a simple structured output tool into a comprehensive AI workflow platform. This release integrates OpenAI's latest Responses API with native support for Code Interpreter, File Search, and MCP servers, while maintaining 100% backward compatibility.

## 🌟 Key Highlights

### Multi-Tool Integration
- **Code Interpreter**: Upload and execute Python code, analyze data files, generate visualizations
- **File Search**: Vector-based document search and retrieval from uploaded files
- **MCP Servers**: Connect to Model Context Protocol servers for extended functionality
- **Unified Workflow**: Combine all tools in a single command for comprehensive analysis

### Hybrid File Routing System
Three flexible syntax options for every file routing operation:

```bash
# Auto-naming (fastest for exploration)
ostruct run analysis.j2 schema.json -fc data.csv -fs docs.pdf

# Equals syntax (compact)
ostruct run analysis.j2 schema.json -fc dataset=data.csv -fs manual=docs.pdf

# Two-argument alias (best for reusable templates)
ostruct run analysis.j2 schema.json --fca dataset data.csv --fsa manual docs.pdf
```

### OpenAI Responses API Integration
- Direct integration with OpenAI Python SDK v1.81.0
- Removed openai-structured wrapper dependency
- Enhanced streaming support and error handling
- Future-proof architecture for upcoming OpenAI features

## 🚀 What's New

### Enhanced CLI Interface

**New File Routing Options**:
- `-ft`/`--fta`: Template files (available in template context only)
- `-fc`/`--fca`: Code Interpreter files (uploaded for execution + available in template)
- `-fs`/`--fsa`: File Search files (uploaded to vector store + available in template)
- `--file-for`: Advanced multi-tool routing syntax

**Perfect Tab Completion**: Two-argument alias syntax provides native shell tab completion for file paths.

**Organized Help System**: CLI help is now categorized with emoji indicators and clear examples.

### Configuration System

**YAML Configuration**:
```yaml
# ostruct.yaml
models:
  default: gpt-4o

tools:
  code_interpreter:
    auto_download: true
    output_directory: "./output"

mcp:
  deepwiki: "https://mcp.deepwiki.com/sse"
```

**Environment Variable Support**: Secure handling of API keys and server URLs.

### Progress & Cost Reporting

**Real-Time Progress**: Clear, user-friendly progress updates with emoji indicators.

**Cost Transparency**: Detailed breakdown of token usage and costs across all tools.

**Unattended Operation**: Full CI/CD compatibility with timeout controls and proper exit codes.

## 📊 Performance & Reliability

### Validated Performance Baselines
- **Basic Operations**: 1-2 seconds
- **Code Interpreter**: 10-16 seconds  
- **File Search**: 7-8 seconds
- **MCP Integration**: 5-6 seconds

### Enhanced Error Handling
- Actionable error messages with specific file routing guidance
- Context window errors suggest exact corrective commands
- Tool-specific error handling with retry logic

### Security & Validation
- Maintained all existing path validation and security controls
- Enhanced token limit validation with file type detection
- MCP server validation for unattended operation

## 🔄 Migration Guide

### 100% Backward Compatibility
All existing commands work unchanged:

```bash
# These continue to work exactly as before
ostruct run template.j2 schema.json -f config config.yaml
ostruct run template.j2 schema.json -d source src/ -R
ostruct run template.j2 schema.json -p logs "*.log"
```

### Error-Driven Migration
When existing commands exceed context limits, you'll get clear guidance:

```bash
❌ Error: Prompt exceeds model context window (150,000 tokens > 128,000 limit)
💡 Tip: Re-run with explicit routing:
   • Data file? Add -fc: ostruct run analysis.j2 schema.json -fc large_dataset.csv
   • Document file? Add -fs: ostruct run analysis.j2 schema.json -fs research_papers.pdf
```

### Progressive Enhancement
Add new capabilities to existing workflows incrementally:

```bash
# Start with existing workflow
ostruct run analysis.j2 schema.json -f config.yaml

# Add Code Interpreter for data analysis
ostruct run analysis.j2 schema.json -f config.yaml -fc data.csv

# Add File Search for documentation context
ostruct run analysis.j2 schema.json -f config.yaml -fc data.csv -fs docs.pdf
```

## 🛠️ Technical Improvements

### Architecture Changes
- **Explicit File Routing**: Clear tool-specific file handling with no magic behavior
- **Template Optimization**: Automatic prompt optimization for better LLM performance
- **Shared System Prompts**: New `include_system:` feature enables sharing common system prompt content across templates for consistency and maintainability
- **Model Registry**: Dynamic model management with enhanced capabilities checking
- **Security Manager**: Comprehensive path validation and access controls

### Dependencies
- **Added**: OpenAI Python SDK v1.81.0
- **Removed**: openai-structured wrapper
- **Updated**: Python 3.10+ requirement (dropped 3.9 support)
- **Enhanced**: Comprehensive test suite with proper mocking

### Testing & Validation
- **Probe Testing**: All features validated through comprehensive probe testing
- **Performance Baselines**: Established and validated performance expectations
- **Integration Tests**: End-to-end validation of all workflows
- **Mock Infrastructure**: Proper OpenAI SDK mocking for reliable testing

## 📚 Updated Documentation

### Comprehensive Examples
- **Updated Examples**: All existing examples updated with new syntax options
- **Enhanced Examples**: New multi-tool analysis demonstrations
- **Migration Examples**: Step-by-step adoption guides

### Reference Documentation
- **CLI Reference**: Complete documentation of all options and syntax
- **Migration Guide**: Detailed migration strategies and patterns
- **Automation Guide**: CI/CD best practices and patterns

## 🔮 Looking Forward

This release establishes a foundation for future AI workflow capabilities:

- **Agent Workflows**: Multi-step automated processes
- **Advanced MCP Integration**: Custom tool development
- **Enterprise Features**: Team management and usage analytics
- **Performance Optimization**: Continued optimization for large-scale usage

## 🙏 Credits

This release was made possible through:

- **Comprehensive Probe Testing**: 13 extensive validation tests ensuring production readiness
- **Community Feedback**: User input driving feature prioritization
- **OpenAI Responses API**: Enabling next-generation AI workflows

---

## Quick Start

1. **Install/Upgrade**:
   ```bash
   pip install --upgrade ostruct-cli
   ```

2. **Basic Multi-Tool Usage**:
   ```bash
   ostruct run analysis.j2 schema.json -fc data.csv -fs docs.pdf -ft config.yaml
   ```

3. **Explore Help**:
   ```bash
   ostruct run --help
   ostruct quick-ref
   ```

For detailed documentation, visit the [examples directory](examples/) and [CLI reference](docs/source/cli.md).

**Full backward compatibility maintained** - all existing commands work unchanged!