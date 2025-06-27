#!/bin/bash
# scripts/docker/test-docker-environments.sh
# Test ostruct installation across Docker environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Docker Environment Testing for ostruct ===${NC}"
echo ""

# Check if dist directory exists and has wheel files
if [ ! -d "dist" ] || [ -z "$(ls -A dist/*.whl 2>/dev/null)" ]; then
    echo -e "${RED}❌ Error: No wheel files found in dist/ directory${NC}"
    echo "Please build the package first with: poetry build"
    exit 1
fi

echo -e "${YELLOW}📦 Found wheel files:${NC}"
ls -la dist/*.whl
echo ""

# Test environments
ENVIRONMENTS=(
    "ubuntu:scripts/docker/test-ubuntu.dockerfile"
    "alpine:scripts/docker/test-alpine.dockerfile"
)

RESULTS=()

for env in "${ENVIRONMENTS[@]}"; do
    IFS=':' read -r env_name dockerfile <<< "$env"

    echo -e "${BLUE}🐳 Testing $env_name environment...${NC}"

    # Build Docker image
    echo "Building Docker image..."
    if docker build -f "$dockerfile" -t "ostruct-test-$env_name" . > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Build successful${NC}"
    else
        echo -e "${RED}❌ Build failed${NC}"
        RESULTS+=("$env_name:BUILD_FAILED")
        continue
    fi

    # Run Docker container
    echo "Running installation test..."
    if docker run --rm "ostruct-test-$env_name" > /tmp/ostruct-test-$env_name.log 2>&1; then
        echo -e "${GREEN}✅ Installation test passed${NC}"
        RESULTS+=("$env_name:PASSED")

        # Show test output
        echo -e "${YELLOW}Test output:${NC}"
        cat /tmp/ostruct-test-$env_name.log | sed 's/^/  /'
    else
        echo -e "${RED}❌ Installation test failed${NC}"
        RESULTS+=("$env_name:FAILED")

        # Show error output
        echo -e "${RED}Error output:${NC}"
        cat /tmp/ostruct-test-$env_name.log | sed 's/^/  /'
    fi

    echo ""
done

# Summary
echo -e "${BLUE}=== Test Results Summary ===${NC}"
echo ""

PASSED=0
FAILED=0
BUILD_FAILED=0

for result in "${RESULTS[@]}"; do
    IFS=':' read -r env_name status <<< "$result"
    case $status in
        "PASSED")
            echo -e "${GREEN}✅ $env_name: PASSED${NC}"
            ((PASSED++))
            ;;
        "FAILED")
            echo -e "${RED}❌ $env_name: FAILED${NC}"
            ((FAILED++))
            ;;
        "BUILD_FAILED")
            echo -e "${RED}🔥 $env_name: BUILD FAILED${NC}"
            ((BUILD_FAILED++))
            ;;
    esac
done

echo ""
echo -e "${BLUE}Total: $((PASSED + FAILED + BUILD_FAILED)) environments tested${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${RED}Build Failed: $BUILD_FAILED${NC}"

# Clean up test images
echo ""
echo -e "${YELLOW}🧹 Cleaning up test images...${NC}"
for env in "${ENVIRONMENTS[@]}"; do
    IFS=':' read -r env_name dockerfile <<< "$env"
    docker rmi "ostruct-test-$env_name" > /dev/null 2>&1 || true
done

# Clean up log files
rm -f /tmp/ostruct-test-*.log

# Exit with appropriate code
if [ $FAILED -gt 0 ] || [ $BUILD_FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Some tests failed. Please review the output above.${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}✅ All Docker environment tests passed!${NC}"
    exit 0
fi
