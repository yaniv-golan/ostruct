CI/CD and Container Deployment
==============================

This guide covers integrating ostruct into automated workflows using CI/CD pipelines and containerized deployments. Learn how to set up GitHub Actions, GitLab CI, Jenkins, Docker containers, and Kubernetes orchestration for scalable ostruct automation.

.. note::
   All examples use pinned versions for security and reproducibility. Container deployments require careful handling of API keys and file access permissions. See the :doc:`../security/overview` guide for security best practices.

CI/CD Integration
=================

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

       - name: Run Security Scan
         env:
           OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
         run: |
           ostruct run templates/security_scan.j2 schemas/security.json \
             --path-security strict \
             --allow ${{ github.workspace }}/src \
             --dir ci:source src/ \
             --output-file security_results.json

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
           --path-security strict \
           --allow $CI_PROJECT_DIR/src \
           --dir ci:source src/ \
           --output-file analysis_results.json
     artifacts:
       paths:
         - analysis_results.json
       expire_in: 1 week

Container Deployment
====================

Docker Fundamentals
===================

Basic Docker Usage
------------------

Run ostruct directly in a container:

.. code-block:: bash

   # Basic container execution
   docker run --rm \
     -e OPENAI_API_KEY="your-api-key" \
     -v $(pwd):/workspace \
     -w /workspace \
     python:3.11-slim \
     bash -c "pip install ostruct-cli && ostruct run template.j2 schema.json --file config data.txt"

Creating Custom Docker Images
=============================

Minimal Dockerfile
------------------

.. code-block:: dockerfile

   FROM python:3.11-slim

   # Install ostruct
   RUN pip install ostruct-cli

   # Create non-root user for security
   RUN useradd --create-home --shell /bin/bash ostruct
   USER ostruct
   WORKDIR /home/ostruct

   # Set default command
   ENTRYPOINT ["ostruct"]

Production Dockerfile
---------------------

.. code-block:: dockerfile

   FROM python:3.11-slim as builder

   # Install build dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       && rm -rf /var/lib/apt/lists/*

   # Create virtual environment
   RUN python -m venv /opt/venv
   ENV PATH="/opt/venv/bin:$PATH"

   # Install ostruct and dependencies
   RUN pip install --no-cache-dir ostruct-cli

   # Production image
   FROM python:3.11-slim

   # Install runtime dependencies only
   RUN apt-get update && apt-get install -y \
       ca-certificates \
       && rm -rf /var/lib/apt/lists/* \
       && apt-get clean

   # Copy virtual environment from builder
   COPY --from=builder /opt/venv /opt/venv
   ENV PATH="/opt/venv/bin:$PATH"

   # Create non-root user
   RUN groupadd -r ostruct && useradd -r -g ostruct ostruct

   # Create directories with proper permissions
   RUN mkdir -p /app/templates /app/schemas /app/data /app/output \
       && chown --recursive ostruct:ostruct /app

   USER ostruct
   WORKDIR /app

   # Health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
     CMD ostruct --version || exit 1

   ENTRYPOINT ["ostruct"]

Docker Compose Deployments
==========================

Basic Docker Compose
--------------------

.. code-block:: yaml

   # docker-compose.yml
   version: '3.8'

   services:
     ostruct:
       build: .
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
       volumes:
         - ./data:/app/data:ro
         - ./templates:/app/templates:ro
         - ./schemas:/app/schemas:ro
         - ./output:/app/output
       command: run /app/templates/analysis.j2 /app/schemas/result.json --file config /app/data/input.csv --output-file /app/output/results.json

Kubernetes Deployment
=====================

Basic Kubernetes Deployment
---------------------------

.. code-block:: yaml

   # deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: ostruct-worker
     labels:
       app: ostruct-worker
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: ostruct-worker
     template:
       metadata:
         labels:
           app: ostruct-worker
       spec:
         containers:
         - name: ostruct
           image: ostruct:production
           env:
           - name: OPENAI_API_KEY
             valueFrom:
               secretKeyRef:
                 name: openai-secret
                 key: api-key
           volumeMounts:
           - name: templates
             mountPath: /app/templates
             readOnly: true
           - name: output
             mountPath: /app/output
           resources:
             requests:
               memory: "256Mi"
               cpu: "250m"
             limits:
               memory: "512Mi"
               cpu: "500m"
         volumes:
         - name: templates
           configMap:
             name: ostruct-templates
         - name: output
           emptyDir: {}

Security Best Practices
=======================

API Key Management
------------------

**GitHub Actions:**

.. code-block:: yaml

   # Store API key as repository secret
   - name: Secure Analysis
     env:
       OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
     run: ostruct run template.j2 schema.json

**Kubernetes:**

.. code-block:: yaml

   # Create secret
   kubectl create secret generic openai-secret --from-literal=api-key=your-api-key

   # Reference in deployment
   env:
   - name: OPENAI_API_KEY
     valueFrom:
       secretKeyRef:
         name: openai-secret
         key: api-key

File Access Security
--------------------

Always use path security restrictions:

.. code-block:: bash

   # Strict path security
   ostruct run template.j2 schema.json \
     --path-security strict \
     --allow /app/data \
     --allow /app/templates \
     --deny /etc \
     --deny /var

Container Security
------------------

**Non-root user:**

.. code-block:: dockerfile

   RUN useradd --create-home --shell /bin/bash ostruct
   USER ostruct

**Read-only volumes:**

.. code-block:: yaml

   volumes:
     - ./templates:/app/templates:ro
     - ./schemas:/app/schemas:ro

**Resource limits:**

.. code-block:: yaml

   resources:
     limits:
       memory: "512Mi"
       cpu: "500m"

Best Practices Summary
======================

1. **Security First**
   - Use secrets management for API keys
   - Implement path security restrictions
   - Run containers as non-root users
   - Use read-only volumes where possible

2. **Performance**
   - Use multi-stage Docker builds
   - Implement proper caching strategies
   - Set appropriate resource limits
   - Use parallel processing where beneficial

3. **Reliability**
   - Implement health checks and probes
   - Use structured logging
   - Handle failures gracefully
   - Test with dry runs

4. **Maintainability**
   - Pin versions for reproducibility
   - Document deployment procedures
   - Use infrastructure as code
   - Monitor and alert on issues

This comprehensive guide provides the foundation for deploying ostruct in production environments with proper security, performance, and reliability considerations.
