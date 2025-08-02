#!/usr/bin/env python3
"""
Data Science Analysis Demo with ostruct

Demonstrates programmatic usage of ostruct for data analysis workflows.
Perfect for Jupyter notebooks, automated scripts, and production pipelines.

Usage:
    python analysis_demo.py [csv_file]
    python analysis_demo.py data/sample.csv
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def analyze_data(
    csv_file: str, description: str = "Dataset analysis"
) -> Dict[str, Any]:
    """
    Analyze CSV data using ostruct and return structured results.

    Args:
        csv_file: Path to CSV file to analyze
        description: Description of the analysis for context

    Returns:
        Dictionary containing analysis results with summary, charts, and data quality

    Raises:
        Exception: If analysis fails or ostruct command returns non-zero exit code
    """
    print(f"🔍 Analyzing {csv_file}: {description}")

    # Build ostruct command
    cmd = [
        "ostruct",
        "run",
        "templates/main.j2",
        "schemas/main.json",
        "--file",
        "ci:sales",
        csv_file,
        "--enable-tool",
        "code-interpreter",
        "--model",
        "gpt-4o-mini",
    ]

    try:
        # Run ostruct analysis
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,  # Run from analysis directory
        )

        if result.returncode == 0:
            # Parse JSON results
            analysis_results = json.loads(result.stdout)
            print("✅ Analysis completed successfully")
            return analysis_results
        else:
            raise Exception(f"Analysis failed: {result.stderr}")

    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse analysis results: {e}")
    except Exception as e:
        raise Exception(f"Analysis error: {e}")


def print_summary(results: Dict[str, Any]) -> None:
    """Print a formatted summary of analysis results."""
    print("\n📊 ANALYSIS SUMMARY")
    print("=" * 50)

    summary = results.get("summary", {})
    print(f"Total Sales:      ${summary.get('total_sales', 0):,.2f}")
    print(f"Average Price:    ${summary.get('average_price', 0):.2f}")
    print(f"Product Count:    {summary.get('product_count', 0)}")
    print(f"Transactions:     {summary.get('total_transactions', 0)}")

    print("\n📈 SALES BY PRODUCT")
    print("-" * 30)
    sales_by_product = results.get("sales_by_product", {})
    for product, sales in sorted(
        sales_by_product.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"{product:<15} ${sales:>10,.2f}")

    print("\n📋 DATA QUALITY")
    print("-" * 20)
    quality = results.get("data_quality", {})
    print(f"Rows Processed:   {quality.get('rows_processed', 0)}")
    print(f"Missing Values:   {quality.get('missing_values', 0)}")

    issues = quality.get("data_issues", [])
    if issues:
        print("Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("No data quality issues detected")

    print("\n🎨 VISUALIZATION")
    print("-" * 20)
    chart_info = results.get("chart_info", {})
    print(f"Chart Type:       {chart_info.get('chart_type', 'N/A')}")
    print(f"Filename:         {chart_info.get('filename', 'N/A')}")
    print(f"Description:      {chart_info.get('description', 'N/A')}")


def validate_csv_file(csv_file: str) -> bool:
    """
    Validate that the CSV file exists and is readable.

    Args:
        csv_file: Path to CSV file

    Returns:
        True if valid, False otherwise
    """
    if not Path(csv_file).exists():
        print(f"❌ Error: File '{csv_file}' not found")
        return False

    try:
        # Quick validation by reading first few rows
        df = pd.read_csv(csv_file, nrows=5)
        print(f"✅ Valid CSV file with {len(df.columns)} columns")
        print(f"   Columns: {', '.join(df.columns.tolist())}")
        return True
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return False


def main():
    """Main function demonstrating ostruct data analysis."""
    print("🚀 ostruct Data Science Analysis Demo")
    print("=" * 50)

    # Default to sample data if no file specified
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "data/sample.csv"

    # Validate input file
    if not validate_csv_file(csv_file):
        sys.exit(1)

    try:
        # Run analysis
        results = analyze_data(csv_file, "Sales performance analysis")

        # Display results
        print_summary(results)

        # Save results for further processing
        output_file = "analysis_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")

        print("\n🎯 Next Steps:")
        print("  1. Review generated chart file in downloads/ directory")
        print("  2. Customize templates/main.j2 for domain-specific analysis")
        print("  3. Extend schemas/main.json for additional metrics")
        print("  4. Use results JSON for further processing or reporting")

    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# Additional utility functions for Jupyter/production use


def batch_analyze(
    csv_files: list, output_dir: str = "batch_results"
) -> Dict[str, Any]:
    """
    Analyze multiple CSV files in batch.

    Args:
        csv_files: List of CSV file paths
        output_dir: Directory to save individual results

    Returns:
        Dictionary with combined results from all files
    """
    Path(output_dir).mkdir(exist_ok=True)
    batch_results = {}

    for csv_file in csv_files:
        try:
            results = analyze_data(csv_file, f"Batch analysis: {csv_file}")

            # Save individual results
            filename = Path(csv_file).stem
            output_file = Path(output_dir) / f"{filename}_analysis.json"
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)

            batch_results[csv_file] = results

        except Exception as e:
            print(f"⚠️ Failed to analyze {csv_file}: {e}")
            batch_results[csv_file] = {"error": str(e)}

    return batch_results


def production_analysis(
    input_file: str, output_dir: str, config: Optional[Dict] = None
) -> bool:
    """
    Production-ready data analysis with comprehensive error handling.

    Args:
        input_file: Path to input CSV file
        output_dir: Directory for output files
        config: Optional configuration overrides

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Validate input
        if not Path(input_file).exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Configure model and settings
        model = config.get("model", "gpt-4.1") if config else "gpt-4.1"

        # Build command with configuration
        cmd = [
            "ostruct",
            "run",
            "templates/main.j2",
            "schemas/main.json",
            "--file",
            f"ci:sales",
            input_file,
            "--enable-tool",
            "code-interpreter",
            "--model",
            model,
            "--output-file",
            f"{output_dir}/analysis.json",
        ]

        # Run analysis
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Production analysis failed: {result.stderr}")
            return False

        print("✅ Production analysis completed successfully")
        return True

    except Exception as e:
        print(f"❌ Production analysis error: {e}")
        return False


# Jupyter notebook helpers


def jupyter_quick_analysis(
    df: pd.DataFrame, filename: str = "temp_data.csv"
) -> Dict[str, Any]:
    """
    Quick analysis helper for Jupyter notebooks.

    Args:
        df: Pandas DataFrame to analyze
        filename: Temporary filename for CSV export

    Returns:
        Analysis results dictionary
    """
    # Save DataFrame to temporary CSV
    df.to_csv(filename, index=False)

    try:
        # Run analysis
        results = analyze_data(filename, "Jupyter notebook analysis")

        # Clean up temporary file
        Path(filename).unlink()

        return results

    except Exception as e:
        # Clean up temporary file on error
        if Path(filename).exists():
            Path(filename).unlink()
        raise e
