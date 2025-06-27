# Troubleshooting Cookbook

> **Tools:** ⚡ None
> **Cost (approx.):** $0.00 (no API calls)

## 1. Description

A comprehensive troubleshooting cookbook showing broken→fixed template pairs for common ostruct issues. This example demonstrates how to identify, diagnose, and fix the most frequent template problems developers encounter.

## 2. Prerequisites

```bash
# No special dependencies required
```

## 3. Quick Start

```bash
# Fast validation (no API calls) - shows all broken examples
./run.sh --test-dry-run

# Live API test (same as dry-run for this example)
./run.sh --test-live

# Full execution (shows broken→fixed pairs)
./run.sh

# Show specific issue type
./run.sh --issue-type syntax
./run.sh --issue-type variables
./run.sh --issue-type logic
```

## 4. Files

| Path | Purpose |
|------|---------|
| `templates/broken_syntax.j2` | Examples of common syntax errors |
| `templates/fixed_syntax.j2` | Corrected versions of syntax issues |
| `templates/broken_variables.j2` | Variable access and scope problems |
| `templates/fixed_variables.j2` | Proper variable handling techniques |
| `templates/broken_logic.j2` | Logic and control flow issues |
| `templates/fixed_logic.j2` | Corrected logic patterns |
| `schemas/troubleshooting.json` | Schema for validation output |
| `data/test_data.json` | Test data for demonstrating issues |

## 5. Expected Output

The example demonstrates:

- **Common syntax errors** and their fixes
- **Variable access issues** and safe patterns
- **Logic problems** and correct implementations
- **Error messages** and how to interpret them

Example troubleshooting output:

```json
{
  "issue_categories": [
    {
      "category": "syntax_errors",
      "examples": [
        {
          "problem": "Unclosed template tag",
          "broken_code": "{% if condition",
          "fixed_code": "{% if condition %}...{% endif %}",
          "explanation": "All template tags must be properly closed"
        }
      ]
    }
  ]
}
```

## 6. Customization

- **Add new issues**: Create additional broken/fixed template pairs
- **Custom scenarios**: Add your own problematic templates to debug
- **Error patterns**: Extend with domain-specific troubleshooting patterns

## 7. Clean-Up

No cleanup required - this example only validates templates and shows error patterns.
