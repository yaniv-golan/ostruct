# Code Review Schema

The code review output follows a structured schema defined in `schemas/code_review.json`. This document explains each field and its purpose.

## Schema Structure

```json
{
  "type": "object",
  "properties": {
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Impact level of the issue"
          },
          "category": {
            "type": "string",
            "enum": [
              "security",
              "performance",
              "maintainability",
              "reliability",
              "style",
              "documentation"
            ],
            "description": "Type of issue identified"
          },
          "description": {
            "type": "string",
            "description": "Detailed explanation of the issue"
          },
          "line_number": {
            "type": "integer",
            "description": "Line where the issue occurs (if applicable)"
          },
          "recommendation": {
            "type": "string",
            "description": "Suggested fix or improvement"
          }
        },
        "required": ["severity", "category", "description", "recommendation"]
      }
    },
    "summary": {
      "type": "string",
      "description": "Overall assessment of the code"
    }
  },
  "required": ["issues", "summary"]
}
```

## Field Descriptions

### Issues Array

Each issue object contains:

- **severity**: Impact level of the issue
  - `high`: Critical problems that must be fixed
  - `medium`: Important issues that should be addressed
  - `low`: Minor issues or suggestions

- **category**: Type of issue
  - `security`: Security vulnerabilities
  - `performance`: Performance problems
  - `maintainability`: Code organization and clarity
  - `reliability`: Error handling and edge cases
  - `style`: Coding style and conventions
  - `documentation`: Documentation completeness

- **description**: Detailed explanation of what's wrong
- **line_number**: Specific line where issue occurs (optional)
- **recommendation**: Concrete steps to fix the issue

### Summary

A high-level overview of the code quality, including:

- Major strengths and weaknesses
- Overall patterns observed
- General recommendations

## Example Output

```json
{
  "issues": [
    {
      "severity": "high",
      "category": "security",
      "description": "SQL injection vulnerability in query construction",
      "line_number": 45,
      "recommendation": "Use parameterized queries instead of string concatenation"
    },
    {
      "severity": "medium",
      "category": "performance",
      "description": "Inefficient database query causing N+1 problem",
      "line_number": 78,
      "recommendation": "Use eager loading with JOIN clause"
    }
  ],
  "summary": "The code has significant security concerns that need immediate attention..."
}
