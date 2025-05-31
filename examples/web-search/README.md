# Web Search Examples

This directory contains examples and best practices for using ostruct's web search integration to get up-to-date information in your structured outputs.

## Overview

The web search tool allows models to search the web for current information, making it perfect for:

- Current events and news analysis
- Latest technology updates
- Real-time data gathering
- Market research with current data
- Fact-checking against recent sources

## Template Guidance for Web Search

### 1. Explicit Instructions

Include clear instructions in your templates to guide the model when to use web search:

```jinja2
{# Template: current_analysis.j2 #}
Please analyze the current state of {{ topic }}.

**Important**: Use web search to find the most recent information about this topic.
Ensure all data is from reliable sources and cite your sources in the 'sources' field.

Current date context: {{ "now"|strftime("%Y-%m-%d") }}

Please provide:
1. Current status and recent developments
2. Key trends and changes in the last 6 months
3. Expert opinions and analysis
4. Reliable source citations
```

### 2. Conditional Instructions Based on Web Search Availability

Use the `web_search_enabled` template variable to provide different instructions:

```jinja2
{# Template: flexible_analysis.j2 #}
{% if web_search_enabled %}
{# Note to AI: Web search is available. Please use it to find current information about {{ topic }}. #}
Research the latest developments in {{ topic }} using web search. Focus on information from the last 30 days and cite all sources used in the 'sources' field.
{% else %}
{# Note to AI: Web search is not available. Use your training data and note any limitations. #}
Analyze {{ topic }} based on available training data. Please note the knowledge cutoff date and any limitations in your analysis due to potentially outdated information.
{% endif %}

Analysis topic: {{ topic }}
Required depth: {{ depth | default("comprehensive") }}
```

### 3. Schema Design for Citations

Design your schemas to capture web search sources properly:

```json
{
  "type": "object",
  "properties": {
    "analysis": {
      "type": "string",
      "description": "Main analysis content without inline citations"
    },
    "key_findings": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of key findings from the research"
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {
            "type": "string",
            "description": "Title of the source page or article"
          },
          "url": {
            "type": "string",
            "format": "uri",
            "description": "URL of the source"
          },
          "date_accessed": {
            "type": "string",
            "description": "When this source was accessed (if available)"
          },
          "relevance": {
            "type": "string",
            "enum": ["primary", "supporting", "reference"],
            "description": "How this source relates to the analysis"
          }
        },
        "required": ["title", "url"]
      },
      "description": "List of web sources used in this analysis"
    },
    "last_updated": {
      "type": "string",
      "description": "Most recent date found in the source material"
    }
  },
  "required": ["analysis", "sources"]
}
```

## Schema Patterns for Web Search Sources

### Basic Sources Pattern

The most common pattern for capturing web search sources is to include a `sources` array in your JSON schema:

```json
{
  "type": "object",
  "properties": {
    "answer": {
      "type": "string",
      "description": "Your main response content"
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {
            "type": "string",
            "description": "Title of the source page or article"
          },
          "url": {
            "type": "string",
            "description": "URL of the source (avoid format: uri for OpenAI strict mode compatibility)"
          },
          "publication": {
            "type": "string",
            "description": "Name of the publication or website"
          },
          "date_published": {
            "type": "string",
            "description": "Publication date (if available)"
          }
        },
        "required": ["title", "url"]
      },
      "description": "List of web sources used to answer the query"
    }
  },
  "required": ["answer", "sources"]
}
```

### Enhanced Sources with Relevance Scoring

For more sophisticated analysis, you can categorize sources by relevance:

```json
{
  "sources": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "url": {"type": "string"},
        "publication": {"type": "string"},
        "date_published": {"type": "string"},
        "relevance": {
          "type": "string",
          "enum": ["primary", "supporting", "background"],
          "description": "How this source relates to the analysis"
        },
        "credibility": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Assessment of source credibility"
        }
      },
      "required": ["title", "url", "relevance"]
    }
  }
}
```

### Multiple Source Categories

For complex research tasks, you might want to separate different types of sources:

```json
{
  "type": "object",
  "properties": {
    "primary_sources": {
      "type": "array",
      "description": "Primary sources (official announcements, press releases, etc.)",
      "items": {"$ref": "#/$defs/source"}
    },
    "news_sources": {
      "type": "array",
      "description": "News articles and reports",
      "items": {"$ref": "#/$defs/source"}
    },
    "analysis_sources": {
      "type": "array",
      "description": "Expert analysis and commentary",
      "items": {"$ref": "#/$defs/source"}
    }
  },
  "$defs": {
    "source": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "url": {"type": "string"},
        "author": {"type": "string"},
        "publication": {"type": "string"},
        "date_published": {"type": "string"}
      },
      "required": ["title", "url"]
    }
  }
}
```

### Important Schema Considerations

1. **OpenAI Strict Mode Compatibility**: Avoid `format: "uri"` on URL fields as this can cause validation errors
2. **Required vs Optional**: Make `title` and `url` required, other fields optional
3. **Citation Separation**: Keep sources in dedicated fields, not mixed with main content
4. **Flexible Dating**: Use string type for dates since formats vary widely across sources

### Template Instructions for Sources

When using these schemas, include clear instructions in your templates:

```jinja2
**Source Requirements**:
- Use web search to find current information
- Cite ALL sources used in the 'sources' field
- Include publication dates when available
- DO NOT use inline citations like [1], [2] in the main text
- Keep the main analysis clean and readable
```

## Best Practices

### Template Instructions

1. **Be Explicit**: Always explicitly instruct the model to use web search when current information is needed
2. **Specify Timeframes**: Ask for information from specific time periods (e.g., "last 30 days", "2024 updates")
3. **Request Source Citations**: Always ask for sources to be included in a dedicated schema field
4. **Avoid Inline Citations**: Don't use `[1]`, `[2]` style citations in text fields - use the sources array instead

### Schema Design

1. **Separate Sources Field**: Always include a dedicated `sources` array in your schema
2. **Clean Text Fields**: Keep analysis text clean without inline citation markers
3. **Source Metadata**: Include title, URL, and optionally date/relevance for each source
4. **Required Sources**: Make the sources field required when using web search

### Usage Patterns

1. **Current Events**: Perfect for news analysis, market updates, recent developments
2. **Technology Research**: Latest software versions, recent releases, current trends
3. **Fact Verification**: Cross-referencing claims against current sources
4. **Competitive Analysis**: Recent company news, product launches, market movements

## Example Usage

```bash
# Basic research (requires 'question' variable)
ostruct run basic_research.j2 basic_research_schema.json --web-search -V question="What are the new features in Python 3.13?"

# Current events analysis (requires 'topic' variable)
ostruct run current_events.j2 current_events_schema.json --web-search -V topic="AI developments"

# Flexible analysis with optional parameters (requires 'topic' variable)
ostruct run flexible_analysis.j2 enhanced_sources_schema.json --web-search -V topic="climate change" -V depth="detailed" -V timeframe="60 days"

# Dry run to validate without API costs
ostruct run basic_research.j2 basic_research_schema.json --web-search --dry-run -V question="Any research question"
```

## Model Compatibility

Web search is supported by the following models:

- **GPT-4o series**: All variants support web search via tools
- **GPT-4.1 series**: All variants except nano support web search
- **O-series models**: All reasoning models (o1, o3, o4) support web search

Models that do NOT support web search:

- GPT-4.1-nano (explicitly unsupported)
- Older GPT models (3.5-turbo, GPT-4 classic)

## Security Considerations

### Data Privacy and Search Queries

**⚠️ Important**: When using `--web-search`, search queries derived from your prompts and templates may be sent to external search services via OpenAI.

#### What Gets Searched

- Template content and variable values
- Prompt instructions and context
- Research questions and topics
- Any text that guides the model to search for information

#### Privacy Best Practices

1. **Avoid Sensitive Information**: Don't include confidential data, internal project names, or proprietary information in prompts when using web search
2. **Use Generic Terms**: Instead of "Project Falcon Q4 results", use "quarterly business results"
3. **Review Template Variables**: Check that template variables don't contain sensitive data
4. **Test with Public Information**: Start with publicly available topics to understand search behavior

#### Example: Secure vs. Insecure Prompts

**❌ Avoid (contains sensitive information):**

```jinja2
Research the latest developments in {{ internal_project_codename }} technology.
Find information about {{ confidential_client_name }}'s recent acquisitions.
```

**✅ Better (uses generic terms):**

```jinja2
Research the latest developments in {{ technology_category }} technology.
Find information about recent acquisitions in the {{ industry_sector }} sector.
```

#### Opt-in Requirement

- Web search is **always opt-in** - you must explicitly use `--web-search`
- This ensures you're aware when external services may be accessed
- Use `--no-web-search` to explicitly disable if needed

#### Platform Protections

- **Azure OpenAI**: Web search is automatically disabled for Azure endpoints with a warning
- **Rate Limits**: Web search uses your OpenAI API quota and may have additional limits
- **Existing API Key**: Uses your existing `OPENAI_API_KEY` - no separate authentication needed

### Model Compatibility

Web search is supported by the following models:

## Troubleshooting

### Common Issues

1. **Model Compatibility**: Use `--dry-run` to check if your model supports web search
2. **Empty Sources**: Ensure your schema requires the sources field and your template asks for citations
3. **Inline Citations**: If you see `[1]`, `[2]` markers, update your template to request clean text with separate sources
4. **Azure Errors**: Check if you're using an Azure OpenAI endpoint (automatically disabled)

### Debug Commands

```bash
# Check model compatibility with basic research
ostruct run basic_research.j2 basic_research_schema.json --web-search --model gpt-4o --dry-run -V question="test question"

# Verbose logging for debugging current events
ostruct run current_events.j2 current_events_schema.json --web-search --verbose -V topic="test topic"

# Test without web search for comparison
ostruct run basic_research.j2 basic_research_schema.json -V question="same research question"
```

## Next Steps

Explore the example templates in this directory to see web search in action:

- `basic_research.j2` - General research questions with comprehensive analysis
- `current_events.j2` - News and current events analysis with timeline focus
- `flexible_analysis.j2` - Adaptive template that works with or without web search
