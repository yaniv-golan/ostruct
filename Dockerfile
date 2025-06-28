# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Accept version as build argument
ARG VERSION
ENV POETRY_DYNAMIC_VERSIONING_BYPASS=${VERSION}

# Install git (required for poetry-dynamic-versioning)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install the package from source
RUN pip install --no-cache-dir .

# Set the entrypoint to the ostruct command
ENTRYPOINT ["ostruct"]

# Default command to run when container starts
CMD ["--help"]
