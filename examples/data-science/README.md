# Data Science Examples

> **Tools:** 🐍 Code Interpreter • 🔍 File Search • 🌐 Web Search • 📊 Multi-Tool Integration
> **Target Audience:** Data Scientists, Analysts, Researchers
> **Prerequisites:** Basic Python, Jupyter/Colab experience

## Overview

This directory contains comprehensive examples demonstrating ostruct's capabilities for data science workflows. These examples show how to leverage ostruct's multi-tool integration for tasks like data analysis, research synthesis, and visualization generation.

## Quick Start

Choose your path based on your experience level:

- **🚀 New to ostruct**: Start with `analysis/basic-dataframe-analysis/`
- **📓 Jupyter User**: Jump to `notebooks/ostruct_data_analysis.ipynb`
- **🔬 Research Focus**: Explore `integration/research-synthesis/`
- **📊 Visualization**: Check out `visualization/automated-charts/`

## Directory Structure

### 📓 `notebooks/`
Jupyter notebooks demonstrating ostruct integration patterns:
- `ostruct_data_analysis.ipynb` - Complete data analysis workflow
- `multi_tool_research.ipynb` - Combining Code Interpreter + File Search + Web Search
- `token_management.ipynb` - Handling large datasets efficiently

### 📊 `analysis/`
Data analysis examples with various complexity levels:
- `basic-dataframe-analysis/` - Simple CSV analysis and insights
- `financial-analysis/` - Business intelligence with market context
- `research-synthesis/` - Academic research automation

### 📈 `visualization/`
Automated visualization generation examples:
- `automated-charts/` - AI-generated matplotlib/seaborn visualizations
- `dashboard-generation/` - Dynamic dashboard creation
- `report-formatting/` - Structured analysis reports

### 🔗 `integration/`
Advanced multi-tool integration patterns:
- `research-synthesis/` - File Search + Web Search + Code Interpreter
- `market-intelligence/` - Business data + web research + analysis
- `academic-workflow/` - Literature review + data analysis + reporting

## Common Use Cases

### Business Intelligence
```bash
# Financial analysis with market context
cd analysis/financial-analysis/
make run

# Market research automation
cd integration/market-intelligence/
make run
```

### Academic Research
```bash
# Literature synthesis with data analysis
cd integration/research-synthesis/
make run

# Multi-source research workflow
cd notebooks/
jupyter notebook multi_tool_research.ipynb
```

### Data Analysis
```bash
# Basic DataFrame analysis
cd analysis/basic-dataframe-analysis/
make run

# Automated visualization generation
cd visualization/automated-charts/
make run
```

## Key Features Demonstrated

**🔧 Multi-Tool Orchestration**
- Combine Code Interpreter for Python execution
- Use File Search for document analysis
- Integrate Web Search for current information
- Route files appropriately (`ci:`, `fs:`, `prompt:`)

**📊 Schema-First Analysis**
- Structured JSON outputs for reproducible analysis
- Validated data structures for downstream processing
- Consistent reporting formats across workflows

**⚡ Performance Optimization**
- Token management for large datasets
- Smart sampling strategies
- Dry-run validation workflows
- Cost-effective model selection

**🔄 Notebook Integration**
- Jupyter magic commands for seamless execution
- DataFrame integration patterns
- Environment variable management
- Visualization pipeline integration

## Prerequisites

### Required Tools
```bash
# Install ostruct with enhanced file detection
pip install ostruct-cli[enhanced-detection]

# Set up environment
export OPENAI_API_KEY="your-key-here"
```

### Recommended Tools
```bash
# For notebook examples
pip install jupyter pandas matplotlib seaborn

# For visualization examples
pip install plotly dash streamlit
```

## Running Examples

Each example directory contains:
- `README.md` - Detailed example documentation
- `Makefile` - Standardized execution targets
- `run.sh` - Shell script for direct execution
- `templates/` - Jinja2 templates
- `schemas/` - JSON schema definitions
- `data/` - Sample datasets

### Standard Commands
```bash
# Quick validation (no API calls)
make test-dry

# Minimal live test
make test-live

# Full execution
make run

# Clean up generated files
make clean
```

## Cost Estimates

| Example Type | Estimated Cost | Model | Notes |
|--------------|----------------|-------|-------|
| Basic Analysis | <$0.01 | gpt-4o-mini | Simple CSV analysis |
| Multi-Tool Research | $0.05-0.15 | gpt-4o | File Search + Web Search |
| Visualization Generation | $0.02-0.05 | gpt-4o-mini | Chart generation |
| Financial Analysis | $0.10-0.25 | gpt-4o | Complex business logic |

*Estimates based on typical dataset sizes and current OpenAI pricing*

## Best Practices

### Data Preparation
- Use representative samples for large datasets
- Ensure data quality before analysis
- Consider token limits when designing workflows

### Template Design
- Focus on clear analysis objectives
- Provide context about data structure
- Include error handling patterns

### Schema Design
- Design schemas for downstream consumption
- Include descriptive field documentation
- Plan for extensibility and reuse

### Cost Management
- Use dry-run for development and testing
- Choose appropriate models for task complexity
- Monitor token usage with large datasets

## Troubleshooting

### Common Issues

**File Search Empty Results**
- Known OpenAI API issue
- Fallback to Code Interpreter parsing
- Use direct prompt inclusion for smaller documents

**Token Limit Errors**
- Implement smart sampling strategies
- Use chunking for large datasets
- Consider model selection (gpt-4o-mini vs gpt-4o)

**Binary File Access**
- Binary files cannot be accessed in templates
- Route to Code Interpreter (`ci:`) or user-data (`ud:`)
- Use metadata access (`.name`, `.path`, `.size`) when needed

### Getting Help

1. Check individual example READMEs for specific guidance
2. Review the [Data Science Integration Guide](../../docs/source/user-guide/data_science_integration.rst)
3. Consult the main [ostruct documentation](https://ostruct.readthedocs.io/)

## Contributing

When adding new examples:

1. Use `ostruct scaffold` to bootstrap consistent structure
2. Follow the established directory organization
3. Include comprehensive README with prerequisites and usage
4. Add appropriate cost estimates and troubleshooting guidance
5. Test both dry-run and live execution scenarios

---

**Next Steps**: Start with `analysis/basic-dataframe-analysis/` for a gentle introduction, or dive into `notebooks/ostruct_data_analysis.ipynb` for interactive exploration.
