# Document Conversion System

A production-ready document conversion system that leverages ostruct as the intelligent brain for analysis, planning, and validation, while bash handles secure command execution with comprehensive error recovery.

## Overview

This system converts various document formats (PDF, DOCX, PPTX, XLSX) to Markdown using an intelligent multi-step workflow:

1. **Document Analysis** - ostruct analyzes the document using Code Interpreter
2. **Conversion Planning** - ostruct creates a detailed execution plan with tool selection
3. **Safety Checking** - ostruct evaluates each command for security risks
4. **Execution** - bash executes commands with comprehensive error recovery
5. **Validation** - ostruct validates the output quality and completeness

## Features

- **Intelligent Tool Selection**: Automatically chooses the best tools based on document analysis
- **Comprehensive Safety**: All commands evaluated for security risks with whitelist validation
- **Error Recovery**: Intelligent replanning when conversions fail
- **Large Document Support**: Automatic chunking for documents >100MB
- **Cost Optimization**: Caching and token management to minimize API costs
- **Production Ready**: Comprehensive logging, monitoring, and error handling

## Quick Start

```bash
# Basic conversion
./convert.sh input.pdf output.md

# Autonomous mode (no user prompts)
./convert.sh --autonomous input.docx output.md

# Analysis only
./convert.sh --analyze-only input.xlsx

# Dry run (no actual execution)
./convert.sh --dry-run input.pptx output.md

# Verbose output
./convert.sh --verbose input.pdf output.md
```

## Installation

### Automated Installation (Recommended)

```bash
# Run the automated installer
./scripts/install_tools.sh

# Or verify existing installation
./scripts/install_tools.sh --verify

# Or install only Python packages
./scripts/install_tools.sh --python
```

The installer supports:

- **macOS** (with Homebrew)
- **Ubuntu/Debian** (with apt)

### Manual Installation

If the automated installer doesn't support your platform:

```bash
# Required tools (install as needed)
brew install pandoc poppler tesseract imagemagick ghostscript pdftk-java mupdf-tools
brew install --cask libreoffice
# or
apt-get install pandoc poppler-utils tesseract-ocr imagemagick ghostscript pdftk mupdf-tools libreoffice

# Python tools
pip install markitdown python-docx openpyxl python-pptx
```

### Setup

```bash
# Clone and setup
cd examples/multi-markdown-convertor
chmod +x convert.sh scripts/*.sh

# Configure (optional)
cp config/default.conf config/local.conf
# Edit config/local.conf as needed

# Test installation
./scripts/check_tools.sh
```

## Configuration

The system uses configuration files in `config/`:

- `default.conf` - Default settings
- `local.conf` - Local overrides (optional)
- Environment variables override config files

Key settings:

```bash
# Model configuration
MODEL_ANALYSIS="gpt-4o-mini"      # Fast analysis
MODEL_PLANNING="gpt-4o"           # Complex planning
MODEL_SAFETY="gpt-4o-mini"        # Security evaluation
MODEL_VALIDATION="gpt-4o-mini"    # Quality assessment

# Safety and performance
MAX_REPLANS=3                     # Replan limit
ENABLE_SAFETY_CACHING=true        # Cache safety decisions
MAX_TOKEN_LIMIT=100000            # Token limit per operation
```

## Supported Formats

### Input Formats

- **PDF**: Text extraction, OCR for scanned documents, image extraction
- **DOCX**: Full document structure, tables, images
- **PPTX**: Slide content, speaker notes, embedded media
- **XLSX**: Sheet data, formulas, charts

### Output Format

- **Markdown**: Clean, structured markdown with preserved formatting

## Architecture

### Workflow Components

1. **Analysis Phase** (`prompts/analyze.j2`)
   - Document format detection
   - Structure analysis (pages, tables, images)
   - Complexity scoring
   - Tool recommendations

2. **Planning Phase** (`prompts/plan.j2`)
   - Tool selection based on analysis
   - Step-by-step command generation
   - Dependency management
   - Error recovery strategies

3. **Safety Phase** (`prompts/safety_check.j2`)
   - Command security evaluation
   - Risk factor identification
   - Approval workflow management

4. **Execution Phase** (bash orchestration)
   - Secure command execution
   - Progress tracking
   - Error handling and recovery

5. **Validation Phase** (`prompts/validate.j2`)
   - Output quality assessment
   - Content completeness verification
   - Improvement recommendations

### Security Features

- **Command Whitelisting**: Only approved tools can be executed
- **Path Validation**: All file operations restricted to project directory
- **Timeout Protection**: Commands have execution time limits
- **Replan Limits**: Maximum 3 replanning attempts to prevent loops
- **Audit Logging**: All security decisions logged for review

## Examples

### Basic PDF Conversion

```bash
# Convert a simple PDF
./convert.sh document.pdf document.md
```

### Complex Document with Custom Settings

```bash
# Convert with specific model and verbose output
MODEL_PLANNING="gpt-4o" ./convert.sh --verbose complex_report.docx report.md
```

### Batch Processing

```bash
# Convert multiple documents
for file in *.pdf; do
    ./convert.sh "$file" "output/${file%.pdf}.md"
done
```

### Large Document Handling

```bash
# The system automatically handles large documents (>100MB)
# with intelligent chunking
./convert.sh large_report.pdf large_report.md
```

## Tool Integration

The system includes comprehensive documentation for supported tools in `tools/`:

- **pandoc** - Universal document converter
- **pdftotext** - Fast PDF text extraction
- **tesseract** - OCR for scanned documents
- **markitdown** - Microsoft's conversion tool
- **libreoffice** - Office document processing
- **imagemagick** - Image processing
- **ghostscript** - PDF manipulation

Tools are automatically selected based on document analysis and availability.

## Error Handling

The system provides robust error recovery:

1. **Automatic Retry**: Failed steps are retried with exponential backoff
2. **Intelligent Replanning**: Alternative approaches generated on failure
3. **Partial Progress**: Completed steps preserved during recovery
4. **User Guidance**: Clear error messages with suggested solutions
5. **Fallback Strategies**: Multiple tool options for each conversion type

## Performance Optimization

- **Caching**: Analysis and planning results cached for identical documents
- **Token Management**: Selective tool documentation to reduce context size
- **Parallel Processing**: Independent steps can run concurrently (future)
- **Resource Monitoring**: Memory and disk usage tracking

## Monitoring and Logging

- **Execution Logs**: Detailed logs in `temp/logs/`
- **Performance Metrics**: Timing and resource usage tracking
- **Cost Tracking**: API usage and cost monitoring
- **Security Audit**: All security decisions logged

## Troubleshooting

### Common Issues

**Tool Not Found**

```bash
# Check tool availability
./scripts/check_tools.sh

# Install all missing tools automatically
./scripts/install_tools.sh

# Or install manually
brew install pandoc  # macOS
apt-get install pandoc  # Ubuntu
```

**Permission Denied**

```bash
# Ensure script is executable
chmod +x convert.sh

# Check file permissions
ls -la input.pdf
```

**Large Document Timeout**

```bash
# Increase timeout in config
echo "DEFAULT_TIMEOUT=600" >> config/local.conf
```

**High API Costs**

```bash
# Enable caching
echo "ENABLE_CACHING=true" >> config/local.conf

# Use smaller models
echo "MODEL_ANALYSIS=gpt-4o-mini" >> config/local.conf
```

### Debug Mode

```bash
# Enable debug output
DEBUG=true ./convert.sh input.pdf output.md

# Dry run to see planned commands
./convert.sh --dry-run input.pdf output.md
```

## Development

### Project Structure

```
examples/multi-markdown-convertor/
├── convert.sh              # Main conversion script
├── prompts/                # ostruct templates
│   ├── analyze.j2         # Document analysis
│   ├── plan.j2            # Conversion planning
│   ├── safety_check.j2    # Security evaluation
│   ├── replan.j2          # Failure recovery
│   └── validate.j2        # Quality assessment
├── schemas/               # JSON schemas
│   ├── analysis.json      # Analysis output
│   ├── plan.json          # Execution plan
│   ├── safety.json        # Safety evaluation
│   └── validation.json    # Quality results
├── tools/                 # Tool documentation
│   ├── pandoc.md          # Universal converter
│   ├── pdftotext.md       # PDF text extraction
│   └── ...                # Other tools
├── config/                # Configuration files
│   ├── default.conf       # Default settings
│   └── local.conf         # Local overrides
├── scripts/               # Utility scripts
│   ├── install_tools.sh   # Automated tool installation
│   ├── check_tools.sh     # Tool validation
│   └── cleanup.sh         # Cleanup utilities
└── test_data/             # Test documents
    ├── simple.pdf         # Basic test cases
    └── complex.docx       # Complex test cases
```

### Testing

```bash
# Run basic tests
./scripts/test_basic.sh

# Test with real documents
./scripts/test_integration.sh

# Performance testing
./scripts/test_performance.sh
```

### Contributing

1. Follow the established patterns in prompts and schemas
2. Test all changes with real documents
3. Update documentation for new features
4. Ensure security best practices are maintained

## License

This project follows the same license as the parent ostruct project.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review logs in `temp/logs/`
3. Test with `--dry-run` to debug planning issues
4. Use `--verbose` for detailed execution information
