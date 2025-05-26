# CI/CD Automation with Enhanced ostruct

This example demonstrates how to leverage ostruct's enhanced multi-tool capabilities in CI/CD pipelines for automated analysis, reporting, and quality assurance.

## Overview

This example shows CI/CD automation patterns using:
- **Configuration Management**: Persistent settings for consistent CI runs
- **Multi-Tool Integration**: Code analysis, documentation search, and execution
- **Cost Controls**: Budget management for automated workflows
- **Progress Reporting**: Clear visibility in CI logs
- **Error Handling**: Robust failure management and retry logic

## Directory Structure

```
.
├── README.md                    # This file
├── .github/
│   └── workflows/
│       ├── analysis.yml         # GitHub Actions workflow
│       ├── security-scan.yml    # Security analysis
│       └── test-generation.yml  # Automated test generation
├── .gitlab-ci.yml              # GitLab CI configuration
├── Jenkinsfile                 # Jenkins pipeline
├── ci/
│   ├── ostruct.yaml            # CI-specific ostruct configuration
│   ├── security.yaml           # Security scanning configuration
│   └── scripts/
│       ├── analysis.sh         # Analysis automation script
│       ├── cost-monitor.py     # Cost monitoring utility
│       └── health-check.sh     # Pre-run health checks
├── prompts/
│   ├── ci-analysis.j2          # CI-specific analysis template
│   ├── security-scan.j2        # Security scanning template
│   ├── test-generation.j2      # Test generation template
│   └── system-ci.txt           # CI system prompt
├── schemas/
│   ├── ci_analysis.json        # CI analysis output schema
│   ├── security_report.json    # Security report schema
│   └── test_results.json       # Test generation schema
└── examples/
    ├── successful-runs/        # Example successful outputs
    ├── failure-scenarios/      # Handling failure cases
    └── cost-optimization/      # Cost reduction examples
```

## GitHub Actions Examples

### Comprehensive Analysis Pipeline

**.github/workflows/analysis.yml**:
```yaml
name: Enhanced Code Analysis
on: 
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  analysis:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for better analysis
          
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install Dependencies
        run: |
          pip install ostruct-cli
          
      - name: Health Check
        run: |
          # Verify API key and configuration
          if [ -z "$OPENAI_API_KEY" ]; then
            echo "❌ OPENAI_API_KEY not set"
            exit 1
          fi
          
          # Test basic functionality
          echo "test" | ostruct run <(echo "{{ stdin }}") <(echo '{"type":"string"}') >/dev/null
          echo "✅ ostruct health check passed"
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          
      - name: Multi-Tool Code Analysis
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          ostruct --config ci/ostruct.yaml run prompts/ci-analysis.j2 schemas/ci_analysis.json \
            -fc src/ \
            -fc tests/ \
            -fs docs/ \
            -fs README.md \
            -ft ci/ \
            --sys-file prompts/system-ci.txt \
            --progress-level basic \
            --output-file analysis_results.json
            
      - name: Security Scan
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          ostruct --config ci/security.yaml run prompts/security-scan.j2 schemas/security_report.json \
            -fc src/ \
            -fs security_docs/ \
            --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
            --sys-file prompts/system-ci.txt \
            -V repo_owner=${{ github.repository_owner }} \
            -V repo_name=${{ github.event.repository.name }} \
            --output-file security_report.json
            
      - name: Check Results
        run: |
          # Parse results and set job status
          python ci/scripts/cost-monitor.py analysis_results.json
          
          # Check for critical issues
          if python -c "
          import json
          with open('analysis_results.json') as f:
              data = json.load(f)
              critical = data.get('critical_issues', [])
              if len(critical) > 0:
                  print(f'❌ Found {len(critical)} critical issues')
                  exit(1)
              print('✅ No critical issues found')
          "; then
            echo "Analysis passed"
          else
            echo "Analysis failed"
            exit 1
          fi
          
      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: analysis-results
          path: |
            analysis_results.json
            security_report.json
            ci_output/
          retention-days: 30
          
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const analysis = JSON.parse(fs.readFileSync('analysis_results.json', 'utf8'));
            
            const comment = `## 🤖 ostruct Analysis Results
            
            **Quality Score**: ${analysis.quality_score}/100
            **Issues Found**: ${analysis.issues.length}
            **Cost**: $${analysis.estimated_cost.toFixed(4)}
            
            ${analysis.summary}
            
            <details>
            <summary>View Details</summary>
            
            ${analysis.issues.map(issue => `- **${issue.severity}**: ${issue.description}`).join('\n')}
            
            </details>`;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Security-Focused Pipeline

**.github/workflows/security-scan.yml**:
```yaml
name: Security Analysis
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install ostruct
        run: pip install ostruct-cli
        
      - name: Security Analysis
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          # Create security-focused configuration
          cat > security_config.yaml << EOF
          models:
            default: gpt-4o
          tools:
            code_interpreter:
              auto_download: true
              output_directory: "./security_analysis"
            file_search:
              max_results: 30
          mcp:
            deepwiki: "https://mcp.deepwiki.com/sse"
          operation:
            timeout_minutes: 45
            retry_attempts: 2
          limits:
            max_cost_per_run: 5.00
            warn_expensive_operations: true
          EOF
          
          # Run comprehensive security scan
          ostruct --config security_config.yaml run prompts/security-scan.j2 schemas/security_report.json \
            -fc src/ \
            -fc config/ \
            -fs security_docs/ \
            --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
            --sys-file prompts/system-ci.txt \
            -V scan_type=comprehensive \
            -V repo_owner=${{ github.repository_owner }} \
            -V repo_name=${{ github.event.repository.name }} \
            --output-file security_report.json
            
      - name: Create Security Issue
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            if (fs.existsSync('security_report.json')) {
              const report = JSON.parse(fs.readFileSync('security_report.json', 'utf8'));
              
              if (report.critical_vulnerabilities && report.critical_vulnerabilities.length > 0) {
                await github.rest.issues.create({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  title: `🚨 Critical Security Vulnerabilities Found`,
                  body: `Critical security issues detected in automated scan:\n\n${report.summary}`,
                  labels: ['security', 'critical']
                });
              }
            }
```

## GitLab CI Configuration

**.gitlab-ci.yml**:
```yaml
stages:
  - health-check
  - analysis
  - security
  - report

variables:
  OSTRUCT_CONFIG: "ci/ostruct.yaml"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

health_check:
  stage: health-check
  image: python:3.11
  before_script:
    - pip install ostruct-cli
  script:
    - ci/scripts/health-check.sh
  only:
    - merge_requests
    - main

code_analysis:
  stage: analysis
  image: python:3.11
  before_script:
    - pip install ostruct-cli
  script:
    - |
      ostruct --config $OSTRUCT_CONFIG run prompts/ci-analysis.j2 schemas/ci_analysis.json \
        -fc src/ \
        -fc tests/ \
        -fs docs/ \
        -ft ci/ \
        --sys-file prompts/system-ci.txt \
        --progress-level basic \
        --output-file analysis_results.json
  artifacts:
    reports:
      junit: analysis_results.json
    paths:
      - analysis_results.json
      - ci_output/
    expire_in: 1 week
  variables:
    OPENAI_API_KEY: $CI_OPENAI_API_KEY

security_scan:
  stage: security
  image: python:3.11
  before_script:
    - pip install ostruct-cli
  script:
    - |
      ostruct --config ci/security.yaml run prompts/security-scan.j2 schemas/security_report.json \
        -fc src/ \
        -fs security_docs/ \
        --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
        --sys-file prompts/system-ci.txt \
        -V repo_owner=$CI_PROJECT_NAMESPACE \
        -V repo_name=$CI_PROJECT_NAME \
        --output-file security_report.json
  artifacts:
    paths:
      - security_report.json
    expire_in: 1 month
  variables:
    OPENAI_API_KEY: $CI_OPENAI_API_KEY
  only:
    - schedules
    - main

generate_report:
  stage: report
  image: python:3.11
  dependencies:
    - code_analysis
    - security_scan
  script:
    - python ci/scripts/generate-report.py
  artifacts:
    paths:
      - final_report.html
    expire_in: 1 month
```

## Jenkins Pipeline

**Jenkinsfile**:
```groovy
pipeline {
    agent any
    
    parameters {
        choice(
            name: 'ANALYSIS_TYPE',
            choices: ['basic', 'comprehensive', 'security-focused'],
            description: 'Type of analysis to run'
        )
        booleanParam(
            name: 'ENABLE_MCP',
            defaultValue: true,
            description: 'Enable MCP server integration'
        )
    }
    
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
        OSTRUCT_CONFIG = 'ci/ostruct.yaml'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    pip install ostruct-cli
                    chmod +x ci/scripts/*.sh
                '''
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    def healthCheck = sh(
                        script: 'ci/scripts/health-check.sh',
                        returnStatus: true
                    )
                    if (healthCheck != 0) {
                        error("Health check failed")
                    }
                }
            }
        }
        
        stage('Analysis') {
            parallel {
                stage('Code Analysis') {
                    steps {
                        script {
                            def mcpFlag = params.ENABLE_MCP ? 
                                '--mcp-server deepwiki@https://mcp.deepwiki.com/sse' : ''
                            
                            sh """
                                ostruct --config \$OSTRUCT_CONFIG run prompts/ci-analysis.j2 schemas/ci_analysis.json \\
                                  -fc src/ \\
                                  -fc tests/ \\
                                  -fs docs/ \\
                                  -ft ci/ \\
                                  ${mcpFlag} \\
                                  --sys-file prompts/system-ci.txt \\
                                  --output-file analysis_results.json
                            """
                        }
                    }
                }
                
                stage('Security Scan') {
                    when {
                        anyOf {
                            branch 'main'
                            expression { params.ANALYSIS_TYPE == 'security-focused' }
                        }
                    }
                    steps {
                        sh '''
                            ostruct --config ci/security.yaml run prompts/security-scan.j2 schemas/security_report.json \\
                              -fc src/ \\
                              -fs security_docs/ \\
                              --mcp-server deepwiki@https://mcp.deepwiki.com/sse \\
                              --sys-file prompts/system-ci.txt \\
                              --output-file security_report.json
                        '''
                    }
                }
            }
        }
        
        stage('Cost Monitoring') {
            steps {
                script {
                    sh 'python ci/scripts/cost-monitor.py analysis_results.json'
                    
                    // Check if costs are within budget
                    def costReport = readJSON file: 'cost_report.json'
                    if (costReport.total_cost > 5.0) {
                        warning("Analysis cost ${costReport.total_cost} exceeds budget")
                    }
                }
            }
        }
        
        stage('Quality Gate') {
            steps {
                script {
                    def analysis = readJSON file: 'analysis_results.json'
                    
                    if (analysis.quality_score < 70) {
                        unstable("Quality score ${analysis.quality_score} below threshold")
                    }
                    
                    if (analysis.critical_issues && analysis.critical_issues.size() > 0) {
                        error("Found ${analysis.critical_issues.size()} critical issues")
                    }
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: '*.json, ci_output/**', allowEmptyArchive: true
            
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'ci_output',
                reportFiles: 'index.html',
                reportName: 'ostruct Analysis Report'
            ])
        }
        
        failure {
            emailext (
                subject: "❌ ostruct Analysis Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: """
                The ostruct analysis pipeline has failed.
                
                Job: ${env.JOB_NAME}
                Build: ${env.BUILD_NUMBER}
                URL: ${env.BUILD_URL}
                
                Please check the logs for details.
                """,
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
        
        success {
            script {
                if (currentBuild.previousBuild?.result == 'FAILURE') {
                    emailext (
                        subject: "✅ ostruct Analysis Recovered: ${env.JOB_NAME}",
                        body: "The ostruct analysis pipeline is now passing.",
                        to: "${env.CHANGE_AUTHOR_EMAIL}"
                    )
                }
            }
        }
    }
}
```

## Configuration Examples

### CI-Optimized Configuration

**ci/ostruct.yaml**:
```yaml
models:
  default: gpt-4o

tools:
  code_interpreter:
    auto_download: true
    output_directory: "./ci_output"
  file_search:
    max_results: 15

mcp:
  deepwiki: "https://mcp.deepwiki.com/sse"

operation:
  timeout_minutes: 20
  retry_attempts: 2
  require_approval: never

limits:
  max_cost_per_run: 3.00
  warn_expensive_operations: true
```

### Security-Focused Configuration

**ci/security.yaml**:
```yaml
models:
  default: gpt-4o

tools:
  code_interpreter:
    auto_download: true
    output_directory: "./security_analysis"
  file_search:
    max_results: 25

mcp:
  deepwiki: "https://mcp.deepwiki.com/sse"

operation:
  timeout_minutes: 30
  retry_attempts: 3
  require_approval: never

limits:
  max_cost_per_run: 5.00
  warn_expensive_operations: true
```

## Automation Scripts

### Health Check Script

**ci/scripts/health-check.sh**:
```bash
#!/bin/bash
set -euo pipefail

echo "🔍 Running ostruct health checks..."

# Check API key
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "❌ OPENAI_API_KEY not set"
    exit 1
fi

# Check configuration files
for config in ci/ostruct.yaml ci/security.yaml; do
    if [ ! -f "$config" ]; then
        echo "❌ Configuration file missing: $config"
        exit 1
    fi
    
    if ! python -c "import yaml; yaml.safe_load(open('$config'))" 2>/dev/null; then
        echo "❌ Invalid YAML in $config"
        exit 1
    fi
done

# Test basic functionality
if echo "test" | ostruct run <(echo "{{ stdin }}") <(echo '{"type":"string"}') >/dev/null 2>&1; then
    echo "✅ Basic functionality test passed"
else
    echo "❌ Basic functionality test failed"
    exit 1
fi

# Check template files
for template in prompts/*.j2; do
    if [ -f "$template" ]; then
        if python -c "from jinja2 import Template; Template(open('$template').read())" 2>/dev/null; then
            echo "✅ Template valid: $(basename "$template")"
        else
            echo "❌ Template invalid: $(basename "$template")"
            exit 1
        fi
    fi
done

echo "✅ All health checks passed"
```

### Cost Monitor Script

**ci/scripts/cost-monitor.py**:
```python
#!/usr/bin/env python3
"""Monitor and report ostruct costs in CI/CD."""

import json
import sys
from pathlib import Path
from datetime import datetime

def monitor_costs(results_file):
    """Monitor costs from ostruct results."""
    
    if not Path(results_file).exists():
        print(f"❌ Results file not found: {results_file}")
        return 1
    
    with open(results_file) as f:
        results = json.load(f)
    
    cost = results.get('estimated_cost', 0)
    tokens = results.get('total_tokens', 0)
    
    print(f"💰 Analysis Cost: ${cost:.4f}")
    print(f"🎯 Tokens Used: {tokens:,}")
    
    # Cost thresholds
    budget = float(os.environ.get('COST_BUDGET', '3.00'))
    warning_threshold = budget * 0.8
    
    if cost > budget:
        print(f"❌ Cost ${cost:.4f} exceeds budget ${budget:.2f}")
        return 1
    elif cost > warning_threshold:
        print(f"⚠️  Cost ${cost:.4f} approaching budget ${budget:.2f}")
    else:
        print(f"✅ Cost within budget: ${cost:.4f} / ${budget:.2f}")
    
    # Log cost data
    cost_log = {
        'timestamp': datetime.now().isoformat(),
        'cost': cost,
        'tokens': tokens,
        'budget': budget,
        'status': 'within_budget' if cost <= budget else 'over_budget'
    }
    
    with open('cost_report.json', 'w') as f:
        json.dump(cost_log, f, indent=2)
    
    return 0

if __name__ == '__main__':
    sys.exit(monitor_costs(sys.argv[1]))
```

## Best Practices for CI/CD

### 1. Configuration Management
- Use environment-specific configuration files
- Set appropriate cost limits for automated runs
- Configure timeouts to prevent hanging
- Use `require_approval: never` for unattended operation

### 2. Error Handling
- Implement health checks before analysis
- Use retry logic with exponential backoff
- Parse results and set appropriate job status
- Provide clear error messages and next steps

### 3. Cost Control
- Set strict budget limits in configuration
- Monitor costs in real-time
- Use explicit file routing to optimize processing
- Cache results when possible

### 4. Security
- Store API keys securely using CI/CD secrets
- Use least-privilege access for service accounts
- Validate all configuration files
- Implement audit logging

### 5. Monitoring and Reporting
- Archive all outputs and analysis results
- Generate human-readable reports
- Set up notifications for failures and anomalies
- Track performance metrics over time

This comprehensive CI/CD automation example demonstrates how ostruct's enhanced capabilities can transform automated analysis workflows, providing better results while maintaining cost control and operational reliability.