#!/usr/bin/env python3
"""
Test 10: xlwings chart export keeps transparent bg
Export chart as PNG, embed in MD renderer
"""

import json
import sys
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


def create_test_xlsx_with_chart() -> Path:
    """Create a test XLSX file with a chart."""
    try:
        from openpyxl import Workbook
        from openpyxl.chart import BarChart, Reference

        # Create workbook with data
        wb = Workbook()
        ws = wb.active
        ws.title = "Chart Data"

        # Add sample data
        data = [
            ["Category", "Values"],
            ["A", 10],
            ["B", 20],
            ["C", 15],
            ["D", 25],
        ]

        for row in data:
            ws.append(row)

        # Create chart
        chart = BarChart()
        chart.title = "Sample Chart"
        chart.x_axis.title = "Categories"
        chart.y_axis.title = "Values"

        # Add data to chart
        data_ref = Reference(ws, min_col=2, min_row=1, max_row=5, max_col=2)
        cats_ref = Reference(ws, min_col=1, min_row=2, max_row=5, max_col=1)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)

        # Add chart to worksheet
        ws.add_chart(chart, "E5")

        # Save to temp file
        temp_file = Path(tempfile.mktemp(suffix=".xlsx"))
        wb.save(str(temp_file))
        return temp_file

    except ImportError:
        # Fallback: use existing XLSX file if available
        test_inputs_dir = Path(__file__).parent.parent.parent / "test-inputs"
        xlsx_files = list(test_inputs_dir.glob("*.xlsx"))
        if xlsx_files:
            return xlsx_files[0]
        else:
            raise RuntimeError(
                "openpyxl not available and no test XLSX files found"
            )


def export_chart_with_xlwings(xlsx_path: Path) -> Dict[str, Any]:
    """Export chart using xlwings and check transparency."""
    try:
        import xlwings as xw
        from PIL import Image
        import numpy as np

        analysis = {
            "xlwings_available": True,
            "chart_exported": False,
            "png_path": None,
            "has_transparency": False,
            "alpha_channel_info": {},
        }

        # Try to open Excel file with xlwings
        try:
            app = xw.App(visible=False)
            wb = app.books.open(str(xlsx_path))
            ws = wb.sheets[0]

            # Look for charts
            charts = ws.charts
            if len(charts) > 0:
                chart = charts[0]

                # Export chart as PNG
                png_path = Path(tempfile.mktemp(suffix=".png"))
                chart.api.Export(str(png_path), "PNG")

                analysis["chart_exported"] = True
                analysis["png_path"] = str(png_path)

                # Check if PNG has alpha channel
                if png_path.exists():
                    img = Image.open(png_path)
                    analysis["alpha_channel_info"] = {
                        "mode": img.mode,
                        "has_alpha": img.mode in ("RGBA", "LA"),
                        "size": img.size,
                    }

                    if img.mode in ("RGBA", "LA"):
                        # Check if alpha channel has transparency
                        img_array = np.array(img)
                        if img.mode == "RGBA":
                            alpha_channel = img_array[:, :, 3]
                            unique_alpha = np.unique(alpha_channel)
                            analysis["has_transparency"] = (
                                len(unique_alpha) > 1 or unique_alpha[0] < 255
                            )
                        analysis["alpha_channel_info"][
                            "unique_alpha_values"
                        ] = (
                            len(unique_alpha)
                            if "unique_alpha" in locals()
                            else 0
                        )

                # Clean up
                png_path.unlink() if png_path.exists() else None

            wb.close()
            app.quit()

        except Exception as e:
            analysis["xlwings_error"] = str(e)

        return analysis

    except ImportError as e:
        return {
            "error": f"Required libraries not available: {e}",
            "xlwings_available": False,
            "chart_exported": False,
            "png_path": None,
            "has_transparency": False,
            "alpha_channel_info": {},
        }
    except Exception as e:
        return {
            "error": str(e),
            "xlwings_available": False,
            "chart_exported": False,
            "png_path": None,
            "has_transparency": False,
            "alpha_channel_info": {},
        }


def run_test() -> Dict[str, Any]:
    """
    Run test 10: Check if xlwings chart export keeps transparent background.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "10",
        "test_name": "xlwings chart export keeps transparent bg",
        "test_case": "Export chart as PNG, embed in MD renderer",
        "success": False,
        "error": None,
        "details": {},
    }

    try:
        print(f"Test 10: xlwings chart export keeps transparent bg")
        print(f"Test case: Export chart as PNG, embed in MD renderer")

        # Create or find test XLSX with chart
        print("Creating test XLSX with chart...")
        xlsx_path = create_test_xlsx_with_chart()
        results["details"]["xlsx_path"] = str(xlsx_path)

        # Export chart with xlwings
        print("Exporting chart with xlwings...")
        analysis = export_chart_with_xlwings(xlsx_path)
        results["details"]["export_analysis"] = analysis

        # Determine success
        if "error" in analysis:
            results["error"] = analysis["error"]
            results["success"] = False
            results["details"]["result"] = f"FAIL: {analysis['error']}"
            print(f"❌ FAIL: {analysis['error']}")
        else:
            if analysis["chart_exported"]:
                if analysis["has_transparency"]:
                    results["success"] = True
                    results["details"]["result"] = (
                        "PASS: Chart exported with transparency preserved"
                    )
                    print(
                        "✅ PASS: Chart exported with transparency preserved"
                    )
                else:
                    results["success"] = False
                    results["details"]["result"] = (
                        "FAIL: Chart exported but no transparency detected"
                    )
                    print(
                        "❌ FAIL: Chart exported but no transparency detected"
                    )

                # Show alpha channel info
                alpha_info = analysis["alpha_channel_info"]
                print(f"   Image mode: {alpha_info.get('mode', 'unknown')}")
                print(
                    f"   Has alpha channel: {alpha_info.get('has_alpha', False)}"
                )
            else:
                results["success"] = False
                results["details"]["result"] = "FAIL: Could not export chart"
                print("❌ FAIL: Could not export chart")

        # Clean up temp file
        if xlsx_path.name.startswith("tmp"):
            try:
                xlsx_path.unlink()
            except:
                pass

    except Exception as e:
        results["error"] = str(e)
        results["details"]["exception"] = str(e)
        print(f"❌ Test failed with error: {e}")

    return results


def main():
    """Run the test."""
    results = run_test()

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_file}")
    return results


if __name__ == "__main__":
    main()
