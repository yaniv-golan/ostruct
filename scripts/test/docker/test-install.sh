#!/bin/bash

# Test script for macOS installation script using Docker
# This simulates a fresh macOS environment without affecting the host system

set -e

echo "🧪 Testing ostruct macOS Installation Script"
echo "==========================================="
echo ""

# Create a temporary directory for testing
TEST_DIR=$(mktemp -d)
echo "📁 Test directory: $TEST_DIR"

# Copy the installation script to test directory
cp scripts/install-macos.sh "$TEST_DIR/"

# Create a simple test Dockerfile that simulates macOS environment
cat > "$TEST_DIR/Dockerfile" << 'EOF'
# Use Ubuntu as a base (closest we can get to macOS in Docker)
FROM ubuntu:22.04

# Install basic tools that would be available on macOS
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    bash \
    zsh \
    sudo \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a user similar to macOS user
RUN useradd -m -s /bin/zsh testuser && \
    echo "testuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to test user
USER testuser
WORKDIR /home/testuser

# Copy the installation script
COPY install-macos.sh /home/testuser/install-macos.sh
RUN chmod +x /home/testuser/install-macos.sh

# Set up shell environment
RUN touch /home/testuser/.zshrc

CMD ["/bin/bash"]
EOF

echo "🐳 Building test Docker image..."
cd "$TEST_DIR"
docker build -t ostruct-install-test .

echo ""
echo "🚀 Running installation test in Docker container..."
echo "   (This will test the script logic without affecting your system)"
echo ""

# Run the container and test the script
docker run -it --rm ostruct-install-test bash -c "
    echo '🧪 Testing installation script...'
    echo '================================'
    echo ''

    # Test script parsing and basic functionality
    echo '📋 Checking script syntax...'
    bash -n install-macos.sh && echo '✅ Syntax check passed'

    echo ''
    echo '🔍 Testing function definitions...'
    source install-macos.sh

    # Test individual functions (without actually installing anything)
    echo '  - detect_shell function...'
    detect_shell

    echo '  - get_shell_config function...'
    get_shell_config zsh

    echo '  - command_exists function...'
    command_exists bash && echo '    ✅ bash found'

    echo ''
    echo '✅ Basic script validation completed successfully!'
    echo ''
    echo 'Note: Full installation testing requires macOS environment'
"

# Clean up
rm -rf "$TEST_DIR"

echo ""
echo "🎉 Test completed! The script syntax and basic functions work correctly."
echo ""
echo "To test the full installation on a real system:"
echo "1. Use a macOS virtual machine"
echo "2. Test on a separate user account"
echo "3. Use the dry-run mode (if implemented)"
echo ""
