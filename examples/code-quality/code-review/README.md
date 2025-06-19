# Automated Code Review

This use case demonstrates how to perform automated code reviews using ostruct CLI with both traditional and enhanced multi-tool capabilities. It analyzes code for potential issues related to security, style, complexity, and more, producing structured JSON output that can be integrated into CI/CD pipelines.

## 🔒 Security & Data Privacy Notice

Please be aware of the following when using `ostruct` with different file routing options:

* **File Uploads to OpenAI Tools**:
  * Flags like `-fc`, `--fca`, `-dc`, `--dca` (for Code Interpreter) and `-fs`, `--fsa`, `-ds`, `--dsa` (for File Search) **will upload your files** to OpenAI's services for processing.
  * Ensure you understand OpenAI's data usage policies before using these options with sensitive data.

* **Template-Only Access & Prompt Content**:
  * Flags like `-ft`, `--fta`, `-dt`, `--dta` (and legacy `-f`, `-d`) are designed for template-only access and **do not directly upload files to Code Interpreter or File Search services.**
  * **However, if your Jinja2 template includes the content of these files (e.g., using `{{ my_file.content }}`), that file content WILL become part of the prompt sent to the main OpenAI Chat Completions API.**
  * For large files or sensitive data that should not be part of the main prompt, even if used with `-ft`, avoid rendering their full content in the template or use redaction techniques.
  * If a large file is intended for analysis or search, prefer using `-fc`/`-fs` to optimize token usage and costs, and to prevent exceeding model context limits by inadvertently including its full content in the prompt. `ostruct` will issue a warning if you attempt to render the content of a large template-only file.

Always review which files are being routed to which tools and how their content is used in your templates to manage data privacy and API costs effectively.

For detailed information about data handling and security best practices, see the [Security Overview](../../../docs/source/security/overview.rst) documentation.

**Alternative**: Use template-only options (`-ft`, `-dt`) for local-only processing without uploads.

## Features

### Core Analysis

* Multi-file code analysis in a single pass
* Structured output following a defined schema
* Security vulnerability detection
* Code style and best practices checking
* Performance issue identification
* Documentation completeness analysis

### Enhanced Multi-Tool Integration

* **Code Interpreter**: Execute code snippets for dynamic analysis
* **File Search**: Search documentation for context and best practices
* **Explicit File Routing**: Optimize processing through targeted file routing
* **Configuration System**: Persistent settings for consistent reviews

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

## Problem This Solves

Manual code reviews are time-consuming and often miss subtle issues. This automated code review system provides consistent, comprehensive analysis that can catch security vulnerabilities, performance problems, and style violations before they reach production. It integrates seamlessly into CI/CD pipelines and provides structured feedback that developers can act on immediately.

### Traditional Usage (Unchanged)

These commands work exactly as before:

1. **Basic Directory Review**:

   ```bash
   # Traditional pattern (still works)
   ostruct run prompts/task.j2 schemas/code_review.json \
     -dc code examples/security \
     -R \
     --sys-file prompts/system.txt
   ```

2. **Pattern Matching**:

   ```bash
   # Traditional pattern matching (still works)
   ostruct run prompts/task.j2 schemas/code_review.json \
     -p code "*.py" \
     --sys-file prompts/system.txt
   ```

3. **Output to File**:

   ```bash
   # Traditional with output file (still works)
   ostruct run prompts/task.j2 schemas/code_review.json \
     -dc code examples/style \
     -R \
     --sys-file prompts/system.txt \
     --output-file style_review.json
   ```

### Enhanced Multi-Tool Usage

#### Code Interpreter Integration

Upload code for execution and dynamic analysis:

```bash
# Directory routing for code analysis
ostruct run prompts/task.j2 schemas/code_review.json \
  -dc security_code examples/security \
  --sys-file prompts/system.txt

# Individual file routing
ostruct run prompts/task.j2 schemas/code_review.json \
  -fc sql_injection examples/security/sql_injection.py \
  -fc perf_code examples/performance/n_plus_one.py \
  --sys-file prompts/system.txt

# Two-argument alias syntax (best tab completion)
ostruct run prompts/task.j2 schemas/code_review.json \
  --file-for-code-interpreter security_code examples/security/sql_injection.py \
  --file-for-code-interpreter performance_code examples/performance/n_plus_one.py \
  --file system_prompt prompts/system.txt
```

#### File Search for Documentation Context

Search documentation for best practices and context:

```bash
# Code review with documentation context
ostruct run prompts/task.j2 schemas/code_review.json \
  -dc security_code examples/security \
  -ds docs docs/ \
  --sys-file prompts/system.txt

# Template-only configuration files
ostruct run prompts/task.j2 schemas/code_review.json \
  -dc source_code source_code/ \
  -ds documentation documentation/ \
  -ft eslint_config .eslintrc.json \
  --sys-file prompts/system.txt
```

#### Multi-Tool Combination

Combine Code Interpreter and File Search for comprehensive analysis:

```bash
# Full multi-tool analysis
ostruct run prompts/task.j2 schemas/code_review.json \
  -dc security_code examples/security \
  -dc performance_code examples/performance \
  -ds docs docs/ \
  -ft config config.yaml \
  --sys-file prompts/system.txt \
  --output-file comprehensive_review.json
```

#### Configuration-Driven Workflows

Use persistent configuration for consistent reviews:

```bash
# Create ostruct.yaml
cat > ostruct.yaml << EOF
models:
  default: gpt-4o
tools:
  code_interpreter:
    auto_download: true
    output_directory: "./review_output"
  file_search:
    max_results: 15
operation:
  timeout_minutes: 30
limits:
  max_cost_per_run: 5.00
EOF

# Run with configuration
ostruct --config ostruct.yaml run prompts/task.j2 schemas/code_review.json \
  -dc src src/ \
  -ds docs docs/ \
  --sys-file prompts/system.txt
```

## Customization

See `docs/customization.md` in this directory for detailed instructions on:

* Modifying the review focus
* Adding custom rules
* Extending the schema
* Using your own examples

## Schema

The review results follow a structured schema defined in `schemas/code_review.json`. See `docs/schema.md` in this directory for:

* Complete schema documentation
* Field descriptions
* Example outputs

## CI/CD Integration

### GitHub Actions

#### Traditional Integration (Still Works)

```yaml
- name: Run Code Review
  run: |
    ostruct run prompts/task.j2 schemas/code_review.json \
      -dc code . \
      -R \
      -p code "*.{py,js,ts}" \
      --sys-file prompts/system.txt \
      --output-file review_results.json
```

#### Enhanced Multi-Tool Integration

```yaml
- name: Enhanced Code Review
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    # Create configuration
    cat > ci_config.yaml << EOF
    models:
      default: gpt-4o
    tools:
      code_interpreter:
        auto_download: true
      file_search:
        max_results: 20
    operation:
      timeout_minutes: 20
    limits:
      max_cost_per_run: 3.00
    EOF

    # Run enhanced analysis
    ostruct --config ci_config.yaml run prompts/task.j2 schemas/code_review.json \
      -dc src src/ \
      -dc tests tests/ \
      -ds docs docs/ \
      -dc workflows .github/workflows \
      --sys-file prompts/system.txt \
      --output-file enhanced_review.json
```

### GitLab CI

#### Traditional CI (Still Works)

```yaml
code_review:
  script:
    - ostruct run prompts/task.j2 schemas/code_review.json \
        -dc code . \
        -R \
        --sys-file prompts/system.txt
```

#### Enhanced CI with Multi-Tool Analysis

```yaml
enhanced_code_review:
  stage: analysis
  image: python:3.11
  before_script:
    - pip install ostruct-cli
  script:
    - |
      cat > .ostruct.yaml << EOF
      models:
        default: gpt-4o
      tools:
        code_interpreter:
          auto_download: true
          output_directory: "./ci_output"
      operation:
        timeout_minutes: 15
      limits:
        max_cost_per_run: 2.00
      EOF
    - |
      ostruct run prompts/task.j2 schemas/code_review.json \
        -dc src src/ \
        -ds documentation documentation/ \
        -dc ci ci/ \
        --sys-file prompts/system.txt \
        --output-file comprehensive_review.json
  artifacts:
    reports:
      junit: comprehensive_review.json
    paths:
      - comprehensive_review.json
      - ci_output/
  variables:
    OPENAI_API_KEY: $CI_OPENAI_API_KEY
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any

    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
    }

    stages {
        stage('Enhanced Code Review') {
            steps {
                script {
                    // Create configuration
                    writeFile file: 'jenkins_config.yaml', text: '''
models:
  default: gpt-4o
tools:
  code_interpreter:
    auto_download: true
    output_directory: "./jenkins_output"
  file_search:
    max_results: 25
operation:
  timeout_minutes: 25
limits:
  max_cost_per_run: 4.00
'''
                }

                sh '''
                    pip install ostruct-cli

                    ostruct --config jenkins_config.yaml run prompts/task.j2 schemas/code_review.json \
                      -dc src src/ \
                      -dc test test/ \
                      -ds docs docs/ \
                      -ft jenkinsfile Jenkinsfile \
                      --sys-file prompts/system.txt \
                      --output-file jenkins_review.json
                '''

                archiveArtifacts artifacts: 'jenkins_review.json,jenkins_output/**'

                script {
                    def review = readJSON file: 'jenkins_review.json'
                    if (review.critical_issues?.size() > 0) {
                        currentBuild.result = 'UNSTABLE'
                        echo "Found ${review.critical_issues.size()} critical issues"
                    }
                }
            }
        }
    }
}

## Prerequisites

- OpenAI Structured CLI installed
- OpenAI API key configured
- Files to review

## Limitations

- Large files (>100KB) are processed in chunks
- Binary files are skipped
- Generated code is excluded by default
