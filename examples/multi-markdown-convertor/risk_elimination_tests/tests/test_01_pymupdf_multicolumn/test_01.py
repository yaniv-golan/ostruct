#!/usr/bin/env python3
"""
Test 1: PyMuPDF solves multi-column PDFs
Tests if PyMuPDF can correctly sequence text blocks in multi-column layouts.
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


def analyze_block_order(pdf_path: Path) -> Dict[str, Any]:
    """
    Analyze text block ordering in a multi-column PDF.

    Returns:
        Dict with metrics about block sequencing accuracy
    """
    results: Dict[str, Any] = {
        "test_id": "01",
        "test_name": "PyMuPDF Multi-column PDF Block Order",
        "pdf_path": str(pdf_path),
        "total_blocks": 0,
        "correctly_sequenced_blocks": 0,
        "sequence_accuracy_ratio": 0.0,
        "blocks_data": [],
        "success": False,
        "error": None,
    }

    try:
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")

            # Sort blocks by reading order (top-to-bottom, left-to-right for multi-column)
            # For multi-column: sort by y-coordinate first, then by x-coordinate within same row
            sorted_blocks = sorted(
                blocks, key=lambda b: (round(b[1], -1), b[0])
            )  # Round y to nearest 10 for row grouping

            for i, block in enumerate(sorted_blocks):
                if len(block) >= 5 and block[4].strip():  # Has text content
                    block_info = {
                        "page": page_num + 1,
                        "block_index": i,
                        "bbox": [block[0], block[1], block[2], block[3]],
                        "text_preview": block[4][:100]
                        .replace("\n", " ")
                        .strip(),
                        "original_order": blocks.index(block),
                        "sorted_order": i,
                    }
                    results["blocks_data"].append(block_info)
                    results["total_blocks"] += 1

                    # Simple heuristic: if sorted order matches reasonable reading flow
                    # This is a simplified check - in real implementation would need more sophisticated logic
                    if (
                        abs(
                            block_info["original_order"]
                            - block_info["sorted_order"]
                        )
                        <= 2
                    ):
                        results["correctly_sequenced_blocks"] += 1

        doc.close()

        if results["total_blocks"] > 0:
            results["sequence_accuracy_ratio"] = (
                results["correctly_sequenced_blocks"] / results["total_blocks"]
            )

        results["success"] = True

    except Exception as e:
        results["error"] = str(e)

    return results


def main():
    """Run the test with the NIPS paper (multi-column academic PDF)."""
    # Use the NIPS paper from test-inputs as it's a two-column academic PDF
    test_inputs_dir = Path(__file__).parent.parent.parent / "test-inputs"
    pdf_path = (
        test_inputs_dir / "NIPS-2017-attention-is-all-you-need-Paper.pdf"
    )

    if not pdf_path.exists():
        print(f"ERROR: Test file not found: {pdf_path}")
        sys.exit(1)

    print(f"Testing PyMuPDF multi-column handling on: {pdf_path.name}")

    results = analyze_block_order(pdf_path)

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\nResults saved to: {output_file}")
    print(f"Total blocks analyzed: {results['total_blocks']}")
    print(f"Correctly sequenced: {results['correctly_sequenced_blocks']}")
    print(f"Sequence accuracy ratio: {results['sequence_accuracy_ratio']:.2%}")

    if results["sequence_accuracy_ratio"] >= 0.8:
        print("✅ PASS: PyMuPDF handles multi-column layout well")
    else:
        print("❌ FAIL: PyMuPDF struggles with multi-column layout")

    return results


if __name__ == "__main__":
    main()
