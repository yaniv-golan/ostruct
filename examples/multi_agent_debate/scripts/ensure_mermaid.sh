#!/usr/bin/env bash
# Ensure Mermaid CLI is callable as `mmdc` in current shell
set -euo pipefail

# Check if mmdc is already available
if command -v mmdc >/dev/null 2>&1; then
  exit 0
fi

# Check if npx is available
if command -v npx >/dev/null 2>&1; then
  echo "[setup] Installing Mermaid CLI via npx cache"
  npx --yes @mermaid-js/mermaid-cli mmdc --version >/dev/null
  exit 0
fi

echo "[error] Mermaid CLI not available and Node+npx not found."
exit 1
