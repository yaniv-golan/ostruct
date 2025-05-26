==============
Cost Control
==============

This guide covers strategies for managing and optimizing costs when using ostruct in production environments, including token usage monitoring, budget controls, and cost-effective processing patterns.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
========

Cost management is crucial when using AI APIs at scale. ostruct provides several mechanisms to help you monitor, control, and optimize your API usage costs.

Key Cost Factors
================

Token Usage
-----------

The primary cost driver is token consumption:

.. code-block:: yaml

   # High token usage pattern
   model: gpt-4
   max_tokens: 4000
   temperature: 0.7

.. code-block:: yaml

   # Optimized token usage
   model: gpt-3.5-turbo
   max_tokens: 1000
   temperature: 0.3

Model Selection
---------------

Choose the appropriate model for your use case:

**gpt-4**:
- Use for complex reasoning, code analysis
- Higher accuracy, higher cost
- Best for critical business decisions

**gpt-3.5-turbo**:
- Use for data extraction, classification
- Lower cost, good performance
- Suitable for most structured data tasks

**gpt-3.5-turbo-16k**:
- Use for large document processing
- Balance between context and cost
- Good for batch processing scenarios

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
     --files "data/*.json" \
     --schema schemas/analysis.json \
     --model gpt-4

Configuration-based Limits
---------------------------

Use configuration files for budget controls:

.. code-block:: yaml

   # ostruct.yaml
   cost_controls:
     daily_limit: 50.00
     request_limit: 1000
     token_limit: 100000
     alert_threshold: 0.8  # Alert at 80% of limit
     
   models:
     default: gpt-3.5-turbo
     fallback: gpt-3.5-turbo  # Fallback if budget exceeded

Monitoring and Tracking
=======================

Real-time Usage Tracking
------------------------

Monitor usage during execution:

.. code-block:: bash

   # Enable verbose cost tracking
   ostruct --verbose \
     --cost-tracking \
     --files "input/*.txt" \
     --template templates/extract.j2

Usage Logs
----------

Configure detailed usage logging:

.. code-block:: yaml

   # logging.yaml
   version: 1
   loggers:
     ostruct.cost:
       level: INFO
       handlers: [cost_file]
   handlers:
     cost_file:
       class: logging.FileHandler
       filename: logs/cost_tracking.log
       formatter: cost_formatter
   formatters:
     cost_formatter:
       format: '%(asctime)s - %(name)s - Cost: $%(cost)s - Tokens: %(tokens)s'

Cost Reports
------------

Generate detailed cost reports:

.. code-block:: bash

   # Generate daily cost report
   ostruct-cost-report \
     --date $(date +%Y-%m-%d) \
     --format json \
     --output reports/daily_cost.json

   # Generate monthly summary
   ostruct-cost-report \
     --month $(date +%Y-%m) \
     --breakdown-by-model \
     --output reports/monthly_summary.csv

Optimization Strategies
=======================

Batch Processing
----------------

Process multiple items efficiently:

.. code-block:: bash

   # Inefficient: One API call per file
   for file in data/*.json; do
     ostruct --files "$file" --template extract.j2
   done

   # Efficient: Batch processing
   ostruct --files "data/*.json" \
     --template templates/batch_extract.j2 \
     --batch-size 10

Template Optimization
---------------------

Design cost-effective templates:

.. code-block:: django

   {# Inefficient template #}
   Please analyze this document in detail:
   {{ file_content }}
   
   Provide comprehensive analysis including:
   - Detailed summary
   - All mentioned entities
   - Complete sentiment analysis
   - Full topic classification

.. code-block:: django

   {# Optimized template #}
   Extract key data from:
   {{ file_content | truncate(2000) }}
   
   Return JSON with:
   - summary (max 100 words)
   - entities (list)
   - sentiment (positive/negative/neutral)

Schema Design
-------------

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
       },
       "confidence": {
         "type": "number",
         "minimum": 0,
         "maximum": 1
       }
     },
     "required": ["summary", "categories", "confidence"],
     "additionalProperties": false
   }

Caching Strategies
==================

Response Caching
----------------

Cache API responses to avoid duplicate calls:

.. code-block:: yaml

   # ostruct.yaml
   cache:
     enabled: true
     backend: redis
     ttl: 3600  # 1 hour
     key_strategy: content_hash
   
   redis:
     host: localhost
     port: 6379
     db: 0

Semantic Caching
----------------

Cache based on content similarity:

.. code-block:: python

   # Custom cache implementation
   import hashlib
   from ostruct.cache import SemanticCache
   
   cache = SemanticCache(
       similarity_threshold=0.95,
       embedding_model="text-embedding-ada-002"
   )
   
   # Check cache before API call
   cache_key = cache.get_semantic_key(input_text)
   if cache.exists(cache_key):
       return cache.get(cache_key)

Multi-tier Caching
------------------

Implement multiple cache levels:

.. code-block:: yaml

   # Multi-tier cache configuration
   cache:
     levels:
       - type: memory
         max_size: 1000
         ttl: 300
       - type: redis
         ttl: 3600
       - type: disk
         path: /tmp/ostruct_cache
         ttl: 86400

Cost-effective Processing Patterns
==================================

Progressive Enhancement
-----------------------

Start with cheaper models, upgrade as needed:

.. code-block:: bash

   # Stage 1: Basic extraction with gpt-3.5-turbo
   ostruct --model gpt-3.5-turbo \
     --files "data/*.txt" \
     --template basic_extract.j2 \
     --output stage1.json

   # Stage 2: Enhanced analysis for high-value items
   ostruct --model gpt-4 \
     --files "high_value_data.json" \
     --template detailed_analysis.j2 \
     --output stage2.json

Conditional Processing
----------------------

Use smart routing based on content characteristics:

.. code-block:: django

   {# Smart model selection template #}
   {% if file_size > 10000 %}
     {# Use more powerful model for large files #}
     {{ use_model("gpt-4") }}
   {% elif complexity_score > 0.8 %}
     {# Use GPT-4 for complex content #}
     {{ use_model("gpt-4") }}
   {% else %}
     {# Use cost-effective model for simple content #}
     {{ use_model("gpt-3.5-turbo") }}
   {% endif %}

Parallel Processing with Limits
-------------------------------

Process multiple items while respecting rate limits:

.. code-block:: bash

   # Parallel processing with cost controls
   ostruct --files "data/*.json" \
     --template extract.j2 \
     --parallel 5 \
     --rate-limit 60 \
     --cost-limit 10.00

Budget Alerting
===============

Real-time Alerts
----------------

Set up alerts for budget thresholds:

.. code-block:: yaml

   # alerts.yaml
   budget_alerts:
     thresholds: [0.5, 0.8, 0.9, 0.95]
     channels:
       - type: email
         recipients: ["admin@company.com"]
       - type: slack
         webhook: "https://hooks.slack.com/..."
       - type: webhook
         url: "https://monitoring.company.com/webhooks/budget"

Alert Configuration
-------------------

Configure different alert types:

.. code-block:: python

   # Custom alert handler
   from ostruct.alerts import BudgetAlert
   
   def handle_budget_alert(alert: BudgetAlert):
       if alert.percentage >= 0.9:
           # Critical alert - stop processing
           alert.stop_processing()
           send_urgent_notification(alert)
       elif alert.percentage >= 0.8:
           # Warning alert - continue with caution
           send_warning_notification(alert)

Cost Analysis and Reporting
===========================

Usage Analytics
---------------

Analyze usage patterns to optimize costs:

.. code-block:: sql

   -- Query usage database
   SELECT 
       model,
       AVG(tokens_used) as avg_tokens,
       AVG(cost) as avg_cost,
       COUNT(*) as request_count,
       DATE(timestamp) as date
   FROM usage_logs 
   WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
   GROUP BY model, DATE(timestamp)
   ORDER BY date DESC;

Cost Optimization Reports
-------------------------

Generate optimization recommendations:

.. code-block:: bash

   # Generate optimization report
   ostruct-analyze-costs \
     --period last-30-days \
     --output optimization_report.json \
     --include-recommendations

   # Example output
   {
     "total_cost": 1250.75,
     "cost_by_model": {
       "gpt-4": 875.50,
       "gpt-3.5-turbo": 375.25
     },
     "recommendations": [
       {
         "type": "model_downgrade",
         "description": "35% of GPT-4 requests could use GPT-3.5-turbo",
         "potential_savings": 215.80
       }
     ]
   }

Best Practices
==============

Model Selection Guidelines
--------------------------

1. **Use GPT-3.5-turbo for**:
   - Data extraction from structured documents
   - Simple classification tasks
   - Format conversion
   - Basic summarization

2. **Use GPT-4 for**:
   - Complex reasoning tasks
   - Code analysis and generation
   - Multi-step problem solving
   - High-stakes business decisions

3. **Use GPT-4-turbo for**:
   - Large document processing
   - Multi-modal tasks
   - Complex data analysis
   - High-accuracy requirements

Template Design
---------------

1. **Be specific**: Clear, focused prompts reduce token waste
2. **Use examples**: Few-shot examples improve accuracy
3. **Limit output**: Use schema constraints to control response length
4. **Cache-friendly**: Design templates for effective caching

Processing Strategy
-------------------

1. **Batch intelligently**: Group similar tasks together
2. **Filter early**: Remove unnecessary data before processing
3. **Use progressive enhancement**: Start cheap, upgrade when needed
4. **Monitor continuously**: Track costs in real-time

Cost Governance
===============

Team Guidelines
---------------

Establish clear cost management policies:

.. code-block:: yaml

   # team-policy.yaml
   cost_governance:
     approval_required_above: 100.00  # USD per day
     model_restrictions:
       gpt-4: ["senior-engineers", "data-scientists"]
       gpt-3.5-turbo: ["all-users"]
     
     default_limits:
       daily_budget: 25.00
       monthly_budget: 500.00
       max_tokens_per_request: 2000

Access Controls
---------------

Implement role-based cost controls:

.. code-block:: bash

   # User-specific configuration
   export OSTRUCT_USER_TIER=standard
   export OSTRUCT_DAILY_LIMIT=50.00
   export OSTRUCT_ALLOWED_MODELS="gpt-3.5-turbo,gpt-3.5-turbo-16k"

Emergency Procedures
====================

Budget Exceeded
---------------

Define procedures for budget overruns:

1. **Immediate actions**:
   - Stop all non-critical processing
   - Alert stakeholders
   - Review recent usage

2. **Investigation**:
   - Identify cause of overage
   - Review recent changes
   - Check for runaway processes

3. **Resolution**:
   - Implement immediate fixes
   - Adjust budgets if justified
   - Update monitoring thresholds

Circuit Breakers
----------------

Implement automatic safeguards:

.. code-block:: python

   # Circuit breaker implementation
   from ostruct.circuit_breaker import CostCircuitBreaker
   
   breaker = CostCircuitBreaker(
       daily_limit=100.00,
       failure_threshold=5,
       recovery_timeout=3600
   )
   
   @breaker.protected
   def process_with_ai(content):
       return ostruct.process(content)

Conclusion
==========

Effective cost control requires:

1. **Proactive monitoring** of usage and spending
2. **Smart model selection** based on task complexity
3. **Efficient template design** to minimize token usage
4. **Caching strategies** to avoid duplicate API calls
5. **Automated controls** to prevent budget overruns
6. **Regular analysis** to identify optimization opportunities

By implementing these strategies, you can significantly reduce AI processing costs while maintaining high-quality results.