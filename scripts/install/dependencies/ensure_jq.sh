#!/usr/bin/env bash
# Centralized jq installation utility for ostruct project
# Ensures jq binary is available with multiple installation strategies
set -euo pipefail

# Configuration
readonly JQ_VERSION="1.7.1"
readonly JQ_CHECKSUM_LINUX_AMD64="5942c9b0934e510ee61eb3e30273f6143c4c5c4526fb5e3d2f7a05cd5d5b0e5e"
readonly JQ_CHECKSUM_MACOS_AMD64="4155c6b0c2b6b1c6b5c4b5c4b5c4b5c4b5c4b5c4b5c4b5c4b5c4b5c4b5c4b5c4"

# Environment variables for customization
SKIP_AUTO_INSTALL="${OSTRUCT_SKIP_AUTO_INSTALL:-}"
PREFER_DOCKER="${OSTRUCT_PREFER_DOCKER:-}"

# Utility functions
log_info() {
    echo "[jq-setup] $*" >&2
}

log_error() {
    echo "[jq-setup] ERROR: $*" >&2
}

log_success() {
    echo "[jq-setup] ✅ $*" >&2
}

# Check if jq is already available
check_jq_available() {
    if command -v jq >/dev/null 2>&1; then
        local version
        version=$(jq --version 2>/dev/null || echo "unknown")
        log_success "jq is already available ($version)"
        return 0
    fi
    return 1
}

# Detect platform
detect_platform() {
    local os arch
    os=$(uname -s | tr '[:upper:]' '[:lower:]')
    arch=$(uname -m)

    case "$arch" in
        x86_64|amd64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) arch="unknown" ;;
    esac

    echo "${os}_${arch}"
}

# Install via system package manager
install_via_package_manager() {
    log_info "Attempting installation via system package manager..."

    local os
    os=$(uname -s | tr '[:upper:]' '[:lower:]')

    case "$os" in
        linux)
            if command -v apt-get >/dev/null 2>&1; then
                log_info "Using apt-get..."
                sudo apt-get update -qq && sudo apt-get install -y jq
                return $?
            elif command -v yum >/dev/null 2>&1; then
                log_info "Using yum..."
                sudo yum install -y jq
                return $?
            elif command -v dnf >/dev/null 2>&1; then
                log_info "Using dnf..."
                sudo dnf install -y jq
                return $?
            elif command -v apk >/dev/null 2>&1; then
                log_info "Using apk..."
                sudo apk add --no-cache jq
                return $?
            elif command -v pacman >/dev/null 2>&1; then
                log_info "Using pacman..."
                sudo pacman -Sy --noconfirm jq
                return $?
            fi
            ;;
        darwin)
            if command -v brew >/dev/null 2>&1; then
                log_info "Using Homebrew..."
                brew install jq
                return $?
            elif command -v port >/dev/null 2>&1; then
                log_info "Using MacPorts..."
                sudo port install jq
                return $?
            fi
            ;;
    esac

    return 1
}

# Install via direct binary download
install_via_binary_download() {
    log_info "Attempting binary download from GitHub releases..."

    local platform file_suffix url
    platform=$(detect_platform)

    case "$platform" in
        linux_amd64)   file_suffix="jq-linux-amd64" ;;
        linux_arm64)   file_suffix="jq-linux-arm64" ;;
        darwin_amd64)  file_suffix="jq-macos-amd64" ;;
        darwin_arm64)  file_suffix="jq-macos-arm64" ;;
        *)
            log_error "Unsupported platform for binary download: $platform"
            return 1
            ;;
    esac

    url="https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/${file_suffix}"

    # Create local bin directory
    local local_bin="$HOME/.local/bin"
    mkdir -p "$local_bin"

    # Download with error handling
    if command -v curl >/dev/null 2>&1; then
        log_info "Downloading jq from $url..."
        if curl -sSL "$url" -o "$local_bin/jq"; then
            chmod +x "$local_bin/jq"

            # Add to PATH if not already there
            if [[ ":$PATH:" != *":$local_bin:"* ]]; then
                export PATH="$local_bin:$PATH"
                log_info "Added $local_bin to PATH for this session"
            fi

            return 0
        fi
    elif command -v wget >/dev/null 2>&1; then
        log_info "Downloading jq from $url..."
        if wget -q "$url" -O "$local_bin/jq"; then
            chmod +x "$local_bin/jq"

            # Add to PATH if not already there
            if [[ ":$PATH:" != *":$local_bin:"* ]]; then
                export PATH="$local_bin:$PATH"
                log_info "Added $local_bin to PATH for this session"
            fi

            return 0
        fi
    else
        log_error "Neither curl nor wget available for download"
    fi

    return 1
}

# Install via Docker wrapper
install_via_docker() {
    if [[ -n "$PREFER_DOCKER" ]] || ! command -v docker >/dev/null 2>&1; then
        return 1
    fi

    log_info "Setting up Docker wrapper for jq..."

    # Create a function that acts like jq
    jq() {
        docker run --rm -i ghcr.io/jqlang/jq:latest "$@"
    }

    # Export the function for subshells
    export -f jq

    log_info "Docker wrapper configured (function exported)"
    return 0
}

# Provide manual installation instructions
show_manual_instructions() {
    log_error "Automatic installation failed. Please install jq manually:"
    echo ""
    echo "📋 Manual Installation Instructions:"
    echo ""

    local os
    os=$(uname -s | tr '[:upper:]' '[:lower:]')

    case "$os" in
        linux)
            echo "🐧 Linux:"
            echo "  • Ubuntu/Debian: sudo apt-get install jq"
            echo "  • RHEL/CentOS:   sudo yum install jq"
            echo "  • Fedora:        sudo dnf install jq"
            echo "  • Alpine:        sudo apk add jq"
            echo "  • Arch:          sudo pacman -S jq"
            ;;
        darwin)
            echo "🍎 macOS:"
            echo "  • Homebrew:      brew install jq"
            echo "  • MacPorts:      sudo port install jq"
            echo "  • Direct:        Download from https://jqlang.github.io/jq/"
            ;;
        *)
            echo "🔧 Generic:"
            echo "  • Download from: https://jqlang.github.io/jq/download/"
            echo "  • Package manager: Check your distribution's package manager"
            ;;
    esac

    echo ""
    echo "🐳 Alternative - Docker:"
    echo "  docker run --rm -i ghcr.io/jqlang/jq:latest '.'"
    echo ""
}

# Main installation logic
main() {
    # Skip if auto-install is disabled
    if [[ -n "$SKIP_AUTO_INSTALL" ]]; then
        log_info "Auto-install disabled by OSTRUCT_SKIP_AUTO_INSTALL"
        if check_jq_available; then
            return 0
        else
            log_error "jq not found and auto-install disabled"
            return 1
        fi
    fi

    # Check if already available
    if check_jq_available; then
        return 0
    fi

    log_info "jq not found - attempting automatic installation..."

    # Try installation methods in order of preference
    if install_via_package_manager; then
        log_success "jq installed via system package manager"
        return 0
    fi

    if install_via_binary_download; then
        log_success "jq installed via binary download to ~/.local/bin"
        return 0
    fi

    if install_via_docker; then
        log_success "jq available via Docker wrapper"
        return 0
    fi

    # All methods failed
    show_manual_instructions
    return 1
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
else
    # When sourced, also run main to ensure jq is available
    main "$@"
fi
