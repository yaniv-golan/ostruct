Advanced Template Patterns
==========================

This guide covers advanced template patterns, optimization techniques, and best practices for complex ostruct use cases. These patterns help you create robust, reusable templates for sophisticated AI workflows.

Template Organization
=====================

Template Libraries
------------------

Organize templates by use case for better maintainability:

.. code-block:: text

   templates/
   ├── analysis/
   │   ├── code-review.j2
   │   ├── data-analysis.j2
   │   └── security-audit.j2
   ├── automation/
   │   ├── ci-report.j2
   │   └── deploy-check.j2
   └── shared/
       ├── expert.txt
       └── common-filters.j2

Reusable Template Components
----------------------------

Create modular template components using shared system prompts:

**shared/expert.txt:**

.. code-block:: text

   You are a senior software engineer with expertise in:
   - Code quality and best practices
   - Security vulnerability assessment
   - Performance optimization
   - System architecture

**templates/analysis/security-audit.j2:**

.. code-block:: jinja

   ---
   include_system: ../shared/expert.txt
   system_prompt: |
     Focus specifically on security vulnerabilities:
     - SQL injection, XSS, CSRF
     - Authentication and authorization flaws
     - Data validation issues
   ---

   Perform a security audit of this codebase:
   {{ file_ref("source") }}

Multi-Tool Integration Patterns
===============================

Multi-Tool Analysis Workflow
----------------------------

A real-world example showing how to structure a template that naturally leverages multiple tools by providing clear instructions and context for each.

.. code-block:: jinja

   # Security Assessment Report

   ## Mission

   Perform a comprehensive security analysis of the provided codebase.

   ## File Manifest

   I have uploaded the following files for your use. Please refer to them by the names provided below.

   ### For Code Interpreter Analysis:

   **Source Code (`source_code`):**
   {% for file in source_code %}
   - `{{ file.path }}`
   {% endfor %}

   **Dependencies (`dependency_files`):**
   {% for file in dependency_files %}
   - `{{ file.path }}`
   {% endfor %}

   ### For File Search:

   **Documentation (`docs`):**
   {% for file in docs %}
   - `{{ file.path }}`
   {% endfor %}

   ## Analysis Instructions

   1. **Static Code Analysis (Code Interpreter)**
      - In the `source_code` files, scan for common vulnerability patterns (SQL injection, XSS, etc.).
      - Check for hardcoded secrets or credentials.
      - Validate input sanitization practices.

   2. **Dependency Security Check (Code Interpreter)**
      - Parse the `dependency_files` to identify all packages and versions.
      - Cross-reference them against known vulnerability databases.

   3. **Best Practices Research (Web Search)**
      - Use Web Search to find current security advisories for the project's technology stack.
      - Research recent CVEs affecting similar applications.

   4. **Documentation Review (File Search)**
      - Use File Search on the `docs` files to locate security-related documentation.
      - Check for existing security policies or guidelines.

   ## Output Requirements

   Provide your analysis in JSON format with:
   - Executive summary of security posture
   - Detailed vulnerability findings with severity levels
   - Remediation recommendations with code examples
   - When creating files, include download links for the security report

**Usage:**

.. code-block:: bash

   ostruct run security_template.j2 security_schema.json \\
     --enable-tool web_search \\
     --dir ci:source_code /path/to/src \\
     --dir ci:dependency_files /path/to/deps \\
     --dir fs:docs /path/to/docs

This template works because it:

- **Provides clear context** by telling the model which files are available to which tools.
- **Gives natural instructions** that prompt specific tool usage without being overly prescriptive.
- **Specifies output format** that matches the JSON schema requirements.
- **Uses download link patterns** that trigger ostruct's automatic file detection.

.. note::
   ostruct automatically detects and downloads Code Interpreter-generated files using OpenAI's
   ``container_file_citation`` annotations. No special formatting is required in templates.

Remote PDF Analysis with Vision Models
======================================

Need to distill information from a **public pitch-deck PDF** without downloading it first?  Use the
``user-data`` target with a remote URL:

.. code-block:: bash

   ostruct run distill_deck.j2 deck_schema.json \
     --file ud:deck "https://example.com/path/StartupPitch.pdf"

Key points:

* **Dry-run reachability check** – ostruct sends a quick ``HEAD`` request; if the URL is reachable the
  execution plan shows:

  .. code-block:: text

     📎 Attachments (1):
        🌐 deck → user-data: https://example.com/path/StartupPitch.pdf

  Unreachable links display ❌ so you can fix them before a live run.
* **Template access** – the file appears as `deck` in the template but **only metadata** is available:

  - `deck.name`, `deck.size`, `deck.is_url`
  - **No** `deck.content` (raises TemplateBinaryError)

* **Model choice** – ensure you pick a **vision-enabled** model (e.g. `gpt-4o` or `gpt-4.1`).  Using a
  non-vision model triggers `UserDataNotSupportedError` during validation.

Template snippet:

.. code-block:: jinja

   ---
   system_prompt: "You are a VC analyst. Summarise the following deck."
   ---

   # Deck Metadata

   * File name: {{ deck.name }}
   * URL: {{ deck }}
   * Size: {{ (deck.size or 0) // 1024 }} KB

   # Task

   Provide a concise summary covering:

   1. Company overview
   2. Problem & solution
   3. Market size
   4. Traction & metrics
   5. Funding ask

Best-practice reminders
-----------------------

* **Don’t** embed the PDF text with `deck.content` – user-data files are opaque to the template.
* Keep PDFs under **512 MB** (50 MB+ triggers a warning, >512 MB aborts the run).
* Use HTTPS URLs or whitelist insecure links with ``--allow-insecure-url``.

Progressive Disclosure Pattern
------------------------------

Handle large codebases by analyzing structure first, then using Code Interpreter for detailed analysis:

.. code-block:: jinja

   ---
   system_prompt: You are a software architect analyzing a codebase.
   ---

   # Project Architecture Analysis

   ## High-Level Overview
   {% set total_files = repo_files | length %}
   This project contains {{ total_files }} files.

   ## Directory Structure
   {% for file in repo_files %}
   - {{ file.path }} ({{ file.size }} bytes)
   {% endfor %}

   ## Analysis Request
   Please analyze the uploaded codebase and provide:

   1. **Architecture Overview**: Identify the main components and their relationships
   2. **Technology Stack**: List the programming languages, frameworks, and tools used
   3. **Code Quality Assessment**: Evaluate code structure, patterns, and potential issues
   4. **Detailed Report**: Create a comprehensive analysis report as a downloadable file

   For the detailed analysis, please:
   - Read and analyze each source file
   - Generate statistics about code complexity, dependencies, and structure
   - Create visualizations if helpful (architecture diagrams, dependency graphs)
   - Save your complete analysis as analysis_report.md

**Schema (analysis_schema.json):**

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "architecture_overview": {
         "type": "string",
         "description": "High-level description of the codebase architecture"
       },
       "technology_stack": {
         "type": "array",
         "items": {"type": "string"},
         "description": "List of technologies, languages, and frameworks used"
       },
       "code_quality_score": {
         "type": "integer",
         "minimum": 1,
         "maximum": 10,
         "description": "Overall code quality rating"
       },
       "analysis_report_link": {
         "type": "string",
         "description": "Download link text for the detailed analysis report"
       }
     },
     "required": ["architecture_overview", "technology_stack", "code_quality_score"]
   }

**Usage:**

.. code-block:: bash

   # Upload entire repository for Code Interpreter analysis
   ostruct run analysis_template.j2 analysis_schema.json \
     --file ci:repo_files /path/to/codebase \
     -V project_name="MyProject"

.. note::
   This pattern leverages Code Interpreter to read and analyze files at runtime,
   avoiding token limits from embedding large amounts of source code directly in the template.
   ostruct automatically handles file downloads when Code Interpreter generates files.

Managing Token Consumption in Multi-Tool Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using multiple tools with large files, be aware of additional token consumption:

.. code-block:: bash

   # This will NOT trigger context window errors (tool files ignored in validation)
   ostruct --file fs:large_doc.pdf --file ci:large_doc.pdf template.j2 schema.json

   # But File Search will inject 15K-25K tokens of retrieved content at runtime
   # Monitor actual usage in OpenAI dashboard

**Key Points:**
- Tool files don't count toward context window validation
- File Search injects significant content (15K-25K tokens per file)
- Code Interpreter has session overhead (~387 tokens)
- Actual token consumption may exceed validation estimates

**References:**
- `OpenAI Community: File Search Token Usage <https://community.openai.com/t/processing-large-documents-128k-limit/620347>`_
- `Tool Pricing Details <https://platform.openai.com/docs/assistants/tools>`_

Dynamic Content Generation
==========================

Conditional Template Sections
-----------------------------

Adapt template content based on available data:

.. code-block:: jinja

   ---
   system_prompt: You are a comprehensive code reviewer.
   ---

   # Code Review Report

   {% if config_files is defined and config_files | length > 0 %}
   ## Configuration Analysis
   Configuration files uploaded: {{ config_files | length }}
   {% for file in config_files %}
   - {{ file.name }} ({{ file.size }} bytes)
   {% endfor %}

   Please analyze the configuration files for:
   - Security best practices
   - Performance settings
   - Potential misconfigurations
   {% endif %}

   {% if test_files is defined and test_files | length > 0 %}
   ## Test Coverage Analysis
   Test files found: {{ test_files | length }}
   {% for file in test_files %}
   - {{ file.name }} ({{ file.size }} bytes)
   {% endfor %}

   Please analyze test coverage and quality.
   {% endif %}

   {% if source_code is defined and source_code | length > 0 %}
   ## Source Code Review
   Source files uploaded: {{ source_code | length }}
   {% for file in source_code %}
   - {{ file.path }} ({{ file.size }} bytes)
   {% endfor %}

   Please perform a comprehensive code review focusing on:
   - Code quality and maintainability
   - Security vulnerabilities
   - Performance issues
   - Best practice adherence
   {% endif %}

   {% if not (config_files is defined or test_files is defined or source_code is defined) %}
   ## No Code Files Provided
   Please provide source code files for analysis using the appropriate CLI flags:
   - `--file ci:config_files /path/to/config/` for configuration files
   - `--file ci:test_files /path/to/tests/` for test files
   - `--file ci:source_code /path/to/src/` for source code
   {% endif %}

Smart File Filtering
--------------------

Process files intelligently based on content and metadata:

.. code-block:: jinja

   ---
   system_prompt: You are a security auditor.
   ---

   # Security Audit Report

   {% set critical_files = [] %}
   {% set config_files = [] %}
   {% set source_files = [] %}

   {% for file in all_files %}
     {% set file_extension = file.path.suffix[1:] if file.path.suffix else '' %}
     {% if file.name in ['config.py', 'settings.py', '.env', 'secrets.yaml'] %}
       {% set _ = critical_files.append(file) %}
     {% elif file_extension in ['json', 'yaml', 'yml', 'ini', 'conf'] %}
       {% set _ = config_files.append(file) %}
     {% elif file_extension in ['py', 'js', 'java', 'cpp', 'c'] %}
       {% set _ = source_files.append(file) %}
     {% endif %}
   {% endfor %}

   ## Critical Security Files
   {% if critical_files | length > 0 %}
   **CRITICAL FILES DETECTED**: {{ critical_files | length }}
   {% for file in critical_files %}
   - {{ file.name }} ({{ file.size }} bytes)
   {% endfor %}

   Please perform detailed security analysis of these critical files.
   {% endif %}

   ## Configuration Files
   {% if config_files | length > 0 %}
   Configuration files found: {{ config_files | length }}
   {% for file in config_files %}
   - {{ file.name }} ({{ file.size }} bytes)
   {% endfor %}

   Please audit configuration files for security issues.
   {% endif %}

   ## Source Code Security Analysis
   {% if source_files | length > 0 %}
   Source files for security review: {{ source_files | length }}
   {% for file in source_files %}
   - {{ file.path }} ({{ file.size }} bytes)
   {% endfor %}

   Please analyze source code for:
   - SQL injection vulnerabilities
   - XSS vulnerabilities
   - Authentication/authorization issues
   - Input validation problems
   - Cryptographic weaknesses
   {% endif %}

Performance Optimization
========================

Large File Handling
-------------------

Handle large files efficiently using Code Interpreter instead of template embedding:

.. code-block:: jinja

   ---
   system_prompt: You are a code reviewer focused on efficiency.
   ---

   # Efficient Large File Analysis

   ## Files for Analysis
   {% for file in source_files %}
   - {{ file.path }} ({{ file.size }} bytes)
   {% endfor %}

   ## Analysis Instructions
   Please analyze the uploaded files efficiently:

   1. **For small files** (< 1KB): Provide complete analysis
   2. **For medium files** (1KB - 10KB): Focus on key patterns and issues
   3. **For large files** (> 10KB): Provide structural analysis and highlight critical sections

   For each file, please:
   - Identify the file type and purpose
   - Analyze code quality and structure
   - Flag any potential issues or improvements
   - For large files, focus on function/class definitions and key logic

   Create a summary report and save it as analysis_summary.md

Token-Aware Content Selection
-----------------------------

Manage large datasets by using Code Interpreter for processing:

.. code-block:: jinja

   ---
   system_prompt: You are an efficient code analyzer.
   ---

   # Smart Content Selection and Analysis

   ## Dataset Overview
   Files available for analysis: {{ source_files | length }}
   {% for file in source_files %}
   - {{ file.path }} ({{ file.size }} bytes)
   {% endfor %}

   ## Processing Strategy
   Please analyze the files using this priority approach:

   1. **Small files first** (< 5KB): Analyze completely
   2. **Medium files** (5KB - 50KB): Focus on key sections
   3. **Large files** (> 50KB): Structural analysis only

   For efficient processing:
   - Start with smaller files to understand the codebase structure
   - For large files, focus on imports, class definitions, and main functions
   - Generate a consolidated analysis report
   - Track your analysis progress and token usage

   Please create a final report as smart_analysis.md that includes:
   - Summary of files processed
   - Key findings and recommendations
   - Analysis methodology used

Error Handling and Robustness
=============================

Defensive Template Programming
------------------------------

Handle missing or malformed data gracefully using macros that check for the existence of file variables before attempting to use them.

.. code-block:: jinja

   ---
   system_prompt: You are a robust data analyzer.
   ---

   # Defensive Data Analysis

   {% macro safe_file_analysis(files, file_type_name="files") %}
   {% if files is defined and files | length > 0 %}
   ## Analyzing {{ files | length }} {{ file_type_name }}

   {% for file in files %}
   - {{ file.path }} ({{ file.size }} bytes)
   {% endfor %}

   Please analyze the content of the {{ file_type_name }} listed above.

   {% else %}
   ## No {{ file_type_name }} provided, skipping analysis.
   {% endif %}
   {% endmacro %}

   {{ safe_file_analysis(source_code, "source code") }}

   {{ safe_file_analysis(config_files, "configuration") }}

   {{ safe_file_analysis(documentation, "documentation") }}

Input Validation
----------------

Validate and sanitize input data:

.. code-block:: jinja

   ---
   system_prompt: You are a data validator and analyzer.
   ---

   # Input Validation and Analysis

   {% set validation_errors = [] %}

   {# Validate required variables #}
   {% if not (source_files is defined and source_files | length > 0) %}
   {% set _ = validation_errors.append("No source files provided") %}
   {% endif %}

   {% if project_name is not defined or project_name | length == 0 %}
   {% set _ = validation_errors.append("Project name is required") %}
   {% endif %}

   {# Validate file formats #}
   {% if source_files is defined %}
   {% for file in source_files %}
   {% set file_extension = file.path.suffix[1:] if file.path.suffix else '' %}
   {% if file_extension not in ['py', 'js', 'java', 'cpp', 'c', 'go', 'rs'] %}
   {% set _ = validation_errors.append("Unsupported file type: " + file.name) %}
   {% endif %}
   {% endfor %}
   {% endif %}

   {% if validation_errors | length > 0 %}
   ## Validation Errors
   {% for error in validation_errors %}
   - ❌ {{ error }}
   {% endfor %}

   Please correct these issues and try again.

   {% else %}
   ## Analysis Proceeding
   ✅ All validation checks passed

   ### Project: {{ project_name }}
   {% for file in source_files %}
   - {{ file.name }} ({{ file.size }} bytes)
   {% endfor %}

   Please proceed with analysis of the validated files.
   {% endif %}

Template Composition Patterns
=============================

Macro Libraries
---------------

Create reusable template macros:

.. code-block:: jinja

   {# Define reusable macros #}
   {% macro render_file_summary(file) %}
   **{{ file.name }}** ({{ file.size }} bytes)
   - Path: {{ file.path }}
   - Extension: {{ file.path.suffix or 'none' }}
   {% endmacro %}

   {% macro render_file_list(files) %}
   {% for file in files %}
   - {{ file.path }} ({{ file.size }} bytes)
   {% endfor %}
   {% endmacro %}

   {% macro render_file_tree(files) %}
   ```
   {% for file in files %}
   {{ file.path }}
   {% endfor %}
   ```
   {% endmacro %}

   # Project Analysis

   ## File Overview
   {{ render_file_tree(source_files) }}

   ## File Details
   {% for file in source_files %}
   {{ render_file_summary(file) }}
   {% endfor %}

   ## Analysis Request
   Please analyze the uploaded source files and provide detailed insights.

Template Inheritance Simulation
-------------------------------

Simulate template inheritance using includes and macros:

**base-analysis.j2:**

.. code-block:: jinja

   {% macro analysis_header(title, project_name) %}
   # {{ title }}

   **Project**: {{ project_name | default("Unnamed Project") }}
   **Files Analyzed**: {{ source_files | length if source_files is defined else 0 }}
   {% endmacro %}

   {% macro analysis_footer() %}

   ---
   *Analysis completed with ostruct*
   {% endmacro %}

**security-analysis.j2:**

.. code-block:: jinja

   ---
   include_system: shared/security-expert.txt
   ---

   {% include 'base-analysis.j2' %}

   {{ analysis_header("Security Analysis Report", project_name) }}

   ## Security Assessment
   Files for security analysis: {{ source_files | length }}
   {% for file in source_files %}
   - {{ file.name }} ({{ file.size }} bytes)
   {% endfor %}

   Please perform a comprehensive security analysis of the uploaded files focusing on:
   - Vulnerability detection
   - Security best practices
   - Potential attack vectors
   - Compliance issues

   {{ analysis_footer() }}

Best Practices Summary
======================

Template Design Principles
--------------------------

1. **Defensive Programming**: Always check if variables exist before using them
2. **Uniform Iteration**: Treat all file variables as collections for consistency
3. **Clear Structure**: Use consistent formatting and clear section headers
4. **Tool Integration**: Leverage Code Interpreter for file analysis instead of embedding content
5. **Error Handling**: Provide meaningful error messages and fallbacks
6. **Modularity**: Use macros and includes for reusable components
7. **Schema-Aware Prompting**: Write prompts that guide the model to produce output matching your JSON schema.
8. **File References**: Use proper FileInfo properties (``file.path``, ``file.size``, ``file.name``)

Template Debugging Strategies
-----------------------------

1. **Start Simple**: Begin with basic templates and add complexity gradually
2. **Use Dry Run**: Always test with ``--dry-run`` before live execution
3. **Incremental Development**: Test each section of complex templates separately
4. **Validation First**: Validate inputs before processing
5. **Clear Error Messages**: Provide helpful error messages for common issues
6. **Test Both Modes**: Use dry-run for template validation, live calls for API testing
7. **Schema Validation**: Ensure your JSON schema matches template expectations

See Also
========

- :doc:`template_guide` - Comprehensive template documentation
- :doc:`template_quick_reference` - Quick syntax reference
- :doc:`cli_reference` - Command-line options and debugging
- :doc:`tool_integration` - Multi-tool integration patterns
