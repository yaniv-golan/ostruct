# Security Examples

Advanced security analysis and vulnerability scanning using ostruct CLI with multi-tool integration.

## 🔒 Security & Data Privacy Notice

**⚠️ IMPORTANT**: These examples upload code and configuration files to OpenAI's Code Interpreter for analysis. Be mindful of:

- **Sensitive Information**: Remove API keys, passwords, and secrets before analysis
- **Proprietary Code**: Consider data sensitivity when uploading source code
- **Compliance Requirements**: Ensure uploads meet your organization's security policies

## Available Examples

### [Vulnerability Scan](vulnerability-scan/)

**Multi-approach automated security vulnerability scanning** - Static Analysis, Code Interpreter execution, and Hybrid Analysis with actionable security recommendations.

**Tools**: 🐍 Code Interpreter · 📄 File Search
**Cost**: ~$0.18-0.27 per analysis

## Key Features

- **Multi-Tool Integration**: Code Interpreter for dynamic analysis + File Search for documentation context
- **Comprehensive Coverage**: Static analysis, dynamic testing, and hybrid approaches
- **Actionable Results**: Specific remediation steps with code examples
- **Security Best Practices**: Industry-standard vulnerability classification

## Getting Started

```bash
# Quick validation
cd security/vulnerability-scan/
./run.sh --test-dry-run

# Live security scan
./run.sh --test-live

# Full vulnerability assessment
./run.sh --file code src/ --file config config/
```
