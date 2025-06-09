#!/usr/bin/env python3
"""
Test 28: LLM semantic-diff false-positive rate < 5%
Compare 50 pairs with ground truth
"""

import json
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple


def create_test_document_pairs() -> List[Tuple[str, str, bool]]:
    """
    Create pairs of documents with known semantic differences.

    Returns:
        List of (doc1, doc2, has_semantic_difference) tuples
    """
    pairs = []

    # True positives - documents with real semantic differences
    true_positive_pairs = [
        (
            "The company reported revenue of $100 million in Q1.",
            "The company reported revenue of $200 million in Q1.",
            True,  # Different revenue amount
        ),
        (
            "The project will be completed by December 2024.",
            "The project will be completed by June 2025.",
            True,  # Different completion date
        ),
        (
            "Our team consists of 5 engineers and 3 designers.",
            "Our team consists of 8 engineers and 2 designers.",
            True,  # Different team composition
        ),
        (
            "The product launch was successful with positive customer feedback.",
            "The product launch failed due to technical issues.",
            True,  # Opposite outcomes
        ),
        (
            "We recommend investing in renewable energy stocks.",
            "We recommend avoiding renewable energy stocks.",
            True,  # Opposite recommendations
        ),
    ]

    # True negatives - documents with only stylistic/formatting differences
    true_negative_pairs = [
        (
            "The company reported revenue of $100 million in Q1.",
            "The company reported Q1 revenue of $100 million.",
            False,  # Same information, different order
        ),
        (
            "Our team includes engineers and designers.",
            "Our team consists of engineers and designers.",
            False,  # Synonym substitution
        ),
        (
            "The project deadline is December 31, 2024.",
            "The project deadline is Dec 31, 2024.",
            False,  # Date format difference
        ),
        (
            "We achieved a 15% increase in sales.",
            "Sales increased by 15%.",
            False,  # Different phrasing, same meaning
        ),
        (
            "The meeting is scheduled for 2:00 PM on Monday.",
            "The meeting is scheduled for 2 PM on Monday.",
            False,  # Time format difference
        ),
    ]

    # Add more pairs to reach 50 total
    base_pairs = true_positive_pairs + true_negative_pairs

    # Generate variations
    for i in range(50 - len(base_pairs)):
        if i % 2 == 0:
            # Generate true positive
            base_text = f"Document {i + 1} contains important information about topic X."
            modified_text = f"Document {i + 1} contains critical information about topic Y."
            pairs.append((base_text, modified_text, True))
        else:
            # Generate true negative
            base_text = (
                f"The analysis shows significant results for case {i + 1}."
            )
            modified_text = f"The analysis demonstrates significant results for case {i + 1}."
            pairs.append((base_text, modified_text, False))

    return base_pairs + pairs


def create_semantic_diff_template() -> Path:
    """Create a template for semantic difference detection."""
    template_content = """---
system: You are an expert at detecting semantic differences between texts.
---

Compare these two text snippets and determine if they have meaningful semantic differences:

Text 1: {{ text1 }}

Text 2: {{ text2 }}

Consider only semantic differences (meaning changes), not stylistic or formatting differences.

Examples of semantic differences: different numbers, opposite meanings, different facts
Examples of non-semantic differences: synonyms, reordering, formatting, punctuation

Provide your analysis in the following format.
"""

    temp_file = Path(__file__).parent / "temp_template.j2"
    with open(temp_file, "w") as f:
        f.write(template_content)
    return temp_file


def create_semantic_diff_schema() -> Path:
    """Create a schema for semantic difference detection."""
    schema = {
        "type": "object",
        "properties": {
            "has_semantic_difference": {
                "type": "boolean",
                "description": "True if there are meaningful semantic differences",
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Confidence level in the assessment (0-1)",
            },
            "explanation": {
                "type": "string",
                "description": "Brief explanation of the differences or similarities",
            },
            "difference_type": {
                "type": "string",
                "enum": ["semantic", "stylistic", "formatting", "none"],
                "description": "Type of difference detected",
            },
        },
        "required": [
            "has_semantic_difference",
            "confidence",
            "explanation",
            "difference_type",
        ],
    }

    temp_file = Path(__file__).parent / "temp_schema.json"
    with open(temp_file, "w") as f:
        json.dump(schema, f, indent=2)
    return temp_file


def test_llm_semantic_diff() -> Dict[str, Any]:
    """
    Test LLM semantic diff false positive rate.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "28",
        "test_name": "LLM semantic-diff false-positive rate < 5%",
        "total_pairs": 50,
        "pairs_tested": 0,
        "true_positives": 0,
        "true_negatives": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "false_positive_rate": 0.0,
        "accuracy": 0.0,
        "ostruct_available": False,
        "test_results": [],
        "success": False,
        "error": None,
    }

    template_file = None
    schema_file = None

    try:
        # Create test pairs
        test_pairs = create_test_document_pairs()
        results["total_pairs"] = len(test_pairs)

        # Create ostruct template and schema
        template_file = create_semantic_diff_template()
        schema_file = create_semantic_diff_schema()

        print(f"Testing {len(test_pairs)} document pairs...")

        # Test each pair
        for i, (text1, text2, ground_truth) in enumerate(test_pairs):
            pair_result = {
                "pair_id": i + 1,
                "ground_truth": ground_truth,
                "llm_prediction": None,
                "confidence": None,
                "explanation": "",
                "correct": False,
                "error": None,
            }

            try:
                # Create output file for clean JSON
                output_file = (
                    Path(__file__).parent / f"temp_output_pair_{i + 1}.json"
                )

                # Use ostruct to get LLM assessment (live API call for accurate results)
                cmd = [
                    "ostruct",
                    "run",
                    str(template_file),
                    str(schema_file),
                    "-V",
                    f"text1={text1}",
                    "-V",
                    f"text2={text2}",
                    "-m",
                    "gpt-4.1",
                    "--output-file",
                    str(output_file),
                ]

                process = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30
                )

                if process.returncode == 0:
                    results["ostruct_available"] = True

                    try:
                        # Read clean JSON from output file
                        with open(output_file, "r") as f:
                            llm_response = json.load(f)

                        # Extract LLM prediction
                        has_semantic_diff = llm_response.get(
                            "has_semantic_difference", False
                        )
                        confidence = llm_response.get("confidence", 0.0)
                        explanation = llm_response.get("explanation", "")

                        pair_result["llm_prediction"] = has_semantic_diff
                        pair_result["confidence"] = confidence
                        pair_result["explanation"] = explanation
                        pair_result["correct"] = (
                            has_semantic_diff == ground_truth
                        )
                        results["pairs_tested"] += 1

                    except (
                        json.JSONDecodeError,
                        FileNotFoundError,
                        KeyError,
                    ) as e:
                        pair_result["error"] = f"JSON parsing error: {str(e)}"

                else:
                    pair_result["error"] = f"ostruct failed: {process.stderr}"

                # Cleanup pair-specific output file
                try:
                    output_file.unlink()
                except:
                    pass

            except subprocess.TimeoutExpired:
                pair_result["error"] = "ostruct call timed out"
            except FileNotFoundError:
                pair_result["error"] = "ostruct not found"
                break  # No point continuing if ostruct isn't available
            except Exception as e:
                pair_result["error"] = str(e)

            results["test_results"].append(pair_result)

        # Calculate metrics
        if results["pairs_tested"] > 0:
            for result in results["test_results"]:
                if result["llm_prediction"] is not None:
                    if result["ground_truth"] and result["llm_prediction"]:
                        results["true_positives"] += 1
                    elif (
                        not result["ground_truth"]
                        and not result["llm_prediction"]
                    ):
                        results["true_negatives"] += 1
                    elif (
                        not result["ground_truth"] and result["llm_prediction"]
                    ):
                        results["false_positives"] += 1
                    elif (
                        result["ground_truth"] and not result["llm_prediction"]
                    ):
                        results["false_negatives"] += 1

            # Calculate rates
            total_negatives = (
                results["true_negatives"] + results["false_positives"]
            )
            if total_negatives > 0:
                results["false_positive_rate"] = (
                    results["false_positives"] / total_negatives
                )

            total_correct = (
                results["true_positives"] + results["true_negatives"]
            )
            results["accuracy"] = total_correct / results["pairs_tested"]

        print(f"Pairs tested: {results['pairs_tested']}")
        print(f"True positives: {results['true_positives']}")
        print(f"True negatives: {results['true_negatives']}")
        print(f"False positives: {results['false_positives']}")
        print(f"False negatives: {results['false_negatives']}")
        print(f"False positive rate: {results['false_positive_rate']:.2%}")
        print(f"Accuracy: {results['accuracy']:.2%}")

        # Success criteria: false positive rate < 5%
        results["success"] = (
            results["pairs_tested"] > 0
            and results["false_positive_rate"] < 0.05
        )

    except Exception as e:
        results["error"] = str(e)
    finally:
        # Clean up temporary files
        for temp_file in [template_file, schema_file]:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

        # Cleanup any remaining output files
        if "Path" in globals():
            for output_file in Path(__file__).parent.glob(
                "temp_output_pair_*.json"
            ):
                try:
                    output_file.unlink()
                except:
                    pass

    return results


def main():
    """Run the LLM semantic diff test."""
    print("Test 28: LLM semantic-diff false-positive rate < 5%")
    print("=" * 60)

    results = test_llm_semantic_diff()

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\nResults saved to: {output_file}")
    print(f"Pairs tested: {results['pairs_tested']}/{results['total_pairs']}")
    print(f"False positive rate: {results['false_positive_rate']:.2%}")
    print(f"Overall accuracy: {results['accuracy']:.2%}")

    if results["success"]:
        print("✅ PASS: False positive rate < 5%")
    else:
        print("❌ FAIL: False positive rate ≥ 5%")
        if results["error"]:
            print(f"Error: {results['error']}")

    return results


if __name__ == "__main__":
    main()
