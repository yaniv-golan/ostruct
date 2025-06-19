#!/bin/bash

# Iterative Fact Extraction Script
# Extracts facts from documents using ostruct with iterative refinement

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
MAX_ITERATIONS=5
ESTIMATE_ONLY=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 <input_folder> [output_name] [options]

Extract facts from documents using iterative refinement.

Arguments:
  input_folder    Directory containing documents to process
  output_name     Optional output name (default: <folder_name>_facts.json)

Options:
  --estimate      Show cost estimates only (dry run)
  --max-iter N    Maximum iterations (default: $MAX_ITERATIONS)
  --help          Show this help message

Examples:
  $0 ./documents
  $0 ./reports company_analysis
  $0 ./pdfs --estimate
  $0 ./docs --max-iter 3

The script creates an intermediate directory with detailed processing files
and generates a comprehensive README.md explaining the pipeline results.
EOF
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"

    # Check for required commands
    local missing_deps=()

    if ! command -v ostruct &> /dev/null; then
        missing_deps+=("ostruct")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo -e "${RED}Error: Missing required dependencies: ${missing_deps[*]}${NC}"
        echo "Please install the missing dependencies and try again."
        return 1
    fi

    # Check for OpenAI API key
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        echo -e "${RED}Error: OPENAI_API_KEY environment variable is not set${NC}"
        echo "Please set your OpenAI API key and try again."
        return 1
    fi

    echo -e "${GREEN}✓ All prerequisites satisfied${NC}"
}

# Function to estimate costs
estimate_costs() {
    echo -e "${BLUE}Estimating costs for fact extraction pipeline...${NC}"
    echo

    # Create temporary sample data for cost estimation in current directory
    local temp_dir="temp_cost_estimation"
    mkdir -p "$temp_dir"
    local sample_conversion='{"converted_text":{"content_file":"sample_content.txt","metadata":{"source_file":"sample.pdf","conversion_method":"pymupdf","page_count":5,"content_length":15000,"document_type":"business","extraction_quality":"complete"}}}'
    local sample_facts='{"extracted_facts":[{"id":"fact_001","text":"Sample fact for estimation","source":"sample.pdf","confidence":0.9,"category":"organization","context":"Sample context","extraction_method":"semantic_analysis"}],"extraction_metadata":{"total_documents":1,"extraction_timestamp":"2024-01-15T10:30:00Z","model_used":"gpt-4"}}'
    local sample_assessment='{"coverage_analysis":{"missing_facts":["Sample missing fact"],"incorrect_facts":["Sample incorrect fact"],"recommendations":["Add financial data","Include technical specifications"]}}'
    local sample_content="This is sample document content for cost estimation purposes. It contains multiple paragraphs of text that would typically be found in business documents, including company information, financial data, and operational details. The content is structured to provide a realistic estimate of token usage for the fact extraction pipeline."

    # Create sample files
    echo "$sample_conversion" > "$temp_dir/conversion.json"
    echo "$sample_facts" > "$temp_dir/facts.json"
    echo "$sample_assessment" > "$temp_dir/assessment.json"
    echo "$sample_content" > "$temp_dir/sample_content.txt"

    cd "$PROJECT_ROOT"

    # Estimate each step
    echo "1. Document Conversion (Code Interpreter):"
    # Create a sample file for estimation
    echo "Sample document content for cost estimation" > "$temp_dir/sample.txt"
    ostruct run --dry-run \
        -fc "$temp_dir/sample.txt" \
        prompts/convert.j2 \
        schemas/convert_schema.json 2>&1 | grep -E "Estimated cost:" || echo "   Cost estimation not available"
    echo

    echo "2. Fact Extraction (File Search):"
    ostruct run --dry-run \
        -ds "$temp_dir" \
        prompts/extract.j2 \
        schemas/extract_schema.json 2>&1 | grep -E "Estimated cost:" || echo "   Cost estimation not available"
    echo

    echo "3. Coverage Analysis:"
    ostruct run --dry-run \
        -ds "$temp_dir" \
        prompts/assess.j2 \
        schemas/assessment_schema.json 2>&1 | grep -E "Estimated cost:" || echo "   Cost estimation not available"
    echo

    echo "4. Patch Generation:"
    ostruct run --dry-run \
        -ds "$temp_dir" \
        prompts/patch.j2 \
        schemas/patch_schema.json 2>&1 | grep -E "Estimated cost:" || echo "   Cost estimation not available"
    echo

    # Cleanup
    rm -rf "$temp_dir"

    echo -e "${YELLOW}Note: Actual costs may vary based on document size and iteration count.${NC}"
    echo -e "${YELLOW}The pipeline typically requires 2-5 iterations for convergence.${NC}"
}

# Function to create README for intermediate directory
create_intermediate_readme() {
    local intermediate_dir="$1"
    local input_folder="$2"
    local output_name="$3"

    cat > "${intermediate_dir}/README.md" << EOF
# Iterative Fact Extraction Pipeline Results

This directory contains the intermediate files and results from the iterative fact extraction pipeline.

## Pipeline Overview

The fact extraction pipeline processes documents through four main stages:

1. **Document Conversion** - Convert input documents to structured text using Code Interpreter
2. **Fact Extraction** - Extract factual statements using File Search and semantic analysis
3. **Fact Review** - Identify missing facts, incorrect facts, and needed corrections
4. **Iterative Refinement** - Generate and apply JSON Patch operations to improve fact accuracy

## File Structure

### Input and Output
- **Input Source**: \`$(basename "$input_folder")\`
- **Final Output**: \`$output_name\`

### Pipeline Stage Files
- [\`01_conversion.json\`](01_conversion.json) - Document conversion results ([schema](../schemas/convert_schema.json))
- [\`extracted_full_text.txt\`](extracted_full_text.txt) - Complete extracted document text
- [\`02_extraction_iter_1.json\`](02_extraction_iter_1.json) - Initial fact extraction ([schema](../schemas/extract_schema.json))

### Iteration Files
Each iteration produces three files:
- \`03_assessment_iter_N.json\` - Coverage analysis results ([schema](../schemas/assessment_schema.json))
- \`04_patches_iter_N.json\` - JSON Patch operations for improvements ([schema](../schemas/patch_schema.json))
- \`02_extraction_iter_N+1.json\` - Updated facts after applying patches

### Support Files
- \`converted_content.txt\` - Temporary file for File Search operations
- \`README.md\` - This documentation file

## Iteration Process

The pipeline iteratively refines fact extraction through these steps:

1. **Fact Review** - Identify missing facts, incorrect facts, and needed corrections
2. **Patch Generation** - Create RFC-6902 JSON Patch operations to address issues
3. **Fact Updates** - Apply patches to add, modify, or remove facts
4. **Repeat** - Continue until no more improvements are needed

## Convergence Criteria

The pipeline stops when any of these conditions are met:

- **No More Patches**: LLM determines no additional facts need to be added, corrected, or removed
- **Maximum Iterations**: Reached $MAX_ITERATIONS iterations to prevent infinite loops

The pipeline focuses on objective patch generation rather than subjective coverage scoring.

## File Usage Guidelines

- **Read-Only**: All files in this directory are generated outputs
- **Schemas**: Linked schema files define the structure and validation rules
- **Cleanup**: This directory can be safely deleted after reviewing results
- **Debugging**: Use iteration files to understand pipeline decision-making

---
*Generated by extract_facts.sh on $(date)*
*Input: $input_folder → Output: $output_name*
*Max iterations: $MAX_ITERATIONS*
EOF
}

# Function to run the extraction pipeline
run_extraction_pipeline() {
    local input_folder="$1"
    local output_name="$2"

    # Create intermediate directory (sanitize name for valid variable names)
    local base_name=$(basename "$output_name" .json)
    local intermediate_dir="${base_name}_intermediate"
    mkdir -p "$intermediate_dir"

    echo -e "${BLUE}Starting iterative fact extraction pipeline...${NC}"
    echo "Input folder: $input_folder"
    echo "Output file: $output_name"
    echo "Intermediate files: $intermediate_dir/"
    echo "Max iterations: $MAX_ITERATIONS"
    echo

    # Create intermediate README
    create_intermediate_readme "$intermediate_dir" "$input_folder" "$output_name"

    cd "$PROJECT_ROOT"

    # Step 1: Convert documents using Code Interpreter
    echo -e "${BLUE}Step 1: Converting documents using Code Interpreter...${NC}"

    # Process each document individually
    local converted_files=()
    local conversion_count=0

    for file in "$input_folder"/*; do
        if [[ -f "$file" ]]; then
            local filename=$(basename "$file")
            local name_without_ext="${filename%.*}"
            local converted_file="${intermediate_dir}/converted_${name_without_ext}.json"

            echo "Converting: $filename"

            if ostruct run \
                --file ci:source_document "$file" \
                prompts/convert.j2 \
                schemas/convert_schema.json \
                --output-file "$converted_file"; then
                echo -e "${GREEN}✓ Converted: $filename${NC}"
                converted_files+=("$converted_file")
                ((conversion_count++))
            else
                echo -e "${YELLOW}⚠ Failed to convert: $filename (skipping)${NC}"
            fi
        fi
    done

    if [[ $conversion_count -eq 0 ]]; then
        echo -e "${RED}Error: No documents were successfully converted${NC}"
        return 1
    fi

    # Combine all converted files into a single output for the pipeline
    local conversion_output="${intermediate_dir}/01_conversion.json"
    if [[ ${#converted_files[@]} -eq 1 ]]; then
        # Single file - just copy it
        cp "${converted_files[0]}" "$conversion_output"
    else
        # Multiple files - use the first one as primary (the pipeline expects single conversion output)
        cp "${converted_files[0]}" "$conversion_output"
        echo -e "${YELLOW}Note: Using first converted file as primary. All files will be available for extraction.${NC}"
    fi

    echo -e "${GREEN}✓ Document conversion completed${NC}"

    # Create corpus directory for File Search (use simple name to avoid path issues)
    local corpus_dir="$(pwd)/corpus_temp"
    mkdir -p "$corpus_dir"

    # Copy all converted files to corpus directory
    for converted_file in "${converted_files[@]}"; do
        cp "$converted_file" "$corpus_dir/"
    done

    # Step 2: Extract facts using File Search
    echo -e "${BLUE}Step 2: Extracting facts using File Search...${NC}"

    local extraction_output="${intermediate_dir}/02_extraction_iter_1.json"

    ostruct run \
        --dir fs:text_files "$corpus_dir" \
        prompts/extract.j2 \
        schemas/extract_schema.json \
        --output-file "$extraction_output" || {
        echo -e "${RED}Error: Fact extraction failed${NC}"
        return 1
    }

    echo -e "${GREEN}✓ Initial fact extraction completed${NC}"

    # Iterative refinement
    local iteration=1
    local current_facts="$extraction_output"

    while [[ $iteration -le $MAX_ITERATIONS ]]; do
        echo
        echo -e "${YELLOW}=== Iteration $iteration ===${NC}"

        # Step 3: Identify missing and incorrect facts
        echo -e "${BLUE}Step 3: Identifying missing and incorrect facts (iteration $iteration)...${NC}"

        local assessment_output="${intermediate_dir}/03_assessment_iter_${iteration}.json"

        # Copy current facts to corpus directory so it gets parsed as JSON
        cp "$current_facts" "$corpus_dir/current_facts.json"

        ostruct run \
            --dir fs:source_documents "$corpus_dir" \
            prompts/assess.j2 \
            schemas/assessment_schema.json \
            --output-file "$assessment_output" || {
            echo -e "${RED}Error: Coverage assessment failed${NC}"
            return 1
        }


        # Check if there are any missing or incorrect facts identified
        local missing_count=$(jq '.coverage_analysis.missing_facts | length' "$assessment_output" 2>/dev/null || echo "0")
        local incorrect_count=$(jq '.coverage_analysis.incorrect_facts | length' "$assessment_output" 2>/dev/null || echo "0")

        echo "Missing facts identified: $missing_count"
        echo "Incorrect facts identified: $incorrect_count"

        # If no issues identified, we're done - skip patch generation
        if [[ "$missing_count" == "0" && "$incorrect_count" == "0" ]]; then
            echo -e "${GREEN}✓ Convergence achieved - no missing or incorrect facts identified${NC}"
            break
        fi

        # Step 4: Generate patches
        echo -e "${BLUE}Step 4: Generating improvement patches (iteration $iteration)...${NC}"

        local patch_output="${intermediate_dir}/04_patches_iter_${iteration}.json"

        # Copy assessment output to corpus directory so it gets parsed as JSON
        cp "$assessment_output" "$corpus_dir/coverage_analysis.json"

        ostruct run \
            --dir fs:analysis_corpus "$corpus_dir" \
            prompts/patch.j2 \
            schemas/patch_schema.json \
            --output-file "$patch_output" || {
            echo -e "${RED}Error: Patch generation failed${NC}"
            return 1
        }

        # Check if patches array exists and has operations
        local patch_count=$(jq '.patch | length' "$patch_output" 2>/dev/null || echo "0")

        if [[ "$patch_count" == "0" ]]; then
            echo -e "${GREEN}✓ Convergence achieved - no more patches needed${NC}"
            break
        fi

        # Apply patches to create new facts file
        echo "Applying $patch_count patch operations..."

        # Read current facts content
        local current_facts_content=$(cat "$current_facts")

        # Apply each patch operation (avoid subshell to preserve variable changes)
        while IFS= read -r patch; do
            local op=$(echo "$patch" | jq -r '.op')
            local path=$(echo "$patch" | jq -r '.path')
            local value=$(echo "$patch" | jq -r '.value // empty')

            case "$op" in
                "add")
                    if [[ -n "$value" ]]; then
                        # Parse the JSON string value for add operations
                        local parsed_value=$(echo "$value" | jq '.')
                        current_facts_content=$(echo "$current_facts_content" | jq --argjson val "$parsed_value" ". as \$root | setpath([\"extracted_facts\"]; (\$root.extracted_facts + [\$val]))")
                    fi
                    ;;
                "replace")
                    if [[ -n "$value" ]]; then
                        # Handle replace operations for specific fields
                        if [[ "$path" =~ /extracted_facts/([0-9]+)/(.+) ]]; then
                            local index="${BASH_REMATCH[1]}"
                            local field="${BASH_REMATCH[2]}"
                            current_facts_content=$(echo "$current_facts_content" | jq --arg val "$value" ".extracted_facts[$index].$field = \$val")
                        fi
                    fi
                    ;;
                "remove")
                    # Handle remove operations
                    if [[ "$path" =~ /extracted_facts/([0-9]+)$ ]]; then
                        local index="${BASH_REMATCH[1]}"
                        current_facts_content=$(echo "$current_facts_content" | jq "del(.extracted_facts[$index])")
                    fi
                    ;;
            esac
        done < <(jq -c '.patch[]' "$patch_output")

        # Save updated facts for next iteration
        local next_iteration=$((iteration + 1))
        current_facts="${intermediate_dir}/02_extraction_iter_${next_iteration}.json"
        echo "$current_facts_content" > "$current_facts"

        echo -e "${GREEN}✓ Applied patches, created iteration $next_iteration facts${NC}"

        iteration=$next_iteration
    done

    # Copy final facts to output location
    cp "$current_facts" "$output_name"

    echo
    echo -e "${GREEN}=== Pipeline Completed ===${NC}"
    echo "Final facts saved to: $output_name"
    echo "Intermediate files in: $intermediate_dir/"
    echo "Total iterations: $((iteration - 1))"

    # Show final summary
    local final_fact_count=$(jq '.extracted_facts | length' "$output_name" 2>/dev/null || echo "0")
    echo "Final fact count: $final_fact_count"



    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Review the extracted facts in: $output_name"
    echo "2. Examine the pipeline process in: $intermediate_dir/"
    echo "3. Clean up intermediate files when no longer needed"
}

# Parse command line arguments
if [[ $# -eq 0 ]]; then
    show_usage
    exit 1
fi

INPUT_FOLDER=""
OUTPUT_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_usage
            exit 0
            ;;
        --estimate)
            ESTIMATE_ONLY=true
            shift
            ;;
        --max-iter)
            MAX_ITERATIONS="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$INPUT_FOLDER" ]]; then
                INPUT_FOLDER="$1"
            elif [[ -z "$OUTPUT_NAME" ]]; then
                OUTPUT_NAME="$1"
            else
                echo -e "${RED}Error: Too many arguments${NC}"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate input folder
if [[ -z "$INPUT_FOLDER" ]]; then
    echo -e "${RED}Error: Input folder is required${NC}"
    show_usage
    exit 1
fi

if [[ ! -d "$INPUT_FOLDER" ]]; then
    echo -e "${RED}Error: Input folder '$INPUT_FOLDER' does not exist${NC}"
    exit 1
fi

# Set default output name if not provided
if [[ -z "$OUTPUT_NAME" ]]; then
    folder_name=$(basename "$INPUT_FOLDER")
    OUTPUT_NAME="${folder_name}_facts.json"
fi

# Ensure output name ends with .json
if [[ "$OUTPUT_NAME" != *.json ]]; then
    OUTPUT_NAME="${OUTPUT_NAME}.json"
fi

# Check prerequisites
check_prerequisites

# Handle estimate mode
if [[ "$ESTIMATE_ONLY" == "true" ]]; then
    estimate_costs
    exit 0
fi

# Run the extraction pipeline
run_extraction_pipeline "$INPUT_FOLDER" "$OUTPUT_NAME"
