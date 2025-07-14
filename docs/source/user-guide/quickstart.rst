Quick Start Guide
=================

Welcome to ostruct! This guide will get you up and running in minutes with a hands-on tutorial featuring Juno the beagle 🐕.

Prerequisites
-------------

- Python 3.10 or higher
- OpenAI API key (get one from the OpenAI Platform)
- ``pip`` or ``poetry`` for installation

Installation
------------

We provide multiple installation methods. For most users, ``pipx`` is recommended as it avoids conflicts with other Python packages.

.. tab-set::

   .. tab-item:: Recommended: pipx

      1. **Install pipx**:

         .. code-block:: bash

            python3 -m pip install --user pipx
            python3 -m pipx ensurepath

         *(Restart your terminal after running ``ensurepath`` to update your ``PATH``)*

      2. **Install ostruct-cli**:

         .. code-block:: bash

            pipx install ostruct-cli

   .. tab-item:: macOS: Homebrew

      If you're on macOS and use Homebrew, you can install `ostruct` with a single command:

      .. code-block:: bash

         brew install yaniv-golan/ostruct/ostruct-cli

   .. tab-item:: Standalone Binaries

      We provide pre-compiled .zip archives for macOS, Windows, and Linux that do not require Python to be installed.

      1. Go to the `Latest Release <https://github.com/yaniv-golan/ostruct/releases/latest>`__ page.
      2. Download the `.zip` file for your operating system (e.g., ``ostruct-macos-latest.zip``, ``ostruct-windows-latest.zip``, ``ostruct-ubuntu-latest.zip``).
      3. Extract the `.zip` file. This will create a folder (e.g., ``ostruct-macos-amd64``).
      4. On macOS/Linux, make the executable inside the extracted folder runnable: ``chmod +x /path/to/ostruct-macos-amd64/ostruct``
      5. Run the executable from within the extracted folder, as it depends on bundled libraries in the same directory.

   .. tab-item:: Docker

      Run ``ostruct`` from our official container image on the GitHub Container Registry.

      .. code-block:: bash

         docker run -it --rm \
           -v "$(pwd)":/app \
           -w /app \
           ghcr.io/yaniv-golan/ostruct:latest \
           run template.j2 schema.json --file input input.txt


Set up your OpenAI API key:

.. code-block:: bash

   # Environment variable
   export OPENAI_API_KEY="your-api-key-here"

   # Or create a .env file
   echo 'OPENAI_API_KEY=your-api-key-here' > .env

Optional Dependencies
---------------------

Enhanced File Type Detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For improved file type detection when using the ``auto`` routing target, install the enhanced-detection package:

.. code-block:: bash

   pip install ostruct-cli[enhanced-detection]

**What it does**: When you use ``--file auto:alias file.txt``, ostruct needs to determine whether files should be routed to the template (for text files) or treated as binary data. Enhanced detection uses machine learning (Magika) for more accurate file type identification.

**Benefits**:

- **More accurate routing**: Better detection of file types beyond simple extensions
- **Handles edge cases**: Correctly identifies files without extensions or with misleading extensions
- **Automatic fallback**: Falls back to extension-based detection if unavailable

**Without enhanced-detection**: ostruct uses extension-based detection for common file types (.txt, .md, .json, .py, .csv, .html, .css, .sql, .sh, .log, .env, and 20+ others).

.. note::
   **Alpine Linux**: Enhanced detection may not install on Alpine Linux due to compilation requirements. ostruct automatically falls back to extension-based detection with a helpful warning message.

Tutorial: Meet Juno the Beagle
-------------------------------

Let's start with a real-world example that showcases ostruct's power. We'll analyze a pet adoption profile and extract structured data.

Step 1: Create the Pet Profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, create a file called ``juno_profile.txt``:

.. code-block:: text

   JUNO - BEAGLE MIX LOOKING FOR HOME

   Meet Juno! This adorable 3-year-old beagle mix is the perfect companion for
   an active family. Juno loves long walks, playing fetch, and snuggling on
   the couch after a day of adventures.

   Personality: Friendly, energetic, loyal, great with kids
   Medical: Fully vaccinated, spayed, microchipped
   Training: House-trained, knows basic commands (sit, stay, come)
   Ideal Home: Active family with a yard, no cats (she gets too excited!)

   Contact the Sunny Valley Animal Shelter to meet Juno today!
   Phone: (555) 123-PETS
   Email: adopt@sunnyvalley.org

Step 2: Define Your Data Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``pet_schema.json`` to specify exactly what information you want to extract:

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "name": {
         "type": "string",
         "description": "Pet's name"
       },
       "breed": {
         "type": "string",
         "description": "Primary breed"
       },
       "age": {
         "type": "integer",
         "description": "Age in years"
       },
       "personality_traits": {
         "type": "array",
         "items": {"type": "string"},
         "description": "Key personality characteristics"
       },
       "medical_status": {
         "type": "object",
         "properties": {
           "vaccinated": {"type": "boolean"},
           "spayed_neutered": {"type": "boolean"},
           "microchipped": {"type": "boolean"}
         },
         "required": ["vaccinated", "spayed_neutered", "microchipped"]
       },
       "training_level": {
         "type": "array",
         "items": {"type": "string"},
         "description": "Training achievements"
       },
       "ideal_home": {
         "type": "string",
         "description": "Description of ideal living situation"
       },
       "contact_info": {
         "type": "object",
         "properties": {
           "organization": {"type": "string"},
           "phone": {"type": "string"},
           "email": {"type": "string"}
         },
         "required": ["organization"]
       }
     },
     "required": ["name", "breed", "age", "personality_traits", "medical_status"]
   }

.. tip::
   **Schema Creation Tool**: Instead of writing schemas manually, use the **Schema Generator** meta-tool to automatically create schemas from your templates:

   .. code-block:: bash

      tools/schema-generator/run.sh -o pet_schema.json analyze_pet.j2

   This tool analyzes your template and generates OpenAI-compliant schemas automatically.

Step 3: Create the Analysis Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``analyze_pet.j2`` to tell the AI how to process the profile:

.. code-block:: text

   ---
   system_prompt: You are an expert pet adoption coordinator who excels at extracting structured information from adoption profiles.
   ---
   Please analyze this pet adoption profile and extract the key information:

   {{ profile.content }}

   Extract the information according to the provided schema, ensuring all medical status fields are boolean values and contact information is properly structured.

.. tip::
   **Pro Tip**: Share system prompts across templates using ``include_system:``:

   .. code-block:: text

      ---
      include_system: shared/pet_expert.txt
      system_prompt: Focus on adoption readiness assessment.
      ---

   See :doc:`template_guide` for advanced shared prompt techniques.

Step 4: Run the Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~

Now use ostruct to extract structured data from Juno's profile:

.. code-block:: bash

   ostruct run analyze_pet.j2 pet_schema.json \
     --file profile juno_profile.txt \
     -m gpt-4o

**Result**: You'll get perfectly structured JSON output like this:

.. code-block:: json

   {
     "name": "Juno",
     "breed": "Beagle Mix",
     "age": 3,
     "personality_traits": ["Friendly", "Energetic", "Loyal", "Great with kids"],
     "medical_status": {
       "vaccinated": true,
       "spayed_neutered": true,
       "microchipped": true
     },
     "training_level": ["House-trained", "Basic commands (sit, stay, come)"],
     "ideal_home": "Active family with a yard, no cats",
     "contact_info": {
       "organization": "Sunny Valley Animal Shelter",
       "phone": "(555) 123-PETS",
       "email": "adopt@sunnyvalley.org"
     }
   }

Understanding What Happened
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's break down the magic:

1. **File Attachment**: ``--file profile juno_profile.txt`` attached the text file to template with custom alias
2. **Template Processing**: The ``.j2`` template combined the profile content with instructions
3. **Schema Validation**: The JSON schema ensured the output matched your exact requirements
4. **AI Intelligence**: GPT-4o understood the context and extracted the right information

Development Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Always validate with --dry-run first:**

Before running any ostruct command for real, validate your template and files:

.. code-block:: bash

   # 1. Validate everything first - catches errors early
   ostruct run analyze_pet.j2 pet_schema.json \
     --file profile juno_profile.txt \
     --dry-run

   # 2. If validation passes, run for real
   ostruct run analyze_pet.j2 pet_schema.json \
     --file profile juno_profile.txt \
     -m gpt-4o

The ``--dry-run`` flag performs comprehensive validation including:

- Template syntax checking
- File access validation (catches binary file issues)
- Schema structure validation
- Security constraint verification

**This saves time and API costs by catching errors before making OpenAI API calls.**

Level Up: Multi-Tool Processing
--------------------------------

Ready for more power? Let's process multiple data sources with different tools.

Advanced Example: Pet Medical Records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``medical_data.csv``:

.. code-block:: text

   Date,Procedure,Veterinarian,Notes
   2024-01-15,Annual Exam,Dr. Sarah Chen,Healthy weight maintained
   2024-01-15,Vaccination Update,Dr. Sarah Chen,DHPP and Rabies boosters
   2024-02-20,Spay Surgery,Dr. Michael Torres,Procedure successful
   2024-03-10,Microchip Implant,Dr. Sarah Chen,Chip ID: 982000123456789

Create ``comprehensive_analysis.j2``:

.. code-block:: text

   ---
   system_prompt: You are a veterinary data analyst specializing in pet health summaries.
   ---
   Analyze this pet's profile and medical history:

   PROFILE:
   {{ profile.content }}

   MEDICAL RECORDS:
   Please analyze the uploaded CSV medical data to extract medical history patterns.

   Provide a comprehensive health and adoption readiness assessment.

Create ``comprehensive_schema.json``:

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "pet_summary": {
         "$ref": "#/$defs/pet_info"
       },
       "medical_summary": {
         "type": "object",
         "properties": {
           "last_exam_date": {"type": "string", "format": "date"},
           "vaccination_status": {"type": "string"},
           "procedures_completed": {
             "type": "array",
             "items": {"type": "string"}
           },
           "health_status": {"type": "string"},
           "microchip_id": {"type": "string"}
         }
       },
       "adoption_readiness": {
         "type": "object",
         "properties": {
           "ready_for_adoption": {"type": "boolean"},
           "recommended_followup": {
             "type": "array",
             "items": {"type": "string"}
           }
         }
       }
     },
     "$defs": {
       "pet_info": {
         "type": "object",
         "properties": {
           "name": {"type": "string"},
           "breed": {"type": "string"},
           "age": {"type": "integer"}
         }
       }
     }
   }

Run the advanced analysis:

.. code-block:: bash

   ostruct run comprehensive_analysis.j2 comprehensive_schema.json \
     --file profile juno_profile.txt \
     --file ci:medical medical_data.csv \
     -m gpt-4o

**What's different?**

- ``--file profile juno_profile.txt``: Profile text for template access with custom alias
- ``--file ci:medical medical_data.csv``: Medical data uploaded to Code Interpreter for analysis
- The AI can now correlate text descriptions with structured data

Three Learning Paths
---------------------

Choose your adventure based on your needs:

🎯 **Quick Integration** (5 minutes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Perfect for developers who need immediate results:

.. code-block:: bash

   # Basic document analysis
   ostruct run template.j2 schema.json --file document document.txt

   # With custom variables
   ostruct run template.j2 schema.json --file doc doc.txt -V env=prod

   # Direct output to file
   ostruct run template.j2 schema.json --file data data.txt --output-file result.json

📊 **Data Processing** (15 minutes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For analysts working with datasets:

.. code-block:: bash

   # Analyze CSV with code execution
   ostruct run analysis.j2 schema.json --file ci:dataset dataset.csv

   # Multi-file processing
   ostruct run process.j2 schema.json --file ci:data1 data1.csv --file ci:data2 data2.csv

   # Directory processing
   ostruct run batch.j2 schema.json --dir ci:data ./data_directory

🔍 **Knowledge Extraction** (30 minutes)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For researchers processing documents:

.. code-block:: bash

   # Semantic search through documents
   ostruct run research.j2 schema.json --file fs:docs documentation.pdf

   # Multi-document research
   ostruct run synthesis.j2 schema.json --dir fs:papers ./research_papers

   # Combined analysis
   ostruct run complete.j2 schema.json \
     --file config config.yaml \
     --file ci:script analysis.py \
     --file fs:knowledge knowledge_base.pdf

Key CLI Patterns to Remember
-----------------------------

**Attachment Syntax**
  - ``--file alias file.txt`` (template access with custom alias)
  - ``--file ci:alias file.txt`` (Code Interpreter with custom alias)
  - ``--file fs:alias file.txt`` (File Search with custom alias)
  - ``--dir alias ./directory`` (directory attachment)
  - ``--collect alias @file-list.txt`` (file collection from list)

**Tool Targeting**
  - ``prompt`` (default): Template access only (configuration, small files)
  - ``code-interpreter`` or ``ci``: Code Interpreter (data analysis, computation)
  - ``file-search`` or ``fs``: File Search (document retrieval, knowledge bases)
  - ``--enable-tool web-search``: Web Search (current events, real-time data)

**Model Options**
  - ``-m gpt-4o`` (default, best for most tasks)
  - ``-m o1`` (complex reasoning, slower)
  - ``-m o3-mini`` (fast and cost-effective)

**Variables**
  - ``-V name=value`` (simple strings)
  - ``-J config='{"env":"prod"}'`` (JSON objects)

**Security**
  - ``--path-security strict`` (enable strict path validation)
  - ``--allow /safe/path`` (allow specific directory)
  - ``--allow-file /specific/file.txt`` (allow specific file)

Next Steps
----------

🎓 **Learn More**
  - :doc:`cli_reference` - Complete CLI documentation
  - :doc:`template_guide` - Comprehensive template techniques
  - :doc:`../security/overview` - Security best practices

🔧 **Integrate**
  - :doc:`../automate/ci_cd_and_containers` - CI/CD integration
