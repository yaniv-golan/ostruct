# ostruct-cli

[![PyPI version](https://badge.fury.io/py/ostruct-cli.svg)](https://badge.fury.io/py/ostruct-cli)
[![Python Versions](https://img.shields.io/pypi/pyversions/ostruct-cli.svg)](https://pypi.org/project/ostruct-cli)
[![Documentation Status](https://readthedocs.org/projects/ostruct/badge/?version=latest)](https://ostruct.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/yaniv-golan/ostruct/actions/workflows/ci.yml/badge.svg)](https://github.com/yaniv-golan/ostruct/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ostruct tranforms unstructured inputs into structured, usable JSON output using OpenAI APIs.

ostruct will process a set of plain text files (data, source code, CSV, etc), input variables, a dynamic prompt template, and a JSON schema specifying the desired output format, and will produce the result in JSON format.

## Features

- Generate structured JSON output from natural language using OpenAI models and a JSON schema
- Rich template system for defining prompts (Jinja2-based)
- Automatic token counting and context window management
- Streaming support for real-time output
- Secure handling of sensitive data

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
