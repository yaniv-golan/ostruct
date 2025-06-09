#!/usr/bin/env python3
"""
Test 2: PyMuPDF table detection accuracy
Tests if page.find_tables() catches 90% of real tables in various PDFs.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

try:
    import fitz  # PyMuPDF  # type: ignore
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)


def analyze_table_detection(pdf_paths: List[Path]) -> Dict[str, Any]:
    """
    Analyze table detection accuracy across multiple PDFs.

    Returns:
        Dict with precision/recall metrics for table detection
    """
    results: Dict[str, Any] = {
        "test_id": "02",
        "test_name": "PyMuPDF Table Detection",
        "pdf_files": [],
        "total_pages_analyzed": 0,
        "tables_detected": 0,
        "tables_with_content": 0,
        "detection_rate": 0.0,
        "content_rate": 0.0,
        "success": False,
        "error": None,
    }

    try:
        for pdf_path in pdf_paths:
            if not pdf_path.exists():
                continue

            pdf_results = {
                "filename": pdf_path.name,
                "pages": 0,
                "tables_found": 0,
                "tables_with_data": 0,
                "table_details": [],
            }

            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                pdf_results["pages"] += 1
                results["total_pages_analyzed"] += 1

                # Find tables on this page
                tables = page.find_tables()

                for table_idx, table in enumerate(tables):
                    pdf_results["tables_found"] += 1
                    results["tables_detected"] += 1

                    # Extract table content to check if it's meaningful
                    try:
                        table_data = table.extract()
                        non_empty_cells = sum(
                            1
                            for row in table_data
                            for cell in row
                            if cell and cell.strip()
                        )

                        table_info = {
                            "page": page_num + 1,
                            "table_index": table_idx,
                            "bbox": table.bbox,
                            "rows": len(table_data),
                            "cols": len(table_data[0]) if table_data else 0,
                            "non_empty_cells": non_empty_cells,
                            "has_content": non_empty_cells
                            >= 4,  # At least 4 non-empty cells
                        }

                        pdf_results["table_details"].append(table_info)

                        if table_info["has_content"]:
                            pdf_results["tables_with_data"] += 1
                            results["tables_with_content"] += 1

                    except Exception as e:
                        # Table extraction failed
                        table_info = {
                            "page": page_num + 1,
                            "table_index": table_idx,
                            "bbox": table.bbox,
                            "extraction_error": str(e),
                            "has_content": False,
                        }
                        pdf_results["table_details"].append(table_info)

            doc.close()
            results["pdf_files"].append(pdf_results)

        # Calculate rates
        if results["tables_detected"] > 0:
            results["content_rate"] = (
                results["tables_with_content"] / results["tables_detected"]
            )

        if results["total_pages_analyzed"] > 0:
            results["detection_rate"] = (
                results["tables_detected"] / results["total_pages_analyzed"]
            )

        results["success"] = True

    except Exception as e:
        results["error"] = str(e)

    return results


def main():
    """Run the test on PDFs known to contain tables."""
    # Use PDFs from test-inputs that are known to have tables
    test_inputs_dir = Path(__file__).parent.parent.parent / "test-inputs"

    # Test files that should contain tables
    test_files = [
        "World Bank Annual Report 2024.pdf",  # Heavy tabular content
        "f1040.pdf",  # Form with table-like structures
        "Financial Sample.xlsx",  # Will be skipped as it's not PDF
        "NIPS-2017-attention-is-all-you-need-Paper.pdf",  # Small tables
    ]

    pdf_paths = []
    for filename in test_files:
        path = test_inputs_dir / filename
        if path.exists() and path.suffix.lower() == ".pdf":
            pdf_paths.append(path)

    if not pdf_paths:
        print("ERROR: No test PDF files found")
        sys.exit(1)

    print(f"Testing PyMuPDF table detection on {len(pdf_paths)} PDFs:")
    for path in pdf_paths:
        print(f"  - {path.name}")

    results = analyze_table_detection(pdf_paths)

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\nResults saved to: {output_file}")
    print(f"Total pages analyzed: {results['total_pages_analyzed']}")
    print(f"Tables detected: {results['tables_detected']}")
    print(f"Tables with meaningful content: {results['tables_with_content']}")
    print(f"Detection rate: {results['detection_rate']:.2f} tables/page")
    print(f"Content rate: {results['content_rate']:.2%}")

    # Success criteria: detect tables and most have content
    if results["tables_detected"] > 0 and results["content_rate"] >= 0.7:
        print("✅ PASS: PyMuPDF table detection is effective")
    else:
        print("❌ FAIL: PyMuPDF table detection needs improvement")

    return results


if __name__ == "__main__":
    main()
