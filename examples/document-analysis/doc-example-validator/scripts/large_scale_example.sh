#!/bin/bash

# large_scale_example.sh - Demonstrates large-scale documentation analysis strategies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏢 Large-Scale Documentation Analysis Example${NC}"
echo ""

# Change to example directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$(dirname "$SCRIPT_DIR")"
cd "$EXAMPLE_DIR"

echo -e "${YELLOW}📁 Working directory: $(pwd)${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}✅ Checking prerequisites...${NC}"

if ! command -v ostruct &> /dev/null; then
    echo -e "${RED}❌ Error: ostruct command not found${NC}"
    echo "Please install ostruct first: pip install ostruct"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# Function to run analysis with timing and cost estimation
run_analysis() {
    local name="$1"
    local description="$2"
    local output_file="$3"
    shift 3
    local cmd="$@"

    echo -e "${CYAN}📊 Running: $name${NC}"
    echo -e "   Description: $description"
    echo -e "   Command: $cmd"
    echo ""

    # Run dry-run first for cost estimation
    echo -e "${YELLOW}🧪 Dry-run for cost estimation...${NC}"
    local dry_run_cmd="${cmd} --dry-run"
    eval $dry_run_cmd
    echo ""

    # Ask user to proceed
    read -p "Proceed with actual analysis? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🚀 Running full analysis...${NC}"
        local start_time=$(date +%s)

        # Run actual command
        eval "$cmd"

        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        if [ -f "$output_file" ]; then
            local task_count=$(jq '.tasks | length' "$output_file" 2>/dev/null || echo "unknown")
            local examples_count=$(jq '.project_info.total_examples_found' "$output_file" 2>/dev/null || echo "unknown")

            echo -e "${GREEN}✅ Analysis completed in ${duration}s${NC}"
            echo -e "   Tasks generated: $task_count"
            echo -e "   Examples found: $examples_count"
            echo -e "   Output: $output_file"
        else
            echo -e "${RED}❌ Analysis failed or output file not created${NC}"
        fi
    else
        echo -e "${YELLOW}⏭️  Skipping actual analysis${NC}"
    fi
    echo ""
}

# Strategy 1: Progressive Analysis (Recommended for new projects)
echo -e "${BLUE}📈 Strategy 1: Progressive Analysis${NC}"
echo "Start with critical documentation, then expand to full analysis"
echo ""

# Phase 1: Critical files only
run_analysis \
    "Progressive Phase 1" \
    "Critical documentation files only" \
    "progressive_phase1.json" \
    "ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
     -fs test_data/sample_project/README.md \
     -fs test_data/sample_project/changelog.md \
     -V project_name=\"ProgressiveDemo\" \
     -V project_type=\"CLI\" \
     -V validation_level=\"critical_only\" \
     --output-file progressive_phase1.json \
     --model gpt-4o --temperature 0"

# Phase 2: Full analysis
run_analysis \
    "Progressive Phase 2" \
    "Complete documentation analysis" \
    "progressive_phase2.json" \
    "ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
     -ds test_data/sample_project/ \
     -V project_name=\"ProgressiveDemo\" \
     -V project_type=\"CLI\" \
     -V validation_level=\"comprehensive\" \
     --output-file progressive_phase2.json \
     --model gpt-4o --temperature 0"

# Strategy 2: Selective Directory Analysis
echo -e "${BLUE}🎯 Strategy 2: Selective Directory Analysis${NC}"
echo "Focus on specific documentation areas for targeted analysis"
echo ""

run_analysis \
    "Selective Analysis" \
    "User-facing documentation only" \
    "selective_analysis.json" \
    "ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
     -fs test_data/sample_project/README.md \
     -ds test_data/sample_project/docs/ \
     -V project_name=\"SelectiveDemo\" \
     -V project_type=\"CLI\" \
     -V focus_areas=\"user_guides,tutorials\" \
     --output-file selective_analysis.json \
     --model gpt-4o --temperature 0"

# Strategy 3: Format-Specific Analysis
echo -e "${BLUE}📝 Strategy 3: Format-Specific Analysis${NC}"
echo "Analyze different documentation formats separately"
echo ""

# Markdown files only
run_analysis \
    "Markdown Analysis" \
    "Markdown documentation files only" \
    "markdown_analysis.json" \
    "ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
     -fs test_data/sample_project/README.md \
     -fs test_data/sample_project/changelog.md \
     -fs test_data/sample_project/docs/installation.md \
     -fs test_data/sample_project/docs/configuration.md \
     -V project_name=\"MarkdownDemo\" \
     -V project_type=\"CLI\" \
     -V preferred_formats=\"markdown\" \
     --output-file markdown_analysis.json \
     --model gpt-4o --temperature 0"

# Strategy 4: Multi-Repository Simulation
echo -e "${BLUE}🏗️ Strategy 4: Multi-Repository Pattern${NC}"
echo "Simulate analysis of multiple related repositories"
echo ""

# Create temporary directories to simulate multiple repos
mkdir -p temp_repos/{frontend,backend,api}/docs

# Copy sample docs to simulate different repos
cp test_data/sample_project/README.md temp_repos/frontend/
cp test_data/sample_project/docs/installation.md temp_repos/frontend/docs/
cp test_data/sample_project/docs/api_reference.rst temp_repos/backend/docs/
cp test_data/sample_project/docs/configuration.md temp_repos/api/docs/

run_analysis \
    "Multi-Repository" \
    "Multiple repository documentation" \
    "multi_repo_analysis.json" \
    "ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
     -ds temp_repos/frontend/ \
     -ds temp_repos/backend/docs/ \
     -ds temp_repos/api/docs/ \
     -V project_name=\"MultiRepoDemo\" \
     -V project_type=\"Microservices\" \
     --output-file multi_repo_analysis.json \
     --model gpt-4o --temperature 0"

# Cleanup temporary directories
rm -rf temp_repos/

# Analysis Summary
echo -e "${BLUE}📊 Analysis Summary${NC}"
echo ""

if ls *.json 1> /dev/null 2>&1; then
    echo -e "${GREEN}Generated analysis files:${NC}"
    for file in *.json; do
        if [ -f "$file" ]; then
            task_count=$(jq '.tasks | length' "$file" 2>/dev/null || echo "?")
            examples_count=$(jq '.project_info.total_examples_found' "$file" 2>/dev/null || echo "?")
            echo -e "  • $file: $task_count tasks, $examples_count examples"
        fi
    done
    echo ""
fi

# Provide recommendations
echo -e "${BLUE}🎯 Recommendations for Large-Scale Projects${NC}"
echo ""
echo -e "${GREEN}For Small Projects (< 50 files):${NC}"
echo "  • Use full directory scan: -ds docs/"
echo "  • Single analysis run"
echo "  • Expected cost: \$0.50 - \$2.00"
echo ""
echo -e "${YELLOW}For Medium Projects (50-200 files):${NC}"
echo "  • Use progressive analysis strategy"
echo "  • Start with critical documentation"
echo "  • Use selective directory scanning"
echo "  • Expected cost: \$2.00 - \$8.00"
echo ""
echo -e "${CYAN}For Large Projects (200-1000 files):${NC}"
echo "  • Use multi-phase approach"
echo "  • Filter by documentation type"
echo "  • Process in batches"
echo "  • Expected cost: \$8.00 - \$25.00"
echo ""
echo -e "${RED}For Enterprise Projects (1000+ files):${NC}"
echo "  • Use repository-specific analysis"
echo "  • Implement automated filtering"
echo "  • Consider budget allocation per team/component"
echo "  • Expected cost: \$25.00+"
echo ""

# Performance optimization tips
echo -e "${BLUE}⚡ Performance Optimization Tips${NC}"
echo ""
echo "1. Use --dry-run first to estimate costs"
echo "2. Focus on user-facing documentation first"
echo "3. Filter out auto-generated docs (changelog, API docs)"
echo "4. Use format-specific processing for better results"
echo "5. Consider time-of-day for API rate limits"
echo "6. Process related repositories separately"
echo "7. Cache results for iterative improvements"
echo ""

# Cleanup option
read -p "Clean up generated analysis files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f *.json
    echo -e "${GREEN}✅ Analysis files cleaned up${NC}"
else
    echo -e "${YELLOW}📁 Analysis files preserved for review${NC}"
fi

echo -e "${GREEN}🎉 Large-scale documentation analysis examples completed!${NC}"
echo ""
echo -e "${BLUE}📚 Next Steps:${NC}"
echo "1. Choose the strategy that best fits your project size"
echo "2. Adjust validation_level based on thoroughness needs"
echo "3. Use cost estimates to plan documentation validation budgets"
echo "4. Set up automation for regular documentation validation"
echo "5. Integrate with CI/CD pipelines for continuous validation"
