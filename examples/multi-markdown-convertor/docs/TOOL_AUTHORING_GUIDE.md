# Tool Documentation Authoring Guide

This guide explains how to create tool documentation files for the multi-markdown converter system.

## File Location and Naming

- **Location**: Place tool documentation files in the `tools/` directory
- **Naming**: Use the exact CLI executable name with `.md` extension (e.g., `pandoc.md`, `tesseract.md`)
- **Case**: Use lowercase to match standard CLI conventions

## File Structure

Each tool documentation file consists of:

1. **YAML Frontmatter** (required)
2. **Markdown Body** (required)

## YAML Frontmatter Schema

The YAML frontmatter provides structured metadata consumed by the planning system:

```yaml
---
tool: pandoc                           # CLI executable name (REQUIRED)
kind: universal-converter              # Tool category (REQUIRED)
tool_min_version: "2.19"              # Minimum tool version required (OPTIONAL)
tool_version_check: "pandoc --version | head -1"  # Command to check version (OPTIONAL)
recommended_output_format: markdown   # Preferred output format (OPTIONAL)
installation:                         # Installation commands (OPTIONAL)
  macos: "brew install pandoc"
  ubuntu: "apt-get install pandoc"
  windows: "choco install pandoc"
---
```

### Required Fields

- **`tool`**: The exact CLI executable name
- **`kind`**: Tool category (see complete list below)

### Optional Fields

- **`tool_min_version`**: Minimum version of the CLI tool required for reliable operation
- **`tool_version_check`**: Shell command to check the installed tool version
- **`recommended_output_format`**: The format this tool produces best results for
- **`installation`**: Platform-specific installation commands
  - **`macos`**: Installation command for macOS (typically using Homebrew)
  - **`ubuntu`**: Installation command for Ubuntu/Debian (typically using apt)
  - **`windows`**: Installation command for Windows (typically using Chocolatey or direct download)

### Complete Kind Values

Choose the most appropriate category for your tool:

- **`universal-converter`**: Multi-format conversion tools (e.g., pandoc)
- **`office-to-markdown`**: Office document to markdown converters (e.g., markitdown)
- **`office-converter`**: General office document converters (e.g., libreoffice)
- **`pdf-extractor`**: PDF text and image extraction tools (e.g., pdftotext, pdfimages)
- **`pdf-to-image`**: PDF to image conversion tools (e.g., imagemagick)
- **`pdf-utility`**: PDF processing and optimization tools (e.g., gs)
- **`image-utility`**: Image processing and conversion tools (e.g., imagemagick)
- **`ocr-engine`**: Optical character recognition tools (e.g., tesseract)
- **`html-validator`**: HTML validation and cleanup tools (e.g., htmlhint, tidy)
- **`xml-validator`**: XML validation tools (e.g., xmllint)
- **`formatter`**: Code and document formatting tools (e.g., prettier, black)
- **`utility`**: General-purpose utilities that don't fit other categories (e.g., jq, awk, sed, iconv, sox, exiftool, csvcut, csvgrep, pdfinfo)

## Markdown Body Template

The markdown body should follow this structure:

```markdown
# Tool Name

## Overview

Brief description of what the tool does and its primary use cases.

**IMPORTANT**: Include any critical limitations or file type restrictions.

## Installation

Provide installation instructions for major platforms:

- **macOS**: `brew install tool-name`
- **Ubuntu/Debian**: `apt-get install tool-name`
- **Windows**: Installation method or download link

## Capabilities

List the tool's main capabilities:

- Feature 1
- Feature 2
- Feature 3

## Common Usage Patterns

### Pattern 1 Name

```bash
tool-name {{INPUT_FILE}} {{OUTPUT_FILE}}
```

Brief explanation of what this command does.

### Pattern 2 Name

```bash
tool-name --option {{INPUT_FILE}} > {{OUTPUT_FILE}}
```

Brief explanation with parameter details.

## Output Formats

List supported output formats and any format-specific considerations.

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ⚠️ Any security warnings
- ❌ Any security risks

## Performance

- **Speed**: Performance characteristics
- **Memory**: Memory usage patterns
- **File Size**: File size limitations or considerations

## Best Practices

1. Numbered list of best practices
2. Common pitfalls to avoid
3. Optimization tips

## When to Use vs When NOT to Use

### When to Use

- Specific use case 1
- Specific use case 2

### When NOT to Use

- Situation where other tools are better
- Known limitations or problems

```

## Variable Naming Conventions

Based on the current script implementation, use these variable names in command templates:

### Primary Variables (Template Replacement)

- **`{{INPUT_FILE}}`**: Input file path (REQUIRED)
  - **Format**: Absolute path (e.g., `/Users/user/project/document.pdf`)
  - **Processing**: User-provided paths are converted to absolute paths via `realpath`
  - **Security**: Validated to be within allowed project directories

- **`{{OUTPUT_FILE}}`**: Output file path (REQUIRED)
  - **Format**: As provided by user (relative or absolute)
  - **Processing**: Parent directory is created automatically via `mkdir -p "$(dirname "$output_file")"`
  - **Security**: Output directory validated to be within allowed project directories

### Shell Variables (No Template Replacement)

- **`$TEMP_DIR`**: Temporary directory for intermediate files (OPTIONAL)
  - **Format**: Absolute path ending WITHOUT trailing slash (e.g., `/Users/user/project/temp`)
  - **Default**: `$PROJECT_ROOT/temp`
  - **Usage**: Use in shell commands like `"$TEMP_DIR/filename.ext"`
  - **Note**: This is a shell variable, NOT a template variable - use `$TEMP_DIR`, not `{{TEMP_DIR}}`

### Variable Replacement Logic

The script performs these exact replacements in command templates:
```bash
command=${command//\{\{INPUT_FILE\}\}/$input_file}
command=${command//\{\{OUTPUT_FILE\}\}/$output_file}
```

### Unsupported Variables

Do NOT use these variations as they are not supported:

- `{{IN}}`, `{{OUT}}`, `{{TMP}}`, `{{INPUT}}`, `{{OUTPUT}}`
- `{{TMP_DIR}}`, `{{TEMP_DIR}}`, `{{OUT_DIR}}`, `{{INPUT_DIR}}`
- Any other short forms or custom variations

### Path Examples

```bash
# Correct usage:
pandoc "{{INPUT_FILE}}" -o "{{OUTPUT_FILE}}"
# Becomes: pandoc "/Users/user/docs/input.pdf" -o "output.md"

pdftotext "{{INPUT_FILE}}" "$TEMP_DIR/extracted.txt"
# Becomes: pdftotext "/Users/user/docs/input.pdf" "/Users/user/project/temp/extracted.txt"

# Incorrect usage:
pandoc "{{IN}}" -o "{{OUT}}"           # ❌ Variables not replaced
pandoc "{{INPUT_FILE}}" -o "{{TMP}}/output.md"  # ❌ {{TMP}} not supported
```

## Strategic Positioning

When documenting your tool, consider its position in the ecosystem:

### Speed vs Quality Spectrum

- **Fast**: markitdown, pandoc (quick conversion)
- **Balanced**: Most specialized tools
- **High-fidelity**: LibreOffice (preserves complex formatting)

### Document Type Specialization

- **Office docs**: markitdown, libreoffice
- **PDFs**: pdftotext, imagemagick + tesseract
- **Web content**: htmlhint, tidy, xmllint
- **Universal**: pandoc

### Comparison Tables

Include strategic comparison tables to help users choose:

| Tool | Speed | Quality | Office Docs | PDFs | Web Content |
|------|-------|---------|-------------|------|-------------|
| pandoc | ⭐⭐⭐ | ⭐⭐ | ⭐ | ❌ | ⭐⭐⭐ |
| markitdown | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ |
| libreoffice | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ❌ | ⭐ |

## Future Enhancements

The system is designed to support future enhancements:

### Tool Version Management

- The `tool_min_version` and `tool_version_check` fields prepare for automatic version validation
- Future versions may enforce minimum tool versions before execution
- Version information will be exposed to the LLM via a `tool_versions` JSON object

### Enhanced Metadata

- Additional fields may be added to support more sophisticated tool selection
- Performance metrics and resource requirements may be tracked
- Tool compatibility matrices may be implemented

## Best Practices for Authors

### Security and Safety

1. **Local processing preferred**: Favor tools that work offline
2. **Document limitations**: Clearly state what file types are NOT supported
3. **Resource warnings**: Note memory or CPU intensive operations
4. **Network dependencies**: Clearly mark any tools requiring internet access

### Performance Guidance

1. **Speed indicators**: Help users choose fast vs thorough tools
2. **File size limits**: Document practical file size limitations
3. **Resource requirements**: Note memory, CPU, or disk requirements
4. **Batch processing**: Indicate if tool supports multiple files efficiently

### LLM Guidance

1. **Clear command templates**: Use consistent variable naming
2. **Strategic positioning**: Explain when to use vs alternatives
3. **Fallback strategies**: Suggest alternatives when tool fails
4. **Quality expectations**: Set realistic expectations for output quality

### Documentation Quality

1. **Self-contained examples**: Every example should work as-is
2. **Current information**: Avoid historical context, focus on current behavior
3. **Practical focus**: Emphasize real-world usage patterns
4. **Error prevention**: Document common mistakes and how to avoid them

## Validation Checklist

Before submitting tool documentation:

- [ ] File named correctly (matches CLI executable)
- [ ] YAML frontmatter includes required fields (`tool`, `kind`)
- [ ] Kind value selected from approved list
- [ ] Command templates use correct variable names
- [ ] Installation instructions provided for major platforms
- [ ] Security considerations documented
- [ ] Performance characteristics noted
- [ ] Strategic positioning explained (when to use vs alternatives)
- [ ] Examples are self-contained and functional
- [ ] No legacy references or outdated information
