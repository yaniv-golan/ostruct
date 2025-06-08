#!/bin/bash
# check_tools.sh - Comprehensive tool availability checker

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load configuration
CONFIG_FILE="$PROJECT_ROOT/config/default.conf"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

echo "=== Document Conversion Tool Checker ==="
echo ""

# Required tools for the system to function
REQUIRED_TOOLS=("ostruct" "jq" "bc")
echo "Required System Tools:"
for tool in "${REQUIRED_TOOLS[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "  ✅ $tool: $(command -v "$tool")"
    else
        echo "  ❌ $tool: NOT FOUND"
    fi
done
echo ""

# Conversion tools
CONVERSION_TOOLS=("pandoc" "pdftotext" "tesseract" "markitdown" "soffice")
echo "Conversion Tools:"
for tool in "${CONVERSION_TOOLS[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        version=""
        case "$tool" in
            pandoc)
                version=$(pandoc --version | head -1 | cut -d' ' -f2)
                ;;
            pdftotext)
                version=$(pdftotext -v 2>&1 | head -1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
                ;;
            tesseract)
                version=$(tesseract --version 2>&1 | head -1 | cut -d' ' -f2)
                ;;
            markitdown)
                version=$(markitdown --version 2>/dev/null || echo "unknown")
                ;;
            soffice)
                version=$(soffice --version 2>/dev/null | cut -d' ' -f2 || echo "unknown")
                ;;
        esac
        if [[ "$tool" == "soffice" ]]; then
            echo "  ✅ libreoffice: $version"
        else
            echo "  ✅ $tool: $version"
        fi
    else
        if [[ "$tool" == "soffice" ]]; then
            echo "  ❌ libreoffice: NOT FOUND"
        else
            echo "  ❌ $tool: NOT FOUND"
        fi
    fi
done
echo ""

# PDF utilities
PDF_TOOLS=("pdfinfo" "pdftk" "pdfimages" "mutool")
echo "PDF Utilities:"
for tool in "${PDF_TOOLS[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "  ✅ $tool: Available"
    else
        echo "  ❌ $tool: NOT FOUND"
    fi
done
echo ""

# Python packages
echo "Python Packages:"
python_packages=("markitdown" "python-docx" "openpyxl" "python-pptx")
for package in "${python_packages[@]}"; do
    case "$package" in
        "python-docx")
            if python3 -c "import docx" 2>/dev/null; then
                echo "  ✅ $package: Available"
            else
                echo "  ❌ $package: NOT FOUND"
            fi
            ;;
        "python-pptx")
            if python3 -c "import pptx" 2>/dev/null; then
                echo "  ✅ $package: Available"
            else
                echo "  ❌ $package: NOT FOUND"
            fi
            ;;
        *)
            if python3 -c "import ${package//-/_}" 2>/dev/null; then
                echo "  ✅ $package: Available"
            else
                echo "  ❌ $package: NOT FOUND"
            fi
            ;;
    esac
done
echo ""

# Installation suggestions
echo "=== Installation Suggestions ==="
echo ""

echo "macOS (Homebrew):"
echo "  brew install pandoc poppler tesseract imagemagick ghostscript"
echo "  brew install --cask libreoffice"
echo "  pip3 install markitdown python-docx openpyxl python-pptx"
echo ""

echo "Ubuntu/Debian:"
echo "  apt-get install pandoc poppler-utils tesseract-ocr imagemagick ghostscript"
echo "  apt-get install libreoffice"
echo "  pip3 install markitdown python-docx openpyxl python-pptx"
echo ""

echo "For additional PDF tools:"
echo "  brew install pdftk-java mupdf-tools  # macOS"
echo "  apt-get install pdftk mupdf-tools    # Ubuntu"
