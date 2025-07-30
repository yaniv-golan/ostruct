# Data Science Analysis with ostruct

> **Tools:** 🐍 Code Interpreter • 📊 Data Analysis • 📈 Visualization
> **Cost (approx.):** <$0.01 with gpt-4o-mini
> **Difficulty:** Beginner

## Overview

This example demonstrates how to use ostruct for data science workflows, combining automated data analysis with visualization generation. Perfect for analysts, data scientists, and researchers who need to quickly analyze datasets and generate insights.

**What you'll learn:**
- Load and analyze CSV data using AI-powered analysis
- Generate professional visualizations automatically
- Use Code Interpreter for statistical computations
- Integrate with Jupyter notebooks and Python workflows
- Create reproducible data analysis pipelines

## Use Cases

- **Financial Analysis**: Quarterly reports, revenue analysis, KPI dashboards
- **Research Data**: Experimental results, survey analysis, statistical summaries
- **Business Intelligence**: Sales performance, customer analytics, market trends
- **Academic Research**: Dataset exploration, preliminary analysis, visualization

## Quick Start

### Command Line Usage

```bash
# Fast validation (no API calls)
make test-dry

# Live API test (minimal cost)
make test-live

# Full execution with sample data
make run

# Custom model selection
make run MODEL=gpt-4o
```

### Jupyter Notebook Integration

```python
import subprocess
import json
import pandas as pd

# Run ostruct analysis from Jupyter
def analyze_data(csv_file, description="Dataset analysis"):
    """Analyze CSV data using ostruct and return structured results."""
    result = subprocess.run([
        'ostruct', 'run',
        'templates/main.j2', 'schemas/main.json',
        '--file', f'ci:sales', csv_file,
        '--enable-tool', 'code-interpreter',
        '--model', 'gpt-4o-mini'
    ], capture_output=True, text=True, cwd='examples/data-science/analysis')

    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        raise Exception(f"Analysis failed: {result.stderr}")

# Example usage in Jupyter
df = pd.read_csv('your_data.csv')
results = analyze_data('your_data.csv', 'Sales performance analysis')

print(f"Total Sales: ${results['summary']['total_sales']:,.2f}")
print(f"Average Price: ${results['summary']['average_price']:.2f}")
print(f"Products Analyzed: {results['summary']['product_count']}")
```

### Google Colab Integration

```python
# Install ostruct in Colab
!pip install ostruct-cli

# Set up API key (required)
import os
os.environ['OPENAI_API_KEY'] = 'your-api-key-here'

# Clone example templates
!git clone https://github.com/yaniv-golan/ostruct examples
%cd examples/data-science/analysis

# Run analysis
!ostruct run templates/main.j2 schemas/main.json \
  --file ci:sales data/sample.csv \
  --enable-tool code-interpreter \
  --model gpt-4o-mini
```

## Files Structure

| Path | Purpose |
|------|---------|
| `templates/main.j2` | AI-powered data analysis template with visualization generation |
| `schemas/main.json` | Validates analysis output: metrics, charts, data quality |
| `data/sample.csv` | Realistic sales data with date, product, quantity, price columns |
| `data/test_tiny.csv` | Minimal test dataset for quick validation |
| `notebooks/analysis_demo.py` | Python script demonstrating programmatic usage |
| `Makefile` | Standard commands: test-dry, test-live, run, clean |

## Expected Output

The analysis produces a comprehensive JSON report:

```json
{
  "summary": {
    "total_sales": 15750.50,
    "average_price": 125.75,
    "product_count": 4,
    "total_transactions": 48
  },
  "sales_by_product": {
    "Widget A": 5250.25,
    "Widget B": 4100.00,
    "Widget C": 3200.75,
    "Widget D": 3199.50
  },
  "chart_info": {
    "filename": "sales_by_product_chart.png",
    "description": "Bar chart showing total sales revenue by product",
    "chart_type": "bar"
  },
  "data_quality": {
    "rows_processed": 48,
    "missing_values": 0,
    "data_issues": []
  }
}
```

**Generated Artifacts:**
- Professional bar chart visualization (PNG)
- Statistical summary and insights
- Data quality assessment
- Downloadable chart files

## Customization

### Custom Data Analysis

Replace `data/sample.csv` with your dataset. Supported formats:
- CSV files with headers
- Excel files (.xlsx) - will be converted automatically
- TSV (tab-separated) files

### Different Chart Types

Modify `templates/main.j2` to request different visualizations:

```jinja
3. **Create visualization**
   - Generate a pie chart showing sales distribution by product  # Changed from bar chart
   - Include data labels showing percentages
   - Use a professional color scheme
   - Save as PNG with 300 DPI for publication quality
```

### Advanced Analysis

Extend the template for sophisticated analysis:

```jinja
5. **Advanced Analysis** (add to template)
   - Calculate correlation coefficients between variables
   - Identify seasonal trends and patterns
   - Perform outlier detection and flag anomalies
   - Generate statistical significance tests
   - Create interactive plotly charts with hover details
```

### Schema Customization

Extend `schemas/main.json` to capture additional metrics:

```json
{
  "advanced_metrics": {
    "type": "object",
    "properties": {
      "growth_rate": {"type": "number"},
      "seasonality_score": {"type": "number"},
      "outliers_detected": {"type": "integer"}
    }
  }
}
```

## Integration Patterns

### Multi-File Analysis

Process multiple datasets in sequence:

```bash
# Analyze quarterly data
for quarter in Q1 Q2 Q3 Q4; do
  ostruct run templates/main.j2 schemas/main.json \
    --file ci:sales "data/${quarter}_sales.csv" \
    --enable-tool code-interpreter \
    --output-file "results/${quarter}_analysis.json"
done
```

### Pipeline Integration

Combine with other ostruct tools:

```bash
# Step 1: Analyze local data
ostruct run templates/main.j2 schemas/main.json \
  --file ci:sales data/sales.csv \
  --enable-tool code-interpreter \
  --output-file step1_analysis.json

# Step 2: Enhance with web research
ostruct run templates/market_context.j2 schemas/enhanced.json \
  --file prompt:analysis step1_analysis.json \
  --enable-tool web-search \
  --web-query "industry sales trends 2024"
```

### Production Deployment

Automated analysis with error handling:

```python
import os
import sys
import subprocess
import logging
from pathlib import Path

def production_analysis(input_file, output_dir):
    """Production-ready data analysis with error handling."""
    try:
        # Validate input
        if not Path(input_file).exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Run analysis
        cmd = [
            'ostruct', 'run',
            'templates/main.j2', 'schemas/main.json',
            '--file', f'ci:sales', input_file,
            '--enable-tool', 'code-interpreter',
            '--model', 'gpt-4o-mini',
            '--output-file', f'{output_dir}/analysis.json'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logging.error(f"Analysis failed: {result.stderr}")
            return False

        logging.info("Analysis completed successfully")
        return True

    except Exception as e:
        logging.error(f"Production analysis error: {e}")
        return False
```

## Configuration

### Code Interpreter Settings

Customize download behavior with `ostruct.yaml`:

```yaml
tools:
  code_interpreter:
    auto_download: true
    output_directory: "./downloads"
    duplicate_outputs: "rename"
    output_validation: "strict"
    timeout_seconds: 300
```

### Model Selection

Choose appropriate models for different use cases:

- **gpt-4o-mini**: Fast, cost-effective for simple analysis
- **gpt-4o**: Balanced performance for complex datasets
- **o1-preview**: Advanced reasoning for statistical analysis
- **o1-mini**: Cost-effective reasoning for data insights

## Troubleshooting

### Common Issues

**"File too large" error:**
```bash
# Split large files or use sampling
head -1000 large_data.csv > sample_data.csv
```

**"Chart generation failed":**
- Check data has numerical columns for visualization
- Ensure data is properly formatted (no special characters)
- Try different chart types in template

**"Schema validation failed":**
- Review schema requirements vs. actual output
- Check for required fields in JSON structure
- Validate data types match schema expectations

### Performance Optimization

**Large datasets:**
- Use gpt-4o-mini for initial exploration
- Sample data for development/testing
- Process in chunks for very large files

**Cost optimization:**
- Start with test-dry validation
- Use smaller models for routine analysis
- Cache results for repeated analysis

## Next Steps

**Beginner:** Try with your own CSV data
**Intermediate:** Customize templates for domain-specific analysis
**Advanced:** Build automated analysis pipelines

**Related Examples:**
- `../notebooks/` - Jupyter integration patterns
- `../visualization/` - Advanced charting techniques
- `../integration/` - Multi-tool workflow examples

## Support

- [ostruct Documentation](https://ostruct.readthedocs.io/)
- [Data Science Integration Guide](https://ostruct.readthedocs.io/en/latest/user-guide/data_science_integration.html)
- [GitHub Issues](https://github.com/yaniv-golan/ostruct/issues) for bug reports
