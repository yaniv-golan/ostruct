#!/usr/bin/env bash
# Basic unit tests for examples/agent/verify.sh

set -euo pipefail

# Resolve paths
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_DIR="$ROOT_DIR/examples/agent"

# shellcheck source=/dev/null
source "$AGENT_DIR/verify.sh"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

pushd "$tmpdir" >/dev/null

##########################
# 01_file_exists_pass
##########################

touch pass.txt
crit='[{"type":"file_exists","path":"pass.txt"}]'
verify_success "$tmpdir" "$crit"
[[ $? -eq 0 ]] || { echo "01_file_exists_pass failed"; exit 1; }

##########################
# 02_file_exists_fail
##########################

crit='[{"type":"file_exists","path":"missing.txt"}]'
verify_success "$tmpdir" "$crit" && { echo "02_file_exists_fail unexpectedly passed"; exit 1; }

##########################
# 03_unknown_primitive
##########################

crit='[{"type":"db_row_equals","table":"t"}]'
verify_success "$tmpdir" "$crit"
[[ $? -eq 2 ]] || { echo "03_unknown_primitive did not return rc 2"; exit 1; }

popd >/dev/null

echo "All verify_success tests passed."
