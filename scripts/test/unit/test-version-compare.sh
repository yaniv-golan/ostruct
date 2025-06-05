#!/bin/bash

# Test script for version comparison function

# Extract just the version_compare function from the template
version_compare() {
    local v1="$1"
    local v2="$2"

    # Extract just the version numbers (remove any prefixes like "ostruct-cli ")
    v1=$(echo "$v1" | sed 's/.*\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/')
    v2=$(echo "$v2" | sed 's/.*\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/')

    # Use sort -V for version comparison
    if [[ "$(printf '%s\n' "$v1" "$v2" | sort -V | head -n1)" == "$v2" ]]; then
        return 0  # v1 >= v2
    else
        return 1  # v1 < v2
    fi
}

# Test cases
echo "Testing version comparison function..."
echo ""

# Test 1: Equal versions
if version_compare "0.8.4" "0.8.4"; then
    echo "✅ 0.8.4 >= 0.8.4: PASS"
else
    echo "❌ 0.8.4 >= 0.8.4: FAIL"
fi

# Test 2: Newer version
if version_compare "0.8.5" "0.8.4"; then
    echo "✅ 0.8.5 >= 0.8.4: PASS"
else
    echo "❌ 0.8.5 >= 0.8.4: FAIL"
fi

# Test 3: Older version (should fail)
if version_compare "0.8.3" "0.8.4"; then
    echo "❌ 0.8.3 >= 0.8.4: FAIL (expected)"
else
    echo "✅ 0.8.3 >= 0.8.4: PASS (correctly failed)"
fi

# Test 4: With prefix
if version_compare "ostruct-cli 0.8.4" "0.8.4"; then
    echo "✅ 'ostruct-cli 0.8.4' >= 0.8.4: PASS"
else
    echo "❌ 'ostruct-cli 0.8.4' >= 0.8.4: FAIL"
fi

# Test 5: Major version difference
if version_compare "1.0.0" "0.8.4"; then
    echo "✅ 1.0.0 >= 0.8.4: PASS"
else
    echo "❌ 1.0.0 >= 0.8.4: FAIL"
fi

echo ""
echo "Version comparison tests complete!"
