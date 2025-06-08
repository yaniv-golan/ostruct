#!/bin/bash
# install_tools.sh - Automated tool installation for Document Conversion System

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Platform detection
detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get >/dev/null 2>&1; then
            echo "ubuntu"
        elif command -v yum >/dev/null 2>&1; then
            echo "centos"
        elif command -v pacman >/dev/null 2>&1; then
            echo "arch"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Install tools on macOS
install_macos() {
    log_info "Installing tools for macOS..."

    # Check if Homebrew is installed
    if ! command -v brew >/dev/null 2>&1; then
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    log_info "Updating Homebrew..."
    brew update

    log_info "Installing system tools..."
    brew install jq bc

    log_info "Installing conversion tools..."
    brew install pandoc poppler tesseract imagemagick ghostscript

    log_info "Installing PDF utilities..."
    brew install pdftk-java mupdf-tools

    log_info "Installing LibreOffice..."
    brew install --cask libreoffice

    log_success "Homebrew packages installed successfully!"
}

# Install tools on Ubuntu/Debian
install_ubuntu() {
    log_info "Installing tools for Ubuntu/Debian..."

    log_info "Updating package lists..."
    sudo apt-get update

    log_info "Installing system tools..."
    sudo apt-get install -y jq bc curl

    log_info "Installing conversion tools..."
    sudo apt-get install -y pandoc poppler-utils tesseract-ocr imagemagick ghostscript

    log_info "Installing PDF utilities..."
    sudo apt-get install -y pdftk mupdf-tools

    log_info "Installing LibreOffice..."
    sudo apt-get install -y libreoffice

    log_success "APT packages installed successfully!"
}

# Install Python packages
install_python_packages() {
    log_info "Installing Python packages..."

    # Check if pip is available
    if ! command -v pip3 >/dev/null 2>&1; then
        log_error "pip3 not found. Please install Python 3 and pip first."
        return 1
    fi

    # Install packages
    log_info "Installing markitdown, python-docx, openpyxl, python-pptx..."
    pip3 install markitdown python-docx openpyxl python-pptx

    log_success "Python packages installed successfully!"
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."

    if [[ -f "$SCRIPT_DIR/check_tools.sh" ]]; then
        bash "$SCRIPT_DIR/check_tools.sh"
    else
        log_warning "Tool checker not found. Please run manually to verify installation."
    fi
}

# Main installation function
main() {
    echo "=== Document Conversion System - Tool Installer ==="
    echo ""

    PLATFORM=$(detect_platform)
    log_info "Detected platform: $PLATFORM"

    # Install based on platform
    case "$PLATFORM" in
        "macos")
            install_macos
            ;;
        "ubuntu")
            install_ubuntu
            ;;
        *)
            log_error "Unsupported platform: $PLATFORM"
            log_info "Please install tools manually using the suggestions from check_tools.sh"
            exit 1
            ;;
    esac

    # Install Python packages
    install_python_packages

    echo ""
    log_success "Installation completed!"
    echo ""

    # Verify installation
    verify_installation
}

# Help function
show_help() {
    echo "Document Conversion System - Tool Installer"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verify   Only verify existing installation"
    echo "  -p, --python   Only install Python packages"
    echo ""
    echo "Supported platforms:"
    echo "  - macOS (with Homebrew)"
    echo "  - Ubuntu/Debian (with apt)"
    echo ""
    echo "This script installs all tools required for the document conversion system."
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verify)
            verify_installation
            exit 0
            ;;
        -p|--python)
            install_python_packages
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main installation
main
