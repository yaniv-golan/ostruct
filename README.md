## 02:07 A.M. CI Failure

*"Build failed. Again. The third time this week our data extraction pipeline broke because someone changed the log format, and our regex-based parser couldn't handle the new structure. Sarah's on vacation, Mike's parsing code is unreadable, and the client wants their analytics dashboard working by morning.*

*There has to be a better way to turn messy data into structured JSON without writing custom parsers for every format change..."*

---

![ostruct](src/assets/ostruct-header.png)

<div align="center">

[![PyPI version](https://badge.fury.io/py/ostruct-cli.svg)](https://badge.fury.io/py/ostruct-cli)
[![Python Versions](https://img.shields.io/pypi/pyversions/ostruct-cli.svg)](https://pypi.org/project/ostruct-cli)
[![Documentation Status](https://readthedocs.org/projects/ostruct/badge/?version=latest)](https://ostruct.readthedocs.io/en/latest/?badge=latest)
[![CI](https://github.com/yaniv-golan/ostruct/actions/workflows/ci.yml/badge.svg)](https://github.com/yaniv-golan/ostruct/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://pepy.tech/badge/ostruct-cli)](https://pepy.tech/project/ostruct-cli)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**ostruct** transforms **unstructured** inputs into **structured**, usable **JSON** output using **OpenAI APIs** with **multi-tool integration**

*The better way you've been looking for.*

</div>

# ostruct-cli

ostruct processes unstructured data (text files, code, CSVs, etc.), input variables, and dynamic prompt templates to produce structured JSON output defined by a JSON schema. With enhanced multi-tool integration, ostruct now supports Code Interpreter for data analysis, File Search for document retrieval, Web Search for real-time information access, and MCP (Model Context Protocol) servers for extended capabilities.

<div align="center">

![How ostruct works](src/assets/ostruct-hl-diagram.png)

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

### Automated Code Review with Multi-Tool Analysis

```bash
# Template-only analysis (fast, cost-effective)
ostruct run prompts/task.j2 schemas/code_review.json --collect source @file-list.txt

# Enhanced with Code Interpreter for deeper analysis
ostruct run prompts/task.j2 schemas/code_review.json --file ci:code examples/security/ --file fs:docs documentation/
```

Analyze code for security vulnerabilities, style issues, and performance problems. The enhanced version uses Code Interpreter for execution analysis and File Search for documentation context.

### Security Vulnerability Scanning

```bash
# Budget-friendly static analysis (recommended for most projects)
ostruct run prompts/static_analysis.j2 schemas/scan_result.json \
  --dir code examples --pattern "*.py" --sys-file prompts/system.txt

# Professional security analysis with Code Interpreter (best balance)
ostruct run prompts/code_interpreter.j2 schemas/scan_result.json \
  --dir ci:code examples --sys-file prompts/system.txt

# Comprehensive hybrid analysis for critical applications
ostruct run prompts/hybrid_analysis.j2 schemas/scan_result.json \
  --dir code examples --dir ci:analysis examples --sys-file prompts/system.txt
```

**Three optimized approaches** for automated security vulnerability scanning:

- **Static Analysis**: $0.18 cost, fast processing, comprehensive vulnerability detection
- **Code Interpreter**: $0.18 cost (same!), superior analysis quality with evidence-based findings
- **Hybrid Analysis**: $0.20 cost (+13%), maximum depth with cross-validation

Each approach finds the same core vulnerabilities but with different levels of detail and analysis quality. Directory-based analysis provides comprehensive project coverage in a single scan, automatically excluding build artifacts and sensitive files via .gitignore patterns.

### Data Analysis with Code Interpreter

```bash
# Upload data for analysis and visualization
ostruct run analysis.j2 schemas/analysis_result.json \
  --file ci:sales sales_data.csv --file ci:customers customer_data.json \
  --dir fs:reports reports/ --file config config.yaml
```

Perform sophisticated data analysis using Python execution, generate visualizations, and create comprehensive reports with document context.

### Performance Features

#### Upload Cache

ostruct automatically caches file uploads to avoid duplicates:

```bash
# First run - uploads files
ostruct run analysis.j2 schema.json --file ci:data large_dataset.csv

# Subsequent runs - reuses cached uploads (instant!)
ostruct run analysis.j2 schema.json --file ci:data large_dataset.csv
```

The cache is enabled by default and works across all file attachments:

- Code Interpreter files (`--file ci:`)
- File Search documents (`--file fs:`)
- Multi-tool attachments (`--file ci,fs:`)

Configure in `ostruct.yaml`:

```yaml
uploads:
  persistent_cache: true  # Default: enabled
```

Or via environment:

```bash
export OSTRUCT_CACHE_UPLOADS=false  # Disable cache
```

### Configuration Validation & Analysis

```bash
# Traditional file comparison
ostruct run prompts/task.j2 schemas/validation_result.json \
  --file dev examples/basic/dev.yaml --file prod examples/basic/prod.yaml

# Enhanced with environment context
ostruct run prompts/task.j2 schemas/validation_result.json \
  --file dev dev.yaml --file prod prod.yaml --dir fs:docs infrastructure_docs/
```

Validate configuration files across environments with documentation context for better analysis and recommendations.

Oh, and also, among endless other use cases:

### Etymology Analysis

```bash
ostruct run prompts/task.j2 schemas/etymology.json --file text examples/scientific.txt
```

Break down words into their components, showing their origins, meanings, and hierarchical relationships. Useful for linguistics, educational tools, and understanding terminology in specialized fields.

### Optional File References

```bash
# Attach files with aliases
ostruct run template.j2 schema.json \
  --dir source-code src/ \
  --file config config.yaml
```

**Two ways to access files in templates:**

```jinja2
{# Option 1: Automatic XML appendix (optional) #}
Analyze {{ file_ref("source-code") }} and {{ file_ref("config") }}.

{# Option 2: Manual formatting (full control) #}
## Source Code
{% for file in source-code %}
### {{ file.name }}
```{{ file.name.split('.')[-1] }}
{{ file.content }}
```

{% endfor %}

The optional `file_ref()` function provides clean references with automatic XML appendix generation. Alternatively, access files directly for custom formatting and placement control. Perfect for code reviews, documentation analysis, and multi-file processing workflows.

## Complete Examples

Ready-to-run examples demonstrating real-world ostruct applications are available in the [`examples/`](examples/) directory:

- **[Automation](examples/automation/)**: Video generation pipelines, workflow automation
- **[Document Analysis](examples/analysis/document/)**: PDF processing, semantic comparison, pitch analysis
- **[Data Analysis](examples/analysis/data/)**: Business intelligence, multi-tool data processing
- **[Security](examples/security/)**: Vulnerability scanning, code security analysis
- **[Tools Integration](examples/tools/)**: Code Interpreter, File Search, Web Search basics

Each example includes complete setup instructions, test data, and standardized `make` commands for easy execution.

## Features

### Core Capabilities

- Generate structured JSON output defined by dynamic prompts using OpenAI models and JSON schemas
- Rich template system for defining prompts (Jinja2-based)
- Automatic token counting and context window management
- Streaming support for real-time output
- Secure handling of sensitive data with comprehensive path validation
- Automatic prompt optimization and token management

### Multi-Tool Integration

- **Code Interpreter**: Upload and analyze data files, execute Python code, generate visualizations
- **File Search**: Vector-based document search and retrieval from uploaded files
- **Web Search**: Real-time information retrieval and current data access via OpenAI's web search tool
- **MCP Servers**: Connect to Model Context Protocol servers for extended functionality
- **Explicit Tool Targeting**: Route files to specific tools (prompt, code-interpreter, file-search) with precise control

### Advanced Features

- **Upload Cache**: Persistent file upload cache eliminates duplicate uploads across runs, saving bandwidth and API costs
- **Configuration System**: YAML-based configuration with environment variable support
- **Gitignore Support**: Automatic .gitignore pattern matching for clean directory file collection
- **Unattended Operation**: Designed for CI/CD and automation scenarios
- **Progress Reporting**: Real-time progress updates with clear, user-friendly messaging
- **Model Registry**: Dynamic model management with support for latest OpenAI models
- **Optional File References**: Clean `file_ref()` function for automatic XML appendix, or direct file access for custom formatting

## Requirements

- Python 3.10 or higher

## Installation

We provide multiple installation methods to suit different user needs. Choose the one that's right for you.

<details>
<summary><strong>Recommended: pipx</strong></summary>

`pipx` is the recommended installation method. It installs `ostruct` in an isolated environment, preventing conflicts with other Python packages.

**macOS (with Homebrew):**

```bash
brew install pipx
pipx install ostruct-cli       # new users
pipx upgrade ostruct-cli       # existing users
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt install pipx
pipx install ostruct-cli       # new users
pipx upgrade ostruct-cli       # existing users
```

**Other systems:**

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
# Restart your terminal
pipx install ostruct-cli
```

</details>

<details>
<summary><strong>macOS: Homebrew</strong></summary>

If you're on macOS and use Homebrew, you can install `ostruct` with a single command:

```bash
brew install yaniv-golan/ostruct/ostruct-cli
```

</details>

<details>
<summary><strong>Standalone Binaries (No Python Required)</strong></summary>

We provide pre-compiled .zip archives for macOS, Windows, and Linux that do not require Python to be installed.

1. Go to the [**Latest Release**](https://github.com/yaniv-golan/ostruct/releases/latest) page.
2. Download the `.zip` file for your operating system (e.g., `ostruct-macos-latest.zip`, `ostruct-windows-latest.zip`, `ostruct-ubuntu-latest.zip`).
3. Extract the `.zip` file. This will create a folder (e.g., `ostruct-macos-amd64`).
4. On macOS/Linux, make the executable inside the extracted folder runnable:

    ```bash
    chmod +x /path/to/ostruct-macos-amd64/ostruct
    ```

5. Run the executable from within the extracted folder, as it depends on bundled libraries in the same directory.

</details>

<details>
<summary><strong>Docker</strong></summary>

If you prefer to use Docker, you can run `ostruct` from our official container image available on the GitHub Container Registry.

```bash
docker run -it --rm \
  -v "$(pwd)":/app \
  -w /app \
  ghcr.io/yaniv-golan/ostruct:latest \
  run template.j2 schema.json --file config input.txt
```

This command mounts the current directory into the container and runs `ostruct`.

</details>

### Uninstallation

To uninstall `ostruct`, use the method corresponding to how you installed it:

- **pipx**: `pipx uninstall ostruct-cli`
- **Homebrew**: `brew uninstall ostruct-cli`
- **Binaries**: Simply delete the binary file.
- **Docker**: No uninstallation is needed for the image itself, but you can remove it with `docker rmi ghcr.io/yaniv-golan/ostruct:latest`.

### Manual Installation

#### For Users

To install the latest stable version from PyPI:

```bash
pip install ostruct-cli
```

**Note**: If the `ostruct` command isn't found after installation, you may need to add Python's user bin directory to your PATH. See the [troubleshooting guide](docs/troubleshooting.md#installation--setup) for details.

#### For Developers

If you plan to contribute to the project, see the [Development Setup](#development-setup) section below for instructions on setting up the development environment with Poetry.

## Environment Variables

ostruct-cli respects the following environment variables:

**API Configuration:**

- `OPENAI_API_KEY`: Your OpenAI API key (required unless provided via command line)
- `OPENAI_API_BASE`: Custom API base URL (optional)
- `OPENAI_API_VERSION`: API version to use (optional)
- `OPENAI_API_TYPE`: API type (e.g., "azure") (optional)

**System Configuration:**

- `OSTRUCT_DISABLE_REGISTRY_UPDATE_CHECKS`: Set to "1", "true", or "yes" to disable automatic registry update checks
- `OSTRUCT_JSON_PARSING_STRATEGY`: JSON parsing strategy: "robust" (default, handles OpenAI API duplication bugs) or "strict" (fail on malformed JSON)
- `OSTRUCT_MCP_URL_<name>`: Custom MCP server URLs (e.g., `OSTRUCT_MCP_URL_stripe=https://mcp.stripe.com`)

**Upload Cache:**

- `OSTRUCT_CACHE_UPLOADS`: Enable/disable persistent upload cache (true/false, default: true)
- `OSTRUCT_CACHE_PATH`: Custom path for upload cache database
- `OSTRUCT_CACHE_ALGO`: Hash algorithm for file deduplication (sha256/sha1/md5, default: sha256)

**File Collection:**

- `OSTRUCT_IGNORE_GITIGNORE`: Set to "true" to ignore .gitignore files by default (default: "false")
- `OSTRUCT_GITIGNORE_FILE`: Default path to gitignore file (default: ".gitignore")

**Template Processing Limits (Template-only files via `--file alias path`):**

- `OSTRUCT_TEMPLATE_FILE_LIMIT`: Maximum individual file size for template access (default: no limit, was 64KB). Use "none", "unlimited", or empty string for no limit. Supports size suffixes: KB, MB, GB.
- `OSTRUCT_TEMPLATE_TOTAL_LIMIT`: Maximum total file size for all template files (default: no limit). Use "none", "unlimited", or empty string for no limit.
- `OSTRUCT_TEMPLATE_PREVIEW_LIMIT`: Maximum characters shown in template debugging previews (default: 4096)

> **Note**: Template limits only apply to files accessed via `--file alias path` (template-only routing). Files routed to Code Interpreter (`--file ci:`) or File Search (`--file fs:`) are not subject to these limits. The default behavior now allows unlimited file sizes to take full advantage of the context window.

**💡 Tip**: ostruct automatically loads `.env` files from the current directory. Environment variables take precedence over `.env` file values.

<details>
<summary><strong>Shell Completion Setup</strong> (Click to expand)</summary>

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

</details>

## Enhanced CLI with Multi-Tool Integration

ostruct provides multiple commands for different workflows:

- **`ostruct run`** - Main execution command for templates and schemas
- **`ostruct files`** - Dedicated file management (upload, cache, diagnostics)
- **`ostruct runx`** - Execute self-contained OST files
- **`ostruct scaffold`** - Generate templates and project scaffolding
- **`ostruct setup`** - Environment configuration and setup

### File Attachment System

ostruct provides a flexible file attachment system with explicit tool targeting:

#### Basic File Attachments

```bash
# Template access only (default - no tool upload)
ostruct run template.j2 schema.json --file config config.yaml

# Code Interpreter (data analysis, code execution)
ostruct run analysis.j2 schema.json --file ci:data data.csv

# File Search (document retrieval)
ostruct run search.j2 schema.json --file fs:docs documentation.pdf

# Multi-tool attachment (share between tools)
ostruct run workflow.j2 schema.json --file ci,fs:shared data.json
```

#### Directory Attachments

```bash
# Template-only directory access
ostruct run template.j2 schema.json --dir config ./config

# Upload directory to Code Interpreter
ostruct run analysis.j2 schema.json --dir ci:datasets ./data

# Upload directory to File Search
ostruct run search.j2 schema.json --dir fs:knowledge ./docs

# Directory with file pattern filtering
ostruct run template.j2 schema.json --dir source ./src --pattern "*.py"
```

#### File Collections

```bash
# Process multiple files from list
ostruct run batch.j2 schema.json --collect files @file-list.txt

# Upload collection to Code Interpreter
ostruct run analyze.j2 schema.json --collect ci:data @datasets.txt
```

#### Tool Targeting

The system uses explicit targets for precise control:

- **`prompt`** (default): Template access only, no upload
- **`code-interpreter`** or **`ci`**: Upload for Python execution and analysis
- **`file-search`** or **`fs`**: Upload to vector store for document search
- **Multi-target**: `ci,fs:alias` shares file between multiple tools

#### Development Best Practice: Always Use --dry-run

**Validate templates before execution** to catch errors early and save API costs:

```bash
# 1. Validate everything first (catches binary file issues, template errors)
ostruct run analysis.j2 schema.json --file ci:data report.xlsx --dry-run

# 2. If validation passes, run for real
ostruct run analysis.j2 schema.json --file ci:data report.xlsx
```

The `--dry-run` flag performs comprehensive validation including template rendering, catching issues like:

- Binary file content access errors
- Template syntax problems
- Missing template variables
- File accessibility issues

#### Security Modes

```bash
# Strict security with explicit allowlists
ostruct run template.j2 schema.json \
  --path-security strict \
  --allow /safe/directory \
  --allow-file /specific/file.txt \
  --file data input.txt
```

#### MCP Server Integration

```bash
# Connect to MCP servers for extended capabilities
ostruct run template.j2 schema.json --mcp-server deepwiki@https://mcp.deepwiki.com/sse
```

### Configuration System

Create an `ostruct.yaml` file for persistent settings:

```yaml
models:
  default: gpt-4o

tools:
  code_interpreter:
    auto_download: true
    output_directory: "./downloads"
    download_strategy: "two_pass_sentinel"  # Enable reliable file downloads

# JSON parsing configuration
json_parsing_strategy: robust  # Handle OpenAI API duplication bugs (default)

mcp:
  custom_server: "https://my-mcp-server.com"

limits:
  max_cost_per_run: 10.00
```

Load custom configuration:

```bash
ostruct --config my-config.yaml run template.j2 schema.json
```

### Model Validation

ostruct automatically validates model names against the OpenAI model registry. Only models that support structured output are available for selection, ensuring compatibility with JSON schema outputs.

```bash
   # See all available models with details
   ostruct models list

# Models are validated at command time
ostruct run template.j2 schema.json --model invalid-model
      # Error: Invalid model 'invalid-model'. Available models: gpt-4o, gpt-4o-mini, o1 (and 12 more).
      #        Run 'ostruct models list' to see all 15 available models.

# Shell completion works with model names
ostruct run template.j2 schema.json --model <TAB>
# Shows: gpt-4o  gpt-4o-mini  o1  o1-mini  o3-mini  ...
```

**Model Registry Updates:**

The model list is automatically updated when you run `ostruct models update`. If you encounter model validation errors, try updating your registry first:

```bash
# Update model registry
ostruct models update

# Check available models
ostruct models list
```

### Code Interpreter File Downloads

**✅ Enhanced Reliability**: ostruct now features a comprehensive multi-tier approach for Code Interpreter file downloads with improved error handling and automatic fallbacks. These enhancements significantly improve success rates but come with additional token usage and latency costs.

#### Key Improvements

- **🎯 Model-Specific Instructions**: Automatic prompt enhancement based on model reliability (gpt-4.1, gpt-4o, o4-mini)
- **🧐 Smart Download Strategy**: Raw HTTP downloads bypass OpenAI SDK limitations for container files
- **⏰ Container Expiry Detection**: Proactive tracking prevents stale download attempts
- **🛡️ Enhanced Error Handling**: Clear diagnostics with actionable suggestions
- **🔁 Exponential Backoff Retry**: Automatic retry with intelligent backoff for transient failures

#### Best Practices

```bash
# Recommended: Use gpt-4.1 for maximum reliability, add --ci-download for file outputs
ostruct run template.j2 schema.json --file ci:data data.csv --model gpt-4.1 --enable-tool code-interpreter --ci-download

# Include message field in schema for download links
{
  "type": "object",
  "properties": {
    "filename": {"type": "string"},
    "success": {"type": "boolean"},
    "message": {"type": "string"}  // ← Essential for download links
  },
  "required": ["filename", "success", "message"],
  "additionalProperties": false
}
```

#### Performance Considerations

- **Success Rate**: Significantly improved with proper schema and model selection
- **Timing**: Typical operations complete in 30-45 seconds
- **Token Usage**: Model-specific instructions add ~100-600 tokens per request
- **File Size Limit**: 100MB per download
- **Container Lifetime**: ~20 minutes
- **API Calls**: Two-pass strategy doubles API usage when needed for reliability

#### Troubleshooting

If you encounter download issues:

1. **Use gpt-4.1**: Most reliable model for file annotations
2. **Include message field**: Essential for download link inclusion
3. **Check verbose logs**: `--verbose` flag provides detailed diagnostics
4. **Verify file sizes**: Must be under 100MB limit

For general troubleshooting, see [docs/troubleshooting.md](docs/troubleshooting.md). For Code Interpreter-specific issues, see [docs/troubleshooting-ci-downloads.md](docs/troubleshooting-ci-downloads.md). For technical implementation details, see [docs/developer-ci-downloads.md](docs/developer-ci-downloads.md).

## Get Started Quickly

🚀 **New to ostruct?** Follow our [step-by-step quickstart guide](https://ostruct.readthedocs.io/en/latest/user-guide/quickstart.html) featuring Juno the beagle for a hands-on introduction.

📝 **Template Scripting:** Learn ostruct's templating capabilities with the [template scripting guide](https://ostruct.readthedocs.io/en/latest/user-guide/ostruct_template_scripting_guide.html) - no prior Jinja2 knowledge required!

📖 **Full Documentation:** <https://ostruct.readthedocs.io/>

## For LLMs: Quick Reference

🤖 **Teaching an LLM to use ostruct?** The [`llms.txt`](llms.txt) file provides a comprehensive, LLM-optimized reference covering all commands, flags, and usage patterns in a structured format.

**How to use `llms.txt`:**

1. **For AI assistants**: Include the entire file in your context when helping users with ostruct
2. **For training**: Use as reference material for LLM fine-tuning on ostruct usage
3. **For documentation**: Quick lookup of all CLI flags and command patterns
4. **For automation**: Parse the structured format to generate help text or validation
5. **Provide a stable URL**: Most modern LLMs can directly fetch and read the file. Pass the raw GitHub URL (e.g., `https://raw.githubusercontent.com/yaniv-golan/ostruct/main/llms.txt`) in your prompt instead of pasting the entire content.

The file follows the [llms.txt specification](https://llmstxt.org/#format) and includes:

- Complete command surface area with all subcommands
- All CLI flags organized by category (attachment, security, model, tools, etc.)
- Template functions and filters reference
- Best practices and operational limits
- Common usage patterns and heuristics

**Example usage in LLM prompts:**

```
Use the ostruct CLI reference available at:
https://raw.githubusercontent.com/yaniv-golan/ostruct/main/llms.txt

Now help the user create a template that analyzes CSV data using Code Interpreter.
```

### Quick Start

1. Set your OpenAI API key:

```bash
# Environment variable
export OPENAI_API_KEY=your-api-key

# Or create a .env file
echo 'OPENAI_API_KEY=your-api-key' > .env
```

### Example 1: Basic Text Extraction (Simplest)

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
        "name": {"type": "string", "description": "The person's full name"},
        "age": {"type": "integer", "description": "The person's age"},
        "occupation": {"type": "string", "description": "The person's job"}
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

# With enhanced options
echo "John Smith is a 35-year-old software engineer" | \
  ostruct run extract_person.j2 schema.json \
  --model gpt-4o \
  --temperature 0.7
```

### Example 2: Multi-Tool Data Analysis

1. Create an analysis template `analysis_template.j2`:

```jinja
Analyze the following data sources:

{% if sales_data_csv is defined %}
Sales Data: {{ sales_data_csv.name }} ({{ sales_data_csv.size }} bytes)
{% endif %}

{% if customer_data_json is defined %}
Customer Data: {{ customer_data_json.name }} ({{ customer_data_json.size }} bytes)
{% endif %}

{% if market_reports_pdf is defined %}
Market Reports: {{ market_reports_pdf.name }} ({{ market_reports_pdf.size }} bytes)
{% endif %}

{% if config_yaml is defined %}
Configuration: {{ config_yaml.content }}
{% endif %}

Provide comprehensive analysis and actionable insights.
```

2. Create an analysis schema `analysis_schema.json`:

```json
{
  "type": "object",
  "properties": {
    "analysis": {
      "type": "object",
      "properties": {
        "insights": {"type": "string", "description": "Key insights from the data"},
        "recommendations": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Actionable recommendations"
        },
        "data_quality": {"type": "string", "description": "Assessment of data quality"}
      },
      "required": ["insights", "recommendations"],
      "additionalProperties": false
    }
  },
  "required": ["analysis"],
  "additionalProperties": false
}
```

3. Use the attachment system for precise tool targeting:

```bash
# Basic multi-tool analysis
ostruct run analysis_template.j2 analysis_schema.json \
  --file ci:sales sales_data.csv \
  --file ci:customers customer_data.json \
  --file fs:reports market_reports.pdf \
  --file config config.yaml

# Multi-tool attachment with shared data
ostruct run analysis_template.j2 analysis_schema.json \
  --file ci,fs:shared_data data.json \
  --file prompt:config settings.yaml

# Directory-based analysis
ostruct run reusable_analysis.j2 analysis_schema.json \
  --dir ci:sales_data ./sales \
  --dir fs:documentation ./docs \
  --file config ./config.yaml

# Code review with multiple tool integration
ostruct run code_review.j2 review_schema.json \
  --dir ci:source ./src \
  --dir fs:docs ./documentation \
  --file config .eslintrc.json
```

<details>
<summary><strong>System Prompt Handling</strong> (Click to expand)</summary>

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

3. Shared system prompts (with template frontmatter):

   ```jinja
   ---
   include_system: shared/base_analyst.txt
   system_prompt: Focus on financial metrics
   ---
   Extract information from: {{ text }}
   ```

4. Default system prompt (built into the CLI)

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

</details>

## Self-Executing ostruct Prompts (OST)

🚀 **New Feature**: OST files are **self-executing ostruct prompts** that package templates into standalone executables with embedded schemas and custom CLI interfaces. Perfect for sharing AI-powered tools without requiring users to understand ostruct's complex syntax.

### What are OST Files?

**OST files are self-executing ostruct prompts** - `.ost` files that combine:

- **Jinja2 template content** for the AI prompt
- **JSON schema** embedded in YAML front-matter
- **CLI metadata** defining custom arguments and help text
- **Global argument policies** for controlling ostruct flags

### Regular ostruct vs OST Files

**Regular ostruct workflow:**

```bash
# Requires separate files and manual configuration
ostruct run template.j2 schema.json --var name="John" --file data.csv --model gpt-4o
```

- Template and schema are separate files
- User must know variable names and types
- Command-line becomes complex with many options
- No built-in help for template-specific usage

**OST file workflow:**

```bash
# Self-contained with custom CLI
./text-analyzer.ost "Hello world" --format json --help
```

- Everything bundled in one executable file
- Custom command-line arguments defined by template author
- Built-in help system: `./tool.ost --help` shows template-specific options
- User-friendly interface hides ostruct complexity

**Configuration Parameters:**
OST files determine which variables become command-line arguments, which files can be attached, and what customizations users can make. The template author pre-configures the experience while still allowing user flexibility.

### Creating Your First OST Template

Generate a complete OST template with the scaffold command:

```bash
# Create a self-executing template
ostruct scaffold template my_tool.ost --cli --name "text-analyzer" --description "Analyzes text content"

# Make it executable (Unix/Linux/macOS)
chmod +x my_tool.ost

# Run it directly
./my_tool.ost "Hello world" --format json --verbose
```

### OST Template Structure

Here's what a complete OST template looks like:

```yaml
#!/usr/bin/env -S ostruct runx
---
cli:
  name: text-analyzer
  description: Analyzes text content and extracts insights
  positional:
    - name: input_text
      help: Text to analyze
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
    # File routing examples
    config:
      names: ["--config"]
      help: Configuration file (template access)
      type: "file"
      target: "prompt"
    data:
      names: ["--data"]
      help: Data file for Code Interpreter analysis
      type: "file"
      target: "ci"

schema: |
  {
    "type": "object",
    "properties": {
      "analysis": {
        "type": "object",
        "properties": {
          "sentiment": {"type": "string"},
          "key_themes": {"type": "array", "items": {"type": "string"}},
          "word_count": {"type": "integer"}
        },
        "required": ["sentiment", "key_themes", "word_count"]
      }
    },
    "required": ["analysis"]
  }

defaults:
  format: "json"
  verbose: false

global_args:
  pass_through_global: true
  --model:
    mode: "allowed"
    allowed: ["gpt-4o", "gpt-4.1", "o1"]
    default: "gpt-4.1"
  --temperature:
    mode: "fixed"
    value: "0.7"
  --enable-tool:
    mode: "blocked"  # Prevent users from enabling tools
---
# Analyze the following text

Text to analyze: {{ input_text }}
Format requested: {{ format }}
Verbose mode: {{ verbose }}

{% if config is defined %}
Configuration: {{ config.content }}
{% endif %}

{% if data is defined %}
Data file available for analysis: {{ data.name }}
{% endif %}

Please analyze this text and provide insights about sentiment, key themes, and word count.
```

### Usage Examples

Once created, OST templates work like native CLI tools:

```bash
# Basic usage
./my_tool.ost "This is amazing!" --format json

# With file attachments
./my_tool.ost "Analyze this" --config settings.yaml --data report.csv

# Get help (automatically generated)
./my_tool.ost --help

# Dry run to test without API calls
ostruct runx my_tool.ost "test input" --dry-run
```

### Global Argument Policies

Control how users can interact with ostruct's global flags:

```yaml
global_args:
  pass_through_global: true  # Allow unknown flags
  --model:
    mode: "allowed"          # Restrict to specific models
    allowed: ["gpt-4o", "gpt-4.1"]
    default: "gpt-4.1"
  --temperature:
    mode: "fixed"            # Lock to specific value
    value: "0.7"
  --enable-tool:
    mode: "blocked"          # Completely prevent usage
  --verbose:
    mode: "pass-through"     # Allow any value
```

**Policy Modes:**

- **`allowed`**: Restrict to whitelisted values
- **`fixed`**: Lock to a specific value, reject overrides
- **`blocked`**: Completely prevent flag usage
- **`pass-through`**: Allow any value (default)

### Cross-Platform Execution

#### Unix/Linux/macOS

```bash
# Direct execution via shebang
./my_tool.ost "input text"

# Or via ostruct command
ostruct runx my_tool.ost "input text"
```

#### Windows Support

On Windows, OST templates can be executed using:

```cmd
# Via ostruct command (works everywhere)
ostruct runx my_tool.ost "input text"

# With Windows launcher (optional)
ostruct scaffold template my_tool.ost --cli --windows-launcher
my_tool_launcher.exe "input text"
```

The Windows launcher uses the same distlib binary that every pip user already has, minimizing antivirus false positives and ensuring reliability.

**Security Note**: The Windows launcher executable is generated using distlib's simple-launcher technology. This is the same trusted binary infrastructure that pip itself uses for console scripts. Since this binary is already present on every system with pip installed, it significantly reduces the likelihood of antivirus false positives compared to custom executable generation. For more details, see the [distlib documentation](https://github.com/pypa/distlib/issues/192) and [PyPI project page](https://pypi.org/project/distlib/).

### File Routing in OST Templates

OST templates support all ostruct file routing targets:

```yaml
options:
  template_file:
    names: ["--template-file"]
    type: "file"
    target: "prompt"          # Template access only

  analysis_data:
    names: ["--data"]
    type: "file"
    target: "ci"              # Code Interpreter analysis

  documentation:
    names: ["--docs"]
    type: "file"
    target: "fs"              # File Search retrieval

  user_document:
    names: ["--pdf"]
    type: "file"
    target: "ud"              # User-data for vision models

  auto_file:
    names: ["--auto"]
    type: "file"
    target: "auto"            # Auto-route by file type
```

### Advanced Features

#### Multi-Tool Integration

```bash
# OST files pre-configure their tool usage internally - users get clean interfaces
./data-analyzer.ost sales_data.csv --include-charts --output-format json

# The OST template author handles complexity like --enable-tool and --ci-download internally
# Users never need to know about ostruct's raw flags
```

#### Environment Setup

```bash
# Register OST file associations on Windows
ostruct setup windows-register

# Unregister when no longer needed
ostruct setup windows-unregister
```

#### Template Debugging

```bash
# Test template rendering without API calls
ostruct runx my_tool.ost "test input" --dry-run

# Verbose debugging
ostruct runx my_tool.ost "test input" --verbose --debug
```

### Best Practices

1. **Use descriptive CLI names**: `--input-file` instead of `--file`
2. **Provide helpful descriptions**: Users see these in `--help`
3. **Set sensible defaults**: Reduce required arguments
4. **Use appropriate file targets**: `ci` for analysis, `fs` for search, `prompt` for templates
5. **Test with `--dry-run`**: Validate before live execution
6. **Version your templates**: OST files are self-contained and portable

### Security Considerations

- **Path validation**: OST templates respect ostruct's security policies
- **Policy enforcement**: Global argument policies prevent unauthorized access
- **Sandboxed execution**: Templates run in isolated environments
- **Audit trail**: All executions are logged and traceable

OST templates make AI-powered tools accessible to non-technical users while maintaining the full power and flexibility of ostruct underneath.

## Model Registry Management

ostruct-cli maintains a registry of OpenAI models and their capabilities, which includes:

- Context window sizes for each model
- Maximum output token limits
- Supported parameters and their constraints
- Model version information

To ensure you're using the latest models and features, you can update the registry:

```bash
# Update from the official repository
ostruct models update

# Update from a custom URL
ostruct models update --url https://example.com/models.yml

# Force an update even if the registry is current
ostruct models update --force
```

This is especially useful when:

- New OpenAI models are released
- Model capabilities or parameters change
- You need to work with custom model configurations

The registry file is stored at `~/.openai_structured/config/models.yml` and is automatically referenced when validating model parameters and token limits.

The update command uses HTTP conditional requests (If-Modified-Since headers) to check if the remote registry has changed before downloading, ensuring efficient updates.

# Testing

## Running Tests

The test suite is divided into two categories:

### Regular Tests (Default)

```bash
# Run all tests (skips live tests by default)
pytest

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v
```

### Live Tests

Live tests make real API calls to OpenAI and require a valid API key. They are skipped by default.

```bash
# Run only live tests (requires OPENAI_API_KEY)
pytest -m live

# Run all tests including live tests
pytest -m "live or not live"

# Run specific live test
pytest tests/test_responses_annotations.py -m live
```

**Live tests include:**

- Tests that make actual OpenAI API calls
- Tests that run `ostruct` commands via subprocess
- Tests that verify real API behavior and file downloads

**Requirements for live tests:**

- Valid `OPENAI_API_KEY` environment variable
- Internet connection
- May incur API costs

## Test Markers

- `@pytest.mark.live` - Tests that make real API calls or run actual commands
- `@pytest.mark.no_fs` - Tests that need real filesystem (not pyfakefs)
- `@pytest.mark.slow` - Performance/stress tests
- `@pytest.mark.flaky` - Tests that may need reruns
- `@pytest.mark.mock_openai` - Tests using mocked OpenAI client

<!--
MAINTAINER NOTE: After editing this README, please test GitHub rendering by:
1. Creating a draft PR or pushing to a test branch
2. Verifying all HTML <details> sections expand/collapse correctly
3. Checking badge display and links work as expected
4. Ensuring quickstart guide link is functional
-->
