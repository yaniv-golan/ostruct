# Market Entry Analysis - Multi-Tool Integration

> **Tools:** 🐍 Code Interpreter • 🔍 File Search • 🌐 Web Search
> **Cost (approx.):** $0.15-0.25 per complete analysis
> **Difficulty:** Advanced

## Overview

This example demonstrates a complete multi-tool business intelligence workflow for market entry analysis. It combines financial modeling (Code Interpreter), regulatory research (File Search), and real-time market intelligence (Web Search) to provide comprehensive strategic recommendations.

**Business Scenario:** A growing tech startup evaluating expansion into European markets needs a data-driven analysis combining internal financial projections, regulatory compliance requirements, and current market conditions.

## What You'll Learn

- **Multi-Tool Orchestration**: Seamlessly combine three ostruct tools in a single analysis
- **Error Handling**: Graceful degradation when data sources are unavailable
- **Business Intelligence**: Structure analysis output for executive decision-making
- **Production Patterns**: Real-world templates and schemas for strategic analysis
- **Cost Optimization**: Balance analysis depth with API costs

## Quick Start

```bash
# Fast validation (no API calls)
make test-dry

# Minimal live test (low cost ~$0.05)
make test-live

# Complete multi-tool analysis (~$0.15-0.25)
make run

# Analysis without web search (lower cost ~$0.08)
make run-minimal
```

## Example Output

The analysis produces a comprehensive strategic recommendation:

```json
{
  "executive_summary": "European market entry presents a strong opportunity with projected 3-year ROI of 145% despite regulatory complexity requiring €75K initial compliance investment.",
  "strategic_recommendation": {
    "decision": "conditional_go",
    "confidence_level": "high",
    "key_rationale": [
      "Large addressable market (€450M) with 22% growth rate",
      "Competitive gaps in AI-first solutions create differentiation opportunity",
      "Strong financial projections show break-even within 18 months",
      "Regulatory complexity manageable with proper local partnerships"
    ]
  },
  "implementation_roadmap": {
    "phases": [
      {
        "phase": "Market Validation & Compliance Setup",
        "duration": "3-6 months",
        "budget": 125000,
        "key_activities": [
          "Complete GDPR compliance implementation",
          "Establish Netherlands BV entity",
          "Validate product-market fit with pilot customers"
        ]
      }
    ],
    "total_timeline": "18-24 months to full market presence"
  }
}
```

## Data Sources

### Financial Data (Code Interpreter)
- **File**: `data/financial_projections.csv`
- **Content**: 3-year financial scenarios (conservative/optimistic/pessimistic)
- **Analysis**: Investment requirements, ROI projections, break-even analysis
- **Outputs**: Professional financial charts and risk-adjusted returns

### Regulatory Documents (File Search)
- **Directory**: `docs/`
- **Content**: EU regulatory requirements, compliance costs, tax implications
- **Analysis**: GDPR compliance, corporate registration, employment law
- **Outputs**: Compliance timeline and cost estimates

### Market Intelligence (Web Search)
- **Query**: "European SaaS market entry analysis 2024 competitive landscape"
- **Analysis**: Market size, competitive landscape, customer segments
- **Outputs**: Market positioning and competitive differentiation strategies

## Multi-Tool Template Pattern

The template demonstrates graceful handling of missing data sources:

```jinja
## Financial Analysis (Code Interpreter)
{% if financial_data is defined %}
**Internal Financial Data Analysis:**
{{ financial_data.content }}
[Detailed financial analysis requirements...]
{% else %}
**No Financial Data Available**
Proceed with qualitative analysis based on regulatory research and market intelligence.
{% endif %}

## Regulatory Research (File Search)
{% if regulatory_docs is defined %}
**Regulatory Environment Analysis:**
{% for doc in regulatory_docs %}
{{ doc.content if doc.size < 75000 else "Analyze key sections" }}
{% endfor %}
{% else %}
**No Regulatory Documents Available**
Recommend conducting regulatory due diligence research.
{% endif %}

## Market Intelligence (Web Search)
{% if web_search_results %}
**Current Market Research:**
{{ web_search_results }}
[Market analysis requirements...]
{% else %}
**Limited Market Intelligence Available**
Base recommendations on available data sources.
{% endif %}
```

## Advanced Features

### Error Handling and Fallbacks

**Template Resilience:**
- Handles missing data sources gracefully
- Provides alternative analysis paths
- Documents data quality limitations
- Includes confidence levels for recommendations

**Cost Management:**
- Configurable model selection (gpt-4o vs gpt-4o-mini)
- Optional web search for cost optimization
- File size limits prevent excessive token usage
- Dry-run validation before expensive API calls

### Production Deployment

**Configuration Management:**
```bash
# Environment-specific configuration
export MARKET_ENTRY_MODEL="gpt-4o"
export MARKET_ENTRY_WEB_QUERY="Custom market research query"
export MARKET_ENTRY_MAX_DOCS_SIZE="100000"
```

**Automated Orchestration:**
```python
import subprocess
import json
from pathlib import Path

def run_market_analysis(data_file, docs_dir, web_query, model="gpt-4o"):
    """Production market entry analysis with error handling."""

    cmd = [
        'ostruct', 'run',
        'templates/market_entry_analysis.j2',
        'schemas/market_entry_schema.json',
        '--file', f'ci:financial_data', data_file,
        '--file', f'fs:regulatory_docs', docs_dir,
        '--enable-tool', 'web-search',
        '--web-query', web_query,
        '--model', model,
        '--output-file', 'analysis_results.json'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        with open('analysis_results.json', 'r') as f:
            return json.load(f)

    except subprocess.CalledProcessError as e:
        return {
            "error": "Analysis failed",
            "details": e.stderr,
            "recommendation": "Review input data and try again"
        }

# Usage
results = run_market_analysis(
    data_file="financial_projections.csv",
    docs_dir="regulatory_docs/",
    web_query="European SaaS market trends 2024"
)
```

## Customization

### Adapt for Your Market
```bash
# Analyze different geographic markets
make run WEB_QUERY="Asian market entry analysis fintech 2024"

# Different industry verticals
make run WEB_QUERY="Healthcare software market analysis Europe regulatory requirements"

# Custom financial models
make run DATA_FILE=your_financial_model.csv DOCS_DIR=your_regulatory_docs/
```

### Schema Customization

Extend the schema for industry-specific requirements:

```json
{
  "industry_specific_analysis": {
    "type": "object",
    "properties": {
      "regulatory_licenses": {"type": "array"},
      "industry_certifications": {"type": "array"},
      "specialized_compliance": {"type": "object"}
    }
  }
}
```

### Template Extensions

Add industry-specific analysis sections:

```jinja
## Industry-Specific Requirements
{% if industry == "fintech" %}
### Financial Services Regulations
- PSD2 compliance requirements
- MiFID II obligations
- Capital adequacy requirements
{% elif industry == "healthcare" %}
### Healthcare Regulations
- Medical device regulations
- Patient data protection (beyond GDPR)
- Clinical trial requirements
{% endif %}
```

## Troubleshooting

### Common Issues

**"No documents found" error:**
```bash
# Check document directory structure
ls -la docs/
# Ensure documents are readable text files
file docs/*
```

**"Web search failed" error:**
```bash
# Test web search separately
make debug-web
# Try simplified query
make run WEB_QUERY="European market analysis"
```

**"Financial data parsing error":**
```bash
# Validate CSV format
head -5 data/financial_projections.csv
# Test financial analysis only
make debug-financial
```

### Performance Optimization

**Reduce Costs:**
- Use `gpt-4o-mini` for development: `make run MODEL=gpt-4o-mini`
- Skip web search for testing: `make run-minimal`
- Limit document size in template: `{% if doc.size < 50000 %}`

**Improve Speed:**
- Cache web search results for development
- Use smaller document sets for testing
- Pre-validate data formats before analysis

## Integration Patterns

### CI/CD Pipeline Integration

```yaml
# .github/workflows/market-analysis.yml
name: Automated Market Analysis
on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly Monday 9 AM

jobs:
  market-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Market Analysis
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cd examples/data-science/integration/market-entry
          make run MODEL=gpt-4o-mini
      - name: Archive Results
        uses: actions/upload-artifact@v3
        with:
          name: market-analysis-results
          path: market_entry_analysis_results.json
```

### Slack Integration

```python
import json
import requests

def post_analysis_to_slack(results_file, webhook_url):
    """Post analysis summary to Slack channel."""

    with open(results_file, 'r') as f:
        results = json.load(f)

    decision = results['strategic_recommendation']['decision']
    confidence = results['strategic_recommendation']['confidence_level']
    summary = results['executive_summary']

    message = {
        "text": f"Market Entry Analysis Complete",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Decision:* {decision.upper()} (Confidence: {confidence})\n*Summary:* {summary}"
                }
            }
        ]
    }

    requests.post(webhook_url, json=message)
```

## Next Steps

**Beginner:** Run with the provided sample data to understand the workflow
**Intermediate:** Adapt templates and schemas for your industry and market
**Advanced:** Build automated analysis pipelines with monitoring and alerting

**Related Examples:**
- `../competitive-intel/` - Competitive analysis workflows
- `../investment-analysis/` - Due diligence and investment workflows
- `../../notebooks/` - Interactive development and testing patterns

## Support

- [Multi-Tool Integration Guide](https://ostruct.readthedocs.io/en/latest/user-guide/data_science_integration.html)
- [Business Intelligence Patterns](https://ostruct.readthedocs.io/en/latest/cookbook/business-intelligence.html)
- [GitHub Issues](https://github.com/yaniv-golan/ostruct/issues) for bug reports
