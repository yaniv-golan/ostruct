# Template & Schema Analyzer

> **Tool Type:** Meta-tool for ostruct development
> **Model:** gpt-4.1 with web search enabled
> **Cost:** ~$0.03-0.15 per analysis (depending on template/schema complexity)

## Overview

The Template & Schema Analyzer is a development tool that performs comprehensive analysis of ostruct templates and JSON schemas. It identifies issues, optimization opportunities, and best practices compliance using ostruct-powered analysis with real-time web search for up-to-date requirements.

**Key Features:**

- **Comprehensive Analysis**: Syntax, security, performance, and best practices
- **OpenAI Compliance**: Real-time checking against current OpenAI structured output requirements
- **Interactive Reports**: Beautiful HTML reports with filtering and detailed recommendations
- **ostruct Optimization**: Specialized analysis of ostruct-specific functions and filters
- **Cross-Analysis**: Template-schema alignment verification

## Installation & Prerequisites

```bash
# Required dependencies
ostruct --version    # ostruct CLI must be installed and accessible
jq --version        # JSON processor (auto-installed via ensure_jq.sh)

# The tool will automatically check and install jq if needed
```

## Usage

```bash
./run.sh [OPTIONS] [TEMPLATE_FILE] [SCHEMA_FILE]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `TEMPLATE_FILE` | Optional: Path to Jinja2 template file to analyze |
| `SCHEMA_FILE` | Optional: Path to JSON schema file to analyze |

If no files are specified, analyzes demo files for testing purposes.

### Options

| Option | Description |
|--------|-------------|
| `--verbose` | Enable verbose logging (INFO level) |
| `--debug` | Enable debug logging (DEBUG level) |
| `--help`, `-h` | Show help message |

### Examples

```bash
# Analyze demo files (default behavior)
./run.sh

# Analyze a specific template
./run.sh my_template.j2

# Analyze template and schema together
./run.sh my_template.j2 my_schema.json

# Enable verbose logging for detailed output
./run.sh --verbose my_template.j2

# Enable debug logging (includes ostruct debug output)
./run.sh --debug my_template.j2 my_schema.json
```

## Output

The analyzer produces multiple outputs:

1. **Console Output**: Real-time progress and summary information
2. **Log Files**: Detailed logs in `./log/` directory
3. **JSON Report**: Structured analysis results in `./analysis_output/`
4. **HTML Report**: Interactive web report automatically opened in browser

### HTML Report Features

- **Summary Dashboard**: Visual overview of issues, errors, warnings, and optimizations
- **Interactive Filtering**: Filter by severity (error/warning/optimization) or category
- **Expandable Details**: Click any issue for full description and recommendations
- **Professional Design**: Suitable for sharing with team members
- **Self-contained**: No external dependencies, works offline

## Analysis Categories

### Template Analysis

| Category | Description |
|----------|-------------|
| **Syntax** | Jinja2 syntax errors, malformed expressions, unclosed tags |
| **Variables** | Undefined variables, missing defaults, naming conventions |
| **Structure** | Complexity, readability, maintainability, organization |
| **Security** | Injection risks, unsafe operations, unescaped output |
| **Performance** | Inefficient loops, redundant operations, expensive filters |
| **Best Practices** | Formatting, documentation, error handling |
| **ostruct Optimization** | Analysis of ostruct-specific filters and functions |

#### ostruct-Specific Analysis

- **Filter Usage**: Text processing, code processing, data processing, table formatting
- **Global Functions**: Utility functions, token estimation, data analysis helpers
- **`file_ref()` Usage**: Safe file access and routing for multi-file templates
- **`safe_get()` Usage**: Nested data access to prevent KeyError exceptions

### Schema Analysis

| Category | Description |
|----------|-------------|
| **JSON Schema Validity** | Syntax and structural correctness |
| **OpenAI Compliance** | Real-time checking against current OpenAI requirements |
| **Type Definitions** | Proper typing, avoiding overly permissive schemas |
| **Validation Rules** | Constraints, enums (within OpenAI limitations) |
| **Documentation** | Missing descriptions, unclear property names |

#### OpenAI Structured Outputs Compliance

The analyzer uses web search to verify current requirements:

- All fields must be required (no optional fields)
- `additionalProperties: false` on all objects
- Maximum 100 properties with 5-level nesting limit
- Supported types only: string, number, boolean, integer, object, array, enum
- Avoids unsupported keywords: minLength, maxLength, pattern, format, etc.

### Cross-Analysis

When both template and schema are provided:

- **Output Alignment**: Template outputs match schema structure
- **Type Consistency**: Template data types align with schema expectations
- **Completeness**: Schema coverage of all template outputs

## Example Output

```json
{
  "analysis_summary": "Template shows good structure but has optimization opportunities for ostruct-specific functions.",
  "total_issues": 3,
  "critical_errors": 0,
  "warnings": 2,
  "optimizations": 1,
  "issues": [
    {
      "severity": "warning",
      "category": "variables",
      "description": "Direct attribute access could cause KeyError",
      "location": "Line 15: {{ data.user.name }}",
      "recommendation": "Use safe_get(data, 'user.name', 'Unknown') to prevent runtime errors"
    },
    {
      "severity": "warning",
      "category": "openai_compatibility",
      "description": "Schema uses unsupported 'minLength' constraint",
      "location": "properties.name.minLength",
      "recommendation": "Remove minLength constraint as it's not supported by OpenAI structured outputs"
    },
    {
      "severity": "optimization",
      "category": "best_practices",
      "description": "Template could benefit from file_ref usage",
      "location": "Multi-file template",
      "recommendation": "Use file_ref('alias') for safer file access in multi-file scenarios"
    }
  ]
}
```

## Directory Structure

```
tools/template-analyzer/
├── README.md                    # This documentation
├── run.sh                       # Main analyzer script
├── src/
│   ├── analyzer.j2             # Main analysis prompt template
│   └── analysis_output.json    # Output schema definition
├── scripts/
│   └── json2html.sh           # HTML report generator
├── test/
│   ├── demo_template.j2        # Example template for testing
│   └── demo_schema.json        # Example schema for testing
├── analysis_output/            # Generated analysis results
└── log/                        # Generated log files
```

## Advanced Usage

### CI/CD Integration

```bash
# Add to your CI pipeline
cd tools/template-analyzer
./run.sh --verbose src/templates/main.j2 src/schemas/output.json

# Check exit code for CI success/failure
if [ $? -eq 0 ]; then
  echo "✅ Template analysis passed"
else
  echo "❌ Template analysis failed"
  exit 1
fi
```

### Batch Analysis

```bash
# Analyze multiple files
for template in src/templates/*.j2; do
  echo "Analyzing $template..."
  ./run.sh "$template"
done
```

### Custom Analysis

Modify `src/analyzer.j2` to add custom analysis rules:

- Company-specific coding standards
- Project-specific security requirements
- Custom ostruct filter usage patterns

## Troubleshooting

### Common Issues

1. **"ostruct not found"**

   ```bash
   # Ensure ostruct is installed and in PATH
   ostruct --version
   pip install ostruct-cli  # if needed
   ```

2. **"jq not found"**

   ```bash
   # The tool will try to install jq automatically
   # If that fails, install manually:
   brew install jq          # macOS
   sudo apt install jq      # Ubuntu/Debian
   ```

3. **"Template file not found"**

   ```bash
   # Ensure the file path is correct
   ls -la my_template.j2
   # Use absolute paths if needed
   ./run.sh /full/path/to/template.j2
   ```

4. **"Analysis failed"**

   ```bash
   # Enable debug logging for detailed error information
   ./run.sh --debug my_template.j2
   # Check log files in ./log/ directory
   ```

### Getting Help

- Use `./run.sh --help` for usage information
- Enable `--debug` for detailed logging
- Check log files in `./log/` directory
- Review HTML reports for detailed analysis

## Contributing

This tool is part of the ostruct project's development infrastructure. To contribute:

1. Test with various template types and complexity levels
2. Report issues with specific templates that cause analysis failures
3. Suggest improvements to analysis rules in `src/analyzer.j2`
4. Enhance HTML report features in `scripts/json2html.sh`

## Related Tools

- **Schema Generator** (`tools/schema-generator/`): Automatically generates JSON schemas from templates
- **ostruct CLI**: The main ostruct command-line interface
- **ostruct Documentation**: <https://ostruct.readthedocs.io/>
