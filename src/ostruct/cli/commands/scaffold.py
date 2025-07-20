"""The scaffold command for creating template files."""

import os
from pathlib import Path
from typing import Optional

import rich_click as click

from ..ost.windows_launcher import generate_launcher_for_template, is_windows


def _check_env_s_support() -> bool:
    """Check if env -S is available (GNU coreutils)."""
    try:
        # Try to run env -S with a simple command
        result = os.system("env -S echo test > /dev/null 2>&1")
        return result == 0
    except Exception:
        return False


def _generate_ost_template(
    name: str,
    description: str,
    output_file: Path,
    include_examples: bool = True,
) -> None:
    """Generate an OST template file with proper front-matter."""

    # Check env -S support and emit warning if not available
    if not _check_env_s_support():
        click.echo(
            click.style(
                "⚠️  Warning: 'env -S' (GNU coreutils) not available. "
                "Shebang execution may not work on this system.",
                fg="yellow",
            ),
            err=True,
        )

    # Generate the template content
    template_content = f"""#!/usr/bin/env -S ostruct runx
---
cli:
  name: {name}
  description: {description}
  positional:
    - name: input_text
      help: Input text to process
  options:
    format:
      names: ["--format", "-f"]
      help: Output format
      default: "json"
      choices: ["json", "yaml", "text"]
    verbose:
      names: ["--verbose", "-v"]
      help: Enable verbose output
      action: "store_true"
    # Examples of different file routing targets
    config_file:
      names: ["--config"]
      help: Configuration file (template access only)
      type: "file"
      target: "prompt"
    data_file:
      names: ["--data"]
      help: Data file for analysis (Code Interpreter)
      type: "file"
      target: "ci"
    docs_file:
      names: ["--docs"]
      help: Documentation file (File Search)
      type: "file"
      target: "fs"
    pdf_file:
      names: ["--pdf"]
      help: PDF file for vision analysis (user-data)
      type: "file"
      target: "ud"
    auto_file:
      names: ["--auto"]
      help: Auto-routed file (based on file type)
      type: "file"
      target: "auto"

schema: |
  {{
    "type": "object",
    "properties": {{
      "result": {{
        "type": "string",
        "description": "The processed result"
      }},
      "format": {{
        "type": "string",
        "description": "The output format used"
      }},
      "input_length": {{
        "type": "integer",
        "description": "Length of input text"
      }},
      "files_processed": {{
        "type": "array",
        "items": {{
          "type": "string"
        }},
        "description": "List of files that were processed"
      }}
    }},
    "required": ["result", "format", "input_length"]
  }}

defaults:
  format: "json"
  verbose: false

global_args:
  pass_through_global: true
  --model:
    values: ["gpt-4o", "gpt-4.1", "o1"]
    mode: "allowed"
    default: "gpt-4.1"
  --verbose:
    mode: "pass-through"
---
{{% if verbose %}}
Processing input: "{{{{ input_text }}}}" in {{{{ format }}}} format
{{% endif %}}

# Task: Process Input Text

You are a helpful assistant that processes text input according to the specified format.

## Input
- Text: {{{{ input_text }}}}
- Format: {{{{ format }}}}
- Verbose: {{{{ verbose }}}}

{{% if config_file is defined %}}
## Configuration
Configuration from: {{{{ config_file.name }}}}
{{{{ config_file.content }}}}
{{% endif %}}

{{% if data_file is defined %}}
## Data Analysis
Data file available for Code Interpreter analysis: {{{{ data_file.name }}}}
{{% endif %}}

{{% if docs_file is defined %}}
## Documentation Search
Documentation available for File Search: {{{{ docs_file.name }}}}
{{% endif %}}

{{% if pdf_file is defined %}}
## PDF Analysis
PDF file available for vision analysis: {{{{ pdf_file.name }}}}
{{% endif %}}

{{% if auto_file is defined %}}
## Auto-routed File
Auto-routed file: {{{{ auto_file.name }}}}
{{% endif %}}

## Instructions
1. Analyze the input text
2. Process it according to the format requirement
3. Use any provided files to enhance the analysis
4. Return the result in the specified structure

## Output Requirements
- result: Your processed text
- format: The format used ({{{{ format }}}})
- input_length: Length of the input text ({{{{ input_text|length }}}})
- files_processed: List of files that were processed

Please process the input now.
"""

    # Write the template to file
    output_file.write_text(template_content, encoding="utf-8")

    # Make the file executable on Unix-like systems
    if os.name != "nt":  # Not Windows
        os.chmod(output_file, 0o755)

    click.echo(f"✅ Created OST template: {output_file}")

    if include_examples:
        click.echo("\n📖 Usage examples:")
        click.echo(f"  ./{output_file.name} 'Hello world' --format json")
        click.echo(f"  ./{output_file.name} 'Test input' --verbose")
        click.echo(
            f"  ostruct runx {output_file.name} 'Sample text' --format yaml"
        )
        click.echo("\n📎 File routing examples:")
        click.echo(f"  ./{output_file.name} 'Text' --config config.yaml")
        click.echo(f"  ./{output_file.name} 'Text' --data data.csv")
        click.echo(f"  ./{output_file.name} 'Text' --docs manual.pdf")
        click.echo(f"  ./{output_file.name} 'Text' --pdf presentation.pdf")
        click.echo(f"  ./{output_file.name} 'Text' --auto document.txt")


@click.group(name="scaffold")
def scaffold() -> None:
    """Generate template files and project scaffolding."""
    pass


@scaffold.command(name="template")
@click.argument("output_file", type=click.Path())
@click.option(
    "--cli",
    is_flag=True,
    help="Generate an OST (Self-Executing Template) with CLI front-matter",
)
@click.option(
    "--name", help="Name for the CLI tool (default: derived from filename)"
)
@click.option(
    "--description",
    help="Description for the CLI tool (default: generic description)",
)
@click.option(
    "--no-examples",
    is_flag=True,
    help="Don't show usage examples after creation",
)
@click.option(
    "--windows-launcher",
    is_flag=True,
    help="Generate Windows launcher files (.exe and .cmd) alongside the OST template",
)
def template(
    output_file: str,
    cli: bool,
    name: Optional[str],
    description: Optional[str],
    no_examples: bool,
    windows_launcher: bool,
) -> None:
    """Generate a template file.

    OUTPUT_FILE: Path where the template file will be created

    Examples:
      ostruct scaffold template my_task.j2
      ostruct scaffold template my_cli.ost --cli
      ostruct scaffold template analyzer.ost --cli --name "text-analyzer" --description "Analyzes text content"
    """
    output_path = Path(output_file)

    # Check if file already exists
    if output_path.exists():
        if not click.confirm(f"File {output_path} already exists. Overwrite?"):
            click.echo("Aborted.")
            return

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if cli:
        # Generate OST template with CLI front-matter
        if not output_path.suffix == ".ost":
            click.echo(
                click.style(
                    "⚠️  Warning: OST templates should use .ost extension",
                    fg="yellow",
                ),
                err=True,
            )

        # Derive name from filename if not provided
        if not name:
            name = output_path.stem.replace("_", "-").replace(" ", "-")

        # Use default description if not provided
        if not description:
            description = f"A self-executing template for {name}"

        _generate_ost_template(
            name=name,
            description=description,
            output_file=output_path,
            include_examples=not no_examples,
        )

        # Generate Windows launcher if requested
        if windows_launcher:
            if is_windows():
                generate_launcher_for_template(output_path)
            else:
                click.echo(
                    click.style(
                        "⚠️  Warning: Windows launcher generation only supported on Windows",
                        fg="yellow",
                    ),
                    err=True,
                )
    else:
        # Generate regular Jinja2 template
        if not output_path.suffix == ".j2":
            click.echo(
                click.style(
                    "⚠️  Warning: Jinja2 templates should use .j2 extension",
                    fg="yellow",
                ),
                err=True,
            )

        # Simple Jinja2 template following ostruct patterns
        template_content = """---
system: |
  You are a helpful assistant. Return valid JSON that follows the provided schema.
---
# Task: {{title | default("Text Processing")}}

{% if description is defined %}
{{description}}
{% else %}
Analyze the provided input and return structured results.
{% endif %}

## Input
{% if input_text is defined %}
Text: {{input_text}}
{% else %}
No input provided. For dry-run validation, use example data.
{% endif %}

{% if data_file is defined %}
## Data File
{{data_file.content}}
{% endif %}

Return your analysis as valid JSON following the schema.
"""

        output_path.write_text(template_content, encoding="utf-8")
        click.echo(f"✅ Created Jinja2 template: {output_path}")

        if not no_examples:
            click.echo("\n📖 Usage examples:")
            click.echo(
                f"  ostruct run {output_path.name} schema.json --var title='My Title'"
            )
            click.echo(
                f"  ostruct run {output_path.name} schema.json --var description='My Description'"
            )
