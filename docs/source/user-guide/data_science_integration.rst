Data Science Integration Guide
==============================

**What is ostruct?** A schema-first CLI that renders Jinja2 templates locally in a sandbox, then sends the resulting prompt + JSON schema to OpenAI's Structured Outputs endpoint for guaranteed valid JSON responses. Perfect for data science workflows requiring reliable, structured analysis outputs.

Learn how to leverage ostruct for data science workflows, including Jupyter/Colab integration, multi-source analysis, and visualization generation. This guide covers everything from basic data extraction to complex research synthesis workflows.

.. note::
   This guide focuses on data science use cases. For general template usage, see the :doc:`template_guide`. For tool integration basics, see :doc:`tool_integration`.

.. tip::
   **Quick Start**: Jump to :ref:`jupyter-integration` if you want to start using ostruct in Jupyter notebooks immediately.

Overview
========

ostruct excels at transforming unstructured data into structured insights, making it perfect for data science workflows where you need to:

- Extract structured data from diverse sources (CSV, PDFs, web pages, APIs)
- Combine quantitative analysis with qualitative research
- Generate consistent, validated output schemas for downstream processing
- Integrate AI-powered analysis into existing data pipelines

Key Benefits for Data Science
-----------------------------

**Schema-First Reliability**
  Every output matches your defined JSON schema, eliminating parsing errors and ensuring consistent data structures for analysis.

**Multi-Tool Orchestration**
  Combine Code Interpreter (Python execution), File Search (document analysis), and Web Search (current data) in a single workflow. Note: ``--tool-choice auto`` (default) lets the model decide when to use tools; use ``--tool-choice required`` to force tool usage.

**Notebook Integration**
  Works seamlessly in Jupyter, Colab, and other notebook environments with proper token management and output formatting.

**Crucial Limitations**
  - **Binary files cannot be accessed in templates** - they must be routed to Code Interpreter (``ci:``) or user-data (``ud:``)
  - **File size limits** apply based on ``OSTRUCT_TEMPLATE_FILE_LIMIT`` environment variable
  - **Internet access** in Code Interpreter may be limited depending on OpenAI's current restrictions

**Reproducible Workflows**
  Template-based approach ensures consistent analysis across different datasets and team members.

.. _jupyter-integration:

Jupyter/Colab Integration
=========================

Setting Up ostruct in Notebooks
--------------------------------

**Installation in Jupyter/Colab:**

.. code-block:: bash

   # Install ostruct in notebook environment
   pip install ostruct-cli

   # For enhanced file type detection (recommended for data science)
   pip install ostruct-cli[enhanced-detection]

   # Verify installation
   ostruct --version

.. code-block:: python

   # Set up OpenAI API key in Python
   import os
   os.environ['OPENAI_API_KEY'] = 'your-api-key-here'

**30-Second Working Example:**

.. code-block:: bash

   # Create simple template
   echo "Analyze this data: {{ data.content }}" > analyze.j2

   # Create schema
   echo '{"type":"object","properties":{"insights":{"type":"array","items":{"type":"string"}}}}' > schema.json

   # Create sample data
   echo "Sales: Jan=100, Feb=150, Mar=120" > data.txt

   # Run analysis
   ostruct run analyze.j2 schema.json --file prompt:data data.txt --model gpt-4o-mini

**Expected Output:**

.. code-block:: json

   {
     "insights": [
       "Sales peaked in February with 150 units",
       "March saw a 20% decline from February",
       "Overall trend shows growth from Jan to Feb, then decline"
     ]
   }

**Basic Notebook Workflow:**

.. code-block:: python

   # Create a simple data extraction template
   template_content = '''
   ---
   system_prompt: You are an expert data analyst. Extract key metrics and insights.
   ---
   Analyze this dataset and extract the key findings:

   {{ data.content }}

   Focus on:
   1. Summary statistics
   2. Notable patterns or trends
   3. Data quality issues
   4. Recommendations for further analysis
   '''

   # Write template to file
   with open('data_analysis.j2', 'w') as f:
       f.write(template_content)

   # Define output schema
   schema = {
       "type": "object",
       "properties": {
           "summary_stats": {
               "type": "object",
               "description": "Key summary statistics"
           },
           "patterns": {
               "type": "array",
               "items": {"type": "string"},
               "description": "Notable patterns or trends found"
           },
           "data_quality": {
               "type": "array",
               "items": {"type": "string"},
               "description": "Data quality issues identified"
           },
           "recommendations": {
               "type": "array",
               "items": {"type": "string"},
               "description": "Recommendations for further analysis"
           }
       },
       "required": ["summary_stats", "patterns", "data_quality", "recommendations"]
   }

   import json
   with open('analysis_schema.json', 'w') as f:
       json.dump(schema, f, indent=2)

**Running Analysis in Notebooks:**

.. code-block:: python

   # Run ostruct analysis
   import subprocess
   import json

   # Execute ostruct command
   result = subprocess.run([
       'ostruct', 'run', 'data_analysis.j2', 'analysis_schema.json',
       '--file', 'ci:data', 'your_dataset.csv',
       '--model', 'gpt-4o',
       '--output-file', 'analysis_results.json'
   ], capture_output=True, text=True)

   # Load and display results
   with open('analysis_results.json', 'r') as f:
       analysis = json.load(f)

   print("Analysis Results:")
   print(f"Patterns found: {len(analysis['patterns'])}")
   for pattern in analysis['patterns']:
       print(f"  • {pattern}")

Try in Colab
------------

.. raw:: html

   <a href="https://colab.research.google.com/github/yaniv-golan/ostruct/blob/main/examples/data-science/notebooks/ostruct_data_analysis.ipynb" target="_blank">
     <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
   </a>

Multi-Tool Data Science Workflows
==================================

Combining Code Interpreter, File Search, and Web Search
-------------------------------------------------------

**Market Research + Data Analysis Example:**

.. code-block:: bash

   # Comprehensive business intelligence workflow
   ostruct run market_analysis.j2 business_intel_schema.json \
     --file ci:sales_data quarterly_sales.csv \
     --file fs:market_reports industry_report.pdf \
     --enable-tool web-search \
     --model gpt-4o

**Template Example (market_analysis.j2):**

.. code-block:: jinja

   ---
   system_prompt: |
     You are a senior business analyst. Combine quantitative sales data with
     market research and current industry trends to provide comprehensive insights.
   ---

   # Business Intelligence Analysis

   ## Sales Data Analysis
   {% if code_interpreter_enabled %}
   Analyze the sales data for trends, seasonality, and performance metrics:
   {{ sales_data.content }}

   Generate visualizations showing:
   - Monthly sales trends
   - Product category performance
   - Regional sales distribution
   {% endif %}

   ## Market Context
   {% if file_search_enabled %}
   Research market conditions and competitive landscape from:
   {{ market_reports.content }}

   Extract insights about:
   - Market size and growth
   - Competitive positioning
   - Industry trends
   {% endif %}

   ## Current Market Intelligence
   {% if web_search_enabled %}
   Research current market conditions, recent news, and industry developments
   relevant to our business sector.
   {% endif %}

   ## Synthesis
   Combine all data sources to provide:
   1. Performance assessment against market conditions
   2. Opportunities and threats analysis
   3. Strategic recommendations
   4. Key metrics to monitor

**Output Schema for Business Intelligence:**

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "sales_analysis": {
         "type": "object",
         "properties": {
           "trends": {"type": "array", "items": {"type": "string"}},
           "key_metrics": {"type": "object"},
           "performance_summary": {"type": "string"}
         }
       },
       "market_context": {
         "type": "object",
         "properties": {
           "market_size": {"type": "string"},
           "growth_rate": {"type": "string"},
           "competitive_position": {"type": "string"}
         }
       },
       "current_intelligence": {
         "type": "array",
         "items": {"type": "string"},
         "description": "Recent market developments"
       },
       "strategic_recommendations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "recommendation": {"type": "string"},
             "priority": {"type": "string", "enum": ["high", "medium", "low"]},
             "rationale": {"type": "string"}
           }
         }
       }
     }
   }

Research Synthesis Workflows
-----------------------------

**Academic Research Analysis:**

.. code-block:: bash

   # Combine literature review with data analysis
   ostruct run research_synthesis.j2 research_schema.json \
     --file fs:papers "*.pdf" --recursive \
     --file ci:dataset research_data.csv \
     --enable-tool web-search \
     --model gpt-4o

This workflow:

1. **Searches papers** using File Search for literature context
2. **Analyzes data** using Code Interpreter for statistical insights
3. **Updates with current research** using Web Search
4. **Synthesizes findings** into structured research output

Data Science Schema Templates
=============================

Common schemas for data science outputs:

Statistical Analysis Results
----------------------------

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "descriptive_stats": {
         "type": "object",
         "properties": {
           "mean": {"type": "number"},
           "median": {"type": "number"},
           "std_deviation": {"type": "number"},
           "min": {"type": "number"},
           "max": {"type": "number"}
         }
       },
       "correlations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "variables": {"type": "array", "items": {"type": "string"}},
             "correlation": {"type": "number"},
             "significance": {"type": "number"}
           }
         }
       },
       "hypothesis_tests": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "test": {"type": "string"},
             "p_value": {"type": "number"},
             "conclusion": {"type": "string"}
           }
         }
       }
     }
   }

Visualization Specifications
-----------------------------

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "visualizations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "type": {"type": "string", "enum": ["scatter", "line", "bar", "histogram", "heatmap"]},
             "title": {"type": "string"},
             "x_axis": {"type": "string"},
             "y_axis": {"type": "string"},
             "data_source": {"type": "string"},
             "insights": {"type": "array", "items": {"type": "string"}}
           }
         }
       }
     }
   }

Practical Examples and Use Cases
=================================

Financial Data Analysis
-----------------------

**Scenario**: Analyze quarterly financial data with market context

.. code-block:: bash

   ostruct run financial_analysis.j2 financial_schema.json \
     --file ci:financials quarterly_report.csv \
     --file fs:industry industry_benchmarks.pdf \
     --enable-tool web-search \
     --model gpt-4o

**Key Features**:
- Automated ratio calculations via Code Interpreter
- Benchmark comparisons via File Search
- Current market conditions via Web Search
- Structured output for further processing

Scientific Research Synthesis
-----------------------------

**Scenario**: Combine experimental data with literature review

.. code-block:: bash

   ostruct run research_synthesis.j2 research_schema.json \
     --file ci:results experimental_data.csv \
     --dir fs:literature "papers/" \
     --enable-tool web-search \
     --model gpt-4o

**Workflow**:
1. Statistical analysis of experimental results
2. Literature context from paper database
3. Current research trends from web search
4. Synthesized conclusions with citations

Market Research Automation
---------------------------

**Scenario**: Automated market intelligence reports

.. code-block:: bash

   ostruct run market_intel.j2 market_schema.json \
     --file ci:sales_data current_sales.csv \
     --file fs:reports competitor_analysis.pdf \
     --enable-tool web-search \
     --ws-context-size comprehensive \
     --model gpt-4o

**Output**: Structured market intelligence report with quantitative metrics, competitive analysis, and current market trends.

Token Management for Large Datasets
====================================

Best Practices
--------------

**Chunking Large Files:**

.. code-block:: python

   # Split large datasets for processing
   import pandas as pd

   # Read large dataset
   df = pd.read_csv('large_dataset.csv')

   # Process in chunks
   chunk_size = 1000
   for i in range(0, len(df), chunk_size):
       chunk = df[i:i+chunk_size]
       chunk.to_csv(f'chunk_{i//chunk_size}.csv', index=False)

       # Process each chunk
       subprocess.run([
           'ostruct', 'run', 'analysis.j2', 'schema.json',
           '--file', 'ci:data', f'chunk_{i//chunk_size}.csv',
           '--output-file', f'results_{i//chunk_size}.json'
       ])

**Dry Run for Token Estimation:**

.. code-block:: bash

   # Preview prompt and token counts without API cost
   ostruct run analysis.j2 schema.json \
     --file ci:data large_dataset.csv \
     --dry-run

   # This shows the full expanded prompt and token count
   # Use this to optimize before making expensive API calls

   # Use token-efficient models for large datasets
   ostruct run analysis.j2 schema.json \
     --file ci:data large_dataset.csv \
     --model gpt-4o-mini  # More cost-effective for large inputs

Error Handling and Troubleshooting
===================================

Known Issues
------------

**File Search Empty Results (Current Bug):**

File Search may return empty results despite successful vector store creation. This is a known upstream OpenAI API issue affecting all models.

**Workarounds:**
- **Fallback to Code Interpreter:** Route documents to ``ci:`` for programmatic parsing
- **Direct prompt inclusion:** Use ``prompt:`` routing for smaller documents that fit in context
- **Hybrid approach:** Combine manual document parsing with web search for current information

.. code-block:: bash

   # If File Search fails, try Code Interpreter parsing
   ostruct run analysis.j2 schema.json \
     --file ci:docs research_paper.pdf \
     --enable-tool web-search \
     --model gpt-4o

Common Issues
-------------

**Binary File Access Errors:**

.. code-block:: jinja

   {# Handle mixed file types gracefully #}
   {% for file in dataset %}
     {% if file.extension in ['csv', 'txt', 'json'] %}
       {{ file.content }}
     {% else %}
       File: {{ file.name }} ({{ file.size }} bytes, binary - use Code Interpreter for analysis)
     {% endif %}
   {% endfor %}

**Token Limit Errors:**

.. code-block:: bash

   # Use summary approach for large files
   ostruct run summarize_first.j2 summary_schema.json \
     --file ci:data large_file.csv \
     --max-output-tokens 4000

**Schema Validation Failures:**

.. code-block:: python

   # Validate schema before processing
   import jsonschema
   import json

   with open('schema.json', 'r') as f:
       schema = json.load(f)

   # Test with sample data
   sample_output = {"test": "data"}
   try:
       jsonschema.validate(sample_output, schema)
       print("Schema is valid")
   except jsonschema.ValidationError as e:
       print(f"Schema error: {e}")

Performance Optimization
========================

Efficient Workflows
-------------------

**Parallel Processing:**

.. code-block:: python

   import concurrent.futures
   import subprocess

   def process_file(filename):
       return subprocess.run([
           'ostruct', 'run', 'analysis.j2', 'schema.json',
           '--file', 'ci:data', filename,
           '--output-file', f'results_{filename}.json'
       ], capture_output=True)

   # Process multiple files in parallel
   files = ['data1.csv', 'data2.csv', 'data3.csv']
   with concurrent.futures.ThreadPoolExecutor() as executor:
       results = list(executor.map(process_file, files))

**Model Selection for Different Tasks:**

.. code-block:: bash

   # Use appropriate models for different complexity levels

   # Simple extraction - use efficient model
   ostruct run extract.j2 schema.json --model gpt-4o-mini

   # Complex analysis - use powerful model
   ostruct run complex_analysis.j2 schema.json --model gpt-4o

   # Reasoning tasks - use reasoning model
   ostruct run reasoning.j2 schema.json --model o1-preview

Integration with Data Science Tools
====================================

Pandas Integration
------------------

.. code-block:: python

   import pandas as pd
   import json
   import subprocess

   # Process DataFrame with ostruct
   def analyze_dataframe(df, analysis_template, schema_file):
       # Save DataFrame temporarily
       temp_file = 'temp_data.csv'
       df.to_csv(temp_file, index=False)

       # Run ostruct analysis
       result = subprocess.run([
           'ostruct', 'run', analysis_template, schema_file,
           '--file', 'ci:data', temp_file,
           '--output-file', 'temp_results.json'
       ], capture_output=True, text=True)

       # Load results
       with open('temp_results.json', 'r') as f:
           return json.load(f)

   # Example usage
   df = pd.read_csv('sales_data.csv')
   insights = analyze_dataframe(df, 'sales_analysis.j2', 'sales_schema.json')

Matplotlib/Seaborn Integration
------------------------------

.. code-block:: python

   # Generate visualization specifications with ostruct
   viz_template = '''
   ---
   system_prompt: You are a data visualization expert. Generate matplotlib/seaborn code specifications.
   ---
   Create visualization specifications for this dataset:
   {{ data.content }}

   Generate specifications for the most insightful charts to show patterns, distributions, and relationships.
   '''

   # Use ostruct to generate viz specs, then create plots
   viz_specs = analyze_dataframe(df, 'viz_template.j2', 'viz_schema.json')

   # Execute generated visualization code
   for viz in viz_specs['visualizations']:
       exec(viz['matplotlib_code'])

Next Steps
==========

**Getting Started:**

1. Set up ostruct in your notebook environment
2. Try the basic data extraction example
3. Experiment with multi-tool workflows
4. Adapt schemas for your specific use cases

**Advanced Usage:**

- Explore the :doc:`template_guide` for complex template patterns
- See :doc:`tool_integration` for multi-tool coordination
- Check :doc:`cli_reference` for all available options

See Also
========

- :doc:`template_guide` - Comprehensive template creation guide
- :doc:`tool_integration` - Multi-tool integration patterns
- :doc:`cli_reference` - Complete command-line reference
- :doc:`quickstart` - General getting started guide
