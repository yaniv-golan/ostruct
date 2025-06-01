"""Quick reference command for ostruct CLI."""

import click


@click.command("quick-ref")
def quick_reference() -> None:
    """Show quick reference for file routing and common usage patterns."""
    quick_ref = """
🚀 OSTRUCT QUICK REFERENCE

📁 FILE ROUTING:
  -ft FILE    📄 Template access only       (config files, small data)
  -fc FILE    💻 Code Interpreter upload    (data files, scripts)
  -fs FILE    🔍 File Search vector store   (documents, manuals)

  -dt DIR     📁 Template directory         (config dirs, reference data)
  -dc DIR     📂 Code execution directory   (datasets, code repos)
  -ds DIR     📁 Search directory           (documentation, knowledge)

🔄 ADVANCED ROUTING:
  --file-for code-interpreter data.csv      Single tool, single file
  --file-for file-search docs.pdf           Single tool, single file
  --file-for code-interpreter shared.json --file-for file-search shared.json   Multi-tool routing

🏷️  VARIABLES:
  -V name=value                             Simple string variables
  -J config='{"key":"value"}'               JSON structured data

🔌 TOOLS:
  --web-search                              🌐 Real-time web search for current info
  --mcp-server label@https://server.com/sse MCP server integration
  --timeout 7200                           2-hour timeout for long operations

⚡ COMMON PATTERNS:
  # Basic template rendering
  ostruct run template.j2 schema.json -V env=prod

  # Data analysis with Code Interpreter
  ostruct run analysis.j2 schema.json -fc data.csv -V task=analyze

  # Document search + processing
  ostruct run search.j2 schema.json -fs docs/ -ft config.yaml

  # Multi-tool workflow
  ostruct run workflow.j2 schema.json -fc raw_data.csv -fs knowledge/ -ft config.json

  # Current information research
  ostruct run research.j2 schema.json --web-search -V topic="latest AI developments"

📖 Full help: ostruct run --help
📖 Documentation: https://ostruct.readthedocs.io
"""
    click.echo(quick_ref)
