CI/CD Integration
=================

Integrate ostruct into your continuous integration and deployment pipelines for automated data processing, code analysis, and report generation. This guide covers GitHub Actions, GitLab CI, Jenkins, and security best practices.

.. note::
   All examples use pinned action versions for security and reproducibility. Update versions as needed for your security requirements.

Quick Start
-----------

Basic ostruct CI/CD integration requires:

1. **API Key Management** - Secure credential storage
2. **Environment Setup** - Python and ostruct installation
3. **File Security** - Proper path restrictions
4. **Output Handling** - Results processing and storage

GitHub Actions
==============

Basic GitHub Actions Workflow
-----------------------------

.. code-block:: yaml

   name: Automated Analysis

   on:
     push:
       branches: [ main, develop ]
     pull_request:
       branches: [ main ]

   jobs:
     analyze:
       runs-on: ubuntu-latest

       steps:
       - uses: actions/checkout@v4

       - name: Set up Python
         uses: actions/setup-python@v5
         with:
           python-version: '3.11'

       - name: Install ostruct
         run: |
           pip install ostruct-cli

       - name: Run Code Analysis
         env:
           OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
         run: |
                     ostruct run templates/code_review.j2 schemas/review.json \
            --path-security strict \
            --allow ${{ github.workspace }}/src \
            --dir ci:source src/ \
            --ci-cleanup \
            --output-file analysis_results.json

       - name: Upload Results
         uses: actions/upload-artifact@v4
         with:
           name: analysis-results
           path: analysis_results.json

Multi-Platform Analysis
-----------------------

.. code-block:: yaml

   name: Cross-Platform Analysis

   on: [push, pull_request]

   jobs:
     analyze:
       strategy:
         matrix:
           os: [ubuntu-latest]
           python-version: ['3.10', '3.11', '3.12']
           # Windows and macOS support available but commented for cost optimization
           # Uncomment and test thoroughly before enabling in production
           # os: [ubuntu-latest, windows-latest, macos-latest]

       runs-on: ${{ matrix.os }}

       steps:
       - uses: actions/checkout@v4

       - name: Set up Python ${{ matrix.python-version }}
         uses: actions/setup-python@v5
         with:
           python-version: ${{ matrix.python-version }}

       - name: Install dependencies
         run: |
           pip install ostruct-cli

       - name: Configure analysis environment
         shell: bash
         run: |
           # Platform-specific path handling
           if [ "${{ runner.os }}" == "Windows" ]; then
             echo "ANALYSIS_BASE=${{ github.workspace }}" >> $GITHUB_ENV
           else
             echo "ANALYSIS_BASE=${{ github.workspace }}" >> $GITHUB_ENV
           fi

       - name: Run Security Scan
         env:
           OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
         run: |
                     ostruct run templates/security_scan.j2 schemas/security.json \
            --path-security strict \
            --allow "${{ env.ANALYSIS_BASE }}/src" \
            --allow "${{ env.ANALYSIS_BASE }}/tests" \
            --dir ci:source src/ \
            --file config config.yaml \
            --ci-cleanup \
            --timeout 600 \
            --output-file security_results.json

Advanced GitHub Actions Patterns
--------------------------------

**Conditional Analysis:**

.. code-block:: yaml

   - name: Analyze Changed Files
     if: github.event_name == 'pull_request'
     env:
       OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
     run: |
       # Get changed files
       git diff --name-only ${{ github.event.pull_request.base.sha }} HEAD > changed_files.txt

       # Only analyze if Python files changed
       if grep -q "\.py$" changed_files.txt; then
         ostruct run templates/pr_review.j2 schemas/pr_analysis.json \
           --path-security strict \
           --allow ${{ github.workspace }}/src \
           --file changed_files changed_files.txt \
           --dir ci:source src/ \
           --output-file pr_analysis.json
       fi

**Matrix Strategy with File Types:**

.. code-block:: yaml

   strategy:
     matrix:
       analysis-type:
         - { name: "security", template: "security_scan.j2", schema: "security.json" }
         - { name: "performance", template: "perf_analysis.j2", schema: "performance.json" }
         - { name: "quality", template: "code_quality.j2", schema: "quality.json" }

   steps:
   - name: Run ${{ matrix.analysis-type.name }} Analysis
     env:
       OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
     run: |
       ostruct run templates/${{ matrix.analysis-type.template }} \
         schemas/${{ matrix.analysis-type.schema }} \
         --dir ci:source src/ --file config config.yaml \
         --output-file ${{ matrix.analysis-type.name }}_results.json

GitLab CI
=========

Basic GitLab CI Configuration
-----------------------------

.. code-block:: yaml

   # .gitlab-ci.yml
   image: python:3.11-slim

   variables:
     PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

   cache:
     paths:
       - .cache/pip/

   before_script:
     - pip install ostruct-cli

   stages:
     - analyze
     - report

   code_analysis:
     stage: analyze
     script:
       - |
                 ostruct run templates/gitlab_analysis.j2 schemas/analysis.json \
          --path-security strict --allow $CI_PROJECT_DIR \
          --allow $CI_PROJECT_DIR/src \
          --allow $CI_PROJECT_DIR/tests \
          --dir ci:data src/ \
          --file config .gitlab-ci.yml \
          --ci-cleanup \
          --output-file analysis_results.json
     artifacts:
       reports:
         junit: analysis_results.json
       paths:
         - analysis_results.json
       expire_in: 1 week
     only:
       - main
       - merge_requests

GitLab CI with Security Scanning
--------------------------------

.. code-block:: yaml

   security_scan:
     stage: analyze
     variables:
       ANALYSIS_TYPE: "security"
     script:
       - |
         # Create secure analysis environment
         export ANALYSIS_DIR="$CI_PROJECT_DIR/analysis"
         mkdir -p $ANALYSIS_DIR

                 ostruct run templates/security_deep_scan.j2 schemas/security_detailed.json \
          --path-security strict --allow $CI_PROJECT_DIR \
          --allow $CI_PROJECT_DIR/src \
          --allow $CI_PROJECT_DIR/config \
          --dir ci:data src/ \
          --dir ci:data config/ \
          --file fs:docs documentation/ \
          --fs-cleanup \
          --ci-cleanup \
          --timeout 900 \
          --output-file $ANALYSIS_DIR/security_report.json

       - |
         # Generate summary for merge request
         if [ "$CI_PIPELINE_SOURCE" = "merge_request_event" ]; then
           ostruct run templates/mr_security_summary.j2 schemas/summary.json \
             --path-security strict --allow $ANALYSIS_DIR \
             --file config security_report.json \
             --output-file mr_security_summary.md
         fi
     artifacts:
       reports:
         security: analysis/security_report.json
       paths:
         - analysis/
         - mr_security_summary.md
     only:
       - merge_requests
       - main

Jenkins Pipeline
================

Declarative Pipeline
--------------------

.. code-block:: groovy

   pipeline {
       agent any

       environment {
           PYTHON_VERSION = '3.11'
           ANALYSIS_WORKSPACE = "${WORKSPACE}/analysis"
       }

       stages {
           stage('Setup') {
               steps {
                   script {
                       // Install Python and ostruct
                       sh '''
                           python3 -m venv venv
                           source venv/bin/activate
                           pip install ostruct-cli
                       '''
                   }
               }
           }

           stage('Code Analysis') {
               environment {
                   OPENAI_API_KEY = credentials('openai-api-key')
               }
               steps {
                   script {
                       sh '''
                           source venv/bin/activate
                           mkdir -p ${ANALYSIS_WORKSPACE}

                                                     ostruct run templates/jenkins_analysis.j2 schemas/ci_analysis.json \
                              --path-security strict --allow ${WORKSPACE} \
                              --allow ${WORKSPACE}/src \
                              --allow ${WORKSPACE}/tests \
                              --dir ci:data src/ \
                              --file config Jenkinsfile \
                              --file config config.yaml \
                              --ci-cleanup \
                              --timeout 600 \
                              --output-file ${ANALYSIS_WORKSPACE}/results.json
                       '''
                   }
               }
               post {
                   always {
                       archiveArtifacts artifacts: 'analysis/**/*', allowEmptyArchive: true
                       publishHTML([
                           allowMissing: false,
                           alwaysLinkToLastBuild: true,
                           keepAll: true,
                           reportDir: 'analysis',
                           reportFiles: '*.json',
                           reportName: 'Analysis Report'
                       ])
                   }
               }
           }

           stage('Security Validation') {
               when {
                   anyOf {
                       branch 'main'
                       changeRequest()
                   }
               }
               environment {
                   OPENAI_API_KEY = credentials('openai-api-key')
               }
               steps {
                   script {
                       sh '''
                           source venv/bin/activate

                                                     ostruct run templates/security_validation.j2 schemas/security_check.json \
                              --path-security strict --allow ${WORKSPACE} \
                              --allow ${WORKSPACE}/src \
                              --dir ci:data src/ \
                              --fs-cleanup \
                              --ci-cleanup \
                              --output-file ${ANALYSIS_WORKSPACE}/security_validation.json
                       '''
                   }
               }
           }
       }

       post {
           cleanup {
               cleanWs()
           }
       }
   }

Scripted Pipeline with Advanced Features
----------------------------------------

.. code-block:: groovy

   node {
       def analysisResults = [:]

       try {
           stage('Checkout') {
               checkout scm
           }

           stage('Setup Environment') {
               sh '''
                   python3 -m venv venv
                   source venv/bin/activate
                   pip install ostruct-cli
               '''
           }

           stage('Parallel Analysis') {
               parallel {
                   'Security Analysis': {
                       withCredentials([string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY')]) {
                           sh '''
                               source venv/bin/activate
                               ostruct run templates/security.j2 schemas/security.json \
                                   --path-security strict --allow ${WORKSPACE} \
                                   --allow ${WORKSPACE}/src \
                                   --dir ci:data src/ \
                                   --timeout 300 \
                                   --output-file security_results.json
                           '''
                           analysisResults.security = readJSON file: 'security_results.json'
                       }
                   },
                   'Performance Analysis': {
                       withCredentials([string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY')]) {
                           sh '''
                               source venv/bin/activate
                               ostruct run templates/performance.j2 schemas/performance.json \
                                   --path-security strict --allow ${WORKSPACE} \
                                   --allow ${WORKSPACE}/src \
                                   --dir ci:data src/ \
                                   --timeout 300 \
                                   --output-file performance_results.json
                           '''
                           analysisResults.performance = readJSON file: 'performance_results.json'
                       }
                   }
               }
           }

           stage('Generate Report') {
               writeJSON file: 'combined_results.json', json: analysisResults

               withCredentials([string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY')]) {
                   sh '''
                       source venv/bin/activate
                       ostruct run templates/final_report.j2 schemas/report.json \
                           --path-security strict --allow ${WORKSPACE} \
                           --file config combined_results.json \
                           -V build_number=${BUILD_NUMBER} \
                           -V git_commit=${GIT_COMMIT} \
                           --output-file final_report.json
                   '''
               }
           }

       } catch (Exception e) {
           currentBuild.result = 'FAILURE'
           throw e
       } finally {
           archiveArtifacts artifacts: '**/*_results.json', allowEmptyArchive: true
       }
   }

Azure DevOps
============

Azure Pipelines YAML
--------------------

.. code-block:: yaml

   # azure-pipelines.yml
   trigger:
     branches:
       include:
         - main
         - develop

   pr:
     branches:
       include:
         - main

   pool:
     vmImage: 'ubuntu-latest'

   variables:
     pythonVersion: '3.11'

   stages:
   - stage: Analysis
     displayName: 'Code Analysis'
     jobs:
     - job: AnalyzeCode
       displayName: 'Run ostruct Analysis'
       steps:
       - task: UsePythonVersion@0
         inputs:
           versionSpec: '$(pythonVersion)'
         displayName: 'Use Python $(pythonVersion)'

       - script: |
           pip install ostruct-cli
         displayName: 'Install ostruct'

       - task: AzureKeyVault@2
         inputs:
           azureSubscription: 'your-service-connection'
           KeyVaultName: 'your-keyvault'
           SecretsFilter: 'openai-api-key'
         displayName: 'Get API Key from KeyVault'

       - script: |
           ostruct run templates/azure_analysis.j2 schemas/analysis.json \
                         --path-security strict --allow $(Build.SourcesDirectory) \
            --allow $(Build.SourcesDirectory)/src \
            --dir ci:data src/ \
            --file config azure-pipelines.yml \
            --ci-cleanup \
            --output-file $(Build.ArtifactStagingDirectory)/analysis_results.json
         env:
           OPENAI_API_KEY: $(openai-api-key)
         displayName: 'Run Analysis'

       - task: PublishBuildArtifacts@1
         inputs:
           pathToPublish: '$(Build.ArtifactStagingDirectory)'
           artifactName: 'analysis-results'
         displayName: 'Publish Results'

Security Best Practices
=======================

API Key Management
------------------

**GitHub Actions:**

.. code-block:: yaml

   # Store in repository secrets
   env:
     OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

**GitLab CI:**

.. code-block:: yaml

   # Store in GitLab CI/CD variables (masked)
   variables:
     OPENAI_API_KEY: $OPENAI_API_KEY

**Jenkins:**

.. code-block:: groovy

   // Use Jenkins credentials
   environment {
       OPENAI_API_KEY = credentials('openai-api-key')
   }

**Azure DevOps:**

.. code-block:: yaml

   # Use Azure Key Vault
   - task: AzureKeyVault@2
     inputs:
       azureSubscription: 'service-connection'
       KeyVaultName: 'keyvault-name'
       SecretsFilter: 'openai-api-key'

Environment Variable Security
-----------------------------

.. code-block:: bash

   # Validate API key is set
   if [ -z "$OPENAI_API_KEY" ]; then
     echo "Error: OPENAI_API_KEY not set"
     exit 1
   fi

   # Mask sensitive values in logs
   set +x  # Disable command echoing for sensitive operations
   ostruct run template.j2 schema.json --api-key "$OPENAI_API_KEY"
   set -x  # Re-enable command echoing

File Access Controls
--------------------

.. code-block:: yaml

   # Restrict file access with explicit allowed directories
   - name: Secure Analysis
     run: |
             ostruct run template.j2 schema.json \
        --path-security strict --allow ${{ github.workspace }} \
        --allow ${{ github.workspace }}/src \
        --allow ${{ github.workspace }}/tests \
        --allow ${{ github.workspace }}/config \
        --dir ci:data src/ \
        --ci-cleanup \
        --fs-cleanup

Network Security
----------------

.. code-block:: yaml

   # For self-hosted runners, consider network restrictions
   - name: Configure Network Security
     run: |
       # Example: Configure firewall rules for outbound HTTPS only
       # This is environment-specific configuration
       echo "Configuring secure network access..."

Performance and Cost Optimization
=================================

Parallel Execution
------------------

.. code-block:: yaml

   # GitHub Actions parallel jobs
   strategy:
     matrix:
       analysis: [security, performance, quality]

   steps:
   - name: Run ${{ matrix.analysis }} Analysis
     run: |
       ostruct run templates/${{ matrix.analysis }}.j2 \
         schemas/${{ matrix.analysis }}.json \
         --dir ci:data src/ --timeout 300

Conditional Execution
---------------------

.. code-block:: yaml

   # Only run expensive analysis on main branch
   - name: Deep Analysis
     if: github.ref == 'refs/heads/main'
     run: |
       ostruct run templates/comprehensive.j2 schema.json \
         --dir ci:data src/ --file fs:docs docs/ --timeout 900

Caching Strategies
------------------

.. code-block:: yaml

   # Cache ostruct installation
   - name: Cache Python packages
     uses: actions/cache@v4
     with:
       path: ~/.cache/pip
       key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

   # Cache analysis results for unchanged files
   - name: Cache Analysis Results
     uses: actions/cache@v4
     with:
       path: analysis_cache/
       key: analysis-${{ hashFiles('src/**/*.py') }}

Timeout and Resource Management
-------------------------------

.. code-block:: yaml

   # Set appropriate timeouts
   - name: Resource-Controlled Analysis
     timeout-minutes: 10
     run: |
             ostruct run template.j2 schema.json \
        --dir ci:data src/ \
        --timeout 300 \
        --ci-cleanup \
        --fs-cleanup

Error Handling and Monitoring
=============================

Comprehensive Error Handling
----------------------------

.. code-block:: yaml

   - name: Analysis with Error Handling
     run: |
       set -e  # Exit on error

       # Validate environment
       if [ -z "$OPENAI_API_KEY" ]; then
         echo "::error::OpenAI API key not configured"
         exit 1
       fi

       # Run analysis with error capture
       if ! ostruct run template.j2 schema.json \
         --dir ci:data src/ \
         --timeout 300 \
         --output-file results.json; then
         echo "::error::Analysis failed"

         # Generate fallback report
         echo '{"status": "failed", "timestamp": "'$(date -Iseconds)'"}' > results.json
         exit 1
       fi

       # Validate output
       if [ ! -f results.json ] || [ ! -s results.json ]; then
         echo "::error::No analysis results generated"
         exit 1
       fi

Notification and Reporting
--------------------------

.. code-block:: yaml

   - name: Notify on Failure
     if: failure()
     uses: actions/github-script@v7
     with:
       script: |
         github.rest.issues.createComment({
           issue_number: context.issue.number,
           owner: context.repo.owner,
           repo: context.repo.repo,
           body: '⚠️ Analysis failed. Please check the workflow logs.'
         })

Integration with External Tools
-------------------------------

.. code-block:: yaml

   # Slack notification
   - name: Slack Notification
     if: always()
     uses: 8398a7/action-slack@v3
     with:
       status: ${{ job.status }}
       channel: '#ci-notifications'
       webhook_url: ${{ secrets.SLACK_WEBHOOK }}

   # Upload to cloud storage
   - name: Upload Results to S3
     uses: aws-actions/configure-aws-credentials@v4
     with:
       aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
       aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
       aws-region: us-east-1

   - run: |
       aws s3 cp results.json s3://analysis-results-bucket/$(date +%Y%m%d)/

Template Examples for CI/CD
===========================

Pull Request Analysis Template
------------------------------

.. code-block:: jinja

   ---
   system_prompt: |
     You are a senior code reviewer analyzing a pull request.
     Focus on security, performance, and maintainability issues.
   ---
   # Pull Request Analysis

   **PR**: #{{ pr_number }} - {{ pr_title }}
   **Author**: {{ pr_author }}
   **Files Changed**: {{ changed_files | length }}

   ## Changed Files
   {% for file in changed_files %}
   ### {{ file.name }}
   {% if file.extension == "py" %}
   **Language**: Python
   **Lines**: {{ file.content | word_count }}
   ```python
   {{ file.content }}
   ```
   {% endif %}
   {% endfor %}

   ## Analysis Request
   Please review this pull request and provide:
   1. **Security Issues**: Any potential vulnerabilities
   2. **Performance Concerns**: Inefficient code patterns
   3. **Code Quality**: Style and maintainability issues
   4. **Test Coverage**: Missing test scenarios

Security Scan Template
----------------------

.. code-block:: jinja

   ---
   system_prompt: |
     You are a cybersecurity expert performing automated security analysis.
     Focus on identifying vulnerabilities, insecure patterns, and compliance issues.
   ---
   # Automated Security Scan

   **Scan Date**: {{ now() }}
   **Repository**: {{ repo_name }}
   **Branch**: {{ branch_name }}
   **Commit**: {{ commit_hash }}

   ## Scanned Files
   {% for file in source_files %}
   - **{{ file.name }}**: {{ file.size }} bytes
   {% endfor %}

   ## Configuration Files
   {% for config in config_files %}
   ### {{ config.name }}
   ```yaml
   {{ config.content }}
   ```
   {% endfor %}

   ## Source Code Analysis
   {% for file in source_files if file.extension in ['py', 'js', 'ts', 'java', 'go'] %}
   ### {{ file.name }}
   ```{{ file.extension }}
   {{ file.content }}
   ```
   {% endfor %}

   Please perform a comprehensive security analysis focusing on:
   1. **Injection vulnerabilities** (SQL, XSS, Command injection)
   2. **Authentication and authorization** flaws
   3. **Cryptographic issues** and weak implementations
   4. **Input validation** and sanitization
   5. **Configuration security** and hardening
   6. **Dependency vulnerabilities** and supply chain risks

Troubleshooting
===============

Common CI/CD Issues
-------------------

**API Key Not Found:**

.. code-block:: bash

   # Debug: Check if API key is available
   echo "API key status: ${OPENAI_API_KEY:+SET}"

   # Solution: Verify secret configuration in CI platform

**File Access Errors:**

.. code-block:: bash

   # Debug: List accessible files
   find . -name "*.py" -type f | head -10

   # Solution: Check base-dir and allowed directory settings
   ostruct run template.j2 schema.json \
     --path-security strict --allow $PWD \
     --allow $PWD/src \
     --verbose

**Timeout Issues:**

.. code-block:: bash

   # Debug: Test with shorter timeout
   ostruct run template.j2 schema.json \
     --dry-run \
     --dir ci:data src/

   # Solution: Increase timeout or reduce file size
   ostruct run template.j2 schema.json \
     --dir ci:data src/ \
     --timeout 900

**Memory/Resource Limits:**

.. code-block:: yaml

   # Solution: Use cleanup and resource limits
   - name: Memory-Controlled Analysis
     run: |
             ostruct run template.j2 schema.json \
        --dir ci:data src/ \
        --ci-cleanup \
        --fs-cleanup \
        --timeout 600

Performance Monitoring
----------------------

.. code-block:: bash

   # Monitor execution time
   time ostruct run template.j2 schema.json --dir ci:data src/

   # Monitor token usage with dry run
   ostruct run template.j2 schema.json --dry-run --dir ci:data src/

Next Steps
==========

- :doc:`containers` - Docker and Kubernetes deployment
- :doc:`scripting_patterns` - Advanced automation patterns
- :doc:`cost_control` - Cost optimization strategies
- :doc:`../security/overview` - Security considerations for CI/CD
