# Code Interpreter • Hello World

> **Tools:** 🐍 Code Interpreter
> **Cost (approx.):** <$0.01 with gpt-4o-mini

## 1. Description

Demonstrates basic Code Interpreter usage by loading a CSV file, computing totals and averages, generating a bar chart visualization, and saving the results. This is the simplest possible example to get started with ostruct's Code Interpreter integration.

## 2. Prerequisites

```bash
# No special dependencies required
```

## 3. Quick Start

```bash
# Fast validation (no API calls)
./run.sh --test-dry-run

# Live API test (minimal cost)
./run.sh --test-live

# Full execution
./run.sh

# With custom model
./run.sh --model gpt-4o
```

## 4. Files

| Path | Purpose |
|------|---------|
| `templates/main.j2` | Primary template that analyzes CSV data and creates visualizations |
| `schemas/main.json` | Validates the analysis output structure with totals, averages, and chart info |
| `data/sample.csv` | Sample sales data with columns: date, product, quantity, price |
| `data/test_tiny.csv` | Minimal test data for quick validation |

## 5. Expected Output

The example produces:

- **JSON analysis** with computed totals and averages
- **Bar chart image** showing sales by product
- **Summary statistics** for the dataset

Example output structure:

```json
{
  "summary": {
    "total_sales": 15750.50,
    "average_price": 125.75,
    "product_count": 4
  },
  "chart_info": {
    "filename": "sales_chart.png",
    "description": "Bar chart showing sales by product"
  }
}
```

## 6. Customization

- **Different datasets**: Replace `data/sample.csv` with your own CSV data
- **Chart types**: Modify the template to request different visualization types
- **Analysis metrics**: Add custom calculations in the template

## 7. Configuration

You can customize download behavior by creating an `ostruct.yaml` file:

```yaml
tools:
  code_interpreter:
    auto_download: true
    output_directory: "./downloads"
    duplicate_outputs: "rename"  # Generate unique names for duplicate files
    output_validation: "basic"   # Validate downloaded files
```

Or use CLI flags for one-off customization:

```bash
# Generate unique names for duplicate files
./run.sh --ci-duplicate-outputs rename

# Save to custom directory
./run.sh --ci-download-dir ./results

# Skip files that already exist
./run.sh --ci-duplicate-outputs skip
```

## 8. Clean-Up

Generated chart files are saved to the downloads/ directory and can be safely deleted after viewing.
