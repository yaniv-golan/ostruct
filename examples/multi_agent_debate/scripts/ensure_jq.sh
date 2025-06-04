#!/usr/bin/env bash
# Ensure jq binary is available in the current shell.
set -euo pipefail

command -v jq >/dev/null 2>&1 && return 0   # already present

echo "[setup] jq not found – attempting auto-install."

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

install_from_package_manager() {
  case "$OS" in
    linux)
      if command -v apt-get >/dev/null 2>&1;   then sudo apt-get -qq update && sudo apt-get -qq install -y jq && return 0; fi
      if command -v yum >/dev/null 2>&1;       then sudo yum -q -y install jq      && return 0; fi
      if command -v apk >/dev/null 2>&1;       then sudo apk add --no-cache jq     && return 0; fi
      if command -v pacman >/dev/null 2>&1;    then sudo pacman -Sy --noconfirm jq && return 0; fi
      ;;
    darwin)
      if command -v brew >/dev/null 2>&1;      then brew install jq                && return 0; fi
      ;;
  esac
  return 1
}

install_from_github_release() {
  echo "[setup] Downloading static jq binary from GitHub…"
  case "${OS}_${ARCH}" in
    linux_x86_64)   FILE=jq-linux64   ;;
    linux_aarch64)  FILE=jq-linux64   ;; # works fine on ARM64
    darwin_x86_64)  FILE=jq-osx-amd64 ;;
    darwin_arm64)   FILE=jq-macos-arm64 ;;
    *) echo "[setup] Unsupported platform for direct download." && return 1 ;;
  esac
  URL="https://github.com/stedolan/jq/releases/latest/download/${FILE}"
  mkdir -p "$HOME/.local/bin"
  curl -sSL "$URL" -o "$HOME/.local/bin/jq"
  chmod +x "$HOME/.local/bin/jq"
  export PATH="$HOME/.local/bin:$PATH"
  command -v jq >/dev/null 2>&1
}

docker_wrapper() {
  if command -v docker >/dev/null 2>&1; then
    echo "[setup] Falling back to Docker wrapper for jq."
    alias jq='docker run --rm -i stedolan/jq jq'
    export -f jq
    return 0
  fi
  return 1
}

# --- try methods in order ----
install_from_package_manager && echo "[setup] jq installed via system package manager." && return 0
install_from_github_release  && echo "[setup] jq downloaded to ~/.local/bin."         && return 0
docker_wrapper               && echo "[setup] Using Docker wrapper for jq."           && return 0

echo "[error] Could not install jq automatically. Please install it manually."
exit 1
