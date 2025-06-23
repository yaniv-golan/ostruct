# Code Quality Examples

This directory contains examples for automated code quality analysis, code review, and quality assurance using ostruct CLI with multi-tool integration.

## 🔒 Security & Data Privacy Notice

Please be aware of the following when using `ostruct` with different file routing options:

* **File Uploads to OpenAI Tools**:
  * Flags like `--file ci:`, `--dir ci:` (for Code Interpreter) and `--file fs:`, `--dir fs:` (for File Search) **will upload your files** to OpenAI's services for processing.
  * Ensure you understand OpenAI's data usage policies before using these options with sensitive data.

* **Template-Only Access & Prompt Content**:
  * Flags like `--file alias` (template-only) are designed for template-only access and **do not directly upload files to Code Interpreter or File Search services.**
  * **However, if your Jinja2 template includes the content of these files (e.g., using `{{ my_file.content }}`), that file content WILL become part of the prompt sent to the main OpenAI Chat Completions API.**
  * For large files or sensitive data that should not be part of the main prompt, even if used with template-only flags, avoid rendering their full content in the template or use redaction techniques.
  * If a large file is intended for analysis or search, prefer using `--file ci:` or `--file fs:` to optimize token usage and costs, and to prevent exceeding model context limits by inadvertently including its full content in the prompt. `ostruct` will issue a warning if you attempt to render the content of a large template-only file.

Always review which files are being routed to which tools and how their content is used in your templates to manage data privacy and API costs effectively.

For detailed information about data handling and security best practices, see the [Security Overview](../../docs/source/security/overview.rst) documentation.

## Available Examples

### [Code Review](code-review/)

**Comprehensive automated code review system** with multi-tool integration:

**Features:**

* Security vulnerability detection with specific line numbers
* Performance issue identification (N+1 queries, complexity)
* Code style and best practices analysis
* Documentation completeness assessment
* Multi-file analysis in single pass
* CI/CD pipeline integration

**Validation Results:**

* **Security analysis**: Found 5 high-severity, 2 medium-severity issues
* **Performance analysis**: Correctly identified N+1 query problems
* **Output quality**: Professional-grade analysis with actionable recommendations
* **Integration**: Works seamlessly with GitHub Actions, GitLab CI, Jenkins

**Best For:** Code review automation, CI/CD quality gates, development workflow integration

## Key Features

### Multi-Tool Integration

All code quality examples leverage ostruct's enhanced capabilities:

* **Code Interpreter**: Execute code for dynamic analysis
* **File Search**: Search documentation for best practices context
* **Template Routing**: Handle configuration files efficiently
* **Combined Analysis**: Comprehensive quality assessment

### Output Quality

**Professional-Grade Results:**

* Specific line numbers and code snippets
* Actionable remediation suggestions
* Risk assessment and severity scoring
* Schema-compliant JSON output for automation

### Usage Patterns

**Directory Routing:**

```bash
# Analyze entire codebase
--dir ci:code examples/security --recursive
```

**Individual File Routing:**

```bash
# Target specific files
--file ci:code file.py
```

**Multi-Tool Combination:**

```bash
# Code + documentation + configuration
--dir ci:code src/ --dir fs:docs docs/ --file config config.yaml
```

## Getting Started

1. Navigate to any example directory
2. Review the specific README.md for usage instructions
3. Start with provided sample code
4. Customize templates and schemas for your needs

## Integration Examples

### CI/CD Integration

* GitHub Actions workflows
* GitLab CI configuration
* Jenkins pipeline integration
* Automated quality gates

### Development Workflow

* Pre-commit hook integration
* IDE plugin compatibility
* Code review automation
* Quality metrics tracking

## Contributing

When adding new code quality examples:

1. Provide comprehensive sample code with known issues
2. Include validation results with specific findings
3. Document expected outputs and interpretation
4. Follow established directory structure
5. Include CI/CD integration examples
