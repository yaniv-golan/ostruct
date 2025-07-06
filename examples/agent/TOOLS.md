# Agent Tools Documentation

This document describes the 10 tools available to the sandboxed agent system.

## Text Processing Tools

### jq
JSON filtering and transformation with stdin support.

**Parameters:**
- `filter`: jq filter expression (required)
- `input`: optional input file path (if not provided, uses stdin)

**Limits:**
- Maximum output size: 32KB

**Example:**
```json
{
  "tool": "jq",
  "filter": ".users[] | select(.active == true)",
  "input": "users.json"
}
```

### grep
Pattern search with line numbers for file content.

**Parameters:**
- `pattern`: search pattern (required)
- `file`: file path to search in (required)

**Limits:**
- Maximum file size: 32KB

**Example:**
```json
{
  "tool": "grep",
  "pattern": "error",
  "file": "logs/app.log"
}
```

### sed
Read-only line extraction using sed expressions.

**Parameters:**
- `expression`: sed expression for line extraction (required)
- `file`: file path to process (required)

**Limits:**
- Maximum file size: 32KB

**Example:**
```json
{
  "tool": "sed",
  "expression": "1,10p",
  "file": "data.txt"
}
```

### awk
Field and line processing using awk scripts.

**Parameters:**
- `script`: awk script (required)
- `file`: file path to process (required)

**Limits:**
- Maximum file size: 32KB

**Example:**
```json
{
  "tool": "awk",
  "script": "{ print $1, $3 }",
  "file": "data.csv"
}
```

## Network Tools

### curl
HTTP download with size limit enforcement.

**Parameters:**
- `url`: URL to download (required)

**Limits:**
- Maximum download size: 10MB

**Example:**
```json
{
  "tool": "curl",
  "url": "https://api.example.com/data.json"
}
```

### download_file
Save HTTP resource to sandbox with size validation.

**Parameters:**
- `url`: URL to download (required)
- `path`: local path to save file (required)

**Limits:**
- Maximum download size: 10MB

**Example:**
```json
{
  "tool": "download_file",
  "url": "https://example.com/file.pdf",
  "path": "downloads/file.pdf"
}
```

## File Operations

### write_file
Create or overwrite file with size check.

**Parameters:**
- `path`: file path to write (required)
- `content`: content to write (required)

**Limits:**
- Maximum file size: 32KB

**Example:**
```json
{
  "tool": "write_file",
  "path": "output.txt",
  "content": "Hello, World!"
}
```

### append_file
Append content to file with size check.

**Parameters:**
- `path`: file path to append to (required)
- `content`: content to append (required)

**Limits:**
- Maximum file size: 32KB (total file size after append)

**Example:**
```json
{
  "tool": "append_file",
  "path": "log.txt",
  "content": "New log entry\n"
}
```

### read_file
Read file content with size limit.

**Parameters:**
- `path`: file path to read (required)

**Limits:**
- Maximum file size: 32KB

**Example:**
```json
{
  "tool": "read_file",
  "path": "config.json"
}
```

### text_replace
Safe search and replace with hit counting.

**Parameters:**
- `file`: file path to process (required)
- `search`: text to search for (required)
- `replace`: text to replace with (required)

**Limits:**
- Maximum file size: 32KB
- Maximum replacements: 1000

**Example:**
```json
{
  "tool": "text_replace",
  "file": "config.txt",
  "search": "old_value",
  "replace": "new_value"
}
```

## Security Notes

1. All file operations are confined to the sandbox directory
2. Path traversal attempts (../) are blocked
3. Symlinks pointing outside the sandbox are rejected
4. Size limits are strictly enforced
5. All operations timeout after reasonable duration
6. Network access is limited to HTTP/HTTPS downloads only

## Error Handling

- Tools return structured error messages on failure
- Size limit violations are reported with specific limits
- Path security violations are logged and blocked
- Network timeouts are handled gracefully
- All errors include diagnostic information for debugging