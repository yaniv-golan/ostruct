#!/usr/bin/env bash
# Standard runner library for ostruct examples
# Provides common functionality to reduce boilerplate in example run.sh scripts

# ── Locate getoptions ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GETOPTIONS="$ROOT/scripts/third_party/getoptions"

# ── Verify getoptions availability ──
if [[ ! -x "$GETOPTIONS" ]]; then
  echo "❌ getoptions not found at $GETOPTIONS"
  echo "   Please ensure getoptions is installed in scripts/third_party/"
  exit 1
fi

# ── Defaults (can be overridden before sourcing) ──
DEFAULT_MODEL="${DEFAULT_MODEL:-gpt-4.1}"
REQUIRES_JQ="${REQUIRES_JQ:-false}"
REQUIRES_MERMAID="${REQUIRES_MERMAID:-false}"

# ── Internal variables ──
MODEL="$DEFAULT_MODEL"
DRY=""
MODE="full"
VERBOSE=false

# ── Helper imports based on requirements ──
if [[ "$REQUIRES_JQ" == "true" ]]; then
  source "$ROOT/scripts/install/dependencies/ensure_jq.sh" || { echo "❌ jq required but not available"; exit 1; }
fi

if [[ "$REQUIRES_MERMAID" == "true" ]]; then
  source "$ROOT/scripts/install/dependencies/ensure_mermaid.sh" || { echo "❌ Mermaid CLI required but not available"; exit 1; }
fi

# ── Helper functions ──

# Wrapper for ostruct run that automatically adds model and dry-run flags
run_ostruct() {
  ostruct run "$@" -m "$MODEL" $DRY
}

# Validate all templates in templates/ directory
validate_all_templates() {
  echo "🧪 Validating all templates..."
  local template schema
  for template in templates/*.j2; do
    if [[ -f "$template" ]]; then
      schema="schemas/$(basename "$template" .j2).json"
      if [[ -f "$schema" ]]; then
        echo "🔹 Validating $(basename "$template")"
        run_ostruct "$template" "$schema" --dry-run
      else
        echo "⚠️ No schema found for $template (expected $schema)"
      fi
    fi
  done
  echo "✅ Template validation completed"
}



# Parse arguments using getoptions with custom options
parse_args_with_getoptions() {
  local custom_options
  custom_options=$(cat)  # Read custom options from stdin

  # Create temporary parser definition function
  parser_definition() {
    setup REST help:usage -- "Usage: $(basename "$0") [options]..." ''
    msg -- 'Standard Options:'
    param   MODEL      --model                        -- "OpenAI model to use (default: gpt-4.1)"
    flag    DRY_RUN    --dry-run                      -- "Run in dry-run mode (no API calls)"
    flag    TEST_DRY   --test-dry-run                 -- "Run test in dry-run mode"
    flag    TEST_LIVE  --test-live                    -- "Run test with live API call"
    flag    VERBOSE    --verbose                      -- "Enable verbose output"
    disp    :usage     --help -h                      -- "Show this help"

    # Add custom options if provided
    if [[ -n "$custom_options" ]]; then
      msg -- '' 'Custom Options:'
      eval "$custom_options"
    fi
  }

  # Generate and use the parser
  eval "$("$GETOPTIONS" parser_definition parse)"
  parse "$@"
  eval "set -- $REST"

  # Set internal variables based on parsed flags
  if [[ -n "${MODEL:-}" ]]; then
    MODEL="$MODEL"
  else
    MODEL="$DEFAULT_MODEL"
  fi

  if [[ "${DRY_RUN:-}" == "1" ]]; then
    DRY="--dry-run"
  fi

  if [[ "${TEST_DRY:-}" == "1" ]]; then
    MODE="test-dry"
    DRY="--dry-run"
  fi

  if [[ "${TEST_LIVE:-}" == "1" ]]; then
    MODE="test-live"
  fi

  if [[ "${VERBOSE:-}" == "1" ]]; then
    VERBOSE=true
    set -x
    DRY="$DRY --debug --progress detailed"
  fi
}



# Run a test command that works for both dry-run and live modes
run_test() {
  local template="$1"
  local schema="$2"
  shift 2
  echo "🧪 Running $([ "$MODE" = "test-dry" ] && echo "dry-run validation" || echo "live API test")..."
  run_ostruct "$template" "$schema" "$@"
  echo "✅ $([ "$MODE" = "test-dry" ] && echo "Dry-run validation" || echo "Live API test") passed"
}

# Execute the example based on mode
execute_mode() {
  if declare -f run_example > /dev/null; then
    run_example
  else
    echo "❌ run_example() function not defined"
    exit 1
  fi
}

# Simple argument parsing for examples with no custom args
parse_standard_args() {
  parse_args_with_getoptions "$@" <<'EOF'
EOF
}
