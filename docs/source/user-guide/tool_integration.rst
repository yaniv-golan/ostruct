Multi-Tool Integration
======================

ostruct provides integration with multiple OpenAI tools and services, allowing you to combine different capabilities in a single workflow. This guide covers how to use Code Interpreter, File Search, Web Search, and MCP servers effectively.

Overview
--------

ostruct supports four main tool categories:

- **Code Interpreter**: Execute code, analyze data, generate visualizations
- **File Search**: Semantic search across uploaded documents
- **Web Search**: Access current information from the internet
- **MCP Servers**: Connect to Model Context Protocol servers for custom tools

All tools can be used individually or combined in the same request for comprehensive analysis workflows.

Automatic File Routing
-----------------------

ostruct can automatically route files to appropriate tools based on file type detection:

**Auto-routing Target**: Use ``--file auto:alias file.txt`` to let ostruct decide:

- **Text files** → Template access (``prompt``)
- **Binary files** → User-data for vision models (``ud``)

**File Type Detection**:

- **Enhanced detection**: Uses machine learning (Magika) for accurate file type identification
- **Extension fallback**: Recognizes 30+ common file extensions (.txt, .md, .json, .py, .csv, etc.)
- **Installation**: ``pip install ostruct-cli[enhanced-detection]`` for enhanced detection

**Example**:

.. code-block:: bash

   # Auto-route based on file type
   ostruct run analysis.j2 schema.json \
     --file auto:doc1 report.pdf \      # → user-data (binary)
     --file auto:doc2 summary.txt \     # → prompt (text)
     --file auto:doc3 data.json         # → prompt (text)

Shared File Usage
-----------------

One of ostruct's most powerful features is the ability to provide the same file to multiple tools simultaneously. This enables comprehensive analysis workflows where a single file can be:

- Programmatically analyzed with Code Interpreter
- Semantically searched with File Search
- Referenced in templates for context

**Multi-Tool File Syntax:**

.. code-block:: bash

   # Same file available to both Code Interpreter and File Search
   ostruct run analysis.j2 schema.json --file ci,fs:data report.csv

   # Multiple files with different tool combinations
   ostruct run analysis.j2 schema.json \
     --file ci,fs:financial quarterly_report.pdf \
     --file ci:sales sales_data.csv \
     --file fs:policies company_handbook.pdf

**Common Use Cases:**

- **Research Documents**: Upload papers that need both statistical analysis and semantic search
- **Financial Reports**: Analyze numbers programmatically while searching for contextual information
- **Technical Documentation**: Process code examples while maintaining searchable knowledge base
- **Mixed Data Sets**: Combine structured data analysis with unstructured document search

This shared approach eliminates file duplication and ensures consistency across different analysis methods.

Code Interpreter
================

Code Interpreter allows the AI model to execute Python code, analyze data, create visualizations, and work with files programmatically.

How It Works
------------

1. Files uploaded with ``--file ci:`` are made available in the execution environment
2. The model can write and execute Python code to analyze your data
3. Generated files (charts, reports, processed data) are automatically downloaded
4. Results and insights are included in the structured output

.. note::
   **💡 Multi-Tool Tip**: Use ``--file ci,fs:alias file.csv`` to make the same file available for both programmatic analysis and semantic search. This is especially useful for research data, financial reports, and technical documentation that benefit from multiple analysis approaches.

CLI Options
-----------

**File Upload:**

.. code-block:: bash

   # Upload single file for code execution
   ostruct run analysis.j2 schema.json --file ci:data sales_data.csv

   # Upload multiple files
   ostruct run analysis.j2 schema.json \
     --file ci:sales sales_data.csv \
     --file ci:customers customer_data.csv

   # Upload directory of files
   ostruct run analysis.j2 schema.json --dir ci:project_data ./data/

**Configuration Options:**

- ``--ci-cleanup``: Clean up uploaded files after execution (default: True)
- ``--ci-download-dir DIR``: Directory to save generated files (default: ./downloads/)
- ``--ci-duplicate-outputs {overwrite|rename|skip}``: Handle duplicate file names

Best Practices
--------------

1. **Data Preparation**: Upload clean, well-structured data files
2. **Clear Instructions**: Specify exactly what analysis or processing you need
3. **File Organization**: Use descriptive aliases for uploaded files
4. **Output Management**: Organize download directories for different projects

Example Template
----------------

.. code-block:: jinja

   ---
   system_prompt: You are a data analyst expert in Python and visualization.
   ---

   Analyze the uploaded sales data and create visualizations showing:
   1. Monthly sales trends
   2. Top-performing products
   3. Regional performance comparison

   Please:
   - Load and clean the uploaded CSV data
   - Create meaningful visualizations using matplotlib/seaborn
   - Generate a summary report with key insights
   - Save charts as PNG files with descriptive names
   - Provide download links for your sales analysis report

File Search
===========

File Search enables semantic search across uploaded documents, allowing the model to find relevant information from large document collections.

.. warning::
   **Known Issue**: The OpenAI Responses API `file_search` tool currently has a widespread issue where it returns empty results despite successful vector store creation. This affects all models and is an upstream OpenAI API bug. See `known-issues/2025-07-openai-file-search-empty-results.md <../../known-issues/2025-07-openai-file-search-empty-results.md>`_ for detailed information and community reports.

How It Works
------------

1. Documents uploaded with ``--file fs:`` are processed and indexed
2. A vector store is created for semantic search capabilities
3. The model can search for relevant information during response generation
4. Search results are automatically included in the analysis context

.. note::
   **💡 Multi-Tool Tip**: Combine with Code Interpreter using ``--file ci,fs:docs report.pdf`` to both analyze document structure programmatically and search content semantically. Perfect for research papers, financial statements, and technical specifications.

CLI Options
-----------

**Document Upload:**

.. code-block:: bash

   # Upload single document
   ostruct run research.j2 schema.json --file fs:manual user_manual.pdf

   # Upload multiple documents
   ostruct run research.j2 schema.json \
     --file fs:docs documentation.pdf \
     --file fs:specs technical_specs.docx

   # Upload directory of documents
   ostruct run research.j2 schema.json --dir fs:knowledge ./documentation/

**Configuration Options:**

- ``--fs-cleanup``: Clean up uploaded files and vector stores (default: True)
- ``--fs-store-name TEXT``: Name for the vector store (useful for reuse)
- ``--fs-timeout FLOAT``: Timeout for vector store indexing (default: 60.0)
- ``--fs-retries INT``: Number of retry attempts (default: 3)

Best Practices
--------------

1. **Document Quality**: Upload well-formatted, text-rich documents
2. **Relevant Content**: Include only documents relevant to your query
3. **Clear Questions**: Ask specific questions that can be answered from the documents
4. **Vector Store Management**: Use meaningful store names for reusable collections

Example Template
----------------

.. code-block:: jinja

   ---
   system_prompt: You are a technical documentation expert.
   ---

   Based on the uploaded technical documentation, please answer:

   1. What are the system requirements for installation?
   2. How do I configure the authentication settings?
   3. What troubleshooting steps are recommended for common issues?

   Search the documentation for relevant information and provide detailed answers with specific references to the source documents.

Web Search
==========

Web Search provides access to current information from the internet, enabling analysis of up-to-date data and current events.

How It Works
------------

1. Web search is enabled with ``--enable-tool web-search``
2. The model can perform web searches during response generation
3. Search results are automatically incorporated into the analysis
4. Geographically tailored results based on specified location

CLI Options
-----------

**Basic Usage:**

.. code-block:: bash

   # Enable web search
   ostruct run research.j2 schema.json --enable-tool web-search

   # Disable web search (if enabled by default)
   ostruct run analysis.j2 schema.json --disable-tool web-search

**Geographic Customization:**

.. code-block:: bash

   # Specify location for tailored results
   ostruct run research.j2 schema.json \
     --enable-tool web-search \
     --ws-country "United States" \
     --ws-region "California" \
     --ws-city "San Francisco"

**Content Control:**

- ``--ws-context-size [low|medium|high]``: Control amount of content retrieved
- ``--ws-country TEXT``: Specify user country for geographically tailored results
- ``--ws-region TEXT``: Specify user region/state for search results
- ``--ws-city TEXT``: Specify user city for search results

Best Practices
--------------

1. **Specific Queries**: Include specific search terms in your template
2. **Current Information**: Use for time-sensitive or rapidly changing topics
3. **Geographic Relevance**: Set location parameters for location-specific queries
4. **Content Filtering**: Use appropriate context size for your needs

Example Template
----------------

.. code-block:: jinja

   ---
   system_prompt: You are a market research analyst.
   ---

   Research the current state of artificial intelligence in healthcare:

   1. What are the latest AI breakthroughs in medical diagnosis?
   2. Which companies are leading AI healthcare innovation in 2024?
   3. What regulatory challenges are affecting AI adoption in healthcare?

   Please search for recent news, research papers, and industry reports to provide a comprehensive analysis with current information.

MCP Servers
===========

Model Context Protocol (MCP) servers allow you to connect to custom tools and services, extending ostruct's capabilities with specialized functionality.

How It Works
------------

1. Connect to MCP servers using ``--mcp-server`` with server URLs
2. Available tools from connected servers are made accessible to the model
3. Tool usage can be controlled with approval settings and allowed tool lists
4. Custom headers can be provided for authentication

CLI Options
-----------

**Server Connection:**

.. code-block:: bash

   # Connect to MCP server
   ostruct run analysis.j2 schema.json --mcp-server https://api.example.com/mcp

   # Connect with custom label
   ostruct run analysis.j2 schema.json --mcp-server mytools@https://api.example.com/mcp

   # Connect to multiple servers
   ostruct run analysis.j2 schema.json \
     --mcp-server tools@https://api.example.com/mcp \
     --mcp-server data@https://data.example.com/mcp

**Authentication and Headers:**

.. code-block:: bash

   # Provide authentication headers
   ostruct run analysis.j2 schema.json \
     --mcp-server https://api.example.com/mcp \
     --mcp-headers '{"Authorization": "Bearer token123", "X-API-Key": "key456"}'

**Tool Control:**

- ``--mcp-require-approval [always|never]``: Control tool usage approval
- ``--mcp-allowed-tools TEXT``: Specify allowed tools per server

.. note::
   **💡 Multi-Tool Tip**: MCP servers work excellently with shared files. Use ``--file ci,fs:data report.pdf`` to make business documents available for both programmatic analysis and semantic search, while MCP tools access your CRM or analytics systems for additional context.

Best Practices
--------------

1. **Secure Connections**: Use HTTPS for MCP server connections
2. **Authentication**: Properly configure headers for authenticated servers
3. **Tool Approval**: Set appropriate approval levels for tool usage
4. **Error Handling**: Monitor for connection and tool execution errors

Example Template
----------------

.. code-block:: jinja

   ---
   system_prompt: You are a business analyst with access to custom tools.
   ---

   Using the available MCP tools, please:

   1. Retrieve the latest sales data from our CRM system
   2. Generate a quarterly performance report
   3. Create forecasts for the next quarter

   Use the appropriate tools to gather data and perform analysis, then provide a comprehensive business summary.

Multi-Tool Workflows
====================

Combining Tools for Comprehensive Analysis
------------------------------------------

ostruct's multi-tool capabilities shine when you need comprehensive analysis that combines different approaches. The key is using shared files that serve multiple purposes simultaneously.

**Research Analysis Workflow:**

.. code-block:: bash

   # Research paper analysis with shared files
   ostruct run research_analysis.j2 schema.json \
     --file ci,fs:paper research_paper.pdf \
     --file ci,fs:data experiment_data.csv \
     --enable-tool web-search \
     --ws-country "United States"

This command makes the research paper and data available to both Code Interpreter (for statistical analysis and visualization) and File Search (for semantic queries about methodology and findings), while also enabling web search for current context.

**Financial Analysis Workflow:**

.. code-block:: bash

   # Comprehensive financial analysis
   ostruct run financial_analysis.j2 schema.json \
     --file ci,fs:quarterly quarterly_report.pdf \
     --file ci,fs:historical historical_data.csv \
     --file fs:policies investment_policies.pdf \
     --enable-tool web-search \
     --ws-country "United States"

The quarterly report and historical data serve dual purposes: Code Interpreter performs numerical analysis and trend calculations, while File Search enables contextual queries about business strategy and policy compliance.

**Technical Documentation Analysis:**

.. code-block:: bash

   # Code and documentation analysis
   ostruct run tech_analysis.j2 schema.json \
     --file ci,fs:specs technical_specification.pdf \
     --file ci:codebase source_code.zip \
     --file fs:docs user_manual.pdf \
     --mcp-server dev@https://api.company.com/mcp

Technical specs benefit from both programmatic analysis (extracting requirements, parsing formats) and semantic search (finding related concepts and dependencies).

Example Multi-Tool Template
---------------------------

.. code-block:: jinja

   ---
   system_prompt: You are a senior analyst with access to multiple data sources and analysis tools.
   ---

   # Comprehensive Analysis Report

   ## Quantitative Analysis
   Using Code Interpreter, analyze the uploaded data files:
   - Calculate key metrics and statistical summaries
   - Identify trends and patterns in the numerical data
   - Create visualizations showing important relationships
   - Generate charts showing analysis results

   ## Contextual Research
   Search the uploaded documents for:
   - Background information and methodology
   - Historical context and previous findings
   - Policy implications and constraints
   - Related research and citations

   ## Current Market Context
   Research current developments related to our analysis topic:
   - Recent industry trends and changes
   - Competitive landscape updates
   - Regulatory or policy changes
   - Expert opinions and market sentiment

   ## Integrated Findings
   Combine insights from all sources:
   1. **Data-Driven Insights**: Key findings from quantitative analysis
   2. **Contextual Understanding**: Background and historical perspective
   3. **Current Relevance**: How findings relate to current market conditions
   4. **Strategic Implications**: Actionable recommendations based on comprehensive analysis

   ## Supporting Evidence
   Reference specific data points, document sections, and current sources that support each conclusion.

**Shared File Benefits:**

1. **Consistency**: Same source data across all analysis methods
2. **Efficiency**: Single upload serves multiple purposes
3. **Completeness**: Comprehensive analysis without data gaps
4. **Cross-Validation**: Findings can be verified across different approaches

**Tool Combination Strategies:**

.. list-table:: Effective Tool Combinations
   :header-rows: 1
   :widths: 30 35 35

   * - Use Case
     - Tool Combination
     - Shared File Strategy
   * - Research Analysis
     - CI + FS + Web Search
     - ``ci,fs:paper`` for papers, ``ci,fs:data`` for datasets
   * - Financial Reporting
     - CI + FS + MCP
     - ``ci,fs:reports`` for statements, ``fs:policies`` for compliance
   * - Technical Documentation
     - CI + FS + MCP
     - ``ci,fs:specs`` for requirements, ``ci:code`` for implementation
   * - Market Research
     - FS + Web Search + MCP
     - ``fs:reports`` for historical data, web search for current trends
   * - Compliance Analysis
     - CI + FS + Web Search
     - ``ci,fs:data`` for metrics, ``fs:regulations`` for compliance docs

Tool Selection Guidelines
-------------------------

Choose tools based on your analysis needs:

**Code Interpreter** for:
- Data processing and analysis
- Statistical calculations
- Visualization creation
- File format conversions

**File Search** for:
- Large document collections
- Research and reference materials
- Historical data analysis
- Knowledge base queries

**Web Search** for:
- Current events and trends
- Market research
- Competitive analysis
- Real-time information

**MCP Servers** for:
- Custom business tools
- Proprietary data sources
- Specialized APIs
- Internal systems integration

Configuration Management
========================

Environment Variables
---------------------

Configure tool behavior using environment variables:

.. code-block:: bash

   # MCP server configuration
   export OSTRUCT_MCP_URL_crm="https://api.company.com/mcp"
   export OSTRUCT_MCP_URL_analytics="https://analytics.company.com/mcp"

   # Default tool settings
   export OSTRUCT_DEFAULT_WS_COUNTRY="United States"
   export OSTRUCT_DEFAULT_CI_DOWNLOAD_DIR="./analysis_outputs"

Configuration File
------------------

Use ``ostruct.yaml`` for persistent configuration:

.. code-block:: yaml

   template:
     max_file_size: null  # unlimited (can also use size suffixes like "128KB", "1MB")

   tools:
     web_search:
       enabled: true
       country: "United States"
       context_size: "medium"

     code_interpreter:
       cleanup: true
       download_dir: "./downloads"
       duplicate_outputs: "rename"

     file_search:
       cleanup: true
       timeout: 60.0
       retries: 3

   mcp:
     servers:
       - label: "crm"
         url: "https://api.company.com/mcp"
         headers:
           Authorization: "Bearer ${CRM_TOKEN}"
       - label: "analytics"
         url: "https://analytics.company.com/mcp"

     require_approval: "never"

Troubleshooting
===============

Common Issues
-------------

**Code Interpreter:**
- Large file upload timeouts: Reduce file sizes or use streaming
- Memory errors: Process data in smaller chunks
- Package availability: Check Python environment limitations

**File Search:**
- **Empty results**: Known OpenAI API issue - see `known-issues/2025-07-openai-file-search-empty-results.md <../../known-issues/2025-07-openai-file-search-empty-results.md>`_
- Indexing failures: Ensure documents are text-readable
- Search timeouts: Increase timeout values for large document sets
- Poor search results: Use more specific queries and relevant documents

**Web Search:**
- No results: Check internet connectivity and search terms
- Geographic restrictions: Verify location settings
- Rate limiting: Reduce search frequency in templates

**MCP Servers:**
- Connection failures: Verify server URLs and network connectivity
- Authentication errors: Check headers and credentials
- Tool unavailability: Verify server status and tool permissions

Performance Optimization
------------------------

1. **Selective Tool Usage**: Only enable tools needed for your specific task
2. **File Size Management**: Optimize file sizes for faster uploads and processing
3. **Concurrent Requests**: Use appropriate timeout values for your network
4. **Caching**: Reuse vector stores and downloaded files when appropriate

See Also
========

- :doc:`cli_reference` - Complete CLI flag reference
- :doc:`template_guide` - Template authoring with tool integration
- :doc:`advanced_patterns` - Advanced multi-tool workflows
- :doc:`../security/overview` - Security considerations for tool usage
