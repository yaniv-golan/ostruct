#!/usr/bin/env bash
# Two-pass pitch-deck distiller – standard example runner
# ------------------------------------------------------
# This script follows the common conventions enforced by
# scripts/examples/standard_runner.sh so that CI can
# automatically execute it with --test-dry-run and
# release workflows can run it with --test-live.

set -euo pipefail

# Required helper: jq is used to merge pass-1 and pass-2 output
REQUIRES_JQ=true

# Locate repository root and import shared runner helpers
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# ── Default parameters (overridable via CLI) ──
DECK_FILE="data/sample_pitch.txt"

# ── Example implementation ──
run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      # Fast validation: run Pass-1 on a small PDF fixture (txt no longer allowed for user-data)
      run_test templates/pass1_core.j2 schemas/pass1_core.json \
        --file user-data:deck examples/airbnb-pitch-deck-2009.pdf
      ;;

    "full")
      echo "🚀 Running full two-pass distillation on $DECK_FILE"

      # Check if we're in dry-run mode
      if [[ "$DRY" == *"--dry-run"* ]]; then
        echo "🔹 Pass 1: core extraction (dry-run)"
        run_ostruct templates/pass1_core.j2 schemas/pass1_core.json \
          --file user-data:deck "$DECK_FILE"

        echo "🔹 Pass 2: taxonomy classification (dry-run)"
        run_ostruct templates/pass2_taxonomy.j2 schemas/pass2_taxonomy_simple.json \
          --file fs:taxonomy reference/taxonomy.md \
          --json-var core_data='{"company_name": "Example Corp", "summary": "Example company summary", "business_model": "Example business model"}' \
          --enable-tool file-search

        echo "✅ Dry-run completed - both passes validated"
      else
        tmp_dir="$(mktemp -d)"

        echo "🔹 Pass 1: core extraction"
        run_ostruct templates/pass1_core.j2 schemas/pass1_core.json \
          --file user-data:deck "$DECK_FILE" \
          > "$tmp_dir/pass1.json"

        echo "🔹 Pass 2: taxonomy classification"
        run_ostruct templates/pass2_taxonomy.j2 schemas/pass2_taxonomy_simple.json \
          --file fs:taxonomy reference/taxonomy.md \
          --json-var core_data="$(cat "$tmp_dir/pass1.json")" \
          --enable-tool file-search \
          > "$tmp_dir/pass2.json"

        echo "🔹 Merging results"
        jq -s '.[0] + {"industry_classification": .[1]}' \
          "$tmp_dir/pass1.json" "$tmp_dir/pass2.json"
      fi
      ;;
  esac
}

# ── CLI argument parsing ──
parse_args_with_getoptions "$@" <<'EOF'
  param   DECK_FILE  --deck-file                    -- "Input pitch deck file (text or PDF)"
EOF

# Handle positional arguments after parsing
eval "set -- $REST"
if [[ $# -ge 1 ]]; then
  DECK_FILE="$1"
fi

execute_mode
