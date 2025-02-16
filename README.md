# ostruct-cli

[![PyPI version](https://badge.fury.io/py/ostruct-cli.svg)](https://badge.fury.io/py/ostruct-cli)
[![Python Versions](https://img.shields.io/pypi/pyversions/ostruct-cli.svg)](https://pypi.org/project/ostruct-cli)
[![Documentation Status](https://readthedocs.org/projects/ostruct/badge/?version=latest)](https://ostruct.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/yaniv-golan/ostruct/actions/workflows/ci.yml/badge.svg)](https://github.com/yaniv-golan/ostruct/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Command-line interface for working with OpenAI models and structured output, powered by the [openai-structured](https://github.com/yaniv-golan/openai-structured) library.

## Features

- Generate structured output from natural language using OpenAI models
- Rich template system for defining output schemas
- Automatic token counting and context window management
- Streaming support for real-time output
- Caching system for cost optimization
- Secure handling of sensitive data

## Installation

```bash
pip install ostruct-cli
```

## Quick Start

1. Set your OpenAI API key:

```bash
export OPENAI_API_KEY=your-api-key
```

2. Create a task template file `task.j2`:

```
Extract information about the person: {{ stdin }}
```

3. Create a schema file `schema.json`:

```json
{
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
  "required": ["name", "age", "occupation"]
}
```

4. Run the CLI:

```bash
ostruct run task.j2 schema.json
```

Or with more options:

```bash
ostruct run task.j2 schema.json \
  -f content input.txt \
  -m gpt-4o \
  --sys-prompt "You are an expert content analyzer"
```

Output:

```json
{
  "name": "John Smith",
  "age": 35,
  "occupation": "software engineer"
}
```

### About Template Files

Template files use the `.j2` extension to indicate they contain Jinja2 template syntax. This convention:

- Enables proper syntax highlighting in most editors
- Makes it clear the file contains template logic
- Follows industry standards for Jinja2 templates

## CLI Options

The CLI revolves around a single subcommand called `run`. Basic usage:

```bash
ostruct run <TASK_TEMPLATE> <SCHEMA_FILE> [OPTIONS]
```

Common options include:

- File & Directory Inputs:
  - `-f <NAME> <PATH>`: Map a single file to a variable name
  - `-d <NAME> <DIR>`: Map a directory to a variable name
  - `-p <NAME> <PATTERN>`: Map files matching a glob pattern to a variable name
  - `-R, --recursive`: Enable recursive directory/pattern scanning

- Variables:
  - `-V name=value`: Define a simple string variable
  - `-J name='{"key":"value"}'`: Define a JSON variable

- Model Parameters:
  - `-m, --model MODEL`: Select the OpenAI model (supported: gpt-4o, o1, o3-mini)
  - `--temperature FLOAT`: Set sampling temperature (0.0-2.0)
  - `--max-output-tokens INT`: Set maximum output tokens
  - `--top-p FLOAT`: Set top-p sampling parameter (0.0-1.0)
  - `--frequency-penalty FLOAT`: Adjust frequency penalty (-2.0-2.0)
  - `--presence-penalty FLOAT`: Adjust presence penalty (-2.0-2.0)
  - `--reasoning-effort [low|medium|high]`: Control model reasoning effort

- System Prompt:
  - `--sys-prompt TEXT`: Provide system prompt directly
  - `--sys-file FILE`: Load system prompt from file
  - `--ignore-task-sysprompt`: Ignore system prompt in template frontmatter

- API Configuration:
  - `--api-key KEY`: OpenAI API key (defaults to OPENAI_API_KEY env var)
  - `--timeout FLOAT`: API timeout in seconds (default: 60.0)

## Debug Options

- `--debug-validation`: Show detailed schema validation debugging
- `--debug-openai-stream`: Enable low-level debug output for OpenAI streaming
- `--progress-level {none,basic,detailed}`: Set progress reporting level
  - `none`: No progress indicators
  - `basic`: Show key operation steps (default)
  - `detailed`: Show all steps with additional info
- `--show-model-schema`: Display the generated Pydantic model schema
- `--verbose`: Enable verbose logging
- `--dry-run`: Validate and render template without making API calls
- `--no-progress`: Disable all progress indicators

All debug and error logs are written to:

- `~/.ostruct/logs/ostruct.log`: General application logs
- `~/.ostruct/logs/openai_stream.log`: OpenAI streaming operations logs

For more detailed documentation and examples, visit our [documentation](https://ostruct.readthedocs.io/).

## Development

To contribute or report issues, please visit our [GitHub repository](https://github.com/yaniv-golan/ostruct).

## Development Setup

1. Clone the repository:

```bash
git clone https://github.com/yanivgolan/ostruct.git
cd ostruct
```

2. Install Poetry if you haven't already:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install dependencies:

```bash
poetry install
```

4. Install openai-structured in editable mode:

```bash
poetry add --editable ../openai-structured  # Adjust path as needed
```

5. Run tests:

```bash
poetry run pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
