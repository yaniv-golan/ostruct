# Sandboxed Agent System

A safe, controlled execution environment for LLM-planned tasks using ostruct. This system provides an autonomous agent that can break down complex tasks into executable steps using a curated set of tools.

## Overview

The sandboxed agent system consists of:

- **PlannerGPT**: Creates initial execution plans for tasks
- **ReplanGPT**: Adapts plans based on execution results
- **Tool Executor**: Safely executes commands in a sandboxed environment
- **State Manager**: Tracks execution history and progress

## Quick Start

1. **Install Dependencies**

   ```bash
   # Ensure required tools are installed
   sudo apt-get install jq curl gawk
   ```

2. **Run a Simple Task**

   ```bash
   cd examples/agent
   ./runner.sh "Create a file named hello.txt with the content 'Hello, World!'"
   ```

3. **Check Results**

   ```bash
   # View logs
   tail -f logs/run_*.log

   # Check sandbox contents
   ls -la workdir/sandbox_*/
   ```

## Architecture

### Components

- **`runner.sh`**: Main orchestrator script
- **`tools.json`**: Tool catalog and specifications
- **`schemas/`**: JSON schemas for validation
- **`templates/`**: Jinja2 templates for LLM prompts
- **`logs/`**: Execution logs (auto-generated)
- **`workdir/`**: Sandbox directories (auto-generated)

### Execution Flow

1. **Planning**: PlannerGPT analyzes the task and creates an initial plan
2. **Execution**: Each step is executed safely in the sandbox
3. **Replanning**: ReplanGPT adapts the plan based on results
4. **Iteration**: Process repeats until task completion or failure

## Available Tools

The agent has access to 10 carefully selected tools:

### Text Processing

- **jq**: JSON filtering and transformation
- **grep**: Pattern search with line numbers
- **sed**: Read-only line extraction
- **awk**: Field and line processing

### Network Operations

- **curl**: HTTP downloads (10MB limit)
- **download_file**: Save HTTP resources to sandbox

### File Operations

- **read_file**: Read file contents (32KB limit)
- **write_file**: Create or overwrite files
- **append_file**: Append to files
- **text_replace**: Safe search and replace

See [TOOLS.md](TOOLS.md) for detailed tool documentation.

## Security Features

### Sandbox Isolation

- All operations confined to per-run sandbox directories
- Path traversal attempts are blocked
- Symlinks pointing outside sandbox are rejected

### Size Limits

- File operations: 32KB maximum
- Downloads: 10MB maximum
- Text replacements: 1000 hit limit

### Resource Controls

- Maximum execution turns: 10
- Maximum ostruct calls: 20
- Command timeouts: 30-60 seconds
- Automatic cleanup of temporary files

## Configuration

### Environment Variables

- `MAX_TURNS`: Maximum execution turns (default: 10)
- `MAX_OSTRUCT_CALLS`: Maximum LLM calls (default: 20)
- `FILE_SIZE_LIMIT`: File size limit in bytes (default: 32KB)
- `DOWNLOAD_SIZE_LIMIT`: Download size limit in bytes (default: 10MB)

### Logging Levels

- `INFO`: General execution flow
- `DEBUG`: Detailed step information
- `WARN`: Non-fatal issues
- `ERROR`: Critical failures

## Usage Examples

### Simple File Operations

```bash
./runner.sh "Create a CSV file with sample data and calculate the sum of a column"
```

### Web Data Processing

```bash
./runner.sh "Download JSON data from a public API and extract specific fields"
```

### Multi-Step Analysis

```bash
./runner.sh "Download a text file, count word frequencies, and create a report"
```

### Error Recovery

```bash
./runner.sh "Try to download a file, if it fails, create a default file instead"
```

## Troubleshooting

### Common Issues

**"Maximum ostruct calls exceeded"**

- The agent made too many LLM calls
- Increase `MAX_OSTRUCT_CALLS` or simplify the task

**"Path escape attempt detected"**

- Tool tried to access files outside sandbox
- This is a security feature - check tool parameters

**"File too large"**

- File exceeds size limits
- Use streaming tools or increase limits carefully

**"Tool execution timeout"**

- Command took too long to execute
- Break down complex operations into smaller steps

### Debugging

1. **Check Logs**

   ```bash
   tail -f logs/run_*.log
   ```

2. **Examine State**

   ```bash
   cat workdir/sandbox_*/agent_state.json | jq .
   ```

3. **Inspect Sandbox**

   ```bash
   ls -la workdir/sandbox_*/
   ```

4. **Test Tools Manually**

   ```bash
   # Test jq
   echo '{"test": "value"}' | jq '.test'

   # Test curl
   curl -s --max-filesize 1000000 https://httpbin.org/json
   ```

## Development

### Adding New Tools

1. **Update `tools.json`**

   ```json
   {
     "new_tool": {
       "description": "Tool description",
       "parameters": {
         "param1": "description"
       },
       "limits": {
         "max_size": "limit"
       }
     }
   }
   ```

2. **Update Schema**
   Add tool to enum in `schemas/plan_step.schema.json`

3. **Implement Executor**
   Add `execute_new_tool()` function in `runner.sh`

4. **Add to Switch Statement**
   Update the case statement in `execute_step()`

### Testing

1. **Unit Tests**

   ```bash
   ./test_agent.sh
   ```

2. **Integration Tests**

   ```bash
   ./runner.sh "Test task description"
   ```

3. **Security Tests**

   ```bash
   # Test path traversal protection
   ./runner.sh "Try to read /etc/passwd"

   # Test size limits
   ./runner.sh "Download a very large file"
   ```

## Best Practices

### Task Design

- Be specific about expected outputs
- Break complex tasks into clear sub-goals
- Specify file formats and locations

### Error Handling

- Tasks should be fault-tolerant
- Provide fallback strategies
- Include validation steps

### Performance

- Use appropriate tools for each task
- Avoid unnecessary file operations
- Consider size limits in task design

## Limitations

- No database operations (by design)
- No network services (outbound HTTP only)
- No system administration tasks
- Limited to ostruct-compatible LLMs
- Sandbox cannot persist between runs

## Security Considerations

- All operations are sandboxed
- No execution of arbitrary code
- Size limits prevent resource exhaustion
- Network access is read-only HTTP/HTTPS
- Comprehensive logging for audit trails

## License

This agent system is part of the ostruct project and follows the same license terms.

## Contributing

See the main ostruct contribution guidelines. When adding features:

1. Maintain security-first design
2. Add comprehensive tests
3. Update documentation
4. Follow bash best practices
