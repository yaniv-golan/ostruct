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

Interactive Jupyter Notebook Example
=====================================

Experience ostruct data science workflows interactively with our comprehensive Jupyter notebook:

.. raw:: html

   <div style="text-align: center; margin: 20px 0;">
   <a href="https://colab.research.google.com/github/yaniv-golan/ostruct/blob/main/examples/data-science/notebooks/ostruct_data_analysis.ipynb" target="_blank">
       <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" style="margin: 10px;">
   </a>
   </div>

**What's included in the notebook:**

- **6 Complete Examples**: From basic analysis to advanced multi-tool workflows
- **Working Code**: All examples include working templates, schemas, and data
- **Financial Analysis**: Quarterly financial analysis with market context
- **Business Intelligence**: Competitive analysis and strategic recommendations
- **Interactive Workflows**: Dynamic analysis based on custom questions
- **Batch Processing**: Production-ready patterns for multiple datasets
- **Best Practices**: Performance optimization, cost management, security

**Local Usage:**

.. code-block:: bash

   # Clone and run locally
   git clone https://github.com/yaniv-golan/ostruct.git
   cd ostruct/examples/data-science/notebooks
   jupyter notebook ostruct_data_analysis.ipynb

The notebook demonstrates all the workflows described in this guide with working code you can run immediately.

Try in Colab
------------

.. raw:: html

   <a href="https://colab.research.google.com/github/yaniv-golan/ostruct/blob/main/examples/data-science/notebooks/ostruct_data_analysis.ipynb" target="_blank">
     <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
   </a>

Advanced Notebook Integration
-----------------------------

**Jupyter Magic Commands for ostruct:**

.. code-block:: python

   # Create reusable magic command for ostruct
   from IPython.core.magic import line_magic, Magics, magics_class
   from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
   import subprocess
   import json

   @magics_class
   class OstructMagics(Magics):

       @line_magic
       @magic_arguments()
       @argument('template', help='Template file path')
       @argument('schema', help='Schema file path')
       @argument('--file', dest='data_file', help='Data file to analyze')
       @argument('--model', default='gpt-4o-mini', help='Model to use')
       def ostruct(self, line):
           """Run ostruct analysis from Jupyter cell"""
           args = parse_argstring(self.ostruct, line)

           result = subprocess.run([
               'ostruct', 'run', args.template, args.schema,
               '--file', f'ci:data', args.data_file,
               '--model', args.model,
               '--output-file', 'results.json'
           ], capture_output=True, text=True)

           if result.returncode == 0:
               with open('results.json', 'r') as f:
                   return json.load(f)
           else:
               print(f"Error: {result.stderr}")
               return None

   # Register the magic
   get_ipython().register_magic_functions(OstructMagics)

   # Usage: %ostruct analysis.j2 schema.json --file data.csv --model gpt-4o

**DataFrame Integration Patterns:**

.. code-block:: python

   import pandas as pd
   import tempfile
   import os

   class DataFrameAnalyzer:
       """Enhanced DataFrame analysis with ostruct integration"""

       def __init__(self, df):
           self.df = df
           self.temp_files = []

       def create_context_template(self, analysis_focus="general"):
           """Generate template with DataFrame context"""
           template = f'''
   ---
   system_prompt: |
     You are analyzing a dataset with {len(self.df)} rows and {len(self.df.columns)} columns.
     Focus on {analysis_focus} analysis patterns.
   ---

   Dataset Overview:
   - Shape: {self.df.shape[0]} rows × {self.df.shape[1]} columns
   - Columns: {", ".join(self.df.columns.tolist())}
   - Data types: {dict(self.df.dtypes.astype(str))}

   Sample data:
   {{{{ data.content }}}}

   Analysis Requirements:
   1. Identify key patterns and trends
   2. Assess data quality and completeness
   3. Suggest follow-up analysis steps
   4. Highlight any anomalies or outliers
   '''
           return template

       def analyze(self, focus="general", sample_size=1000):
           """Run ostruct analysis on DataFrame"""

           # Sample large datasets
           sample_df = self.df.sample(min(sample_size, len(self.df)))

           # Create temporary files
           with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
               csv_file = f.name
               sample_df.to_csv(f, index=False)
               self.temp_files.append(csv_file)

           with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
               template_file = f.name
               f.write(self.create_context_template(focus))
               self.temp_files.append(template_file)

           # Define schema
           schema = {
               "type": "object",
               "properties": {
                   "summary": {"type": "string", "description": "Overall dataset summary"},
                   "patterns": {
                       "type": "array",
                       "items": {"type": "string"},
                       "description": "Key patterns identified"
                   },
                   "quality_issues": {
                       "type": "array",
                       "items": {"type": "string"},
                       "description": "Data quality concerns"
                   },
                   "recommendations": {
                       "type": "array",
                       "items": {"type": "string"},
                       "description": "Analysis recommendations"
                   }
               }
           }

           with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
               schema_file = f.name
               json.dump(schema, f, indent=2)
               self.temp_files.append(schema_file)

           # Run analysis
           result = subprocess.run([
               'ostruct', 'run', template_file, schema_file,
               '--file', f'ci:data', csv_file,
               '--model', 'gpt-4o-mini'
           ], capture_output=True, text=True)

           if result.returncode == 0:
               return json.loads(result.stdout)
           else:
               print(f"Analysis failed: {result.stderr}")
               return None

       def cleanup(self):
           """Clean up temporary files"""
           for file_path in self.temp_files:
               try:
                   os.unlink(file_path)
               except FileNotFoundError:
                   pass
           self.temp_files = []

       def __del__(self):
           self.cleanup()

   # Usage example
   df = pd.read_csv('sales_data.csv')
   analyzer = DataFrameAnalyzer(df)
   insights = analyzer.analyze(focus="sales trends")
   print(f"Found {len(insights['patterns'])} patterns")

**Token Management for Large Datasets:**

.. code-block:: python

   def smart_sample_for_analysis(df, max_tokens=8000, chars_per_token=4):
       """
       Intelligently sample DataFrame to fit within token limits
       """
       # Estimate current size
       csv_str = df.to_csv(index=False)
       estimated_tokens = len(csv_str) // chars_per_token

       if estimated_tokens <= max_tokens:
           return df

       # Calculate sample size needed
       sample_ratio = max_tokens / estimated_tokens
       sample_size = int(len(df) * sample_ratio * 0.8)  # 80% buffer

       print(f"Dataset too large ({estimated_tokens} tokens). Sampling {sample_size} rows.")

       # Stratified sampling if categorical columns exist
       categorical_cols = df.select_dtypes(include=['object']).columns
       if len(categorical_cols) > 0:
           return df.groupby(categorical_cols[0]).apply(
               lambda x: x.sample(min(len(x), sample_size // df[categorical_cols[0]].nunique()))
           ).reset_index(drop=True)
       else:
           return df.sample(sample_size)

   # Usage
   large_df = pd.read_csv('large_dataset.csv')
   manageable_df = smart_sample_for_analysis(large_df)
   analyzer = DataFrameAnalyzer(manageable_df)

**Environment Variable Management:**

.. code-block:: python

   # Secure API key management for notebooks
   import os
   from getpass import getpass

   def setup_ostruct_environment():
       """Setup ostruct environment variables securely"""

       if 'OPENAI_API_KEY' not in os.environ:
           print("OpenAI API key not found in environment.")
           api_key = getpass("Enter your OpenAI API key: ")
           os.environ['OPENAI_API_KEY'] = api_key
           print("✓ API key set for this session")

       # Set notebook-friendly defaults
       os.environ['OSTRUCT_CACHE_UPLOADS'] = 'true'
       os.environ['OSTRUCT_TEMPLATE_FILE_LIMIT'] = '10MB'

       print("✓ ostruct environment configured")

   # Run at start of notebook
   setup_ostruct_environment()

**Visualization Integration:**

.. code-block:: python

   def generate_analysis_visualizations(df, analysis_results):
       """
       Generate visualizations based on ostruct analysis recommendations
       """
       import matplotlib.pyplot as plt
       import seaborn as sns

       # Extract visualization suggestions from analysis
       if 'recommendations' in analysis_results:
           viz_suggestions = [
               rec for rec in analysis_results['recommendations']
               if any(word in rec.lower() for word in ['plot', 'chart', 'graph', 'visualiz'])
           ]

           for suggestion in viz_suggestions:
               print(f"Visualization suggestion: {suggestion}")

       # Auto-generate basic plots for numeric columns
       numeric_cols = df.select_dtypes(include=['number']).columns

       if len(numeric_cols) > 0:
           fig, axes = plt.subplots(2, 2, figsize=(12, 10))

           # Distribution plot
           df[numeric_cols[0]].hist(ax=axes[0,0])
           axes[0,0].set_title(f'Distribution of {numeric_cols[0]}')

           # Correlation heatmap if multiple numeric columns
           if len(numeric_cols) > 1:
               corr_matrix = df[numeric_cols].corr()
               sns.heatmap(corr_matrix, annot=True, ax=axes[0,1])
               axes[0,1].set_title('Correlation Matrix')

           # Box plot for outlier detection
           df.boxplot(column=numeric_cols[0], ax=axes[1,0])
           axes[1,0].set_title(f'Outliers in {numeric_cols[0]}')

           # Trend over index (if meaningful)
           df[numeric_cols[0]].plot(ax=axes[1,1])
           axes[1,1].set_title(f'Trend of {numeric_cols[0]}')

           plt.tight_layout()
           plt.show()

   # Usage after analysis
   viz_results = generate_analysis_visualizations(df, insights)

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

Comprehensive Multi-Tool Workflow Patterns
===========================================

CSV Analysis with Code Interpreter
-----------------------------------

**Pattern 1: Enhanced Data Analysis with Visualization**

.. code-block:: bash

   # Deep CSV analysis with automated visualization generation
   ostruct run csv_deep_analysis.j2 analysis_schema.json \
     --file ci:dataset sales_data.csv \
     --file ci:reference benchmark_data.csv \
     --model gpt-4o

**Template (csv_deep_analysis.j2):**

.. code-block:: jinja

   ---
   system_prompt: |
     You are a senior data analyst. Perform comprehensive analysis including
     statistical testing, visualization generation, and business insights.
   ---

   # Comprehensive CSV Data Analysis

   ## Dataset Overview
   Primary dataset: {{ dataset.name }} ({{ dataset.size }} bytes)
   Reference dataset: {{ reference.name }} ({{ reference.size }} bytes)

   ## Analysis Tasks

   ### 1. Statistical Analysis
   Load and analyze the primary dataset:
   ```python
   import pandas as pd
   import numpy as np
   import matplotlib.pyplot as plt
   import seaborn as sns
   from scipy import stats

   # Load data
   df = pd.read_csv('{{ dataset.name }}')
   ref_df = pd.read_csv('{{ reference.name }}')

   # Generate comprehensive statistics
   print("=== DATASET SUMMARY ===")
   print(df.describe())
   print(f"Dataset shape: {df.shape}")
   print(f"Missing values: {df.isnull().sum().sum()}")
   ```

   ### 2. Visualization Generation
   Create insightful visualizations:
   ```python
   # Set up the plotting environment
   plt.style.use('seaborn-v0_8')
   fig, axes = plt.subplots(2, 2, figsize=(15, 12))

   # 1. Distribution analysis
   numeric_cols = df.select_dtypes(include=[np.number]).columns
   if len(numeric_cols) > 0:
       df[numeric_cols[0]].hist(bins=30, ax=axes[0,0])
       axes[0,0].set_title(f'Distribution of {numeric_cols[0]}')

   # 2. Correlation heatmap
   if len(numeric_cols) > 1:
       corr_matrix = df[numeric_cols].corr()
       sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', ax=axes[0,1])
       axes[0,1].set_title('Correlation Matrix')

   # 3. Time series or trend analysis
   if 'date' in df.columns or 'timestamp' in df.columns:
       # Time series visualization logic
       pass
   else:
       # Box plot for outlier detection
       if len(numeric_cols) > 0:
           df.boxplot(column=numeric_cols[0], ax=axes[1,0])
           axes[1,0].set_title(f'Outlier Analysis: {numeric_cols[0]}')

   # 4. Comparative analysis with reference data
   # Compare key metrics between datasets
   axes[1,1].bar(['Primary', 'Reference'],
                 [df[numeric_cols[0]].mean(), ref_df[numeric_cols[0]].mean()])
   axes[1,1].set_title('Comparative Analysis')

   plt.tight_layout()
   plt.savefig('comprehensive_analysis.png', dpi=300, bbox_inches='tight')
   plt.show()
   ```

   ### 3. Statistical Testing
   Perform significance tests:
   ```python
   # Compare primary vs reference dataset
   if len(numeric_cols) > 0:
       primary_values = df[numeric_cols[0]].dropna()
       reference_values = ref_df[numeric_cols[0]].dropna()

       # T-test for mean differences
       t_stat, p_value = stats.ttest_ind(primary_values, reference_values)
       print(f"T-test results: t={t_stat:.4f}, p={p_value:.4f}")

       # Effect size (Cohen's d)
       pooled_std = np.sqrt(((len(primary_values)-1)*primary_values.var() +
                            (len(reference_values)-1)*reference_values.var()) /
                           (len(primary_values)+len(reference_values)-2))
       cohens_d = (primary_values.mean() - reference_values.mean()) / pooled_std
       print(f"Effect size (Cohen's d): {cohens_d:.4f}")
   ```

   Provide business insights and recommendations based on the analysis.

**Output Schema:**

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "dataset_summary": {
         "type": "object",
         "properties": {
           "rows": {"type": "number"},
           "columns": {"type": "number"},
           "missing_values": {"type": "number"},
           "data_types": {"type": "object"}
         }
       },
       "statistical_analysis": {
         "type": "object",
         "properties": {
           "descriptive_stats": {"type": "object"},
           "correlations": {"type": "array", "items": {"type": "object"}},
           "significance_tests": {"type": "array", "items": {"type": "object"}}
         }
       },
       "visualizations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "filename": {"type": "string"},
             "type": {"type": "string"},
             "description": {"type": "string"},
             "insights": {"type": "array", "items": {"type": "string"}}
           }
         }
       },
       "business_insights": {
         "type": "array",
         "items": {"type": "string"}
       },
       "recommendations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "recommendation": {"type": "string"},
             "priority": {"type": "string"},
             "rationale": {"type": "string"}
           }
         }
       }
     }
   }

Web Research + Data Analysis Combinations
------------------------------------------

**Pattern 2: Market Intelligence with Data Validation**

.. code-block:: bash

   # Combine internal sales data with current market intelligence
   ostruct run market_intelligence.j2 market_schema.json \
     --file ci:sales internal_sales.csv \
     --file ci:competitor competitor_analysis.csv \
     --enable-tool web-search \
     --ws-context-size comprehensive \
     --model gpt-4o

**Template (market_intelligence.j2):**

.. code-block:: jinja

   ---
   system_prompt: |
     You are a market intelligence analyst. Use web search to gather current
     market data and validate it against internal analysis.
   ---

   # Market Intelligence Analysis

   ## Internal Data Analysis

   ### Sales Performance Analysis
   ```python
   import pandas as pd
   import matplotlib.pyplot as plt

   # Load internal data
   sales_df = pd.read_csv('{{ sales.name }}')
   competitor_df = pd.read_csv('{{ competitor.name }}')

   # Analyze sales trends
   print("=== INTERNAL SALES ANALYSIS ===")
   monthly_sales = sales_df.groupby('month')['revenue'].sum()
   print("Monthly revenue trends:")
   print(monthly_sales.describe())

   # Competitive position analysis
   print("\n=== COMPETITIVE ANALYSIS ===")
   print("Market share analysis:")
   print(competitor_df['market_share'].describe())

   # Generate comparison chart
   fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

   monthly_sales.plot(kind='line', ax=ax1, title='Internal Sales Trend')
   competitor_df['market_share'].plot(kind='bar', ax=ax2, title='Market Share Distribution')

   plt.tight_layout()
   plt.savefig('internal_analysis.png')
   plt.show()
   ```

   ## Current Market Research

   Research current market conditions and trends:
   - Industry growth rates and forecasts
   - Recent competitor announcements and strategy changes
   - Regulatory changes affecting the market
   - Consumer behavior shifts and emerging trends
   - Technology disruptions in the sector

   Focus your search on:
   1. Market size and growth projections for {{ sales.content | extract_industry }}
   2. Recent competitor activities and market positioning
   3. Consumer preference shifts in the last 6 months
   4. Regulatory or economic factors affecting demand

   ## Data Validation and Synthesis

   ```python
   # Cross-validate web research findings with internal data
   print("=== VALIDATION ANALYSIS ===")

   # Check if internal trends align with market research
   internal_growth = (monthly_sales.iloc[-1] - monthly_sales.iloc[0]) / monthly_sales.iloc[0] * 100
   print(f"Internal growth rate: {internal_growth:.2f}%")

   # This will be compared with web research findings
   print("Compare this with market research growth rates above")

   # Identify discrepancies and opportunities
   avg_competitor_share = competitor_df['market_share'].mean()
   our_estimated_share = 100 / len(competitor_df)  # Assuming equal distribution

   print(f"Average competitor market share: {avg_competitor_share:.2f}%")
   print(f"Our estimated position: {our_estimated_share:.2f}%")
   ```

   Synthesize findings from internal data and web research to provide:
   1. Market opportunity assessment
   2. Competitive positioning recommendations
   3. Strategic actions based on combined insights
   4. Risk factors identified from external research

File Search + Code Interpreter for Research Synthesis
-----------------------------------------------------

**Pattern 3: Academic Literature + Data Analysis**

.. code-block:: bash

   # Combine literature review with experimental data analysis
   ostruct run research_synthesis.j2 research_schema.json \
     --file fs:literature "research_papers/*.pdf" --recursive \
     --file ci:data experimental_results.csv \
     --file ci:reference baseline_data.csv \
     --enable-tool web-search \
     --model gpt-4o

**Template (research_synthesis.j2):**

.. code-block:: jinja

   ---
   system_prompt: |
     You are a research scientist. Synthesize literature findings with
     experimental data analysis to draw comprehensive conclusions.
   ---

   # Research Synthesis Analysis

   ## Literature Review Summary

   {% if file_search_enabled %}
   Based on the research papers in your knowledge base:

   {{ literature }}

   Extract and summarize:
   1. **Methodology consensus**: What experimental approaches are most validated?
   2. **Key findings**: What are the established relationships and effects?
   3. **Gaps identified**: What questions remain unanswered?
   4. **Methodological considerations**: What are the best practices?
   {% else %}
   Note: File Search unavailable. Proceeding with data analysis and web research.
   {% endif %}

   ## Experimental Data Analysis

   ### Statistical Analysis of Results
   ```python
   import pandas as pd
   import numpy as np
   import matplotlib.pyplot as plt
   import seaborn as sns
   from scipy import stats
   import statsmodels.api as sm

   # Load experimental data
   results_df = pd.read_csv('{{ data.name }}')
   baseline_df = pd.read_csv('{{ reference.name }}')

   print("=== EXPERIMENTAL DATA ANALYSIS ===")
   print(f"Experimental data shape: {results_df.shape}")
   print(f"Baseline data shape: {baseline_df.shape}")

   # Descriptive statistics
   print("\nExperimental Results Summary:")
   print(results_df.describe())

   print("\nBaseline Summary:")
   print(baseline_df.describe())

   # Statistical comparisons
   numeric_cols = results_df.select_dtypes(include=[np.number]).columns

   for col in numeric_cols:
       if col in baseline_df.columns:
           exp_values = results_df[col].dropna()
           baseline_values = baseline_df[col].dropna()

           # T-test
           t_stat, p_val = stats.ttest_ind(exp_values, baseline_values)

           # Effect size
           pooled_std = np.sqrt(((len(exp_values)-1)*exp_values.var() +
                                (len(baseline_values)-1)*baseline_values.var()) /
                               (len(exp_values)+len(baseline_values)-2))
           effect_size = (exp_values.mean() - baseline_values.mean()) / pooled_std

           print(f"\n{col} Analysis:")
           print(f"  Experimental mean: {exp_values.mean():.4f}")
           print(f"  Baseline mean: {baseline_values.mean():.4f}")
           print(f"  T-test p-value: {p_val:.4f}")
           print(f"  Effect size: {effect_size:.4f}")
   ```

   ### Visualization of Key Findings
   ```python
   # Create comprehensive visualization
   fig, axes = plt.subplots(2, 2, figsize=(15, 12))

   # 1. Comparison of means
   if len(numeric_cols) > 0:
       col = numeric_cols[0]
       means = [results_df[col].mean(), baseline_df[col].mean()]
       stds = [results_df[col].std(), baseline_df[col].std()]

       x_pos = np.arange(len(['Experimental', 'Baseline']))
       axes[0,0].bar(x_pos, means, yerr=stds, capsize=5)
       axes[0,0].set_xticks(x_pos)
       axes[0,0].set_xticklabels(['Experimental', 'Baseline'])
       axes[0,0].set_title(f'Comparison of {col}')

   # 2. Distribution comparison
   if len(numeric_cols) > 0:
       axes[0,1].hist(results_df[numeric_cols[0]].dropna(), alpha=0.7, label='Experimental')
       axes[0,1].hist(baseline_df[numeric_cols[0]].dropna(), alpha=0.7, label='Baseline')
       axes[0,1].legend()
       axes[0,1].set_title('Distribution Comparison')

   # 3. Correlation analysis
   if len(numeric_cols) > 1:
       corr_matrix = results_df[numeric_cols].corr()
       sns.heatmap(corr_matrix, annot=True, ax=axes[1,0])
       axes[1,0].set_title('Experimental Data Correlations')

   # 4. Trend analysis or scatter plot
   if len(numeric_cols) > 1:
       axes[1,1].scatter(results_df[numeric_cols[0]], results_df[numeric_cols[1]])
       axes[1,1].set_xlabel(numeric_cols[0])
       axes[1,1].set_ylabel(numeric_cols[1])
       axes[1,1].set_title('Relationship Analysis')

   plt.tight_layout()
   plt.savefig('research_analysis.png', dpi=300)
   plt.show()
   ```

   ## Current Research Context

   Search for recent publications and developments related to:
   - Latest methodological advances in this research area
   - Recent findings that support or contradict our results
   - Emerging theoretical frameworks
   - Clinical or practical applications of similar research

   ## Synthesis and Conclusions

   ```python
   print("=== RESEARCH SYNTHESIS ===")

   # Summary statistics for reporting
   if len(numeric_cols) > 0:
       primary_metric = numeric_cols[0]
       exp_mean = results_df[primary_metric].mean()
       baseline_mean = baseline_df[primary_metric].mean()
       improvement = ((exp_mean - baseline_mean) / baseline_mean) * 100

       print(f"Primary outcome ({primary_metric}):")
       print(f"  Experimental: {exp_mean:.4f}")
       print(f"  Baseline: {baseline_mean:.4f}")
       print(f"  Improvement: {improvement:.2f}%")

   print("\nReady for synthesis with literature and current research...")
   ```

   Provide comprehensive synthesis addressing:
   1. How experimental results align with literature findings
   2. Novel contributions of this research
   3. Limitations and considerations based on methodological review
   4. Future research directions
   5. Practical implications and applications

Visualization Generation Patterns
---------------------------------

**Pattern 4: Automated Chart Generation with Business Context**

.. code-block:: bash

   # Generate contextual visualizations with business insights
   ostruct run viz_generation.j2 visualization_schema.json \
     --file ci:data business_metrics.csv \
     --file ci:benchmark industry_benchmarks.csv \
     --enable-tool web-search \
     --model gpt-4o

**Template (viz_generation.j2):**

.. code-block:: jinja

   ---
   system_prompt: |
     You are a data visualization expert and business analyst. Create insightful
     visualizations that tell a compelling business story.
   ---

   # Business Data Visualization Generation

   ## Data Exploration and Preparation

   ```python
   import pandas as pd
   import matplotlib.pyplot as plt
   import seaborn as sns
   import plotly.graph_objects as go
   import plotly.express as px
   from plotly.subplots import make_subplots
   import numpy as np
   from datetime import datetime

   # Load data
   business_df = pd.read_csv('{{ data.name }}')
   benchmark_df = pd.read_csv('{{ benchmark.name }}')

   print("=== DATA OVERVIEW ===")
   print(f"Business data shape: {business_df.shape}")
   print(f"Benchmark data shape: {benchmark_df.shape}")
   print("\nBusiness data columns:", business_df.columns.tolist())
   print("Benchmark data columns:", benchmark_df.columns.tolist())

   # Data quality check
   print("\nMissing values:")
   print("Business data:", business_df.isnull().sum().sum())
   print("Benchmark data:", benchmark_df.isnull().sum().sum())
   ```

   ## Visualization 1: Performance Dashboard

   ```python
   # Create a comprehensive dashboard
   fig = make_subplots(
       rows=2, cols=2,
       subplot_titles=('Revenue Trend', 'Performance vs Benchmark',
                      'Category Breakdown', 'Growth Analysis'),
       specs=[[{"secondary_y": True}, {"type": "bar"}],
              [{"type": "pie"}, {"type": "scatter"}]]
   )

   # 1. Revenue trend with growth rate
   if 'date' in business_df.columns and 'revenue' in business_df.columns:
       business_df['date'] = pd.to_datetime(business_df['date'])
       monthly_revenue = business_df.groupby('date')['revenue'].sum().reset_index()

       fig.add_trace(
           go.Scatter(x=monthly_revenue['date'], y=monthly_revenue['revenue'],
                     mode='lines+markers', name='Revenue'),
           row=1, col=1
       )

       # Add growth rate on secondary y-axis
       monthly_revenue['growth_rate'] = monthly_revenue['revenue'].pct_change() * 100
       fig.add_trace(
           go.Scatter(x=monthly_revenue['date'], y=monthly_revenue['growth_rate'],
                     mode='lines', name='Growth Rate %', yaxis='y2'),
           row=1, col=1, secondary_y=True
       )

   # 2. Performance vs Benchmark
   if 'metric' in business_df.columns and 'value' in business_df.columns:
       metrics = business_df['metric'].unique()[:5]  # Top 5 metrics
       business_values = [business_df[business_df['metric']==m]['value'].mean() for m in metrics]
       benchmark_values = [benchmark_df[benchmark_df['metric']==m]['value'].mean() for m in metrics]

       fig.add_trace(
           go.Bar(x=metrics, y=business_values, name='Our Performance'),
           row=1, col=2
       )
       fig.add_trace(
           go.Bar(x=metrics, y=benchmark_values, name='Industry Benchmark'),
           row=1, col=2
       )

   # 3. Category breakdown
   if 'category' in business_df.columns and 'value' in business_df.columns:
       category_totals = business_df.groupby('category')['value'].sum()
       fig.add_trace(
           go.Pie(labels=category_totals.index, values=category_totals.values,
                 name="Category Distribution"),
           row=2, col=1
       )

   # 4. Growth analysis scatter
   if 'investment' in business_df.columns and 'return' in business_df.columns:
       fig.add_trace(
           go.Scatter(x=business_df['investment'], y=business_df['return'],
                     mode='markers', name='ROI Analysis',
                     text=business_df.get('category', ''),
                     textposition="top center"),
           row=2, col=2
       )

   fig.update_layout(height=800, showlegend=True,
                     title_text="Business Performance Dashboard")
   fig.write_html("business_dashboard.html")
   fig.show()
   ```

   ## Visualization 2: Competitive Analysis Charts

   ```python
   # Advanced competitive positioning
   plt.style.use('seaborn-v0_8')
   fig, axes = plt.subplots(2, 2, figsize=(16, 12))

   # Market positioning bubble chart
   if all(col in business_df.columns for col in ['market_share', 'growth_rate', 'revenue']):
       scatter = axes[0,0].scatter(business_df['market_share'],
                                  business_df['growth_rate'],
                                  s=business_df['revenue']/1000,  # Bubble size
                                  alpha=0.6, c=range(len(business_df)),
                                  cmap='viridis')
       axes[0,0].set_xlabel('Market Share (%)')
       axes[0,0].set_ylabel('Growth Rate (%)')
       axes[0,0].set_title('Market Positioning (Bubble size = Revenue)')

       # Add competitor benchmarks if available
       if all(col in benchmark_df.columns for col in ['market_share', 'growth_rate']):
           axes[0,0].scatter(benchmark_df['market_share'],
                            benchmark_df['growth_rate'],
                            marker='x', s=100, c='red', label='Competitors')
           axes[0,0].legend()

   # Performance radar chart simulation
   categories = ['Revenue', 'Market Share', 'Customer Satisfaction', 'Innovation', 'Efficiency']
   if len([col for col in categories if col.lower().replace(' ', '_') in business_df.columns]) >= 3:
       # Create radar chart data
       our_scores = []
       benchmark_scores = []

       for category in categories:
           col_name = category.lower().replace(' ', '_')
           if col_name in business_df.columns:
               our_scores.append(business_df[col_name].mean())
               benchmark_scores.append(benchmark_df[col_name].mean() if col_name in benchmark_df.columns else our_scores[-1] * 0.9)
           else:
               our_scores.append(0)
               benchmark_scores.append(0)

       # Polar plot simulation using regular plot
       angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
       our_scores += our_scores[:1]  # Complete the circle
       benchmark_scores += benchmark_scores[:1]
       angles += angles[:1]

       axes[0,1].plot(angles, our_scores, 'o-', linewidth=2, label='Our Performance')
       axes[0,1].fill(angles, our_scores, alpha=0.25)
       axes[0,1].plot(angles, benchmark_scores, 'o-', linewidth=2, label='Industry Average')
       axes[0,1].fill(angles, benchmark_scores, alpha=0.25)
       axes[0,1].set_title('Performance Radar')
       axes[0,1].legend()

   # Trend comparison
   if 'date' in business_df.columns:
       business_df['date'] = pd.to_datetime(business_df['date'])
       monthly_data = business_df.groupby('date').agg({
           'revenue': 'sum',
           'customers': 'sum' if 'customers' in business_df.columns else 'count'
       }).reset_index()

       ax2_twin = axes[1,0].twinx()
       line1 = axes[1,0].plot(monthly_data['date'], monthly_data['revenue'],
                             'b-', label='Revenue')
       line2 = ax2_twin.plot(monthly_data['date'], monthly_data['customers'],
                            'r--', label='Customers')

       axes[1,0].set_xlabel('Date')
       axes[1,0].set_ylabel('Revenue', color='b')
       ax2_twin.set_ylabel('Customers', color='r')
       axes[1,0].set_title('Revenue and Customer Trends')

       # Combine legends
       lines = line1 + line2
       labels = [l.get_label() for l in lines]
       axes[1,0].legend(lines, labels, loc='upper left')

   # ROI and efficiency analysis
   if 'investment' in business_df.columns and 'return' in business_df.columns:
       business_df['roi'] = (business_df['return'] - business_df['investment']) / business_df['investment'] * 100

       # Box plot of ROI by category
       if 'category' in business_df.columns:
           categories = business_df['category'].unique()
           roi_by_category = [business_df[business_df['category']==cat]['roi'].values for cat in categories]
           axes[1,1].boxplot(roi_by_category, labels=categories)
           axes[1,1].set_title('ROI Distribution by Category')
           axes[1,1].set_ylabel('ROI (%)')
           plt.setp(axes[1,1].get_xticklabels(), rotation=45)

   plt.tight_layout()
   plt.savefig('competitive_analysis.png', dpi=300, bbox_inches='tight')
   plt.show()
   ```

   ## Current Market Context Research

   Research current market trends and industry benchmarks:
   - Industry performance metrics and KPIs
   - Recent market shifts and opportunities
   - Competitive landscape changes
   - Economic factors affecting performance

   ## Visualization Insights Summary

   ```python
   print("=== VISUALIZATION INSIGHTS ===")

   # Generate summary statistics for each visualization
   print("Dashboard Summary:")
   if 'revenue' in business_df.columns:
       total_revenue = business_df['revenue'].sum()
       avg_monthly_revenue = business_df.groupby('date')['revenue'].sum().mean() if 'date' in business_df.columns else business_df['revenue'].mean()
       print(f"  Total Revenue: ${total_revenue:,.2f}")
       print(f"  Average Monthly Revenue: ${avg_monthly_revenue:,.2f}")

   print("\nPerformance vs Benchmark:")
   if 'metric' in business_df.columns and 'value' in business_df.columns:
       our_avg = business_df['value'].mean()
       benchmark_avg = benchmark_df['value'].mean() if 'value' in benchmark_df.columns else 0
       performance_ratio = our_avg / benchmark_avg if benchmark_avg > 0 else 1
       print(f"  Our Average Performance: {our_avg:.2f}")
       print(f"  Industry Average: {benchmark_avg:.2f}")
       print(f"  Performance Ratio: {performance_ratio:.2f}x")

   print("\nVisualization files generated:")
   print("  - business_dashboard.html (Interactive dashboard)")
   print("  - competitive_analysis.png (Static analysis charts)")
   ```

Data Science Schema Templates
=============================

Ready-to-use JSON schema templates for common data science workflows. These schemas ensure consistent, validated outputs across different analysis types and can be easily customized for specific use cases.

## Schema Template Library

### 1. Comprehensive Data Analysis Schema

**Use Case**: Complete dataset analysis with statistics, patterns, and recommendations

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "analysis_metadata": {
         "type": "object",
         "properties": {
           "dataset_name": {"type": "string", "description": "Name of the analyzed dataset"},
           "analysis_date": {"type": "string", "format": "date-time"},
           "analyst": {"type": "string", "description": "Name or ID of the analyst"},
           "analysis_type": {"type": "string", "enum": ["exploratory", "confirmatory", "descriptive", "predictive"]},
           "model_used": {"type": "string", "description": "OpenAI model used for analysis"}
         },
         "required": ["dataset_name", "analysis_date", "analysis_type"]
       },
       "dataset_summary": {
         "type": "object",
         "properties": {
           "rows": {"type": "integer", "minimum": 0},
           "columns": {"type": "integer", "minimum": 0},
           "missing_values": {"type": "integer", "minimum": 0},
           "data_types": {
             "type": "object",
             "additionalProperties": {"type": "string"}
           },
           "memory_usage": {"type": "string", "description": "Memory usage in MB/GB"},
           "date_range": {
             "type": "object",
             "properties": {
               "start_date": {"type": "string", "format": "date"},
               "end_date": {"type": "string", "format": "date"}
             }
           }
         },
         "required": ["rows", "columns"]
       },
       "statistical_analysis": {
         "type": "object",
         "properties": {
           "descriptive_stats": {
             "type": "object",
             "patternProperties": {
               "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                 "type": "object",
                 "properties": {
                   "count": {"type": "number"},
                   "mean": {"type": "number"},
                   "median": {"type": "number"},
                   "std": {"type": "number"},
                   "min": {"type": "number"},
                   "max": {"type": "number"},
                   "q25": {"type": "number"},
                   "q75": {"type": "number"},
                   "skewness": {"type": "number"},
                   "kurtosis": {"type": "number"}
                 },
                 "required": ["count", "mean", "std"]
               }
             }
           },
           "correlations": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "variable_1": {"type": "string"},
                 "variable_2": {"type": "string"},
                 "correlation_coefficient": {"type": "number", "minimum": -1, "maximum": 1},
                 "p_value": {"type": "number", "minimum": 0, "maximum": 1},
                 "significance_level": {"type": "string", "enum": ["***", "**", "*", "ns"]},
                 "interpretation": {"type": "string"}
               },
               "required": ["variable_1", "variable_2", "correlation_coefficient"]
             }
           },
           "hypothesis_tests": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "test_name": {"type": "string"},
                 "variables": {"type": "array", "items": {"type": "string"}},
                 "statistic": {"type": "number"},
                 "p_value": {"type": "number", "minimum": 0, "maximum": 1},
                 "degrees_of_freedom": {"type": "integer", "minimum": 0},
                 "effect_size": {"type": "number"},
                 "confidence_interval": {
                   "type": "object",
                   "properties": {
                     "lower": {"type": "number"},
                     "upper": {"type": "number"},
                     "confidence_level": {"type": "number", "default": 0.95}
                   }
                 },
                 "conclusion": {"type": "string"},
                 "interpretation": {"type": "string"}
               },
               "required": ["test_name", "p_value", "conclusion"]
             }
           }
         }
       },
       "patterns_and_insights": {
         "type": "object",
         "properties": {
           "key_patterns": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "pattern": {"type": "string"},
                 "variables_involved": {"type": "array", "items": {"type": "string"}},
                 "strength": {"type": "string", "enum": ["weak", "moderate", "strong"]},
                 "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                 "business_impact": {"type": "string"}
               }
             }
           },
           "anomalies": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "type": {"type": "string", "enum": ["outlier", "missing_data", "inconsistency", "trend_break"]},
                 "description": {"type": "string"},
                 "affected_variables": {"type": "array", "items": {"type": "string"}},
                 "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                 "recommended_action": {"type": "string"}
               }
             }
           },
           "trends": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "variable": {"type": "string"},
                 "trend_type": {"type": "string", "enum": ["increasing", "decreasing", "seasonal", "cyclical", "stable"]},
                 "strength": {"type": "number", "minimum": 0, "maximum": 1},
                 "time_period": {"type": "string"},
                 "forecast": {"type": "string"}
               }
             }
           }
         }
       },
       "recommendations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "category": {"type": "string", "enum": ["data_quality", "analysis", "business_action", "further_investigation"]},
             "recommendation": {"type": "string"},
             "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
             "rationale": {"type": "string"},
             "expected_impact": {"type": "string"},
             "effort_required": {"type": "string", "enum": ["minimal", "moderate", "significant"]},
             "timeline": {"type": "string"}
           },
           "required": ["recommendation", "priority", "rationale"]
         }
       }
     },
     "required": ["analysis_metadata", "dataset_summary", "statistical_analysis", "patterns_and_insights", "recommendations"]
   }

### 2. Advanced Visualization Schema

**Use Case**: Comprehensive visualization specifications with business context

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "visualization_suite": {
         "type": "object",
         "properties": {
           "title": {"type": "string"},
           "description": {"type": "string"},
           "created_date": {"type": "string", "format": "date-time"},
           "data_source": {"type": "string"},
           "target_audience": {"type": "string", "enum": ["technical", "business", "executive", "general"]}
         }
       },
       "visualizations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "id": {"type": "string"},
             "type": {
               "type": "string",
               "enum": ["line", "bar", "scatter", "histogram", "box", "heatmap", "pie", "area", "radar", "bubble", "treemap", "waterfall", "funnel", "gauge", "sankey"]
             },
             "title": {"type": "string"},
             "subtitle": {"type": "string"},
             "data_specification": {
               "type": "object",
               "properties": {
                 "x_axis": {
                   "type": "object",
                   "properties": {
                     "variable": {"type": "string"},
                     "label": {"type": "string"},
                     "data_type": {"type": "string", "enum": ["categorical", "numerical", "datetime"]},
                     "format": {"type": "string"}
                   }
                 },
                 "y_axis": {
                   "type": "object",
                   "properties": {
                     "variable": {"type": "string"},
                     "label": {"type": "string"},
                     "data_type": {"type": "string", "enum": ["categorical", "numerical", "datetime"]},
                     "format": {"type": "string"}
                   }
                 },
                 "color_by": {"type": "string"},
                 "size_by": {"type": "string"},
                 "filters": {
                   "type": "array",
                   "items": {
                     "type": "object",
                     "properties": {
                       "variable": {"type": "string"},
                       "condition": {"type": "string"},
                       "value": {"type": ["string", "number", "array"]}
                     }
                   }
                 },
                 "aggregation": {
                   "type": "object",
                   "properties": {
                     "method": {"type": "string", "enum": ["sum", "mean", "median", "count", "min", "max", "std"]},
                     "group_by": {"type": "array", "items": {"type": "string"}}
                   }
                 }
               }
             },
             "styling": {
               "type": "object",
               "properties": {
                 "color_palette": {"type": "string"},
                 "theme": {"type": "string", "enum": ["light", "dark", "corporate", "minimal"]},
                 "width": {"type": "integer"},
                 "height": {"type": "integer"},
                 "interactive": {"type": "boolean"},
                 "annotations": {
                   "type": "array",
                   "items": {
                     "type": "object",
                     "properties": {
                       "type": {"type": "string", "enum": ["text", "arrow", "line", "rectangle"]},
                       "text": {"type": "string"},
                       "position": {"type": "object"},
                       "style": {"type": "object"}
                     }
                   }
                 }
               }
             },
             "insights": {
               "type": "array",
               "items": {
                 "type": "object",
                 "properties": {
                   "insight": {"type": "string"},
                   "type": {"type": "string", "enum": ["trend", "anomaly", "comparison", "distribution", "correlation"]},
                   "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                   "business_relevance": {"type": "string"}
                 }
               }
             },
             "implementation": {
               "type": "object",
               "properties": {
                 "python_code": {"type": "string"},
                 "libraries_required": {"type": "array", "items": {"type": "string"}},
                 "file_outputs": {"type": "array", "items": {"type": "string"}},
                 "estimated_runtime": {"type": "string"}
               }
             }
           },
           "required": ["type", "title", "data_specification"]
         }
       },
       "dashboard_layout": {
         "type": "object",
         "properties": {
           "grid_layout": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "visualization_id": {"type": "string"},
                 "row": {"type": "integer"},
                 "column": {"type": "integer"},
                 "width": {"type": "integer"},
                 "height": {"type": "integer"}
               }
             }
           },
           "narrative_flow": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "section": {"type": "string"},
                 "description": {"type": "string"},
                 "visualizations": {"type": "array", "items": {"type": "string"}},
                 "key_message": {"type": "string"}
               }
             }
           }
         }
       }
     },
     "required": ["visualization_suite", "visualizations"]
   }

### 3. Research Synthesis Schema

**Use Case**: Academic and scientific research synthesis with literature integration

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "research_synthesis": {
         "type": "object",
         "properties": {
           "study_title": {"type": "string"},
           "research_question": {"type": "string"},
           "methodology": {"type": "string"},
           "synthesis_date": {"type": "string", "format": "date-time"},
           "researcher": {"type": "string"}
         },
         "required": ["study_title", "research_question"]
       },
       "literature_review": {
         "type": "object",
         "properties": {
           "sources_analyzed": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "title": {"type": "string"},
                 "authors": {"type": "array", "items": {"type": "string"}},
                 "year": {"type": "integer"},
                 "journal": {"type": "string"},
                 "doi": {"type": "string"},
                 "relevance_score": {"type": "number", "minimum": 1, "maximum": 5},
                 "quality_score": {"type": "number", "minimum": 1, "maximum": 5},
                 "key_findings": {"type": "array", "items": {"type": "string"}}
               }
             }
           },
           "methodological_consensus": {
             "type": "object",
             "properties": {
               "common_approaches": {"type": "array", "items": {"type": "string"}},
               "validated_methods": {"type": "array", "items": {"type": "string"}},
               "methodological_gaps": {"type": "array", "items": {"type": "string"}},
               "best_practices": {"type": "array", "items": {"type": "string"}}
             }
           },
           "theoretical_framework": {
             "type": "object",
             "properties": {
               "established_theories": {"type": "array", "items": {"type": "string"}},
               "emerging_concepts": {"type": "array", "items": {"type": "string"}},
               "contradicting_findings": {"type": "array", "items": {"type": "string"}},
               "research_gaps": {"type": "array", "items": {"type": "string"}}
             }
           }
         }
       },
       "experimental_analysis": {
         "type": "object",
         "properties": {
           "study_design": {
             "type": "object",
             "properties": {
               "type": {"type": "string", "enum": ["experimental", "observational", "cross-sectional", "longitudinal", "case-control", "cohort"]},
               "sample_size": {"type": "integer"},
               "groups": {"type": "array", "items": {"type": "string"}},
               "variables": {
                 "type": "object",
                 "properties": {
                   "independent": {"type": "array", "items": {"type": "string"}},
                   "dependent": {"type": "array", "items": {"type": "string"}},
                   "confounding": {"type": "array", "items": {"type": "string"}}
                 }
               }
             }
           },
           "statistical_results": {
             "type": "object",
             "properties": {
               "primary_outcomes": {
                 "type": "array",
                 "items": {
                   "type": "object",
                   "properties": {
                     "outcome": {"type": "string"},
                     "measurement": {"type": "string"},
                     "result": {"type": "number"},
                     "confidence_interval": {
                       "type": "object",
                       "properties": {
                         "lower": {"type": "number"},
                         "upper": {"type": "number"},
                         "level": {"type": "number", "default": 0.95}
                       }
                     },
                     "p_value": {"type": "number"},
                     "effect_size": {"type": "number"},
                     "clinical_significance": {"type": "string"}
                   }
                 }
               },
               "secondary_outcomes": {
                 "type": "array",
                 "items": {
                   "type": "object",
                   "properties": {
                     "outcome": {"type": "string"},
                     "result": {"type": "number"},
                     "significance": {"type": "string"}
                   }
                 }
               },
               "subgroup_analyses": {
                 "type": "array",
                 "items": {
                   "type": "object",
                   "properties": {
                     "subgroup": {"type": "string"},
                     "results": {"type": "object"},
                     "interaction_p_value": {"type": "number"}
                   }
                 }
               }
             }
           }
         }
       },
       "synthesis_conclusions": {
         "type": "object",
         "properties": {
           "key_findings": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "finding": {"type": "string"},
                 "evidence_strength": {"type": "string", "enum": ["weak", "moderate", "strong", "very_strong"]},
                 "consistency_across_studies": {"type": "string", "enum": ["inconsistent", "somewhat_consistent", "consistent"]},
                 "literature_support": {"type": "string"},
                 "novel_contribution": {"type": "boolean"}
               }
             }
           },
           "limitations": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "limitation": {"type": "string"},
                 "impact": {"type": "string", "enum": ["minor", "moderate", "major"]},
                 "mitigation": {"type": "string"}
               }
             }
           },
           "implications": {
             "type": "object",
             "properties": {
               "theoretical": {"type": "array", "items": {"type": "string"}},
               "practical": {"type": "array", "items": {"type": "string"}},
               "clinical": {"type": "array", "items": {"type": "string"}},
               "policy": {"type": "array", "items": {"type": "string"}}
             }
           },
           "future_research": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "direction": {"type": "string"},
                 "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                 "methodology": {"type": "string"},
                 "expected_impact": {"type": "string"}
               }
             }
           }
         }
       }
     },
     "required": ["research_synthesis", "synthesis_conclusions"]
   }

### 4. Business Intelligence Schema

**Use Case**: Market analysis and business intelligence reporting

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "business_intelligence_report": {
         "type": "object",
         "properties": {
           "report_title": {"type": "string"},
           "analysis_period": {
             "type": "object",
             "properties": {
               "start_date": {"type": "string", "format": "date"},
               "end_date": {"type": "string", "format": "date"}
             }
           },
           "analyst": {"type": "string"},
           "report_date": {"type": "string", "format": "date-time"},
           "executive_summary": {"type": "string"},
           "key_metrics": {
             "type": "object",
             "patternProperties": {
               "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                 "type": "object",
                 "properties": {
                   "value": {"type": "number"},
                   "unit": {"type": "string"},
                   "change_from_previous": {"type": "number"},
                   "trend": {"type": "string", "enum": ["increasing", "decreasing", "stable"]},
                   "target": {"type": "number"},
                   "performance_vs_target": {"type": "string"}
                 }
               }
             }
           }
         },
         "required": ["report_title", "analysis_period", "executive_summary"]
       },
       "market_analysis": {
         "type": "object",
         "properties": {
           "market_size": {
             "type": "object",
             "properties": {
               "total_addressable_market": {"type": "number"},
               "serviceable_addressable_market": {"type": "number"},
               "serviceable_obtainable_market": {"type": "number"},
               "currency": {"type": "string", "default": "USD"},
               "growth_rate": {"type": "number"},
               "forecast_period": {"type": "string"}
             }
           },
           "competitive_landscape": {
             "type": "object",
             "properties": {
               "market_leaders": {
                 "type": "array",
                 "items": {
                   "type": "object",
                   "properties": {
                     "company": {"type": "string"},
                     "market_share": {"type": "number", "minimum": 0, "maximum": 100},
                     "strengths": {"type": "array", "items": {"type": "string"}},
                     "weaknesses": {"type": "array", "items": {"type": "string"}},
                     "recent_developments": {"type": "array", "items": {"type": "string"}}
                   }
                 }
               },
               "our_position": {
                 "type": "object",
                 "properties": {
                   "market_share": {"type": "number"},
                   "rank": {"type": "integer"},
                   "competitive_advantages": {"type": "array", "items": {"type": "string"}},
                   "areas_for_improvement": {"type": "array", "items": {"type": "string"}}
                 }
               }
             }
           },
           "market_trends": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "trend": {"type": "string"},
                 "impact": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                 "magnitude": {"type": "string", "enum": ["low", "medium", "high"]},
                 "timeline": {"type": "string"},
                 "implications": {"type": "string"}
               }
             }
           },
           "customer_insights": {
             "type": "object",
             "properties": {
               "segments": {
                 "type": "array",
                 "items": {
                   "type": "object",
                   "properties": {
                     "segment_name": {"type": "string"},
                     "size": {"type": "number"},
                     "growth_rate": {"type": "number"},
                     "key_characteristics": {"type": "array", "items": {"type": "string"}},
                     "pain_points": {"type": "array", "items": {"type": "string"}},
                     "preferences": {"type": "array", "items": {"type": "string"}}
                   }
                 }
               },
               "behavior_changes": {
                 "type": "array",
                 "items": {
                   "type": "object",
                   "properties": {
                     "change": {"type": "string"},
                     "drivers": {"type": "array", "items": {"type": "string"}},
                     "business_impact": {"type": "string"}
                   }
                 }
               }
             }
           }
         }
       },
       "performance_analysis": {
         "type": "object",
         "properties": {
           "financial_performance": {
             "type": "object",
             "properties": {
               "revenue": {
                 "type": "object",
                 "properties": {
                   "current_period": {"type": "number"},
                   "previous_period": {"type": "number"},
                   "year_over_year_growth": {"type": "number"},
                   "by_segment": {"type": "object"},
                   "by_geography": {"type": "object"}
                 }
               },
               "profitability": {
                 "type": "object",
                 "properties": {
                   "gross_margin": {"type": "number"},
                   "operating_margin": {"type": "number"},
                   "net_margin": {"type": "number"},
                   "margin_trends": {"type": "array", "items": {"type": "string"}}
                 }
               },
               "key_ratios": {
                 "type": "object",
                 "properties": {
                   "current_ratio": {"type": "number"},
                   "debt_to_equity": {"type": "number"},
                   "return_on_assets": {"type": "number"},
                   "return_on_equity": {"type": "number"}
                 }
               }
             }
           },
           "operational_performance": {
             "type": "object",
             "properties": {
               "efficiency_metrics": {"type": "object"},
               "quality_metrics": {"type": "object"},
               "customer_satisfaction": {"type": "object"},
               "employee_metrics": {"type": "object"}
             }
           }
         }
       },
       "strategic_recommendations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "category": {"type": "string", "enum": ["growth", "efficiency", "competitive", "innovation", "risk_mitigation"]},
             "recommendation": {"type": "string"},
             "rationale": {"type": "string"},
             "expected_impact": {"type": "string"},
             "implementation_timeline": {"type": "string"},
             "resources_required": {"type": "string"},
             "success_metrics": {"type": "array", "items": {"type": "string"}},
             "risks": {"type": "array", "items": {"type": "string"}},
             "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
           },
           "required": ["recommendation", "rationale", "priority"]
         }
       },
       "risk_assessment": {
         "type": "object",
         "properties": {
           "identified_risks": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "risk": {"type": "string"},
                 "category": {"type": "string", "enum": ["market", "operational", "financial", "regulatory", "technological", "competitive"]},
                 "probability": {"type": "string", "enum": ["low", "medium", "high"]},
                 "impact": {"type": "string", "enum": ["low", "medium", "high"]},
                 "mitigation_strategies": {"type": "array", "items": {"type": "string"}},
                 "monitoring_indicators": {"type": "array", "items": {"type": "string"}}
               }
             }
           },
           "risk_matrix": {
             "type": "object",
             "properties": {
               "high_probability_high_impact": {"type": "array", "items": {"type": "string"}},
               "high_probability_low_impact": {"type": "array", "items": {"type": "string"}},
               "low_probability_high_impact": {"type": "array", "items": {"type": "string"}},
               "low_probability_low_impact": {"type": "array", "items": {"type": "string"}}
             }
           }
         }
       }
     },
     "required": ["business_intelligence_report", "strategic_recommendations"]
   }

### 5. Quick Analysis Schema

**Use Case**: Rapid analysis with essential insights (lightweight version)

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "quick_analysis": {
         "type": "object",
         "properties": {
           "dataset": {"type": "string"},
           "analysis_date": {"type": "string", "format": "date-time"},
           "key_metrics": {"type": "object"},
           "top_insights": {
             "type": "array",
             "maxItems": 5,
             "items": {"type": "string"}
           },
           "red_flags": {
             "type": "array",
             "maxItems": 3,
             "items": {"type": "string"}
           },
           "immediate_actions": {
             "type": "array",
             "maxItems": 3,
             "items": {"type": "string"}
           }
         },
         "required": ["dataset", "top_insights"]
       }
     }
   }

## Schema Usage Guidelines

### Customization Tips

1. **Remove unnecessary fields** for simpler analyses
2. **Add domain-specific properties** (e.g., medical, financial, engineering fields)
3. **Adjust enum values** to match your business terminology
4. **Modify validation rules** (min/max values, required fields) based on your data

### Schema Selection Guide

- **Comprehensive Data Analysis**: Full statistical analysis with business context
- **Advanced Visualization**: Complex dashboards and chart specifications
- **Research Synthesis**: Academic or scientific research projects
- **Business Intelligence**: Market analysis and strategic planning
- **Quick Analysis**: Rapid insights for daily operations

### Best Practices

1. **Always include metadata** (analyst, date, data source) for traceability
2. **Use consistent field naming** across your organization's schemas
3. **Include confidence levels** for insights and recommendations
4. **Provide clear descriptions** in schema properties for AI model understanding
5. **Validate outputs** against schemas to ensure consistency

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

Practical Examples and Use Cases
===================================

This section provides complete, real-world workflows demonstrating ostruct's power for data science applications.

Financial Data Analysis Workflow
---------------------------------

**Scenario:** Automated quarterly financial analysis combining market data, company reports, and regulatory filings.

**Complete Workflow:**

**Step 1: Market Data Collection and Analysis**

.. code-block:: bash

   # Template: financial_analysis.j2
   ostruct run financial_analysis.j2 financial_schema.json \
     --file ci:data quarterly_data.xlsx \
     --enable-tool web-search \
     --web-query "{{company_name}} Q3 2024 earnings market reaction analysis" \
     --model gpt-4o

**Template (financial_analysis.j2):**

.. code-block:: jinja

   ## Financial Analysis for {{company_name}} - {{quarter}}

   ### Market Data Analysis
   Analyze the following financial data and provide comprehensive insights:

   **Raw Data:**
   {{ quarterly_data.content }}

   **Market Context (from web search):**
   {% if web_search_results %}
   {{ web_search_results }}
   {% endif %}

   ### Analysis Requirements:
   1. **Performance Metrics**: Calculate key ratios (ROE, EBITDA margin, debt-to-equity)
   2. **Trend Analysis**: Compare with previous 4 quarters
   3. **Market Position**: Benchmark against industry peers
   4. **Risk Assessment**: Identify potential financial risks
   5. **Growth Projection**: Forecast next quarter based on current trends

   ### Regulatory Compliance Check:
   Review all metrics against SEC disclosure requirements and flag any concerning trends.

**Schema (financial_schema.json):**

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "executive_summary": {
         "type": "string",
         "description": "2-3 sentence summary of financial health"
       },
       "key_metrics": {
         "type": "object",
         "properties": {
           "revenue": {"type": "number"},
           "net_income": {"type": "number"},
           "roe": {"type": "number"},
           "ebitda_margin": {"type": "number"},
           "debt_to_equity": {"type": "number"}
         },
         "required": ["revenue", "net_income", "roe"]
       },
       "trend_analysis": {
         "type": "object",
         "properties": {
           "revenue_growth": {"type": "number"},
           "profit_margin_trend": {"type": "string"},
           "quarter_over_quarter_change": {"type": "number"}
         }
       },
       "risk_factors": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "risk_type": {"type": "string"},
             "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
             "description": {"type": "string"},
             "mitigation_suggestions": {"type": "string"}
           },
           "required": ["risk_type", "severity", "description"]
         }
       },
       "growth_forecast": {
         "type": "object",
         "properties": {
           "next_quarter_revenue_estimate": {"type": "number"},
           "confidence_level": {"type": "string", "enum": ["low", "medium", "high"]},
           "key_assumptions": {"type": "array", "items": {"type": "string"}}
         }
       },
       "compliance_flags": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "regulation": {"type": "string"},
             "status": {"type": "string", "enum": ["compliant", "attention_required", "violation"]},
             "details": {"type": "string"}
           }
         }
       }
     },
     "required": ["executive_summary", "key_metrics", "risk_factors"]
   }

**Step 2: Report Generation and Visualization**

.. code-block:: bash

   # Generate presentation-ready report
   ostruct run financial_report.j2 report_schema.json \
     --file prompt:previous_analysis results.json \
     --enable-tool code-interpreter \
     --model gpt-4o

Scientific Research Synthesis
-----------------------------

**Scenario:** Automated literature review combining research papers, recent publications, and domain expert opinions.

**Complete Workflow:**

**Step 1: Multi-Source Research Collection**

.. code-block:: bash

   # Combine local papers with latest research
   ostruct run research_synthesis.j2 research_schema.json \
     --file fs:papers research_papers/ \
     --enable-tool web-search \
     --web-query "{{research_topic}} 2024 latest findings systematic review" \
     --model o1-preview

**Template (research_synthesis.j2):**

.. code-block:: jinja

   ## Comprehensive Research Synthesis: {{research_topic}}

   ### Local Research Papers Analysis
   {% for paper in research_papers %}
   **Paper:** {{ paper.name }}
   **Content:** {{ paper.content if paper.size < 50000 else "Large paper - analyze key sections" }}
   {% endfor %}

   ### Latest Web Research
   {% if web_search_results %}
   **Recent Findings:**
   {{ web_search_results }}
   {% endif %}

   ### Synthesis Requirements:
   1. **Literature Gap Analysis**: Identify research gaps and contradictions
   2. **Methodology Comparison**: Compare approaches across studies
   3. **Evidence Quality Assessment**: Rate evidence strength using GRADE criteria
   4. **Emerging Trends**: Identify novel approaches and future directions
   5. **Practical Applications**: Translate findings to actionable insights

   ### Meta-Analysis Elements:
   - Sample sizes and statistical power across studies
   - Effect sizes and confidence intervals
   - Heterogeneity assessment
   - Publication bias evaluation

**Schema (research_schema.json):**

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "research_summary": {
         "type": "string",
         "description": "Comprehensive 3-4 sentence summary of current state"
       },
       "key_findings": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "finding": {"type": "string"},
             "evidence_level": {"type": "string", "enum": ["strong", "moderate", "weak", "insufficient"]},
             "supporting_studies": {"type": "array", "items": {"type": "string"}},
             "contradictory_evidence": {"type": "array", "items": {"type": "string"}}
           },
           "required": ["finding", "evidence_level"]
         }
       },
       "methodology_analysis": {
         "type": "object",
         "properties": {
           "dominant_approaches": {"type": "array", "items": {"type": "string"}},
           "emerging_methods": {"type": "array", "items": {"type": "string"}},
           "methodological_limitations": {"type": "array", "items": {"type": "string"}}
         }
       },
       "research_gaps": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "gap_description": {"type": "string"},
             "importance": {"type": "string", "enum": ["critical", "important", "moderate", "minor"]},
             "suggested_approaches": {"type": "array", "items": {"type": "string"}}
           },
           "required": ["gap_description", "importance"]
         }
       },
       "practical_implications": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "domain": {"type": "string"},
             "implication": {"type": "string"},
             "confidence_level": {"type": "string", "enum": ["high", "medium", "low"]},
             "implementation_complexity": {"type": "string", "enum": ["simple", "moderate", "complex"]}
           }
         }
       },
       "future_directions": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "direction": {"type": "string"},
             "priority": {"type": "string", "enum": ["high", "medium", "low"]},
             "feasibility": {"type": "string", "enum": ["high", "medium", "low"]},
             "potential_impact": {"type": "string", "enum": ["transformative", "significant", "incremental"]}
           }
         }
       }
     },
     "required": ["research_summary", "key_findings", "research_gaps"]
   }

Business Intelligence Report Generation
---------------------------------------

**Scenario:** Automated competitive analysis combining internal sales data, market reports, and real-time competitor monitoring.

**Complete Workflow:**

**Step 1: Multi-Source Business Intelligence**

.. code-block:: bash

   # Comprehensive competitive analysis
   ostruct run bi_analysis.j2 bi_schema.json \
     --file ci:data sales_data.xlsx \
     --file fs:reports market_reports/ \
     --enable-tool web-search \
     --web-query "{{competitor_name}} Q4 2024 market share pricing strategy" \
     --model gpt-4o

**Template (bi_analysis.j2):**

.. code-block:: jinja

   ## Business Intelligence Report - {{analysis_period}}

   ### Internal Performance Analysis
   **Sales Data:**
   {{ sales_data.content }}

   ### Market Context Analysis
   **Market Reports:**
   {% for report in market_reports %}
   **Report:** {{ report.name }}
   {{ report.content if report.size < 30000 else "Large report - focus on executive summary and key metrics" }}
   {% endfor %}

   ### Competitive Intelligence
   {% if web_search_results %}
   **Latest Competitor Activity:**
   {{ web_search_results }}
   {% endif %}

   ### Analysis Requirements:
   1. **Market Position**: Our position vs competitors across key metrics
   2. **Growth Opportunities**: Untapped segments and expansion possibilities
   3. **Competitive Threats**: Emerging competitors and market disruptions
   4. **Pricing Analysis**: Price positioning and optimization opportunities
   5. **Strategic Recommendations**: Actionable next steps with ROI projections

   ### Executive Briefing Elements:
   - Top 3 strategic priorities
   - Revenue impact projections
   - Resource requirements
   - Timeline for implementation

**Schema (bi_schema.json):**

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "executive_summary": {
         "type": "string",
         "description": "CEO-ready 2-3 sentence summary of strategic position"
       },
       "market_position": {
         "type": "object",
         "properties": {
           "market_share": {"type": "number"},
           "competitive_ranking": {"type": "integer"},
           "differentiation_strengths": {"type": "array", "items": {"type": "string"}},
           "competitive_gaps": {"type": "array", "items": {"type": "string"}}
         }
       },
       "growth_opportunities": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "opportunity": {"type": "string"},
             "market_size": {"type": "number"},
             "revenue_potential": {"type": "number"},
             "time_to_market": {"type": "string"},
             "investment_required": {"type": "number"},
             "risk_level": {"type": "string", "enum": ["low", "medium", "high"]}
           },
           "required": ["opportunity", "revenue_potential", "risk_level"]
         }
       },
       "competitive_threats": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "threat_source": {"type": "string"},
             "threat_type": {"type": "string"},
             "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
             "timeline": {"type": "string"},
             "mitigation_strategies": {"type": "array", "items": {"type": "string"}}
           }
         }
       },
       "strategic_recommendations": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "recommendation": {"type": "string"},
             "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
             "expected_roi": {"type": "number"},
             "implementation_timeline": {"type": "string"},
             "resource_requirements": {"type": "array", "items": {"type": "string"}},
             "success_metrics": {"type": "array", "items": {"type": "string"}}
           },
           "required": ["recommendation", "priority", "expected_roi"]
         }
       },
       "pricing_analysis": {
         "type": "object",
         "properties": {
           "current_positioning": {"type": "string"},
           "competitor_comparison": {"type": "array", "items": {"type": "object"}},
           "optimization_opportunities": {"type": "array", "items": {"type": "string"}},
           "revenue_impact_estimate": {"type": "number"}
         }
       }
     },
     "required": ["executive_summary", "market_position", "growth_opportunities", "strategic_recommendations"]
   }

Market Research Automation
---------------------------

**Scenario:** Automated market entry analysis combining demographic data, competitor landscape, and regulatory environment.

**Complete Workflow:**

**Step 1: Comprehensive Market Entry Analysis**

.. code-block:: bash

   # Complete market entry assessment
   ostruct run market_entry.j2 market_schema.json \
     --file ci:data demographic_data.csv \
     --file fs:docs regulatory_requirements/ \
     --enable-tool web-search \
     --web-query "{{target_market}} {{industry}} market entry barriers regulatory requirements 2024" \
     --model gpt-4o

**Template (market_entry.j2):**

.. code-block:: jinja

   ## Market Entry Analysis: {{target_market}} - {{industry}}

   ### Demographic and Market Data
   **Market Demographics:**
   {{ demographic_data.content }}

   ### Regulatory Environment
   **Regulatory Requirements:**
   {% for doc in regulatory_requirements %}
   **Document:** {{ doc.name }}
   {{ doc.content if doc.size < 40000 else "Large regulatory document - focus on key compliance requirements" }}
   {% endfor %}

   ### Competitive Landscape Research
   {% if web_search_results %}
   **Current Market Intelligence:**
   {{ web_search_results }}
   {% endif %}

   ### Analysis Framework:
   1. **Market Attractiveness**: Size, growth, profitability assessment
   2. **Competitive Intensity**: Porter's Five Forces analysis
   3. **Entry Barriers**: Regulatory, financial, operational obstacles
   4. **Go-to-Market Strategy**: Channel analysis and market penetration approach
   5. **Financial Projections**: Revenue forecasts and investment requirements
   6. **Risk Assessment**: Market, operational, and regulatory risks

   ### Decision Framework:
   Provide clear GO/NO-GO recommendation with supporting rationale and alternative strategies.

**Schema (market_schema.json):**

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "market_attractiveness": {
         "type": "object",
         "properties": {
           "market_size_usd": {"type": "number"},
           "growth_rate": {"type": "number"},
           "profit_margin_potential": {"type": "number"},
           "market_maturity": {"type": "string", "enum": ["emerging", "growth", "mature", "declining"]},
           "attractiveness_score": {"type": "integer", "minimum": 1, "maximum": 10}
         },
         "required": ["market_size_usd", "growth_rate", "attractiveness_score"]
       },
       "competitive_analysis": {
         "type": "object",
         "properties": {
           "market_concentration": {"type": "string", "enum": ["fragmented", "moderate", "concentrated", "monopolistic"]},
           "key_competitors": {
             "type": "array",
             "items": {
               "type": "object",
               "properties": {
                 "company": {"type": "string"},
                 "market_share": {"type": "number"},
                 "competitive_advantages": {"type": "array", "items": {"type": "string"}},
                 "vulnerabilities": {"type": "array", "items": {"type": "string"}}
               }
             }
           },
           "competitive_intensity": {"type": "integer", "minimum": 1, "maximum": 5}
         }
       },
       "entry_barriers": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "barrier_type": {"type": "string"},
             "severity": {"type": "string", "enum": ["low", "medium", "high", "prohibitive"]},
             "description": {"type": "string"},
             "mitigation_strategies": {"type": "array", "items": {"type": "string"}},
             "estimated_cost": {"type": "number"}
           },
           "required": ["barrier_type", "severity", "description"]
         }
       },
       "go_to_market_strategy": {
         "type": "object",
         "properties": {
           "recommended_channels": {"type": "array", "items": {"type": "string"}},
           "market_penetration_approach": {"type": "string"},
           "customer_acquisition_strategy": {"type": "string"},
           "pricing_strategy": {"type": "string"},
           "marketing_budget_estimate": {"type": "number"}
         }
       },
       "financial_projections": {
         "type": "object",
         "properties": {
           "year_1_revenue": {"type": "number"},
           "year_3_revenue": {"type": "number"},
           "break_even_timeline": {"type": "string"},
           "initial_investment_required": {"type": "number"},
           "roi_projection": {"type": "number"}
         },
         "required": ["year_1_revenue", "initial_investment_required"]
       },
       "risk_assessment": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "risk_category": {"type": "string"},
             "risk_description": {"type": "string"},
             "likelihood": {"type": "string", "enum": ["low", "medium", "high"]},
             "impact": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
             "mitigation_plan": {"type": "string"}
           }
         }
       },
       "recommendation": {
         "type": "object",
         "properties": {
           "decision": {"type": "string", "enum": ["go", "no_go", "conditional_go", "delayed_entry"]},
           "confidence_level": {"type": "string", "enum": ["low", "medium", "high"]},
           "key_rationale": {"type": "array", "items": {"type": "string"}},
           "next_steps": {"type": "array", "items": {"type": "string"}},
           "alternative_strategies": {"type": "array", "items": {"type": "string"}}
         },
         "required": ["decision", "confidence_level", "key_rationale"]
       }
     },
     "required": ["market_attractiveness", "competitive_analysis", "entry_barriers", "recommendation"]
   }

**Step 2: Action Plan Generation**

.. code-block:: bash

   # Generate implementation roadmap
   ostruct run implementation_plan.j2 plan_schema.json \
     --file prompt:analysis market_entry_results.json \
     --model gpt-4o

Best Practices for Complex Workflows
-------------------------------------

**Template Design Principles:**

1. **Structured Instructions**: Provide clear, numbered requirements
2. **Context Awareness**: Handle missing data gracefully
3. **Progressive Disclosure**: Start broad, then drill into specifics
4. **Error Resilience**: Include fallback strategies for data issues

**Schema Design Principles:**

1. **Business-Ready Output**: Structure matches decision-making needs
2. **Validation Built-In**: Use enums and constraints for data quality
3. **Extensible Design**: Allow for future requirement additions
4. **Confidence Indicators**: Include certainty levels for AI outputs

**Workflow Orchestration:**

1. **Multi-Stage Processing**: Break complex analysis into digestible stages
2. **Tool Selection**: Match tool capabilities to data types and complexity
3. **Quality Gates**: Validate intermediate outputs before final processing
4. **Documentation**: Maintain audit trail of analysis steps

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
