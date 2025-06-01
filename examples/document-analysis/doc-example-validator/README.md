# Documentation Example Validator

This example demonstrates ostruct's ability to analyze project documentation using File Search integration to extract and validate all code examples. The system uploads documentation files to a vector store, analyzes them with AI, and outputs a structured task list for testing every example found in the documentation.

## 🔒 Security & Data Privacy Notice

**⚠️ IMPORTANT**: This example uses File Search (`-fs`) features that **upload your documentation files to OpenAI's services** for processing.

**Before using with your documentation:**

- **Review content sensitivity** - Do not upload confidential, proprietary, or sensitive documentation
- **Consider documentation content** - Docs may contain internal implementation details, API keys, or business logic
- **Check data governance policies** - Verify your organization allows documentation uploads to external services

**For detailed information about data handling and security best practices**, see the [Security Overview](../../docs/source/security/overview.rst) documentation.

## Overview

- **Input**: Project directory with documentation files (Markdown, RST, etc.)
- **Processing**: File Search indexes all documentation, AI extracts examples
- **Output**: Structured JSON task list for validating all documentation examples
- **Tools Used**: File Search for documentation indexing and semantic search

## Quick Start

```bash
# Navigate to example directory
cd examples/document-analysis/doc-example-validator

# Analyze ostruct's own documentation
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds ../../../docs/ \
  -V project_name=ostruct \
  -V project_type=CLI \
  --model gpt-4o --temperature 0
```

## Features

- **Multi-Format Support**: Analyzes Markdown (.md), reStructuredText (.rst), plain text (.txt), and other documentation formats
- **Intelligent Example Detection**: Identifies code blocks, command examples, API usage patterns
- **Task List Generation**: Creates comprehensive validation tasks with dependencies and status tracking
- **Context-Aware Analysis**: Adapts example detection based on project type (CLI, API, Library, etc.)
- **Validation Strategy**: Generates specific test criteria and validation steps for each example
- **Agent-Ready Output**: Produces task lists compatible with AI coding agents (Cursor, Claude, etc.)

## Usage

### Basic Documentation Analysis

```bash
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds /path/to/project/docs/ \
  -V project_name="MyProject" \
  -V project_type="API" \
  --output-file example_tasks.json
```

### Advanced Analysis with Specific Files

```bash
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -fs README.md \
  -fs docs/installation.md \
  -ds docs/ \
  -V project_name="MyAPI" \
  -V project_type="REST_API" \
  -V include_setup_examples=true \
  --output-file api_example_tasks.json
```

### Command-Line Options

- `-ds <directory>`: Upload entire documentation directory to File Search
- `-fs <file>`: Upload specific documentation files to File Search
- `-V project_name=<name>`: Specify the project name for context-aware analysis
- `-V project_type=<type>`: Specify project type (CLI, API, Library, Framework, etc.)
- `-V include_setup_examples=<bool>`: Include installation/setup examples in analysis
- `-V validation_level=<level>`: Set validation depth (basic, comprehensive, exhaustive)

### Using the Test Data

The test data includes documentation in multiple formats to demonstrate format support:

- **Markdown**: README.md, changelog.md, installation.md, configuration.md
- **reStructuredText**: api_reference.rst
- **Plain Text**: troubleshooting.txt

```bash
# Run with provided sample project documentation (all formats)
./scripts/run_example.sh

# Test specific format combinations
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -fs test_data/sample_project/README.md \
  -fs test_data/sample_project/docs/api_reference.rst \
  -fs test_data/sample_project/docs/troubleshooting.txt \
  -V project_name="MultiFormat" \
  -V project_type="CLI"

# Validate output format
python scripts/validate_output.py example_tasks.json

# Dry run (validation only)
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds test_data/sample_project/ \
  -V project_name="SampleProject" \
  -V project_type="CLI" \
  --dry-run
```

## Output Format

The analysis produces a JSON object with the following structure:

```json
{
  "project_info": {
    "name": "ostruct",
    "type": "CLI",
    "documentation_files_analyzed": 15,
    "total_examples_found": 42
  },
  "task_management": {
    "instructions": "How to update task status and manage dependencies",
    "status_legend": {
      "PENDING": "Not started yet",
      "IN_PROGRESS": "Currently being worked on",
      "COMPLETED": "Task finished and verified",
      "FAILED": "Task failed validation",
      "BLOCKED": "Cannot proceed due to dependency"
    }
  },
  "tasks": [
    {
      "id": "T1.1",
      "title": "Validate Basic CLI Help Command",
      "status": "PENDING",
      "priority": "CRITICAL",
      "dependencies": [],
      "example_location": {
        "file": "README.md",
        "section": "Quick Start",
        "line_range": "15-17"
      },
      "example_content": "ostruct --help",
      "validation_criteria": [
        "Command executes without errors",
        "Help text includes all major options",
        "Exit code is 0"
      ],
      "test_instructions": [
        "Run: ostruct --help",
        "Verify output contains expected sections",
        "Check exit code"
      ],
      "expected_output_pattern": "usage: ostruct",
      "automation_ready": true
    }
  ]
}
```

### Task Status Management

Update task status by modifying the JSON file:

```bash
# Mark task as in progress
jq '.tasks[0].status = "IN_PROGRESS"' example_tasks.json > temp.json && mv temp.json example_tasks.json

# Mark task as completed with timestamp
jq '.tasks[0].status = "COMPLETED" | .tasks[0].completed_at = now' example_tasks.json > temp.json && mv temp.json example_tasks.json
```

### Priority Levels

- **CRITICAL**: Core functionality that must work (installation, basic usage)
- **HIGH**: Important features used by most users
- **MEDIUM**: Advanced features or edge cases
- **LOW**: Nice-to-have functionality or documentation examples

## Technical Details

### How It Works

1. **Documentation Discovery**: File Search indexes all documentation files in the specified directory
2. **Format Processing**: Handles multiple documentation formats (Markdown, RST, plain text) transparently
3. **Example Extraction**: AI analyzes documentation to identify code examples, commands, and usage patterns
4. **Context Analysis**: Determines project type and adapts example detection accordingly
5. **Task Generation**: Creates comprehensive validation tasks with dependencies and clear criteria
6. **Output Formatting**: Structures results as JSON compatible with AI coding agents

### Project Type Detection

The system adapts its analysis based on project type:

- **CLI**: Focuses on command-line examples, flag usage, subcommands
- **API**: Emphasizes API endpoints, request/response examples, authentication
- **Library**: Highlights import statements, function calls, configuration
- **Framework**: Identifies setup patterns, configuration examples, workflow examples

### Example Categories Detected

- **Installation/Setup**: Package installation, environment setup, dependencies
- **Basic Usage**: Getting started examples, hello world patterns
- **Advanced Features**: Complex use cases, integration patterns
- **Configuration**: Config file examples, environment variables
- **API Usage**: Endpoint calls, authentication, response handling
- **CLI Commands**: Command syntax, options, subcommands
- **Code Snippets**: Function usage, class instantiation, method calls

## File Structure

```
examples/document-analysis/doc-example-validator/
├── README.md                          # This documentation
├── prompts/
│   └── extract_examples.j2           # Main template for example extraction
├── schemas/
│   └── example_task_list.schema.json # JSON schema for output validation
├── test_data/
│   └── sample_project/
│       ├── README.md                  # Sample project documentation (Markdown)
│       ├── changelog.md               # Version history with examples (Markdown)
│       ├── docs/
│       │   ├── installation.md        # Installation guide (Markdown)
│       │   ├── api_reference.rst      # API documentation (reStructuredText)
│       │   ├── configuration.md       # Configuration examples (Markdown)
│       │   └── troubleshooting.txt    # Troubleshooting guide (Plain text)
│       └── expected_output.json      # Expected analysis results
└── scripts/
    ├── run_example.sh                # Full execution script
    └── validate_output.py            # Output validation script
```

## Requirements

- **ostruct**: v0.8.0 or later (File Search support required)
- **OpenAI API**: Access required for gpt-4o model
- **Python Libraries**: jq for JSON manipulation (optional)
- **Documentation**: Markdown, RST, or text files to analyze

## Integration with AI Coding Agents

The generated task list is designed to be executed by AI coding agents:

### Cursor Integration

```bash
# Generate task list
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds docs/ -V project_name="MyProject" -V project_type="CLI" \
  --output-file validation_tasks.json

# Use with Cursor
# 1. Open validation_tasks.json in Cursor
# 2. Ask: "Execute all PENDING tasks in this validation list"
# 3. Agent will work through each task systematically
```

### Claude/ChatGPT Integration

```bash
# Include task list in conversation
cat validation_tasks.json | jq '.tasks[] | select(.status == "PENDING")'

# Prompt: "Here are validation tasks for project examples. Execute them one by one,
# updating status and adding results to each task."
```

## Scaling to Large Documentation Bases

### Why File Search for Large Projects

File Search is specifically designed for large documentation scenarios:

- **Efficient Processing**: Handles hundreds of documentation files without context overflow
- **Semantic Search**: Finds relevant examples across entire documentation sets intelligently
- **Cost Optimization**: More efficient than processing all files individually in context
- **Parallel Processing**: Can handle multiple documentation formats simultaneously

### Large-Scale Examples

```bash
# Analyze large open-source project (e.g., entire docs/ directory)
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds /path/to/large-project/docs/ \
  -ds /path/to/large-project/examples/ \
  -ds /path/to/large-project/wiki/ \
  -V project_name="LargeProject" \
  -V project_type="Framework" \
  -V validation_level="comprehensive" \
  --output-file large_project_validation.json

# Multi-repository documentation analysis
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds /repos/frontend/docs/ \
  -ds /repos/backend/docs/ \
  -ds /repos/api/docs/ \
  -V project_name="Microservices" \
  -V project_type="Distributed_System" \
  --output-file microservices_validation.json
```

### Optimization Strategies

**1. Selective Directory Scanning**:

```bash
# Focus on specific documentation areas
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds docs/user-guides/ \
  -ds docs/api-reference/ \
  -ds docs/tutorials/ \
  -V project_name="SelectiveAnalysis" \
  -V focus_areas="user_facing_docs"
```

**2. Progressive Analysis**:

```bash
# Step 1: High-priority documentation first
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -fs README.md \
  -fs GETTING_STARTED.md \
  -ds docs/quick-start/ \
  -V project_name="Progressive" \
  -V validation_level="critical_only"

# Step 2: Complete analysis
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds docs/ \
  -V project_name="Progressive" \
  -V validation_level="comprehensive"
```

**3. Format-Specific Processing**:

```bash
# Prioritize certain formats
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds docs/ \
  -V project_name="FormatPriority" \
  -V preferred_formats="markdown,rst" \
  -V exclude_formats="txt,log"
```

### Cost and Performance Considerations

| Documentation Size | Recommended Approach | Estimated Cost* | Processing Time |
|-------------------|---------------------|----------------|-----------------|
| Small (< 50 files) | Full directory scan (`-ds docs/`) | $0.50 - $2.00 | 1-3 minutes |
| Medium (50-200 files) | Selective scanning + File Search | $2.00 - $8.00 | 3-8 minutes |
| Large (200-1000 files) | Progressive analysis strategy | $8.00 - $25.00 | 8-20 minutes |
| Enterprise (1000+ files) | Multi-stage filtering approach | $25.00+ | 20+ minutes |

*Estimates based on gpt-4o pricing and typical documentation complexity

### Enterprise-Scale Patterns

**Documentation Repository Analysis**:

```bash
# Analyze multiple documentation repositories
for repo in docs-user docs-dev docs-api; do
  ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
    -ds "/repos/$repo/" \
    -V project_name="Enterprise_${repo}" \
    -V project_type="Documentation_Set" \
    --output-file "${repo}_validation.json"
done

# Combine results
jq -s 'add' *_validation.json > enterprise_validation.json
```

**Filtered Analysis for Specific Use Cases**:

```bash
# Focus on installation/setup examples only
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds docs/ \
  -V project_name="SetupFocus" \
  -V example_types="installation,setup,configuration" \
  -V exclude_types="api_examples,advanced_features"
```

## Common Use Cases

### Documentation Quality Assurance

```bash
# Validate all examples before release
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds docs/ \
  -V project_name="MyProject" \
  -V validation_level="comprehensive" \
  --output-file pre_release_validation.json
```

### CI/CD Integration

```bash
# Add to CI pipeline
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds docs/ \
  -V project_name="$PROJECT_NAME" \
  -V project_type="$PROJECT_TYPE" \
  --output-file ci_validation_tasks.json

# Execute validation with AI agent
python scripts/execute_validation_tasks.py ci_validation_tasks.json
```

### Documentation Migration

```bash
# Validate examples after major version changes
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds docs/ \
  -V project_name="MyProject" \
  -V project_version="2.0" \
  -V migration_context="Breaking changes in v2.0" \
  --output-file migration_validation.json
```

## Troubleshooting

### Common Issues

1. **No Examples Found**: Increase `validation_level` or check if documentation contains code blocks
2. **Too Many Tasks**: Use `project_type` filter or reduce documentation scope
3. **Invalid JSON Output**: Check schema validation and model temperature (use 0)
4. **Missing Dependencies**: Ensure task dependencies are correctly identified

### Performance Tips

- **Start with dry-run**: Use `--dry-run` to estimate costs before processing large documentation sets
- **Progressive analysis**: Begin with critical files, then expand to full documentation
- **Selective processing**: Use specific file patterns instead of entire directories when possible
- **Temperature control**: Set `temperature=0` for consistent, structured output
- **Monitor costs**: File Search charges based on vector store usage - monitor costs for large documentation sets
- **Batch related files**: Group similar documentation types for more efficient processing
- **Filter noise**: Exclude auto-generated docs, logs, and temporary files

### File Search Optimization for Large Documentation

**Upload Strategy**:

- Use `-ds` for entire directories (most efficient for large sets)
- Use `-fs` for specific high-priority files
- Combine both approaches for hybrid strategies

**Cost Management**:

- Vector stores are charged per GB per day - clean up unused stores
- Larger uploads are more cost-effective than many small uploads
- Consider documentation refresh frequency vs. storage costs

**Processing Limits**:

- File Search handles thousands of files efficiently
- Individual file size limit: 512MB
- Total vector store size: Up to 100GB
- Optimal chunk size for long documents: automatically handled

## Quick Reference: Large-Scale Documentation Analysis

### Commands by Project Size

| Project Scale | Files | Recommended Command | Estimated Cost |
|--------------|-------|-------------------|---------------|
| **Small** | < 50 | `ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json -ds docs/ -V project_name="Small" -V project_type="CLI"` | $0.50-$2 |
| **Medium** | 50-200 | `./scripts/large_scale_example.sh` (Progressive strategy) | $2-$8 |
| **Large** | 200-1000 | Multiple targeted `-ds` calls with filtering | $8-$25 |
| **Enterprise** | 1000+ | Repository-specific analysis with automation | $25+ |

### Large-Scale Script

For comprehensive large-scale examples:

```bash
# Run the large-scale demonstration script
./scripts/large_scale_example.sh

# This script demonstrates:
# - Progressive analysis strategies
# - Cost estimation and optimization
# - Multi-repository patterns
# - Format-specific processing
# - Performance benchmarking
```

## Example Scenarios

### Open Source Project

```bash
# Analyze a typical open source project
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -fs README.md \
  -fs CONTRIBUTING.md \
  -ds docs/ \
  -V project_name="awesome-cli" \
  -V project_type="CLI" \
  -V include_contributing_examples=true
```

### API Documentation

```bash
# Focus on API endpoint examples
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds api-docs/ \
  -V project_name="payments-api" \
  -V project_type="REST_API" \
  -V focus_areas="authentication,endpoints,webhooks"
```

### Internal Documentation

```bash
# Validate internal setup guides
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -fs docs/internal/setup.md \
  -fs docs/internal/deployment.md \
  -V project_name="internal-tools" \
  -V project_type="Framework" \
  -V audience="internal_developers"
```
