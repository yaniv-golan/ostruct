# Configuration Validation Schema Reference

This document describes the JSON schema used for configuration validation results.

## Schema Overview

The validation results follow a structured schema defined in `schemas/validation_result.json`. The schema is designed to provide detailed, actionable feedback about configuration issues.

## Core Structure

```json
{
  "validation_results": [
    {
      "file_path": "string",
      "is_valid": "boolean",
      "findings": [
        {
          "severity": "string",
          "message": "string",
          "location": {
            "line": "integer",
            "column": "integer",
            "path": "string"
          }
        }
      ]
    }
  ],
  "summary": {
    "total_files": "integer",
    "valid_files": "integer",
    "total_findings": "integer"
  }
}
```

## Field Descriptions

### Validation Results

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Relative path to the configuration file |
| `is_valid` | boolean | Whether the configuration is valid |
| `findings` | array | List of validation findings |
| `metadata` | object | Additional file metadata |

### Finding

| Field | Type | Description |
|-------|------|-------------|
| `severity` | string | One of: error, warning, info, security |
| `message` | string | Human-readable description |
| `location` | object | Where the issue was found |
| `suggestion` | string | (Optional) How to fix the issue |
| `context` | object | (Optional) Additional context |

### Location

| Field | Type | Description |
|-------|------|-------------|
| `line` | integer | Line number (1-based) |
| `column` | integer | Column number (1-based) |
| `path` | string | JSON/YAML path to the field |

### Context

| Field | Type | Description |
|-------|------|-------------|
| `related_files` | array | Other relevant files |
| `documentation` | string | Link to documentation |
| `best_practice` | string | Best practice description |

### Summary

| Field | Type | Description |
|-------|------|-------------|
| `total_files` | integer | Number of files analyzed |
| `valid_files` | integer | Number of valid files |
| `total_findings` | integer | Total number of findings |
| `findings_by_severity` | object | Count of findings by severity |

## Example Output

```json
{
  "validation_results": [
    {
      "file_path": "config/production.yaml",
      "is_valid": false,
      "findings": [
        {
          "severity": "security",
          "message": "Database password should not be hardcoded",
          "location": {
            "line": 12,
            "column": 3,
            "path": "database.password"
          },
          "suggestion": "Use environment variable: ${DB_PASSWORD}",
          "context": {
            "documentation": "https://example.com/docs/security",
            "best_practice": "Store sensitive values in environment variables"
          }
        }
      ],
      "metadata": {
        "environment": "production",
        "last_modified": "2024-01-27T10:30:00Z"
      }
    }
  ],
  "summary": {
    "total_files": 1,
    "valid_files": 0,
    "total_findings": 1,
    "findings_by_severity": {
      "security": 1,
      "error": 0,
      "warning": 0,
      "info": 0
    }
  }
}
```

## Severity Levels

### Error

- Configuration will not work
- Must be fixed before deployment
- Example: Invalid YAML syntax

### Warning

- Configuration may cause issues
- Should be reviewed and fixed
- Example: Deprecated field usage

### Info

- Suggestions for improvement
- Not critical but recommended
- Example: Missing optional documentation

### Security

- Security-related issues
- Must be addressed for production
- Example: Hardcoded credentials

## Cross-Environment Issues

The schema includes support for cross-environment validation:

```json
{
  "cross_environment_issues": [
    {
      "description": "Inconsistent database pool sizes",
      "affected_environments": ["dev", "prod"]
    }
  ]
}
```

## Using the Schema

### Validation

Use JSON Schema validation tools to ensure your output matches:

```bash
jsonschema -i results.json schemas/validation_result.json
```

### Integration

The schema is designed for easy integration with:

- CI/CD pipelines
- Monitoring systems
- Documentation generators
- Custom tooling

### Extensions

The schema can be extended with custom fields:

1. Add new properties to the schema
2. Update validation logic
3. Maintain backward compatibility
