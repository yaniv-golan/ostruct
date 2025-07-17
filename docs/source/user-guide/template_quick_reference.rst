Template Quick Reference
========================

This quick reference provides a concise summary of ostruct's most commonly used template features. For comprehensive documentation, see the :doc:`template_guide`.

Template Structure
==================

.. code-block:: jinja

   ---
   system_prompt: You are an expert assistant.
   ---

   # Template content with {{ variables }} and {% logic %}

.. note::
   **Model and Temperature**: Use CLI flags ``--model gpt-4o --temperature 0.7`` instead of frontmatter.

Essential Syntax
================

Variables
---------

.. code-block:: jinja

   {{ variable_name }}              <!-- Output variable -->
   {{ file.content }}               <!-- File content (REQUIRED .content) -->
   {{ config.database.host }}      <!-- Nested object access -->
   {{ items | length }}             <!-- Apply filter -->

Control Flow
------------

.. code-block:: jinja

   {% if condition %}...{% endif %}
   {% if var is defined %}...{% endif %}
   {% for item in items %}...{% endfor %}
   {% for file in files if file.extension == "py" %}...{% endfor %}

Comments
--------

.. code-block:: jinja

   {# This is a comment #}

File Variables
==============

File Routing Flags
------------------

.. list-table:: File Routing Quick Reference
   :header-rows: 1
   :widths: 20 30 50

   * - Flag
     - Purpose
     - Template Variable
   * - ``--file alias``
     - Template access only
     - ``alias`` variable
   * - ``--file ci:data``
     - Code Interpreter upload
     - ``data`` variable with analysis context
   * - ``--file fs:docs``
     - File Search upload
     - ``docs`` variable with search context

File Aliases
------------

Choose meaningful aliases for your files:

.. code-block:: bash

   --file config config.yaml                    # → config
   --file app_config config.yaml               # → app_config

File Content Access
-------------------

.. code-block:: jinja

   ✅ {{ my_file.content }}           <!-- Correct -->
   ❌ {{ my_file }}                   <!-- Wrong - shows guidance message -->

File Properties
---------------

.. code-block:: jinja

   {{ file.name }}          <!-- filename.txt -->
   {{ file.path }}          <!-- relative/path/filename.txt -->
   {{ file.abs_path }}      <!-- /full/path/filename.txt -->
   {{ file.size }}          <!-- 1024 (bytes) -->
   {{ file.extension }}     <!-- txt -->
   {{ file.suffix }}        <!-- .txt -->
   {{ file.stem }}          <!-- filename without extension -->
   {{ file.mtime }}         <!-- modification time (Unix timestamp) -->
   {{ file.first }}         <!-- first file (itself for single files) -->
   {{ file.is_collection }} <!-- false for single files -->

Boolean Properties
------------------

.. code-block:: jinja

   {% if file.exists %}     <!-- file exists -->
   {% if file.is_file %}    <!-- is regular file -->
   {% if file.is_url %}     <!-- is remote URL -->

Multiple Files
--------------

.. code-block:: jinja

   {% for file in source_files %}
   ## {{ file.name }}
   {{ file.content }}
   {% endfor %}

Tool Variables
==============

.. code-block:: jinja

   {% if code_interpreter_enabled %}
   {% if file_search_enabled %}
   {% if web_search_enabled %}
   {% if auto_download_enabled %}

   {{ current_model }}              <!-- gpt-4o -->
   {{ code_interpreter_config }}    <!-- CI configuration object -->

.. note:: Advanced only

   ``auto_download_enabled`` and ``code_interpreter_config`` are useful when you
   write *meta*-templates that must adapt to different Code-Interpreter settings.
   Most templates can ignore them.

Standard Input
==============

.. code-block:: jinja

   {% if stdin %}{{ stdin }}{% endif %}

CLI Variables
=============

String Variables
----------------

.. code-block:: bash

   ostruct run template.j2 schema.json -V env=production -V debug=false

.. code-block:: jinja

   Environment: {{ env }}
   Debug: {{ debug }}

JSON Variables
--------------

.. code-block:: bash

   ostruct run template.j2 schema.json -J config='{"host": "localhost", "port": 5432}'

.. code-block:: jinja

   Host: {{ config.host }}
   Port: {{ config.port }}

Essential Filters
=================

Text Processing
---------------

.. code-block:: jinja

   {{ text | word_count }}             <!-- Count words -->
   {{ text | char_count }}             <!-- Count characters -->
   {{ text | length }}                 <!-- Count characters (built-in) -->
   {{ text | upper }}                  <!-- UPPERCASE -->
   {{ text | lower }}                  <!-- lowercase -->
   {{ long_text | truncate(100) }}     <!-- Truncate to 100 chars -->

Data Processing
---------------

.. code-block:: jinja

   {{ items | length }}                <!-- Count items -->
   {{ items | sort_by("name") }}       <!-- Sort by property -->
   {{ items | unique }}                <!-- Remove duplicates -->
   {{ users | extract_field("email") }} <!-- Extract field -->

JSON Operations
---------------

.. code-block:: jinja

   {{ data | to_json }}                <!-- Convert to JSON -->
   {{ json_string | from_json }}       <!-- Parse JSON -->

Table Formatting
----------------

.. code-block:: jinja

   {{ dictionary | dict_to_table }}    <!-- Dict to markdown table -->
   {{ list_data | list_to_table }}     <!-- List to markdown table -->

Code Processing
---------------

.. code-block:: jinja

   {{ code | format_code("python") }}  <!-- Syntax highlighting -->
   {{ code | strip_comments("python") }} <!-- Remove comments -->

Common Patterns
===============

Conditional Content
-------------------

.. code-block:: jinja

   {% if config_file is defined %}
   Configuration: {{ config_file.content }}
   {% else %}
   No configuration provided.
   {% endif %}

File Processing
---------------

.. code-block:: jinja

   {% for file in source_files %}
   ### {{ file.path }}

   **Size**: {{ file.size }} bytes
   **Type**: {{ file.extension }}

   ```{{ file.extension }}
   {{ file.content }}
   ```
   {% endfor %}

Data Analysis
-------------

.. code-block:: jinja

   {% set stats = data | aggregate %}
   Total: {{ stats.sum }}
   Average: {{ stats.avg }}
   Count: {{ stats.count }}

Error Handling
--------------

.. code-block:: jinja

   {% if files and files | length > 0 %}
   Processing {{ files | length }} files...
   {% else %}
   No files to process.
   {% endif %}

Global Functions
================

Utility Functions
-----------------

.. code-block:: jinja

   {{ now() }}                         <!-- Current timestamp -->
   {{ type_of(variable) }}             <!-- Get type name -->
   {{ debug(variable) }}               <!-- Debug output -->

Token Estimation
----------------

.. code-block:: jinja

   Estimated tokens: {{ estimate_tokens(content) }}

Data Analysis
-------------

.. code-block:: jinja

   {% set summary = summarize(data_list) %}
   Records: {{ summary.total_records }}

Common Issues
=============

File Content Access
-------------------

.. code-block:: jinja

   ❌ {{ my_file }}                   <!-- Shows: guidance message -->
   ✅ {{ my_file.content }}           <!-- Shows: actual file content -->

Variable Existence
------------------

.. code-block:: jinja

   {% if optional_var is defined %}
   {{ optional_var }}
   {% endif %}

Safe Defaults
-------------

.. code-block:: jinja

   <!-- Simple variable defaults -->
   {{ config.timeout | default(30) }}
   {{ project_name | default("Unnamed Project") }}

   <!-- Safe nested property access -->
   {{ safe_get("config.database.host", "localhost") }}
   {{ safe_get("user.profile.name", "Anonymous") }}
   {{ safe_get("api.response.data") }}              <!-- Empty string default -->

CLI Examples
============

Basic Usage
-----------

.. code-block:: bash

   # Simple file processing
   ostruct run template.j2 schema.json --file config config.yaml

   # Multiple files with custom names
   ostruct run template.j2 schema.json --file config config.yaml --file data data.csv

   # Directory processing
   ostruct run template.j2 schema.json --dir ci:data source_code/

Multi-Tool Integration
----------------------

.. code-block:: bash

   # Code analysis with execution
   ostruct run analysis.j2 schema.json --file ci:data data.csv --file fs:docs docs.pdf

   # With web search
   ostruct run research.j2 schema.json --enable-tool web-search -V topic="AI trends"

Variables and Configuration
---------------------------

.. code-block:: bash

   # String and JSON variables
   ostruct run template.j2 schema.json \
     -V env=production \
     -J config='{"debug": false, "timeout": 30}'

   # With system prompt
   ostruct run template.j2 schema.json \
     --sys-prompt "You are an expert analyst" \
     --file config data.txt

Debugging
---------

.. code-block:: bash

   # Show available variables
   ostruct run template.j2 schema.json --template-debug vars --file config config.yaml

   # Dry run to test template
   ostruct run template.j2 schema.json --dry-run --file config config.yaml

   # Debug template expansion
   ostruct run template.j2 schema.json --template-debug post-expand --file config config.yaml

.. seealso::

   - :doc:`template_guide` - Complete templating guide
   - :doc:`cli_reference` - Full CLI documentation
   - :doc:`examples` - Practical examples and use cases
