# ostruct-cli

Command-line interface for working with OpenAI models and structured output, powered by the [openai-structured](https://github.com/yanivgolan/openai-structured) library.

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
echo "John Smith is a 35 year old software engineer" | ostruct --task @task.j2 --schema schema.json
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

While the CLI accepts templates with any extension (when prefixed with `@`), we recommend using `.j2` for better tooling support and clarity.

## Documentation

For detailed documentation, visit our [Read the Docs](https://ostruct-cli.readthedocs.io/).

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

## Migration from openai-structured

If you were previously using the CLI bundled with openai-structured (pre-1.0.0), this is its new home. The migration is straightforward:

1. Update openai-structured to version 1.0.0 or later
2. Install ostruct-cli
3. Replace any `openai-structured` CLI commands with `ostruct`

The functionality remains the same, just moved to a dedicated package for better maintenance and focus.
