#!/usr/bin/env bash
# OST Generator - Generate self-executing OST files from templates and schemas
# Chains analysis → generation → assembly → validation for a given template/schema pair.
# Usage: ./run.sh -t TEMPLATE.j2 -s SCHEMA.json [-o OUTPUT_DIR] [--dry-run] [--verbose]

set -euo pipefail

# Suppress ostruct logging noise
export OSTRUCT_LOG_LEVEL=ERROR
export PYTHONPATH="${PYTHONPATH:-}:."
export OSTRUCT_VERBOSITY=0
export PYTHONWARNINGS="ignore"

################################################################################
# Color helpers
################################################################################
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
step()  { echo -e "${BLUE}➤ $*${NC}"; }
info()  { echo -e "${GREEN}  ✓ $*${NC}"; }
warn()  { echo -e "${YELLOW}  ! $*${NC}"; }
fail()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

# Progress indicator function
show_progress() {
    local message="$1"
    shift

    if command -v gum &> /dev/null; then
        gum spin --spinner dot --title "$message" -- "$@"
    else
        echo -e "${BLUE}➤ $message${NC}"
        if "$@"; then
            echo -e "${GREEN}  ✓ Complete${NC}"
        else
            echo -e "${RED}  ✗ Failed${NC}"
            return 1
        fi
    fi
}

# Validation helper
validate_phase_output() {
    local file="$1"
    local phase="$2"

    # In dry-run mode, files may not be created - create minimal placeholders
    if [[ -n "$DRY_RUN" ]]; then
        if [[ ! -s "$file" ]]; then
            info "$phase completed (dry-run mode - creating placeholder)"
            # Create appropriate placeholder based on the phase
            case "$phase" in
                "Template analysis")
                    echo '{"variables":[],"complexity_score":"low","template_structure":{"has_conditionals":false,"has_loops":false}}' > "$file"
                    ;;
                "Variable classification")
                    echo '{"classified_variables":[],"classification_summary":{"total_variables":0,"type_distribution":{"scalar":0,"boolean":0,"file":0}}}' > "$file"
                    ;;
                "Schema analysis")
                    echo '{"schema_structure":{"root_type":"object","required_fields":[]},"validation_rules":{"complexity_score":"low"}}' > "$file"
                    ;;
                "Pattern detection")
                    echo '{"pattern_summary":{"complexity_score":"low"},"security_patterns":{"input_validation":{"risk_level":"low"}}}' > "$file"
                    ;;
                "CLI specification generation")
                    echo '{"cli_specification":{"tool_name":"test-tool","description":"Test tool","version":"1.0.0","arguments":[]}}' > "$file"
                    ;;
                "CLI naming generation")
                    echo '{"naming_results":{"tool_name":{"validated":"test-tool"}},"quality_metrics":{"usability_score":"high","total_conflicts":0,"resolved_conflicts":0}}' > "$file"
                    ;;
                "OST assembly")
                    echo '{"assembly_metadata":{"tool_name":"test-tool","file_name":"test-tool.ost","version":"1.0.0","description":"Test tool"},"validation_results":{"yaml_valid":true,"template_valid":true}}' > "$file"
                    ;;
                *)
                    echo '{}' > "$file"
                    ;;
            esac
            return 0
        fi
    fi

    if [[ ! -s "$file" ]]; then
        fail "$phase failed: $file is missing or empty"
    fi

    if ! jq empty "$file" 2>/dev/null; then
        fail "$phase failed: $file contains invalid JSON"
    fi
}

# Summary functions for each phase
show_template_analysis_summary() {
    local file="$1"
    if [[ -n "$DRY_RUN" ]]; then
        echo "  📋 Analysis: Template structure analyzed (dry-run mode)"
        return
    fi

    local var_count=$(jq -r '.variables | length' "$file" 2>/dev/null || echo "0")
    local has_conditionals=$(jq -r '.template_structure.has_conditionals' "$file" 2>/dev/null || echo "false")
    local has_loops=$(jq -r '.template_structure.has_loops' "$file" 2>/dev/null || echo "false")
    local complexity=$(jq -r '.complexity_score' "$file" 2>/dev/null || echo "0")

    echo "  📋 Found $var_count variables, complexity: $complexity"
    if [[ "$has_conditionals" == "true" ]]; then
        echo "  🔀 Template uses conditional logic"
    fi
    if [[ "$has_loops" == "true" ]]; then
        echo "  🔄 Template uses loops"
    fi
}

show_variable_classification_summary() {
    local file="$1"
    if [[ -n "$DRY_RUN" ]]; then
        echo "  🏷️  Variables: Classified for CLI mapping (dry-run mode)"
        return
    fi

    local total_vars=$(jq -r '.classification_summary.total_variables' "$file" 2>/dev/null || echo "0")
    local scalars=$(jq -r '.classification_summary.type_distribution.scalar' "$file" 2>/dev/null || echo "0")
    local booleans=$(jq -r '.classification_summary.type_distribution.boolean' "$file" 2>/dev/null || echo "0")
    local files=$(jq -r '.classification_summary.type_distribution.file' "$file" 2>/dev/null | sed 's/null/0/')

    echo "  🏷️  Classified $total_vars variables: $scalars scalar, $booleans boolean, $files file"

    # Show variable names
    local var_names=$(jq -r '.classified_variables[].name' "$file" 2>/dev/null | head -4 | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
    if [[ -n "$var_names" ]]; then
        echo "  📝 Variables: $var_names"
    fi
}

show_schema_analysis_summary() {
    local file="$1"
    if [[ -n "$DRY_RUN" ]]; then
        echo "  📊 Schema: Structure analyzed (dry-run mode)"
        return
    fi

    local root_type=$(jq -r '.schema_structure.root_type' "$file" 2>/dev/null || echo "unknown")
    local required_count=$(jq -r '.schema_structure.required_fields | length' "$file" 2>/dev/null || echo "0")
    local has_enum=$(jq -r '.validation_rules.has_enum_constraints' "$file" 2>/dev/null || echo "false")
    local complexity=$(jq -r '.validation_rules.complexity_score' "$file" 2>/dev/null || echo "low")

    echo "  📊 Schema: $root_type with $required_count required fields, complexity: $complexity"
    if [[ "$has_enum" == "true" ]]; then
        echo "  🎯 Schema includes enum constraints"
    fi

    # Show required fields
    local required_fields=$(jq -r '.schema_structure.required_fields[]' "$file" 2>/dev/null | head -4 | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
    if [[ -n "$required_fields" ]]; then
        echo "  ✅ Required: $required_fields"
    fi
}

show_pattern_detection_summary() {
    local file="$1"
    if [[ -n "$DRY_RUN" ]]; then
        echo "  🔍 Patterns: Usage patterns detected (dry-run mode)"
        return
    fi

    local complexity=$(jq -r '.pattern_summary.complexity_score' "$file" 2>/dev/null || echo "low")
    local code_interpreter=$(jq -r '.tool_hints.code_interpreter.suggested' "$file" 2>/dev/null || echo "false")
    local file_search=$(jq -r '.tool_hints.file_search.suggested' "$file" 2>/dev/null || echo "false")
    local web_search=$(jq -r '.tool_hints.web_search.suggested' "$file" 2>/dev/null || echo "false")
    local risk_level=$(jq -r '.security_patterns.input_validation.risk_level' "$file" 2>/dev/null || echo "unknown")

    echo "  🔍 Pattern complexity: $complexity, security risk: $risk_level"

    local tools_suggested=""
    if [[ "$code_interpreter" == "true" ]]; then tools_suggested="$tools_suggested code-interpreter"; fi
    if [[ "$file_search" == "true" ]]; then tools_suggested="$tools_suggested file-search"; fi
    if [[ "$web_search" == "true" ]]; then tools_suggested="$tools_suggested web-search"; fi

    if [[ -n "$tools_suggested" ]]; then
        echo "  🛠️  Suggested tools:$tools_suggested"
    else
        echo "  📝 No additional tools required"
    fi
}

show_cli_spec_summary() {
    local file="$1"
    if [[ -n "$DRY_RUN" ]]; then
        echo "  ⚙️  CLI: Interface specification generated (dry-run mode)"
        return
    fi

    local tool_name=$(jq -r '.cli_specification.tool_name' "$file" 2>/dev/null || echo "unknown")
    local arg_count=$(jq -r '.cli_specification.arguments | length' "$file" 2>/dev/null || echo "0")
    local required_count=$(jq -r '[.cli_specification.arguments[] | select(.required == true)] | length' "$file" 2>/dev/null || echo "0")
    local optional_count=$((arg_count - required_count))

    echo "  ⚙️  CLI: '$tool_name' with $arg_count arguments ($required_count required, $optional_count optional)"

    # Show argument flags
    local flags=$(jq -r '.cli_specification.arguments[] | .cli_flag + " (" + .short_flag + ")"' "$file" 2>/dev/null | head -4 | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
    if [[ -n "$flags" ]]; then
        echo "  🏁 Flags: $flags"
    fi
}

show_naming_summary() {
    local file="$1"
    if [[ -n "$DRY_RUN" ]]; then
        echo "  🏷️  Naming: Conventions applied (dry-run mode)"
        return
    fi

    local tool_name=$(jq -r '.naming_results.tool_name.validated' "$file" 2>/dev/null || echo "unknown")
    local conflicts=$(jq -r '.quality_metrics.total_conflicts' "$file" 2>/dev/null || echo "0")
    local resolved=$(jq -r '.quality_metrics.resolved_conflicts' "$file" 2>/dev/null || echo "0")
    local usability=$(jq -r '.quality_metrics.usability_score' "$file" 2>/dev/null || echo "medium")

    echo "  🏷️  Final name: '$tool_name' (usability: $usability)"
    if [[ "$conflicts" -gt 0 ]]; then
        echo "  ⚠️  Resolved $resolved/$conflicts naming conflicts"
    else
        echo "  ✅ No naming conflicts detected"
    fi
}

show_assembly_summary() {
    local file="$1"
    if [[ -n "$DRY_RUN" ]]; then
        echo "  🔧 Assembly: OST file structure created (dry-run mode)"
        return
    fi

    local tool_name=$(jq -r '.assembly_metadata.tool_name' "$file" 2>/dev/null || echo "unknown")
    local file_name=$(jq -r '.assembly_metadata.file_name' "$file" 2>/dev/null || echo "unknown")
    local version=$(jq -r '.assembly_metadata.version' "$file" 2>/dev/null || echo "unknown")

    echo "  🔧 Assembly: '$tool_name' v$version → $file_name"

    # Check if validation passed
    local yaml_valid=$(jq -r '.validation_results.yaml_valid' "$file" 2>/dev/null || echo "unknown")
    local template_valid=$(jq -r '.validation_results.template_valid' "$file" 2>/dev/null || echo "unknown")

    if [[ "$yaml_valid" == "true" && "$template_valid" == "true" ]]; then
        echo "  ✅ Structure validation passed"
    fi
}

# Display CLI interface (simulated --help output)
show_cli_interface() {
    local cli_spec_file="$1"

    if [[ -n "$DRY_RUN" ]]; then
        echo "🔧 Generated CLI Interface (dry-run mode):"
        echo "  Help output would be generated based on CLI specification"
        return
    fi

    if [[ ! -f "$cli_spec_file" ]]; then
        echo "🔧 Generated CLI Interface: (specification not available)"
        return
    fi

    local tool_name=$(jq -r '.cli_specification.tool_name' "$cli_spec_file" 2>/dev/null || echo "unknown")
    local description=$(jq -r '.cli_specification.description' "$cli_spec_file" 2>/dev/null || echo "")
    local version=$(jq -r '.cli_specification.version' "$cli_spec_file" 2>/dev/null || echo "1.0.0")

    echo "🔧 Generated CLI Interface:"
    echo ""
    echo "Usage: $tool_name [OPTIONS]"
    echo ""
    echo "$description"
    echo ""
    echo "Version: $version"
    echo ""
    echo "Options:"

    # Extract and display arguments with better formatting
    if jq -e '.cli_specification.arguments[]' "$cli_spec_file" >/dev/null 2>&1; then
        while IFS= read -r arg; do
            local flag=$(echo "$arg" | jq -r '.cli_flag')
            local short_flag=$(echo "$arg" | jq -r '.short_flag')
            local help_text=$(echo "$arg" | jq -r '.help_text')
            local required=$(echo "$arg" | jq -r '.required')
            local default_val=$(echo "$arg" | jq -r '.default_value // empty')

            local flag_display="  $flag, $short_flag"
            local requirement=""
            if [[ "$required" == "true" ]]; then
                requirement=" [required]"
            elif [[ -n "$default_val" && "$default_val" != "null" ]]; then
                requirement=" [default: $default_val]"
            fi

            printf "  %-20s %s%s\n" "$flag, $short_flag" "$help_text" "$requirement"
        done < <(jq -c '.cli_specification.arguments[]' "$cli_spec_file")
    fi

    echo "  -h, --help        Show this help message and exit"
    echo "  --version         Show version and exit"
    echo ""

    # Show usage examples if available
    if jq -e '.usage_examples[]' "$cli_spec_file" >/dev/null 2>&1; then
        echo "Examples:"
        jq -r '.usage_examples[] | "  " + .command' "$cli_spec_file" | head -3
        echo ""
    fi
}

################################################################################
# CLI parsing
################################################################################
TEMPLATE=""; SCHEMA=""; OUTDIR="output"; DRY_RUN=""; VERBOSE=""

# Common flags to reduce noise and suppress security warnings when invoking ostruct
OSTRUCT_COMMON_FLAGS=(--progress none --path-security permissive)

# We'll compute directory-specific --allow flags *after* CLI arg parsing once
# TEMPLATE and SCHEMA paths are known.

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--template) TEMPLATE="$2"; shift 2;;
    -s|--schema)   SCHEMA="$2"; shift 2;;
    -o|--out-dir)  OUTDIR="$2"; shift 2;;
    --dry-run)     DRY_RUN="--dry-run"; shift;;
    --verbose)     VERBOSE="--verbose"; shift;;
    -h|--help)
      echo "Usage: $0 -t TEMPLATE.j2 -s SCHEMA.json [-o OUTDIR] [--dry-run] [--verbose]"
      echo ""
      echo "Generate a self-executing OST file from a template and schema."
      echo ""
      echo "Arguments:"
      echo "  -t, --template TEMPLATE.j2    Jinja2 template file"
      echo "  -s, --schema   SCHEMA.json    JSON schema file"
      echo "  -o, --out-dir  OUTPUT_DIR     Output directory (default: output)"
      echo "  --dry-run                     Test without API calls"
      echo "  --verbose                     Show detailed progress"
      echo ""
      echo "Example:"
      echo "  $0 -t my_template.j2 -s my_schema.json -o my_output"
      exit 0;;
    *) fail "Unknown option: $1";;
  esac
done

[[ -z "$TEMPLATE" || -z "$SCHEMA" ]] && fail "Template (-t) and schema (-s) are required."
[[ ! -f "$TEMPLATE" ]] && fail "Template not found: $TEMPLATE"
[[ ! -f "$SCHEMA"   ]] && fail "Schema not found: $SCHEMA"
mkdir -p "$OUTDIR"

# ---------------------------------------------------------------------------
# Build --allow flags now that TEMPLATE and SCHEMA variables are known.
# ---------------------------------------------------------------------------

TEMPLATE_DIR=$(dirname "$(realpath "$TEMPLATE")")
SCHEMA_DIR=$(dirname "$(realpath "$SCHEMA")")
PWD_DIR="$(pwd)"

ALLOW_FLAGS=()
if [[ "$TEMPLATE_DIR" != "$PWD_DIR" ]]; then
  ALLOW_FLAGS+=(--allow "$TEMPLATE_DIR")
fi
if [[ "$SCHEMA_DIR" != "$PWD_DIR" && "$SCHEMA_DIR" != "$TEMPLATE_DIR" ]]; then
  ALLOW_FLAGS+=(--allow "$SCHEMA_DIR")
fi

# Merge allow flags into common flags
OSTRUCT_FLAGS=("${OSTRUCT_COMMON_FLAGS[@]}" "${ALLOW_FLAGS[@]}")

################################################################################
# Phase 1 - Template and Schema Analysis
################################################################################

run_phase1_analysis() {
    local analysis_dir="$1"

    info "Running parallel analysis of template and schema..."

    # Run independent analysis steps in parallel with faster model
    echo -e "${BLUE}➤ Starting parallel analysis jobs...${NC}"

    # Start template analysis in background
    echo -e "${BLUE}  • Template analysis (background)...${NC}"
    poetry run ostruct run tools/ost-generator/src/analyze_template.j2 \
        tools/ost-generator/src/analysis_schema.json \
        --file prompt:template "$TEMPLATE" \
        --output-file "$analysis_dir/template_analysis.json" $DRY_RUN $VERBOSE \
        --model gpt-4o-mini \
        "${OSTRUCT_FLAGS[@]}" &
    local template_pid=$!

    # Start schema analysis in background
    echo -e "${BLUE}  • Schema analysis (background)...${NC}"
    poetry run ostruct run tools/ost-generator/src/analyze_schema.j2 \
        tools/ost-generator/src/schema_analysis_schema.json \
        --file prompt:schema "$SCHEMA" \
        --output-file "$analysis_dir/schema_analysis.json" $DRY_RUN $VERBOSE \
        --model gpt-4o-mini \
        "${OSTRUCT_FLAGS[@]}" &
    local schema_pid=$!

    # Wait for parallel jobs to complete
    echo -e "${BLUE}➤ Waiting for parallel jobs to complete...${NC}"
    wait $template_pid
    local template_exit=$?
    echo -e "${GREEN}  ✓ Template analysis complete${NC}"

    wait $schema_pid
    local schema_exit=$?
    echo -e "${GREEN}  ✓ Schema analysis complete${NC}"

    # Check if any parallel job failed
    if [ $template_exit -ne 0 ] || [ $schema_exit -ne 0 ]; then
        fail "One or more parallel analysis steps failed"
    fi

    info "Parallel analysis completed successfully!"

    # Validate and show summaries for completed parallel steps
    validate_phase_output "$analysis_dir/template_analysis.json" "Template analysis"
    show_template_analysis_summary "$analysis_dir/template_analysis.json"

    validate_phase_output "$analysis_dir/schema_analysis.json" "Schema analysis"
    show_schema_analysis_summary "$analysis_dir/schema_analysis.json"

    # Variable classification depends on template analysis (must run after)
    show_progress "Classifying template variables..." \
        poetry run ostruct run tools/ost-generator/src/classify_variables.j2 \
            tools/ost-generator/src/classification_schema.json \
            --file prompt:analysis_json "$analysis_dir/template_analysis.json" \
            --output-file "$analysis_dir/variable_classification.json" $DRY_RUN $VERBOSE \
            --model gpt-4o-mini \
            "${OSTRUCT_FLAGS[@]}"

    validate_phase_output "$analysis_dir/variable_classification.json" "Variable classification"
    show_variable_classification_summary "$analysis_dir/variable_classification.json"

    # Pattern detection (uses results from previous analysis steps) - needs full model
    show_progress "Detecting usage patterns..." \
        poetry run ostruct run tools/ost-generator/src/detect_patterns.j2 \
            tools/ost-generator/src/pattern_detection_schema.json \
            --file prompt:template_analysis "$analysis_dir/template_analysis.json" \
            --file prompt:variable_classification "$analysis_dir/variable_classification.json" \
            --file prompt:schema_analysis "$analysis_dir/schema_analysis.json" \
            --output-file "$analysis_dir/pattern_detection.json" $DRY_RUN $VERBOSE \
            "${OSTRUCT_FLAGS[@]}"

    validate_phase_output "$analysis_dir/pattern_detection.json" "Pattern detection"
    show_pattern_detection_summary "$analysis_dir/pattern_detection.json"
}

################################################################################
# Phase 2 - CLI Generation
################################################################################
ANALYSIS_DIR="$OUTDIR/analysis"; mkdir -p "$ANALYSIS_DIR"

step "Analyzing template and schema..."

# Run Phase 1 analysis
run_phase1_analysis "$ANALYSIS_DIR"

step "Generating CLI specification..."
# Generate CLI specification using analysis results
poetry run ostruct run tools/ost-generator/src/generate_cli_spec.j2 \
    tools/ost-generator/src/cli_spec_schema.json \
    --file prompt:template_analysis "$ANALYSIS_DIR/template_analysis.json" \
    --file prompt:variable_classification "$ANALYSIS_DIR/variable_classification.json" \
    --file prompt:schema_analysis "$ANALYSIS_DIR/schema_analysis.json" \
    --file prompt:pattern_detection "$ANALYSIS_DIR/pattern_detection.json" \
    --output-file "$ANALYSIS_DIR/cli_spec.json" $DRY_RUN $VERBOSE \
    "${OSTRUCT_FLAGS[@]}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ CLI specification generated${NC}"
else
    echo -e "${RED}  ✗ CLI specification generation failed${NC}"
    exit 1
fi

validate_phase_output "$ANALYSIS_DIR/cli_spec.json" "CLI specification generation"
show_cli_spec_summary "$ANALYSIS_DIR/cli_spec.json"

# Generate naming conventions (simple rule-based step)
echo -e "${BLUE}➤ Creating naming conventions...${NC}"
poetry run ostruct run tools/ost-generator/src/generate_names.j2 \
    tools/ost-generator/src/cli_naming_schema.json \
    --file prompt:cli_specification "$ANALYSIS_DIR/cli_spec.json" \
    --output-file "$ANALYSIS_DIR/cli_naming.json" $DRY_RUN $VERBOSE \
    --model gpt-4o-mini \
    "${OSTRUCT_FLAGS[@]}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ Naming conventions created${NC}"
else
    echo -e "${RED}  ✗ Naming conventions creation failed${NC}"
    exit 1
fi

validate_phase_output "$ANALYSIS_DIR/cli_naming.json" "CLI naming generation"
show_naming_summary "$ANALYSIS_DIR/cli_naming.json"

################################################################################
# Phase 3 - OST Assembly
################################################################################
step "Assembling OST file..."
ASSEMBLY_DIR="$OUTDIR/assembly"; mkdir -p "$ASSEMBLY_DIR"
BUNDLE_JSON="$ASSEMBLY_DIR/bundle.json"

# Build JSON bundle for assemble_ost using jq (requires jq 1.6+)
if [[ -n "$DRY_RUN" ]]; then
    # In dry-run mode, create a minimal bundle with placeholder data
    cat > "$BUNDLE_JSON" << 'EOF'
{
  "template_content": "# Test Template\nTest content: {{ input_text }}\n",
  "schema_content": "{\"type\":\"object\",\"properties\":{\"result\":{\"type\":\"string\"}},\"required\":[\"result\"]}",
  "cli_specification": {
    "cli_specification": {
      "tool_name": "test-tool",
      "description": "Test tool for dry-run",
      "version": "1.0.0",
      "arguments": [
        {
          "variable_name": "input_text",
          "cli_flag": "--input-text",
          "short_flag": "-i",
          "argument_type": "single_value",
          "required": true,
          "default_value": null,
          "help_text": "Input text to process",
          "validation": {"type": "string", "allowed_values": null}
        }
      ]
    }
  },
  "cli_naming": {
    "naming_results": {
      "tool_name": {
        "validated": "test-tool"
      }
    },
    "quality_metrics": {
      "usability_score": "high",
      "total_conflicts": 0,
      "resolved_conflicts": 0
    }
  },
  "help_documentation": {},
  "policy_configuration": {},
  "defaults_management": {}
}
EOF
else
    # Normal mode - build from actual files
    jq -n --slurpfile spec "$ANALYSIS_DIR/cli_spec.json" \
          --slurpfile name "$ANALYSIS_DIR/cli_naming.json" \
          --rawfile template "$TEMPLATE" \
          --rawfile schema "$SCHEMA" \
    '{template_content: $template,
      schema_content:   $schema,
      cli_specification: $spec[0],
      cli_naming: $name[0],
      help_documentation: {},
      policy_configuration: {},
      defaults_management: {}}' > "$BUNDLE_JSON"
fi

# Generate final OST assembly
echo -e "${BLUE}➤ Finalizing OST assembly...${NC}"
poetry run ostruct run tools/ost-generator/src/assemble_ost.j2 \
    tools/ost-generator/src/assembly_schema.json \
    --file prompt:input "$BUNDLE_JSON" \
    --output-file "$ASSEMBLY_DIR/assembly.json" $DRY_RUN $VERBOSE \
    "${OSTRUCT_FLAGS[@]}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ OST assembly finalized${NC}"
else
    echo -e "${RED}  ✗ OST assembly failed${NC}"
    exit 1
fi

validate_phase_output "$ASSEMBLY_DIR/assembly.json" "OST assembly"
show_assembly_summary "$ASSEMBLY_DIR/assembly.json"

################################################################################
# Final OST File Generation
################################################################################
step "Building final OST file..."
OST_FILE="$OUTDIR/$(jq -r '.assembly_metadata.file_name // "generated.ost"' "$ASSEMBLY_DIR/assembly.json")"

# Extract metadata from CLI specification
tool_name=$(jq -r '.cli_specification.cli_specification.tool_name // "template-tool"' "$BUNDLE_JSON" 2>/dev/null || echo "template-tool")
description_val=$(jq -r '.cli_specification.cli_specification.description // "Generic CLI generated by OST Generator"' "$BUNDLE_JSON" 2>/dev/null || echo "Generic CLI generated by OST Generator")
version_val=$(jq -r '.cli_specification.cli_specification.version // "0.1.0"' "$BUNDLE_JSON" 2>/dev/null || echo "0.1.0")

# Extract argument definitions from CLI specification
arguments_json=$(jq -c '.cli_specification.cli_specification.arguments // []' "$BUNDLE_JSON" 2>/dev/null || echo "[]")

# Extract OST content from assembly (assembly.json contains the correct format)
if jq -e '.ost_file_content' "$ASSEMBLY_DIR/assembly.json" >/dev/null 2>&1; then
  # Use the correctly formatted OST content from assembly
  jq -r '.ost_file_content' "$ASSEMBLY_DIR/assembly.json" > "$OST_FILE"
else
  # Fallback: Build final OST file with documented format only
  {
    echo "#!/usr/bin/env -S ostruct runx"
    echo "---"
    echo "cli:"
    echo "  name: $tool_name"
    echo "  description: |"
    echo "    $description_val"
    echo "  options:"
    # Convert arguments to proper YAML format for cli.options with proper escaping
    jq -r '.cli_specification.cli_specification.arguments[] | "    " + .variable_name + ":\n      names: [\"" + .cli_flag + "\", \"" + .short_flag + "\"]\n      help: " + (.help_text | @json) + "\n      type: " + (if .argument_type == "single_value" then "str" elif .argument_type == "flag" then "bool" else .argument_type end) + (if .required then "\n      required: true" else "" end) + (if .default_value then "\n      default: " + (.default_value | @json) else "" end) + (if .validation.allowed_values then "\n      choices: " + (.validation.allowed_values | @json) else "" end)' "$BUNDLE_JSON"

    echo "schema: |"
    # Indent embedded schema by two spaces for YAML block scalar
    jq -r '.schema_content' "$BUNDLE_JSON" | sed 's/^/  /'

    # Add defaults section if arguments have default values
    default_values=$(jq -r '.cli_specification.cli_specification.arguments[] | select(.default_value != null) | "  " + .variable_name + ": " + (.default_value | @json)' "$BUNDLE_JSON")
    if [[ -n "$default_values" ]]; then
        echo "defaults:"
        echo "$default_values"
    else
        echo "defaults: {}"
    fi

    echo "global_args:"
    echo "  pass_through_global: true"
    echo "  model:"
    echo "    mode: \"allowed\""
    echo "    allowed: [\"gpt-4o\", \"gpt-4o-mini\"]"
    echo "    default: \"gpt-4o-mini\""

    echo "---"
    echo ""
    # Append original template content
    jq -r '.template_content' "$BUNDLE_JSON"
  } > "$OST_FILE"
fi

info "OST file created: $OST_FILE"
chmod +x "$OST_FILE"

# Validate the generated OST file
if [[ -z "$DRY_RUN" ]]; then
  echo -e "${BLUE}➤ Validating OST file...${NC}"
  bash tools/ost-generator/src/validate_ost.sh "$OST_FILE"
  if [ $? -eq 0 ]; then
      echo -e "${GREEN}  ✓ OST file validation passed${NC}"
  else
      echo -e "${RED}  ✗ OST file validation failed${NC}"
      exit 1
  fi
else
  info "Skipping validation in dry-run mode"
fi

################################################################################
# Completion
################################################################################
echo ""
echo -e "${GREEN}✅ OST file generation complete!${NC}"
echo ""

# Show the generated CLI interface
show_cli_interface "$ANALYSIS_DIR/cli_spec.json"

echo -e "${BLUE}Generated file: $OST_FILE${NC}"
echo ""
echo "To use your OST file:"
echo "  chmod +x $OST_FILE"
echo "  ./$OST_FILE --help"
echo ""
echo "Or run with ostruct:"
echo "  ostruct runx $OST_FILE [arguments]"
