"""Quick reference command for ostruct CLI."""

import click


@click.command("quick-ref")
def quick_reference() -> None:
    """Show quick reference for file routing and common usage patterns."""
    quick_ref = """
🚀 OSTRUCT QUICK REFERENCE

📎 NEW ATTACHMENT SYSTEM:
  --file alias file.txt                     📄 Template access (default target)
  --file ci:data file.csv                   💻 Code Interpreter upload
  --file fs:docs file.pdf                   🔍 File Search vector store
  --file prompt:config config.yaml         📄 Template access (explicit)

  --dir alias ./src                         📁 Directory attachment (template)
  --dir ci:data ./datasets                  📂 Code execution directory
  --dir fs:docs ./documentation             📁 Search directory

🔄 MULTI-TOOL ROUTING:
  --file ci,fs:shared data.csv              Share file between Code Interpreter and File Search
  --file prompt,ci:config settings.json    Make file available in template AND Code Interpreter

📝 FILE COLLECTIONS:
  --collect all:files @filelist.txt         📄 Attach multiple files from list
  --collect ci:data @datasets.txt           💻 Upload file collection to Code Interpreter

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
