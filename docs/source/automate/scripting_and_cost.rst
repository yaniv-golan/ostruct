Scripting and Cost Control
==========================

Advanced automation patterns for ostruct including batch processing, error handling, monitoring, cost optimization, and integration patterns. Learn how to build robust, cost-effective automation workflows that scale with your needs.

.. note::
   These patterns build on the foundation provided in :doc:`ci_cd_and_containers`. Adapt examples to your specific infrastructure and requirements.

Batch Processing Patterns
=========================

Sequential File Processing
--------------------------

Process multiple files in sequence with comprehensive error handling:

.. code-block:: bash

   #!/bin/bash
   # process_files.sh - Sequential file processor

   set -euo pipefail  # Exit on error, undefined vars, pipe failures

   # Configuration
   TEMPLATE_DIR="./templates"
   SCHEMA_DIR="./schemas"
   INPUT_DIR="./input"
   OUTPUT_DIR="./output"
   TIMEOUT=300

   # Logging setup
   LOG_FILE="./logs/processing_$(date +%Y%m%d_%H%M%S).log"
   mkdir -p "$(dirname "$LOG_FILE")"

   log() {
       echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
   }

   # Process a single file
   process_file() {
       local input_file="$1"
       local template="$2"
       local schema="$3"
       local output_file="$4"

       log "Processing: $input_file -> $output_file"

       if ostruct run "$template" "$schema" \
           --path-security strict --allow "$PWD" \
           --file config "$input_file" \
           --timeout "$TIMEOUT" \
           --output-file "$output_file"; then
           log "SUCCESS: $output_file"
           return 0
       else
           log "ERROR: Failed to process $input_file"
           return 1
       fi
   }

Cost Control and Optimization
=============================

Understanding Costs
-------------------

Choose the appropriate model for your use case:

**gpt-4o-mini**:
- Use for data extraction, classification
- Lower cost, good performance
- Suitable for most structured data tasks

**gpt-4o**:
- Use for large document processing and complex reasoning
- Balance between capability and cost
- Good for most production scenarios

**gpt-4**:
- Use for complex reasoning, code analysis
- Higher accuracy, higher cost
- Best for critical business decisions

Budget Controls
===============

Environment Variables
---------------------

Set spending limits using environment variables:

.. code-block:: bash

   # Daily budget limit (in USD)
   export OPENAI_DAILY_BUDGET=100.00

   # Monthly budget limit
   export OPENAI_MONTHLY_BUDGET=2000.00

   # Token limit per request
   export OPENAI_MAX_TOKENS_PER_REQUEST=2000

Pre-execution Cost Estimation
-----------------------------

Estimate costs before processing:

.. code-block:: bash

   # Dry run to estimate costs
   ostruct --dry-run \
     --file data "data.json" \
     --schema schemas/analysis.json \
     --model gpt-4

Configuration-based Limits
--------------------------

Use configuration files for budget controls:

.. code-block:: yaml

   # ostruct.yaml
   cost_controls:
     daily_limit: 50.00
     request_limit: 1000
     token_limit: 100000
     alert_threshold: 0.8  # Alert at 80% of limit

   models:
     default: gpt-4o-mini
     fallback: gpt-4o-mini  # Fallback if budget exceeded

Template Optimization
---------------------

Design cost-effective templates:

.. code-block:: django

   {# Optimized template #}
   Extract key data from:
   {{ file_content | truncate(2000) }}

   Return JSON with:
   - summary (max 100 words)
   - entities (list)
   - sentiment (positive/negative/neutral)

Schema Design for Cost Control
------------------------------

Use precise schemas to reduce output tokens:

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "summary": {
         "type": "string",
         "maxLength": 500
       },
       "categories": {
         "type": "array",
         "maxItems": 5,
         "items": {"type": "string"}
       }
     },
     "required": ["summary", "categories"],
     "additionalProperties": false
   }

Best Practices Summary
======================

1. **Cost Management**
   - Use appropriate models for each task
   - Implement budget controls and monitoring
   - Optimize templates and schemas
   - Track usage patterns

2. **Efficient Processing**
   - Batch similar tasks together
   - Use parallel processing where beneficial
   - Implement proper error handling
   - Monitor performance metrics

3. **Production Integration**
   - Use configuration files for settings
   - Implement proper logging
   - Set up alerting for issues
   - Test with dry runs before production

This guide provides the foundation for building cost-effective, scalable ostruct automation workflows.
