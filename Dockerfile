# Use an official Python runtime as a parent image
FROM python:3.12-slim

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
