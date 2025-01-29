# Automated Code Review

This use case demonstrates how to perform automated code reviews on multiple files using the OpenAI Structured CLI. It analyzes code for potential issues related to security, style, complexity, and more, producing a structured JSON output that can be integrated into CI/CD pipelines.

## Features

- Multi-file code analysis in a single pass
- Structured output following a defined schema
- Security vulnerability detection
- Code style and best practices checking
- Performance issue identification
- Documentation completeness analysis

## Files

- `system_prompt.yaml`: Configures the AI to act as a thorough code reviewer
- `task.j2`: Template for processing source code files
- `schema.json`: Defines the structure of the review output
- `run.sh`: Script to execute the code review
- `sample_input/`: Example code files to demonstrate the review process

## Usage

1. **Basic Usage**:

   ```bash
   ./run.sh path/to/your/code
   ```

2. **With Custom Extensions**:

   ```bash
   ./run.sh path/to/your/code --ext py,js,ts
   ```

3. **Output to File**:

   ```bash
   ./run.sh path/to/your/code --output-file review_results.json
   ```

## Sample Input

The `sample_input/` directory contains example files demonstrating various code patterns:

- Security vulnerabilities
- Style issues
- Performance concerns
- Documentation gaps

## Output Format

The review results follow this structure:

```json
{
  "reviews": [
    {
      "file": "path/to/file.py",
      "issues": [
        {
          "severity": "major",
          "category": "security",
          "description": "Hardcoded credentials found",
          "line_number": 45,
          "recommendation": "Move credentials to environment variables"
        }
      ],
      "summary": "Overall file assessment..."
    }
  ],
  "overall_summary": "Project-wide summary..."
}
```

## Integration

### GitHub Actions

```yaml
- name: Run Code Review
  run: |
    ostruct \
      --task @review.j2 \
      --schema review_schema.json \
      --dir code=. \
      --ext py,js,ts \
      --recursive \
      --output-file review_results.json
```

### GitLab CI

```yaml
code_review:
  script:
    - ostruct --task @review.j2 --schema review_schema.json --dir code=. --recursive
```

## Customization

1. Modify `system_prompt.yaml` to focus on specific aspects (security, performance, etc.)
2. Adjust `schema.json` to capture additional metadata
3. Update `task.j2` to change how files are processed
4. Edit `run.sh` to add preprocessing steps

## Prerequisites

- OpenAI Structured CLI installed
- OpenAI API key configured
- Files to review

## Limitations

- Large files (>100KB) are processed in chunks
- Binary files are skipped
- Generated code is excluded by default
