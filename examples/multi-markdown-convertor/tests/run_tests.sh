#!/bin/bash
# Test runner for convert.sh modules

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test file
run_test_file() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .sh)
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if bash "$test_file"; then
        echo -e "${GREEN}✅ $test_name PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ $test_name FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo
}

# Change to script directory
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "=== Convert.sh Test Suite ==="
echo "Starting test execution at $(date)"
echo

# Run unit tests
echo -e "${YELLOW}=== UNIT TESTS ===${NC}"
if [[ -d "unit" ]]; then
    for test in unit/test_*.sh; do
        if [[ -f "$test" ]]; then
            run_test_file "$test"
        fi
    done
else
    echo "No unit tests directory found"
fi

# Run integration tests
echo -e "${YELLOW}=== INTEGRATION TESTS ===${NC}"
if [[ -d "integration" ]]; then
    for test in integration/test_*.sh; do
        if [[ -f "$test" ]]; then
            run_test_file "$test"
        fi
    done
else
    echo "No integration tests directory found"
fi

# Summary
echo "=== TEST SUMMARY ==="
echo "Total tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 $FAILED_TESTS test(s) failed${NC}"
    exit 1
fi
