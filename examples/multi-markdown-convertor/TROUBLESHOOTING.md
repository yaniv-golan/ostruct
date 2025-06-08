# Troubleshooting Guide

This guide covers common issues and their solutions when using the Document Conversion System.

## Quick Diagnostics

### Check System Status

```bash
# Check tool availability
./convert.sh --check-tools

# Test basic functionality
./scripts/test_basic.sh

# Run comprehensive tests
./scripts/test_all.sh --basic-only
```

### Enable Debug Mode

```bash
# Enable verbose output
./convert.sh --verbose input.pdf output.md

# Enable debug mode
DEBUG=true ./convert.sh input.pdf output.md

# Dry run to see planned commands
./convert.sh --dry-run input.pdf output.md
```

## Common Issues

### 1. Tool Not Found Errors

**Symptoms:**

- Error: "Command not found: pandoc"
- Tool availability check shows missing tools

**Solutions:**

#### macOS (Homebrew)

```bash
# Install core tools
brew install pandoc poppler tesseract imagemagick ghostscript

# Install Python tools
pip install markitdown python-docx openpyxl python-pptx

# Install LibreOffice
brew install --cask libreoffice
```

#### Ubuntu/Debian

```bash
# Install core tools
sudo apt-get update
sudo apt-get install pandoc poppler-utils tesseract-ocr imagemagick ghostscript

# Install Python tools
pip install markitdown python-docx openpyxl python-pptx

# Install LibreOffice
sudo apt-get install libreoffice
```

#### CentOS/RHEL

```bash
# Install EPEL repository first
sudo yum install epel-release

# Install core tools
sudo yum install pandoc poppler-utils tesseract imagemagick ghostscript

# Install Python tools
pip install markitdown python-docx openpyxl python-pptx

# Install LibreOffice
sudo yum install libreoffice
```

### 2. Permission Denied Errors

**Symptoms:**

- "Permission denied" when running convert.sh
- Cannot write to output directory

**Solutions:**

```bash
# Make script executable
chmod +x convert.sh
chmod +x scripts/*.sh

# Check file permissions
ls -la input.pdf

# Create output directory with proper permissions
mkdir -p output
chmod 755 output

# Check disk space
df -h .
```

### 3. API Key Issues

**Symptoms:**

- "API key not found" errors
- Authentication failures with OpenAI

**Solutions:**

```bash
# Set API key in environment
export OPENAI_API_KEY="your-api-key-here"

# Or add to shell profile
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# Verify API key is set
echo $OPENAI_API_KEY

# Test API connectivity
ostruct --version
```

### 4. Large Document Timeouts

**Symptoms:**

- Conversion stops with timeout errors
- Large PDFs fail to process

**Solutions:**

```bash
# Increase timeout in configuration
echo "DEFAULT_TIMEOUT=600" >> config/local.conf

# Enable chunking for large documents
echo "LARGE_DOCUMENT_THRESHOLD=52428800" >> config/local.conf  # 50MB

# Use faster models for large documents
echo "MODEL_ANALYSIS=gpt-4o-mini" >> config/local.conf
echo "MODEL_PLANNING=gpt-4o-mini" >> config/local.conf
```

### 5. High API Costs

**Symptoms:**

- Unexpected high costs
- Cost warnings during conversion

**Solutions:**

```bash
# Enable caching to reduce repeat costs
echo "ENABLE_CACHING=true" >> config/local.conf

# Use more cost-effective models
echo "MODEL_ANALYSIS=gpt-4o-mini" >> config/local.conf
echo "MODEL_SAFETY=gpt-4o-mini" >> config/local.conf
echo "MODEL_VALIDATION=gpt-4o-mini" >> config/local.conf

# Set cost warning threshold
echo "COST_WARNING_THRESHOLD=1.00" >> config/local.conf

# Monitor costs
grep "Cost:" temp/logs/*.log
```

### 6. Memory Issues

**Symptoms:**

- "Out of memory" errors
- System becomes unresponsive

**Solutions:**

```bash
# Check available memory
free -h

# Reduce chunk size for large documents
echo "PDF_CHUNK_SIZE=25" >> config/local.conf

# Clear cache to free space
./scripts/cleanup.sh --cache

# Monitor memory usage
top -p $(pgrep -f convert.sh)
```

### 7. Network Connectivity Issues

**Symptoms:**

- API timeouts
- Connection refused errors

**Solutions:**

```bash
# Test internet connectivity
ping api.openai.com

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Test API connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Increase retry attempts
echo "MAX_RETRIES=5" >> config/local.conf
```

### 8. Conversion Quality Issues

**Symptoms:**

- Poor output quality
- Missing content in converted files

**Solutions:**

```bash
# Use higher quality models
echo "MODEL_PLANNING=gpt-4o" >> config/local.conf
echo "MODEL_VALIDATION=gpt-4o" >> config/local.conf

# Enable verbose validation
echo "VERBOSE=true" >> config/local.conf

# Check validation results
grep "validation" temp/logs/*.log

# Try alternative tools
./convert.sh --dry-run input.pdf output.md  # See planned tools
```

### 9. Configuration Issues

**Symptoms:**

- Configuration not loading
- Settings not taking effect

**Solutions:**

```bash
# Validate configuration syntax
bash -n config/default.conf
bash -n config/local.conf

# Check configuration loading
DEBUG=true ./convert.sh --help 2>&1 | grep -i config

# Reset to defaults
mv config/local.conf config/local.conf.backup
cp config/default.conf config/local.conf
```

### 10. Disk Space Issues

**Symptoms:**

- "No space left on device"
- Conversion fails during processing

**Solutions:**

```bash
# Check disk space
df -h .

# Clean up temporary files
./scripts/cleanup.sh --all

# Move temp directory to larger disk
echo "TEMP_DIR=/path/to/larger/disk/temp" >> config/local.conf

# Monitor disk usage
du -sh temp/ output/ cache/
```

## Advanced Debugging

### Log Analysis

```bash
# View recent logs
tail -f temp/logs/convert.log

# Search for errors
grep -i error temp/logs/*.log

# Check performance logs
cat temp/logs/performance.log

# Security audit logs
cat temp/logs/security.log
```

### Function Testing

```bash
# Test individual functions
./scripts/test_unit.sh

# Test specific document types
./scripts/test_integration.sh --basic-only

# Performance testing
time ./convert.sh --analyze-only test.pdf
```

### Manual Command Testing

```bash
# Test ostruct directly
ostruct run prompts/analyze.j2 schemas/analysis.json \
  --fta input test.pdf

# Test individual tools
pandoc --version
pdftotext -v
tesseract --version
```

## Performance Optimization

### Speed Improvements

```bash
# Use faster models
MODEL_ANALYSIS=gpt-4o-mini
MODEL_PLANNING=gpt-4o-mini

# Enable caching
ENABLE_CACHING=true

# Reduce token limits
MAX_TOKEN_LIMIT=50000

# Skip validation for speed
SKIP_VALIDATION=true  # Not recommended for production
```

### Cost Optimization

```bash
# Use mini models where possible
MODEL_ANALYSIS=gpt-4o-mini
MODEL_SAFETY=gpt-4o-mini
MODEL_VALIDATION=gpt-4o-mini

# Enable aggressive caching
ENABLE_CACHING=true
SAFETY_CACHE_TTL=86400  # 24 hours

# Set cost limits
COST_WARNING_THRESHOLD=0.50
```

## Getting Help

### Log Collection

When reporting issues, include:

```bash
# System information
uname -a
./convert.sh --check-tools

# Recent logs
tar -czf debug-logs.tar.gz temp/logs/

# Configuration
cat config/local.conf 2>/dev/null || echo "No local config"

# Test results
./scripts/test_basic.sh > test-results.txt 2>&1
```

### Useful Commands

```bash
# Complete system test
./scripts/test_all.sh

# Clean slate test
./scripts/cleanup.sh --all
./scripts/test_basic.sh

# Minimal working example
echo "Test content" > test.txt
./convert.sh --analyze-only test.txt
```

### Support Resources

1. **Documentation**: README.md for comprehensive guide
2. **Examples**: Check `test_data/` for working examples
3. **Logs**: Always check `temp/logs/` for detailed error information
4. **Testing**: Use test scripts to isolate issues
5. **Configuration**: Review config files for proper settings

## Prevention Tips

1. **Regular Testing**: Run `./scripts/test_basic.sh` periodically
2. **Log Monitoring**: Check logs for warnings and errors
3. **Tool Updates**: Keep conversion tools updated
4. **Cache Management**: Clean cache regularly with `./scripts/cleanup.sh`
5. **Configuration Backup**: Keep backup of working configurations
6. **Resource Monitoring**: Monitor disk space and memory usage
