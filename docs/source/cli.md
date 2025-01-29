# CLI Reference

`ostruct` is a command-line tool for generating structured output from OpenAI models. It allows you to process text and files using OpenAI's models while ensuring the output follows a specific JSON schema.

## Basic Usage

```bash
ostruct --task TEMPLATE --schema SCHEMA_FILE [OPTIONS]
```

## Required Arguments

- `--task TEMPLATE`: The task template string or @file (recommended extension: .j2)
- `--schema SCHEMA_FILE`: JSON Schema file that defines the structure of the output

## Template Files

Template files use the `.j2` extension to indicate they contain Jinja2 template syntax. This convention:

- Enables proper syntax highlighting in most editors
- Makes it clear the file contains template logic
- Follows industry standards for Jinja2 templates

While the CLI accepts templates with any extension (when prefixed with `@`), we recommend using `.j2` for better tooling support and clarity.

## Common Options

### Input Options

- `--file NAME=PATH`: Map a file to a variable (can be used multiple times)
- `--files NAME=PATTERN`: Map glob pattern to variable (can be used multiple times)
- `--dir NAME=PATH`: Map directory to variable (can be used multiple times)
- `--dir-recursive`: Process directories recursively
- `--dir-ext EXTENSIONS`: Comma-separated list of file extensions to include in directory processing
- `--allowed-dir PATH`: Additional allowed directory or @file

### Variable Options

- `--var NAME=VALUE`: Pass simple variables to template
- `--json-var NAME=JSON`: Pass JSON-structured variables to template

### Model Options

- `--model MODEL`: OpenAI model to use (default: gpt-4o-2024-08-06)
- `--temperature float`: Temperature for sampling (default: 0.0)
- `--max-tokens int`: Maximum tokens to generate
- `--top-p float`: Top-p sampling parameter (default: 1.0)
- `--frequency-penalty float`: Frequency penalty parameter (default: 0.0)
- `--presence-penalty float`: Presence penalty parameter (default: 0.0)

### System Prompt Options

- `--system-prompt TEXT`: Override system prompt (can use @file)
- `--ignore-task-sysprompt`: Ignore system prompt from task template

### Debug Options

- `--show-model-schema`: Display the generated Pydantic model schema
- `--debug-validation`: Show detailed schema validation debugging
- `--verbose-schema`: Enable verbose schema debugging output
- `--debug-openai-stream`: Enable low-level debug output for OpenAI streaming (very verbose)
- `--progress-level {none,basic,detailed}`: Set progress reporting level (default: basic)

## Examples

### Basic Example with Schema

1. Create a schema file `review_schema.json`:

```json
{
  "type": "object",
  "properties": {
    "summary": {
      "type": "string",
      "description": "Brief summary of the text"
    },
    "sentiment": {
      "type": "string",
      "enum": ["positive", "negative", "neutral"],
      "description": "Overall sentiment"
    },
    "key_points": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Main points from the text"
    }
  },
  "required": ["summary", "sentiment", "key_points"]
}
```

2. Create a task template `review.j2`:

```
Analyze this text and provide a structured review:

{{ input.content }}
```

3. Run the analysis:

```bash
ostruct \
  --task @review.j2 \
  --schema review_schema.json \
  --file input=article.txt \
  --model gpt-4o-2024-08-06
```

### Directory Processing Example

Process all Python files in a directory:

```bash
ostruct \
  --task @analyze.j2 \
  --schema code_review_schema.json \
  --dir src=./src \
  --dir-recursive \
  --dir-ext py \
  --model gpt-4o-2024-08-06
```

### Code Review Example

1. Create a schema for code review `code_review_schema.json`:

```json
{
  "type": "object",
  "properties": {
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["high", "medium", "low"]
          },
          "description": {"type": "string"},
          "suggestion": {"type": "string"}
        },
        "required": ["severity", "description", "suggestion"]
      }
    },
    "best_practices": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": ["issues", "best_practices"]
}
```

2. Create a task template with system prompt:

```
{% system_prompt %}
You are an expert code reviewer focusing on Python best practices and security.
{% end_system_prompt %}

Review this Python code and provide structured feedback:

{{ code.content }}
```

3. Run the code review:

```bash
ostruct \
  --task @review_template.j2 \
  --schema code_review_schema.json \
  --file code=app.py \
  --model gpt-4o-2024-08-06
```

### Handling Large Files

When working with large files, it's recommended to structure your prompt to place the file content at the end, delimited by clear markers. This helps the model better understand the context and improves processing of large documents.

1. Create a schema for claims extraction (`claims_schema.json`):

```json
{
  "type": "object",
  "properties": {
    "claims": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "claim": {
            "type": "string",
            "description": "The extracted claim"
          },
          "source": {
            "type": "string",
            "description": "Source or context of the claim"
          }
        },
        "required": ["claim"]
      }
    }
  },
  "required": ["claims"]
}
```

2. Run the analysis with delimited content:

```bash
ostruct \
  --task "Distill all claims from the document in the <doc> element into the JSON response. Place the claim itself in the 'claim' element, and the source (if available) in the 'source' element. <doc>{{ input.content }}</doc>" \
  --file input=large_document.txt \
  --schema claims_schema.json \
  --allowed-dir .
```

### Testing with Dry Run

Before making actual API calls, you can use the `--dry-run` flag to preview what the CLI would do:

```bash
ostruct \
  --task "Analyze this text: {{ input.content }}" \
  --schema schema.json \
  --file input=document.txt \
  --system-prompt "You are a helpful assistant that analyzes text." \
  --dry-run
```

The dry run will show:

- The rendered system and user prompts
- Estimated token count
- Model parameters (temperature, max tokens, etc.)
- Schema validation status
- Output file path (if specified)
- No API call will be made

This is particularly useful for:

- Verifying prompt rendering
- Checking token usage before processing large files
- Testing schema validation
- Ensuring correct file access permissions

Note: While `--debug-openai-stream` is available for debugging actual API calls, it won't show streaming data during a dry run since no API calls are made. To debug streaming, use `--debug-openai-stream` without `--dry-run`.

### Multiple Files Example

Compare two files using a structured schema:

1. Create a comparison schema (`compare_schema.json`):

```json
{
  "type": "object",
  "properties": {
    "differences": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string",
            "enum": ["addition", "deletion", "modification"],
            "description": "Type of difference"
          },
          "description": {
            "type": "string",
            "description": "Description of the difference"
          },
          "location": {
            "type": "string",
            "description": "Where the difference occurs"
          }
        },
        "required": ["type", "description"]
      }
    },
    "similarity_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Overall similarity between files (0-1)"
    }
  },
  "required": ["differences", "similarity_score"]
}
```

2. Create a task template (`compare.txt`):

```
Compare these two files and identify their differences:

## File A:
{{ file_a.content }}

## File B:
{{ file_b.content }}
```

3. Run the comparison:

```bash
ostruct \
  --task @compare.txt \
  --schema compare_schema.json \
  --file file_a=version1.py \
  --file file_b=version2.py \
  --model gpt-4o-2024-08-06 \
  --output-file differences.json
```

This example demonstrates:

- Using multiple `--file` arguments to process multiple inputs
- Structured comparison using a detailed schema
- Saving results to a file with `--output-file`

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

## Logging

The CLI maintains two log files in the `~/.ostruct/logs/` directory:

- `ostruct.log`: Contains general application logs including debug information, errors, and operation status
- `openai_stream.log`: Specific to OpenAI streaming operations, particularly useful when debugging API interactions with `--debug-openai-stream`

Both log files capture DEBUG level messages by default and use the format:

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Security Notes

By default, the CLI only allows access to files within the current working directory. To access files in other directories:

1. Use `--allowed-dir` to specify additional allowed directories
2. Use `@file` syntax to load allowed directories from a file
3. Always use absolute paths to prevent ambiguity
