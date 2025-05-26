# Automation Updates Migration

This example demonstrates how to migrate existing CI/CD scripts and automation workflows to use ostruct's enhanced multi-tool capabilities.

## Overview

This guide covers:
- **CI/CD Script Migration**: Update existing automation scripts
- **Configuration Management**: Centralized settings for automation
- **Cost Controls**: Prevent runaway costs in automated environments
- **Error Handling**: Robust automation with proper failure management
- **Monitoring**: Track performance and costs in automation

## Directory Structure

```
.
├── README.md                    # This file
├── before/                     # Original automation scripts
│   ├── github-actions.yml      # Original GitHub Actions
│   ├── gitlab-ci.yml           # Original GitLab CI
│   ├── jenkins-pipeline.groovy # Original Jenkins
│   └── analysis-script.sh      # Original analysis script
├── after/                      # Enhanced automation scripts
│   ├── enhanced-github.yml     # Enhanced GitHub Actions
│   ├── enhanced-gitlab.yml     # Enhanced GitLab CI
│   ├── enhanced-jenkins.groovy # Enhanced Jenkins
│   └── enhanced-script.sh      # Enhanced analysis script
├── configs/                    # Automation configurations
│   ├── ci-basic.yaml           # Basic CI configuration
│   ├── ci-advanced.yaml        # Advanced CI configuration
│   ├── security-scan.yaml      # Security-focused config
│   └── cost-controlled.yaml    # Cost-controlled config
├── scripts/                    # Migration utilities
│   ├── migrate-ci.py           # CI migration tool
│   ├── validate-automation.sh  # Automation validation
│   ├── cost-monitor.py         # Cost monitoring
│   └── health-check.sh         # Health checking
└── templates/                  # Updated templates
    ├── ci-analysis.j2          # CI-optimized analysis
    ├── security-scan.j2        # Security scanning
    └── quality-check.j2        # Quality checking
```

## Before: Traditional Automation

### Original GitHub Actions

**before/github-actions.yml**:
```yaml
name: Traditional Analysis
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install ostruct
        run: pip install ostruct-cli
        
      - name: Run Analysis
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          # Traditional approach - all files processed the same way
          ostruct run analysis.j2 schema.json \
            -f code=src/ \
            -d tests=tests/ \
            -d docs=docs/ \
            --dir-recursive \
            --output-file results.json
```

**Issues with traditional approach:**
- All files processed identically (inefficient)
- No cost controls
- Limited error handling
- High token usage
- No configuration management

### Original GitLab CI

**before/gitlab-ci.yml**:
```yaml
stages:
  - analysis

analyze:
  stage: analysis
  image: python:3.11
  before_script:
    - pip install ostruct-cli
  script:
    # Traditional single-command approach
    - ostruct run analysis.j2 schema.json -d source=. --dir-recursive
  artifacts:
    paths:
      - results.json
  variables:
    OPENAI_API_KEY: $CI_OPENAI_API_KEY
```

### Original Jenkins Pipeline

**before/jenkins-pipeline.groovy**:
```groovy
pipeline {
    agent any
    
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
    }
    
    stages {
        stage('Analysis') {
            steps {
                sh 'pip install ostruct-cli'
                sh '''
                    ostruct run analysis.j2 schema.json \
                      -d code=. \
                      --dir-recursive
                '''
            }
        }
    }
}
```

## After: Enhanced Automation

### Enhanced GitHub Actions

**after/enhanced-github.yml**:
```yaml
name: Enhanced Multi-Tool Analysis
on: 
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  analyze:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install Dependencies
        run: pip install ostruct-cli
        
      - name: Health Check
        run: |
          # Validate environment and configuration
          if [ -z "$OPENAI_API_KEY" ]; then
            echo "❌ OPENAI_API_KEY not set"
            exit 1
          fi
          
          # Test basic functionality
          echo "test" | ostruct run <(echo "{{ stdin }}") <(echo '{"type":"string"}') >/dev/null
          echo "✅ Health check passed"
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          
      - name: Create CI Configuration
        run: |
          cat > ci-config.yaml << EOF
          models:
            default: gpt-4o
          tools:
            code_interpreter:
              auto_download: true
              output_directory: "./ci_output"
            file_search:
              max_results: 20
          operation:
            timeout_minutes: 20
            retry_attempts: 2
            require_approval: never
          limits:
            max_cost_per_run: 3.00
            warn_expensive_operations: true
          EOF
          
      - name: Multi-Tool Analysis
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          # Enhanced approach with explicit routing
          ostruct --config ci-config.yaml run templates/ci-analysis.j2 schemas/analysis_result.json \
            -fc src/ \
            -fc tests/ \
            -fs docs/ \
            -fs README.md \
            -ft .github/ \
            --progress-level basic \
            --output-file analysis_results.json
            
      - name: Security Scan
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          ostruct --config ci-config.yaml run templates/security-scan.j2 schemas/security_report.json \
            -fc src/ \
            -fs security_docs/ \
            --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
            -V repo_owner=${{ github.repository_owner }} \
            -V repo_name=${{ github.event.repository.name }} \
            --output-file security_report.json
            
      - name: Cost Monitoring
        run: |
          python scripts/cost-monitor.py analysis_results.json
          
      - name: Quality Gate
        run: |
          # Check analysis results and set job status
          python -c "
          import json, sys
          with open('analysis_results.json') as f:
              data = json.load(f)
          
          quality_score = data.get('quality_score', 0)
          critical_issues = data.get('critical_issues', [])
          
          print(f'Quality Score: {quality_score}')
          print(f'Critical Issues: {len(critical_issues)}')
          
          if quality_score < 70:
              print('❌ Quality score below threshold')
              sys.exit(1)
          
          if len(critical_issues) > 0:
              print('❌ Critical issues found')
              sys.exit(1)
              
          print('✅ Quality gate passed')
          "
          
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
        if: github.event_name == 'pull_request' && always()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            if (fs.existsSync('analysis_results.json')) {
              const analysis = JSON.parse(fs.readFileSync('analysis_results.json', 'utf8'));
              
              const comment = `## 🤖 Enhanced ostruct Analysis
              
              **Quality Score**: ${analysis.quality_score}/100
              **Issues Found**: ${analysis.issues?.length || 0}
              **Cost**: $${analysis.estimated_cost?.toFixed(4) || '0.0000'}
              
              ${analysis.summary || 'Analysis completed successfully.'}
              `;
              
              await github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: comment
              });
            }
```

### Enhanced GitLab CI

**after/enhanced-gitlab.yml**:
```yaml
stages:
  - setup
  - analysis
  - security
  - report

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  OSTRUCT_CONFIG: "configs/ci-advanced.yaml"

cache:
  paths:
    - .cache/pip/

setup:
  stage: setup
  image: python:3.11
  script:
    - pip install ostruct-cli
    - scripts/health-check.sh
  artifacts:
    paths:
      - configs/
    expire_in: 1 hour

code_analysis:
  stage: analysis
  image: python:3.11
  dependencies:
    - setup
  before_script:
    - pip install ostruct-cli
  script:
    # Enhanced multi-tool analysis
    - |
      ostruct --config $OSTRUCT_CONFIG run templates/ci-analysis.j2 schemas/analysis_result.json \
        -fc src/ \
        -fc tests/ \
        -fs docs/ \
        -ft configs/ \
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
  dependencies:
    - setup
  before_script:
    - pip install ostruct-cli
  script:
    - |
      ostruct --config configs/security-scan.yaml run templates/security-scan.j2 schemas/security_report.json \
        -fc src/ \
        -fs security_docs/ \
        --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
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
    - main
    - security-scan

cost_monitoring:
  stage: report
  image: python:3.11
  dependencies:
    - code_analysis
    - security_scan
  script:
    - python scripts/cost-monitor.py analysis_results.json security_report.json
    - python scripts/generate-report.py
  artifacts:
    paths:
      - cost_report.json
      - final_report.html
    expire_in: 1 month
```

### Enhanced Jenkins Pipeline

**after/enhanced-jenkins.groovy**:
```groovy
pipeline {
    agent any
    
    parameters {
        choice(
            name: 'ANALYSIS_LEVEL',
            choices: ['basic', 'comprehensive', 'security-focused'],
            description: 'Level of analysis to perform'
        )
        booleanParam(
            name: 'ENABLE_MCP',
            defaultValue: true,
            description: 'Enable MCP server integration'
        )
        string(
            name: 'COST_LIMIT',
            defaultValue: '5.00',
            description: 'Maximum cost per run ($)'
        )
    }
    
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
        OSTRUCT_CONFIG = 'configs/ci-advanced.yaml'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    pip install ostruct-cli
                    chmod +x scripts/*.sh
                '''
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    def healthResult = sh(
                        script: 'scripts/health-check.sh',
                        returnStatus: true
                    )
                    if (healthResult != 0) {
                        error("Health check failed")
                    }
                }
            }
        }
        
        stage('Create Dynamic Configuration') {
            steps {
                script {
                    def config = """
models:
  default: gpt-4o
tools:
  code_interpreter:
    auto_download: true
    output_directory: "./jenkins_output"
  file_search:
    max_results: ${params.ANALYSIS_LEVEL == 'comprehensive' ? '25' : '15'}
operation:
  timeout_minutes: ${params.ANALYSIS_LEVEL == 'comprehensive' ? '30' : '20'}
  retry_attempts: 2
  require_approval: never
limits:
  max_cost_per_run: ${params.COST_LIMIT}
  warn_expensive_operations: true
"""
                    writeFile file: 'dynamic-config.yaml', text: config
                }
            }
        }
        
        stage('Enhanced Analysis') {
            parallel {
                stage('Code Analysis') {
                    steps {
                        script {
                            def mcpFlag = params.ENABLE_MCP ? 
                                '--mcp-server deepwiki@https://mcp.deepwiki.com/sse' : ''
                            
                            sh """
                                ostruct --config dynamic-config.yaml run templates/ci-analysis.j2 schemas/analysis_result.json \\
                                  -fc src/ \\
                                  -fc tests/ \\
                                  -fs docs/ \\
                                  -ft configs/ \\
                                  ${mcpFlag} \\
                                  --output-file analysis_results.json
                            """
                        }
                    }
                }
                
                stage('Security Scan') {
                    when {
                        anyOf {
                            branch 'main'
                            expression { params.ANALYSIS_LEVEL == 'security-focused' }
                        }
                    }
                    steps {
                        sh '''
                            ostruct --config configs/security-scan.yaml run templates/security-scan.j2 schemas/security_report.json \\
                              -fc src/ \\
                              -fs security_docs/ \\
                              --mcp-server deepwiki@https://mcp.deepwiki.com/sse \\
                              --output-file security_report.json
                        '''
                    }
                }
            }
        }
        
        stage('Cost Analysis') {
            steps {
                script {
                    sh 'python scripts/cost-monitor.py analysis_results.json'
                    
                    def costReport = readJSON file: 'cost_report.json'
                    echo "Total Cost: \$${costReport.total_cost}"
                    
                    if (costReport.total_cost > params.COST_LIMIT.toFloat()) {
                        warning("Cost \$${costReport.total_cost} exceeds limit \$${params.COST_LIMIT}")
                    }
                }
            }
        }
        
        stage('Quality Gate') {
            steps {
                script {
                    def analysis = readJSON file: 'analysis_results.json'
                    
                    echo "Quality Score: ${analysis.quality_score}"
                    echo "Issues Found: ${analysis.issues?.size() ?: 0}"
                    
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
            archiveArtifacts artifacts: '*.json, jenkins_output/**', allowEmptyArchive: true
            
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'jenkins_output',
                reportFiles: 'index.html',
                reportName: 'Enhanced Analysis Report'
            ])
        }
        
        success {
            script {
                if (currentBuild.previousBuild?.result == 'FAILURE') {
                    slackSend channel: '#dev',
                             color: 'good',
                             message: "✅ Enhanced ostruct analysis recovered: ${env.JOB_NAME}"
                }
            }
        }
        
        failure {
            slackSend channel: '#dev',
                     color: 'danger',
                     message: "❌ Enhanced ostruct analysis failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}"
        }
    }
}
```

## Configuration Files for Automation

### Basic CI Configuration

**configs/ci-basic.yaml**:
```yaml
models:
  default: gpt-4o

tools:
  code_interpreter:
    auto_download: true
    output_directory: "./ci_output"
  file_search:
    max_results: 10

operation:
  timeout_minutes: 15
  retry_attempts: 1
  require_approval: never

limits:
  max_cost_per_run: 2.00
  warn_expensive_operations: true
```

### Advanced CI Configuration

**configs/ci-advanced.yaml**:
```yaml
models:
  default: gpt-4o

tools:
  code_interpreter:
    auto_download: true
    output_directory: "./ci_output"
  file_search:
    max_results: 20

mcp:
  deepwiki: "https://mcp.deepwiki.com/sse"

operation:
  timeout_minutes: 25
  retry_attempts: 2
  require_approval: never

limits:
  max_cost_per_run: 4.00
  warn_expensive_operations: true
```

### Security Scan Configuration

**configs/security-scan.yaml**:
```yaml
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
  timeout_minutes: 30
  retry_attempts: 3
  require_approval: never

limits:
  max_cost_per_run: 6.00
  warn_expensive_operations: true
```

## Migration Tools

### CI Migration Tool

**scripts/migrate-ci.py**:
```python
#!/usr/bin/env python3
"""Migrate existing CI/CD scripts to enhanced ostruct usage."""

import re
import sys
from pathlib import Path

def migrate_github_actions(content):
    """Migrate GitHub Actions workflow."""
    
    # Replace traditional ostruct commands
    patterns = [
        (r'ostruct run (\S+) (\S+) -f (\w+)=(\S+)', 
         r'ostruct --config ci-config.yaml run \1 \2 -ft \4'),
        (r'ostruct run (\S+) (\S+) -d (\w+)=(\S+)', 
         r'ostruct --config ci-config.yaml run \1 \2 -fc \4'),
        (r'--dir-recursive', '--progress-level basic'),
    ]
    
    migrated = content
    for pattern, replacement in patterns:
        migrated = re.sub(pattern, replacement, migrated)
    
    # Add configuration setup
    config_step = '''
      - name: Create CI Configuration
        run: |
          cat > ci-config.yaml << EOF
          models:
            default: gpt-4o
          tools:
            code_interpreter:
              auto_download: true
              output_directory: "./ci_output"
          operation:
            timeout_minutes: 20
            require_approval: never
          limits:
            max_cost_per_run: 3.00
          EOF
'''
    
    # Insert after Python setup
    migrated = re.sub(
        r'(- name: Setup Python.*?\n.*?python-version:.*?\n)',
        r'\1' + config_step,
        migrated,
        flags=re.DOTALL
    )
    
    return migrated

def migrate_file(filepath):
    """Migrate a CI/CD file."""
    
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    if 'github' in filepath.lower():
        migrated = migrate_github_actions(content)
    else:
        print(f"⚠️  Migration not implemented for: {filepath}")
        return False
    
    # Create backup
    backup_path = f"{filepath}.backup"
    with open(backup_path, 'w') as f:
        f.write(content)
    
    # Write migrated version
    with open(filepath, 'w') as f:
        f.write(migrated)
    
    print(f"✅ Migrated: {filepath}")
    print(f"📋 Backup created: {backup_path}")
    return True

def main():
    """Main migration function."""
    
    if len(sys.argv) < 2:
        print("Usage: migrate-ci.py <ci-file> [ci-file2] ...")
        sys.exit(1)
    
    success_count = 0
    for filepath in sys.argv[1:]:
        if migrate_file(filepath):
            success_count += 1
    
    print(f"\n📊 Migration Summary:")
    print(f"✅ Successfully migrated: {success_count}")
    print(f"❌ Failed migrations: {len(sys.argv) - 1 - success_count}")

if __name__ == "__main__":
    main()
```

## Benefits of Enhanced Automation

### Performance Improvements
- **50-70% token reduction** through explicit file routing
- **Faster execution** with parallel tool processing
- **Better error handling** with retry logic and health checks

### Cost Benefits
- **Configurable cost limits** prevent runaway charges
- **Real-time cost monitoring** in CI/CD pipelines
- **Optimized processing** reduces overall API usage

### Quality Improvements
- **Multi-tool integration** provides richer analysis
- **Code execution** enables dynamic analysis
- **Documentation context** improves recommendations
- **External knowledge** through MCP integration

### Operational Benefits
- **Centralized configuration** ensures consistency
- **Health checks** prevent failures
- **Detailed reporting** improves visibility
- **Quality gates** maintain standards

## Migration Checklist

### Pre-Migration
- [ ] Document current CI/CD workflows
- [ ] Measure baseline performance and costs
- [ ] Identify file types and routing opportunities
- [ ] Test enhanced commands locally

### Migration Steps
- [ ] Create configuration files for different environments
- [ ] Update CI/CD scripts with enhanced syntax
- [ ] Add health checks and error handling
- [ ] Implement cost monitoring
- [ ] Add quality gates and reporting

### Post-Migration Validation
- [ ] Compare performance metrics
- [ ] Verify cost improvements
- [ ] Test failure scenarios
- [ ] Update team documentation
- [ ] Monitor production usage

This comprehensive automation migration guide ensures your CI/CD pipelines can take full advantage of ostruct's enhanced capabilities while maintaining reliability and cost control.