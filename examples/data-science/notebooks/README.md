# Jupyter Notebook Integration with ostruct

> **Tools:** 📓 Jupyter • 🐍 Python • 🤖 AI Analysis
> **Cost (approx.):** <$0.05 for complete demo
> **Difficulty:** Intermediate

## Overview

This example demonstrates how to integrate ostruct with Jupyter notebooks for interactive data science workflows. Perfect for data scientists who want to combine AI-driven analysis with interactive Python environments.

**What you'll learn:**
- Run ostruct analysis directly from Jupyter cells
- Create reusable analysis functions for notebooks
- Build interactive data science workflows
- Integrate AI insights with pandas and visualization libraries
- Work seamlessly in Google Colab

## Quick Start

### 🚀 Try in Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yaniv-golan/ostruct/blob/main/examples/data-science/notebooks/ostruct_data_analysis.ipynb)

Click the badge above to open the interactive notebook in Google Colab. No local setup required!

### 💻 Local Jupyter Setup

```bash
# Install required packages
pip install ostruct-cli jupyter pandas matplotlib seaborn

# Start Jupyter
jupyter notebook ostruct_data_analysis.ipynb

# Or use JupyterLab
jupyter lab ostruct_data_analysis.ipynb
```

## Files

| File | Purpose |
|------|---------|
| `ostruct_data_analysis.ipynb` | Complete interactive Jupyter notebook with examples |
| `jupyter_integration.ost` | Self-executing template for advanced workflows |
| `README.md` | This documentation file |

## Notebook Examples

### 📊 Example 1: Basic Data Analysis
- Load CSV data into pandas
- Run ostruct analysis with Code Interpreter
- Display results with formatted summaries
- Visualize generated charts in notebook

### 🔄 Example 2: Multi-Tool Analysis Pipeline
- Combine Code Interpreter + Web Search
- Create enhanced templates with market context
- Use custom schemas for business intelligence
- Generate strategic recommendations

### 📈 Example 3: Interactive Data Science Workflow
- Dynamic template generation based on questions
- Real-time analysis of pandas DataFrames
- Custom visualization integration
- Error handling and validation

### 🚀 Example 4: Advanced Workflows
- Financial analysis with AI insights
- Business intelligence reports
- Multi-tool integration patterns
- Professional visualization generation

## Integration Patterns

### Basic ostruct Function

```python
import subprocess
import json

def analyze_data(csv_file, template='analysis.j2', schema='schema.json'):
    """Run ostruct analysis and return structured results."""
    result = subprocess.run([
        'ostruct', 'run', template, schema,
        '--file', f'ci:data', csv_file,
        '--enable-tool', 'code-interpreter',
        '--model', 'gpt-4o-mini'
    ], capture_output=True, text=True)

    return json.loads(result.stdout)

# Usage in notebook
results = analyze_data('sales_data.csv')
print(f"Total Revenue: ${results['summary']['total_sales']:,.2f}")
```

### Advanced Integration with pandas

```python
def jupyter_ostruct_analysis(df, question, model='gpt-4o-mini'):
    """Analyze pandas DataFrame with custom question."""
    # Save DataFrame temporarily
    temp_file = 'temp_analysis.csv'
    df.to_csv(temp_file, index=False)

    # Create dynamic template
    template = f"""
    Answer this question about the dataset: {question}

    Analyze the CSV data and provide insights in structured format.
    """

    # Run analysis
    results = run_ostruct_with_template(template, temp_file, model)

    # Cleanup
    os.unlink(temp_file)

    return results

# Interactive usage
df = pd.read_csv('data.csv')
insights = jupyter_ostruct_analysis(df, "What are the key sales drivers?")
```

## Google Colab Integration

### Setup Instructions

```python
# In first Colab cell
!pip install ostruct-cli

# Set up API key securely
import os
from google.colab import userdata
os.environ['OPENAI_API_KEY'] = userdata.get('OPENAI_API_KEY')

# Clone examples (if needed)
!git clone https://github.com/yaniv-golan/ostruct.git
%cd ostruct/examples/data-science/notebooks
```

### File Upload Integration

```python
# Upload files in Colab
from google.colab import files
uploaded = files.upload()

# Process uploaded files
for filename in uploaded.keys():
    results = analyze_data(filename)
    print(f"Analysis of {filename}:")
    display_results(results)
```

### Drive Integration

```python
# Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Access files from Drive
data_path = '/content/drive/MyDrive/data/sales_data.csv'
results = analyze_data(data_path)
```

## Best Practices

### 💡 Key Tips

- **Model Selection**: Use `gpt-4o-mini` for exploration, `gpt-4o` for complex analysis
- **API Key Safety**: Never commit API keys to notebooks or version control
- **Error Handling**: Always wrap ostruct calls in try/catch blocks
- **Cost Management**: Start with smaller models and sample data for development
- **Schema Design**: Focus on business questions, not just technical metrics

## Troubleshooting

### Common Issues

**"ostruct command not found":**
```bash
# Install ostruct
pip install ostruct-cli

# Verify installation
ostruct --version
```

**"API key not configured":**
```python
# Set API key in notebook
import os
os.environ['OPENAI_API_KEY'] = 'your-key-here'

# Or use secure input
import getpass
os.environ['OPENAI_API_KEY'] = getpass.getpass('API key: ')
```

**"Template not found":**
```python
# Use absolute paths
import os
template_path = os.path.abspath('../analysis/templates/main.j2')
```

**"JSON parsing error":**
```python
# Add error handling
try:
    results = json.loads(output)
except json.JSONDecodeError as e:
    print(f"Raw output: {output}")
    raise e
```

### Performance Issues

**Large file analysis:**
```python
# Sample large files
df_sample = df.sample(n=1000)  # Use 1000 rows for development
```

**Large datasets:**
```python
# Sample large files for development
df_sample = df.sample(n=1000)
analyze_data(df_sample)
```

## Next Steps

1. **Open the notebook** - Click the "Open in Colab" badge above
2. **Try your own data** - Upload CSV files and run analysis
3. **Customize templates** - Create templates for your specific domain
4. **Build workflows** - Integrate with your existing data science process

## Resources

- [Data Science Integration Guide](https://ostruct.readthedocs.io/en/latest/user-guide/data_science_integration.html)
- [ostruct Documentation](https://ostruct.readthedocs.io/)
- [GitHub Repository](https://github.com/yaniv-golan/ostruct)
