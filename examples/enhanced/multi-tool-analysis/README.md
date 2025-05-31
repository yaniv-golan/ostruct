# Multi-Tool Analysis Example

This example demonstrates the power of ostruct's enhanced multi-tool integration by combining Code Interpreter, File Search, and MCP servers for comprehensive analysis workflows.

## 🔒 Security & Data Privacy Notice

**⚠️ IMPORTANT**: This example uses Code Interpreter (`-fc`, `-dc`) and File Search (`-fs`, `-ds`) features that **upload your files to OpenAI's services** for processing.

**Before using with your data:**

- **Review data sensitivity** - Do not upload proprietary data, source code, or confidential information
- **Consider data types** - CSV files, logs, and code may contain sensitive business information
- **Check compliance requirements** - Verify your organization allows data uploads to external services
- **Use test data** - The provided examples use sample data for demonstration purposes

**For detailed information about data handling and security best practices**, see the [Security Overview](../../../docs/source/security/overview.rst) documentation.

## Overview

This example shows how to leverage multiple tools simultaneously for:

- **Code Interpreter**: Data analysis and Python execution
- **File Search**: Document retrieval and context search
- **MCP Server**: External repository documentation access
- **Explicit File Routing**: Optimized file processing

## Directory Structure

```
.
├── README.md              # This file
├── prompts/              # Analysis prompts
│   ├── system.txt        # Multi-tool expert system prompt
│   └── analysis.j2       # Comprehensive analysis template
├── schemas/              # Output structure
│   └── analysis_result.json
├── data/                 # Sample data files
│   ├── sales_data.csv    # Sales analytics data
│   ├── user_metrics.json # User behavior data
│   └── performance.log   # System performance logs
├── code/                 # Source code to analyze
│   ├── analytics.py      # Data analysis functions
│   ├── reports.py        # Report generation
│   └── utils.py          # Utility functions
├── docs/                 # Documentation files
│   ├── api_guide.md      # API documentation
│   ├── best_practices.md # Development guidelines
│   └── troubleshooting.md # Common issues
└── config/               # Configuration files
    ├── analysis.yaml     # Analysis configuration
    └── ostruct.yaml      # ostruct configuration
```

## Usage Examples

### 1. Basic Multi-Tool Analysis

Combine all tools for comprehensive analysis:

```bash
ostruct run prompts/analysis.j2 schemas/analysis_result.json \
  -fc sales_data data/sales_data.csv \
  -fc analytics_code code/analytics.py \
  -ds docs docs/ \
  -ft analysis_config config/analysis.yaml \
  --sys-file prompts/system.txt \
  --output-file comprehensive_analysis.json
```

### 2. Data Analysis with Documentation Context

Analyze data while searching for relevant documentation:

```bash
ostruct run prompts/analysis.j2 schemas/analysis_result.json \
  -dc data data/ \
  -ds docs docs/ \
  --sys-file prompts/system.txt \
  -V analysis_type=data_exploration \
  -V include_visualizations=true
```

### 3. Code Analysis with Repository Context

Analyze code using external repository documentation via MCP:

```bash
ostruct run prompts/analysis.j2 schemas/analysis_result.json \
  -dc code code/ \
  -ds docs docs/ \
  --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
  --sys-file prompts/system.txt \
  -V repo_owner=your-org \
  -V repo_name=your-project \
  -V analysis_type=code_quality
```

### 4. Performance Analysis with Execution

Execute performance analysis code while searching documentation:

```bash
ostruct run prompts/analysis.j2 schemas/analysis_result.json \
  -fc performance_log data/performance.log \
  -fc analytics_code code/analytics.py \
  -ft troubleshooting docs/troubleshooting.md \
  --sys-file prompts/system.txt \
  -V analysis_type=performance \
  -V execute_analysis=true \
  --output-file performance_report.json
```

### 5. Configuration-Driven Multi-Tool Workflow

Use persistent configuration for consistent multi-tool analysis:

```bash
# The config/ostruct.yaml file configures:
# - Model preferences
# - Tool-specific settings
# - MCP server shortcuts
# - Cost controls

ostruct --config config/ostruct.yaml run prompts/analysis.j2 schemas/analysis_result.json \
  -dc data data/ \
  -dc src src/ \
  -ds docs docs/ \
  -dc config config/ \
  --sys-file prompts/system.txt
```

## Configuration File Example

**config/ostruct.yaml**:

```yaml
models:
  default: gpt-4o

tools:
  code_interpreter:
    auto_download: true
    output_directory: "./analysis_output"
  file_search:
    max_results: 20

mcp:
  deepwiki: "https://mcp.deepwiki.com/sse"

operation:
  timeout_minutes: 45
  require_approval: never

limits:
  max_cost_per_run: 8.00
  warn_expensive_operations: true
```

## Benefits Demonstrated

### 1. Tool Synergy

Each tool contributes unique capabilities:

- **Code Interpreter**: Executes analysis scripts, generates visualizations
- **File Search**: Provides contextual documentation and best practices
- **MCP Server**: Accesses external repository knowledge
- **Template Files**: Handle configuration and metadata

### 2. Optimized Processing

Explicit file routing ensures:

- Data files go to Code Interpreter for analysis
- Documentation goes to File Search for context
- Configuration stays in template context
- No redundant processing

### 3. Cost Efficiency

Smart routing reduces costs by:

- Only processing files with appropriate tools
- Avoiding unnecessary uploads
- Using configuration to set limits
- Preventing token waste

### 4. Enhanced Results

Multi-tool integration provides:

- Executable analysis with real results
- Contextual documentation insights
- External knowledge integration
- Comprehensive reporting

## Use Cases

This pattern is ideal for:

1. **Data Science Workflows**: Analyze data while referencing methodology docs
2. **Code Quality Reviews**: Execute code while searching best practices
3. **Performance Analysis**: Run diagnostics while accessing troubleshooting guides
4. **Research Projects**: Combine analysis with literature search
5. **Compliance Audits**: Execute checks while referencing standards

## Migration from Traditional Usage

### Before (Traditional)

```bash
# All files processed the same way
ostruct run analysis.j2 schema.json \
  -dc all_files . \
  -R
```

### After (Enhanced)

```bash
# Optimized routing for better results
ostruct run analysis.j2 schema.json \
  -dc data data/ \
  -dc code code/ \
  -ds docs docs/ \
  -dc config config/
```

## CI/CD Integration

```yaml
name: Multi-Tool Analysis
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install ostruct
        run: pip install ostruct-cli

      - name: Multi-Tool Analysis
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          ostruct --config config/ostruct.yaml run prompts/analysis.j2 schemas/analysis_result.json \
            -dc data data/ \
            -dc src src/ \
            -ds docs docs/ \
            -dc config config/ \
            --progress-level none \
            --output-file analysis_results.json

      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: analysis-results
          path: |
            analysis_results.json
            analysis_output/
```

## Key Takeaways

1. **Explicit Routing**: Be specific about how files should be processed
2. **Tool Synergy**: Combine tools for capabilities no single tool provides
3. **Configuration**: Use persistent settings for consistent workflows
4. **Cost Management**: Route files appropriately to control costs
5. **Documentation Context**: Always include relevant docs for better analysis

This example demonstrates the transformative power of multi-tool integration, showing how ostruct's enhanced capabilities can create analysis workflows that were previously impossible with traditional approaches.
