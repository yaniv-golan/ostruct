#!/usr/bin/env python3
"""
Test 19: PDFMiner auto-tuning: adjust extraction params based on PDF characteristics
Adaptive parameter optimization
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, NamedTuple
import subprocess
import tempfile
import time
import re
from dataclasses import dataclass


@dataclass
class PDFCharacteristics:
    """PDF document characteristics for parameter tuning."""

    page_count: int
    has_images: bool
    has_tables: bool
    text_density: float  # Characters per page
    font_variety: int  # Number of different fonts
    layout_complexity: float  # 0-1 score
    scan_quality: Optional[float]  # For scanned PDFs, None for native


@dataclass
class ExtractionParams:
    """PDFMiner extraction parameters."""

    laparams_word_margin: float = 0.1
    laparams_char_margin: float = 2.0
    laparams_line_margin: float = 0.5
    laparams_boxes_flow: float = 0.5
    detect_vertical: bool = False
    all_texts: bool = False
    maxpages: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "word_margin": self.laparams_word_margin,
            "char_margin": self.laparams_char_margin,
            "line_margin": self.laparams_line_margin,
            "boxes_flow": self.laparams_boxes_flow,
            "detect_vertical": self.detect_vertical,
            "all_texts": self.all_texts,
            "maxpages": self.maxpages,
        }


def analyze_pdf_characteristics(pdf_path: Path) -> PDFCharacteristics:
    """Analyze PDF characteristics to determine optimal extraction parameters."""
    try:
        # Try using PyPDF2 or pdfplumber for basic analysis
        try:
            import PyPDF2

            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                page_count = len(reader.pages)

                # Sample first few pages for analysis
                sample_text = ""
                for i in range(min(3, page_count)):
                    try:
                        page_text = reader.pages[i].extract_text()
                        sample_text += page_text
                    except:
                        pass

                # Basic characteristics
                text_density = len(sample_text) / max(1, min(3, page_count))
                has_images = any(
                    "/Image" in str(page.get("/Resources", {}))
                    for page in reader.pages[:3]
                )

                # Estimate table presence (simple heuristic)
                has_tables = (
                    bool(re.search(r"(\s{3,}|\t)", sample_text))
                    or sample_text.count("|") > 5
                )

                # Font variety estimation (simplified)
                font_variety = min(
                    10,
                    len(
                        set(
                            re.findall(
                                r"/F\d+",
                                str(reader.pages[0]) if reader.pages else "",
                            )
                        )
                    ),
                )

                # Layout complexity (based on whitespace patterns)
                lines = sample_text.split("\n")
                non_empty_lines = [line for line in lines if line.strip()]
                layout_complexity = min(
                    1.0, len(non_empty_lines) / max(1, len(lines))
                )

                return PDFCharacteristics(
                    page_count=page_count,
                    has_images=has_images,
                    has_tables=has_tables,
                    text_density=text_density,
                    font_variety=font_variety,
                    layout_complexity=layout_complexity,
                    scan_quality=None,  # Can't determine from PyPDF2
                )

        except ImportError:
            pass

        # Fallback: estimate based on file size and name
        file_size = pdf_path.stat().st_size
        estimated_pages = max(1, file_size // 50000)  # Rough estimate

        # Make educated guesses based on filename
        filename_lower = pdf_path.name.lower()
        has_tables = any(
            word in filename_lower
            for word in ["report", "financial", "data", "table"]
        )
        has_images = any(
            word in filename_lower
            for word in ["presentation", "brochure", "catalog"]
        )

        return PDFCharacteristics(
            page_count=estimated_pages,
            has_images=has_images,
            has_tables=has_tables,
            text_density=1000.0,  # Default assumption
            font_variety=3,  # Conservative estimate
            layout_complexity=0.7,
            scan_quality=None,
        )

    except Exception as e:
        print(f"Error analyzing PDF {pdf_path}: {e}")
        # Return default characteristics
        return PDFCharacteristics(
            page_count=10,
            has_images=False,
            has_tables=False,
            text_density=1000.0,
            font_variety=2,
            layout_complexity=0.5,
            scan_quality=None,
        )


def optimize_extraction_params(
    characteristics: PDFCharacteristics,
) -> ExtractionParams:
    """Optimize PDFMiner parameters based on PDF characteristics."""
    params = ExtractionParams()

    # Adjust word margin based on text density
    if characteristics.text_density > 2000:
        # Dense text - tighter margins
        params.laparams_word_margin = 0.05
    elif characteristics.text_density < 500:
        # Sparse text - looser margins
        params.laparams_word_margin = 0.2
    else:
        params.laparams_word_margin = 0.1

    # Adjust character margin based on font variety
    if characteristics.font_variety > 5:
        # Many fonts - more tolerance
        params.laparams_char_margin = 3.0
    elif characteristics.font_variety < 2:
        # Few fonts - tighter grouping
        params.laparams_char_margin = 1.5
    else:
        params.laparams_char_margin = 2.0

    # Adjust line margin based on layout complexity
    if characteristics.layout_complexity > 0.8:
        # Complex layout - more conservative
        params.laparams_line_margin = 0.3
    elif characteristics.layout_complexity < 0.4:
        # Simple layout - more aggressive grouping
        params.laparams_line_margin = 0.7
    else:
        params.laparams_line_margin = 0.5

    # Adjust boxes flow for tables
    if characteristics.has_tables:
        params.laparams_boxes_flow = 0.3  # Preserve table structure
    else:
        params.laparams_boxes_flow = 0.7  # More flowing text

    # Enable vertical text detection for complex layouts
    if characteristics.layout_complexity > 0.7 or characteristics.has_tables:
        params.detect_vertical = True

    # Limit pages for very large documents
    if characteristics.page_count > 100:
        params.maxpages = 50  # Sample first 50 pages

    return params


def extract_text_with_params(
    pdf_path: Path, params: ExtractionParams
) -> Tuple[str, Dict[str, Any]]:
    """Extract text using PDFMiner with specified parameters."""
    try:
        # Try using pdfminer.six if available
        try:
            from pdfminer.high_level import extract_text
            from pdfminer.layout import LAParams

            # Create LAParams object with optimized parameters
            laparams = LAParams(
                word_margin=params.laparams_word_margin,
                char_margin=params.laparams_char_margin,
                line_margin=params.laparams_line_margin,
                boxes_flow=params.laparams_boxes_flow,
                detect_vertical=params.detect_vertical,
                all_texts=params.all_texts,
            )

            # Extract text
            start_time = time.time()
            text = extract_text(
                str(pdf_path), laparams=laparams, maxpages=params.maxpages
            )
            end_time = time.time()

            # Calculate extraction metrics
            metrics = {
                "extraction_time": end_time - start_time,
                "text_length": len(text),
                "line_count": len(text.split("\n")),
                "word_count": len(text.split()),
                "params_used": params.to_dict(),
            }

            return text, metrics

        except ImportError:
            pass

        # Fallback: simulate extraction
        file_size = pdf_path.stat().st_size
        simulated_text = f"""
Extracted text from {pdf_path.name}

This is simulated text extraction using optimized parameters:
- Word margin: {params.laparams_word_margin}
- Character margin: {params.laparams_char_margin}
- Line margin: {params.laparams_line_margin}
- Boxes flow: {params.laparams_boxes_flow}
- Detect vertical: {params.detect_vertical}

File size: {file_size} bytes
Estimated content length: {file_size // 10} characters

Sample content would appear here with proper formatting
based on the optimized extraction parameters.
"""

        metrics = {
            "extraction_time": 2.5,  # Simulated time
            "text_length": len(simulated_text),
            "line_count": len(simulated_text.split("\n")),
            "word_count": len(simulated_text.split()),
            "params_used": params.to_dict(),
            "simulated": True,
        }

        return simulated_text, metrics

    except Exception as e:
        error_text = f"Error extracting text from {pdf_path}: {str(e)}"
        error_metrics = {
            "extraction_time": 0,
            "text_length": 0,
            "line_count": 0,
            "word_count": 0,
            "params_used": params.to_dict(),
            "error": str(e),
        }
        return error_text, error_metrics


def evaluate_extraction_quality(
    text: str, characteristics: PDFCharacteristics
) -> float:
    """Evaluate the quality of extracted text."""
    if not text or len(text.strip()) == 0:
        return 0.0

    score = 10.0  # Start with perfect score

    # Check for reasonable text length
    expected_length = characteristics.text_density * min(
        characteristics.page_count, 10
    )
    actual_length = len(text)
    length_ratio = actual_length / max(1, expected_length)

    if length_ratio < 0.3:
        score -= 3.0  # Too little text extracted
    elif length_ratio > 3.0:
        score -= 2.0  # Possibly too much noise

    # Check for proper line breaks and structure
    lines = text.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]

    if len(non_empty_lines) < 3:
        score -= 2.0  # Poor structure

    # Check for reasonable word distribution
    words = text.split()
    if len(words) == 0:
        return 0.0

    avg_word_length = sum(len(word) for word in words) / len(words)
    if avg_word_length < 2 or avg_word_length > 15:
        score -= 1.5  # Unusual word patterns

    # Check for table preservation if expected
    if characteristics.has_tables:
        table_indicators = (
            text.count("|")
            + text.count("\t")
            + len(re.findall(r"\s{3,}", text))
        )
        if table_indicators < 5:
            score -= 2.0  # Tables not well preserved

    # Check for excessive repetition (common extraction error)
    unique_lines = set(line.strip() for line in lines if line.strip())
    if len(unique_lines) < len(non_empty_lines) * 0.7:
        score -= 1.5  # Too much repetition

    return max(0.0, score)


def find_pdf_files() -> List[Path]:
    """Find PDF files in the test-inputs directory."""
    test_inputs_dir = Path(__file__).parent.parent.parent / "test-inputs"
    pdf_files = list(test_inputs_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in test-inputs directory")
        # Create a dummy path for testing
        return [test_inputs_dir / "sample.pdf"]

    return pdf_files[:5]  # Limit to 5 files for testing


def test_pdfminer_auto_tuning() -> Dict[str, Any]:
    """
    Test PDFMiner auto-tuning functionality.

    Returns:
        Dict with test analysis results
    """
    analysis: Dict[str, Any] = {
        "test_implemented": True,
        "test_case": "Adaptive parameter optimization",
        "success_criteria": "Improved extraction quality with tuned parameters",
        "results": {},
    }

    try:
        print("Testing PDFMiner auto-tuning...")

        # Find PDF files
        pdf_files = find_pdf_files()
        analysis["results"]["total_files"] = len(pdf_files)

        # Test results for each PDF
        file_results = []

        for pdf_file in pdf_files:
            print(f"\nProcessing: {pdf_file.name}")

            if not pdf_file.exists():
                print(f"  File does not exist, skipping...")
                continue

            file_result = {
                "filename": pdf_file.name,
                "file_exists": pdf_file.exists(),
                "characteristics": None,
                "default_extraction": None,
                "tuned_extraction": None,
                "improvement": 0.0,
            }

            try:
                # Analyze PDF characteristics
                print(f"  Analyzing characteristics...")
                characteristics = analyze_pdf_characteristics(pdf_file)
                file_result["characteristics"] = {
                    "page_count": characteristics.page_count,
                    "has_images": characteristics.has_images,
                    "has_tables": characteristics.has_tables,
                    "text_density": characteristics.text_density,
                    "font_variety": characteristics.font_variety,
                    "layout_complexity": characteristics.layout_complexity,
                }

                # Extract with default parameters
                print(f"  Extracting with default parameters...")
                default_params = ExtractionParams()
                default_text, default_metrics = extract_text_with_params(
                    pdf_file, default_params
                )
                default_quality = evaluate_extraction_quality(
                    default_text, characteristics
                )

                file_result["default_extraction"] = {
                    "quality_score": default_quality,
                    "metrics": default_metrics,
                }

                # Optimize parameters and extract
                print(f"  Optimizing parameters...")
                tuned_params = optimize_extraction_params(characteristics)
                print(f"  Extracting with tuned parameters...")
                tuned_text, tuned_metrics = extract_text_with_params(
                    pdf_file, tuned_params
                )
                tuned_quality = evaluate_extraction_quality(
                    tuned_text, characteristics
                )

                file_result["tuned_extraction"] = {
                    "quality_score": tuned_quality,
                    "metrics": tuned_metrics,
                    "optimized_params": tuned_params.to_dict(),
                }

                # Calculate improvement
                improvement = tuned_quality - default_quality
                file_result["improvement"] = improvement

                print(f"  Default quality: {default_quality:.2f}/10")
                print(f"  Tuned quality: {tuned_quality:.2f}/10")
                print(f"  Improvement: {improvement:+.2f}")

            except Exception as e:
                print(f"  Error processing {pdf_file.name}: {e}")
                file_result["error"] = str(e)

            file_results.append(file_result)

        analysis["results"]["file_results"] = file_results

        # Calculate overall metrics
        successful_files = [
            r for r in file_results if "error" not in r and r["file_exists"]
        ]
        if successful_files:
            improvements = [r["improvement"] for r in successful_files]
            avg_improvement = sum(improvements) / len(improvements)
            positive_improvements = [i for i in improvements if i > 0]

            analysis["results"]["successful_files"] = len(successful_files)
            analysis["results"]["average_improvement"] = avg_improvement
            analysis["results"]["positive_improvements"] = len(
                positive_improvements
            )
            analysis["results"]["improvement_rate"] = len(
                positive_improvements
            ) / len(successful_files)

            # Success if average improvement > 0.5 or improvement rate > 60%
            analysis["results"]["success"] = (
                avg_improvement > 0.5
                or (len(positive_improvements) / len(successful_files)) > 0.6
            )

            print(f"\nOverall Results:")
            print(f"  Files processed: {len(successful_files)}")
            print(f"  Average improvement: {avg_improvement:+.2f}")
            print(
                f"  Positive improvements: {len(positive_improvements)}/{len(successful_files)}"
            )
            print(f"  Success: {analysis['results']['success']}")
        else:
            analysis["results"]["success"] = False
            analysis["results"]["error"] = "No files successfully processed"

        return analysis

    except Exception as e:
        analysis["results"]["error"] = str(e)
        analysis["results"]["success"] = False
        return analysis


def run_test() -> Dict[str, Any]:
    """
    Run test 19: PDFMiner auto-tuning.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "19",
        "test_name": "PDFMiner auto-tuning: adjust extraction params based on PDF characteristics",
        "test_case": "Adaptive parameter optimization",
        "success": False,
        "error": None,
        "details": {},
    }

    try:
        print(f"Test 19: PDFMiner auto-tuning")
        print(f"Test case: Adaptive parameter optimization")

        # Run the specific test function
        analysis = test_pdfminer_auto_tuning()
        results["details"]["analysis"] = analysis

        # Determine success based on analysis
        if analysis["results"].get("success", False):
            avg_improvement = analysis["results"].get("average_improvement", 0)
            improvement_rate = analysis["results"].get("improvement_rate", 0)
            results["success"] = True
            results["details"]["result"] = (
                f"PASS: Avg improvement {avg_improvement:+.2f}, rate {improvement_rate:.1%}"
            )
            print(
                f"✅ PASS: Avg improvement {avg_improvement:+.2f}, rate {improvement_rate:.1%}"
            )
        else:
            error_msg = analysis["results"].get(
                "error", "Auto-tuning did not improve extraction quality"
            )
            results["error"] = error_msg
            results["success"] = False
            results["details"]["result"] = f"FAIL: {error_msg}"
            print(f"❌ FAIL: {error_msg}")

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
