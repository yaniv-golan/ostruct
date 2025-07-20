#!/usr/bin/env bash
# Centralized gum installation utility for ostruct project
# Ensures gum binary is available with multiple installation strategies

set -euo pipefail

###############################################################################
# Configuration
###############################################################################
readonly GUM_VERSION="0.14.5"
readonly GITHUB_REPO="charmbracelet/gum"

# Environment toggles
SKIP_AUTO_INSTALL="${OSTRUCT_SKIP_AUTO_INSTALL:-}"
PREFER_DOCKER="${OSTRUCT_PREFER_DOCKER:-}"

log()  { echo "[gum-setup] $*" >&2; }
ok()   { log "✅ $*"; }
err()  { log "ERROR: $*"; }

###############################################################################
# Helpers
###############################################################################
command_exists() { command -v "$1" >/dev/null 2>&1; }

check_gum() {
  if command_exists gum; then
    ok "gum already available ($(gum --version 2>/dev/null || echo "version unknown"))"
    return 0
  fi
  return 1
}

detect_platform() {
  local os arch
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64) arch="amd64";;
    aarch64|arm64) arch="arm64";;
    i386|i686) arch="i386";;
    *) arch="unknown";;
  esac
  echo "${os}_${arch}"
}

###############################################################################
# Installation methods
###############################################################################
install_via_pkg() {
  log "Attempting installation via system package manager..."
  local os; os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  case "$os" in
    linux)
      # Try various package managers
      if command_exists apt-get; then
        # For Ubuntu/Debian, gum might be in universe or via snap
        if sudo apt-get update -qq && sudo apt-get install -y gum 2>/dev/null; then
          return 0
        fi
        # Try via snapd if available
        if command_exists snap && sudo snap install gum 2>/dev/null; then
          return 0
        fi
      fi
      if command_exists yum && sudo yum install -y gum 2>/dev/null; then return 0; fi
      if command_exists dnf && sudo dnf install -y gum 2>/dev/null; then return 0; fi
      if command_exists pacman && sudo pacman -Sy --noconfirm gum 2>/dev/null; then return 0; fi
      if command_exists apk && sudo apk add --no-cache gum 2>/dev/null; then return 0; fi
      ;;
    darwin)
      if command_exists brew && brew install gum; then return 0; fi
      if command_exists port && sudo port install gum 2>/dev/null; then return 0; fi
      ;;
  esac
  return 1
}

install_via_binary() {
  log "Attempting direct binary download..."
  local platform asset url local_bin
  platform="$(detect_platform)"
  case "$platform" in
    linux_amd64)  asset="gum_${GUM_VERSION}_Linux_x86_64";;
    linux_arm64)  asset="gum_${GUM_VERSION}_Linux_arm64";;
    linux_i386)   asset="gum_${GUM_VERSION}_Linux_i386";;
    darwin_amd64) asset="gum_${GUM_VERSION}_Darwin_x86_64";;
    darwin_arm64) asset="gum_${GUM_VERSION}_Darwin_arm64";;
    *) err "Unsupported platform $platform"; return 1;;
  esac

  url="https://github.com/${GITHUB_REPO}/releases/download/v${GUM_VERSION}/${asset}.tar.gz"
  local_bin="$HOME/.local/bin"; mkdir -p "$local_bin"

  if command_exists curl; then
    if curl -sSL "$url" | tar -xz -C /tmp && mv "/tmp/gum" "$local_bin/gum" 2>/dev/null; then
      chmod +x "$local_bin/gum"
      # Add to PATH if not already there
      if [[ ":$PATH:" != *":$local_bin:"* ]]; then
        export PATH="$local_bin:$PATH"
        log "Added $local_bin to PATH for this session"
      fi
      return 0
    fi
  elif command_exists wget; then
    if wget -qO- "$url" | tar -xz -C /tmp && mv "/tmp/gum" "$local_bin/gum" 2>/dev/null; then
      chmod +x "$local_bin/gum"
      # Add to PATH if not already there
      if [[ ":$PATH:" != *":$local_bin:"* ]]; then
        export PATH="$local_bin:$PATH"
        log "Added $local_bin to PATH for this session"
      fi
      return 0
    fi
  fi
  return 1
}

install_via_go() {
  if command_exists go; then
    log "Attempting installation via Go..."
    if go install "github.com/${GITHUB_REPO}@v${GUM_VERSION}" 2>/dev/null; then
      # Add GOPATH/bin to PATH if needed
      local go_bin
      go_bin="$(go env GOPATH)/bin"
      if [[ ":$PATH:" != *":$go_bin:"* ]]; then
        export PATH="$go_bin:$PATH"
        log "Added $go_bin to PATH for this session"
      fi
      return 0
    fi
  fi
  return 1
}

install_via_docker() {
  if [[ -n "$PREFER_DOCKER" ]] || ! command_exists docker; then return 1; fi
  log "Configuring gum docker wrapper..."
  # Note: gum doesn't have an official Docker image, but we can create a simple wrapper
  # This is more complex for gum since it's interactive, so we'll skip Docker for now
  return 1
}

show_manual_instructions() {
  err "Automatic installation failed. Please install gum manually:"
  echo ""
  echo "📋 Manual Installation Instructions:"
  echo ""

  local os
  os=$(uname -s | tr '[:upper:]' '[:lower:]')

  case "$os" in
    linux)
      echo "🐧 Linux:"
      echo "  • Ubuntu/Debian: sudo apt install gum (or via snap: sudo snap install gum)"
      echo "  • Arch Linux:    sudo pacman -S gum"
      echo "  • Alpine:        sudo apk add gum"
      echo "  • Or download from: https://github.com/charmbracelet/gum/releases"
      ;;
    darwin)
      echo "🍎 macOS:"
      echo "  • Homebrew:      brew install gum"
      echo "  • MacPorts:      sudo port install gum"
      echo "  • Or download from: https://github.com/charmbracelet/gum/releases"
      ;;
    *)
      echo "🔧 Generic:"
      echo "  • Download from: https://github.com/charmbracelet/gum/releases"
      echo "  • Or install via Go: go install github.com/charmbracelet/gum@latest"
      ;;
  esac

  echo ""
  echo "🔧 Alternative - Via Go (if available):"
  echo "  go install github.com/charmbracelet/gum@latest"
  echo ""
}

###############################################################################
# Main
###############################################################################
main() {
  if [[ -n "$SKIP_AUTO_INSTALL" ]]; then
    log "Auto-install disabled (OSTRUCT_SKIP_AUTO_INSTALL set)"
    check_gum || { err "gum not found"; return 1; }
    return 0
  fi

  check_gum && return 0

  log "gum not found – attempting automatic installation..."

  install_via_pkg     && { ok "gum installed via system package manager"; return 0; }
  install_via_binary  && { ok "gum installed in ~/.local/bin"; return 0; }
  install_via_go      && { ok "gum installed via Go"; return 0; }

  # Show manual instructions and return error
  show_manual_instructions
  return 1
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
else
    # When sourced, also run main to ensure gum is available
    main "$@"
fi
