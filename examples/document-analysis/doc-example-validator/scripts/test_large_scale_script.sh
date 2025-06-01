#!/bin/bash

# test_large_scale_script.sh - Quick validation that large_scale_example.sh works

set -e

echo "🧪 Quick validation of large_scale_example.sh..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

tests_passed=0
total_tests=3

# Test 1: Script syntax check
echo -e "${BLUE}🔍 Checking script syntax...${NC}"
if bash -n scripts/large_scale_example.sh; then
    echo -e "${GREEN}✅ Script syntax valid${NC}"
    ((tests_passed++))
else
    echo -e "${RED}❌ Script syntax errors found${NC}"
fi
echo ""

# Test 2: Required files exist
echo -e "${BLUE}📂 Checking required files...${NC}"
required_files=(
    "prompts/extract_examples.j2"
    "schemas/example_task_list.schema.json"
    "test_data/sample_project/README.md"
    "test_data/sample_project/docs/api_reference.rst"
    "test_data/sample_project/docs/troubleshooting.txt"
)

all_exist=true
for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  ✅ $file"
    else
        echo -e "  ${RED}❌ $file${NC}"
        all_exist=false
    fi
done

if $all_exist; then
    echo -e "${GREEN}✅ All required files present${NC}"
    ((tests_passed++))
else
    echo -e "${RED}❌ Missing required files${NC}"
fi
echo ""

# Test 3: ostruct command availability
echo -e "${BLUE}🔧 Checking ostruct availability...${NC}"
if command -v ostruct &> /dev/null; then
    echo -e "${GREEN}✅ ostruct command available${NC}"
    ((tests_passed++))
else
    echo -e "${RED}❌ ostruct command not found${NC}"
    echo "Install with: pip install ostruct"
fi
echo ""

# Summary
echo -e "${BLUE}📊 Validation Results: $tests_passed/$total_tests tests passed${NC}"
echo ""

if [[ $tests_passed -eq $total_tests ]]; then
    echo -e "${GREEN}🎉 large_scale_example.sh is ready to use!${NC}"
    echo ""
    echo "Usage: ./scripts/large_scale_example.sh"
    exit 0
else
    echo -e "${RED}❌ Please fix the issues above before running the example${NC}"
    exit 1
fi
