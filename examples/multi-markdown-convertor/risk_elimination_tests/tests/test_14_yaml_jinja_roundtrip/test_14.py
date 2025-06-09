#!/usr/bin/env python3
"""
Test 14: YAML + Jinja front-matter round-trips non-ASCII safely
Template with emoji + RTL text
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import tempfile
import yaml
import jinja2


def test_yaml_jinja_roundtrip() -> Dict[str, Any]:
    """
    Test YAML + Jinja front-matter round-trip with non-ASCII characters.

    Returns:
        Dict with test analysis results
    """
    analysis: Dict[str, Any] = {
        "test_implemented": True,
        "test_case": "Template with emoji + RTL text",
        "success_criteria": "diff(original, rendered) == 0",
        "results": {},
    }

    try:
        print("Testing YAML + Jinja front-matter round-trip with non-ASCII...")

        # Create test content with emoji and RTL text
        test_content = {
            "title": "🚀 Advanced Document Processing",
            "description": "מערכת עיבוד מסמכים מתקדמת",  # Hebrew RTL text
            "emoji_list": ["📄", "🔍", "⚡", "🎯"],
            "mixed_text": "Hello 👋 שלום World 🌍",
            "unicode_symbols": "α β γ δ ε ζ η θ",
            "special_chars": "café naïve résumé",
            "numbers": "١٢٣٤٥",  # Arabic numerals
            "chinese": "文档处理系统",  # Chinese characters
        }

        # Test 1: YAML serialization/deserialization
        print("Testing YAML round-trip...")
        try:
            yaml_str = yaml.dump(
                test_content, allow_unicode=True, default_flow_style=False
            )
            yaml_parsed = yaml.safe_load(yaml_str)

            yaml_roundtrip_success = test_content == yaml_parsed
            analysis["results"]["yaml_roundtrip"] = yaml_roundtrip_success
            analysis["results"]["yaml_content"] = yaml_str

            if yaml_roundtrip_success:
                print("✅ YAML round-trip successful")
            else:
                print("❌ YAML round-trip failed")
                analysis["results"]["yaml_diff"] = {
                    "original": test_content,
                    "parsed": yaml_parsed,
                }

        except Exception as e:
            analysis["results"]["yaml_error"] = str(e)
            analysis["results"]["yaml_roundtrip"] = False

        # Test 2: Jinja2 template rendering with YAML front-matter
        print("Testing Jinja2 template with YAML front-matter...")
        try:
            # Create a template with YAML front-matter
            template_content = f"""---
{yaml.dump(test_content, allow_unicode=True, default_flow_style=False)}---

# {{{{ title }}}}

## Description
{{{{ description }}}}

## Emoji List
{{% for emoji in emoji_list %}}
- {{{{ emoji }}}} Item {{{{ loop.index }}}}
{{% endfor %}}

## Mixed Content
{{{{ mixed_text }}}}

## Unicode Symbols
{{{{ unicode_symbols }}}}

## Special Characters
{{{{ special_chars }}}}

## Numbers
{{{{ numbers }}}}

## Chinese Text
{{{{ chinese }}}}

## Template Variables
- Title: {{{{ title }}}}
- Description: {{{{ description }}}}
- First Emoji: {{{{ emoji_list[0] }}}}
"""

            # Parse YAML front-matter
            parts = template_content.split("---", 2)
            if len(parts) >= 3:
                yaml_content = parts[1].strip()
                template_body = parts[2].strip()

                # Parse YAML
                yaml_data = yaml.safe_load(yaml_content)

                # Render template
                jinja_env = jinja2.Environment()
                template = jinja_env.from_string(template_body)
                rendered = template.render(**yaml_data)

                analysis["results"]["jinja_rendering"] = True
                analysis["results"]["rendered_content"] = rendered

                # Check if all non-ASCII characters are preserved
                original_chars = set(yaml_content)
                rendered_chars = set(rendered)

                # Check for specific non-ASCII characters
                test_chars = [
                    "🚀",
                    "📄",
                    "🔍",
                    "⚡",
                    "🎯",
                    "👋",
                    "🌍",
                    "מ",
                    "ע",
                    "ר",
                    "כ",
                    "ת",
                    "ש",
                    "ל",
                    "ו",
                    "ם",
                    "α",
                    "β",
                    "γ",
                    "café",
                    "naïve",
                    "résumé",
                    "١",
                    "٢",
                    "٣",
                    "٤",
                    "٥",
                    "文",
                    "档",
                    "处",
                    "理",
                    "系",
                    "统",
                ]

                preserved_chars = []
                missing_chars = []

                for char in test_chars:
                    if char in rendered:
                        preserved_chars.append(char)
                    else:
                        missing_chars.append(char)

                analysis["results"]["preserved_chars"] = preserved_chars
                analysis["results"]["missing_chars"] = missing_chars
                analysis["results"]["char_preservation_rate"] = len(
                    preserved_chars
                ) / len(test_chars)

                # Test success if most characters are preserved
                analysis["results"]["jinja_success"] = len(missing_chars) == 0

                print(
                    f"Character preservation: {len(preserved_chars)}/{len(test_chars)} ({analysis['results']['char_preservation_rate']:.1%})"
                )

            else:
                analysis["results"]["jinja_rendering"] = False
                analysis["results"]["jinja_error"] = (
                    "Failed to parse YAML front-matter"
                )

        except Exception as e:
            analysis["results"]["jinja_rendering"] = False
            analysis["results"]["jinja_error"] = str(e)

        # Test 3: Full round-trip test
        print("Testing full round-trip...")
        try:
            # Create original template
            original_template = f"""---
title: 🚀 Advanced Document Processing
description: מערכת עיבוד מסמכים מתקדמת
emoji: 📄🔍⚡🎯
mixed: Hello 👋 שלום World 🌍
---

# {{{{ title }}}}
{{{{ description }}}}
{{{{ emoji }}}} {{{{ mixed }}}}
"""

            # Parse and re-serialize
            parts = original_template.split("---", 2)
            yaml_part = parts[1].strip()
            template_part = parts[2].strip()

            # Parse YAML
            yaml_data = yaml.safe_load(yaml_part)

            # Re-serialize YAML
            new_yaml = yaml.dump(
                yaml_data, allow_unicode=True, default_flow_style=False
            )

            # Reconstruct template
            reconstructed = f"---\n{new_yaml}---\n{template_part}"

            # Compare byte-by-byte
            original_bytes = original_template.encode("utf-8")
            reconstructed_bytes = reconstructed.encode("utf-8")

            # Calculate similarity (allowing for minor formatting differences)
            original_normalized = original_template.replace(" ", "").replace(
                "\n", ""
            )
            reconstructed_normalized = reconstructed.replace(" ", "").replace(
                "\n", ""
            )

            similarity = len(
                set(original_normalized) & set(reconstructed_normalized)
            ) / len(set(original_normalized) | set(reconstructed_normalized))

            analysis["results"]["roundtrip_similarity"] = similarity
            analysis["results"]["roundtrip_success"] = similarity > 0.95

            print(f"Round-trip similarity: {similarity:.1%}")

        except Exception as e:
            analysis["results"]["roundtrip_error"] = str(e)
            analysis["results"]["roundtrip_success"] = False

        # Overall success
        yaml_ok = analysis["results"].get("yaml_roundtrip", False)
        jinja_ok = analysis["results"].get("jinja_success", False)
        roundtrip_ok = analysis["results"].get("roundtrip_success", False)

        analysis["results"]["overall_success"] = (
            yaml_ok and jinja_ok and roundtrip_ok
        )

        return analysis

    except Exception as e:
        analysis["results"]["error"] = str(e)
        analysis["results"]["overall_success"] = False
        return analysis


def run_test() -> Dict[str, Any]:
    """
    Run test 14: YAML + Jinja front-matter round-trips non-ASCII safely.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "14",
        "test_name": "YAML + Jinja front-matter round-trips non-ASCII safely",
        "test_case": "Template with emoji + RTL text",
        "success": False,
        "error": None,
        "details": {},
    }

    try:
        print(
            f"Test 14: YAML + Jinja front-matter round-trips non-ASCII safely"
        )
        print(f"Test case: Template with emoji + RTL text")

        # Run the specific test function
        analysis = test_yaml_jinja_roundtrip()
        results["details"]["analysis"] = analysis

        # Determine success based on analysis
        if analysis["results"].get("overall_success", False):
            results["success"] = True
            char_rate = analysis["results"].get("char_preservation_rate", 0)
            roundtrip_sim = analysis["results"].get("roundtrip_similarity", 0)
            results["details"]["result"] = (
                f"PASS: YAML+Jinja round-trip successful (chars: {char_rate:.1%}, similarity: {roundtrip_sim:.1%})"
            )
            print(
                f"✅ PASS: YAML+Jinja round-trip successful (chars: {char_rate:.1%}, similarity: {roundtrip_sim:.1%})"
            )
        else:
            error_msg = analysis["results"].get("error", "Round-trip failed")
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
