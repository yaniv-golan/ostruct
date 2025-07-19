#!/usr/bin/env bash
# Centralized yq installation utility for ostruct project
# Ensures yq binary is available with multiple installation strategies
# Inspired by scripts/install/dependencies/ensure_jq.sh

set -euo pipefail

###############################################################################
# Configuration
###############################################################################
readonly YQ_VERSION="4.46.1"
readonly GITHUB_REPO="mikefarah/yq"

# Environment toggles
SKIP_AUTO_INSTALL="${OSTRUCT_SKIP_AUTO_INSTALL:-}"
PREFER_DOCKER="${OSTRUCT_PREFER_DOCKER:-}"

log()  { echo "[yq-setup] $*" >&2; }
ok()   { log "✅ $*"; }
err()  { log "ERROR: $*"; }

###############################################################################
# Helpers
###############################################################################
command_exists() { command -v "$1" >/dev/null 2>&1; }

check_yq() {
  if command_exists yq; then
    ok "yq already available ($(yq --version 2>/dev/null || true))"
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
      if command_exists apt-get;   then sudo apt-get update -qq && sudo apt-get install -y yq && return 0; fi
      if command_exists yum;       then sudo yum install -y yq && return 0; fi
      if command_exists dnf;       then sudo dnf install -y yq && return 0; fi
      if command_exists apk;       then sudo apk add --no-cache yq && return 0; fi
      if command_exists pacman;    then sudo pacman -Sy --noconfirm yq && return 0; fi
      ;;
    darwin)
      if command_exists brew;      then brew install yq && return 0; fi
      if command_exists port;      then sudo port install yq && return 0; fi
      ;;
  esac
  return 1
}

install_via_binary() {
  log "Attempting direct binary download..."
  local platform asset url local_bin
  platform="$(detect_platform)"
  case "$platform" in
    linux_amd64)  asset="yq_linux_amd64";;
    linux_arm64)  asset="yq_linux_arm64";;
    darwin_amd64) asset="yq_darwin_amd64";;
    darwin_arm64) asset="yq_darwin_arm64";;
    *) err "Unsupported platform $platform"; return 1;;
  esac
  url="https://github.com/${GITHUB_REPO}/releases/download/v${YQ_VERSION}/${asset}.tar.gz"
  local_bin="$HOME/.local/bin"; mkdir -p "$local_bin"
  if command_exists curl; then
    curl -sSL "$url" | tar -xz -C "$local_bin" && chmod +x "$local_bin/yq" && export PATH="$local_bin:$PATH" && return 0
  elif command_exists wget; then
    wget -qO- "$url" | tar -xz -C "$local_bin" && chmod +x "$local_bin/yq" && export PATH="$local_bin:$PATH" && return 0
  fi
  return 1
}

install_via_docker() {
  if [[ -n "$PREFER_DOCKER" ]] || ! command_exists docker; then return 1; fi
  log "Configuring yq docker wrapper..."
  yq() { docker run --rm -i ghcr.io/mikefarah/yq:latest "$@"; }
  export -f yq
  ok "yq available via docker wrapper"
  return 0
}

###############################################################################
# Main
###############################################################################
main() {
  if [[ -n "$SKIP_AUTO_INSTALL" ]]; then
    log "Auto-install disabled (OSTRUCT_SKIP_AUTO_INSTALL set)"
    check_yq || { err "yq not found"; return 1; }
    return 0
  fi

  check_yq && return 0

  log "yq not found – attempting automatic installation..."

  install_via_pkg     && { ok "yq installed via system package manager"; return 0; }
  install_via_binary  && { ok "yq installed in ~/.local/bin"; return 0; }
  install_via_docker  && return 0

  err "Automatic yq installation failed — please install manually (https://github.com/mikefarah/yq)"
  return 1
}

main "$@"
