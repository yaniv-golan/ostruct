# Multi-Markdown Converter Testing Guide

This guide explains how to execute the 30 risk elimination tests in a completely isolated environment without affecting the main ostruct project.

## 🚀 Quick Start

1. **Activate the isolated environment:**

   ```bash
   ./setup_env.sh
   ```

2. **Run all tests in dry-run mode (safe, no API costs):**

   ```bash
   python test_runner.py --category all --dry-run
   ```

3. **Run specific test categories:**

   ```bash
   python test_runner.py --category pdf --dry-run
   python test_runner.py --category document --dry-run
   python test_runner.py --category performance --dry-run
   ```

## 🔧 Environment Setup

### What's Included

The isolated test environment includes:

**Python Packages (in `test_env/`):**

- PyMuPDF, python-docx, python-pptx, openpyxl, pandas
- markitdown, camelot-py, tabula-py, pdfminer.six
- pytesseract, Pillow, opencv-python
- openai, requests, pyyaml, jinja2
- ostruct-cli (development mode from main project)

**System Dependencies (required on host):**

- pandoc (document conversion)
- tesseract (OCR)
- docker (container tests)

### Isolation Guarantees

✅ **Complete isolation from main project:**

- All test dependencies installed in `test_env/` virtual environment
- Main ostruct project remains completely untouched
- No modifications to system Python or main project dependencies

✅ **Resource isolation:**

- Test artifacts cleaned up automatically
- Temporary files scoped to test directories
- Docker images cleaned up after tests

## 📊 Test Categories

### PDF Processing Tests (1-3)

- **Test 1:** PyMuPDF multi-column handling
- **Test 2:** PyMuPDF table detection
- **Test 3:** OCR via Tesseract
- **Characteristics:** No API calls, fast execution, file processing

### Document Conversion Tests (4-10)

- **Tests 4-10:** Pandoc, MarkItDown, DOCX, PPTX, Excel processing
- **Characteristics:** No API calls, system tool dependencies

### LLM Integration Tests (11-22)

- **Tests 11-22:** OpenAI API integration, structured outputs, tool usage
- **Characteristics:** API calls required, costs money in live mode

### Performance/Infrastructure Tests (23-30)

- **Tests 23-30:** Token limits, parallel execution, Docker images
- **Characteristics:** Mixed (some API calls, some infrastructure)

## 🎯 Execution Modes

### Dry-Run Mode (Default, Recommended)

```bash
python test_runner.py --category all --dry-run
```

- **Safe:** No API calls, no costs
- **Fast:** Tests complete in minutes
- **Validates:** Dependencies, file processing, basic functionality

### Live Mode (API Calls)

```bash
python test_runner.py --category llm --live
```

- **⚠️ Warning:** Costs money (OpenAI API charges)
- **Required for:** LLM integration tests (11-22)
- **Setup needed:** Valid OPENAI_API_KEY in environment

## 📋 Command Reference

### Basic Usage

```bash
# Run all tests in dry-run mode
python test_runner.py --category all --dry-run

# Run specific category
python test_runner.py --category pdf --dry-run
python test_runner.py --category document --dry-run
python test_runner.py --category llm --live  # Costs money!
python test_runner.py --category performance --dry-run

# Custom timeout and output
python test_runner.py --timeout 600 --output my_report.json

# Parallel execution (safe tests only)
python test_runner.py --category pdf --parallel
```

### Test Categories

- `pdf` - Tests 1-3 (PyMuPDF, OCR)
- `document` - Tests 4-10 (Pandoc, Office formats)
- `llm` - Tests 11-22 (OpenAI API integration)
- `performance` - Tests 23-30 (Infrastructure, scaling)
- `all` - All 30 tests

### Options

- `--dry-run` - Safe mode, no API calls (default)
- `--live` - Enable API calls (costs money)
- `--timeout N` - Test timeout in seconds (default: 300)
- `--parallel` - Run safe tests in parallel
- `--output FILE` - Report output file (default: test_report.json)

## 📈 Understanding Results

### Test Reports

Each test execution generates:

- **Individual results:** `tests/test_XX_*/results.json`
- **Comprehensive report:** `test_report.json`
- **Console output:** Real-time progress and summary

### Success Criteria

- **✅ PASS:** Test completed successfully, met success criteria
- **❌ FAIL:** Test failed, error details in report
- **⏱️ TIMEOUT:** Test exceeded time limit
- **🔧 ERROR:** Environment or setup issue

### Example Report Structure

```json
{
  "execution_info": {
    "timestamp": "2024-01-01T10:00:00",
    "dry_run": true,
    "total_duration": 45.2
  },
  "summary": {
    "total_tests": 30,
    "passed": 28,
    "failed": 2,
    "success_rate": 93.3
  },
  "results": [...],
  "failed_tests": [...]
}
```

## 🛠️ Troubleshooting

### Common Issues

**"Virtual environment not found"**

```bash
# Recreate the environment
python3 -m venv test_env
source test_env/bin/activate
pip install -r requirements_test.txt
pip install -e ../../..
```

**"Pandoc not found"**

```bash
# macOS
brew install pandoc

# Ubuntu/Debian
sudo apt-get install pandoc
```

**"API key not set"**

```bash
# Set for current session
export OPENAI_API_KEY="your-key-here"

# Or create .env file
echo "OPENAI_API_KEY=your-key-here" > .env
```

**Test timeouts**

```bash
# Increase timeout
python test_runner.py --timeout 600
```

### Dependency Issues

**Missing Python packages:**

```bash
source test_env/bin/activate
pip install -r requirements_test.txt
```

**System tool missing:**

```bash
# Check what's available
./setup_env.sh

# Install missing tools (macOS)
brew install pandoc tesseract tesseract-lang poppler
```

### Resource Cleanup

**Manual cleanup:**

```bash
# Remove virtual environment
rm -rf test_env/

# Clean test artifacts
find tests/ -name "*.tmp" -delete
find tests/ -name "temp_*" -delete
```

## 💰 Cost Management

### API Cost Estimation

- **Dry-run mode:** $0 (no API calls)
- **Live LLM tests:** ~$0.50-2.00 (depends on model and content)
- **Full live run:** ~$2-5 (all API tests)

### Cost Control

```bash
# Test individual categories first
python test_runner.py --category pdf --dry-run      # Free
python test_runner.py --category document --dry-run # Free
python test_runner.py --category llm --live         # Costs money

# Use smaller model for testing
export OPENAI_MODEL=gpt-3.5-turbo  # Cheaper than gpt-4
```

## 📝 Development Workflow

### Recommended Testing Flow

1. **Initial validation (free):**

   ```bash
   python test_runner.py --category all --dry-run
   ```

2. **Verify specific categories:**

   ```bash
   python test_runner.py --category pdf --dry-run
   python test_runner.py --category document --dry-run
   ```

3. **Critical LLM tests (costs money):**

   ```bash
   python test_runner.py --category llm --live
   ```

4. **Full validation if needed:**

   ```bash
   python test_runner.py --category all --live
   ```

### CI/CD Integration

The test runner is designed for automation:

```bash
# Exit code 0 = all tests passed
# Exit code 1 = some tests failed
python test_runner.py --category all --dry-run && echo "All tests passed!"
```

## 🔍 Next Steps

After running tests:

1. **Review test_report.json** for detailed results
2. **Examine failed tests** in individual results.json files
3. **Use insights** to improve the multi-markdown converter
4. **Iterate** on specific test categories as needed

The isolated environment ensures your testing activities won't interfere with the main ostruct project while providing comprehensive validation of the multi-markdown converter requirements.
