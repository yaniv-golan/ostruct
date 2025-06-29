Introduction to ostruct
=======================

This documentation covers ``ostruct-cli`` version |version|.

What is ostruct?
----------------

``ostruct-cli`` is a command-line tool that transforms unstructured inputs into structured JSON output using OpenAI APIs and Jinja2 templates. It enables AI-powered data processing with validation, security controls, and streaming support.

The tool bridges the gap between unstructured data (text files, documents, code) and structured output (JSON) by leveraging OpenAI's language models with the reliability of JSON Schema validation.

Key Features
------------

- **Schema-First Approach**: Define your output structure using JSON Schema with automatic validation
- **Template-Based Input**: Use Jinja2 templates with support for YAML frontmatter and system prompts
- **Multi-Tool Integration**: Seamless integration with Code Interpreter, File Search, Web Search, and MCP servers
- **File Processing**: Handle single files, multiple files, or entire directories with thread-safe operations
- **Cross-Platform**: Robust support for Windows, macOS, and Linux with consistent path handling
- **Security-Focused**: Safe file access with explicit directory permissions and enhanced error handling
- **Structured Output**: Guaranteed valid JSON output matching your schema
- **Token Management**: Automatic token limit validation and handling
- **Model Support**: Optimized handling for both streaming and non-streaming models

Why ostruct?
------------

Modern development workflows often involve processing unstructured data and extracting meaningful information. Traditional approaches typically require:

1. **Manual parsing** of documents, logs, or code
2. **Custom scripts** for each data format
3. **Inconsistent output** that's hard to integrate
4. **No validation** of extracted data
5. **Security concerns** when processing files

ostruct solves these problems by providing:

**Consistent Structure**
  Every output follows your predefined JSON schema, making integration predictable and reliable.

**AI-Powered Intelligence**
  Leverage OpenAI's advanced language models to understand context, extract insights, and handle complex data.

**Template Flexibility**
  Use Jinja2 templates to customize how your data is processed and presented to the AI model.

**Built-in Security**
  Path validation, symlink resolution, and directory restrictions protect against unauthorized file access.

**Tool Integration**
  Native support for Code Interpreter (data analysis), File Search (document retrieval), Web Search (real-time information), and MCP servers (external services).

**Developer Experience**
  Simple CLI interface with comprehensive options for various use cases, from quick scripts to production pipelines.

Core Concepts
-------------

**Templates**
  Jinja2 templates that define how to present your data to the AI model. They can include system prompts, file content, and variables. Supports shared system prompts via ``include_system:`` for consistency across templates.

**Schemas**
  JSON Schema definitions that specify the exact structure and validation rules for your output.

**File Routing**
  Explicit control over which files go to which tools (template access, code execution, or document search).

**Security Manager**
  Centralized security validation ensuring all file operations are safe and authorized.

**Model Integration**
  Direct integration with OpenAI's structured output API for reliable JSON generation.

Getting Started
---------------

The quickest way to understand ostruct is through a simple example:

1. **Create a schema** (``summary.json``):

   .. code-block:: json

      {
        "type": "object",
        "properties": {
          "summary": {
            "type": "string",
            "description": "Brief summary of the content"
          },
          "key_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Main points or topics"
          }
        },
        "required": ["summary", "key_points"]
      }

   .. tip::
      **Automated Schema Creation**: Use the Schema Generator meta-tool to create schemas automatically:

      .. code-block:: bash

         tools/schema-generator/run.sh -o summary.json summarize.j2

2. **Create a template** (``summarize.j2``):

   .. code-block:: text

      ---
      system_prompt: You are an expert content analyst.
      ---
      Please analyze this document and provide a summary:

      {{ document.content }}

3. **Run the analysis**:

   .. code-block:: bash

      ostruct run summarize.j2 summary.json \
        --file config document.txt \
        -m gpt-4o

The result will be valid JSON matching your schema, ready for further processing or integration.

Next Steps
----------

- :doc:`quickstart` - Follow the step-by-step tutorial
- :doc:`cli_reference` - Explore all CLI options and features
- :doc:`template_guide` - Learn comprehensive template techniques
- :doc:`../security/overview` - Understand security considerations

.. note::
   If you use the standalone binary release, download the `.zip` file for your OS from the release page, extract it, and run the executable from within the extracted folder (e.g., ``ostruct-windows-amd64``, ``ostruct-macos-amd64``, ``ostruct-linux-amd64``). Do not move the executable out of the folder, as it depends on bundled libraries in the same directory.
