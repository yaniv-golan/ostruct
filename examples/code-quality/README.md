# Code Quality Examples

This directory contains examples for automated code quality analysis, code review, and quality assurance using ostruct CLI with multi-tool integration.

## 🔒 Security & Data Privacy Notice

**⚠️ IMPORTANT**: Examples in this directory use Code Interpreter (`-fc`, `-dc`) and File Search (`-fs`, `-ds`) features that, if used on your own. code, **upload your files to OpenAI's services** for processing.

**Before using with your code:**

- **Review data sensitivity** - Do not upload proprietary, confidential, or sensitive code
- **Check compliance policies** - Verify your organization allows code uploads to external services
- **Use test/demo code** - Examples include sample code for demonstration purposes

**For detailed security guidelines**, see the [Security Overview](../../docs/source/security/overview.rst) documentation.

## Available Examples

### [Code Review](code-review/)

**Comprehensive automated code review system** with multi-tool integration:

**Features:**

- Security vulnerability detection with specific line numbers
- Performance issue identification (N+1 queries, complexity)
- Code style and best practices analysis
- Documentation completeness assessment
- Multi-file analysis in single pass
- CI/CD pipeline integration

**Validation Results:**

- **Security analysis**: Found 5 high-severity, 2 medium-severity issues
- **Performance analysis**: Correctly identified N+1 query problems
- **Output quality**: Professional-grade analysis with actionable recommendations
- **Integration**: Works seamlessly with GitHub Actions, GitLab CI, Jenkins

**Best For:** Code review automation, CI/CD quality gates, development workflow integration

## Key Features

### Multi-Tool Integration

All code quality examples leverage ostruct's enhanced capabilities:

- **Code Interpreter**: Execute code for dynamic analysis
- **File Search**: Search documentation for best practices context
- **Template Routing**: Handle configuration files efficiently
- **Combined Analysis**: Comprehensive quality assessment

### Output Quality

**Professional-Grade Results:**

- Specific line numbers and code snippets
- Actionable remediation suggestions
- Risk assessment and severity scoring
- Schema-compliant JSON output for automation

### Usage Patterns

**Directory Routing:**

```bash
# Analyze entire codebase
--dca code examples/security -R
```

**Individual File Routing:**

```bash
# Target specific files
--fca code file.py
```

**Multi-Tool Combination:**

```bash
# Code + documentation + configuration
-dc code src/ -ds docs docs/ -ft config config.yaml
```

## Getting Started

1. Navigate to any example directory
2. Review the specific README.md for usage instructions
3. Start with provided sample code
4. Customize templates and schemas for your needs

## Integration Examples

### CI/CD Integration

- GitHub Actions workflows
- GitLab CI configuration
- Jenkins pipeline integration
- Automated quality gates

### Development Workflow

- Pre-commit hook integration
- IDE plugin compatibility
- Code review automation
- Quality metrics tracking

## Contributing

When adding new code quality examples:

1. Provide comprehensive sample code with known issues
2. Include validation results with specific findings
3. Document expected outputs and interpretation
4. Follow established directory structure
5. Include CI/CD integration examples
