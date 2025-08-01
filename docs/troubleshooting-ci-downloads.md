# Troubleshooting Code Interpreter File Downloads

This guide helps resolve common issues with Code Interpreter file downloads in ostruct.

## Overview

Code Interpreter file downloads in ostruct use a multi-tier approach to work around known OpenAI API limitations and improve reliability:

1. **Model-specific instructions** enhance AI compliance
2. **Container expiry detection** prevents stale download attempts
3. **Raw HTTP downloads** bypass OpenAI SDK limitations
4. **Enhanced error handling** provides clear diagnostics
5. **Exponential backoff retry** handles transient failures

**Note**: These enhancements address several OpenAI API bugs, particularly with structured output mode preventing file download annotations. For detailed technical information, see [docs/known-issues/2025-06-responses-ci-file-output.md](../known-issues/2025-06-responses-ci-file-output.md).

## Common Issues & Solutions

### 1. Files Created But Not Downloaded

**Symptoms:**

- AI creates files successfully
- No download links appear in output
- Warning: "Failed to download generated files"

**Causes & Solutions:**

#### Missing Download Links in Schema

```json
{
  "type": "object",
  "properties": {
    "filename": {"type": "string"},
    "success": {"type": "boolean"},
    "message": {"type": "string"}  // ← Include this!
  },
  "required": ["filename", "success"],
  "additionalProperties": false
}
```

**Solution:** Always include a `message` field in your schema to allow the AI to provide download links.

#### Model Not Following Instructions

Some models are less reliable at including download links. ostruct automatically applies model-specific instructions:

- **gpt-4.1**: Strong "CRITICAL FILE HANDLING" instructions
- **gpt-4o**: Moderate "File Handling Notes"
- **o4-mini**: "MANDATORY FILE DOWNLOAD" instructions

**Solution:** Use gpt-4.1 for best reliability, or include explicit download instructions in your template.

### 2. Container Expiry Errors

**Symptoms:**

- Error: "Container expired or file not found"
- Downloads fail after successful file creation

**Cause:** OpenAI containers expire after ~20 minutes

**Solutions:**

- **Immediate**: Re-run the command - ostruct will create a fresh container
- **Prevention**: Complete file operations within 20 minutes
- **Monitoring**: Check logs for container age warnings

### 3. SDK Download Limitations

**Symptoms:**

- Files with `cfile_` prefix fail to download via SDK
- "SDK limitation" errors in logs

**Cause:** OpenAI Python SDK doesn't support container file downloads

**Solution:** ostruct automatically uses raw HTTP downloads for `cfile_` files. This is handled transparently.

### 4. Network Timeouts

**Symptoms:**

- "Download timed out after 30 seconds"
- Large files fail to download

**Solutions:**

- **File Size**: Check if files exceed 100MB limit
- **Network**: Verify stable internet connection
- **Retry**: ostruct automatically retries with exponential backoff

### 5. Rate Limiting

**Symptoms:**

- HTTP 429 errors
- "Rate limited" messages

**Solution:** ostruct includes built-in rate limit handling with exponential backoff. Wait and retry.

## Diagnostic Commands

### Test Basic Functionality

```bash
# Simple test with gpt-4.1 (most reliable)
ostruct run template.j2 schema.json --model gpt-4.1 --enable-tool code-interpreter --verbose
```

### Check Model-Specific Instructions

```bash
# View the expanded template with model-specific instructions applied
ostruct run template.j2 schema.json --model gpt-4.1 --enable-tool code-interpreter --template-debug post-expand --dry-run
```

### Test Different Models

```bash
# Compare reliability across models
for model in gpt-4.1 gpt-4o o4-mini; do
  echo "Testing $model..."
  ostruct run template.j2 schema.json --model $model --enable-tool code-interpreter
done
```

## Best Practices

### Template Design

```jinja2
Create a chart and save it as 'analysis.png'.
Include a download link in your response.

Data: {{ data }}
```

### Schema Design

```json
{
  "type": "object",
  "properties": {
    "filename": {"type": "string"},
    "success": {"type": "boolean"},
    "message": {"type": "string"},
    "file_size": {"type": "integer"}
  },
  "required": ["filename", "success", "message"],
  "additionalProperties": false
}
```

### Command Usage

```bash
# Recommended: Use gpt-4.1 with verbose logging
ostruct run template.j2 schema.json \
  --model gpt-4.1 \
  --enable-tool code-interpreter \
  --verbose
```

## Performance Expectations

Based on testing:

- **Success Rate**: Significantly improved with gpt-4.1 + proper schema
- **Typical Timing**: 30-45 seconds for chart generation
- **File Size Limit**: 100MB per download
- **Container Lifetime**: ~20 minutes

## Error Reference

### Download Error Types

| Error Type | Description | Solution |
|------------|-------------|----------|
| `container_expired` | Container > 20min old | Re-run command |
| `sdk_limitation` | SDK can't download file | Automatic raw HTTP fallback |
| `network_timeout` | Download > 30s | Check file size/network |
| `api_rate_limit` | Too many requests | Automatic retry with backoff |
| `file_not_found` | File missing from container | Check AI response for errors |
| `annotation_missing` | No download metadata | Improve template instructions |

### Log Analysis

Look for these patterns in verbose logs:

```
✅ Good signs:
- "CRITICAL FILE HANDLING" (instructions applied)
- "Download activity detected" (files being processed)
- "container_file_citation" (proper annotations)

⚠️ Warning signs:
- "No sentinel JSON found" (missing download metadata)
- "Container age: 18+ minutes" (expiry approaching)
- "SDK limitation" (expected for cfile_ downloads)

❌ Error signs:
- "Container expired" (need fresh container)
- "No valid JSON output" (model/schema issues)
- "Rate limited" (temporary - will retry)
```

## Getting Help

If issues persist:

1. **Check logs** with `--verbose` flag
2. **Test with gpt-4.1** (most reliable model)
3. **Verify schema** includes `message` field
4. **Review template** for explicit download instructions
5. **Check file sizes** (must be < 100MB)

For complex scenarios, consult the developer documentation or create isolated test cases to diagnose specific issues.

## See Also

- **[Known Issues](known-issues/2025-06-responses-ci-file-output.md)** - OpenAI API bug details and workarounds
- **[Developer Implementation Guide](developer-ci-downloads.md)** - Technical details for contributors
