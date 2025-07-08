#!/usr/bin/env python3
"""Generate hardened plan_step.schema.json from tools.json.

Usage:
    python generate_plan_step_schema.py > plan_step.schema.json

The script reads the sibling ``tools.json`` file and emits a JSON Schema
where each tool becomes a fully-enumerated variant inside a top-level
``oneOf`` array.  All tool parameters are marked as required (along with
``tool`` and ``reasoning``) and ``additionalProperties`` is set to false
so that the ostruct validator rejects missing or extraneous fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
TOOLS_FILE = ROOT.parent / "tools.json"
OUTPUT_FILE = ROOT / "plan_step.schema.json"

REASONING_PROPERTY = {
    "reasoning": {
        "type": "string",
        "description": "Explanation of why this tool is needed for the task",
    }
}


def build_variant(tool: str, parameters: Dict[str, str]) -> Dict[str, object]:
    """Return a JSON-Schema variant for *tool* with *parameters*."""
    properties: Dict[str, object] = {
        "tool": {"const": tool},
        **REASONING_PROPERTY,
    }
    # Default to string type for all parameters (can be refined manually later)
    properties.update({name: {"type": "string"} for name in parameters})

    required: List[str] = ["tool", "reasoning", *parameters]

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


def main() -> None:
    tools = json.loads(TOOLS_FILE.read_text())

    variants = [
        build_variant(tool, meta["parameters"]) for tool, meta in tools.items()
    ]

    schema: Dict[str, object] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "oneOf": variants,
    }

    json.dump(schema, OUTPUT_FILE.open("w"), indent=4)
    print(
        f"Generated {OUTPUT_FILE.relative_to(ROOT)} with {len(variants)} variants."
    )


if __name__ == "__main__":
    main()
