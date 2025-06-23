# Security Examples

This directory contains examples for security analysis, vulnerability scanning, and security automation using ostruct CLI.

## 🔒 Security & Data Privacy Notice

Please be aware of the following when using `ostruct` with different file routing options:

* **File Uploads to OpenAI Tools**:
  * Flags like `--file ci:`, `--dir ci:` (for Code Interpreter) and `--file fs:`, `--dir fs:` (for File Search) **will upload your files** to OpenAI's services for processing.
  * Ensure you understand OpenAI's data usage policies before using these options with sensitive data.

* **Template-Only Access & Prompt Content**:
  * Flags like `--file alias` (template-only, no target prefix) are designed for template-only access and **do not directly upload files to Code Interpreter or File Search services.**
  * **However, if your Jinja2 template includes the content of these files (e.g., using `{{ my_file.content }}`), that file content WILL become part of the prompt sent to the main OpenAI Chat Completions API.**
  * For large files or sensitive data that should not be part of the main prompt, even if used with template-only flags, avoid rendering their full content in the template or use redaction techniques.
  * If a large file is intended for analysis or search, prefer using `--file ci:` or `--file fs:` to optimize token usage and costs, and to prevent exceeding model context limits by inadvertently including its full content in the prompt. `ostruct` will issue a warning if you attempt to render the content of a large template-only file.

Always review which files are being routed to which tools and how their content is used in your templates to manage data privacy and API costs effectively.

For detailed information about data handling and security best practices, see the [Security Overview](../../docs/source/security/overview.rst) documentation.

## Available Examples

### [Vulnerability Scan](vulnerability-scan/)

**Three-approach automated security vulnerability scanning** with validated performance metrics:

* **Static Analysis**: 6,762 tokens, $0.18 cost (budget option)
* **Code Interpreter**: 6,406 tokens, $0.18 cost (recommended)
* **Hybrid Analysis**: 15,728 tokens, $0.20 cost (comprehensive)

**Features:**

* Professional-grade vulnerability detection
* CWE IDs and OWASP category mapping
* Specific remediation recommendations
* Directory-based project analysis
* Evidence-based severity assessment

**Best For:** Automated security scanning, CI/CD integration, security audits

## Getting Started

1. Navigate to any example directory
2. Read the specific README.md for detailed usage instructions
3. Ensure you have proper authorization before scanning any code
4. Start with the provided test/demo files

## Usage Patterns

All security examples support:

* **Single file analysis**: For focused security review
* **Directory analysis**: For comprehensive project scanning
* **Multi-tool integration**: Code Interpreter + File Search + Template routing
* **CI/CD integration**: Automated security scanning in pipelines

## Contributing

When adding new security examples:

1. Include comprehensive security warnings
2. Provide test/demo data (never real sensitive code)
3. Document cost estimates and token usage
4. Include validation of accuracy with test cases
5. Follow the established directory structure pattern
