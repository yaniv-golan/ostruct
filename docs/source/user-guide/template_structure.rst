File References
===============

File references provide an **optional** mechanism to reference attached files in templates using ``{{ file_ref("alias") }}`` syntax. When used, files are automatically included in an XML appendix at the end of your prompt.

**This is completely optional** - you can always access files directly in templates using standard Jinja2 syntax if you prefer manual control over formatting and placement.

Quick Start
-----------

1. Attach files via CLI:

   .. code-block:: bash

      ostruct run template.j2 schema.json \
        --dir source-code src/ \
        --file config config.yaml \
        --collect data-files @filelist.txt

2. Reference in template:

   .. code-block:: jinja

      Analyze the source code in {{ file_ref("source-code") }}.
      Check the configuration in {{ file_ref("config") }}.
      Review the data files in {{ file_ref("data-files") }}.

3. Output includes references and XML appendix:

   .. code-block:: text

      Analyze the source code in <source-code>.
      Check the configuration in <config>.
      Review the data files in <data-files>.

      <files>
        <dir alias="source-code" path="src/">
          <file path="main.py">
            <content><![CDATA[...]]></content>
          </file>
        </dir>
        <file alias="config" path="config.yaml">
          <content><![CDATA[...]]></content>
        </file>
        <collection alias="data-files" path="@filelist.txt">
          <file path="data1.csv">
            <content><![CDATA[...]]></content>
          </file>
        </collection>
      </files>

Automatic File References (Optional)
-------------------------------------

.. code-block:: bash

   # Attach files with aliases
   ostruct run template.j2 schema.json \
     --file config config.yaml \
     --dir source src/ \
     --collect data @filelist.txt

.. code-block:: jinja

   {# In your template - automatic XML appendix #}
   Review the configuration in {{ file_ref("config") }}.
   Analyze the source code in {{ file_ref("source") }}.
   Process the data files in {{ file_ref("data") }}.

Manual File Formatting (Alternative)
-------------------------------------

You can access files directly and format them however you prefer:

.. code-block:: jinja

   {# Manual markdown formatting #}
   ## Configuration Analysis

   ```yaml
   {{ config.content }}
   ```

   ## Source Code Files

   {% for file in source %}
   ### {{ file.name }}
   ```{{ file.name.split('.')[-1] }}
   {{ file.content }}
   ```
   {% endfor %}

   ## Data Files Summary

   {% for file in data %}
   - **{{ file.name }}**: {{ file.content | length }} characters
   {% endfor %}

Mixed Approach
--------------

You can combine both approaches in the same template:

.. code-block:: jinja

   {# Manual formatting for main analysis #}
   ## Quick Overview
   The configuration sets debug mode to {{ config.content | from_yaml | attr('debug') }}.

   {# Automatic XML appendix for detailed reference #}
   For complete file contents, see {{ file_ref("config") }} and {{ file_ref("source") }}.

Important: File Placement Strategy
----------------------------------

LLM performance is heavily influenced by the position of information in the prompt. Research confirms that models recall information best when it is placed at the **very beginning (primacy)** or the **very end (recency)** of the context window. Information placed in the middle is more likely to be overlooked (a phenomenon known as the "Lost in the Middle" problem).

Use this principle to guide your choice between manual and automatic file inclusion:

- **For Critical Files:** Manually place your most important file(s) immediately after your primary instructions at the **beginning** of the prompt. This puts them in a high-attention zone.
- **For Reference Material:** Use the automatic ``file_ref()`` appendix for all supporting files. This correctly places them at the **end** of the prompt, another high-attention zone.

**Best Practice Example:**
This template manually includes the critical ``main.py`` at the top for immediate analysis, while relegating logs and configs to the high-attention zone at the end via the XML appendix.

.. code-block:: jinja

   {# Critical file is placed manually at the top #}
   Please review this Python script for performance issues.

   ```python
   {{ source['main.py'].content }}
   ```

   My main concern is the efficiency of the data processing loop.
   Analyze the script above and use the attached logs and configuration for context.

   Supporting files for your analysis: {{ file_ref("logs") }} {{ file_ref("config") }}

How It Works
------------

1. **Template Processing**: Your template is rendered normally
2. **Reference Tracking**: Any ``file_ref()`` calls are tracked
3. **Appendix Generation**: Referenced files are automatically included in an XML appendix

Troubleshooting
---------------

If you encounter issues:

- Check that file aliases match your CLI attachments
- Verify files exist and are accessible

Core Concepts
-------------

- **file_ref() function**: Reference file collections by CLI alias
- **XML appendix**: Structured, machine-readable file organization
- **Alias-based**: Works directly with CLI attachment names
- **Automatic**: Only referenced files appear in appendix

CLI Integration
---------------

File references work seamlessly with existing file attachment options:

- ``--file alias path`` - Single file attachment
- ``--dir alias path`` - Directory attachment
- ``--collect alias @filelist`` - Collection from file list

Template Functions
------------------

file_ref(alias)
~~~~~~~~~~~~~~~

References a file collection by its CLI alias name.

**Parameters:**
- ``alias`` (string): The alias from CLI attachment

**Returns:**
- Reference string that renders as ``<alias>``

**Example:**

.. code-block:: jinja

   {{ file_ref("source-code") }}  → <source-code>

Error Handling
--------------

Ostruct provides clear error messages with suggestions:

.. code-block:: text

   Template Structure Error: Unknown alias 'unknown' in file_ref()
   Suggestions:
     • Available aliases: source-code, config, data-files
     • Check your --dir and --file attachments

Best Practices
--------------

1. Use descriptive alias names
2. Reference only needed files
3. Use template debug for troubleshooting

Examples
--------

Code Review Template
~~~~~~~~~~~~~~~~~~~~

.. code-block:: jinja

   # Code Review Request

   Please review the following code:

   ## Source Code
   Review the implementation in {{ file_ref("source") }}.

   ## Configuration
   Check the settings in {{ file_ref("config") }}.

   ## Tests
   Verify the test coverage in {{ file_ref("tests") }}.

   Focus on:
   - Code quality and maintainability
   - Security considerations
   - Performance implications

Data Analysis Template
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: jinja

   # Data Analysis Request

   Please analyze the following datasets:

   ## Primary Dataset
   Main analysis data: {{ file_ref("main-data") }}

   ## Reference Data
   Supporting information: {{ file_ref("reference-data") }}

   ## Analysis Requirements

   1. **Data Quality Assessment**
      - Check completeness in {{ file_ref("main-data") }}
      - Validate consistency with {{ file_ref("reference-data") }}

   2. **Statistical Analysis**
      - Descriptive statistics for all datasets
      - Correlation analysis between datasets

   3. **Insights and Recommendations**
      - Key findings from the analysis
      - Actionable recommendations

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Unknown alias error:**

.. code-block:: text

   Template Structure Error: Unknown alias 'missing' in file_ref()

- Check that the alias matches your CLI attachment
- Verify spelling and case sensitivity

**File references not working:**

.. code-block:: text

   Template Structure Error: File references not initialized

- Check template processing pipeline
- Ensure files are properly attached via CLI

Debug Mode
~~~~~~~~~~

Use ``--template-debug`` to see file reference operations:

.. code-block:: bash

   ostruct run template.j2 schema.json --dir code src/ --template-debug

Debug output shows:

- Alias registration
- Reference tracking
- Appendix generation
