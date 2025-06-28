# Data Analysis Examples

This directory contains examples for comprehensive data processing, multi-tool analysis workflows, and advanced analytical patterns using ostruct CLI with integrated tool capabilities.

## Available Examples

### [Multi-Tool Analysis](multi-tool-analysis/)

**Comprehensive multi-tool analysis patterns** - Code Interpreter + File Search + MCP integration for complex data workflows:

**Features:**

- **Complete Integration**: Code Interpreter for data processing + File Search for context + Web Search for current data + MCP for external knowledge
- **Configuration-Driven**: Flexible analysis types controlled through configuration variables
- **Scalable Patterns**: Handles diverse data types and analysis requirements
- **Professional Output**: Structured results with comprehensive analysis and recommendations

**Validation Results:**

- **Versatility**: Supports data exploration, code analysis, research workflows, and hybrid approaches
- **Efficiency**: Optimized tool usage reduces processing time by 40-60%
- **Quality**: Multi-tool integration provides richer insights than single-tool approaches
- **Integration Ready**: Works seamlessly with data science pipelines and analytical workflows

**Best For:** Data exploration, research analysis, code analysis with context, complex multi-step analytical workflows

## Key Features

### Comprehensive Tool Integration

All data analysis examples leverage the full spectrum of ostruct's capabilities:

- **Code Interpreter**: Execute analysis code, process datasets, generate visualizations
- **File Search**: Search documentation, research papers, and contextual references
- **Template Variables**: Handle configuration and metadata efficiently
- **MCP Integration**: Access external knowledge bases and specialized analysis tools

### Analytical Versatility

**Multi-Domain Support:**

- Data science and statistical analysis
- Code analysis with business context
- Research workflows with literature integration
- Hybrid analytical approaches combining multiple data sources

### Usage Patterns

**Comprehensive Data Exploration:**

```bash
# Complete data analysis with context
ostruct run prompts/analysis.j2 schemas/analysis_result.json \
  --file ci:dataset dataset.csv \
  --file ci:analysis_code analysis_code.py \
  --file fs:documentation documentation/ \
  -V analysis_type=data_exploration
```

**Code Analysis with Context:**

```bash
# Code analysis with documentation context
ostruct run prompts/analysis.j2 schemas/analysis_result.json \
  --file ci:codebase codebase/ \
  --file fs:docs docs/ \
  --file fs:readme README.md \
  -V analysis_type=code_analysis
```

**Research-Enhanced Analysis:**

```bash
# Analysis with external knowledge integration
ostruct run prompts/analysis.j2 schemas/analysis_result.json \
  --file ci:research_data research_data.csv \
  --file fs:literature literature/ \
  --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
  -V analysis_type=research_analysis
```

**Multi-Source Integration:**

```bash
# Complex workflow with multiple data sources
ostruct run prompts/analysis.j2 schemas/analysis_result.json \
  --file ci:sales_data sales_data.csv \
  --file ci:customer_data customer_data.csv \
  --file ci:analysis_scripts analysis_scripts/ \
  --file fs:business_docs business_docs/ \
  -V analysis_type=business_intelligence
```

## Getting Started

1. Navigate to the specific example directory (e.g., `multi-tool-analysis/`)
2. Review the README.md for configuration options and analysis types
3. Start with simple data exploration examples
4. Expand to multi-tool integration as needed
5. Customize templates and schemas for your analytical requirements

## Analysis Patterns

### 1. Data Exploration Workflows

- Automated statistical analysis and data profiling
- Interactive data visualization and reporting
- Pattern detection and anomaly identification
- Data quality assessment and validation

### 2. Research Integration

- Literature search and context integration
- External knowledge base integration
- Research paper analysis and synthesis
- Evidence-based analytical conclusions

### 3. Code Analysis with Context

- Code quality analysis with business context
- Architecture analysis with documentation reference
- Performance analysis with benchmarking data
- Security analysis with threat intelligence

### 4. Multi-Source Analytics

- Cross-platform data integration
- Hybrid analytical workflows
- Real-time and batch processing patterns
- Complex data pipeline orchestration

## Configuration-Driven Analysis

### Analysis Type Configuration

**Data Exploration:**

```yaml
analysis:
  type: data_exploration
  focus: statistical_analysis
  include_visualizations: true
  depth: comprehensive
```

**Research Analysis:**

```yaml
analysis:
  type: research_analysis
  literature_integration: true
  external_knowledge: enabled
  citation_tracking: true
```

**Business Intelligence:**

```yaml
analysis:
  type: business_intelligence
  stakeholder_focus: executive
  include_recommendations: true
  format: dashboard_ready
```

### Tool Integration Settings

**Balanced Configuration:**

```yaml
tools:
  code_interpreter:
    auto_download: true
    output_directory: "./analysis_output"
    duplicate_outputs: "rename"  # Handle duplicate files
    output_validation: "basic"   # Validate downloads
  file_search:
    max_results: 20
    include_metadata: true
mcp:
  servers:
    deepwiki: "https://mcp.deepwiki.com/sse"
```

**Performance-Optimized:**

```yaml
tools:
  code_interpreter:
    auto_download: true
    parallel_processing: true
    duplicate_outputs: "overwrite"  # Fast processing
    output_validation: "off"        # Skip validation for speed
  file_search:
    max_results: 30
    deep_search: enabled
operation:
  timeout_minutes: 45
  retry_attempts: 2
```

## Advanced Analytical Techniques

### Multi-Tool Orchestration

**Sequential Processing:**

1. Code Interpreter processes raw data
2. File Search provides contextual information
3. MCP integration adds external knowledge
4. Template synthesis combines all insights

**Parallel Processing:**

- Simultaneous tool operation for efficiency
- Independent analysis streams
- Result synthesis and correlation
- Comprehensive reporting integration

### Quality Assurance

**Validation Patterns:**

- Cross-verification between tool outputs
- Consistency checking across data sources
- Statistical validation of analytical results
- Documentation compliance and traceability

### Scalability Considerations

**Large Dataset Handling:**

- Chunked processing for memory efficiency
- Incremental analysis with progress tracking
- Resource optimization and cost management
- Parallel processing where applicable

**High-Volume Workflows:**

- Batch processing patterns
- Queue management for analytical jobs
- Resource pooling and optimization
- Cost-effective scaling strategies

## Best Practices

### 1. Data Preparation

- Clean and validate data before analysis
- Document data sources and transformations
- Implement data quality checks
- Consider privacy and security requirements

### 2. Tool Selection

- Use Code Interpreter for computational analysis
- Use File Search for contextual information
- Use MCP integration for external knowledge
- Combine tools strategically for comprehensive insights

### 3. Result Management

- Structure outputs for downstream consumption
- Implement versioning for analytical results
- Document methodology and assumptions
- Provide clear recommendations and next steps

### 4. Performance Optimization

- Use explicit file routing for efficiency
- Configure appropriate timeouts and limits
- Monitor resource usage and costs
- Cache intermediate results when beneficial

## Integration Patterns

### Data Science Pipelines

- Jupyter notebook integration
- MLOps workflow integration
- Model training and validation
- Feature engineering and selection

### Business Intelligence

- Dashboard integration
- Report automation
- KPI tracking and monitoring
- Stakeholder communication

### Research Workflows

- Literature review automation
- Hypothesis testing and validation
- Reproducible research patterns
- Publication-ready output generation

## Contributing

When adding new data analysis examples:

1. Include diverse analysis types and use cases
2. Provide comprehensive test datasets with known characteristics
3. Document expected analytical outcomes and validation criteria
4. Include configuration examples for different analytical approaches
5. Follow established patterns for multi-tool integration
6. Ensure examples demonstrate scalable analytical techniques

## Future Examples

This category is designed to accommodate additional analytical patterns:

- **Machine Learning Integration**: ML model training and evaluation workflows
- **Real-Time Analytics**: Streaming data analysis and monitoring
- **Geospatial Analysis**: Location-based data analysis and visualization
- **Time Series Analysis**: Temporal data analysis and forecasting
- **Natural Language Processing**: Text analysis and linguistic processing
- **Computer Vision**: Image and video analysis workflows
- **Financial Analysis**: Quantitative finance and risk analysis patterns
- **Scientific Computing**: Research-grade computational analysis
