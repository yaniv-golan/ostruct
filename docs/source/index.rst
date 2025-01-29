ostruct-cli
===========

``ostruct-cli`` is a command-line tool for generating structured output from OpenAI models. It combines the power of OpenAI's language models with the reliability of JSON Schema validation to ensure consistent, well-structured responses.

Key Features
-----------

- **Schema-First Approach**: Define your output structure using JSON Schema
- **Template-Based Input**: Use Jinja2 templates for flexible input processing
- **File Processing**: Handle single files, multiple files, or entire directories
- **Security-Focused**: Safe file access with explicit directory permissions
- **Structured Output**: Guaranteed valid JSON output matching your schema

Quick Start
----------

1. Install the package:

   .. code-block:: bash

      pip install ostruct-cli

2. Define your schema (``schema.json``):

   .. code-block:: json

      {
        "type": "object",
        "properties": {
          "summary": {
            "type": "string",
            "description": "Brief summary of the content"
          },
          "topics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Main topics covered"
          }
        },
        "required": ["summary", "topics"]
      }

3. Create a task template (``task.txt``):

   .. code-block:: text

      Analyze this content and extract key information:

      {{ content.content }}

4. Run the analysis:

   .. code-block:: bash

      ostruct \
        --task @task.txt \
        --schema schema.json \
        --file content=input.txt \
        --model gpt-4o-2024-08-06

Documentation
------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   cli
   migration

Why Structured Output?
-------------------

Structured output offers several advantages:

1. **Reliability**: Schema validation ensures responses match your requirements
2. **Consistency**: Get the same structure every time, making responses easier to process
3. **Integration**: JSON output works seamlessly with other tools and systems
4. **Validation**: Catch and handle invalid responses before they reach your application

Requirements
-----------

- Python 3.9 or higher
- OpenAI API key
- ``openai-structured`` >= 0.9.1

Support
-------

- GitHub Issues: https://github.com/yaniv-golan/ostruct/issues
- Documentation: https://ostruct-cli.readthedocs.io/ 