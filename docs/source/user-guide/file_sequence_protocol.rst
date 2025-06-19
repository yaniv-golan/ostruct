Working with Files in Templates
=================================

When writing templates, you'll often need to work with files that users attach via the command line. These files might be single files (``--file code main.py``) or collections of files (``--dir code ./src/``). This guide shows you how to write templates that work seamlessly with both.

The Problem: Single Files vs. Collections
------------------------------------------

Without proper handling, you'd need different template code for single files versus multiple files:

.. code-block:: jinja

   {# This doesn't work - some attachments are single files, others are collections #}
   {% for file in code %}  {# Fails if code is a single file #}
     ## {{ file.path }}
   {% endfor %}

   {{ code.content }}      {# Fails if code is multiple files #}

The Solution: Uniform File Handling
------------------------------------

Ostruct makes all file variables work the same way - you can always iterate over them, whether they contain one file or many:

.. code-block:: jinja

   {# This works for both single files and collections #}
   {% for file in code %}
     ## {{ file.path }}
     {{ file.content }}
   {% endfor %}

Whether the user runs:
- ``ostruct run template.j2 schema.json --file code main.py`` (single file)
- ``ostruct run template.j2 schema.json --dir code ./src/`` (multiple files)

Your template code remains the same!

Common Template Patterns
------------------------

Always Use Loops
~~~~~~~~~~~~~~~~

The safest approach is to always loop over file variables:

.. code-block:: jinja

   # Code Review Report

   {% for file in code %}
   ## {{ file.path }}

   **Size:** {{ file.size }} bytes
   **Language:** {{ file.extension }}

   ```{{ file.extension }}
   {{ file.content }}
   ```

   {% endfor %}

This template works whether ``code`` contains one file or fifty files.

Accessing the Primary File
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes you need just the first/main file from a collection:

.. code-block:: jinja

   # Main file analysis
   Primary file: {{ code.first.path }}

   {% if code.is_collection %}
   This is part of a {{ code|length }} file collection.
   {% else %}
   This is a single file.
   {% endif %}

The ``.first`` property gives you the primary file from any file variable.

Direct Access (Single Files Only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you know a variable will always be a single file, you can access properties directly:

.. code-block:: jinja

   {# Only works if 'report' is guaranteed to be a single file #}
   # {{ report.path }}

   {{ report.content }}

**Warning:** This will fail if the user provides multiple files. Use ``.first`` or loops for safer templates.

Checking File Types
~~~~~~~~~~~~~~~~~~~~

Use the ``fileish`` test to check if a variable contains files:

.. code-block:: jinja

   {% if data is fileish %}
   {# Process as files #}
   {% for file in data %}
   Processing: {{ file.name }}
   {% endfor %}
   {% else %}
   {# Handle as regular data #}
   Data value: {{ data }}
   {% endif %}

Helper Filters
---------------

files Filter
~~~~~~~~~~~~

The ``|files`` filter ensures any value can be looped over, but is **unnecessary for ostruct file variables**:

.. code-block:: jinja

   {# File variables work directly - no filter needed #}
   {% for file in my_files %}
     {{ file.name }}
   {% endfor %}

   {# |files filter only useful for non-file variables #}
   {% for item in uncertain_non_file_variable|files %}
     {{ item }}
   {% endfor %}

**You should almost never need the** ``|files`` **filter** when working with ostruct file variables, since they are already designed to work uniformly in loops.

.. note::
   The ``|files`` filter exists as a safety net for edge cases with non-file variables that might not be iterable. However, ostruct's file variables already work correctly in loops without any special handling, making this filter redundant for normal template authoring.

Command Line Examples
---------------------

Your templates work the same way regardless of how users attach files:

Single File Commands
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # User provides one file
   ostruct run template.j2 schema.json --file code main.py
   ostruct run template.j2 schema.json --file code data.csv
   ostruct run template.j2 schema.json --file code README.md

Multiple File Commands
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # User provides multiple files
   ostruct run template.j2 schema.json --dir code ./src/
   ostruct run template.j2 schema.json --dir code ./data/
   ostruct run template.j2 schema.json --dir code ./docs/

Your template code handles both cases automatically.

Real Template Examples
----------------------

Code Review Template
~~~~~~~~~~~~~~~~~~~~

This template works whether the user provides one file or an entire directory:

.. code-block:: jinja

   # Code Review: {{ code.first.path }}

   {% if code.is_collection %}
   Reviewing {{ code|length }} files from {{ code.first.path|dirname }}
   {% else %}
   Reviewing single file: {{ code.first.name }}
   {% endif %}

   {% for file in code %}
   ## {{ file.path }}

   **Size:** {{ file.size }} bytes
   **Type:** {{ file.extension or 'text' }}

   ```{{ file.extension or 'text' }}
   {{ file.content }}
   ```

   {% endfor %}

Documentation Compiler
~~~~~~~~~~~~~~~~~~~~~~

Combines multiple markdown files into a single document:

.. code-block:: jinja

   # {{ docs.first.name|replace('.md', '')|title }} Documentation

   {% for file in docs %}
   {% if file.name.endswith('.md') %}
   {{ file.content }}

   {% if not loop.last %}
   ---
   {% endif %}
   {% endif %}
   {% endfor %}

   *Generated from {{ docs|length }} file(s)*

Common Mistakes to Avoid
------------------------

Don't Use Conditional Logic
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Avoid this pattern:**

.. code-block:: jinja

   {# Don't do this - unnecessary complexity #}
   {% if files is iterable %}
     {% for file in files %}
       {{ file.name }}
     {% endfor %}
   {% else %}
     {{ files.name }}
   {% endif %}

**Use this instead:**

.. code-block:: jinja

   {# Simple and works for all cases #}
   {% for file in files %}
     {{ file.name }}
   {% endfor %}

Be Careful with Direct Access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**This can break:**

.. code-block:: jinja

   {# Fails if user provides multiple files #}
   Main file: {{ code.content }}

**Use this instead:**

.. code-block:: jinja

   {# Always works #}
   Main file: {{ code.first.content }}

Quick Reference
---------------

**Always safe patterns:**

.. code-block:: jinja

   {# Loop over any file variable #}
   {% for file in myfiles %}
     {{ file.name }}: {{ file.content }}
   {% endfor %}

   {# Get the primary file #}
   {{ myfiles.first.name }}

   {# Check if it's multiple files #}
   {% if myfiles.is_collection %}
     Processing {{ myfiles|length }} files
   {% endif %}

**Patterns to avoid:**

.. code-block:: jinja

   {# Don't use conditional iteration #}
   {% if myfiles is iterable %}...{% endif %}

   {# Don't access properties directly unless certain it's a single file #}
   {{ myfiles.content }}  {# Use myfiles.first.content instead #}

Summary
-------

The key insight is simple: **always treat file variables as collections, even when they contain just one file**. Use loops for processing and ``.first`` when you need the primary file. This makes your templates work reliably regardless of how users attach files.

See Also
--------

- :doc:`template_authoring` - Complete template authoring guide
- :doc:`../cli/file_attachments` - Command-line file attachment options
