Examples and Use Cases
======================

This section provides a comprehensive guide to the examples available in the ostruct repository, demonstrating real-world use cases and best practices for different scenarios.

.. note::
   All examples are located in the ``examples/`` directory of the ostruct repository and include complete, runnable code with sample data.

Schema Creation Tool
====================

Before diving into specific examples, we strongly recommend using the **Meta-Schema Generator** to create schemas for your ostruct prompts.

Meta-Schema Generator
---------------------

The meta-schema generator automatically creates and validates JSON schemas for your ostruct prompt templates, ensuring compatibility with OpenAI's Structured Outputs feature.

**Location**: ``examples/meta-schema-generator/``

**Quick Start**:

.. code-block:: bash

   # Generate schema for your template
   cd examples/meta-schema-generator
   ./scripts/generate_and_validate_schema.sh my_template.j2

   # Save to file
   ./scripts/generate_and_validate_schema.sh -o schema.json my_template.j2

**Key Features**:

- **Automated schema generation** from template analysis
- **OpenAI Structured Outputs compliance** checking
- **Iterative refinement** based on validation feedback
- **Best practices enforcement** for schema quality

**When to Use**:

- Creating schemas for new ostruct prompts
- Validating existing schemas for compliance
- Learning proper schema structure through examples

See the `Meta-Schema Generator README <https://github.com/yaniv-golan/ostruct/blob/main/examples/meta-schema-generator/README.md>`_ for detailed usage instructions.

Available Examples
==================

Security Examples
-----------------

**Vulnerability Scanning** (``security/vulnerability-scan/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Three-approach automated security vulnerability scanning with comprehensive testing and cost analysis.

**Features**:
- Static Analysis ($0.18)
- Code Interpreter Analysis ($0.18) - Recommended
- Hybrid Analysis ($0.20) - Comprehensive

**Use Cases**: Security audits, CI/CD integration, code reviews

**Quick Start**:

.. code-block:: bash

   cd examples/security/vulnerability-scan

   # Recommended: Code Interpreter approach
   ostruct run prompts/code_interpreter.j2 schemas/scan_result.json \
     --fca code examples/basic/app.py \
     --sys-file prompts/system.txt

**PII Scanner** (``security/pii-scanner/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GDPR/PII data leak detection for compliance and privacy protection.

**Features**: Personal data detection, GDPR compliance checking, remediation suggestions

**Multi-Repo Scanner** (``security/multi-repo-scan/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Security analysis across multiple repositories and codebases.

**SAST Processor** (``security/sast-processor/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Static Application Security Testing (SAST) results processing and reporting.

Code Quality Examples
---------------------

**Code Review** (``code-quality/code-review/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automated code review with security, style, and performance analysis.

**Features**:
- Multi-file analysis
- Security vulnerability detection
- Code style and best practices checking
- Performance issue identification

**Quick Start**:

.. code-block:: bash

   cd examples/code-quality/code-review
   ostruct run prompts/task.j2 schemas/code_review.json \
     -f code examples/security/sql_injection.py \
     --sys-file prompts/system.txt

**Clone Detection** (``code-quality/clone-detection/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Code clone and duplication detection with refactoring suggestions.

**TODO Extractor** (``code-quality/todo-extractor/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Project-wide TODO, FIXME, and technical debt extraction and tracking.

Testing Examples
----------------

**Test Generator** (``testing/test-generator/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automated test case generation for improved code coverage.

**Failure Analysis** (``testing/failure-analysis/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test failure root cause analysis and debugging assistance.

**API Testing** (``testing/api-testing/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API testing with OpenAPI specification integration.

Infrastructure Examples
-----------------------

**Pipeline Validator** (``infrastructure/pipeline-validator/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CI/CD pipeline validation and optimization recommendations.

**IaC Validator** (``infrastructure/iac-validator/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Infrastructure as Code validation for Terraform, CloudFormation, and other IaC tools.

**License Audit** (``infrastructure/license-audit/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dependency license auditing and compliance checking.

Data Processing Examples
------------------------

**Log Analyzer** (``data-processing/log-analyzer/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Log file analysis for error detection, pattern recognition, and troubleshooting.

**Stream Processor** (``data-processing/stream-processor/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Streaming text analysis for real-time data processing.

**Table Extractor** (``data-processing/table-extractor/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Table data extraction from various formats (CSV, Excel, databases).

**Pipeline Config** (``data-processing/pipeline-config/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Data pipeline configuration validation and optimization.

Schema Validation Examples
--------------------------

**Config Validator** (``config-validation/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

JSON/YAML configuration validation with semantic analysis and cross-environment consistency checking.

**Features**:
- Multi-file configuration validation
- Cross-environment consistency
- Security recommendations
- Intelligent error messages

**Quick Start**:

.. code-block:: bash

   cd examples/config-validation
   ostruct run prompts/task.j2 schemas/validation_result.json \
     -f dev_config examples/basic/dev.yaml \
     -f prod_config examples/basic/prod.yaml

**Proto Validator** (``schema-validation/proto-validator/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Protocol Buffer validation and schema evolution management.

Document Analysis Examples
-----------------------------

**PDF Semantic Diff** (``document-analysis/pdf-semantic-diff/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Advanced PDF comparison with Code Interpreter integration for semantic document analysis.

**Features**:
- PDF document processing
- Change categorization (added, deleted, reworded, changed_in_meaning)
- Semantic analysis with structured output
- Complete validation workflow

**Documentation Example Validator** (``document-analysis/doc-example-validator/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Automated documentation example testing with File Search integration for comprehensive project validation.

**Features**:
- Intelligent example detection in documentation
- Multi-format support (Markdown, RST, plain text)
- AI agent-compatible task list generation
- Large-scale documentation processing
- Project-type aware analysis (CLI, API, Library, Framework)

**Use Cases**: Documentation quality assurance, CI/CD integration, project migration validation, example testing automation

**Quick Start**:

.. code-block:: bash

   cd examples/document-analysis/doc-example-validator

   # Basic documentation analysis
   ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
     -ds test_data/sample_project/ \
     -V project_name="MyProject" \
     -V project_type="CLI"

   # Large-scale project analysis
   ./scripts/large_scale_example.sh

Data Analysis Examples
----------------------

**Multi-Tool Analysis** (``data-analysis/multi-tool-analysis/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive analysis combining Code Interpreter, File Search, and MCP servers.

**Features**:
- Code Interpreter for data analysis
- File Search for documentation
- MCP server integration
- Configuration-driven workflows

Infrastructure Examples (Advanced)
----------------------------------

**CI/CD Automation** (``infrastructure/ci-cd-automation/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CI/CD automation with enhanced ostruct capabilities for automated analysis and reporting.

**Features**:
- GitHub Actions integration
- GitLab CI patterns
- Jenkins workflow automation
- Cost controls and error handling

Optimization Examples
---------------------

**Prompt Optimization** (``optimization/prompt-optimization/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates ostruct's built-in optimization capabilities for better performance and cost efficiency.

**Features**:
- 50-70% token reduction techniques
- Smart template design patterns
- Tool-specific routing optimization
- Before/after comparison examples

Specialized Examples
--------------------

**Etymology Analysis** (``etymology/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Etymological analysis of words with component breakdown and origin identification.

**Features**: Detailed word analysis, component identification, hierarchical relationships

**Web Search** (``web-search/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integration with web search for current information and real-time data gathering.

Debugging Examples
------------------

**Template Debugging** (``debugging/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive debugging examples for template troubleshooting and optimization.

**Features**:
- Template expansion debugging
- Variable troubleshooting
- Optimization analysis
- Common error patterns

**Quick Start**:

.. code-block:: bash

   cd examples/debugging
   # See README.md for specific debugging scenarios

Getting Started with Examples
=============================

Basic Workflow
--------------

1. **Choose an Example**: Select based on your use case from the categories above
2. **Navigate to Directory**: ``cd examples/[category]/[example-name]/``
3. **Read the README**: Each example has comprehensive documentation
4. **Generate Schema** (if needed): Use the meta-schema generator for new templates
5. **Run the Example**: Follow the Quick Start commands in each README

Example Structure
-----------------

Each example follows this consistent structure:

.. code-block:: text

   example-name/
   ├── README.md           # Description, usage, and expected output
   ├── prompts/           # AI prompts
   │   ├── system.txt     # AI's role and expertise
   │   └── task.j2        # Task template
   ├── schemas/           # Output structure
   │   └── result.json    # Schema definition
   └── examples/          # Example inputs
       └── basic/         # Basic examples

Prerequisites
-------------

For all examples, ensure you have:

- Python 3.10 or higher
- ``ostruct-cli`` installed (``pip install ostruct-cli``)
- OpenAI API key set in environment (``OPENAI_API_KEY``)

Example-Specific Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some examples may require additional dependencies:

- **Meta-Schema Generator**: ``jq``, JSON Schema validator (``ajv-cli`` or ``jsonschema``)
- **Code Interpreter Examples**: May upload files to OpenAI
- **File Search Examples**: May create vector stores
- **MCP Examples**: External service connections

Cost Considerations
-------------------

Examples include cost estimates where available:

- **Static Analysis**: ~$0.18 per analysis
- **Code Interpreter**: ~$0.18-$0.27 per analysis
- **File Search**: Additional costs for vector store creation
- **Multi-Tool**: Combined costs of all tools used

Use ``--dry-run`` to estimate costs before running:

.. code-block:: bash

   ostruct run template.j2 schema.json -ft file.txt --dry-run

Contributing Examples
====================

We welcome contributions of new examples! Please follow these guidelines:

1. **Create Complete Examples**: Include all necessary files (schema, templates, sample data)
2. **Follow Structure**: Use the standard example directory structure
3. **Add Documentation**: Include comprehensive README.md with usage examples
4. **Test Thoroughly**: Ensure examples are self-contained and runnable
5. **Include Costs**: Provide cost estimates where possible

See the `Contributing Guide <https://github.com/yaniv-golan/ostruct/blob/main/CONTRIBUTING.md>`_ for detailed instructions.

Next Steps
==========

- :doc:`quickstart` - Get started with basic ostruct usage
- :doc:`template_authoring` - Learn advanced template techniques
- :doc:`cli_reference` - Complete CLI reference
- `GitHub Repository <https://github.com/yaniv-golan/ostruct>`_ - Browse all examples
