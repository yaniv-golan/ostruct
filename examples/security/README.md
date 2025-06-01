# Security Examples

This directory contains examples for security analysis, vulnerability scanning, and security automation using ostruct CLI.

## 🔒 Security & Data Privacy Notice

**⚠️ CRITICAL WARNING**: All examples in this directory use features that **upload your source code to OpenAI's services** for security analysis.

**Before using these examples:**

- **NEVER upload production code** - Only use test/demo code or properly sanitized examples
- **Review data sensitivity** - Source code may expose business logic, API endpoints, or sensitive information
- **Check compliance requirements** - Many organizations prohibit uploading source code to external services
- **Consider legal implications** - Code uploads may violate confidentiality agreements

**For detailed security guidelines**, see the [Security Overview](../../docs/source/security/overview.rst) documentation.

## Available Examples

### [Vulnerability Scan](vulnerability-scan/)

**Three-approach automated security vulnerability scanning** with validated performance metrics:

- **Static Analysis**: 6,762 tokens, $0.18 cost (budget option)
- **Code Interpreter**: 6,406 tokens, $0.18 cost (recommended)
- **Hybrid Analysis**: 15,728 tokens, $0.20 cost (comprehensive)

**Features:**

- Professional-grade vulnerability detection
- CWE IDs and OWASP category mapping
- Specific remediation recommendations
- Directory-based project analysis
- Evidence-based severity assessment

**Best For:** Automated security scanning, CI/CD integration, security audits

## Getting Started

1. Navigate to any example directory
2. Read the specific README.md for detailed usage instructions
3. Ensure you have proper authorization before scanning any code
4. Start with the provided test/demo files

## Usage Patterns

All security examples support:

- **Single file analysis**: For focused security review
- **Directory analysis**: For comprehensive project scanning
- **Multi-tool integration**: Code Interpreter + File Search + Template routing
- **CI/CD integration**: Automated security scanning in pipelines

## Contributing

When adding new security examples:

1. Include comprehensive security warnings
2. Provide test/demo data (never real sensitive code)
3. Document cost estimates and token usage
4. Include validation of accuracy with test cases
5. Follow the established directory structure pattern
