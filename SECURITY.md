# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in ostruct itself (not in the example code), please report it by emailing [security contact] or creating a private security advisory on GitHub.

## Intentionally Vulnerable Code

⚠️ **Important Notice**: This repository contains intentionally vulnerable code for educational and demonstration purposes.

### Vulnerable Examples Directory

The following directory contains **intentionally insecure code** designed to demonstrate security vulnerabilities:

- `examples/security/vulnerability-scan/` - Contains deliberately vulnerable code samples for testing security scanning tools

### Security Scanning Exclusions

These directories should be **excluded from security scanning** as they contain intentional vulnerabilities:

```
examples/security/vulnerability-scan/examples/
examples/security/vulnerability-scan/test_code.py
```

### For Security Researchers

If you're using automated security scanning tools on this repository:

1. **Exclude the paths listed above** from your security analysis
2. Focus security testing on the **main application code** in `src/ostruct/`
3. The vulnerable examples are clearly marked and documented as intentional

### Safe Usage

- The vulnerable example code is isolated and not used in the main application
- Examples include clear warnings about their insecure nature
- Users are instructed to use these examples only in isolated environments

## Legitimate Security Concerns

Please report actual security issues in:

- Main application code (`src/ostruct/`)
- CLI interface and file handling
- Template processing and validation
- Dependency vulnerabilities in production code

**Do not report vulnerabilities found in `examples/security/vulnerability-scan/` as these are intentional.**
