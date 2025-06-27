FROM ubuntu:22.04

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for testing
RUN useradd -m -s /bin/bash testuser
USER testuser
WORKDIR /home/testuser

# Copy wheel file to container
COPY dist/*.whl /tmp/

# Install ostruct from wheel
RUN pip3 install --user /tmp/*.whl

# Add user's local bin to PATH
ENV PATH="/home/testuser/.local/bin:${PATH}"

# Test basic functionality
RUN ostruct --help
RUN ostruct --version

# Test dry-run functionality
RUN echo '{"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}' > test_schema.json
RUN echo 'Test: {{ "hello from Ubuntu" }}' > test_template.j2
RUN ostruct run test_template.j2 test_schema.json --dry-run

# Create verification script
RUN echo '#!/bin/bash' > verify.sh && \
    echo 'echo "=== Ubuntu 22.04 Installation Test ==="' >> verify.sh && \
    echo 'echo "Python version: $(python3 --version)"' >> verify.sh && \
    echo 'echo "Pip version: $(pip3 --version)"' >> verify.sh && \
    echo 'echo "Ostruct version: $(ostruct --version)"' >> verify.sh && \
    echo 'echo "Ostruct help works: $(ostruct --help > /dev/null && echo OK || echo FAILED)"' >> verify.sh && \
    echo 'echo "Dry-run test: $(ostruct run test_template.j2 test_schema.json --dry-run > /dev/null && echo OK || echo FAILED)"' >> verify.sh && \
    echo 'echo "=== Test Complete ==="' >> verify.sh && \
    chmod +x verify.sh

CMD ["./verify.sh"]
