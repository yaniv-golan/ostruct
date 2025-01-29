ostruct-cli
===========

``ostruct-cli`` is a command-line tool for generating structured output from OpenAI models. It combines the power of OpenAI's language models with the reliability of JSON Schema validation to ensure consistent, well-structured responses.

Key Features
-----------

- **Schema-First Approach**: Define your output structure using JSON Schema (validation is always performed automatically)
- **Template-Based Input**: Use Jinja2 templates with support for YAML frontmatter and system prompts
- **File Processing**: Handle single files, multiple files, or entire directories
- **Security-Focused**: Safe file access with explicit directory permissions
- **Structured Output**: Guaranteed valid JSON output matching your schema
- **Token Management**: Automatic token limit validation and handling

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

      ---
      system_prompt: You are an expert content analyzer.
      ---
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

Handling Large Files
------------------

When working with large files, the CLI provides several features to help:

1. **Token Validation**: Automatically validates token usage against model limits
2. **Prompt Structure**: Recommends placing content at the end with clear delimiters
3. **Dry Run**: Preview token usage before making API calls (note: `--debug-openai-stream` won't show streaming data during dry runs)
4. **Progress Reporting**: Track processing status for large operations

See the CLI documentation for detailed guidance on handling large files.

Requirements
-----------

- Python 3.9 or higher
- OpenAI API key
- ``openai-structured`` >= 0.9.1

Logging
-------

The CLI writes logs to the following files in ``~/.ostruct/logs/``:

- ``ostruct.log``: General application logs (debug, errors, status)
- ``openai_stream.log``: OpenAI streaming operations logs

Support
-------

- GitHub Issues: https://github.com/yaniv-golan/ostruct/issues
- Documentation: https://ostruct-cli.readthedocs.io/ 