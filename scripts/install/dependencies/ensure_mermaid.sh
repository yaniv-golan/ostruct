#!/usr/bin/env bash
# Centralized Mermaid CLI installation utility for ostruct project
# Ensures mmdc (Mermaid CLI) is available with multiple installation strategies
set -euo pipefail

# Environment variables for customization
SKIP_AUTO_INSTALL="${OSTRUCT_SKIP_AUTO_INSTALL:-}"
PREFER_DOCKER="${OSTRUCT_PREFER_DOCKER:-}"

# Utility functions
log_info() {
    echo "[mermaid-setup] $*" >&2
}

log_error() {
    echo "[mermaid-setup] ERROR: $*" >&2
}

log_success() {
    echo "[mermaid-setup] ✅ $*" >&2
}

log_warning() {
    echo "[mermaid-setup] ⚠️  $*" >&2
}

# Check if Mermaid CLI is already available
check_mermaid_available() {
    if command -v mmdc >/dev/null 2>&1; then
        local version
        version=$(mmdc --version 2>/dev/null | head -n1 || echo "unknown")
        log_success "Mermaid CLI is already available ($version)"
        return 0
    fi
    return 1
}

# Check if Node.js and npm/npx are available
check_node_available() {
    if command -v node >/dev/null 2>&1 && command -v npx >/dev/null 2>&1; then
        local node_version npm_version
        node_version=$(node --version 2>/dev/null || echo "unknown")
        npm_version=$(npm --version 2>/dev/null || echo "unknown")
        log_info "Node.js available: $node_version, npm: $npm_version"
        return 0
    fi
    return 1
}

# Install Node.js via system package manager
install_nodejs_via_package_manager() {
    log_info "Attempting Node.js installation via system package manager..."

    local os
    os=$(uname -s | tr '[:upper:]' '[:lower:]')

    case "$os" in
        linux)
            if command -v apt-get >/dev/null 2>&1; then
                log_info "Using apt-get to install Node.js..."
                # Install NodeSource repository for latest Node.js
                curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
                sudo apt-get install -y nodejs
                return $?
            elif command -v yum >/dev/null 2>&1; then
                log_info "Using yum to install Node.js..."
                curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
                sudo yum install -y nodejs npm
                return $?
            elif command -v dnf >/dev/null 2>&1; then
                log_info "Using dnf to install Node.js..."
                curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash -
                sudo dnf install -y nodejs npm
                return $?
            elif command -v apk >/dev/null 2>&1; then
                log_info "Using apk to install Node.js..."
                sudo apk add --no-cache nodejs npm
                return $?
            elif command -v pacman >/dev/null 2>&1; then
                log_info "Using pacman to install Node.js..."
                sudo pacman -Sy --noconfirm nodejs npm
                return $?
            fi
            ;;
        darwin)
            if command -v brew >/dev/null 2>&1; then
                log_info "Using Homebrew to install Node.js..."
                brew install node
                return $?
            elif command -v port >/dev/null 2>&1; then
                log_info "Using MacPorts to install Node.js..."
                sudo port install nodejs18 +universal
                return $?
            fi
            ;;
    esac

    return 1
}

# Install Mermaid CLI via npx (cached)
install_via_npx() {
    if ! check_node_available; then
        return 1
    fi

    log_info "Installing Mermaid CLI via npx (cached)..."

    # Use npx to install and cache the package
    if npx --yes @mermaid-js/mermaid-cli@latest mmdc --version >/dev/null 2>&1; then
        log_success "Mermaid CLI installed via npx cache"

        # Create a wrapper script for easier access
        local local_bin="$HOME/.local/bin"
        mkdir -p "$local_bin"

        cat > "$local_bin/mmdc" << 'EOF'
#!/usr/bin/env bash
# Wrapper for Mermaid CLI via npx
exec npx --yes @mermaid-js/mermaid-cli@latest mmdc "$@"
EOF
        chmod +x "$local_bin/mmdc"

        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$local_bin:"* ]]; then
            export PATH="$local_bin:$PATH"
            log_info "Added $local_bin to PATH for this session"
        fi

        return 0
    fi

    return 1
}

# Install Mermaid CLI globally via npm
install_via_npm_global() {
    if ! check_node_available; then
        return 1
    fi

    log_info "Installing Mermaid CLI globally via npm..."

    if npm install -g @mermaid-js/mermaid-cli; then
        log_success "Mermaid CLI installed globally via npm"
        return 0
    fi

    return 1
}

# Install via Docker wrapper
install_via_docker() {
    if [[ -z "$PREFER_DOCKER" ]] && ! command -v docker >/dev/null 2>&1; then
        return 1
    fi

    log_info "Setting up Docker wrapper for Mermaid CLI..."

    # Test if Docker can run the Mermaid container
    if ! docker run --rm minlag/mermaid-cli:latest mmdc --version >/dev/null 2>&1; then
        log_error "Failed to run Mermaid Docker container"
        return 1
    fi

    # Create a wrapper function
    mmdc() {
        # Handle file I/O with Docker volume mounts
        local input_file output_file
        local docker_args=()
        local mmdc_args=()
        local current_dir
        current_dir=$(pwd)

        # Parse arguments to handle file paths
        while [[ $# -gt 0 ]]; do
            case "$1" in
                -i|--input)
                    input_file="$2"
                    mmdc_args+=("-i" "/data/$(basename "$input_file")")
                    shift 2
                    ;;
                -o|--output)
                    output_file="$2"
                    mmdc_args+=("-o" "/data/$(basename "$output_file")")
                    shift 2
                    ;;
                *)
                    mmdc_args+=("$1")
                    shift
                    ;;
            esac
        done

        # Set up volume mount for current directory
        docker_args+=("-v" "$current_dir:/data")
        docker_args+=("-w" "/data")

        # Run the container
        docker run --rm "${docker_args[@]}" minlag/mermaid-cli:latest mmdc "${mmdc_args[@]}"
    }

    # Export the function for subshells
    export -f mmdc

    log_success "Mermaid CLI available via Docker wrapper"
    return 0
}

# Provide manual installation instructions
show_manual_instructions() {
    log_error "Automatic installation failed. Please install Mermaid CLI manually:"
    echo ""
    echo "📋 Manual Installation Instructions:"
    echo ""

    echo "🟢 Recommended - Node.js + npm:"
    echo "  1. Install Node.js:"

    local os
    os=$(uname -s | tr '[:upper:]' '[:lower:]')

    case "$os" in
        linux)
            echo "     • Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - &
& sudo apt-get install -y nodejs"
            echo "     • RHEL/CentOS:   curl -fsSL https://rpm.nodesource.com/setup_lts.x | sudo bash - && s
udo yum install -y nodejs npm"
            echo "     • Alpine:        sudo apk add nodejs npm"
            echo "     • Arch:          sudo pacman -S nodejs npm"
            ;;
        darwin)
            echo "     • Homebrew:      brew install node"
            echo "     • MacPorts:      sudo port install nodejs18"
            echo "     • Direct:        Download from https://nodejs.org/"
            ;;
        *)
            echo "     • Download from: https://nodejs.org/"
            ;;
    esac

    echo "  2. Install Mermaid CLI:"
    echo "     npm install -g @mermaid-js/mermaid-cli"
    echo ""

    echo "🐳 Alternative - Docker:"
    echo "  docker run --rm -v \$(pwd):/data minlag/mermaid-cli:latest mmdc -i input.mmd -o output.svg"
    echo ""

    echo "💡 Quick test with npx (if Node.js available):"
    echo "  npx @mermaid-js/mermaid-cli mmdc --version"
    echo ""
}

# Main installation logic
main() {
    # Skip if auto-install is disabled
    if [[ -n "$SKIP_AUTO_INSTALL" ]]; then
        log_info "Auto-install disabled by OSTRUCT_SKIP_AUTO_INSTALL"
        if check_mermaid_available; then
            return 0
        else
            log_error "Mermaid CLI not found and auto-install disabled"
            return 1
        fi
    fi

    # Check if already available
    if check_mermaid_available; then
        return 0
    fi

    log_info "Mermaid CLI not found - attempting automatic installation..."

    # Try installation methods in order of preference
    if install_via_npx; then
        log_success "Mermaid CLI available via npx"
        return 0
    fi

    # If Node.js not available, try to install it first
    if ! check_node_available; then
        log_info "Node.js not found - attempting installation..."
        if install_nodejs_via_package_manager; then
            log_success "Node.js installed successfully"
            # Retry Mermaid installation
            if install_via_npx; then
                log_success "Mermaid CLI installed via npx after Node.js installation"
                return 0
            fi
        else
            log_warning "Failed to install Node.js automatically"
        fi
    fi

    # Try global npm installation
    if install_via_npm_global; then
        log_success "Mermaid CLI installed globally via npm"
        return 0
    fi

    # Try Docker as fallback
    if install_via_docker; then
        log_success "Mermaid CLI available via Docker wrapper"
        return 0
    fi

    # All methods failed
    show_manual_instructions
    return 1
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
