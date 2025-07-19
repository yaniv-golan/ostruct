# OST Generator

The **OST Generator** converts an existing Jinja2 template + JSON-schema pair into a fully-packaged **OST file** (self-executing ostruct prompt) with an intelligent, custom CLI interface.

## Quick Start

```bash
# From the ost-generator directory
chmod +x run.sh

# Generate an OST file from template & schema
./run.sh \
    -t test/fixtures/simple_template.j2 \
    -s test/fixtures/simple_schema.json \
    -o output
```

## What It Does

The OST Generator implements a **5-phase analysis and generation pipeline**:

### Phase 1: Template & Schema Analysis

- **Parallel execution** for performance optimization
- **Template analysis**: Variables, complexity, conditionals, loops, file patterns
- **Schema analysis**: Structure, validation rules, field constraints
- **Variable classification**: CLI mapping suggestions with validation hints
- **Pattern detection**: Tool recommendations, security analysis, usage patterns

### Phase 2: CLI Specification Generation

- **Intelligent CLI design**: Generates flags, help text, validation rules
- **Naming conventions**: Kebab-case conversion, conflict resolution
- **Tool integration**: Recommends code-interpreter, file-search, web-search
- **Security considerations**: Input validation, file safety patterns

### Phase 3: OST Assembly

- **YAML front-matter generation**: Proper OST structure with metadata
- **Template integration**: Preserves original template with CLI wrapper
- **Validation**: YAML syntax, template rendering, schema compliance
- **Final packaging**: Self-executing OST file with proper shebang

## Script Options

| Flag | Description |
|------|-------------|
| `-t, --template` | Path to the source Jinja2 template (.j2) |
| `-s, --schema`   | Path to the matching JSON schema (.json) |
| `-o, --out-dir`  | Output directory (default: `output/`) |
| `--dry-run`      | Test without API calls - validates pipeline with placeholders |
| `--verbose`      | Show detailed progress and analysis summaries |

## Example Output

```bash
./run.sh -t simple_template.j2 -s simple_schema.json --verbose

➤ Analyzing template and schema...
➤ Starting parallel analysis jobs...
  • Template analysis (background)...
  • Schema analysis (background)...
➤ Waiting for parallel jobs to complete...
  ✓ Template analysis complete
  ✓ Schema analysis complete
  📋 Found 4 variables, complexity: medium
  🔀 Template uses conditional logic
  📊 Schema: object with 4 required fields, complexity: low
  🎯 Schema includes enum constraints

➤ Generating CLI specification...
  ⚙️  CLI: 'text-analyzer' with 4 arguments (3 required, 1 optional)

➤ Assembling OST file...
  🔧 Assembly: 'text-analyzer' v1.0.0 → text-analyzer.ost

✅ OST file generation complete!
Generated file: output/text-analyzer.ost
```

## Project Structure

```
tools/ost-generator/
├── run.sh                      # Main orchestration script
├── src/                        # Analysis templates & schemas
│   ├── analyze_template.j2     # Template structure analysis
│   ├── analyze_schema.j2       # Schema validation analysis
│   ├── classify_variables.j2   # Variable-to-CLI mapping
│   ├── detect_patterns.j2      # Usage pattern detection
│   ├── generate_cli_spec.j2    # CLI specification generation
│   ├── generate_names.j2       # Naming convention application
│   ├── assemble_ost.j2         # Final OST assembly
│   ├── validate_ost.sh         # OST file validation
│   └── *_schema.json          # JSON schemas for each phase
├── test/                       # Test fixtures and utilities
│   ├── fixtures/              # Sample templates and schemas
│   └── test_*.sh              # Phase-specific test scripts
└── output/                     # Generated files
    ├── analysis/              # Intermediate analysis results
    ├── assembly/              # Assembly metadata
    └── *.ost                  # Final OST files
```

## Troubleshooting

### Common Issues

- **Variable mismatches**: Ensure template variables match schema field names
- **YAML validation**: Template shouldn't contain existing `---` frontmatter blocks
- **Missing dependencies**: Run from ostruct project root with `poetry install`

### Performance Tips

- **Use `--dry-run`** for pipeline testing without API costs
- **Parallel processing** handles template/schema analysis simultaneously
- **Model optimization** uses faster models for simple analysis tasks

### Debug Information

Run with `--verbose` to see:

- Variable classification details
- Tool recommendation reasoning
- Security pattern analysis
- CLI specification rationale
- Assembly validation results
