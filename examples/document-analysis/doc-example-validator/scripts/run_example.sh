#!/bin/bash

# run_example.sh - Full execution script for documentation example validator

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Documentation Example Validator - Running Full Example${NC}"
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

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: jq not found - JSON validation will be limited${NC}"
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# Run dry-run first
echo -e "${BLUE}🧪 Running dry-run validation...${NC}"
ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds test_data/sample_project/ \
  -V project_name="AwesomeCLI" \
  -V project_type="CLI" \
  -V validation_level="comprehensive" \
  --dry-run

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dry-run validation passed${NC}"
else
    echo -e "${RED}❌ Dry-run validation failed${NC}"
    exit 1
fi
echo ""

# Run actual analysis
echo -e "${BLUE}🚀 Running full documentation analysis...${NC}"
OUTPUT_FILE="validation_tasks_$(date +%Y%m%d_%H%M%S).json"

ostruct run prompts/extract_examples.j2 schemas/example_task_list.schema.json \
  -ds test_data/sample_project/ \
  -V project_name="AwesomeCLI" \
  -V project_type="CLI" \
  -V validation_level="comprehensive" \
  --output-file "$OUTPUT_FILE" \
  --model gpt-4o \
  --temperature 0

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Analysis completed successfully${NC}"
    echo -e "${BLUE}📄 Output saved to: $OUTPUT_FILE${NC}"
else
    echo -e "${RED}❌ Analysis failed${NC}"
    exit 1
fi
echo ""

# Validate output format
echo -e "${BLUE}🔍 Validating output format...${NC}"

if [ -f "$OUTPUT_FILE" ]; then
    # Check if it's valid JSON
    if jq empty "$OUTPUT_FILE" 2>/dev/null; then
        echo -e "${GREEN}✅ Valid JSON format${NC}"

        # Extract basic statistics
        PROJECT_NAME=$(jq -r '.project_info.name' "$OUTPUT_FILE")
        TOTAL_EXAMPLES=$(jq -r '.project_info.total_examples_found' "$OUTPUT_FILE")
        TOTAL_TASKS=$(jq -r '.tasks | length' "$OUTPUT_FILE")

        echo -e "${BLUE}📊 Analysis Results:${NC}"
        echo -e "  • Project: $PROJECT_NAME"
        echo -e "  • Examples found: $TOTAL_EXAMPLES"
        echo -e "  • Validation tasks: $TOTAL_TASKS"

        # Show task breakdown by priority
        CRITICAL_TASKS=$(jq -r '.tasks | map(select(.priority == "CRITICAL")) | length' "$OUTPUT_FILE")
        HIGH_TASKS=$(jq -r '.tasks | map(select(.priority == "HIGH")) | length' "$OUTPUT_FILE")
        MEDIUM_TASKS=$(jq -r '.tasks | map(select(.priority == "MEDIUM")) | length' "$OUTPUT_FILE")
        LOW_TASKS=$(jq -r '.tasks | map(select(.priority == "LOW")) | length' "$OUTPUT_FILE")

        echo -e "  • Critical tasks: $CRITICAL_TASKS"
        echo -e "  • High priority: $HIGH_TASKS"
        echo -e "  • Medium priority: $MEDIUM_TASKS"
        echo -e "  • Low priority: $LOW_TASKS"

    else
        echo -e "${RED}❌ Invalid JSON format${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Output file not found${NC}"
    exit 1
fi
echo ""

# Compare with expected output (basic structure check)
echo -e "${BLUE}🔍 Comparing with expected structure...${NC}"

if [ -f "test_data/sample_project/expected_output.json" ]; then
    EXPECTED_TASKS=$(jq -r '.tasks | length' "test_data/sample_project/expected_output.json")
    ACTUAL_TASKS=$(jq -r '.tasks | length' "$OUTPUT_FILE")

    echo -e "  • Expected tasks: $EXPECTED_TASKS"
    echo -e "  • Generated tasks: $ACTUAL_TASKS"

    if [ "$ACTUAL_TASKS" -ge 5 ]; then
        echo -e "${GREEN}✅ Task generation looks reasonable${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: Fewer tasks generated than expected${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Expected output file not found - skipping comparison${NC}"
fi
echo ""

# Show sample tasks
echo -e "${BLUE}📋 Sample tasks generated:${NC}"
jq -r '.tasks[0:3] | .[] | "  • \(.id): \(.title) (\(.priority))"' "$OUTPUT_FILE"
echo ""

# Provide next steps
echo -e "${GREEN}🎉 Documentation analysis complete!${NC}"
echo ""
echo -e "${BLUE}📝 Next steps:${NC}"
echo -e "  1. Review the generated task list: $OUTPUT_FILE"
echo -e "  2. Execute tasks with an AI agent:"
echo -e "     • Open the JSON file in Cursor"
echo -e "     • Ask: 'Execute all PENDING tasks in this validation list'"
echo -e "  3. Update task status as you complete them:"
echo -e "     • Use: jq '.tasks[0].status = \"COMPLETED\"' file.json"
echo -e "  4. Validate the output format:"
echo -e "     • Run: python scripts/validate_output.py $OUTPUT_FILE"
echo ""

echo -e "${GREEN}✅ Example execution completed successfully!${NC}"
