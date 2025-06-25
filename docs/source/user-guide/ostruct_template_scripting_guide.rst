ostruct Template Scripting Guide
================================

This comprehensive guide teaches you everything you need to know about creating effective prompt templates for ostruct. You don't need prior Jinja2 knowledge—this guide covers ostruct's complete templating capabilities from basics to advanced techniques.

.. note::
   ostruct uses a customized Jinja2 environment with enhanced capabilities specifically designed for AI prompt engineering and structured data processing.

.. tip::
   **Quick Start**: Jump to :ref:`practical-examples` if you prefer learning by example, or start with :ref:`template-basics` for a systematic approach.

.. _template-basics:

Template Basics
===============

What Are ostruct Templates?
---------------------------

ostruct templates are text files (typically with ``.j2`` extension though you can use any other extension) that combine:

- **Static text** - Content that appears exactly as written
- **Dynamic variables** - Placeholders that get replaced with actual data
- **Logic and control** - Loops, conditions, and data processing
- **Filters** - Functions that transform and format data
- **Configuration** - YAML frontmatter for system prompts and settings

Basic Template Structure
------------------------

Here's a simple template that demonstrates core concepts:

.. code-block:: jinja

   ---
   system_prompt: You are an expert code reviewer with 10+ years of experience.
   ---

   # Code Review Request

   Please review the following {{ file_type }} file:

   **File**: {{ source_code.name }}
   **Size**: {{ source_code.size }} bytes
   **Last Modified**: {{ source_code.mtime }}

   ```{{ file_type }}
   {{ source_code.content }}
   ```

   Focus on:
   {% for area in review_areas %}
   - {{ area }}
   {% endfor %}

This template shows:

- **YAML frontmatter** (``---`` blocks) for configuration
- **Variables** (``{{ variable_name }}``) for dynamic content
- **Control structures** (``{% for %}``) for loops and logic
- **Static text** mixed throughout

.. _variables-and-data:

Variables and Data Access
=========================

Understanding Variable Sources
------------------------------

ostruct provides data through several sources:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Source
     - How to Access
     - Example Usage
   * - **File Variables**
     - From ``--file``, ``--file ci:``, ``--file fs:`` flags
     - ``{{ config_yaml.content }}``
   * - **CLI Variables**
     - From ``-V`` and ``-J`` flags
     - ``{{ project_name }}``
   * - **System Variables**
     - Built-in ostruct context
     - ``{{ stdin }}``
   * - **Global Functions**
     - Template helper functions
     - ``{{ now() }}``

.. _file-variables:

File Variables
==============

File Routing and Variable Creation
----------------------------------

ostruct creates variables from files using different routing options:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Flag
     - Purpose
     - Template Access
   * - ``--file``
     - Template access only
     - Direct file content and metadata
   * - ``--file ci:``
     - Code Interpreter upload
     - Analysis results and execution context
   * - ``--file fs:``
     - File Search upload
     - Search results and document context

Variable Naming Rules
---------------------

ostruct automatically converts file paths to valid variable names:

.. list-table::
   :header-rows: 1
   :widths: 40 35 25

   * - File Path
     - Generated Variable
     - Rule Applied
   * - ``config.yaml``
     - ``config_yaml``
     - Dots → underscores
   * - ``my-file.txt``
     - ``my_file_txt``
     - Hyphens → underscores
   * - ``hello.world.json``
     - ``hello_world_json``
     - All non-alphanumeric → underscores
   * - ``123data.csv``
     - ``_123data_csv``
     - Prepend underscore if starts with digit

**Custom Variable Names**

Override auto-naming with explicit names:

.. code-block:: bash

   # Auto-naming
   ostruct run template.j2 schema.json --file config config.yaml
   # Creates: config_yaml

   # Custom naming (equals syntax)
   ostruct run template.j2 schema.json --file app_config config.yaml
   # Creates: app_config

   # Custom naming (alias syntax - best for tab completion)
   ostruct run template.j2 schema.json --file app_config config.yaml
   # Creates: app_config

.. _file-content-access:

File Content Access
-------------------

**Critical**: Always use ``.content`` to access file content in templates:

.. code-block:: jinja

   ✅ Correct:   {{ my_file.content }}
   ❌ Incorrect: {{ my_file }}  # Shows guidance message, not content

**File Object Properties**

Each file variable provides rich metadata:

.. code-block:: jinja

   {# Content and paths #}
   {{ file.content }}        <!-- File contents as string -->
   {{ file.path }}           <!-- Relative path from base directory -->
   {{ file.abs_path }}       <!-- Absolute filesystem path -->
   {{ file.name }}           <!-- File name with extension -->

   {# File properties #}
   {{ file.basename }}       <!-- Name without extension -->
   {{ file.extension }}      <!-- Extension (e.g., "txt") -->
   {{ file.stem }}           <!-- Name without extension -->
   {{ file.dirname }}        <!-- Parent directory name -->
   {{ file.parent }}         <!-- Parent directory path -->

   {# Metadata #}
   {{ file.size }}           <!-- File size in bytes -->
   {{ file.mtime }}          <!-- Modification time -->
   {{ file.encoding }}       <!-- File encoding -->
   {{ file.hash }}           <!-- File hash -->

   {# Type checking #}
   {% if file.exists %}      <!-- File exists -->
   {% if file.is_file %}     <!-- Is a regular file -->
   {% if file.is_dir %}      <!-- Is a directory -->

**Working with Multiple Files**

When processing directories or multiple files:

.. code-block:: jinja

   {# Iterate over all files #}
   {% for file in source_files %}
   ## {{ file.name }}

   **Path**: {{ file.path }}
   **Size**: {{ file.size }} bytes

   ```{{ file.extension }}
   {{ file.content }}
   ```
   {% endfor %}

**Single File Extraction**

Use the ``|single`` filter when you expect exactly one file:

.. code-block:: jinja

   {# Extract single file from a list #}
   {{ (config_files|single).content }}

   {# Error handling - raises error if not exactly 1 file #}
   {% set config = config_files|single %}
   Configuration: {{ config.content }}

.. _template-environment-variables:

Template Environment Variables
==============================

ostruct provides several environment variables to control template processing behavior. These variables only affect template-only file access (``--file alias path``) and do not impact Code Interpreter (``--file ci:``) or File Search (``--file fs:``) operations.

File Size Limits
-----------------

Control how large files are handled in templates:

.. code-block:: bash

   # Set individual file size limit (default: 65536 bytes / 64KB)
   export OSTRUCT_TEMPLATE_FILE_LIMIT=131072  # 128KB

   # Set total file size limit (default: 1048576 bytes / 1MB)
   export OSTRUCT_TEMPLATE_TOTAL_LIMIT=5242880  # 5MB

   # Run with custom limits
   ostruct run template.j2 schema.json --file config large_config.yaml

**When to adjust these limits:**

- **Large configuration files**: Increase limits for processing large YAML/JSON configs
- **Document processing**: Handle larger text files for analysis
- **Memory constraints**: Reduce limits in resource-constrained environments

**Example usage:**

.. code-block:: bash

   # For processing large documentation
   export OSTRUCT_TEMPLATE_FILE_LIMIT=262144    # 256KB per file
   export OSTRUCT_TEMPLATE_TOTAL_LIMIT=10485760 # 10MB total

   ostruct run doc_analysis.j2 schema.json \
     --file docs ./documentation/ \
     --file config ./config.yaml

Template Debug Preview Limits
-----------------------------

Control how much content is shown in template debugging:

.. code-block:: bash

   # Set preview character limit (default: 4096)
   export OSTRUCT_TEMPLATE_PREVIEW_LIMIT=8192  # 8KB preview

   # Run with debug preview
   ostruct run template.j2 schema.json \
     --file data large_file.txt \
     --template-debug preview

**When to adjust preview limits:**

- **Detailed debugging**: Increase for more context in debug output
- **Clean logs**: Decrease for shorter, cleaner debug messages
- **Large files**: Adjust based on typical file sizes you're processing

Environment Variable Scope
---------------------------

**Important**: These environment variables only affect template processing:

.. list-table:: Environment Variable Scope
   :header-rows: 1
   :widths: 30 35 35

   * - Variable
     - Affects Template Files
     - Does NOT Affect
   * - ``OSTRUCT_TEMPLATE_FILE_LIMIT``
     - ``--file alias path``
     - ``--file ci:`` or ``--file fs:``
   * - ``OSTRUCT_TEMPLATE_TOTAL_LIMIT``
     - ``--file alias path``
     - ``--file ci:`` or ``--file fs:``
   * - ``OSTRUCT_TEMPLATE_PREVIEW_LIMIT``
     - Template debug output
     - API calls or tool operations

**Example demonstrating scope:**

.. code-block:: bash

   # These files are subject to template limits
   ostruct run template.j2 schema.json \
     --file config config.yaml \          # ← Template limits apply
     --file docs documentation.md \       # ← Template limits apply
     --file ci:data large_dataset.csv \   # ← Template limits DO NOT apply
     --file fs:docs manual.pdf             # ← Template limits DO NOT apply

Configuration Best Practices
----------------------------

**Set in .env files for project-specific limits:**

.. code-block:: bash

   # .env file in your project
   OSTRUCT_TEMPLATE_FILE_LIMIT=262144
   OSTRUCT_TEMPLATE_TOTAL_LIMIT=5242880
   OSTRUCT_TEMPLATE_PREVIEW_LIMIT=8192

**Set globally for your development environment:**

.. code-block:: bash

   # Add to ~/.bashrc or ~/.zshrc
   export OSTRUCT_TEMPLATE_FILE_LIMIT=131072
   export OSTRUCT_TEMPLATE_TOTAL_LIMIT=2097152
   export OSTRUCT_TEMPLATE_PREVIEW_LIMIT=6144

**Temporary overrides for specific tasks:**

.. code-block:: bash

   # One-time override for large file processing
   OSTRUCT_TEMPLATE_FILE_LIMIT=524288 \
   OSTRUCT_TEMPLATE_TOTAL_LIMIT=10485760 \
   ostruct run large_analysis.j2 schema.json --file data huge_file.txt

.. _cli-variables:

CLI Variables
=============

String Variables (``-V`` flag)
------------------------------

Simple string values passed from the command line:

.. code-block:: bash

   ostruct run template.j2 schema.json -V env=production -V debug=false

.. code-block:: jinja

   Environment: {{ env }}
   Debug mode: {{ debug }}

   {% if env == "production" %}
   Using production settings
   {% else %}
   Using development settings
   {% endif %}

JSON Variables (``-J`` flag)
----------------------------

Complex data structures passed as JSON:

.. code-block:: bash

   ostruct run template.j2 schema.json -J config='{"database": {"host": "localhost", "port": 5432}, "features": ["auth", "logging"]}'

.. code-block:: jinja

   Database: {{ config.database.host }}:{{ config.database.port }}

   Enabled features:
   {% for feature in config.features %}
   - {{ feature }}
   {% endfor %}

.. _control-structures:

Control Structures
==================

Conditional Logic
-----------------

**Basic If Statements**

.. code-block:: jinja

   {% if user_role == "admin" %}
   You have administrative privileges.
   {% elif user_role == "moderator" %}
   You have moderation privileges.
   {% else %}
   You have standard user privileges.
   {% endif %}

**Complex Conditions**

.. code-block:: jinja

   {% if config_file.exists and config_file.size > 0 %}
   Configuration loaded successfully.
   {% endif %}

   {% if env == "production" and debug == "false" %}
   Production mode with debugging disabled.
   {% endif %}

**Checking Variable Existence**

.. code-block:: jinja

   {% if optional_config is defined %}
   Optional configuration: {{ optional_config.content }}
   {% else %}
   Using default configuration.
   {% endif %}

Loops and Iteration
-------------------

**Basic For Loops**

.. code-block:: jinja

   {% for file in source_files %}
   Processing {{ file.name }}...
   {% endfor %}

**Loop with Index**

.. code-block:: jinja

   {% for file in source_files %}
   {{ loop.index }}. {{ file.name }} ({{ file.size }} bytes)
   {% endfor %}

**Loop Variables**

ostruct provides helpful loop variables:

.. code-block:: jinja

   {% for item in items %}
   Item {{ loop.index }} of {{ loop.length }}:
   - First item: {{ loop.first }}
   - Last item: {{ loop.last }}
   - Index (0-based): {{ loop.index0 }}
   - Remaining: {{ loop.revindex }}
   {% endfor %}

**Conditional Loops**

.. code-block:: jinja

   {% for file in source_files if file.extension == "py" %}
   Python file: {{ file.name }}
   {% endfor %}

**Nested Loops**

.. code-block:: jinja

   {% for category in categories %}
   ## {{ category.name }}
   {% for item in category.items %}
   - {{ item.name }}: {{ item.description }}
   {% endfor %}
   {% endfor %}

.. _filters-and-functions:

Filters and Functions
=====================

Text Processing Filters
-----------------------

**Basic Text Operations**

.. code-block:: jinja

   {# Word and character counting #}
   Word count: {{ content | word_count }}
   Character count: {{ content | char_count }}

   {# Text formatting #}
   {{ text | upper }}           <!-- UPPERCASE -->
   {{ text | lower }}           <!-- lowercase -->
   {{ text | title }}           <!-- Title Case -->
   {{ text | capitalize }}      <!-- Capitalize first letter -->

**Text Manipulation**

.. code-block:: jinja

   {# Wrapping and indentation #}
   {{ long_text | wrap(80) }}           <!-- Wrap to 80 characters -->
   {{ code_block | indent(4) }}         <!-- Indent by 4 spaces -->
   {{ messy_text | normalize }}         <!-- Normalize whitespace -->

   {# Content cleaning #}
   {{ markdown_text | strip_markdown }}     <!-- Remove markdown formatting -->
   {{ code_with_comments | remove_comments }}  <!-- Remove code comments -->

**Advanced Text Processing**

.. code-block:: jinja

   {# JSON operations #}
   {{ data | to_json }}                 <!-- Convert to JSON string -->
   {{ json_string | from_json }}        <!-- Parse JSON string -->

   {# Validation #}
   {% if user_input | validate_json %}
   Valid JSON provided
   {% endif %}

Code Processing Filters
-----------------------

**Syntax Highlighting**

.. code-block:: jinja

   {# Format code with syntax highlighting #}
   {{ python_code | format_code("terminal", "python") }}
   {{ javascript_code | format_code("html", "javascript") }}
   {{ generic_code | format_code("plain") }}

**Comment Removal**

.. code-block:: jinja

   {# Remove comments by language #}
   {{ python_code | strip_comments("python") }}
   {{ js_code | strip_comments("javascript") }}
   {{ java_code | strip_comments("java") }}

Data Processing Filters
-----------------------

**List Operations**

.. code-block:: jinja

   {# Sorting and filtering #}
   {{ items | sort_by("name") }}                    <!-- Sort by property -->
   {{ items | filter_by("status", "active") }}     <!-- Filter by value -->
   {{ items | unique }}                             <!-- Remove duplicates -->

   {# Data extraction #}
   {{ users | extract_field("email") }}            <!-- Extract specific field -->
   {{ values | frequency }}                         <!-- Count frequencies -->

**Grouping and Aggregation**

.. code-block:: jinja

   {# Group data #}
   {% set grouped = items | group_by("category") %}
   {% for category, group_items in grouped.items() %}
   ## {{ category }}
   {% for item in group_items %}
   - {{ item.name }}
   {% endfor %}
   {% endfor %}

   {# Calculate statistics #}
   {% set stats = numbers | aggregate %}
   Total: {{ stats.sum }}
   Average: {{ stats.avg }}
   Min/Max: {{ stats.min }}/{{ stats.max }}

Table Formatting Filters
------------------------

**Automatic Table Generation**

.. code-block:: jinja

   {# Convert data to tables #}
   {{ dictionary | dict_to_table }}        <!-- Dictionary to table -->
   {{ list_data | list_to_table }}         <!-- List to table -->
   {{ any_data | auto_table }}             <!-- Auto-detect format -->

**Custom Table Formatting**

.. code-block:: jinja

   {# Manual table creation #}
   {{ headers | table(rows) }}                      <!-- Basic table -->
   {{ headers | align_table(rows, ["left", "center", "right"]) }}  <!-- Aligned table -->

Global Functions
----------------

**Utility Functions**

.. code-block:: jinja

   {# Date and time #}
   Current time: {{ now() }}

   {# Token estimation #}
   Estimated tokens: {{ content | estimate_tokens }}

   {# Debugging #}
   {{ debug(variable) }}                    <!-- Print debug info -->
   Type: {{ type_of(variable) }}           <!-- Get type name -->
   Attributes: {{ dir_of(variable) }}      <!-- List attributes -->

**Data Analysis Functions**

.. code-block:: jinja

   {# Statistical analysis #}
   {% set summary = summarize(data_list) %}
   Total records: {{ summary.total_records }}

   {# Pivot tables #}
   {% set pivot = pivot_table(sales_data, "region", "amount", "sum") %}
   {% for region, data in pivot.aggregates.items() %}
   {{ region }}: ${{ data.value }}
   {% endfor %}

.. _yaml-frontmatter:

YAML Frontmatter
================

Configuration and System Prompts
--------------------------------

Templates can include YAML configuration at the top:

.. code-block:: jinja

   ---
   system_prompt: |
     You are an expert software architect with deep knowledge of:
     - Microservices design patterns
     - Cloud-native architectures
     - Security best practices
     - Performance optimization
   ---

   # Architecture Review

   Please analyze the following system design...

**Available Configuration Options**

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Option
     - Purpose
     - Example
   * - ``system_prompt``
     - Define AI's role and expertise
     - ``You are an expert...``
   * - ``include_system``
     - Include shared system prompts
     - ``shared/expert.txt``

.. note::
   **Model and Temperature Configuration**: Model and temperature must be specified via CLI flags (``--model gpt-4o --temperature 0.7``) as they are not currently supported in YAML frontmatter.

**Dynamic System Prompts**

System prompts can use template variables:

.. code-block:: jinja

   ---
   system_prompt: |
     You are an expert {{ domain }} specialist with {{ experience_years }} years of experience.
     Your expertise includes {{ specializations | join(", ") }}.
   ---

.. _practical-examples:

Practical Examples
==================

Example 1: Code Review Template
-------------------------------

**Template** (``code_review.j2``):

.. code-block:: jinja

   ---
   system_prompt: |
     You are a senior software engineer performing code reviews.
     Focus on security, performance, maintainability, and best practices.
   ---

   # Code Review: {{ project_name | default("Unnamed Project") }}

   ## Files for Review

   {% for file in source_code %}
   ### {{ file.path }}

   **Language**: {{ file.extension }}
   **Size**: {{ file.size }} bytes
   **Last Modified**: {{ file.mtime }}

   ```{{ file.extension }}
   {{ file.content }}
   ```

   {% endfor %}

   ## Review Criteria

   Please evaluate each file for:

   {% for criterion in review_criteria %}
   - **{{ criterion.name }}**: {{ criterion.description }}
   {% endfor %}

   ## Additional Context

   {% if documentation is defined %}
   **Project Documentation**:
   {{ documentation.content | truncate(500) }}
   {% endif %}

   **Review Focus**: {{ focus_areas | join(", ") }}
   **Target Audience**: {{ target_audience }}

**Usage**:

.. code-block:: bash

   ostruct run code_review.j2 review_schema.json \
     --dir ci:data source_code ./src/ \
     --file config documentation README.md \
     -V project_name="My Web App" \
     -V target_audience="junior developers" \
     -J review_criteria='[
       {"name": "Security", "description": "Check for vulnerabilities"},
       {"name": "Performance", "description": "Identify bottlenecks"}
     ]' \
     -J focus_areas='["error handling", "input validation"]'

Example 2: Data Analysis Template
---------------------------------

**Template** (``data_analysis.j2``):

.. code-block:: jinja

   ---
   system_prompt: |
     You are a data scientist with expertise in statistical analysis,
     data visualization, and business intelligence.
   ---

   # Data Analysis Report

   ## Dataset Overview

   {% for dataset in datasets %}
   ### {{ dataset.name }}

   **Format**: {{ dataset.extension }}
   **Size**: {{ dataset.size | filesizeformat }}
   **Records**: {{ dataset.content | from_json | length if dataset.extension == "json" else "Unknown" }}

   {% if dataset.extension == "csv" %}
   **Sample Data** (first 5 lines):
   ```
   {{ dataset.content.split('\n')[:5] | join('\n') }}
   ```
   {% endif %}

   {% endfor %}

   ## Analysis Requirements

   {% if analysis_config is defined %}
   **Metrics to Calculate**:
   {% for metric in analysis_config.metrics %}
   - {{ metric.name }}: {{ metric.description }}
   {% endfor %}

   **Grouping**: {{ analysis_config.group_by | join(", ") }}
   **Time Period**: {{ analysis_config.time_range }}
   {% endif %}

   ## Expected Deliverables

   1. **Statistical Summary**: {{ deliverables.summary | default("Basic descriptive statistics") }}
   2. **Trend Analysis**: {{ deliverables.trends | default("Time-series analysis") }}
   3. **Recommendations**: {{ deliverables.recommendations | default("Actionable insights") }}

   {% if constraints is defined %}
   ## Constraints and Considerations

   {% for constraint in constraints %}
   - **{{ constraint.type }}**: {{ constraint.description }}
   {% endfor %}
   {% endif %}

**Usage**:

.. code-block:: bash

   ostruct run data_analysis.j2 analysis_schema.json \
     --file ci:data datasets ./data/ \
     -J analysis_config='{
       "metrics": [
         {"name": "Revenue Growth", "description": "Month-over-month revenue change"},
         {"name": "Customer Retention", "description": "Percentage of returning customers"}
       ],
       "group_by": ["region", "product_category"],
       "time_range": "Q4 2023"
     }' \
     -J deliverables='{
       "summary": "Comprehensive statistical analysis with confidence intervals",
       "trends": "Seasonal patterns and growth trajectories",
       "recommendations": "Strategic recommendations for Q1 2024"
     }'

Example 3: Multi-Tool Integration Template
------------------------------------------

**Template** (``comprehensive_analysis.j2``):

.. code-block:: jinja

   ---
   system_prompt: |
     You are a senior technical consultant performing comprehensive system analysis.
     You have access to code execution, document search, and web search capabilities.
   ---

   # Comprehensive System Analysis

   ## Code Analysis

   {% if source_code is defined %}
   **Source Code Files** ({{ source_code | length }} files):
   {% for file in source_code %}
   - {{ file.path }} ({{ file.size }} bytes, {{ file.content | word_count }} words)
   {% endfor %}

   Please analyze the codebase for:
   - Architecture patterns and design quality
   - Performance bottlenecks and optimization opportunities
   - Security vulnerabilities and compliance issues
   - Code maintainability and technical debt
   {% endif %}

   ## Documentation Review

   {% if documentation is defined %}
   **Available Documentation**:
   {% for doc in documentation %}
   - {{ doc.name }} ({{ doc.extension }} format)
   {% endfor %}

   Use the documentation to understand:
   - System requirements and specifications
   - Deployment and operational procedures
   - Known issues and limitations
   {% endif %}

   ## Configuration Analysis

   {% if config_files is defined %}
   **Configuration Files**:
   {% for config in config_files %}
   ### {{ config.name }}
   ```{{ config.extension }}
   {{ config.content }}
   ```
   {% endfor %}
   {% endif %}

   ## Analysis Scope

   **Primary Focus**: {{ analysis_scope.primary }}
   **Secondary Areas**: {{ analysis_scope.secondary | join(", ") }}
   **Deliverable Format**: {{ output_format }}

   {% if external_research %}
   ## External Research Required

   Please also research current best practices and industry standards for:
   {% for topic in research_topics %}
   - {{ topic }}
   {% endfor %}
   {% endif %}

**Usage**:

.. code-block:: bash

   ostruct run comprehensive_analysis.j2 analysis_schema.json \
     --dir ci:data source_code ./src/ \
     --file fs:docs documentation ./docs/ \
     --file config config_files ./config/ \
     --enable-tool web-search \
     -J analysis_scope='{
       "primary": "Security and performance assessment",
       "secondary": ["scalability", "maintainability", "compliance"]
     }' \
     -V output_format="Executive summary with technical appendix" \
     -V external_research=true \
     -J research_topics='["cloud security best practices", "microservices monitoring"]'

.. _advanced-techniques:

Advanced Techniques
===================

Template Optimization
---------------------

**Conditional Content Loading**

Only include expensive operations when needed:

.. code-block:: jinja

   {% if detailed_analysis %}
   {# Only perform expensive analysis if requested #}
   {% for file in large_dataset %}
   {{ file.content | complex_analysis }}
   {% endfor %}
   {% endif %}

**Efficient File Processing**

Process files selectively based on criteria:

.. code-block:: jinja

   {# Only process relevant files #}
   {% for file in source_files if file.extension in ["py", "js", "ts"] %}
   {# Process only code files #}
   {% endfor %}

   {# Skip large files in quick mode #}
   {% for file in files if quick_mode and file.size < 10000 or not quick_mode %}
   {# Conditional processing based on mode #}
   {% endfor %}

Error Handling and Defensive Programming
----------------------------------------

**Safe Variable Access**

.. code-block:: jinja

   {# Safe access with defaults #}
   {{ config.database.host | default("localhost") }}
   {{ user.preferences.theme | default("light") }}

   {# Check existence before access #}
   {% if config and config.database %}
   Database: {{ config.database.host }}
   {% endif %}

**Graceful Degradation**

.. code-block:: jinja

   {# Provide fallbacks for missing data #}
   {% if detailed_logs is defined and detailed_logs %}
   {# Show detailed analysis #}
   {% else %}
   {# Show summary analysis #}
   Basic analysis based on available data...
   {% endif %}

**Input Validation**

.. code-block:: jinja

   {# Validate required variables #}
   {% if not project_name %}
   {% set project_name = "Unnamed Project" %}
   {% endif %}

   {# Validate data types #}
   {% if config_data | validate_json %}
   Configuration is valid JSON
   {% else %}
   Warning: Invalid configuration format
   {% endif %}

Template Modularity
-------------------

**Reusable Macros**

.. code-block:: jinja

   {# Define reusable components #}
   {% macro file_summary(file) %}
   **{{ file.name }}** ({{ file.size }} bytes)
   - Path: {{ file.path }}
   - Modified: {{ file.mtime }}
   - Type: {{ file.extension }}
   {% endmacro %}

   {# Use the macro #}
   {% for file in files %}
   {{ file_summary(file) }}
   {% endfor %}

**Conditional Includes**

.. code-block:: jinja

   {# Include different sections based on context #}
   {% if analysis_type == "security" %}
   {% include "security_analysis_section.j2" %}
   {% elif analysis_type == "performance" %}
   {% include "performance_analysis_section.j2" %}
   {% endif %}

.. _troubleshooting:

Troubleshooting
===============

Common Issues and Solutions
---------------------------

**Issue: Guidance message appears instead of file content**

**Problem**: Using ``{{ variable }}`` instead of ``{{ variable.content }}``

.. code-block:: jinja

   ❌ Wrong:   {{ my_file }}        # Shows: guidance message
   ✅ Correct: {{ my_file.content }}  # Shows: actual file content

**Issue: "UndefinedError" for file variables**

**Solutions**:

1. Check file path and variable name
2. Verify correct file routing flag (``--file``, ``--file ci:``, ``--file fs:``)
3. Use ``--template-debug vars`` to see available variables

.. code-block:: bash

   ostruct run template.j2 schema.json --file config config.yaml --template-debug vars

**Issue: Template breaks with different directory structures**

**Problem**: Using auto-naming with changing directory names

.. code-block:: bash

   # ❌ Problem: variable name depends on directory name
   ostruct run template.j2 schema.json --dir ci:data ./project_v1/src    # → src variable
   ostruct run template.j2 schema.json --dir ci:data ./project_v2/source # → source variable

**Solution**: Use directory aliases for stable variable names

.. code-block:: bash

   # ✅ Solution: stable variable name
   ostruct run template.j2 schema.json --dir ci:code ./project_v1/src    # → code variable
   ostruct run template.j2 schema.json --dir ci:code ./project_v2/source # → code variable

**Issue: Empty or missing content**

**Solution**: Add defensive checks

.. code-block:: jinja

   {% if my_file and my_file.content %}
   Content: {{ my_file.content }}
   {% else %}
   File is empty or could not be read.
   {% endif %}

Debugging Templates
-------------------

**Show Available Variables**

.. code-block:: jinja

   {# Debug: Show all available variables #}
   Available variables:
   {% for key in context.keys() %}
   - {{ key }}: {{ type_of(context[key]) }}
   {% endfor %}

**Inspect Variable Content**

.. code-block:: jinja

   {# Debug: Inspect variable structure #}
   {{ debug(my_variable) }}
   Type: {{ type_of(my_variable) }}
   Attributes: {{ dir_of(my_variable) }}

**Validate Template Logic**

.. code-block:: jinja

   {# Debug: Check conditions #}
   {% if condition %}
   Condition is true
   {% else %}
   Condition is false: {{ condition }}
   {% endif %}

Best Practices
==============

Template Organization
---------------------

1. **Use descriptive variable names**

   .. code-block:: bash

      # ✅ Good
      --file app_config config.yaml
      --file ci:sales_data data.csv

      # ❌ Avoid
      --file config config.yaml  # Creates config_yaml

2. **Structure templates logically**

   .. code-block:: jinja

      ---
      system_prompt: Clear role definition
      ---

      # Main heading

      ## Context section
      {# Provide all necessary context #}

      ## Instructions section
      {# Clear, specific instructions #}

      ## Output requirements
      {# Specify expected format #}

3. **Use consistent formatting**

   .. code-block:: jinja

      {# Consistent spacing and indentation #}
      {% for item in items %}
      - {{ item.name }}: {{ item.value }}
      {% endfor %}

Performance Optimization
------------------------

1. **Minimize expensive operations**

   .. code-block:: jinja

      {# ✅ Good: Process only when needed #}
      {% if detailed_mode %}
      {{ large_dataset | complex_analysis }}
      {% endif %}

      {# ❌ Avoid: Always processing everything #}
      {{ large_dataset | complex_analysis }}

2. **Use appropriate file routing**

   .. code-block:: bash

      # ✅ Good: Route files to appropriate tools
      --file config config.yaml      # Template-only (fast)
      --file ci:data data.csv         # Code Interpreter (when needed)
      --file fs:docs docs.pdf         # File Search (when needed)

3. **Leverage caching and reuse**

   .. code-block:: jinja

      {# ✅ Good: Calculate once, use multiple times #}
      {% set file_count = source_files | length %}
      Processing {{ file_count }} files...
      Total files: {{ file_count }}

Security Considerations
-----------------------

1. **Validate inputs**

   .. code-block:: jinja

      {% if user_input | validate_json %}
      Processing valid input...
      {% else %}
      Error: Invalid input format
      {% endif %}

2. **Sanitize file content**

   .. code-block:: jinja

      {# Remove potentially harmful content #}
      {{ file.content | strip_comments | escape_special }}

3. **Use safe defaults**

   .. code-block:: jinja

      {# Provide safe fallbacks #}
      {{ config.timeout | default(30) }}
      {{ config.max_retries | default(3) }}

Conclusion
==========

This guide covers ostruct's complete templating capabilities. You now know how to:

- Create dynamic templates with variables and logic
- Process files and data efficiently
- Use filters and functions for data transformation
- Handle errors and edge cases gracefully
- Optimize templates for performance and maintainability

For more examples and advanced patterns, explore the ``examples/`` directory in the ostruct repository.

.. seealso::

   - :doc:`cli_reference` - Complete CLI documentation
   - :doc:`examples` - Practical examples and use cases
