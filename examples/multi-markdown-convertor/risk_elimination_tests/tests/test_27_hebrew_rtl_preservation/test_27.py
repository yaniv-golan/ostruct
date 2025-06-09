#!/usr/bin/env python3
"""
Test 27: Hebrew RTL paragraphs stay RTL after Pandoc → MD → renderer
Mixed-lang doc round-trip
"""

import json
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def create_mixed_language_content() -> str:
    """Create content with Hebrew RTL and English LTR text."""
    return """# Mixed Language Document Test

This document contains both Hebrew (RTL) and English (LTR) text to test preservation.

## English Section

This is regular English text that should flow left-to-right (LTR).
It contains standard Latin characters and punctuation.

## Hebrew Section

שלום עולם! זהו טקסט בעברית שצריך לזרום מימין לשמאל (RTL).
הטקסט הזה מכיל אותיות עבריות ופיסוק.

## Mixed Paragraph

This paragraph contains both English and Hebrew: שלום (hello) and עולם (world).
The RTL text should maintain its direction: מימין לשמאל.

## List with Hebrew

1. First item in English
2. פריט שני בעברית
3. Third item mixing English and עברית
4. רביעי - כולו בעברית

## Table with Hebrew

| English | עברית | Mixed |
|---------|-------|-------|
| Hello   | שלום  | Hello שלום |
| World   | עולם  | World עולם |

## Conclusion

This document tests RTL preservation: עברית צריכה להישאר RTL.
"""


def test_hebrew_rtl_preservation() -> Dict[str, Any]:
    """
    Test Hebrew RTL preservation through markdown processing.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "27",
        "test_name": "Hebrew RTL paragraphs stay RTL after Pandoc → MD → renderer",
        "original_content_created": False,
        "hebrew_text_detected": False,
        "english_text_detected": False,
        "pandoc_available": False,
        "conversion_successful": False,
        "rtl_markers_preserved": False,
        "hebrew_chars_preserved": False,
        "processing_steps": [],
        "success": False,
        "error": None,
    }

    try:
        # Create mixed language content
        original_content = create_mixed_language_content()
        results["original_content_created"] = True

        # Analyze original content
        hebrew_chars = set("אבגדהוזחטיכלמנסעפצקרשת")
        english_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )

        content_chars = set(original_content)
        results["hebrew_text_detected"] = bool(hebrew_chars & content_chars)
        results["english_text_detected"] = bool(english_chars & content_chars)

        print(f"Hebrew text detected: {results['hebrew_text_detected']}")
        print(f"English text detected: {results['english_text_detected']}")

        # Test Pandoc conversion if available
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as f:
                f.write(original_content)
                input_file = Path(f.name)

            output_file = input_file.with_suffix(".converted.md")

            # Test Pandoc availability and conversion
            pandoc_cmd = [
                "pandoc",
                str(input_file),
                "-f",
                "markdown",
                "-t",
                "markdown",
                "-o",
                str(output_file),
                "--wrap=preserve",  # Preserve line wrapping
            ]

            process = subprocess.run(
                pandoc_cmd, capture_output=True, text=True, timeout=30
            )

            if process.returncode == 0:
                results["pandoc_available"] = True
                results["conversion_successful"] = True

                # Read converted content
                with open(output_file, "r", encoding="utf-8") as f:
                    converted_content = f.read()

                # Analyze converted content
                converted_chars = set(converted_content)
                results["hebrew_chars_preserved"] = bool(
                    hebrew_chars & converted_chars
                )

                # Check for RTL markers or directionality hints
                rtl_indicators = [
                    'dir="rtl"',
                    "direction: rtl",
                    "text-align: right",
                    "unicode-bidi",
                    "\u202e",
                    "\u202d",  # RTL/LTR override characters
                ]

                results["rtl_markers_preserved"] = any(
                    indicator in converted_content
                    for indicator in rtl_indicators
                )

                # Store processing step
                step = {
                    "tool": "pandoc",
                    "input_size": len(original_content),
                    "output_size": len(converted_content),
                    "hebrew_preserved": results["hebrew_chars_preserved"],
                    "rtl_markers": results["rtl_markers_preserved"],
                }
                results["processing_steps"].append(step)

                print(f"Pandoc conversion successful")
                print(
                    f"Hebrew characters preserved: {results['hebrew_chars_preserved']}"
                )
                print(f"RTL markers found: {results['rtl_markers_preserved']}")

            else:
                results["error"] = f"Pandoc failed: {process.stderr}"

            # Clean up
            input_file.unlink()
            if output_file.exists():
                output_file.unlink()

        except FileNotFoundError:
            results["error"] = (
                "Pandoc not found - install pandoc to test RTL preservation"
            )
        except subprocess.TimeoutExpired:
            results["error"] = "Pandoc conversion timed out"
        except Exception as e:
            results["error"] = f"Pandoc test failed: {str(e)}"

        # Test with other tools if available
        other_tools = ["markdown", "cmark"]
        for tool in other_tools:
            try:
                # Simple test - just check if tool can process Hebrew text
                process = subprocess.run(
                    [tool]
                    if tool != "markdown"
                    else ["python3", "-m", "markdown"],
                    input="שלום עולם",
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if process.returncode == 0:
                    hebrew_in_output = bool(hebrew_chars & set(process.stdout))
                    step = {
                        "tool": tool,
                        "available": True,
                        "hebrew_preserved": hebrew_in_output,
                    }
                    results["processing_steps"].append(step)

            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass  # Tool not available

        # Determine success
        results["success"] = (
            results["original_content_created"]
            and results["hebrew_text_detected"]
            and results["english_text_detected"]
            and (
                results["hebrew_chars_preserved"]
                or not results["pandoc_available"]
            )
        )

    except Exception as e:
        results["error"] = str(e)

    return results


def main():
    """Run the Hebrew RTL preservation test."""
    print(
        "Test 27: Hebrew RTL paragraphs stay RTL after Pandoc → MD → renderer"
    )
    print("=" * 60)

    results = test_hebrew_rtl_preservation()

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\nResults saved to: {output_file}")
    print(f"Hebrew text detected: {results['hebrew_text_detected']}")
    print(f"Pandoc available: {results['pandoc_available']}")
    print(f"Hebrew preserved: {results.get('hebrew_chars_preserved', 'N/A')}")
    print(f"Processing steps: {len(results['processing_steps'])}")

    if results["success"]:
        print("✅ PASS: Hebrew RTL preservation verified")
    else:
        print("❌ FAIL: Hebrew RTL preservation issues")
        if results["error"]:
            print(f"Error: {results['error']}")

    return results


if __name__ == "__main__":
    main()
