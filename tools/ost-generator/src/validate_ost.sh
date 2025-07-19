#!/bin/bash

# OST File Validation Script
# Validates generated OST files using jq for syntax checks and ostruct --dry-run for execution

set -euo pipefail

# Ensure yq is available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Deterministic path to ensure_yq.sh (repo-root/scripts/install/dependencies)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
bash "$PROJECT_ROOT/scripts/install/dependencies/ensure_yq.sh" >/dev/null 2>&1 || true

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation functions
validate_yaml_frontmatter() {
    local ost_file="$1"
    echo -e "${BLUE}Validating YAML front-matter...${NC}"

    # Extract YAML front-matter (between first and second ---)
    local yaml_content
    yaml_content=$(sed -n '/^---$/,/^---$/p' "$ost_file" | sed '1d;$d')

    if [ -z "$yaml_content" ]; then
        echo -e "${RED}✗ No YAML front-matter found${NC}"
        return 1
    fi

    # Validate YAML syntax using yq (yq availability ensured earlier)
    echo "$yaml_content" | yq eval '.' >/dev/null 2>&1 || {
        echo -e "${RED}✗ YAML syntax is invalid${NC}"
        return 1
    }
    echo -e "${GREEN}✓ YAML syntax is valid${NC}"

    return 0
}

validate_required_fields() {
    local ost_file="$1"
    echo -e "${BLUE}Validating required fields...${NC}"

    # Extract YAML front-matter
    local yaml_content
    yaml_content=$(sed -n '/^---$/,/^---$/p' "$ost_file" | sed '1d;$d')

    # Check for required fields
    local required_fields=("name" "description" "version" "arguments")
    local missing_fields=()

    for field in "${required_fields[@]}"; do
        if ! echo "$yaml_content" | yq eval ".$field" >/dev/null 2>&1; then
            missing_fields+=("$field")
        fi
    done

    if [ ${#missing_fields[@]} -eq 0 ]; then
        echo -e "${GREEN}✓ All required fields present${NC}"
        return 0
    else
        echo -e "${RED}✗ Missing required fields: ${missing_fields[*]}${NC}"
        return 1
    fi
}

validate_jinja_template() {
    local ost_file="$1"
    echo -e "${BLUE}Validating Jinja2 template syntax...${NC}"

    # Extract template content (after second ---)
    local template_content
    # Use awk to capture everything *after* the second front-matter delimiter.
    # This approach tolerates optional whitespace around the delimiter (e.g. " --- ")
    # and avoids the previous two-sed pipeline that inadvertently returned the YAML
    # header instead of the Jinja template body.
    template_content=$(awk '
        /^[[:space:]]*---[[:space:]]*$/ { delim++; next }  # count delimiters, skip the line
        delim >= 2                         { print }       # print once we are past the second delimiter
    ' "$ost_file")

    if [ -z "$template_content" ]; then
        echo -e "${RED}✗ No template content found${NC}"
        return 1
    fi

    # Basic Jinja2 syntax validation using Python; silent success
    if OST_TEMPLATE_CONTENT="$template_content" python3 - <<'PY'
import sys, jinja2, textwrap, os
from pathlib import Path
template_content = os.environ.get("OST_TEMPLATE_CONTENT", "")
env = jinja2.Environment()
try:
    env.from_string(template_content)
except jinja2.exceptions.TemplateSyntaxError as e:
    print(e, file=sys.stderr)
    sys.exit(1)
PY
then
        echo -e "${GREEN}✓ Jinja2 template syntax is valid${NC}"
        return 0
    else
        echo -e "${RED}✗ Jinja2 template syntax error${NC}"
        return 1
    fi
}

validate_cli_arguments() {
    local ost_file="$1"
    echo -e "${BLUE}Validating CLI arguments structure...${NC}"

    # Extract YAML front-matter
    local yaml_content
    yaml_content=$(sed -n '/^---$/,/^---$/p' "$ost_file" | sed '1d;$d')

    # Check if arguments array exists and is valid
    local arg_count
    arg_count=$(echo "$yaml_content" | yq eval '.arguments | length' 2>/dev/null || echo "0")

    if [ "$arg_count" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $arg_count CLI arguments${NC}"

        # Validate each argument has required fields
        local arg_errors=0
        for ((i=0; i<arg_count; i++)); do
            local arg_name
            arg_name=$(echo "$yaml_content" | yq eval ".arguments[$i].name" 2>/dev/null || echo "null")

            if [ "$arg_name" = "null" ]; then
                echo -e "${RED}✗ Argument $i missing 'name' field${NC}"
                ((arg_errors++))
            fi

            local arg_type
            arg_type=$(echo "$yaml_content" | yq eval ".arguments[$i].type" 2>/dev/null || echo "null")

            if [ "$arg_type" = "null" ]; then
                echo -e "${RED}✗ Argument $i missing 'type' field${NC}"
                ((arg_errors++))
            fi
        done

        if [ $arg_errors -eq 0 ]; then
            echo -e "${GREEN}✓ All CLI arguments have required fields${NC}"
            return 0
        else
            echo -e "${RED}✗ $arg_errors CLI argument validation errors${NC}"
            return 1
        fi
    else
        # if no arguments section yq returns 0 length
        if [ "$arg_count" -eq 0 ]; then
            echo -e "${YELLOW}⚠ No CLI arguments found${NC}"
            return 0
        fi
    fi
}

validate_with_ostruct_dry_run() {
    local ost_file="$1"
    echo -e "${BLUE}Validating with ostruct --dry-run...${NC}"

    # Create a temporary schema file for validation
    local temp_schema
    temp_schema=$(mktemp)
    cat > "$temp_schema" << 'EOF'
{
    "type": "object",
    "properties": {
        "result": {
            "type": "string",
            "description": "Validation result"
        }
    },
    "required": ["result"]
}
EOF

    # Build placeholder args for required options if yq is available
    CLI_ARGS=()
    if command -v yq >/dev/null 2>&1; then
        # Extract all CLI options
        mapfile -t ALL_FLAGS < <(yq eval '.cli.options | to_entries[] | .value.names[0]' "$ost_file" 2>/dev/null)

        for flag in "${ALL_FLAGS[@]}"; do
            # Derive placeholder value depending on option type
            opt_type=$(yq eval ".cli.options | to_entries[] | select(.value.names[0] == \"$flag\") | .value.type" "$ost_file" 2>/dev/null)
            case "$opt_type" in
                bool)
                    first_choice=$(yq eval ".cli.options | to_entries[] | select(.value.names[0] == \"$flag\") | .value.choices[0]" "$ost_file" 2>/dev/null || echo "")
                    if [[ -n "$first_choice" && "$first_choice" != "null" ]]; then
                        CLI_ARGS+=("$flag" "$first_choice")
                    else
                        CLI_ARGS+=("$flag" "true")
                    fi ;;
                *)
                    first_choice=$(yq eval ".cli.options | to_entries[] | select(.value.names[0] == \"$flag\") | .value.choices[0]" "$ost_file" 2>/dev/null || echo "")
                    if [[ -n "$first_choice" && "$first_choice" != "null" ]]; then
                        CLI_ARGS+=("$flag" "$first_choice")
                    else
                        CLI_ARGS+=("$flag" "dummy")
                    fi ;;
            esac
        done
    fi

    if poetry run ostruct runx "$ost_file" --dry-run "${CLI_ARGS[@]}" --progress none --path-security permissive 2>&1 | sed -E '/^(INFO|WARNING):ostruct/d' >/dev/null; then
        echo -e "${GREEN}✓ ostruct --dry-run validation passed${NC}"
        rm -f "$temp_schema"
        return 0
    else
        echo -e "${RED}✗ ostruct --dry-run validation failed${NC}"
        echo "Running ostruct --dry-run for detailed error:"
        poetry run ostruct runx "$ost_file" --dry-run "${CLI_ARGS[@]}" --progress none --path-security permissive 2>&1 | sed -E '/^(INFO|WARNING):ostruct/d' | head -10
        rm -f "$temp_schema"
        return 1
    fi
}

validate_file_structure() {
    local ost_file="$1"
    echo -e "${BLUE}Validating file structure...${NC}"

    # Check if file exists
    if [ ! -f "$ost_file" ]; then
        echo -e "${RED}✗ OST file does not exist: $ost_file${NC}"
        return 1
    fi

    # Check if file is readable
    if [ ! -r "$ost_file" ]; then
        echo -e "${RED}✗ OST file is not readable: $ost_file${NC}"
        return 1
    fi

    # Check if file has content
    if [ ! -s "$ost_file" ]; then
        echo -e "${RED}✗ OST file is empty: $ost_file${NC}"
        return 1
    fi

    # Check for proper OST structure (should have two --- delimiters)
    local delimiter_count
    delimiter_count=$(grep -c "^---$" "$ost_file" 2>/dev/null || echo "0")

    if [ "$delimiter_count" -lt 2 ]; then
        echo -e "${RED}✗ OST file missing proper front-matter delimiters (expected 2 '---' lines, found $delimiter_count)${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ File structure is valid${NC}"
    return 0
}

# Main validation function
validate_ost_file() {
    local ost_file="$1"
    local validation_errors=0

    echo -e "${BLUE}Validating OST file: $ost_file${NC}"
    echo

    # Run all validation checks
    validate_file_structure "$ost_file" || ((validation_errors++))
    echo

    validate_yaml_frontmatter "$ost_file" || ((validation_errors++))
    echo

    validate_required_fields "$ost_file" || ((validation_errors++))
    echo

    validate_cli_arguments "$ost_file" || ((validation_errors++))
    echo

    validate_jinja_template "$ost_file" || ((validation_errors++))
    echo

    validate_with_ostruct_dry_run "$ost_file" || ((validation_errors++))
    echo

    # Summary
    if [ $validation_errors -eq 0 ]; then
        echo -e "${GREEN}🎉 All validations passed! OST file is valid.${NC}"
        return 0
    else
        echo -e "${RED}❌ $validation_errors validation error(s) found.${NC}"
        return 1
    fi
}

# Script entry point
if [ $# -eq 0 ]; then
    echo "Usage: $0 <ost_file>"
    echo "Validates an OST file using multiple validation methods"
    exit 1
fi

validate_ost_file "$1"
