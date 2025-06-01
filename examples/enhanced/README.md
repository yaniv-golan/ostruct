# Enhanced Multi-Tool Examples

This directory contains advanced examples showcasing ostruct's enhanced multi-tool capabilities, including Code Interpreter, File Search, and MCP server integration. These examples demonstrate the most sophisticated features and optimization patterns available in ostruct v0.8.0.

## 🚀 Key Features

### Multi-Tool Integration

- **Code Interpreter**: Execute Python code, analyze data, generate visualizations
- **File Search**: Vector-based document search and retrieval
- **MCP Server Integration**: Connect to external services and APIs
- **Explicit File Routing**: Optimize performance through targeted file processing

### Optimization Patterns

- **50-70% token reduction** through smart file routing
- **Cost-efficient processing** with tool-specific optimization
- **Configuration-driven workflows** for consistency
- **Template optimization** for enhanced prompt engineering

## Available Examples

### [PDF Semantic Diff](pdf-semantic-diff/)

**Advanced document analysis with Code Interpreter integration**

**Features:**

- Semantic comparison of PDF documents
- Change categorization (added, deleted, reworded, changed_in_meaning)
- Professional-grade analysis with specific examples
- Schema-validated JSON output

**Validation Results:**

- Successfully analyzed contract changes (payment $5,000→$7,500, React→React+TypeScript)
- Cost: $0.17 for comprehensive analysis
- Auto-enabled Code Interpreter with 2 files routed correctly

**Best For:** Contract analysis, document versioning, legal document review

### [Multi-Tool Analysis](multi-tool-analysis/)

**Comprehensive examples demonstrating all tool combinations**

**Features:**

- Code Interpreter + File Search + MCP integration
- Data analysis with documentation context
- External repository knowledge access
- Cost-optimized file routing patterns

**Best For:** Learning multi-tool patterns, comprehensive analysis workflows

### [CI/CD Automation](ci-cd-automation/)

**Enhanced automation patterns with cost controls and error handling**

**Features:**

- GitHub Actions, GitLab CI, Jenkins integration
- Automated cleanup and timeout controls
- Cost monitoring and budget enforcement
- Professional security and code review workflows

**Best For:** Production automation, CI/CD pipelines, enterprise workflows

### [Prompt Optimization](prompt-optimization/)

**Smart template design with tool-specific routing for maximum efficiency**

**Features:**

- Before/after optimization comparisons
- Token usage reduction techniques
- Configuration-driven cost controls
- Performance benchmarking tools

**Validation Results:**

- Demonstrates 50-70% token reduction through smart routing
- Cost-focused vs performance-focused configurations
- Template optimization best practices

**Best For:** Cost optimization, prompt engineering, performance tuning

## Usage Patterns

### Explicit File Routing

**Code Interpreter Files:**

```bash
# Upload for execution and analysis
-fc data_file data.csv
--fca dataset data.csv
```

**File Search Files:**

```bash
# Upload to vector store for search
-fs documentation docs.pdf
--fsa manual docs.pdf
```

**Template Files:**

```bash
# Available in template context only
-ft config config.yaml
--fta settings config.yaml
```

### Multi-Tool Combinations

**Comprehensive Analysis:**

```bash
ostruct run template.j2 schema.json \
  -fc data.csv \
  -fs documentation.pdf \
  -ft config.yaml \
  --mcp-server api@https://example.com/mcp
```

### Configuration-Driven Workflows

**ostruct.yaml example:**

```yaml
models:
  default: gpt-4o
tools:
  code_interpreter:
    auto_download: true
  file_search:
    max_results: 20
mcp:
  deepwiki: "https://mcp.deepwiki.com/sse"
operation:
  timeout_minutes: 45
limits:
  max_cost_per_run: 8.00
```

## Getting Started

1. **Start with PDF Semantic Diff** - Concrete example with live validation
2. **Explore Multi-Tool Analysis** - Learn integration patterns
3. **Review Prompt Optimization** - Understand efficiency techniques
4. **Implement CI/CD Automation** - Production-ready patterns

## Performance Benefits

### Token Reduction

- **Traditional approach**: All files in template context (high token usage)
- **Enhanced approach**: Tool-specific routing (50-70% reduction)

### Cost Optimization

- **Explicit routing**: Only process files with appropriate tools
- **Configuration management**: Set cost limits and warnings
- **Smart templates**: Reduced prompt complexity

### Quality Improvement

- **Tool synergy**: Each tool contributes unique capabilities
- **Contextual analysis**: Documentation + code + execution
- **Professional outputs**: Schema-validated, actionable results

## Contributing

When adding enhanced examples:

1. Demonstrate clear multi-tool benefits
2. Include performance comparisons (before/after)
3. Provide cost estimates and token usage
4. Show real-world applicability
5. Include configuration examples
6. Validate outputs with live testing
