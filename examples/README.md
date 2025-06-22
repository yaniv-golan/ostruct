# ostruct Examples

This directory contains practical examples demonstrating ostruct's capabilities for structured AI output generation with various integrations.

## 🚀 New Template Features

### File Reference System

Examples now use the new `file_ref()` function for cleaner syntax and automatic XML appendix generation:

```jinja2
{# Old approach - manual file iteration #}
{% for file in source %}
{{ file.content }}
{% endfor %}

{# New approach - automatic XML appendix #}
Analyze the code in {{ file_ref("source") }}.
```

### Safe Variable Access

Examples use `safe_get()` for robust variable access with defaults:

```jinja2
{# Old approach - default filter #}
{{ scan_type | default('full') }}

{# New approach - safe_get function #}
{{ safe_get('scan_type', 'full') }}
```

## 📁 Example Categories

### 🔍 Analysis & Review

- **[code-quality/code-review](code-quality/code-review/)** - Automated code review with file references
- **[security/vulnerability-scan](security/vulnerability-scan/)** - Multi-modal security analysis
- **[document-analysis](document-analysis/)** - Document processing and validation
- **[data-analysis](data-analysis/)** - Data analysis with multiple file types

### 🛠️ Development Tools

- **[testing/test-generation](testing/test-generation/)** - Automated test case generation
- **[debugging](debugging/)** - Template debugging and optimization examples
- **[config-validation](config-validation/)** - Configuration file validation
- **[meta-schema-generator](meta-schema-generator/)** - JSON schema generation from templates

### 🤖 AI Workflows

- **[multi_agent_debate](multi_agent_debate/)** - Multi-agent debate simulation with web search
- **[web-search](web-search/)** - Web search integration examples
- **[arg_to_aif](arg_to_aif/)** - Argument structure extraction

### 🏗️ Infrastructure & Automation

- **[infrastructure](infrastructure/)** - CI/CD and automation examples
- **[migration](migration/)** - Migration and automation strategies
- **[optimization](optimization/)** - Performance optimization examples

## 🎯 Key Template Patterns

### 1. File Reference Pattern

Use `file_ref()` for clean file references with automatic XML appendix:

```jinja2
# Security Analysis Example
Review the code in {{ file_ref("source") }}.
Check configuration in {{ file_ref("config") }}.

# Results in template with <source> and <config> references
# Plus automatic XML appendix with file contents
```

### 2. Safe Variable Access Pattern

Use `safe_get()` for robust variable handling:

```jinja2
# Configuration with defaults
- Analysis Type: {{ safe_get('analysis_type', 'comprehensive') }}
- Focus Areas: {{ safe_get('focus_areas', ['general']) | join(', ') }}
- Minimum Severity: {{ safe_get('min_severity', 'low') }}
```

### 3. Conditional Logic Pattern

Combine both patterns for robust templates:

```jinja2
{% if safe_get('web_search_enabled', false) %}
Research {{ topic }} using web search capabilities.
{% else %}
Analyze {{ topic }} using available training data.
{% endif %}

Review the documentation: {{ file_ref("docs") }}
```

## 🚦 Migration Status

All examples have been migrated to use the new patterns:

✅ **Migrated Examples:**

- Code quality and security analysis templates
- Testing and debugging templates
- Configuration validation templates
- Document analysis and schema generation
- Web search and research templates
- Multi-agent debate templates (already used safe_get)

🔧 **Template Improvements:**

- Cleaner, more readable template syntax
- Automatic XML appendix generation for files
- Robust variable access with sensible defaults
- Better error handling and template validation

## 📖 Usage Examples

### Basic File Analysis

```bash
# Code review with file references
ostruct run code-quality/code-review/prompts/task.j2 schema.json \
  --dir code src/ \
  --dry-run

# Security scan with multiple file types
ostruct run security/vulnerability-scan/prompts/task.j2 schema.json \
  --dir code_files src/ \
  --dir config_files config/ \
  --dry-run
```

### Web Search Integration

```bash
# Research analysis with web search
ostruct run web-search/flexible_analysis.j2 schema.json \
  -V topic="AI safety regulations" \
  -V depth="comprehensive" \
  --dry-run
```

### Multi-Modal Analysis

```bash
# Hybrid security analysis (static + code execution)
ostruct run security/vulnerability-scan/prompts/hybrid_analysis.j2 schema.json \
  --dir code src/ \
  --dry-run
```

## 🔗 Integration Examples

### File Search + Code Interpreter

```bash
# Document analysis with file search and code execution
ostruct run document-analysis/doc-example-validator/prompts/extract_examples.j2 schema.json \
  --dir docs:fs docs/ \
  --dry-run
```

### Template Debugging

```bash
# Debug template expansion
ostruct run debugging/template-expansion/debug_template.j2 schema.json \
  --file config_yaml config.yaml \
  --file code_files app.py \
  --template-debug
```

## 📚 Learning Path

1. **Start with [file-references](file-references/)** - Learn the new file reference system
2. **Try [debugging](debugging/)** - Understand template debugging and optimization
3. **Explore [code-quality](code-quality/)** - See practical analysis workflows
4. **Advanced: [multi_agent_debate](multi_agent_debate/)** - Complex multi-agent workflows

## 🛡️ Security & Privacy

When using file attachments:

- **Template files** (`--file alias file`) - Content included in main prompt
- **Code Interpreter files** (`--file ci:alias file`) - Uploaded to OpenAI Code Interpreter
- **File Search files** (`--file fs:alias file`) - Uploaded to OpenAI File Search

Review the [Security Overview](../docs/source/security/overview.rst) for detailed information.

## 🤝 Contributing

When adding new examples:

1. Use `file_ref()` for file references where appropriate
2. Use `safe_get()` for variable access with defaults
3. Include comprehensive JSON schemas
4. Add README with usage instructions
5. Test with both `--dry-run` and live execution

For detailed contribution guidelines, see [Contributing Guide](../docs/source/contribute/how_to_contribute.rst).
