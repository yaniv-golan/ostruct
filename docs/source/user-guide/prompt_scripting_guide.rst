Template Authoring Guide
========================

Learn how to create powerful Jinja2 templates for ostruct that combine static text with dynamic content, file processing, and advanced filtering capabilities.

.. note::
   This guide assumes no prior knowledge of Jinja2. Templates use a customized Jinja2 environment with ostruct-specific enhancements.

.. tip::
   **Schema Creation Tool**: When creating templates, use the **Meta-Schema Generator** to automatically create corresponding JSON schemas:

   .. code-block:: bash

      examples/meta-schema-generator/scripts/generate_and_validate_schema.sh -o my_schema.json my_template.j2

   This ensures your schemas are OpenAI-compliant and match your template structure. See :doc:`examples` for complete documentation.

Template Basics
================

Template Structure
------------------

ostruct templates are Jinja2 files (typically with ``.j2`` extension) that can include:

- **Static text** - Regular content that appears as-is
- **Variables** - Dynamic content from files, CLI arguments, or system data
- **Control structures** - Loops, conditionals, and logic
- **Filters** - Functions to process and transform data
- **YAML frontmatter** - Configuration and system prompts

Basic Template Example
----------------------

.. code-block:: jinja

   ---
   system_prompt: You are an expert data analyst.
   ---
   Analyze this configuration file:

   {{ config_yaml.content }}

   Summary of findings:
   {% for file in logs %}
   - {{ file.name }}: {{ file.content | word_count }} words
   {% endfor %}

Variables and Data Access
=========================

Variable Sources
----------------

ostruct makes data available through several sources:

1. **File Variables** - From file routing options (``--file``, ``--file ci:``, ``--file fs:``)
2. **Directory Variables** - From directory routing options (``--dir``, ``--dir ci:``, ``--dir fs:``)
3. **Literal Variables** - From ``-V key=value`` command line arguments
4. **Environment Variables** - From ``-E`` or ``--env`` flags
5. **System Variables** - Built-in ostruct context

File Variables
==============

Understanding File Routing
---------------------------

Different file routing options make files available in different ways:

.. list-table:: File Routing Options
   :header-rows: 1
   :widths: 20 30 50

   * - Flag
     - Purpose
     - Template Access
   * - ``--file`` (Template)
     - File available in template only
     - Direct content access via ``.content``
   * - ``--file ci:`` (Code Interpreter)
     - Upload for code execution and analysis
     - Analysis results and execution context
   * - ``--file fs:`` (File Search)
     - Upload for semantic search and retrieval
     - Search results and document context

Variable Naming Rules
---------------------

ostruct automatically generates variable names from file paths following these rules:

.. list-table::
   :header-rows: 1
   :widths: 40 35 25

   * - File Path
     - Generated Variable
     - Pattern Applied
   * - ``config.yaml``
     - ``config_yaml``
     - Replace dots with underscores
   * - ``my-file.txt``
     - ``my_file_txt``
     - Replace hyphens with underscores
   * - ``hello.world.json``
     - ``hello_world_json``
     - Replace all non-alphanumeric with underscores
   * - ``123data.csv``
     - ``_123data_csv``
     - Prepend underscore if starts with digit

.. note::
   Frankly, auto-naming was probably not a good idea, and might get deprecated in the future. Probably the best way to go is to use aliases.

Auto-Naming Examples
--------------------

.. code-block:: bash

   # Auto-naming syntax
   ostruct run template.j2 schema.json --file config config.yaml
   # Creates variable: config_yaml

   ostruct run template.j2 schema.json --file ci:data sales-data.csv
   # Creates variable: sales_data_csv

.. code-block:: jinja

   # Access in template (IMPORTANT: use .content)
   Configuration settings:
   {{ config_yaml.content }}

   Sales data summary:
   {{ sales_data_csv.content | word_count }} characters

Custom Variable Names
---------------------

Override auto-naming with explicit variable names:

.. code-block:: bash

   # Two-argument alias syntax
   ostruct run template.j2 schema.json --file app_config config.yaml

.. code-block:: jinja

   # Access with custom name (IMPORTANT: use .content)
   Application configuration:
   {{ app_config.content }}

**Important: File Content Access**

All file variables in ostruct require the ``.content`` property to access file content:

.. code-block:: jinja

   ✅ Correct:   {{ my_file.content }}
   ❌ Incorrect: {{ my_file }}  # Shows guidance message, not content

If you accidentally use ``{{ my_file }}`` without ``.content``, you'll see a helpful message like:
``[File 'config.yaml' - Use {{ my_file.content }} to access file content]``

File Variable Properties
-------------------------

Each file variable provides these properties:

**Content and Path Information:**

.. code-block:: jinja

   {{ file.content }}        <!-- File contents as string -->
   {{ file.path }}           <!-- Relative path from base directory -->
   {{ file.abs_path }}       <!-- Absolute filesystem path -->
   {{ file.name }}           <!-- File name with extension -->

**File Properties:**

.. code-block:: jinja

   {{ file.basename }}       <!-- Name without extension -->
   {{ file.extension }}      <!-- Extension (e.g., "txt") -->
   {{ file.stem }}           <!-- Name without extension -->
   {{ file.dirname }}        <!-- Parent directory name -->
   {{ file.parent }}         <!-- Parent directory path -->

**Metadata:**

.. code-block:: jinja

   {{ file.size }}           <!-- File size in bytes -->
   {{ file.mtime }}          <!-- Modification time -->
   {{ file.encoding }}       <!-- File encoding -->
   {{ file.hash }}           <!-- File hash -->

**Type Checking:**

.. code-block:: jinja

   {% if file.exists %}      <!-- File exists -->
   {% if file.is_file %}     <!-- Is a regular file -->
   {% if file.is_dir %}      <!-- Is a directory -->

File Collection Behavior
-------------------------

**Important:** All file variables in ostruct templates provide a consistent interface whether you're working with single files or collections.

**Adaptive Properties:**

File variables have adaptive properties that return different types based on the content:

- **Single file from file mapping** (``--file``, ``--file ci:``, ``--file fs:``): Returns scalar values
- **Multiple files or directory mapping** (``--dir``): Returns lists

.. code-block:: jinja

   <!-- For single file: my_file contains 1 file from --file ci:my_file data.csv -->
   {{ my_file.name }}        <!-- Returns: "data.csv" (string) -->
   {{ my_file.content }}     <!-- Returns: file contents (string) -->
   {{ my_file.path }}        <!-- Returns: "data.csv" (string) -->
   {{ my_file.size }}        <!-- Returns: 1024 (integer) -->

   <!-- For multiple files: logs contains 3 files from --dir config logs=./log_files -->
   {{ logs.name }}           <!-- Returns: ["app.log", "error.log", "debug.log"] (list) -->
   {{ logs.content }}        <!-- Returns: [content1, content2, content3] (list) -->
   {{ logs.path }}           <!-- Returns: ["app.log", "error.log", "debug.log"] (list) -->
   {{ logs.size }}           <!-- Returns: [1024, 2048, 512] (list) -->

**Always-List Properties:**

For explicit list access, use the ``.names`` property:

.. code-block:: jinja

   <!-- Always returns a list, even for single files -->
   {{ my_file.names }}       <!-- Returns: ["data.csv"] (list) -->
   {{ logs.names }}          <!-- Returns: ["app.log", "error.log", "debug.log"] (list) -->

**Single File Extraction:**

Use the ``|single`` filter to explicitly extract a single file from a list:

.. code-block:: jinja

   <!-- Extract single file when you expect exactly one -->
   {{ (my_files|single).name }}     <!-- Returns the name of the single file -->
   {{ (my_files|single).content }}  <!-- Returns the content of the single file -->

   <!-- Error handling: raises TemplateRuntimeError if not exactly 1 file -->
   {{ empty_list|single.name }}   <!-- Error: expected 1 file, got 0 -->
   {{ multi_files|single.name }}  <!-- Error: expected 1 file, got 3 -->

**List Operations:**

Since file variables support list operations, you can use standard list operations:

.. code-block:: jinja

   <!-- Access individual files by index -->
   {{ my_files[0].content }}     <!-- First file content -->
   {{ my_files[-1].name }}       <!-- Last file name -->

   <!-- Iterate over all files -->
   {% for file in my_files %}
   File: {{ file.name }}
   Content: {{ file.content }}
   {% endfor %}

   <!-- Check list length -->
   Found {{ my_files | length }} files

   <!-- Slice operations -->
   {% for file in my_files[1:3] %}
   Processing: {{ file.name }}
   {% endfor %}

Common File Access Patterns
---------------------------

Here are the most common patterns for working with file variables:

**Single File Content Access:**

.. code-block:: jinja

   <!-- Most common: accessing content of a single file -->
   Configuration:
   {{ config_file.content }}

   <!-- Alternative for single files -->
   Configuration:
   {{ (config_file|single).content }}

**Multiple Files:**

.. code-block:: jinja

   <!-- Processing multiple files -->
   {% for file in source_files %}
   ## {{ file.name }}
   {{ file.content }}
   {% endfor %}

**File Metadata:**

.. code-block:: jinja

   <!-- Using file properties -->
   Processing {{ my_file.name }} ({{ my_file.size }} bytes)
   Last modified: {{ my_file.mtime }}
   Encoding: {{ my_file.encoding }}

**Conditional Processing:**

.. code-block:: jinja

   <!-- Check if files exist or have certain properties -->
   {% if config_file.exists %}
   Configuration loaded: {{ config_file.content }}
   {% else %}
   No configuration file found.
   {% endif %}

Troubleshooting File Variables
------------------------------

**Problem: Guidance message appears instead of file content**

This means you're using ``{{ variable }}`` instead of ``{{ variable.content }}``:

.. code-block:: jinja

   ❌ Wrong:   {{ my_file }}        # Shows: guidance message
   ✅ Correct: {{ my_file.content }}  # Shows: actual file content

**Problem: "UndefinedError" for file variables**

Check that:

1. The file path is correct
2. The variable name matches (check for typos)
3. You're using the right file routing flag

Use ``--template-debug vars`` to see all available variables:

.. code-block:: bash

   ostruct run template.j2 schema.json --file config config.yaml --template-debug vars

**Problem: Empty or missing content**

.. code-block:: jinja

   <!-- Check if file has content -->
   {% if my_file.content %}
   Content: {{ my_file.content }}
   {% else %}
   File is empty or could not be read.
   {% endif %}

Troubleshooting Directory Variables
-----------------------------------

**Problem: Template variable changes between runs**

This happens when using auto-naming directory routing and the directory name changes:

.. code-block:: bash

   # ❌ Problem: variable name depends on directory name
   ostruct run template.j2 schema.json --dir ci:data ./project_v1/src    # → src variable
   ostruct run template.j2 schema.json --dir ci:data ./project_v2/source # → source variable

**Solution**: Use directory aliases for stable variable names:

.. code-block:: bash

   # ✅ Solution: stable variable name
   ostruct run template.j2 schema.json --dir ci:code ./project_v1/src    # → code variable
   ostruct run template.j2 schema.json --dir ci:code ./project_v2/source # → code variable

**Problem: "UndefinedError" for directory variables**

Common causes:

1. **Directory doesn't exist**: Check the directory path
2. **Directory is empty**: No files to process
3. **Permission issues**: Can't read directory contents

.. code-block:: jinja

   {# Defensive template coding #}
   {% if source_code is defined and source_code %}
   Found {{ source_code | length }} files in source directory
   {% else %}
   No source code files found or directory not accessible
   {% endif %}

**Problem: Template breaks with different project structures**

.. code-block:: jinja

   {# ❌ Brittle template - assumes specific directory names #}
   {% for file in src %}...{% endfor %}
   {% for file in config %}...{% endfor %}

**Solution**: Use aliases and defensive coding:

.. code-block:: jinja

   {# ✅ Robust template - works with any directory structure #}
   {% if source_code is defined %}
   {% for file in source_code %}...{% endfor %}
   {% endif %}

   {% if app_config is defined %}
   {% for file in app_config %}...{% endfor %}
   {% endif %}

**Problem: Need to work with unknown directory structures**

Use aliases and make templates flexible:

.. code-block:: bash

   # Template can work with any project structure
   ostruct run analysis.j2 schema.json --dir ci:code ./any/source/path

.. code-block:: jinja

   {# Template works regardless of actual directory structure #}
   {% if code %}
   # Code Analysis

   {% for file in code %}
   ## {{ file.name }}

   {% if file.extension in ['py', 'js', 'ts'] %}
   Programming file detected: {{ file.content | word_count }} words
   {% elif file.extension in ['md', 'txt'] %}
   Documentation file: {{ file.name }}
   {% else %}
   Other file: {{ file.name }}
   {% endif %}
   {% endfor %}
   {% endif %}

Directory Access Patterns
-------------------------

ostruct provides two approaches for directory routing, each suited to different template use cases:

**Auto-Naming**
~~~~~~~~~~~~~~~

Use auto-naming when your template is designed for a specific directory structure:

.. code-block:: bash

   # Auto-naming syntax
   ostruct run template.j2 schema.json --dir config ./config_files     # → config_files variable
   ostruct run template.j2 schema.json --dir ci:data ./datasets        # → datasets variable
   ostruct run template.j2 schema.json --dir fs:docs ./documentation   # → documentation variable

.. code-block:: jinja

   {# Template must know actual directory names #}
   Configuration files:
   {% for file in config_files %}
   - {{ file.name }}: {{ file.content | truncate(50) }}
   {% endfor %}

   Dataset files:
   {% for file in datasets %}
   - {{ file.name }} ({{ file.size }} bytes)
   {% endfor %}

**Alias Access (Stable Variables)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use aliases when your template needs to work with different directory structures:

.. code-block:: bash

   # Alias syntax for stable variable names
   ostruct run template.j2 schema.json --dir app_config ./settings      # → app_config variable
   ostruct run template.j2 schema.json --dir ci:source_code ./src          # → source_code variable
   ostruct run template.j2 schema.json --dir fs:knowledge_base ./docs      # → knowledge_base variable

.. code-block:: jinja

   {# Template uses stable variable names #}
   Application Configuration:
   {% for file in app_config %}
   - {{ file.name }}: {{ file.content }}
   {% endfor %}

   Source Code Analysis:
   {% for file in source_code %}
   ## {{ file.name }}
   {{ file.content | word_count }} words of code
   {% endfor %}

   Knowledge Base:
   {% for file in knowledge_base %}
   Document: {{ file.name }}
   Summary: {{ file.content | truncate(200) }}
   {% endfor %}

**Best Practices for Directory Routing**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tip::
   **Template Reusability**: Use aliases (``--dir alias``, ``--dir ci:alias``, ``--dir fs:alias``) for templates that need to work across different projects or directory structures.

.. code-block:: jinja

   {# Reusable template that works with any project structure #}
   {% if source_code %}
   # Source Code Analysis

   Total files: {{ source_code | length }}

   {% for file in source_code %}
   ## {{ file.name }}
   - Size: {{ file.size }} bytes
   - Type: {{ file.extension }}
   {% if file.extension in ['py', 'js', 'java'] %}
   - Code content: {{ file.content | word_count }} words
   {% endif %}
   {% endfor %}
   {% endif %}

   {% if app_config %}
   # Configuration Analysis

   {% for file in app_config %}
   Configuration file: {{ file.name }}
   {% if file.extension == 'json' %}
   JSON content detected
   {% elif file.extension in ['yaml', 'yml'] %}
   YAML content detected
   {% endif %}
   {% endfor %}
   {% endif %}

**Directory Structure Flexibility**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The same template works with different project structures when using aliases:

.. code-block:: bash

   # Project A structure
   ostruct run analysis.j2 schema.json --dir ci:code ./src --dir configs ./settings

   # Project B structure
   ostruct run analysis.j2 schema.json --dir ci:code ./source --dir configs ./config

   # Project C structure
   ostruct run analysis.j2 schema.json --dir ci:code ./app --dir configs ./env

**Checking Directory Contents**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: jinja

   {# Check if directory contains files #}
   {% if source_code %}
   Found {{ source_code | length }} source files:
   {% for file in source_code %}
   - {{ file.name }}
   {% endfor %}
   {% else %}
   No source code files found.
   {% endif %}

   {# Filter files by type #}
   {% set python_files = source_code | selectattr('extension', 'equalto', 'py') | list %}
   {% if python_files %}
   Python files ({{ python_files | length }}):
   {% for file in python_files %}
   - {{ file.name }}: {{ file.content | word_count }} lines
   {% endfor %}
   {% endif %}

CLI Variables
=============

String Variables
----------------

Simple string values from the ``-V`` flag:

.. code-block:: bash

   ostruct run template.j2 schema.json -V env=production -V debug=false

.. code-block:: jinja

   Environment: {{ env }}
   Debug mode: {{ debug }}

   {% if env == "production" %}
   Using production settings
   {% endif %}

JSON Variables
--------------

Complex data structures from the ``-J`` flag allow you to pass structured data to templates:

**Basic JSON Objects:**

.. code-block:: bash

   ostruct run template.j2 schema.json -J config='{"database":{"host":"localhost","port":5432},"features":["auth","billing"]}'

.. code-block:: jinja

   Database configuration:
   - Host: {{ config.database.host }}
   - Port: {{ config.database.port }}

   Enabled features:
   {% for feature in config.features %}
   - {{ feature }}
   {% endfor %}

**Arrays and Lists:**

.. code-block:: bash

   ostruct run template.j2 schema.json -J servers='["web1","web2","db1"]' -J ports='[80,443,3306]'

.. code-block:: jinja

   Server list:
   {% for server in servers %}
   - {{ server }}
   {% endfor %}

   Port configuration:
   {% for port in ports %}
   - Port {{ port }}
   {% endfor %}

**Complex Nested Structures:**

.. code-block:: bash

   ostruct run template.j2 schema.json -J app_config='{
     "environments": {
       "production": {"replicas": 3, "resources": {"cpu": "2", "memory": "4Gi"}},
       "staging": {"replicas": 1, "resources": {"cpu": "1", "memory": "2Gi"}}
     },
     "services": ["api", "worker", "scheduler"],
     "monitoring": {"enabled": true, "alerts": ["cpu", "memory", "disk"]}
   }'

.. code-block:: jinja

   # Application Configuration

   ## Environments
   {% for env_name, env_config in app_config.environments.items() %}
   ### {{ env_name | title }}
   - Replicas: {{ env_config.replicas }}
   - CPU: {{ env_config.resources.cpu }}
   - Memory: {{ env_config.resources.memory }}
   {% endfor %}

   ## Services
   {% for service in app_config.services %}
   - {{ service }}
   {% endfor %}

   ## Monitoring
   {% if app_config.monitoring.enabled %}
   Monitoring enabled with alerts for:
   {% for alert in app_config.monitoring.alerts %}
   - {{ alert }}
   {% endfor %}
   {% endif %}

**Boolean and Null Values:**

.. code-block:: bash

   ostruct run template.j2 schema.json -J settings='{"debug":true,"cache":false,"api_key":null}'

.. code-block:: jinja

   Configuration:
   {% if settings.debug %}
   - Debug mode: ENABLED
   {% else %}
   - Debug mode: DISABLED
   {% endif %}

   {% if settings.cache %}
   - Cache: ENABLED
   {% else %}
   - Cache: DISABLED
   {% endif %}

   {% if settings.api_key %}
   - API Key: {{ settings.api_key }}
   {% else %}
   - API Key: Not configured
   {% endif %}

**Combining JSON with Other Variables:**

.. code-block:: bash

   ostruct run template.j2 schema.json \
     -V environment=production \
     -J thresholds='{"cpu":80,"memory":90,"disk":95}' \
     --file ci:metrics metrics.csv

.. code-block:: jinja

   # {{ environment | title }} Environment Monitoring

   ## Alert Thresholds
   - CPU: {{ thresholds.cpu }}%
   - Memory: {{ thresholds.memory }}%
   - Disk: {{ thresholds.disk }}%

   ## Current Metrics
   {{ metrics.content }}

**JSON Validation and Error Handling:**

.. code-block:: jinja

   {# Check if JSON variable exists and has expected structure #}
   {% if config is defined and config.database is defined %}
   Database: {{ config.database.host }}:{{ config.database.port }}
   {% else %}
   Warning: Database configuration not found
   {% endif %}

   {# Safe access with defaults #}
   {% set db_host = config.database.host if config.database is defined else "localhost" %}
   {% set db_port = config.database.port if config.database is defined else 5432 %}
   Connection: {{ db_host }}:{{ db_port }}

**Common JSON Patterns:**

*Feature flags:*

.. code-block:: bash

   ostruct run template.j2 schema.json -J features='{"new_ui":true,"beta_api":false,"analytics":true}'

.. code-block:: jinja

   {% if features.new_ui %}
   Using new UI components
   {% endif %}

   {% if features.analytics %}
   Analytics tracking enabled
   {% endif %}

*Configuration overrides:*

.. code-block:: bash

   ostruct run template.j2 schema.json -J overrides='{"timeout":30,"retries":3,"batch_size":100}'

.. code-block:: jinja

   Settings:
   - Timeout: {{ overrides.timeout }}s
   - Retry attempts: {{ overrides.retries }}
   - Batch size: {{ overrides.batch_size }}

*User preferences:*

.. code-block:: bash

   ostruct run template.j2 schema.json -J user_prefs='{"theme":"dark","language":"en","notifications":{"email":true,"sms":false}}'

.. code-block:: jinja

   User Settings:
   - Theme: {{ user_prefs.theme }}
   - Language: {{ user_prefs.language }}
   - Email notifications: {{ "enabled" if user_prefs.notifications.email else "disabled" }}
   - SMS notifications: {{ "enabled" if user_prefs.notifications.sms else "disabled" }}

**JSON Processing with Filters:**

.. code-block:: jinja

   {# Convert back to JSON string #}
   Configuration as JSON:
   {{ config | to_json }}

   {# Pretty-printed JSON #}
   Configuration (formatted):
   {{ config | to_json(indent=2) }}

   {# Extract specific fields #}
   {% set db_configs = environments | extract_field('database') %}
   Database configurations:
   {% for db in db_configs %}
   - {{ db.host }}:{{ db.port }}
   {% endfor %}

Control Structures
==================

Conditional Logic
-----------------

.. code-block:: jinja

   {% if env == "production" %}
   **PRODUCTION ENVIRONMENT**
   {% elif env == "staging" %}
   **STAGING ENVIRONMENT**
   {% else %}
   **DEVELOPMENT ENVIRONMENT**
   {% endif %}

   {% if file.size > 1000000 %}
   Warning: Large file detected ({{ file.size | filesizeformat }})
   {% endif %}

Loops and Iteration
-------------------

.. code-block:: jinja

   Processing {{ files | length }} files:
   {% for file in files %}
   {{ loop.index }}. {{ file.name }}
      - Size: {{ file.size }} bytes
      - Modified: {{ file.mtime }}
      {% if file.extension == "py" %}
      - Python file detected
      {% endif %}
   {% endfor %}

**Loop Variables:**

- ``loop.index`` - Current iteration (1-based)
- ``loop.index0`` - Current iteration (0-based)
- ``loop.first`` - True if first iteration
- ``loop.last`` - True if last iteration
- ``loop.length`` - Total number of items

Filtering and Grouping
----------------------

.. code-block:: jinja

   Python files:
   {% for file in files if file.extension == "py" %}
   - {{ file.name }}
   {% endfor %}

   Files by extension:
   {% for ext, group in files | groupby('extension') %}
   {{ ext }} files:
   {% for file in group %}
     - {{ file.name }}
   {% endfor %}
   {% endfor %}

Template Filters
================

Text Processing Filters
-----------------------

**Word and Character Counting:**

.. code-block:: jinja

   Document statistics:
   - Words: {{ content | word_count }}
   - Characters: {{ content | char_count }}

**Text Cleaning and Formatting:**

.. code-block:: jinja

   Clean code (comments removed):
   {{ source_code | remove_comments }}

   Normalized text:
   {{ messy_text | normalize }}

   Wrapped text:
   {{ long_text | wrap(width=80) }}

**Content Extraction:**

.. code-block:: jinja

   Key points:
   {% for keyword in text | extract_keywords %}
   - {{ keyword }}
   {% endfor %}

Data Processing Filters
-----------------------

**JSON Handling:**

.. code-block:: jinja

   Configuration as JSON:
   {{ config | to_json }}

   Parsed data:
   {% set data = json_string | from_json %}
   {{ data.key }}

**List Processing:**

.. code-block:: jinja

   Sorted files:
   {% for file in files | sort_by('name') %}
   - {{ file.name }}
   {% endfor %}

   Unique extensions:
   {% for ext in files | extract_field('extension') | unique %}
   - {{ ext }}
   {% endfor %}

**Statistical Analysis:**

.. code-block:: jinja

   File size statistics:
   {% set stats = files | extract_field('size') | aggregate %}
   - Total files: {{ stats.count }}
   - Average size: {{ stats.avg }}
   - Largest: {{ stats.max }}
   - Smallest: {{ stats.min }}

**Single Item Extraction:**

The ``|single`` filter extracts exactly one item from a list, with error handling:

.. code-block:: jinja

   <!-- Extract single file when expecting exactly one -->
   {{ (my_files|single).name }}        <!-- Returns the name of the single file -->
   {{ (my_files|single).content }}     <!-- Returns the content of the single file -->

   <!-- Works with any list type -->
   {{ single_item_list|single }}     <!-- Returns the single item -->

   <!-- Error handling for invalid cases -->
   {{ empty_list|single }}           <!-- TemplateRuntimeError: expected 1 item, got 0 -->
   {{ multi_files|single }}          <!-- TemplateRuntimeError: expected 1 item, got 3 -->

**Use Cases:**

- **File Processing**: When you expect exactly one file but receive multiple files
- **Data Validation**: Ensure lists contain exactly one item before processing
- **API Consistency**: Convert adaptive properties to single values explicitly

.. code-block:: jinja

   <!-- Validate single file upload -->
   {% if uploaded_files|length == 1 %}
   Processing file: {{ (uploaded_files|single).name }}
   Content: {{ (uploaded_files|single).content }}
   {% else %}
   Error: Expected exactly one file, got {{ uploaded_files|length }}
   {% endif %}

Code Processing Filters
-----------------------

**Syntax Highlighting:**

.. code-block:: jinja

   Python code with highlighting:
   {{ python_code | format_code('python') }}

   Auto-detected language:
   {{ code | format_code }}

**Comment Handling:**

.. code-block:: jinja

   Code without comments:
   {{ source | strip_comments }}

Table and Data Formatting
-------------------------

**Automatic Table Generation:**

.. code-block:: jinja

   File listing:
   {{ files | auto_table }}

   Custom table:
   {{ data | dict_to_table }}

Global Functions
================

Token Estimation
----------------

Estimate tokens for content planning:

.. code-block:: jinja

   Content size: {{ estimate_tokens(large_text) }} tokens

   {% if estimate_tokens(content) > 4000 %}
   Warning: Content may exceed context limits
   {% endif %}

Utility Functions
-----------------

**Date and Time:**

.. code-block:: jinja

   Generated at: {{ now() }}

**Debugging:**

.. code-block:: jinja

   Debug info: {{ debug(complex_variable) }}
   Variable type: {{ type_of(variable) }}
   Available attributes: {{ dir_of(object) }}

**Validation:**

.. code-block:: jinja

   {% if validate_json(json_string, schema) %}
   JSON is valid
   {% else %}
   JSON validation failed
   {% endif %}

System Prompts and Frontmatter
===============================

YAML Frontmatter
-----------------

Add configuration and system prompts to templates using YAML frontmatter:

.. code-block:: jinja

   ---
   system_prompt: |
     You are an expert software architect with deep knowledge of
     system design patterns and best practices.
   ---
   Analyze this system architecture:

   {{ architecture_doc.content }}

.. note::
   **Model and Temperature Configuration**: Model and temperature must be specified via CLI flags (``--model gpt-4o --temperature 0.3``) as they are not currently supported in YAML frontmatter.

System Prompt Best Practices
-----------------------------

**Clear Role Definition:**

.. code-block:: yaml

   ---
   system_prompt: |
     You are a senior security analyst specializing in application security.
     Focus on identifying potential vulnerabilities and security best practices.
   ---

**Context-Specific Instructions:**

.. code-block:: yaml

   ---
   system_prompt: |
     You are analyzing {{ env }} environment configuration files.
     Pay attention to security settings, resource allocation, and compliance requirements.
     Provide actionable recommendations for {{ env }} deployment.
   ---

**Output Format Guidance:**

.. code-block:: yaml

   ---
   system_prompt: |
     Analyze the provided code and return findings in the exact JSON schema format specified.
     Focus on actionable feedback with specific line numbers and concrete suggestions.
   ---

Shared System Prompts (v0.8.0+)
=================================

The ``include_system:`` feature allows you to share common system prompt content across multiple templates, promoting consistency and reducing duplication in your prompt engineering workflows.

Basic Usage
-----------

Use ``include_system:`` to reference external system prompt files:

.. code-block:: yaml

   ---
   include_system: shared/base_analyst.txt
   system_prompt: |
     For this specific analysis, focus on:
     - Performance optimization opportunities
     - Code maintainability issues
     - Documentation completeness
   ---

**Benefits of Shared System Prompts:**

- **Maintain consistency** across multiple templates with shared expertise
- **Reduce duplication** by centralizing common instructions
- **Enable specialization** by adding template-specific guidance
- **Simplify maintenance** by updating shared prompts in one location
- **Version control** shared prompts independently from templates
- **Team collaboration** through standardized prompt libraries

Advanced Usage Patterns
-----------------------

**Multiple includes** for modular prompt construction:

.. code-block:: yaml

   ---
   include_system: shared/base_expert.txt
   include_system: shared/code_analysis_specialist.txt
   include_system: shared/security_focus.txt
   system_prompt: |
     For this specific task, also consider:
     - Performance implications of suggested changes
     - Backwards compatibility requirements
   ---

**Conditional includes** based on template context:

.. code-block:: jinja

   ---
   {% if analysis_type == "security" %}
   include_system: shared/security_expert.txt
   {% elif analysis_type == "performance" %}
   include_system: shared/performance_expert.txt
   {% else %}
   include_system: shared/general_analyst.txt
   {% endif %}
   system_prompt: |
     Analysis type: {{ analysis_type }}
     Focus on {{ focus_areas | join(", ") }}
   ---

Shared Prompt Library Examples
------------------------------

**Base Expert** (``shared/base_expert.txt``):

.. code-block:: text

   You are an expert software engineer with 15+ years of experience in:
   - Code architecture and design patterns
   - Performance optimization and scalability
   - Security best practices and vulnerability assessment
   - Code quality metrics and maintainability

   Communication style:
   - Always provide specific, actionable recommendations
   - Include code examples when applicable
   - Assess risk levels for identified issues
   - Prioritize suggestions by business impact

**Security Specialist** (``shared/security_expert.txt``):

.. code-block:: text

   You are a cybersecurity expert specializing in:
   - OWASP Top 10 vulnerabilities
   - Secure coding practices
   - Threat modeling and risk assessment
   - Compliance frameworks (SOC2, PCI DSS, GDPR)

   For security analysis, always:
   1. Identify potential attack vectors
   2. Assess severity using CVSS scoring
   3. Provide specific remediation steps
   4. Consider defense-in-depth strategies

**Data Science Expert** (``shared/data_scientist.txt``):

.. code-block:: text

   You are a senior data scientist with expertise in:
   - Statistical analysis and hypothesis testing
   - Machine learning algorithm selection
   - Data quality assessment and cleaning
   - Visualization best practices

   Always approach analysis with:
   - Statistical rigor and appropriate confidence intervals
   - Clear assumptions and limitations
   - Actionable insights for business stakeholders
   - Reproducible methodology

Organizational Patterns
-----------------------

**Hierarchical organization** for large teams:

.. code-block:: text

   prompts/
   ├── shared/
   │   ├── base/
   │   │   ├── expert.txt                 # Foundation expert persona
   │   │   ├── analyst.txt                # Basic analyst role
   │   │   └── communicator.txt           # Communication guidelines
   │   ├── domain/
   │   │   ├── security_expert.txt        # Security specialization
   │   │   ├── performance_expert.txt     # Performance specialization
   │   │   ├── data_scientist.txt         # Data science expertise
   │   │   └── devops_engineer.txt        # DevOps specialization
   │   └── project/
   │       ├── project_alpha_context.txt  # Project-specific context
   │       └── compliance_requirements.txt # Regulatory context
   └── templates/
       ├── security/
       │   ├── code_review.j2             # Uses security_expert.txt
       │   └── vulnerability_scan.j2      # Uses security_expert.txt
       └── analysis/
           ├── performance_analysis.j2    # Uses performance_expert.txt
           └── data_exploration.j2        # Uses data_scientist.txt

**Team-specific includes:**

.. code-block:: yaml

   ---
   # Frontend team template
   include_system: shared/base/expert.txt
   include_system: shared/domain/frontend_specialist.txt
   include_system: shared/project/ui_guidelines.txt
   system_prompt: |
     Review this React component for:
     - Accessibility compliance (WCAG 2.1)
     - Performance optimization opportunities
     - Code maintainability and testing
   ---

Path Resolution Rules
---------------------

The ``include_system:`` path is resolved using these rules:

1. **Relative to template location** (primary):

   .. code-block:: text

      templates/analysis/review.j2
      include_system: ../shared/expert.txt
      # Resolves to: templates/shared/expert.txt

2. **Relative to current working directory**:

   .. code-block:: text

      # If running from project root
      include_system: prompts/shared/expert.txt

3. **Absolute paths** (when needed):

   .. code-block:: text

      include_system: /path/to/shared/prompts/expert.txt

**Best practice:** Use relative paths from template directory for portability.

Template Composition Example
----------------------------

**Template using shared prompts:**

.. code-block:: jinja

   ---
   include_system: ../shared/security_expert.txt
   include_system: ../shared/code_reviewer.txt
   system_prompt: |
     Focus specifically on these security concerns:
     - Input validation and sanitization
     - Authentication and authorization flaws
     - SQL injection and XSS vulnerabilities

     Analyze for {{ threat_model }} threat model.
   ---

   # Security Code Review

   ## Analysis Target
   {% if files %}
   {% for file in files %}
   **{{ file.name }}** ({{ file.size }} bytes):
   ```{{ file.extension }}
   {{ file.content }}
   ```
   {% endfor %}
   {% endif %}

   ## Security Requirements
   - Threat model: {{ threat_model }}
   - Compliance: {{ compliance_standards | join(", ") }}
   - Risk tolerance: {{ risk_tolerance }}

Error Handling and Debugging
----------------------------

**Common issues and solutions:**

.. code-block:: bash

   # Debug include resolution
   ostruct run template.j2 schema.json --dry-run --verbose

**Error: include_system file not found**

.. code-block:: text

   Error: Could not find include_system file: shared/expert.txt
   Template: /path/to/templates/analysis.j2
   Search paths:
   - /path/to/templates/shared/expert.txt (relative to template)
   - /path/to/shared/expert.txt (relative to cwd)

**Solution:** Check file paths and ensure shared prompt files exist.

**Error: circular include detected**

.. code-block:: text

   Error: Circular include detected in shared/base.txt
   Include chain: base.txt → expert.txt → base.txt

**Solution:** Restructure shared prompts to avoid circular dependencies.

Migration and Best Practices
----------------------------

**Migrating from inline system prompts:**

.. code-block:: jinja

   {# Before - inline duplication #}
   ---
   system_prompt: |
     You are an expert software engineer...
     [repeated across multiple templates]
   ---

   {# After - shared expertise #}
   ---
   include_system: shared/software_expert.txt
   system_prompt: |
     For this specific analysis...
     [template-specific instructions only]
   ---

**Best practices:**

1. **Start with base personas** - Create fundamental expert roles first
2. **Add domain specializations** - Build specific expertise on top of base
3. **Use version control** - Track changes to shared prompts carefully
4. **Document prompt libraries** - Maintain clear documentation of available includes
5. **Test includes together** - Verify combined prompts work well
6. **Keep includes focused** - Each file should have a single, clear purpose

.. note::
   Both ``include_system:`` content and ``system_prompt:`` content are combined,
   with the included content appearing first, followed by the template-specific system prompt.

Advanced Template Patterns
===========================

Multi-File Analysis Template
----------------------------

.. code-block:: jinja

   ---
   system_prompt: You are a code review expert analyzing a multi-file codebase.
   ---
   # Code Review Analysis

   ## Files Analyzed
   {% for file in source_files %}
   - **{{ file.name }}** ({{ file.size }} bytes, {{ file.content | word_count }} words)
   {% endfor %}

   ## Security Concerns
   {% for file in source_files if 'password' in file.content.lower() or 'secret' in file.content.lower() %}
   ⚠️ **{{ file.name }}**: Potential credential exposure detected
   {% endfor %}

   ## Code Quality Metrics
   {% set total_lines = source_files | sum(attribute='content') | word_count %}
   - Total lines across all files: {{ total_lines }}
   - Average file size: {{ (source_files | extract_field('size') | sum) // (source_files | length) }} bytes

   ## Detailed Analysis
   {% for file in source_files %}
   ### {{ file.name }}
   ```{{ file.extension }}
   {{ file.content }}
   ```
   {% endfor %}

Configuration Comparison Template
---------------------------------

.. code-block:: jinja

   ---
   system_prompt: You are a DevOps engineer comparing environment configurations.
   ---
   # Configuration Comparison: {{ env1 }} vs {{ env2 }}

   ## {{ env1 | title }} Configuration
   ```yaml
   {{ config1.content }}
   ```

   ## {{ env2 | title }} Configuration
   ```yaml
   {{ config2.content }}
   ```

   ## Analysis Request
   Compare these configurations and identify:
   1. **Security differences** - Authentication, encryption, access controls
   2. **Resource allocation** - CPU, memory, storage differences
   3. **Feature flags** - Enabled/disabled features
   4. **Environment-specific settings** - URLs, database connections
   5. **Potential issues** - Misconfigurations or inconsistencies

Data Analysis Template
----------------------

.. code-block:: jinja

   ---
   system_prompt: You are a data scientist analyzing business metrics.
   ---
   # Data Analysis Report

   ## Dataset Overview
   {% for dataset in datasets %}
   **{{ dataset.name }}**:
   - Size: {{ dataset.content | char_count }} characters
   - Estimated records: {{ dataset.content | word_count // 10 }}
   {% endfor %}

   ## Analysis Parameters
   - Analysis type: {{ analysis_type }}
   - Date range: {{ date_range }}
   - Metrics focus: {{ metrics.join(', ') }}

   ## Raw Data
   {% for dataset in datasets %}
   ### {{ dataset.name }}
   ```
   {{ dataset.content }}
   ```
   {% endfor %}

   Please analyze this data focusing on trends, anomalies, and business insights.

Tool Integration Variables
==========================

Code Interpreter Context
------------------------

When files are routed to Code Interpreter (``--file ci:``), additional context is available:

.. code-block:: jinja

   Data files available for analysis:
   {% for file in code_interpreter_files %}
   - {{ file.name }} (uploaded for Python analysis)
   {% endfor %}

   Please analyze the uploaded data and generate visualizations showing:
   1. Key trends over time
   2. Distribution patterns
   3. Correlation analysis

File Search Context
-------------------

When files are routed to File Search (``--file fs:``), they're available for semantic search:

.. code-block:: jinja

   Knowledge base documents:
   {% for file in search_files %}
   - {{ file.name }} (available for semantic search)
   {% endfor %}

   Use the uploaded documents to answer questions about {{ topic }}.
   Provide specific references to source documents in your responses.

Web Search Context
------------------

When web search is enabled (``--enable-tool web-search``), the ``web_search_enabled`` variable is available:

.. code-block:: jinja

   {% if web_search_enabled %}
   {# Note to AI: Web search is available. Please use it for current information. #}
   Research the latest developments in {{ topic }} using web search.
   Focus on information from the last 30 days and cite all sources in the 'sources' field.
   {% else %}
   {# Note to AI: Web search not available. Use training data. #}
   Analyze {{ topic }} based on available training data.
   Note any limitations due to knowledge cutoff date.
   {% endif %}

**Best practices for web search templates:**

.. code-block:: jinja

   ---
   system_prompt: You are a research analyst with access to current information.
   ---

   {% if web_search_enabled %}
   Please research {{ research_topic }} using web search to find:
   - Recent developments (last 30 days)
   - Current market trends
   - Expert opinions and analysis

   **Important**: Cite all sources in the 'sources' field. Do not use inline citations like [1], [2].
   {% else %}
   Please analyze {{ research_topic }} based on your training data.
   Note: This analysis is based on information available up to your knowledge cutoff.
   {% endif %}

   Focus areas:
   1. Current status and recent changes
   2. Key trends and patterns
   3. Future outlook and predictions

Template Organization and Reuse
===============================

Template Libraries
------------------

Organize templates by use case:

.. code-block:: text

   templates/
   ├── analysis/
   │   ├── code_review.j2
   │   ├── security_scan.j2
   │   └── performance_analysis.j2
   ├── reporting/
   │   ├── daily_summary.j2
   │   └── incident_report.j2
   └── configuration/
       ├── env_comparison.j2
       └── deployment_check.j2

Reusable Template Snippets
--------------------------

Create modular template components:

**File listing snippet:**

.. code-block:: jinja

   {# files_table.j2 #}
   {% macro file_table(files) %}
   | File | Size | Modified |
   |------|------|----------|
   {% for file in files %}
   | {{ file.name }} | {{ file.size }} | {{ file.mtime }} |
   {% endfor %}
   {% endmacro %}

**Security check snippet:**

.. code-block:: jinja

   {# security_checks.j2 #}
   {% macro security_scan(content) %}
   {% set issues = [] %}
   {% if 'password' in content.lower() %}{% set _ = issues.append('Hardcoded passwords detected') %}{% endif %}
   {% if 'api_key' in content.lower() %}{% set _ = issues.append('API keys in code') %}{% endif %}
   {% if issues %}
   ⚠️ Security Issues:
   {% for issue in issues %}
   - {{ issue }}
   {% endfor %}
   {% endif %}
   {% endmacro %}

Template Testing and Debugging
===============================

Dry Run Testing
---------------

Test templates without API calls:

.. code-block:: bash

   # Test template rendering
   ostruct run template.j2 schema.json --dry-run --file config config.yaml

   # Verbose output for debugging
   ostruct run template.j2 schema.json --dry-run --verbose --file config data.csv

Debug Variables
---------------

Use debug functions in templates:

.. code-block:: jinja

   {# Debug variable contents #}
   Debug info: {{ debug(config) }}

   {# Check variable types #}
   Type of data: {{ type_of(data) }}

   {# List available attributes #}
   Available methods: {{ dir_of(file_object) }}

Common Template Issues
----------------------

**Variable naming conflicts:**

.. code-block:: jinja

   {# Wrong - conflicts with built-in #}
   {{ list.content }}

   {# Right - descriptive names #}
   {{ file_list.content }}

**Missing file checks:**

.. code-block:: jinja

   {# Wrong - may fail if file missing #}
   {{ config.content }}

   {# Right - defensive programming #}
   {% if config and config.exists %}
   {{ config.content }}
   {% else %}
   No configuration file found
   {% endif %}

**Inefficient loops:**

.. code-block:: jinja

   {# Inefficient - nested processing #}
   {% for file in files %}
   {% for line in file.content.split('\n') %}
   Process line: {{ line }}
   {% endfor %}
   {% endfor %}

   {# Better - use filters #}
   {% for file in files %}
   Lines: {{ file.content | word_count }}
   {% endfor %}

Best Practices
==============

Template Design
---------------

1. **Clear structure** - Use consistent formatting and organization
2. **Defensive coding** - Check for variable existence before use
3. **Meaningful names** - Use descriptive variable names
4. **Modular design** - Break complex templates into reusable components
5. **Documentation** - Comment complex logic and requirements

Performance Optimization
------------------------

1. **Filter efficiently** - Use filters instead of loops when possible
2. **Cache expensive operations** - Store results in variables
3. **Limit content size** - Use ``truncate`` for large files
4. **Smart iteration** - Filter before iterating over large collections

Security Considerations
-----------------------

1. **Sanitize inputs** - Use ``escape`` filter for user content
2. **Validate data** - Check file existence and formats
3. **Limit exposure** - Don't include sensitive data in templates
4. **Review outputs** - Ensure templates don't leak credentials

Error Handling
--------------

.. code-block:: jinja

   {# Graceful error handling #}
   {% if files %}
   {% for file in files %}
   {% if file.exists %}
   {{ file.content }}
   {% else %}
   File not found: {{ file.path }}
   {% endif %}
   {% endfor %}
   {% else %}
   No files provided for analysis
   {% endif %}



Next Steps
==========

- :doc:`quickstart` - Learn with hands-on examples
- :doc:`cli_reference` - Complete CLI option reference
- :doc:`../security/overview` - Security considerations for templates
- `Jinja2 Documentation <https://jinja.palletsprojects.com/>`_ - Advanced Jinja2 features
