# Multi-Tool Data Analysis Integration

> **Tools:** 🐍 Code Interpreter • 🔍 File Search • 🌐 Web Search
> **Cost (approx.):** $0.10-0.25 per complete analysis
> **Difficulty:** Advanced

## Overview

This example demonstrates advanced multi-tool orchestration for comprehensive business intelligence analysis. By combining Code Interpreter, File Search, and Web Search, you can create powerful workflows that analyze internal data, search through documentation, and incorporate real-time market intelligence.

**What you'll learn:**
- Orchestrate multiple ostruct tools in a single analysis
- Design templates that gracefully handle missing data sources
- Create production-ready error handling and fallback strategies
- Build step-by-step workflows for complex business scenarios
- Implement troubleshooting and debugging techniques

## Use Cases

- **Market Entry Analysis**: Combine financial models, regulatory research, and market intelligence
- **Competitive Intelligence**: Analyze internal performance + competitor research + market trends
- **Risk Assessment**: Financial data + regulatory documents + current market conditions
- **Product Strategy**: Sales data + customer feedback documents + market research
- **Investment Analysis**: Financial statements + industry reports + real-time market data

## Quick Start

```bash
# Fast validation (no API calls)
make test-dry

# Live test with minimal data (low cost)
make test-live

# Full multi-tool business intelligence analysis
make run

# Custom scenario with your data
make run DATA_FILE=your_data.csv DOCS_DIR=your_docs/ MARKET_QUERY="your market research query"
```

## Example Scenarios

This directory contains three complete multi-tool analysis scenarios:

### 1. Market Entry Analysis (`market-entry/`)
**Scenario**: Tech startup evaluating expansion into European markets

**Data Sources:**
- **Code Interpreter**: Financial projections and market sizing models
- **File Search**: Regulatory compliance documents and market research reports
- **Web Search**: Current market conditions and competitor activities

**Workflow:**
1. Analyze financial readiness and investment requirements
2. Search regulatory documents for compliance requirements
3. Research current market conditions and competitive landscape
4. Generate comprehensive go/no-go recommendation with risk assessment

### 2. Competitive Intelligence (`competitive-intel/`)
**Scenario**: SaaS company performing quarterly competitive analysis

**Data Sources:**
- **Code Interpreter**: Internal sales and customer data analysis
- **File Search**: Previous competitive analysis reports and customer feedback
- **Web Search**: Competitor pricing, features, and market positioning

**Workflow:**
1. Analyze internal performance trends and customer satisfaction
2. Search historical reports for benchmark comparisons
3. Research current competitor strategies and market positioning
4. Generate strategic recommendations with priority rankings

### 3. Investment Due Diligence (`investment-analysis/`)
**Scenario**: Investment firm evaluating acquisition target

**Data Sources:**
- **Code Interpreter**: Financial statement analysis and valuation models
- **File Search**: Due diligence documents and industry reports
- **Web Search**: Market outlook and regulatory changes

**Workflow:**
1. Perform comprehensive financial analysis and modeling
2. Search due diligence documents for risk factors and opportunities
3. Research market conditions and industry outlook
4. Generate investment recommendation with confidence intervals

## Architecture Pattern

All examples follow a consistent multi-tool orchestration pattern:

```bash
# Standard multi-tool command structure
ostruct run template.j2 schema.json \
  --file ci:data financial_data.csv \
  --file fs:docs documents/ \
  --enable-tool web-search \
  --web-query "market research query" \
  --model gpt-4o
```

### Template Structure

```jinja
# Multi-Tool Analysis Template Pattern

## Data Analysis (Code Interpreter)
{% if financial_data is defined %}
**Internal Data Analysis:**
{{ financial_data.content }}
{% else %}
No internal data provided. Focus on external research and documentation.
{% endif %}

## Document Research (File Search)
{% if documents is defined %}
**Document Analysis:**
{% for doc in documents %}
**{{ doc.name }}:** {{ doc.content if doc.size < 50000 else "Large document - analyze key sections" }}
{% endfor %}
{% else %}
No documents provided. Skip document analysis phase.
{% endif %}

## Market Intelligence (Web Search)
{% if web_search_results %}
**Current Market Research:**
{{ web_search_results }}
{% else %}
Web search not available. Base analysis on internal data and documents only.
{% endif %}

## Synthesis Requirements
Combine insights from all available sources:
1. **Data-Driven Insights**: Statistical analysis and trends
2. **Document-Based Evidence**: Regulatory, historical, and contextual information
3. **Market Intelligence**: Current conditions and competitive landscape
4. **Integrated Recommendations**: Actionable insights based on all sources
```

### Schema Design

```json
{
  "type": "object",
  "properties": {
    "data_analysis": {
      "type": "object",
      "properties": {
        "key_metrics": {"type": "object"},
        "trends_identified": {"type": "array"},
        "data_quality_assessment": {"type": "string"}
      }
    },
    "document_insights": {
      "type": "object",
      "properties": {
        "key_findings": {"type": "array"},
        "risk_factors": {"type": "array"},
        "regulatory_considerations": {"type": "array"}
      }
    },
    "market_intelligence": {
      "type": "object",
      "properties": {
        "market_conditions": {"type": "string"},
        "competitive_landscape": {"type": "array"},
        "market_opportunities": {"type": "array"}
      }
    },
    "integrated_analysis": {
      "type": "object",
      "properties": {
        "executive_summary": {"type": "string"},
        "recommendations": {"type": "array"},
        "confidence_level": {"type": "string"},
        "next_steps": {"type": "array"}
      }
    }
  },
  "required": ["integrated_analysis"]
}
```

## Error Handling & Troubleshooting

### Common Issues and Solutions

**Tool Not Available:**
```jinja
{% if web_search_results %}
{{ web_search_results }}
{% else %}
<!-- Web search unavailable - proceed with available data -->
Based on internal data and documents only (web search unavailable).
{% endif %}
```

**File Access Errors:**
```jinja
{% for doc in documents %}
{% if doc.size < 100000 %}
{{ doc.content }}
{% else %}
**{{ doc.name }}** ({{ doc.size }} bytes): File too large, analyze key sections only.
{% endif %}
{% endfor %}
```

**Data Quality Issues:**
```jinja
## Data Validation
1. Verify data completeness and quality
2. Flag any anomalies or missing values
3. Document assumptions made during analysis
4. Provide confidence levels for all insights
```

### Debugging Strategies

**Incremental Testing:**
```bash
# Test each tool individually
ostruct run template.j2 schema.json --file ci:data data.csv --dry-run
ostruct run template.j2 schema.json --file fs:docs docs/ --dry-run
ostruct run template.j2 schema.json --enable-tool web-search --dry-run
```

**Verbose Output:**
```bash
# Enable detailed logging
ostruct run template.j2 schema.json \
  --file ci:data data.csv \
  --file fs:docs docs/ \
  --enable-tool web-search \
  --verbose \
  --model gpt-4o
```

**Component Isolation:**
```bash
# Test with minimal viable data
ostruct run template.j2 schema.json \
  --file ci:test minimal_test.csv \
  --enable-tool web-search \
  --web-query "simple test query"
```

## Production Deployment

### Orchestration Script

```python
#!/usr/bin/env python3
"""
Production multi-tool analysis orchestrator.
Handles errors, retries, and result aggregation.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

class MultiToolAnalyzer:
    def __init__(self, config_file: str = "analysis_config.json"):
        self.config = self.load_config(config_file)
        self.setup_logging()

    def run_analysis(self, scenario: str, data_sources: Dict) -> Dict:
        """Run complete multi-tool analysis with error handling."""
        try:
            # Validate inputs
            self.validate_inputs(data_sources)

            # Build command
            cmd = self.build_command(scenario, data_sources)

            # Execute with retry logic
            result = self.execute_with_retry(cmd)

            # Validate output
            return self.validate_output(result)

        except Exception as e:
            logging.error(f"Analysis failed: {e}")
            return self.generate_error_report(e)

    def validate_inputs(self, data_sources: Dict):
        """Validate all input sources before analysis."""
        if 'data_file' in data_sources:
            if not Path(data_sources['data_file']).exists():
                raise FileNotFoundError(f"Data file not found: {data_sources['data_file']}")

        if 'docs_dir' in data_sources:
            docs_path = Path(data_sources['docs_dir'])
            if not docs_path.exists() or not any(docs_path.iterdir()):
                logging.warning(f"Documents directory empty: {docs_path}")

    def execute_with_retry(self, cmd: List[str], max_retries: int = 3) -> Dict:
        """Execute command with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return json.loads(result.stdout)
            except subprocess.CalledProcessError as e:
                if attempt == max_retries - 1:
                    raise
                logging.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
```

### Configuration Management

```json
{
  "scenarios": {
    "market_entry": {
      "template": "templates/market_entry.j2",
      "schema": "schemas/market_entry.json",
      "default_model": "gpt-4o",
      "timeout": 300
    },
    "competitive_intel": {
      "template": "templates/competitive_intel.j2",
      "schema": "schemas/competitive_intel.json",
      "default_model": "gpt-4o",
      "timeout": 240
    }
  },
  "error_handling": {
    "retry_attempts": 3,
    "fallback_model": "gpt-4o-mini",
    "enable_graceful_degradation": true
  }
}
```

## Performance Optimization

### Cost Management

- **Model Selection**: Use gpt-4o for complex analysis, gpt-4o-mini for simpler tasks
- **Data Sampling**: Use representative samples for development and testing
- **Caching**: Store intermediate results to avoid re-processing
- **Incremental Analysis**: Process data in stages for large datasets

### Speed Optimization

- **Parallel Processing**: Run independent analysis components concurrently
- **Template Optimization**: Minimize token usage while maintaining quality
- **Smart Routing**: Route files to appropriate tools based on content type
- **Result Streaming**: Process results as they become available

## Best Practices

### Template Design

1. **Graceful Degradation**: Handle missing data sources elegantly
2. **Clear Instructions**: Provide specific analysis requirements for each tool
3. **Error Resilience**: Include fallback strategies for each component
4. **Quality Gates**: Validate data quality and flag assumptions

### Schema Design

1. **Modular Structure**: Separate results from each tool for clarity
2. **Confidence Indicators**: Include certainty levels for all insights
3. **Extensible Format**: Allow for additional data sources and analysis types
4. **Business Alignment**: Structure output for decision-making needs

### Operational Excellence

1. **Monitoring**: Track success rates, costs, and performance metrics
2. **Alerting**: Set up notifications for failures and quality issues
3. **Documentation**: Maintain runbooks for common scenarios and troubleshooting
4. **Testing**: Regular validation of templates and schemas with production data

## Next Steps

**Beginner**: Start with one example scenario using your own data
**Intermediate**: Adapt templates for your specific business domain
**Advanced**: Build automated orchestration pipelines for production use

**Related Examples:**
- `../analysis/` - Single-tool data analysis patterns
- `../notebooks/` - Interactive development and testing
- `../visualization/` - Advanced charting and dashboard creation

## Support

- [Multi-Tool Integration Guide](https://ostruct.readthedocs.io/en/latest/user-guide/data_science_integration.html#multi-tool-analysis-pipeline)
- [Tool Integration Documentation](https://ostruct.readthedocs.io/en/latest/user-guide/tool_integration.html)
- [GitHub Issues](https://github.com/yaniv-golan/ostruct/issues) for bug reports
