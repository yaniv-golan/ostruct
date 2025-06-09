#!/bin/bash
# Setup script for isolated test environment

echo "=== Multi-Markdown Converter Test Environment Setup ==="

# Check if virtual environment exists
if [ ! -d "test_env" ]; then
    echo "❌ Virtual environment not found. Please run the setup first."
    exit 1
fi

# Check for .env file and help user create it
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Environment file (.env) not found."
    echo "📋 You need to create one from the template for API access."
    echo ""
    echo "Quick setup:"
    echo "  1. cp test.env.template .env"
    echo "  2. Edit .env and add your OpenAI API key"
    echo ""
    echo "Or run: cp test.env.template .env && nano .env"
    echo ""
    echo "For dry-run tests (no API calls), you can continue without an API key."
    echo ""
fi

# Activate virtual environment
source test_env/bin/activate

echo "✅ Virtual environment activated"
echo "✅ Python: $(python --version)"
echo "✅ Ostruct: $(ostruct --version)"

# Check key dependencies
echo ""
echo "=== Checking Dependencies ==="

# Python packages
python -c "import fitz; print('✅ PyMuPDF available')" 2>/dev/null || echo "❌ PyMuPDF missing"
python -c "import pandas; print('✅ Pandas available')" 2>/dev/null || echo "❌ Pandas missing"
python -c "import openai; print('✅ OpenAI available')" 2>/dev/null || echo "❌ OpenAI missing"

# System tools
which pandoc >/dev/null && echo "✅ Pandoc available" || echo "❌ Pandoc missing"
which tesseract >/dev/null && echo "✅ Tesseract available" || echo "❌ Tesseract missing"
which docker >/dev/null && echo "✅ Docker available" || echo "❌ Docker missing"

# Check .env configuration
if [ -f ".env" ]; then
    if grep -q "your_openai_api_key_here" .env; then
        echo "⚠️  API key placeholder detected in .env - update for live tests"
    else
        echo "✅ .env file configured"
    fi
else
    echo "⚠️  No .env file - API tests will not work"
fi

echo ""
echo "=== Ready to run tests! ==="
echo "Usage examples:"
echo "  python test_runner.py --category pdf --dry-run      # Safe, no API calls"
echo "  python test_runner.py --category all --dry-run      # Test everything safely"
echo "  python test_runner.py --category llm --live         # Requires API key, costs money!"

# Keep shell active with environment
exec bash 