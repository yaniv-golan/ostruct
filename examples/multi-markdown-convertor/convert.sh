#!/bin/bash
# convert.sh - Document converter using ostruct as the brain
# Production-ready document conversion system with comprehensive safety and error recovery

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Script metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Initialize variables
INPUT_FILE=""
OUTPUT_FILE=""
AUTONOMOUS=false
ANALYZE_ONLY=false
DRY_RUN=false
VERBOSE=false
DEBUG=false
CHECK_TOOLS=false
ALLOW_EXTERNAL_TOOLS=false
INTERACTIVE_APPROVAL=false

# Configuration
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_ROOT/config/default.conf}"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Override with local config if exists
LOCAL_CONFIG="$PROJECT_ROOT/config/local.conf"
if [[ -f "$LOCAL_CONFIG" ]]; then
    source "$LOCAL_CONFIG"
fi

# Configuration validation
validate_configuration() {
    local errors=()

    # Validate model settings
    if [[ -z "${DEFAULT_MODEL_ANALYSIS:-}" ]]; then
        errors+=("DEFAULT_MODEL_ANALYSIS not set")
    fi

    if [[ -z "${DEFAULT_MODEL_PLANNING:-}" ]]; then
        errors+=("DEFAULT_MODEL_PLANNING not set")
    fi

    # Validate numeric settings
    if [[ ! "${DEFAULT_TIMEOUT:-}" =~ ^[0-9]+$ ]]; then
        errors+=("DEFAULT_TIMEOUT must be a number")
    fi

    if [[ ! "${MAX_REPLANS:-}" =~ ^[0-9]+$ ]]; then
        errors+=("MAX_REPLANS must be a number")
    fi

    if [[ ! "${MAX_RETRIES:-}" =~ ^[0-9]+$ ]]; then
        errors+=("MAX_RETRIES must be a number")
    fi

    # Validate boolean settings
    if [[ "${ENABLE_CACHING:-}" != "true" && "${ENABLE_CACHING:-}" != "false" ]]; then
        errors+=("ENABLE_CACHING must be true or false")
    fi

    # Validate directory settings
    if [[ -n "${DEFAULT_TEMP_DIR:-}" ]] && [[ ! -d "$(dirname "${DEFAULT_TEMP_DIR}")" ]]; then
        errors+=("Parent directory of DEFAULT_TEMP_DIR does not exist")
    fi

    # Report errors
    if [[ ${#errors[@]} -gt 0 ]]; then
        log "❌ Configuration validation failed:"
        for error in "${errors[@]}"; do
            log "  - $error"
        done
        return 1
    fi

    log_debug "Configuration validation passed"
    return 0
}

# Directory setup
TEMP_DIR="${TEMP_DIR:-$PROJECT_ROOT/temp}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/output}"
CACHE_DIR="${CACHE_DIR:-$TEMP_DIR/cache}"
LOG_DIR="$TEMP_DIR/logs"

# Create directories
mkdir -p "$TEMP_DIR" "$OUTPUT_DIR" "$CACHE_DIR" "$LOG_DIR"

# Logging setup
LOG_FILE="$LOG_DIR/convert_$(date +%Y%m%d_%H%M%S).log"
SECURITY_LOG_FILE="$LOG_DIR/security.log"
PERFORMANCE_LOG_FILE="$LOG_DIR/performance.log"
COMPLETED_STEPS_FILE="$TEMP_DIR/completed_steps.txt"

# Initialize log files
touch "$LOG_FILE" "$SECURITY_LOG_FILE" "$PERFORMANCE_LOG_FILE" "$COMPLETED_STEPS_FILE"

# Logging functions
log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$LOG_FILE" >&2
    if [[ "$VERBOSE" == "true" ]]; then
        echo "$message" >&2
    fi
}

log_section() {
    local section="$1"
    log ""
    log "=== $section ==="
    log ""
}

log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        log "DEBUG: $1"
    fi
}

# Error handling
error_exit() {
    local message="$1"
    local exit_code="${2:-1}"
    log "❌ ERROR: $message"
    exit "$exit_code"
}

# Performance tracking
profile_execution() {
    local start_time=$(date +%s.%N)
    local operation="$1"
    shift

    # Execute operation
    "$@"
    local exit_code=$?

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")

    if [[ "$ENABLE_PERFORMANCE_LOGGING" == "true" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S'),$operation,$duration,$exit_code" >> "$PERFORMANCE_LOG_FILE"
    fi

    return $exit_code
}

# Tool validation
validate_required_tools() {
    local required_tools=("ostruct" "jq")
    local missing_tools=()

    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error_exit "Missing required tools: ${missing_tools[*]}"
    fi
}

# Check all conversion tools
check_conversion_tools() {
    log_section "Tool Availability Check"

    # Dynamically get tool list from tools directory
    local tools=()
    local available_tools=()
    local missing_tools=()

    # Read all tool documentation files
    while IFS= read -r -d '' tool_file; do
        local tool_name=$(basename "$tool_file" .md)
        tools+=("$tool_name")
    done < <(find "$PROJECT_ROOT/tools" -name "*.md" -print0 2>/dev/null)

    # Check each tool availability
    for tool in "${tools[@]}"; do
        local base_command="$tool"
        local is_virtual_tool=false

        # Check if this is a virtual tool
        local tool_file="$PROJECT_ROOT/tools/${tool}.md"
        if [[ -f "$tool_file" ]] && grep -q "is_virtual_tool: true" "$tool_file" 2>/dev/null; then
            is_virtual_tool=true
            base_command=$(grep "base_command:" "$tool_file" | head -1 | sed 's/.*base_command: *//' | tr -d '"' || echo "$tool")
        fi

        if command -v "$base_command" >/dev/null 2>&1; then
            available_tools+=("$tool")
            log "✅ $tool: Available"
        else
            missing_tools+=("$tool")
            log "❌ $tool: Not found"
        fi
    done

    log ""
    log "Available tools: ${#available_tools[@]}/${#tools[@]}"

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log "Missing tools: ${missing_tools[*]}"
        log "Install missing tools for full functionality"
    fi

    return 0
}

# Validate tools required by a specific plan
validate_plan_tools() {
    local plan="$1"
    local required_tools=()
    local missing_tools=()

    # Extract required tools from plan commands
    while IFS= read -r tool; do
        if [[ -n "$tool" ]]; then
            required_tools+=("$tool")
        fi
    done < <(echo "$plan" | jq -r '.steps[].command' | grep -oE '^[a-zA-Z0-9_-]+' | sort -u)

    # Check each tool availability
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done

    # Report missing tools
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log "❌ Missing required tools for plan: ${missing_tools[*]}"
        suggest_tool_installation "${missing_tools[@]}"
        return 1
    fi

    log_debug "All required tools available for plan execution"
    return 0
}

# Suggest tool installation based on platform
suggest_tool_installation() {
    local missing_tools=("$@")

    log ""
    log "Installation suggestions:"

    # Detect platform
    local platform=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        platform="macOS"
        log "macOS (Homebrew):"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        platform="Linux"
        log "Ubuntu/Debian:"
    else
        platform="Other"
        log "Your platform:"
    fi

    for tool in "${missing_tools[@]}"; do
        local tool_file="$PROJECT_ROOT/tools/${tool}.md"
        local install_cmd=""

        # Try to extract installation info from tool documentation
        if [[ -f "$tool_file" ]]; then
            # First, try to get installation info from YAML frontmatter
            local in_frontmatter=false
            local in_installation=false
            local platform_key=""

            # Map platform to frontmatter key
            case "$platform" in
                "macOS") platform_key="macos" ;;
                "Linux") platform_key="ubuntu" ;;
                *) platform_key="" ;;
            esac

            if [[ -n "$platform_key" ]]; then
                while IFS= read -r line; do
                    # Check if we're in frontmatter
                    if [[ "$line" == "---" ]]; then
                        if [[ "$in_frontmatter" == "false" ]]; then
                            in_frontmatter=true
                        else
                            # End of frontmatter
                            break
                        fi
                    elif [[ "$in_frontmatter" == "true" ]]; then
                        # Check for installation section
                        if [[ "$line" =~ ^installation:[[:space:]]*$ ]]; then
                            in_installation=true
                        elif [[ "$in_installation" == "true" ]]; then
                            # Look for our platform
                            if [[ "$line" =~ ^[[:space:]]+${platform_key}:[[:space:]]*\"(.+)\"[[:space:]]*$ ]] ||
                               [[ "$line" =~ ^[[:space:]]+${platform_key}:[[:space:]]*(.+)[[:space:]]*$ ]]; then
                                install_cmd="${BASH_REMATCH[1]}"
                                break
                            elif [[ ! "$line" =~ ^[[:space:]] ]]; then
                                # End of installation section
                                in_installation=false
                            fi
                        fi
                    fi
                done < "$tool_file"
            fi

            # If no frontmatter installation found, fall back to markdown body
            if [[ -z "$install_cmd" ]]; then
                # Look for installation section in the tool doc
                local in_install_section=false
                while IFS= read -r line; do
                    if [[ "$line" =~ ^##.*[Ii]nstall ]]; then
                        in_install_section=true
                    elif [[ "$line" =~ ^## ]] && [[ "$in_install_section" == "true" ]]; then
                        break
                    elif [[ "$in_install_section" == "true" ]] && [[ "$line" =~ ^[[:space:]]*[\`\$] ]]; then
                        # Extract command that matches our platform
                        if [[ "$platform" == "macOS" ]] && [[ "$line" =~ brew ]]; then
                            install_cmd=$(echo "$line" | sed 's/^[[:space:]]*[\`\$]*//' | sed 's/\`*$//')
                            break
                        elif [[ "$platform" == "Linux" ]] && [[ "$line" =~ apt ]]; then
                            install_cmd=$(echo "$line" | sed 's/^[[:space:]]*[\`\$]*//' | sed 's/\`*$//')
                            break
                        fi
                    fi
                done < "$tool_file"
            fi
        fi

        if [[ -n "$install_cmd" ]]; then
            log "  $install_cmd"
        else
            # Fallback to generic suggestions for common tools
            case "$tool" in
                pandoc|pdftotext|tesseract|markitdown|libreoffice|pdftk|tidy|xmllint|htmlhint)
                    if [[ "$platform" == "macOS" ]]; then
                        case "$tool" in
                            pandoc) log "  brew install pandoc" ;;
                            pdftotext) log "  brew install poppler" ;;
                            tesseract) log "  brew install tesseract" ;;
                            markitdown) log "  pip3 install markitdown" ;;
                            libreoffice) log "  brew install --cask libreoffice" ;;
                            pdftk) log "  brew install pdftk-java" ;;
                            tidy) log "  brew install tidy-html5" ;;
                            xmllint) log "  brew install libxml2" ;;
                            htmlhint) log "  npm install -g htmlhint" ;;
                        esac
                    elif [[ "$platform" == "Linux" ]]; then
                        case "$tool" in
                            pandoc) log "  apt-get install pandoc" ;;
                            pdftotext) log "  apt-get install poppler-utils" ;;
                            tesseract) log "  apt-get install tesseract-ocr" ;;
                            markitdown) log "  pip3 install markitdown" ;;
                            libreoffice) log "  apt-get install libreoffice" ;;
                            pdftk) log "  apt-get install pdftk" ;;
                            tidy) log "  apt-get install tidy" ;;
                            xmllint) log "  apt-get install libxml2-utils" ;;
                            htmlhint) log "  npm install -g htmlhint" ;;
                        esac
                    fi
                    ;;
                *)
                    log "  # Check documentation for $tool installation"
                    ;;
            esac
        fi
    done

    if [[ "$platform" == "Other" ]]; then
        log ""
        log "Please install the missing tools using your system's package manager"
    fi

    log ""
}

# Retry mechanism for ostruct calls
retry_ostruct() {
    local max_retries="${MAX_RETRIES:-2}"
    local retry_count=0

    while [[ $retry_count -le $max_retries ]]; do
        if "$@"; then
            return 0
        else
            local exit_code=$?
            ((retry_count++))

            if [[ $retry_count -le $max_retries ]]; then
                log "ostruct call failed (attempt $retry_count), retrying..."
                sleep $((retry_count * 2))
            else
                log "ostruct call failed after $max_retries attempts"
                return $exit_code
            fi
        fi
    done
}

# Cache management
get_cache_key() {
    local input_file="$1"
    echo "$(md5sum "$input_file" 2>/dev/null | cut -d' ' -f1 || echo "nocache")"
}

validate_cache_entry() {
    local cache_file="$1"
    local source_file="$2"

    # Check cache file exists and is readable
    if [[ ! -f "$cache_file" ]] || [[ ! -r "$cache_file" ]]; then
        return 1
    fi

    # Verify cache is newer than source
    if [[ "$cache_file" -ot "$source_file" ]]; then
        log_debug "Cache expired: $cache_file older than $source_file"
        return 1
    fi

    # Validate JSON structure for analysis/plan caches
    if [[ "$cache_file" == *"analysis"* ]] || [[ "$cache_file" == *"plan"* ]]; then
        if ! jq empty "$cache_file" 2>/dev/null; then
            log_debug "Cache corrupted: Invalid JSON in $cache_file"
            rm -f "$cache_file"  # Remove corrupted cache
            return 1
        fi
    fi

    return 0
}

get_cached_analysis() {
    local input_file="$1"
    local cache_key=$(get_cache_key "$input_file")
    local cache_file="$CACHE_DIR/analysis_${cache_key}.json"

    if [[ "$ENABLE_CACHING" == "true" ]] && validate_cache_entry "$cache_file" "$input_file"; then
        log_debug "Using cached analysis for $input_file"
        cat "$cache_file"
        return 0
    fi

    return 1
}

store_cached_analysis() {
    local input_file="$1"
    local analysis="$2"
    local cache_key=$(get_cache_key "$input_file")
    local cache_file="$CACHE_DIR/analysis_${cache_key}.json"

    if [[ "$ENABLE_CACHING" == "true" ]]; then
        echo "$analysis" > "$cache_file"
        log_debug "Cached analysis for $input_file"
    fi
}

# File validation
validate_file_path() {
    local file_path="$1"
    local resolved_path

    # Resolve path and check it's within project directory
    resolved_path=$(realpath "$file_path" 2>/dev/null) || return 1

    # Ensure path is within allowed directories
    case "$resolved_path" in
        "$PROJECT_ROOT"/*|"$TEMP_DIR"/*|"$OUTPUT_DIR"/*)
            return 0
            ;;
        *)
            log "❌ SECURITY: Path outside allowed directories: $resolved_path"
            return 1
            ;;
    esac
}

# Output directory validation (for files that don't exist yet)
validate_output_directory() {
    local dir_path="$1"

    # Handle relative paths
    if [[ ! "$dir_path" =~ ^/ ]]; then
        dir_path="$PWD/$dir_path"
    fi

    # Normalize the path
    dir_path=$(echo "$dir_path" | sed 's|/\./|/|g' | sed 's|//|/|g')

    # Ensure directory is within allowed directories
    case "$dir_path" in
        "$PROJECT_ROOT"/*|"$TEMP_DIR"/*|"$OUTPUT_DIR"/*|"$PWD"/output/*|"$PWD"/temp/*)
            return 0
            ;;
        *)
            log "❌ SECURITY: Output directory outside allowed directories: $dir_path"
            return 1
            ;;
    esac
}

# Large document handling
handle_large_document() {
    local input_file="$1"
    local file_size
    file_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file" 2>/dev/null)

    # Check if file is larger than threshold
    if [[ $file_size -gt ${LARGE_DOCUMENT_THRESHOLD:-104857600} ]]; then
        log "Large document detected ($(( file_size / 1024 / 1024 ))MB), implementing chunking strategy"

        case "${input_file##*.}" in
            pdf)
                chunk_pdf_document "$input_file"
                ;;
            *)
                log "⚠️  Large document of unsupported type, proceeding with caution"
                return 1
                ;;
        esac
    else
        return 1  # Not a large document, use normal processing
    fi
}

chunk_pdf_document() {
    local input_file="$1"
    local chunk_dir="$TEMP_DIR/chunks_$(basename "$input_file" .pdf)"
    mkdir -p "$chunk_dir"

    # Get page count
    local page_count
    if command -v pdfinfo >/dev/null 2>&1; then
        page_count=$(pdfinfo "$input_file" | grep "Pages:" | awk '{print $2}')
    else
        log "⚠️  pdfinfo not available, cannot determine page count"
        return 1
    fi

    # Chunk into segments
    local chunk_size="${PDF_CHUNK_SIZE:-50}"
    local chunk_num=1

    for ((start=1; start<=page_count; start+=chunk_size)); do
        local end=$((start + chunk_size - 1))
        if [[ $end -gt $page_count ]]; then
            end=$page_count
        fi

        local chunk_file="$chunk_dir/chunk_${chunk_num}.pdf"
        if command -v pdftk >/dev/null 2>&1; then
            pdftk "$input_file" cat "${start}-${end}" output "$chunk_file"
            log "Created chunk $chunk_num: pages $start-$end"
            ((chunk_num++))
        else
            log "⚠️  pdftk not available, cannot chunk PDF"
            return 1
        fi
    done

    echo "$chunk_dir"
}

# Dependency handling functions
check_dependencies() {
    local step="$1"
    local depends_on=$(echo "$step" | jq -r '.depends_on // empty')

    if [[ -n "$depends_on" ]]; then
        # Check if dependency was completed
        if ! grep -q "^$depends_on$" "$COMPLETED_STEPS_FILE"; then
            log "❌ Dependency not met: $depends_on"
            return 1
        fi

        # Validate dependency output exists
        local dep_output=$(get_step_output "$depends_on")
        if [[ -n "$dep_output" ]] && [[ ! -f "$dep_output" ]]; then
            log "❌ Dependency output missing: $dep_output"
            return 1
        fi
    fi

    return 0
}

get_step_output() {
    local step_id="$1"
    # Extract output file from completed step record
    # This is a simplified implementation - in practice, you'd store step outputs
    echo ""  # Return empty for now, can be enhanced later
}

validate_plan_dependencies() {
    local plan="$1"
    local step_ids=()
    local errors=()

    # Extract all step IDs
    while IFS= read -r step_id; do
        step_ids+=("$step_id")
    done < <(echo "$plan" | jq -r '.steps[].id')

    # Check each step's dependencies
    local total_steps=$(echo "$plan" | jq -r '.steps | length')
    for ((i=0; i<total_steps; i++)); do
        local step=$(echo "$plan" | jq -r ".steps[$i]")
        local step_id=$(echo "$step" | jq -r '.id')
        local depends_on=$(echo "$step" | jq -r '.depends_on // empty')

        if [[ -n "$depends_on" ]]; then
            # Check if dependency exists in plan
            local found=false
            for existing_id in "${step_ids[@]}"; do
                if [[ "$existing_id" == "$depends_on" ]]; then
                    found=true
                    break
                fi
            done

            if [[ "$found" == "false" ]]; then
                errors+=("Step $step_id depends on non-existent step: $depends_on")
            fi
        fi
    done

    # Check for circular dependencies (simplified check)
    detect_circular_dependencies "$plan"

    if [[ ${#errors[@]} -gt 0 ]]; then
        log "❌ Plan validation errors:"
        for error in "${errors[@]}"; do
            log "  - $error"
        done
        return 1
    fi

    return 0
}

detect_circular_dependencies() {
    local plan="$1"
    # Simplified circular dependency detection
    # In a full implementation, this would use proper graph algorithms
    local total_steps=$(echo "$plan" | jq -r '.steps | length')

    for ((i=0; i<total_steps; i++)); do
        local step=$(echo "$plan" | jq -r ".steps[$i]")
        local step_id=$(echo "$step" | jq -r '.id')
        local depends_on=$(echo "$step" | jq -r '.depends_on // empty')

        if [[ -n "$depends_on" && "$depends_on" == "$step_id" ]]; then
            log "❌ Circular dependency detected: Step $step_id depends on itself"
            return 1
        fi
    done

    return 0
}

# Safety checking with ostruct
safety_check() {
    local command="$1"
    local autonomous="$2"

    # Try cached safety decision first
    local cache_key=$(echo "$command" | md5sum | cut -d' ' -f1)
    local cache_file="$CACHE_DIR/safety_${cache_key}.json"
    local SAFETY_CHECK=""

    if [[ -f "$cache_file" ]] && [[ "$ENABLE_SAFETY_CACHING" == "true" ]]; then
        # Check cache age
        local cache_age=$(($(date +%s) - $(stat -c %Y "$cache_file" 2>/dev/null || echo 0)))
        if [[ $cache_age -lt ${SAFETY_CACHE_TTL:-86400} ]]; then
            log_debug "Using cached safety decision for command"
            SAFETY_CHECK=$(cat "$cache_file")
        fi
    fi

    # If no valid cache, use ostruct for intelligent safety evaluation
    if [[ -z "$SAFETY_CHECK" ]]; then
        log_debug "Evaluating command safety with ostruct"
        SAFETY_CHECK=$(retry_ostruct ostruct run prompts/safety_check.j2 schemas/safety.json \
            -V "command=$command" \
            -V "autonomous=$autonomous" \
            --dta tools_docs tools/ \
            --model "${MODEL_SAFETY:-gpt-4.1}" \
            --temperature 0.1 \
            --progress-level none)

        # Cache the decision if caching is enabled
        if [[ "$ENABLE_SAFETY_CACHING" == "true" ]]; then
            echo "$SAFETY_CHECK" > "$cache_file"
        fi
    fi

    # Parse and act on safety result
    local status=$(echo "$SAFETY_CHECK" | jq -r '.status')
    local reason=$(echo "$SAFETY_CHECK" | jq -r '.reason // empty')

    case "$status" in
        "safe")
            log_debug "Command approved as safe: $command"
            return 0
            ;;
        "needs_approval")
            handle_approval_needed "$command" "$reason"
            ;;
        "malicious")
            handle_malicious_command "$command" "$reason"
            return 1
            ;;
        *)
            log "⚠️  Unknown safety status: $status"
            return 1
            ;;
    esac
}

# Handle commands that need approval
handle_approval_needed() {
    local command="$1"
    local reason="$2"

    if [[ "$AUTONOMOUS" == "true" ]]; then
        log "❌ Command needs approval but running in autonomous mode: $command"
        log "Reason: $reason"
        return 1
    else
        log "⚠️  Command requires approval: $command"
        log "Reason: $reason"

        echo "Do you want to execute this command? (y/N): "
        read -r response

        case "$response" in
            [yY][eE][sS]|[yY])
                log "✅ User approved command execution"
                return 0
                ;;
            *)
                log "❌ User rejected command execution"
                return 1
                ;;
        esac
    fi
}

# Handle malicious commands
handle_malicious_command() {
    local command="$1"
    local reason="$2"

    log "🚨 SECURITY: Malicious command blocked: $command"
    log "Reason: $reason"

    # Log to security audit file
    echo "$(date '+%Y-%m-%d %H:%M:%S') MALICIOUS_COMMAND_BLOCKED: $command | $reason" >> "$SECURITY_LOG_FILE"

    return 1
}

# Secure command execution
execute_command_safely() {
    local command="$1"
    local input_file="$2"
    local output_file="$3"

    # Extract the tool name from the command for validation
    local tool
    tool=$(echo "$command" | awk '{print $1}')

    # For virtual tools, we need to check the base command
    local base_command="$tool"
    local check_tool="$tool"

    # Check if this might be a virtual tool command (e.g., starts with "ostruct run")
    if [[ "$tool" == "ostruct" ]] && [[ "$command" =~ ^ostruct[[:space:]]+run ]]; then
        # This is an ostruct virtual tool command, it's allowed if ostruct is in allowlist
        check_tool="ostruct"
    fi

    # SECURITY: Validate tool is in allowlist
    if [[ ! " ${ALLOWED_TOOLS[*]} " =~ " ${check_tool} " ]]; then
        log "❌ SECURITY: Tool '$check_tool' not in allowlist"
        return 1
    fi

    # SECURITY: Validate tool exists
    if ! command -v "$tool" >/dev/null 2>&1; then
        log "❌ Tool '$tool' not found"
        return 1
    fi

    # SECURITY: Validate file paths are within project directory
    # Skip validation for placeholder paths (like "input.md", "output.pdf")
    # These are plan templates, not actual file paths
    if [[ "$input_file" != "null" && "$input_file" != "" && ! "$input_file" =~ ^[a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+$ ]]; then
        if ! validate_file_path "$input_file"; then
            log "❌ SECURITY: Invalid input file path detected: $input_file"
            return 2  # Security error - should not retry
        fi
    fi

    if [[ "$output_file" != "null" && "$output_file" != "" && ! "$output_file" =~ ^[a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+$ ]]; then
        # For output files, validate the directory path instead of the full path
        local output_dir=$(dirname "$output_file")
        if ! validate_output_directory "$output_dir"; then
            log "❌ SECURITY: Invalid output directory detected: $output_dir"
            return 2  # Security error - should not retry
        fi
    fi

    # SECURITY: Execute with timeout using bash to handle shell features like redirection
    # Use eval with proper quoting to handle complex commands with redirection
    timeout "${DEFAULT_TIMEOUT:-300}" bash -c "$command" 2>&1 | tee -a "$LOG_FILE"
    return "${PIPESTATUS[0]}"
}

# Pre-analyze document with tools to gather metadata
pre_analyze_document() {
    local input_file="$1"
    local file_ext="${input_file##*.}"
    local file_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file" 2>/dev/null || echo "0")

    log_debug "Planning pre-analysis for $file_ext file"

    # Use ostruct to determine which pre-analysis tools to run
    local pre_analysis_plan_file="$TEMP_DIR/pre_analysis_plan_$$.json"

    # Use the same available tools directory as main analysis
    # This ensures ostruct can see all tools and decide which are appropriate for pre-analysis
    local available_tools_dir="$TEMP_DIR/available_tools"
    create_available_tools_docs "$available_tools_dir"

    # Get pre-analysis plan from ostruct
    if ostruct run prompts/pre_analyze.j2 schemas/pre_analysis.json \
        -V "input_file=$input_file" \
        -V "file_extension=$file_ext" \
        -V "file_size_bytes=$file_size" \
        --dta tools_docs "$available_tools_dir" \
        --model "${MODEL_ANALYSIS:-gpt-4o-mini}" \
        --temperature 0.1 \
        --progress-level none \
        --output-file "$pre_analysis_plan_file" 2>/dev/null; then

        local pre_analysis_plan=$(cat "$pre_analysis_plan_file")

        # Initialize result variables
        local document_metadata=""
        local media_analysis=""
        local text_sample=""
        local text_coverage_percent="0"
        local additional_analysis=""

        # Execute each pre-analysis step
        local step_count=$(echo "$pre_analysis_plan" | jq -r '.pre_analysis_steps | length')

        for ((i=0; i<step_count; i++)); do
            local step=$(echo "$pre_analysis_plan" | jq -r ".pre_analysis_steps[$i]")
            local tool=$(echo "$step" | jq -r '.tool')
            local command=$(echo "$step" | jq -r '.command')
            local output_type=$(echo "$step" | jq -r '.output_type')

            log_debug "Running pre-analysis: $tool"

            # Execute command and capture output
            local output=""
            if command -v "$tool" >/dev/null 2>&1; then
                output=$(eval "$command" 2>/dev/null || echo "")
            fi

            # Store output in appropriate variable based on type
            case "$output_type" in
                metadata)
                    document_metadata="$output"
                    ;;
                media_list)
                    media_analysis="$output"
                    ;;
                text_sample)
                    text_sample="$output"
                    # Try to extract coverage percentage if the command included it
                    if [[ "$command" =~ "coverage" ]]; then
                        text_coverage_percent=$(echo "$output" | grep -oE '[0-9]+%' | head -1 | tr -d '%' || echo "100")
                    else
                        text_coverage_percent="100"
                    fi
                    ;;
                structure_info|file_info)
                    additional_analysis="${additional_analysis}${output}\n"
                    ;;
            esac
        done

        # Clean up
        rm -f "$pre_analysis_plan_file"

        # Create JSON object with pre-analysis data
        local pre_analysis_json=$(jq -n \
            --arg dm "$document_metadata" \
            --arg ma "$media_analysis" \
            --arg ts "$text_sample" \
            --arg tcp "$text_coverage_percent" \
            --arg aa "$additional_analysis" \
            '{
                document_metadata: $dm,
                media_analysis: $ma,
                text_sample: $ts,
                text_coverage_percent: $tcp,
                additional_analysis: $aa
            }')

        echo "$pre_analysis_json"
    else
        # Fallback: return empty pre-analysis if ostruct fails
        log_debug "Pre-analysis planning failed, using empty pre-analysis"
        echo '{"document_metadata":"","media_analysis":"","text_sample":"","text_coverage_percent":"100","additional_analysis":""}'
    fi
}

# Document analysis
analyze_document() {
    local input_file="$1"

    log_section "Document Analysis"
    log "Analyzing document: $(basename "$input_file")"

    # Check cache first
    local analysis
    if analysis=$(get_cached_analysis "$input_file"); then
        log "Using cached analysis"
        echo "$analysis"
        return 0
    fi

    # Run pre-analysis to gather tool outputs
    log_debug "Running pre-analysis tools..."
    local pre_analysis_data
    pre_analysis_data=$(pre_analyze_document "$input_file")

    # Extract individual components for passing to ostruct
    local document_metadata=$(echo "$pre_analysis_data" | jq -r '.document_metadata // ""')
    local media_analysis=$(echo "$pre_analysis_data" | jq -r '.media_analysis // ""')
    local text_sample=$(echo "$pre_analysis_data" | jq -r '.text_sample // ""')
    local text_coverage_percent=$(echo "$pre_analysis_data" | jq -r '.text_coverage_percent // "0"')
    local additional_analysis=$(echo "$pre_analysis_data" | jq -r '.additional_analysis // ""')

    # Perform analysis with ostruct
    log "Performing document analysis with ostruct..."

    # Create input_file metadata for template
    local file_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file" 2>/dev/null || echo "0")
    local file_name=$(basename "$input_file")
    local file_ext="${file_name##*.}"
    local input_file_json="{\"name\":\"$file_name\",\"size\":$file_size,\"extension\":\"$file_ext\"}"

    # Debug output
    log_debug "input_file_json: $input_file_json"
    log_debug "Pre-analysis data gathered: metadata=$(echo "$document_metadata" | wc -l) lines, media=$(echo "$media_analysis" | wc -l) lines"

    # Use temporary file for clean JSON output
    local temp_analysis_file="$TEMP_DIR/analysis_$$.json"

    # Create filtered tools directory with only available tools for analysis
    local available_tools_dir="$TEMP_DIR/available_tools"
    create_available_tools_docs "$available_tools_dir"

    if profile_execution "analysis" retry_ostruct ostruct run prompts/analyze.j2 schemas/analysis.json \
        --fca input_file "$input_file" \
        -J "input_file=$input_file_json" \
        -V "document_metadata=$document_metadata" \
        -V "media_analysis=$media_analysis" \
        -V "text_sample=$text_sample" \
        -V "text_coverage_percent=$text_coverage_percent" \
        -V "additional_analysis=$additional_analysis" \
        --dca tools_docs "$available_tools_dir" \
        --model "${MODEL_ANALYSIS:-gpt-4.1}" \
        --temperature 0.1 \
        --progress-level none \
        --output-file "$temp_analysis_file"; then

        analysis=$(cat "$temp_analysis_file")

        # Keep temp file for debugging if debug mode is enabled
        if [[ "$DEBUG" != "true" ]]; then
            rm -f "$temp_analysis_file"
        else
            log_debug "Analysis JSON saved to: $temp_analysis_file"
        fi

        if [[ -n "$analysis" ]]; then
            store_cached_analysis "$input_file" "$analysis"
            log "✅ Analysis completed successfully"
            echo "$analysis"
            return 0
        else
            error_exit "Document analysis failed - empty response"
        fi
    else
        if [[ "$DEBUG" != "true" ]]; then
            rm -f "$temp_analysis_file"
        else
            log_debug "Failed analysis attempt saved to: $temp_analysis_file"
        fi
        error_exit "Document analysis failed"
    fi
}

# Conversion planning
create_conversion_plan() {
    local analysis="$1"
    local output_file="$2"

    log_section "Conversion Planning"
    log "Creating conversion plan based on analysis..."

    # Extract target format from output file extension
    local target_format="${output_file##*.}"
    log_debug "Target format detected: $target_format"

    # Filter tools based on analysis recommendations
    local filtered_tools_dir="$TEMP_DIR/filtered_tools"
    filter_tool_docs_by_analysis "$analysis" "$filtered_tools_dir"

    # Create plan with ostruct using temporary file for clean JSON output
    local temp_plan_file="$TEMP_DIR/plan_$$.json"

    if profile_execution "planning" retry_ostruct ostruct run prompts/plan.j2 schemas/plan.json \
        -V "analysis=$analysis" \
        -V "target_format=$target_format" \
        -V "allow_external_tools=$ALLOW_EXTERNAL_TOOLS" \
        --dta tools_docs "$filtered_tools_dir" \
        --model "${MODEL_PLANNING:-gpt-4.1}" \
        --temperature 0.3 \
        --progress-level none \
        --output-file "$temp_plan_file"; then

        local plan=$(cat "$temp_plan_file")

        # Keep temp file for debugging if debug mode is enabled
        if [[ "$DEBUG" != "true" ]]; then
            rm -f "$temp_plan_file"
        else
            log_debug "Plan JSON saved to: $temp_plan_file"
        fi

        if [[ -n "$plan" ]]; then
            log "✅ Conversion plan created successfully"
            echo "$plan"
            return 0
        else
            error_exit "Conversion planning failed - empty response"
        fi
    else
        if [[ "$DEBUG" != "true" ]]; then
            rm -f "$temp_plan_file"
        else
            log_debug "Failed planning attempt saved to: $temp_plan_file"
        fi
        error_exit "Conversion planning failed"
    fi
}

# Create directory with only available tools documentation
create_available_tools_docs() {
    local available_dir="$1"

    mkdir -p "$available_dir"

    # Get list of all tools from the tools directory
    local all_tools=()
    while IFS= read -r -d '' tool_file; do
        local tool_name=$(basename "$tool_file" .md)
        all_tools+=("$tool_name")
    done < <(find "$PROJECT_ROOT/tools" -name "*.md" -print0 2>/dev/null)

    for tool in "${all_tools[@]}"; do
        local tool_file="$PROJECT_ROOT/tools/${tool}.md"
        local base_command="$tool"
        local is_virtual_tool=false

        # Check if this is a virtual tool by reading its metadata
        if [[ -f "$tool_file" ]]; then
            # Extract base_command from tool metadata if it's a virtual tool
            if grep -q "is_virtual_tool: true" "$tool_file" 2>/dev/null; then
                is_virtual_tool=true
                base_command=$(grep "base_command:" "$tool_file" | head -1 | sed 's/.*base_command: *//' | tr -d '"' || echo "$tool")
                log_debug "Tool $tool is a virtual tool using base command: $base_command"
            fi
        fi

        # Check if tool (or its base command) is available on the system
        if command -v "$base_command" >/dev/null 2>&1; then
            # Check if base command is in allowlist for virtual tools, or tool itself for regular tools
            local check_tool="$tool"
            if [[ "$is_virtual_tool" == "true" ]]; then
                check_tool="$base_command"
            fi

            if [[ " ${ALLOWED_TOOLS[*]} " =~ " ${check_tool} " ]]; then
                if [[ -f "$tool_file" ]]; then
                    cp "$tool_file" "$available_dir/"
                    log_debug "Including available tool documentation: $tool"
                else
                    log_debug "⚠️  Tool documentation not found for available tool: $tool"
                fi
            else
                log_debug "⚠️  Tool $tool (base: $base_command) available but not in allowlist, skipping"
            fi
        else
            log_debug "⚠️  Tool $tool (base: $base_command) not available on system, excluding from analysis"
        fi
    done

    # Ensure we have at least some tools available
    local available_count=$(find "$available_dir" -name "*.md" | wc -l)
    if [[ $available_count -eq 0 ]]; then
        log "⚠️  No tools available for analysis, this may cause issues"
    else
        log_debug "Analysis will consider $available_count available tools"
    fi
}

# Filter tool documentation by analysis
filter_tool_docs_by_analysis() {
    local analysis="$1"
    local filtered_dir="$2"

    mkdir -p "$filtered_dir"

    # Extract recommended tools from analysis
    local recommended_tools
    recommended_tools=$(echo "$analysis" | jq -r '.recommended_tools[]? // empty' 2>/dev/null || echo "")

    if [[ -n "$recommended_tools" ]]; then
        # Copy only relevant tool docs based on analysis recommendations
        # but only if the tools are actually available on the system
        while IFS= read -r tool; do
            local tool_file="$PROJECT_ROOT/tools/${tool}.md"
            local base_command="$tool"
            local is_virtual_tool=false

            # Check if this is a virtual tool
            if [[ -f "$tool_file" ]]; then
                if grep -q "is_virtual_tool: true" "$tool_file" 2>/dev/null; then
                    is_virtual_tool=true
                    base_command=$(grep "base_command:" "$tool_file" | head -1 | sed 's/.*base_command: *//' | tr -d '"' || echo "$tool")
                fi
            fi

            # Check if tool (or its base command) is available on the system
            if ! command -v "$base_command" >/dev/null 2>&1; then
                log_debug "⚠️  Tool $tool (base: $base_command) recommended by analysis but not available on system, skipping"
                continue
            fi

            if [[ -f "$tool_file" ]]; then
                cp "$tool_file" "$filtered_dir/"
                log_debug "Including tool documentation: $tool"
            else
                log_debug "⚠️  Tool documentation not found: $tool"
            fi
        done <<< "$recommended_tools"
    else
        # Fallback: include all available tools from allowlist
        # Let the planner decide which ones to use
        local available_tools_dir="$TEMP_DIR/available_tools"
        create_available_tools_docs "$available_tools_dir"

        # Copy all available tools
        if [[ -d "$available_tools_dir" ]]; then
            cp "$available_tools_dir"/*.md "$filtered_dir/" 2>/dev/null || true
            log_debug "No specific recommendations, including all available tools"
        fi
    fi
}

# Create replan when original plan fails
create_replan() {
    local original_analysis="$1"
    local failed_plan="$2"
    local failure_reason="$3"
    local replan_count="${4:-1}"

    log_section "Replanning"
    log "Creating alternative plan (attempt $replan_count)"

    # Use ostruct to generate alternative plan with temporary file for clean JSON output
    local temp_replan_file="$TEMP_DIR/replan_$$.json"

    if profile_execution "replanning" retry_ostruct ostruct run prompts/replan.j2 schemas/plan.json \
        -V "original_analysis=$original_analysis" \
        -V "failed_plan=$failed_plan" \
        -V "failure_reason=$failure_reason" \
        -V "replan_count=$replan_count" \
        --dta tools_docs tools/ \
        --model "${MODEL_PLANNING:-gpt-4.1}" \
        --temperature 0.3 \
        --progress-level none \
        --output-file "$temp_replan_file"; then

        local replan=$(cat "$temp_replan_file")

        # Keep temp file for debugging if debug mode is enabled
        if [[ "$DEBUG" != "true" ]]; then
            rm -f "$temp_replan_file"
        else
            log_debug "Replan JSON saved to: $temp_replan_file"
        fi

        if [[ -n "$replan" ]]; then
            log "✅ Replan generated successfully"
            echo "$replan"
            return 0
        else
            log "❌ Replan generation failed - empty response"
            return 1
        fi
    else
        if [[ "$DEBUG" != "true" ]]; then
            rm -f "$temp_replan_file"
        else
            log_debug "Failed replanning attempt saved to: $temp_replan_file"
        fi
        log "❌ Replan generation failed"
        return 1
    fi
}

# Display plan for user review
display_plan() {
    local plan="$1"
    local plan_type="${2:-Plan}"

    log_section "$plan_type Review"

    local total_steps=$(echo "$plan" | jq -r '.total_steps')
    local estimated_duration=$(echo "$plan" | jq -r '.estimated_duration // "unknown"')
    local plan_id=$(echo "$plan" | jq -r '.plan_id // "unknown"')

    log "Plan ID: $plan_id"
    log "Total Steps: $total_steps"
    log "Estimated Duration: ${estimated_duration}s"
    log ""

    # Display each step
    for ((i=0; i<total_steps; i++)); do
        local step=$(echo "$plan" | jq -r ".steps[$i]")
        local step_id=$(echo "$step" | jq -r '.id')
        local description=$(echo "$step" | jq -r '.description')
        local command=$(echo "$step" | jq -r '.command')
        local tool=$(echo "$step" | jq -r '.tool')
        local depends_on=$(echo "$step" | jq -r '.depends_on // "none"')

        log "Step $((i+1)): $step_id"
        log "  Description: $description"
        log "  Tool: $tool"
        log "  Command: $command"
        log "  Depends on: $depends_on"
        log ""
    done

    # Display quality checks
    local quality_checks=$(echo "$plan" | jq -r '.quality_checks[]? // empty' 2>/dev/null)
    if [[ -n "$quality_checks" ]]; then
        log "Quality Checks:"
        while IFS= read -r check; do
            log "  - $check"
        done <<< "$quality_checks"
        log ""
    fi

    # Display fallback strategy
    local fallback=$(echo "$plan" | jq -r '.fallback_strategy // empty')
    if [[ -n "$fallback" ]]; then
        log "Fallback Strategy: $fallback"
        log ""
    fi
}

# Get user approval for plan execution
get_plan_approval() {
    local plan_type="${1:-Plan}"

    while true; do
        echo -n "Do you want to proceed with this $plan_type? [y/N/s(how again)]: " >&2
        read -r response

        case "$response" in
            [Yy]|[Yy][Ee][Ss])
                return 0
                ;;
            [Ss]|[Ss][Hh][Oo][Ww])
                return 2  # Show again
                ;;
            [Nn]|[Nn][Oo]|"")
                log "❌ Plan execution cancelled by user"
                return 1
                ;;
            *)
                echo "Please answer y(es), n(o), or s(how again)" >&2
                ;;
        esac
    done
}

# Display step before execution
display_step() {
    local step="$1"
    local step_number="$2"
    local total_steps="$3"

    local step_id=$(echo "$step" | jq -r '.id')
    local description=$(echo "$step" | jq -r '.description')
    local command=$(echo "$step" | jq -r '.command')
    local tool=$(echo "$step" | jq -r '.tool')

    log_section "Executing Step $step_number/$total_steps"
    log "Step ID: $step_id"
    log "Description: $description"
    log "Tool: $tool"
    log "Command: $command"
    log ""
}

# Execute conversion plan with replanning on failure
execute_conversion_plan() {
    local plan="$1"
    local input_file="$2"
    local output_file="$3"
    local original_analysis="${4:-}"
    local replan_count="${5:-0}"

    log_section "Plan Execution"

    # Validate plan dependencies first
    if ! validate_plan_dependencies "$plan"; then
        log "❌ Plan validation failed"
        return 1
    fi

    # Validate required tools are available
    if ! validate_plan_tools "$plan"; then
        log "❌ Required tools not available for plan execution"
        return 1
    fi

    local total_steps
    total_steps=$(echo "$plan" | jq -r '.total_steps')
    log "Executing plan with $total_steps steps"

    # Execute steps sequentially
    for ((i=0; i<total_steps; i++)); do
        local step
        step=$(echo "$plan" | jq -r ".steps[$i]")
        local step_id
        step_id=$(echo "$step" | jq -r '.id')

        # Display step information
        display_step "$step" "$((i+1))" "$total_steps"

        if execute_step_with_recovery "$step" "$input_file" "$output_file"; then
            echo "$step_id" >> "$COMPLETED_STEPS_FILE"
            log "✅ Step $step_id completed"
        else
            log "❌ Step $step_id failed"

            # Attempt replanning if we haven't exceeded max replans
            if [[ $replan_count -lt ${MAX_REPLANS:-3} ]]; then
                log "Attempting to replan..."
                local new_replan_count=$((replan_count + 1))

                if [[ -n "$original_analysis" ]]; then
                    local replan
                    if replan=$(create_replan "$original_analysis" "$plan" "Step $step_id failed" "$new_replan_count"); then
                        # Interactive replan approval
                        if [[ "$INTERACTIVE_APPROVAL" == "true" ]]; then
                            while true; do
                                display_plan "$replan" "Replan #$new_replan_count"
                                get_plan_approval "replan"
                                local approval_result=$?

                                case $approval_result in
                                    0) break ;;  # Approved, continue
                                    1)
                                        log "❌ Replan execution cancelled by user"
                                        return 1
                                        ;;  # Rejected
                                    2) continue ;;  # Show again
                                esac
                            done
                        fi

                        log "Executing replan..."
                        if execute_conversion_plan "$replan" "$input_file" "$output_file" "$original_analysis" "$new_replan_count"; then
                            return 0
                        fi
                    fi
                fi
            else
                log "❌ Maximum replan attempts ($MAX_REPLANS) exceeded"
            fi

            return 1
        fi
    done

    return 0
}

# Execute a single step with recovery
execute_step_with_recovery() {
    local step="$1"
    local input_file="$2"
    local output_file="$3"
    local max_step_retries=2
    local retry_count=0

    local step_id
    step_id=$(echo "$step" | jq -r '.id')

    while [[ $retry_count -le $max_step_retries ]]; do
        if execute_single_step "$step" "$input_file" "$output_file"; then
            return 0
        else
            local exit_code=$?

            # Security errors (exit code 2) should not be retried
            if [[ $exit_code -eq 2 ]]; then
                log "❌ Step $step_id failed with security error - aborting without retry"
                return $exit_code
            fi

            ((retry_count++))

            if [[ $retry_count -le $max_step_retries ]]; then
                log "Step $step_id failed (attempt $retry_count), retrying..."
                sleep $((retry_count * 2))
            else
                log "Step $step_id failed after $max_step_retries attempts"
                return $exit_code
            fi
        fi
    done
}

# Execute a single step
execute_single_step() {
    local step="$1"
    local input_file="$2"
    local output_file="$3"

    local step_id
    step_id=$(echo "$step" | jq -r '.id')
    local command
    command=$(echo "$step" | jq -r '.command')
    local step_input
    step_input=$(echo "$step" | jq -r '.input_file')
    local step_output
    step_output=$(echo "$step" | jq -r '.output_file')

    # Replace template variables in command
    # Handle quoted template variables properly by escaping the file paths
    local escaped_input_file=$(printf '%q' "$input_file")
    local escaped_output_file=$(printf '%q' "$output_file")
    local escaped_temp_dir=$(printf '%q' "$TEMP_DIR")
    command=${command//\{\{INPUT_FILE\}\}/$escaped_input_file}
    command=${command//\{\{OUTPUT_FILE\}\}/$escaped_output_file}
    # Also replace $TEMP_DIR variable references
    command=${command//\$TEMP_DIR/$escaped_temp_dir}

    # Validate command doesn't contain newlines
    if [[ "$command" =~ $'\n' ]]; then
        log "❌ Step $step_id contains multiple commands (newlines detected)"
        log "Command: $command"
        log "Each step must contain only a single command. Use multiple steps for multiple commands."
        return 1
    fi

    log_debug "Executing step $step_id: $command"

    # Check dependencies first
    if ! check_dependencies "$step"; then
        log "❌ Step $step_id dependencies not met"
        return 1
    fi

    # Safety check the command
    if ! safety_check "$command" "$AUTONOMOUS"; then
        log "❌ Step $step_id failed safety check"
        return 1
    fi

    # Execute the command safely
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would execute: $command"
        return 0
    else
        if execute_command_safely "$command" "$input_file" "$output_file"; then
            log_debug "✅ Step $step_id executed successfully"
            return 0
        else
            local exit_code=$?
            log "❌ Step $step_id failed with exit code $exit_code"
            return $exit_code
        fi
    fi
}

# Validate output with ostruct
validate_output() {
    local output_file="$1"
    local original_analysis="$2"

    log_section "Output Validation"
    log "Validating output: $(basename "$output_file")"

    if [[ ! -f "$output_file" ]]; then
        log "❌ Output file not found: $output_file"
        return 1
    fi

    # Validate with ostruct
    local temp_validation_file
    temp_validation_file=$(mktemp)

    if profile_execution "validation" retry_ostruct ostruct run prompts/validate.j2 schemas/validation.json \
        --fca output_file "$output_file" \
        -V "original_analysis=$original_analysis" \
        --model "${MODEL_VALIDATION:-gpt-4.1}" \
        --temperature 0.1 \
        --progress-level none \
        --output-file "$temp_validation_file"; then

        local validation
        validation=$(cat "$temp_validation_file")

        # Keep temp file for debugging if debug mode is enabled
        if [[ "$DEBUG" != "true" ]]; then
            rm -f "$temp_validation_file"
        else
            log_debug "Validation JSON saved to: $temp_validation_file"
        fi

        if [[ -n "$validation" ]]; then
            local overall_quality
            overall_quality=$(echo "$validation" | jq -r '.overall_quality')
            local success
            success=$(echo "$validation" | jq -r '.success')

            log "Overall quality score: $overall_quality/10"

            if [[ "$success" == "true" ]]; then
                log "✅ Output validation successful"
                return 0
            else
                log "⚠️  Output validation indicates issues"
                echo "$validation" | jq -r '.issues_found[] | "- \(.severity): \(.description)"'
                return 1
            fi
        else
            log "⚠️  Output validation failed - empty response"
            return 1
        fi
    else
        if [[ "$DEBUG" != "true" ]]; then
            rm -f "$temp_validation_file"
        else
            log_debug "Failed validation attempt saved to: $temp_validation_file"
        fi
        log "⚠️  Output validation failed"
        return 1
    fi
}

# Perform dry-run analysis without API calls
perform_dry_run_analysis() {
    local input_file="$1"
    local output_file="$2"

    log_section "Dry Run Analysis"

    # Basic file analysis
    local file_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file" 2>/dev/null || echo "0")
    local file_name=$(basename "$input_file")
    local file_ext="${file_name##*.}"
    local file_size_mb=$((file_size / 1024 / 1024))

    log "📄 File: $file_name"
    log "📏 Size: ${file_size_mb} MB ($file_size bytes)"
    log "🏷️  Type: $file_ext"

    # Detect file type and provide generic guidance
    local file_ext_lower=$(echo "$file_ext" | tr '[:upper:]' '[:lower:]')
    case "$file_ext_lower" in
        pdf)
            log "🔍 PDF Analysis:"
            if command -v pdfinfo >/dev/null 2>&1; then
                local page_count=$(pdfinfo "$input_file" 2>/dev/null | grep "Pages:" | awk '{print $2}' || echo "unknown")
                log "   📖 Pages: $page_count"
                if [[ "$page_count" != "unknown" && "$page_count" -gt 50 ]]; then
                    log "   ⚠️  Large document - may require chunking"
                fi
            fi
            log "🔧 Suggested approach: Text extraction followed by format conversion"
            ;;
        docx|doc)
            log "🔍 Word Document Analysis:"
            log "🔧 Suggested approach: Direct conversion or high-fidelity extraction"
            ;;
        pptx|ppt)
            log "🔍 PowerPoint Analysis:"
            log "🔧 Suggested approach: Slide-aware conversion preserving structure"
            ;;
        xlsx|xls)
            log "🔍 Excel Analysis:"
            log "🔧 Suggested approach: Table-preserving conversion"
            ;;
        html|htm)
            log "🔍 HTML Analysis:"
            log "🔧 Suggested approach: Structure-preserving conversion with validation"
            ;;
        *)
            log "🔍 Unknown file type: $file_ext"
            log "🔧 Suggested approach: Universal conversion based on content analysis"
            ;;
    esac

    log ""
    log "📋 Dry Run Summary:"
    log "ℹ️  Would analyze document structure with AI model: ${MODEL_ANALYSIS:-gpt-4o-mini}"
    log "ℹ️  Would create conversion plan with AI model: ${MODEL_PLANNING:-gpt-4o}"
    log "ℹ️  Would execute conversion steps using available tools"
    log "ℹ️  Would validate output with AI model: ${MODEL_VALIDATION:-gpt-4o-mini}"

    # Show available tools count
    local available_tools_count=0
    if [[ -d "$PROJECT_ROOT/tools" ]]; then
        while IFS= read -r -d '' tool_file; do
            local tool_name=$(basename "$tool_file" .md)
            local base_command="$tool_name"

            # Check for virtual tools
            if grep -q "is_virtual_tool: true" "$tool_file" 2>/dev/null; then
                base_command=$(grep "base_command:" "$tool_file" | head -1 | sed 's/.*base_command: *//' | tr -d '"' || echo "$tool_name")
            fi

            if command -v "$base_command" >/dev/null 2>&1; then
                ((available_tools_count++))
            fi
        done < <(find "$PROJECT_ROOT/tools" -name "*.md" -print0 2>/dev/null)
    fi

    log "🔧 Available conversion tools: $available_tools_count"

    # Estimate costs and time
    local estimated_tokens=1000
    if [[ "$file_size_mb" -gt 1 ]]; then
        estimated_tokens=$((file_size_mb * 500))
    fi

    local estimated_cost_cents=$((estimated_tokens / 100))
    log ""
    log "📊 Estimates:"
    log "⏱️  Time: 30-90 seconds (depending on file complexity)"
    local cost_display=$(printf "~\$0.%02d" $estimated_cost_cents)
    log "💰 Cost: $cost_display (${estimated_tokens} tokens estimated)"
    log "🎯 Output: $output_file"

    log ""
    log "✅ Dry run complete - no API calls made, no costs incurred"
}

# Main conversion function
convert_document() {
    local input_file="$1"
    local output_file="$2"

    log_section "Document Conversion"
    log "Converting: $(basename "$input_file") -> $(basename "$output_file")"

    # Validate input file
    if [[ ! -f "$input_file" ]]; then
        error_exit "Input file not found: $input_file"
    fi

    # Create output directory
    mkdir -p "$(dirname "$output_file")"

    # Handle dry-run mode early (no API calls)
    if [[ "$DRY_RUN" == "true" ]]; then
        perform_dry_run_analysis "$input_file" "$output_file"
        return 0
    fi

    # Step 1: Analyze document
    local analysis
    analysis=$(analyze_document "$input_file")

    if [[ "$ANALYZE_ONLY" == "true" ]]; then
        log "Analysis complete (analyze-only mode)"
        echo "$analysis" | jq .
        return 0
    fi

    # Step 2: Create conversion plan
    local plan
    plan=$(create_conversion_plan "$analysis" "$output_file")

    # Interactive plan approval
    if [[ "$INTERACTIVE_APPROVAL" == "true" ]]; then
        while true; do
            display_plan "$plan" "Conversion Plan"
            get_plan_approval "plan"
            local approval_result=$?

            case $approval_result in
                0) break ;;  # Approved, continue
                1) error_exit "Plan execution cancelled by user" ;;  # Rejected
                2) continue ;;  # Show again
            esac
        done
    fi

    # Step 3: Execute conversion
    if execute_conversion_plan "$plan" "$input_file" "$output_file"; then
        log "✅ Conversion completed successfully"

        # Step 4: Validate output
        if validate_output "$output_file" "$analysis"; then
            log "✅ Output validation passed"
            return 0
        else
            log "⚠️  Output validation failed, but conversion completed"
            return 0
        fi
    else
        error_exit "Conversion failed"
    fi
}

# Usage information
show_usage() {
    cat << EOF
Document Conversion System v$SCRIPT_VERSION

USAGE:
    $0 [OPTIONS] INPUT_FILE OUTPUT_FILE
    $0 [OPTIONS] --analyze-only INPUT_FILE
    $0 --check-tools

OPTIONS:
    --autonomous           Run without user prompts
    --analyze-only         Only analyze document, don't convert
    --dry-run             Show planned steps without executing
    --verbose             Enable verbose output
    --debug               Enable debug output
    --check-tools         Check availability of conversion tools
    --allow-external-tools Allow using external validation services (default: false)
    --interactive         Show plans for user approval before execution (default: false)
    -h, --help            Show this help message

EXAMPLES:
    # Basic conversion
    $0 document.pdf document.md

    # Autonomous mode
    $0 --autonomous presentation.pptx slides.md

    # Analysis only
    $0 --analyze-only complex_report.docx

    # Dry run to see planned steps
    $0 --dry-run spreadsheet.xlsx data.md

ENVIRONMENT VARIABLES:
    MODEL_ANALYSIS     Model for document analysis (default: gpt-4o-mini)
    MODEL_PLANNING     Model for conversion planning (default: gpt-4o)
    MODEL_SAFETY       Model for safety checking (default: gpt-4o-mini)
    MODEL_VALIDATION   Model for output validation (default: gpt-4o-mini)
    DEBUG              Enable debug output (true/false)
    AUTONOMOUS         Run in autonomous mode (true/false)

For more information, see README.md
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --autonomous)
                AUTONOMOUS=true
                shift
                ;;
            --analyze-only)
                ANALYZE_ONLY=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --check-tools)
                CHECK_TOOLS=true
                shift
                ;;
            --allow-external-tools)
                ALLOW_EXTERNAL_TOOLS=true
                shift
                ;;
            --interactive)
                INTERACTIVE_APPROVAL=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                error_exit "Unknown option: $1"
                ;;
            *)
                if [[ -z "$INPUT_FILE" ]]; then
                    INPUT_FILE="$1"
                elif [[ -z "$OUTPUT_FILE" ]] && [[ "$ANALYZE_ONLY" != "true" ]]; then
                    OUTPUT_FILE="$1"
                else
                    error_exit "Too many arguments"
                fi
                shift
                ;;
        esac
    done
}

# Main function
main() {
    # Parse arguments
    parse_arguments "$@"

    # Override with environment variables
    AUTONOMOUS="${AUTONOMOUS:-false}"
    DEBUG="${DEBUG:-false}"
    VERBOSE="${VERBOSE:-false}"

    # Initialize logging
    log_section "Document Conversion System v$SCRIPT_VERSION"
    log "Started at $(date)"

    # Validate required tools
    validate_required_tools

    # Validate configuration
    validate_configuration

    # Handle special modes
    if [[ "$CHECK_TOOLS" == "true" ]]; then
        check_conversion_tools
        exit 0
    fi

    # Validate arguments
    if [[ -z "$INPUT_FILE" ]]; then
        show_usage
        error_exit "Input file required"
    fi

    if [[ "$ANALYZE_ONLY" != "true" ]] && [[ -z "$OUTPUT_FILE" ]]; then
        show_usage
        error_exit "Output file required (unless using --analyze-only)"
    fi

    # Convert paths to absolute
    INPUT_FILE=$(realpath "$INPUT_FILE")
    if [[ -n "$OUTPUT_FILE" ]]; then
        # Create absolute path for output file (may not exist yet)
        if [[ "$OUTPUT_FILE" = /* ]]; then
            # Already absolute
            OUTPUT_FILE="$OUTPUT_FILE"
        else
            # Make relative path absolute
            OUTPUT_FILE="$(pwd)/$OUTPUT_FILE"
        fi
    fi

    # Convert document
    if convert_document "$INPUT_FILE" "$OUTPUT_FILE"; then
        log "✅ Conversion completed successfully"
        exit 0
    else
        error_exit "Conversion failed"
    fi
}

# Run main function with all arguments
main "$@"
