#!/bin/bash

# Dependency Management Script
# Ensures all required tools are installed for the agent system

set -euo pipefail

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

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "$ID"
    elif [[ -f /etc/redhat-release ]]; then
        echo "rhel"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

# Check if tool is installed
check_tool() {
    local tool="$1"
    if command -v "$tool" >/dev/null 2>&1; then
        log_success "$tool is installed"
        return 0
    else
        log_warning "$tool is not installed"
        return 1
    fi
}

# Install tools based on OS
install_tools_debian() {
    log_info "Installing tools for Debian/Ubuntu"

    # Update package lists
    sudo apt-get update

    # Install required packages
    sudo apt-get install -y jq curl gawk sed grep coreutils

    # Install gum (Charmbracelet) - Official method
    if ! command -v gum >/dev/null 2>&1; then
        log_info "Installing gum (Charmbracelet) v0.16.2"
        # Use official Charm repository
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
        echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list
        sudo apt update && sudo apt install gum
        log_success "gum installed successfully"
    fi

    log_success "Tools installed successfully"
}

install_tools_rhel() {
    log_info "Installing tools for RHEL/CentOS/Fedora"

    # For RHEL/CentOS
    if command -v yum >/dev/null 2>&1; then
        sudo yum install -y jq curl gawk sed grep coreutils
    # For Fedora
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y jq curl gawk sed grep coreutils
    else
        log_error "No suitable package manager found"
        return 1
    fi

    # Install gum (Charmbracelet) - Official method
    if ! command -v gum >/dev/null 2>&1; then
        log_info "Installing gum (Charmbracelet) v0.16.2"
        # Use official Charm repository
        echo '[charm]
name=Charm
baseurl=https://repo.charm.sh/yum/
enabled=1
gpgcheck=1
gpgkey=https://repo.charm.sh/yum/gpg.key' | sudo tee /etc/yum.repos.d/charm.repo
        sudo rpm --import https://repo.charm.sh/yum/gpg.key

        # Install based on package manager
        if command -v yum >/dev/null 2>&1; then
            sudo yum install gum
        elif command -v dnf >/dev/null 2>&1; then
            sudo dnf install gum
        fi
        log_success "gum installed successfully"
    fi

    log_success "Tools installed successfully"
}

install_tools_alpine() {
    log_info "Installing tools for Alpine Linux"

    # Update package lists
    sudo apk update

    # Install required packages
    sudo apk add jq curl gawk sed grep coreutils

    # Install gum (Charmbracelet) - Binary download method for Alpine
    if ! command -v gum >/dev/null 2>&1; then
        log_info "Installing gum (Charmbracelet) v0.16.2"
        local gum_version="v0.16.2"
        local arch=$(uname -m)
        case "$arch" in
            x86_64) arch="amd64" ;;
            aarch64) arch="arm64" ;;
            *) log_error "Unsupported architecture: $arch"; return 1 ;;
        esac

        local gum_url="https://github.com/charmbracelet/gum/releases/download/${gum_version}/gum_${gum_version#v}_linux_${arch}.tar.gz"
        local temp_dir=$(mktemp -d)

        curl -sL "$gum_url" | tar -xz -C "$temp_dir"
        sudo mv "$temp_dir/gum" /usr/local/bin/
        rm -rf "$temp_dir"

        log_success "gum installed successfully"
    fi

    log_success "Tools installed successfully"
}

install_tools_macos() {
    log_info "Installing tools for macOS"

    # Check if Homebrew is installed
    if ! command -v brew >/dev/null 2>&1; then
        log_error "Homebrew not found. Please install Homebrew first:"
        log_error "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        return 1
    fi

    # Install required packages
    brew install jq curl gawk gnu-sed grep coreutils

    # Install gum (Charmbracelet) - Official Homebrew method
    if ! command -v gum >/dev/null 2>&1; then
        log_info "Installing gum (Charmbracelet) v0.16.2"
        brew install gum
        log_success "gum installed successfully"
    fi

    log_success "Tools installed successfully"
    log_warning "Note: Some tools may have different names on macOS (e.g., gsed for sed)"
}

# Check gawk vs busybox awk compatibility
check_awk_compatibility() {
    log_info "Checking awk compatibility"

    # Test awk functionality
    if echo "test 123" | awk '{print $2}' | grep -q "123"; then
        log_success "awk is working correctly"

        # Check if it's gawk
        if awk --version 2>&1 | grep -q "GNU Awk"; then
            log_success "GNU Awk (gawk) detected"
        else
            log_warning "Non-GNU awk detected. Some features may not work as expected."
        fi
    else
        log_error "awk is not functioning correctly"
        return 1
    fi
}

# Check tool versions
check_tool_versions() {
    log_info "Checking tool versions"

    # Check jq version
    if command -v jq >/dev/null 2>&1; then
        local jq_version=$(jq --version 2>/dev/null || echo "unknown")
        log_info "jq version: $jq_version"
    fi

    # Check curl version
    if command -v curl >/dev/null 2>&1; then
        local curl_version=$(curl --version 2>/dev/null | head -1)
        log_info "curl version: $curl_version"
    fi

    # Check awk version
    if command -v awk >/dev/null 2>&1; then
        local awk_version=$(awk --version 2>/dev/null | head -1 || echo "unknown")
        log_info "awk version: $awk_version"
    fi
}

# Main dependency check
check_dependencies() {
    log_info "Checking dependencies for agent system"

    local missing_tools=()

    # Check required tools
    if ! check_tool "jq"; then
        missing_tools+=("jq")
    fi

    if ! check_tool "curl"; then
        missing_tools+=("curl")
    fi

    if ! check_tool "awk"; then
        missing_tools+=("awk")
    fi

    if ! check_tool "sed"; then
        missing_tools+=("sed")
    fi

    if ! check_tool "grep"; then
        missing_tools+=("grep")
    fi

    if ! check_tool "timeout"; then
        missing_tools+=("timeout")
    fi

    if ! check_tool "head"; then
        missing_tools+=("head")
    fi

    if ! check_tool "stat"; then
        missing_tools+=("stat")
    fi

    if ! check_tool "gum"; then
        missing_tools+=("gum")
    fi

    if [[ ${#missing_tools[@]} -eq 0 ]]; then
        log_success "All required tools are installed"
        check_awk_compatibility
        check_tool_versions
        return 0
    else
        log_error "Missing tools: ${missing_tools[*]}"
        return 1
    fi
}

# Install missing dependencies
install_dependencies() {
    local os=$(detect_os)

    log_info "Detected OS: $os"

    case "$os" in
        "ubuntu"|"debian")
            install_tools_debian
            ;;
        "rhel"|"centos"|"fedora")
            install_tools_rhel
            ;;
        "alpine")
            install_tools_alpine
            ;;
        "darwin")
            install_tools_macos
            ;;
        *)
            log_error "Unsupported OS: $os"
            log_error "Please install the following tools manually:"
            log_error "  - jq (JSON processor)"
            log_error "  - curl (HTTP client)"
            log_error "  - gawk (GNU Awk)"
            log_error "  - sed (Stream editor)"
            log_error "  - grep (Pattern matching)"
            log_error "  - timeout (Command timeout)"
            log_error "  - head (Output first lines)"
            log_error "  - stat (File statistics)"
            return 1
            ;;
    esac
}

# Test ostruct availability
test_ostruct() {
    log_info "Testing ostruct availability"

    if command -v ostruct >/dev/null 2>&1; then
        log_success "ostruct is available"

        # Test ostruct version
        local ostruct_version=$(ostruct --version 2>/dev/null || echo "unknown")
        log_info "ostruct version: $ostruct_version"

        # Test basic ostruct functionality
        if ostruct --help >/dev/null 2>&1; then
            log_success "ostruct is functioning correctly"
        else
            log_warning "ostruct may not be working correctly"
        fi
    else
        log_error "ostruct is not installed or not in PATH"
        log_error "Please install ostruct first:"
        log_error "  pip install ostruct"
        return 1
    fi
}

# Performance test
performance_test() {
    log_info "Running performance test"

    # Test jq performance
    local start_time=$(date +%s)
    echo '{"test": "value"}' | jq '.test' >/dev/null 2>&1
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [[ $duration -lt 5 ]]; then
        log_success "Performance test passed"
    else
        log_warning "Performance test slow (${duration}s)"
    fi
}

# Main function
main() {
    local action="${1:-check}"

    case "$action" in
        "check")
            if check_dependencies; then
                test_ostruct
                performance_test
                log_success "All dependencies are ready"
            else
                log_error "Some dependencies are missing"
                log_info "Run '$0 install' to install missing dependencies"
                exit 1
            fi
            ;;
        "install")
            if ! check_dependencies; then
                install_dependencies
                log_info "Rechecking dependencies after installation"
                if check_dependencies; then
                    test_ostruct
                    log_success "All dependencies are now ready"
                else
                    log_error "Some dependencies are still missing after installation"
                    exit 1
                fi
            else
                log_info "All dependencies are already installed"
            fi
            ;;
        "test")
            check_dependencies
            test_ostruct
            performance_test
            ;;
        "help")
            echo "Usage: $0 [check|install|test|help]"
            echo ""
            echo "Commands:"
            echo "  check   - Check if dependencies are installed (default)"
            echo "  install - Install missing dependencies"
            echo "  test    - Run full dependency test"
            echo "  help    - Show this help message"
            ;;
        *)
            log_error "Unknown action: $action"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
