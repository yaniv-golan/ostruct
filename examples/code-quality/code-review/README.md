# Automated Code Review

This use case demonstrates how to perform automated code reviews on multiple files using the OpenAI Structured CLI. It analyzes code for potential issues related to security, style, complexity, and more, producing a structured JSON output that can be integrated into CI/CD pipelines.

## Features

- Multi-file code analysis in a single pass
- Structured output following a defined schema
- Security vulnerability detection
- Code style and best practices checking
- Performance issue identification
- Documentation completeness analysis

## Directory Structure

```
.
├── README.md           # This file
├── prompts/           # AI prompts
│   ├── system.txt     # AI's role and expertise
│   └── task.j2        # Review request template
├── schemas/           # Output structure
│   └── code_review.json
├── examples/          # Sample code to review
│   ├── security/      # Security vulnerabilities
│   │   ├── env_leak.py     # Environment variable exposure
│   │   ├── sql_injection.py # SQL injection vulnerability
│   │   └── xss.py          # Cross-site scripting (XSS)
│   ├── performance/   # Performance issues
│   │   └── n_plus_one.py   # N+1 query problem
│   └── style/         # Style violations
│       └── complex_function.py # Multiple style issues
└── docs/             # Example documentation
    ├── customization.md  # How to customize
    └── schema.md        # Schema reference
```

## Usage

1. **Basic Usage**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/code_review.json \
     -d code path/to/your/code \
     -R \
     --sys-file prompts/system.txt
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/code_review.json \
     -d code examples/security \
     -R \
     --sys-file prompts/system.txt
   ```

2. **With Custom Extensions**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/code_review.json \
     -d code path/to/your/code \
     -R \
     -p code "*.{py,js,ts}" \
     --sys-file prompts/system.txt
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/code_review.json \
     -d code examples/performance \
     -R \
     -p code "*.py" \
     --sys-file prompts/system.txt
   ```

3. **Output to File**:

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/code_review.json \
     -d code path/to/your/code \
     -R \
     --sys-file prompts/system.txt \
     --output-file review_results.json
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/code_review.json \
     -d code examples/style \
     -R \
     --sys-file prompts/system.txt \
     --output-file style_review.json
   ```

## Customization

See `docs/customization.md` in this directory for detailed instructions on:

- Modifying the review focus
- Adding custom rules
- Extending the schema
- Using your own examples

## Schema

The review results follow a structured schema defined in `schemas/code_review.json`. See `docs/schema.md` in this directory for:

- Complete schema documentation
- Field descriptions
- Example outputs

## Integration

### GitHub Actions

```yaml
- name: Run Code Review
  run: |
    ostruct run prompts/task.j2 schemas/code_review.json \
      -d code . \
      -R \
      -p code "*.{py,js,ts}" \
      --sys-file prompts/system.txt \
      --output-file review_results.json
```

### GitLab CI

```yaml
code_review:
  script:
    - ostruct run prompts/task.j2 schemas/code_review.json \
        -d code . \
        -R \
        --sys-file prompts/system.txt
```

## Prerequisites

- OpenAI Structured CLI installed
- OpenAI API key configured
- Files to review

## Limitations

- Large files (>100KB) are processed in chunks
- Binary files are skipped
- Generated code is excluded by default
