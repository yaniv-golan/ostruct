# Troubleshooting Guide

This guide helps diagnose and resolve common ostruct issues. For specialized problems, see the [specialized guides](#specialized-guides) below.

## Quick Diagnostics

### Test Basic Functionality

```bash
# Test basic ostruct installation and API connection
ostruct run --help

# Test with a simple template (no external dependencies)
echo "Hello {{name}}!" > test.j2
echo '{"type": "object", "properties": {"greeting": {"type": "string"}}, "required": ["greeting"], "additionalProperties": false}' > test.json
ostruct run test.j2 test.json --var name=World --dry-run
```

### Check Configuration

```bash
# View current configuration
ostruct --version
ostruct models list --show-deprecated

# Test API connection
ostruct models list | head -5
```

## Common Issues

### 1. Installation & Setup

#### Command Not Found: `ostruct`

**Symptoms:**

- `bash: ostruct: command not found`
- `zsh: command not found: ostruct`

**Solutions:**

```bash
# Recommended: pipx (isolated environment)
pipx install ostruct-cli       # new users
pipx upgrade ostruct-cli       # existing users

# Alternative: pip
pip install ostruct-cli

# macOS with Homebrew
brew install yaniv-golan/ostruct/ostruct-cli

# Check installation
which ostruct
ostruct --version

# For developers only (if working on ostruct source)
poetry install
poetry run ostruct --help
```

#### Import Errors

**Symptoms:**

- `ModuleNotFoundError: No module named 'ostruct'`
- Python import failures

**Solutions:**

```bash
# Reinstall with pipx (recommended)
pipx uninstall ostruct-cli
pipx install ostruct-cli

# Or reinstall with pip
pip uninstall ostruct-cli
pip install ostruct-cli

# Verify installation
python -c "import ostruct; print(ostruct.__version__)"

# For developers only (if working on ostruct source)
poetry install --sync
poetry env info
poetry show ostruct-cli
```

### 2. API Connection Issues

#### No OpenAI API Key

**Symptoms:**

- `[API_ERROR] No OpenAI API key found`
- Authentication failures

**Solutions:**

```bash
# Set API key in environment
export OPENAI_API_KEY="your-api-key-here"

# Or create .env file
echo "OPENAI_API_KEY=your-api-key-here" > .env

# Test API connection
ostruct models list | head -3
```

#### API Connection Failures

**Symptoms:**

- Network timeouts
- Connection refused errors
- SSL/TLS errors

**Solutions:**

```bash
# Test network connectivity
curl -I https://api.openai.com/v1/models

# Check API key validity
ostruct models list

# Use verbose logging for diagnosis
ostruct run template.j2 schema.json --verbose --dry-run
```

#### Rate Limiting

**Symptoms:**

- `HTTP 429: Too Many Requests`
- `Rate limit exceeded`

**Solutions:**

- **Wait**: Rate limits reset automatically
- **Reduce frequency**: Space out requests
- **Check quota**: Verify OpenAI account limits
- **Upgrade plan**: Consider higher rate limit tiers

### 3. Model & Configuration Issues

#### Model Not Found

**Symptoms:**

- `Model 'model-name' not found`
- Invalid model errors

**Solutions:**

```bash
# List available models
ostruct models list

# Use a known working model
ostruct run template.j2 schema.json --model gpt-4.1

# Check model registry updates
ostruct models update
```

#### Schema Validation Errors

**Symptoms:**

- `Invalid schema` errors
- JSON schema validation failures
- `additionalProperties` errors

**Solutions:**

```bash
# Validate schema format
python -c "import json; print(json.load(open('schema.json')))"

# Add required properties
# Ensure schema includes: "additionalProperties": false

# Test with minimal schema
echo '{"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"], "additionalProperties": false}' > minimal.json
```

### 4. Template Issues

#### Template Syntax Errors

**Symptoms:**

- Jinja2 syntax errors
- Variable not found errors
- Template rendering failures

**Solutions:**

```bash
# Test template syntax
ostruct run template.j2 schema.json --dry-run --verbose

# Debug template expansion
ostruct run template.j2 schema.json --template-debug post-expand --dry-run

# Check variable definitions
ostruct run template.j2 schema.json --var name=value --dry-run
```

#### File Reference Issues

**Symptoms:**

- File not found errors
- Attachment failures
- Variable access errors

**Solutions:**

```bash
# Check file paths
ls -la your-file.txt

# Test file attachment (template access)
ostruct run template.j2 schema.json --file data your-file.txt --dry-run

# Test Code Interpreter file attachment
ostruct run template.j2 schema.json --file ci:data your-file.csv --dry-run

# Debug file processing
ostruct run template.j2 schema.json --file data your-file.txt --verbose --dry-run
```

For detailed template troubleshooting, see [template_troubleshooting.md](template_troubleshooting.md).

### 5. Tool Integration Issues

#### Code Interpreter Problems

**Symptoms:**

- Files created but not downloaded
- Tool enablement failures
- Container expiry errors

**Solutions:**

```bash
# Test Code Interpreter with file
ostruct run template.j2 schema.json --file ci:data data.csv --enable-tool code-interpreter --model gpt-4.1 --verbose

# Check schema includes message field
# Ensure your schema has: "message": {"type": "string"}

# Use most reliable model
ostruct run template.j2 schema.json --file ci:data data.csv --enable-tool code-interpreter --model gpt-4.1
```

For detailed Code Interpreter troubleshooting, see [troubleshooting-ci-downloads.md](troubleshooting-ci-downloads.md).

#### MCP Server Issues

**Symptoms:**

- MCP server connection failures
- Tool registration errors

**Solutions:**

```bash
# Test MCP server configuration
ostruct run template.j2 schema.json --mcp-server api@https://example.com/mcp/sse --dry-run --verbose

# Check server accessibility
curl -I your-mcp-server-url

# Validate MCP configuration format
```

#### Web Search Issues

**Symptoms:**

- Web search tool not working
- No search results returned
- Geographic targeting issues

**Solutions:**

```bash
# Test Web Search tool
ostruct run template.j2 schema.json --enable-tool web-search --ws-context-size low --dry-run --verbose

# Test with geographic targeting
ostruct run template.j2 schema.json --enable-tool web-search --ws-country US --ws-region Americas

# Force web search usage
ostruct run template.j2 schema.json --tool-choice web-search --ws-context-size medium
```

### 6. Performance Issues

#### Slow Response Times

**Symptoms:**

- Commands taking > 60 seconds
- Timeout errors
- Poor performance

**Solutions:**

```bash
# Use faster models for testing
ostruct run template.j2 schema.json --model gpt-4o-mini

# Reduce file sizes
# Keep attachments under reasonable limits

# Check network connectivity
ping api.openai.com

# Use progress indicators
ostruct run template.j2 schema.json --progress detailed --verbose
```

#### Memory Issues

**Symptoms:**

- Out of memory errors
- Large file processing failures

**Solutions:**

```bash
# Check file sizes
ls -lh your-files/

# Use file size limits
# ostruct automatically limits downloads to 100MB

# Process files in smaller batches
```

## Diagnostic Commands

### Environment Check

```bash
# Complete environment diagnostic
echo "=== ostruct Environment Diagnostic ==="
echo "ostruct version: $(ostruct --version)"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "API key set: $([ -n "$OPENAI_API_KEY" ] && echo "YES" || echo "NO")"
echo "Available models: $(ostruct models list | wc -l) models"
echo "Poetry env: $(poetry env info --path 2>/dev/null || echo "Not using Poetry")"
```

### Connection Test

```bash
# Test full pipeline with minimal example
cat > diagnostic.j2 << 'EOF'
Test message: {{test_var}}
Current time: $(date)
EOF

cat > diagnostic.json << 'EOF'
{
  "type": "object",
  "properties": {
    "status": {"type": "string"},
    "message": {"type": "string"}
  },
  "required": ["status"],
  "additionalProperties": false
}
EOF

ostruct run diagnostic.j2 diagnostic.json --var test_var=diagnostic_test --model gpt-4.1 --verbose
```

### Debug Logging

```bash
# Maximum verbosity for troubleshooting
ostruct run template.j2 schema.json \
  --verbose \
  --debug \
  --progress detailed \
  --template-debug post-expand \
  --dry-run
```

## Getting Help

### 1. Check Logs

Always run with `--verbose` to see detailed operation logs:

```bash
ostruct run template.j2 schema.json --verbose 2>&1 | tee ostruct.log
```

### 2. Minimal Reproduction

Create the smallest possible example that reproduces your issue:

```bash
# Minimal template
echo "Simple test: {{var}}" > minimal.j2

# Minimal schema
echo '{"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"], "additionalProperties": false}' > minimal.json

# Test command
ostruct run minimal.j2 minimal.json --var var=test --verbose
```

### 3. Environment Information

When reporting issues, include:

```bash
# System info
ostruct --version
python --version
poetry --version  # if using Poetry
echo $OPENAI_API_KEY | cut -c1-10  # First 10 chars only

# Configuration
ostruct models list | head -5
ls -la .env  # if using .env file
```

## Specialized Guides

For specific problem areas, consult these specialized troubleshooting guides:

- **[Template Issues](template_troubleshooting.md)** - Template syntax, variables, file attachments
- **[Code Interpreter Downloads](troubleshooting-ci-downloads.md)** - File download issues, container problems
- **[Template Debugging](template_debugging.md)** - Advanced debugging techniques and tools
- **[Known Issues](known-issues/)** - Documented bugs and workarounds

## Common Error Patterns

### JSON Schema Errors

```
Error: Invalid schema for response_format
Solution: Add "additionalProperties": false to your schema
```

### Template Variable Errors

```
Error: Variable 'name' not found in template context
Solution: Add --var name=value or check variable spelling
```

### API Authentication Errors

```
Error: No OpenAI API key found
Solution: Set OPENAI_API_KEY environment variable
```

### File Attachment Errors

```
Error: File not found: path/to/file.txt
Solution: Check file path and permissions
```

If you've tried these solutions and still have issues, create a minimal reproduction case and consult the specialized guides or seek community support.
