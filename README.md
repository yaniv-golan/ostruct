![ostruct](src/assets/ostruct-header.png)

<div align="center">

[![PyPI version](https://badge.fury.io/py/ostruct-cli.svg)](https://badge.fury.io/py/ostruct-cli)
[![Python Versions](https://img.shields.io/pypi/pyversions/ostruct-cli.svg)](https://pypi.org/project/ostruct-cli)
[![Documentation Status](https://readthedocs.org/projects/ostruct/badge/?version=latest)](https://ostruct.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/yaniv-golan/ostruct/actions/workflows/ci.yml/badge.svg)](https://github.com/yaniv-golan/ostruct/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ostruct** tranforms **unstructured** inputs into **structured**, usable **JSON** output using **OpenAI APIs** using dynamic **templates**

</div>

# ostruct-cli

ostruct will process a set of plain text files (data, source code, CSV, etc), input variables, a dynamic prompt template, and a JSON schema specifying the desired output format, and will produce the result in JSON format.

<div align="center">

![How ostruct works](src/assets/ostrict-hl-diagram.png)

</div>

## Why ostruct?

LLMs are powerful, but getting consistent, structured output from them can be challenging. ostruct solves this problem by providing a streamlined approach to transform unstructured data into reliable JSON structures. The motivation behind creating ostruct was to:

- **Bridge the gap** between freeform LLM capabilities and structured data needs in production systems
- **Simplify integration** of AI into existing workflows and applications that expect consistent data formats
- **Ensure reliability** and validate output against a defined schema to avoid unexpected formats or missing data
- **Reduce development time** by providing a standardized way to interact with OpenAI models for structured outputs
- **Enable non-developers** to leverage AI capabilities through a simple CLI interface with templates

## Real-World Use Cases

ostruct can be used for various scenarios, including:

### Etymology Analysis

```bash
ostruct run prompts/task.j2 schemas/etymology.json -f input examples/scientific.txt --model gpt-4o
```

Break down words into their components, showing their origins, meanings, and hierarchical relationships. Useful for linguistics, educational tools, and understanding terminology in specialized fields.

### Automated Code Review

```bash
ostruct run prompts/task.j2 schemas/code_review.json -p source "examples/security/*.py" --model gpt-4o
```

Analyze code for security vulnerabilities, style issues, and performance problems, producing structured reports that can be easily integrated into CI/CD pipelines or developer workflows.

### Security Vulnerability Scanning

```bash
ostruct run prompts/task.j2 schemas/scan_result.json -d examples/intermediate --model gpt-4o
```

Scan codebases for security vulnerabilities, combining static analysis with AI-powered reasoning to identify potential issues, suggest fixes, and provide detailed explanations.

### Configuration Validation & Analysis

```bash
ostruct run prompts/task.j2 schemas/validation_result.json -f dev examples/basic/dev.yaml -f prod examples/basic/prod.yaml
```

Validate configuration files across environments, check for inconsistencies, and provide intelligent feedback on potential issues or improvements in infrastructure setups.

## Features

- Generate structured JSON output from natural language using OpenAI models and a JSON schema
- Rich template system for defining prompts (Jinja2-based)
- Automatic token counting and context window management
- Streaming support for real-time output
- Secure handling of sensitive data
- Model registry management with support for updating to the latest OpenAI models
- Non-intrusive registry update checks with user notifications

## Requirements

- Python 3.10 or higher

## Installation

### For Users

To install the latest stable version from PyPI:

```bash
pip install ostruct-cli
```

### For Developers

If you plan to contribute to the project, see the [Development Setup](#development-setup) section below for instructions on setting up the development environment with Poetry.

## Environment Variables

ostruct-cli respects the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key (required unless provided via command line)
- `OPENAI_API_BASE`: Custom API base URL (optional)
- `OPENAI_API_VERSION`: API version to use (optional)
- `OPENAI_API_TYPE`: API type (e.g., "azure") (optional)
- `OSTRUCT_DISABLE_UPDATE_CHECKS`: Set to "1", "true", or "yes" to disable automatic registry update checks

## Shell Completion

ostruct-cli supports shell completion for Bash, Zsh, and Fish shells. To enable it:

### Bash

Add this to your `~/.bashrc`:

```bash
eval "$(_OSTRUCT_COMPLETE=bash_source ostruct)"
```

### Zsh

Add this to your `~/.zshrc`:

```bash
eval "$(_OSTRUCT_COMPLETE=zsh_source ostruct)"
```

### Fish

Add this to your `~/.config/fish/completions/ostruct.fish`:

```fish
eval (env _OSTRUCT_COMPLETE=fish_source ostruct)
```

After adding the appropriate line, restart your shell or source the configuration file.
Shell completion will help you with:

- Command options and their arguments
- File paths for template and schema files
- Directory paths for `-d` and `--base-dir` options
- And more!

## Quick Start

1. Set your OpenAI API key:

```bash
export OPENAI_API_KEY=your-api-key
```

### Example 1: Using stdin (Simplest)

1. Create a template file `extract_person.j2`:

```jinja
Extract information about the person from this text: {{ stdin }}
```

2. Create a schema file `schema.json`:

```json
{
  "type": "object",
  "properties": {
    "person": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "The person's full name"
        },
        "age": {
          "type": "integer",
          "description": "The person's age"
        },
        "occupation": {
          "type": "string",
          "description": "The person's job or profession"
        }
      },
      "required": ["name", "age", "occupation"],
      "additionalProperties": false
    }
  },
  "required": ["person"],
  "additionalProperties": false
}
```

3. Run the CLI:

```bash
# Basic usage
echo "John Smith is a 35-year-old software engineer" | ostruct run extract_person.j2 schema.json

# For longer text using heredoc
cat << EOF | ostruct run extract_person.j2 schema.json
John Smith is a 35-year-old software engineer
working at Tech Corp. He has been programming
for over 10 years.
EOF

# With advanced options
echo "John Smith is a 35-year-old software engineer" | \
  ostruct run extract_person.j2 schema.json \
  --model gpt-4o \
  --sys-prompt "Extract precise information about the person" \
  --temperature 0.7
```

The command will output:

```json
{
  "person": {
    "name": "John Smith",
    "age": 35,
    "occupation": "software engineer"
  }
}
```

### Example 2: Processing a Single File

1. Create a template file `extract_from_file.j2`:

```jinja
Extract information about the person from this text: {{ text.content }}
```

2. Use the same schema file `schema.json` as above.

3. Run the CLI:

```bash
# Basic usage
ostruct run extract_from_file.j2 schema.json -f text input.txt

# With advanced options
ostruct run extract_from_file.j2 schema.json \
  -f text input.txt \
  --model gpt-4o \
  --max-output-tokens 1000 \
  --temperature 0.7
```

The command will output:

```json
{
  "person": {
    "name": "John Smith",
    "age": 35,
    "occupation": "software engineer"
  }
}
```

## System Prompt Handling

ostruct-cli provides three ways to specify a system prompt, with a clear precedence order:

1. Command-line option (`--sys-prompt` or `--sys-file`):

   ```bash
   # Direct string
   ostruct run template.j2 schema.json --sys-prompt "You are an expert analyst"

   # From file
   ostruct run template.j2 schema.json --sys-file system_prompt.txt
   ```

2. Template frontmatter:

   ```jinja
   ---
   system_prompt: You are an expert analyst
   ---
   Extract information from: {{ text }}
   ```

3. Default system prompt (built into the CLI)

### Precedence Rules

When multiple system prompts are provided, they are resolved in this order:

1. Command-line options take highest precedence:
   - If both `--sys-prompt` and `--sys-file` are provided, `--sys-prompt` wins
   - Use `--ignore-task-sysprompt` to ignore template frontmatter

2. Template frontmatter is used if:
   - No command-line options are provided
   - `--ignore-task-sysprompt` is not set

3. Default system prompt is used only if no other prompts are provided

Example combining multiple sources:

```bash
# Command-line prompt will override template frontmatter
ostruct run template.j2 schema.json --sys-prompt "Override prompt"

# Ignore template frontmatter and use default
ostruct run template.j2 schema.json --ignore-task-sysprompt
```

## Model Registry Management

ostruct-cli maintains a registry of OpenAI models and their capabilities, which includes:

- Context window sizes for each model
- Maximum output token limits
- Supported parameters and their constraints
- Model version information

To ensure you're using the latest models and features, you can update the registry:

```bash
# Update from the official repository
ostruct update-registry

# Update from a custom URL
ostruct update-registry --url https://example.com/models.yml

# Force an update even if the registry is current
ostruct update-registry --force
```

This is especially useful when:

- New OpenAI models are released
- Model capabilities or parameters change
- You need to work with custom model configurations

The registry file is stored at `~/.openai_structured/config/models.yml` and is automatically referenced when validating model parameters and token limits.

The update command uses HTTP conditional requests (If-Modified-Since headers) to check if the remote registry has changed before downloading, ensuring efficient updates.
