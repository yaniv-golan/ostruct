FROM python:3.11-alpine

# Install system dependencies including build tools for native packages
RUN apk add --no-cache \
    bash \
    curl \
    git \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    make \
    rust \
    cargo \
    g++ \
    cmake \
    protobuf-dev \
    linux-headers \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    build-base \
    openssl-dev
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$HOME/.local/bin:$PATH"

# Create a non-root user for testing
RUN adduser -D -s /bin/bash testuser
USER testuser
WORKDIR /home/testuser

# Copy pre-built wheel (built outside Docker to avoid Git dependency issues)
COPY --chown=testuser:testuser dist/*.whl ./

# Install ostruct from the wheel
RUN pip install --user *.whl

# Add user's local bin to PATH
ENV PATH="/home/testuser/.local/bin:${PATH}"

# Test basic functionality
RUN ostruct --help
RUN ostruct --version

# Test dry-run functionality
RUN echo '{"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}' > test_schema.json
RUN echo 'Test: {{ "hello from Alpine" }}' > test_template.j2
RUN ostruct run test_template.j2 test_schema.json --dry-run

# Create verification script
RUN echo '#!/bin/bash' > verify.sh && \
    echo 'echo "=== Alpine Linux Installation Test ==="' >> verify.sh && \
    echo 'echo "Python version: $(python --version)"' >> verify.sh && \
    echo 'echo "Pip version: $(pip --version)"' >> verify.sh && \
    echo 'echo "Ostruct version: $(ostruct --version)"' >> verify.sh && \
    echo 'echo "Ostruct help works: $(ostruct --help > /dev/null && echo OK || echo FAILED)"' >> verify.sh && \
    echo 'echo "Dry-run test: $(ostruct run test_template.j2 test_schema.json --dry-run > /dev/null && echo OK || echo FAILED)"' >> verify.sh && \
    echo 'echo "=== Test Complete ==="' >> verify.sh && \
    chmod +x verify.sh

CMD ["./verify.sh"]
