# Installation Guide

This guide provides detailed installation instructions for AwesomeCLI across different platforms and environments.

## Prerequisites

Before installing AwesomeCLI, ensure you have:

- Python 3.8 or higher
- pip package manager

Check your Python version:

```bash
python --version
```

Check pip installation:

```bash
pip --version
```

## Standard Installation

### Using pip (Recommended)

Install the latest stable version:

```bash
pip install awesome-cli
```

Install a specific version:

```bash
pip install awesome-cli==1.2.3
```

Upgrade to the latest version:

```bash
pip install --upgrade awesome-cli
```

### Using pipx (Isolated Installation)

For isolated installation that doesn't affect your global Python environment:

```bash
pipx install awesome-cli
```

## Development Installation

### From Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/example/awesome-cli.git
cd awesome-cli
pip install -e .
```

Install with development dependencies:

```bash
pip install -e ."[dev]"
```

### Using Poetry

If you prefer Poetry for dependency management:

```bash
git clone https://github.com/example/awesome-cli.git
cd awesome-cli
poetry install
poetry shell
```

## Platform-Specific Instructions

### Windows

Install using Command Prompt:

```cmd
pip install awesome-cli
```

Or using PowerShell:

```powershell
pip install awesome-cli
```

Add to PATH (if not automatically added):

```cmd
set PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python39\Scripts
```

### macOS

Install using Homebrew:

```bash
brew install awesome-cli
```

Or using pip:

```bash
pip3 install awesome-cli
```

### Linux

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install python3-pip
pip3 install awesome-cli
```

#### CentOS/RHEL/Fedora

```bash
sudo yum install python3-pip
# or for newer versions:
sudo dnf install python3-pip

pip3 install awesome-cli
```

#### Arch Linux

```bash
sudo pacman -S python-pip
pip install awesome-cli
```

## Virtual Environment Installation

### Using venv

Create and activate a virtual environment:

```bash
python -m venv awesome-cli-env
source awesome-cli-env/bin/activate  # On Windows: awesome-cli-env\Scripts\activate
pip install awesome-cli
```

### Using conda

```bash
conda create -n awesome-cli python=3.9
conda activate awesome-cli
pip install awesome-cli
```

## Docker Installation

### Using Pre-built Image

Pull and run the official Docker image:

```bash
docker pull awesome-cli:latest
docker run --rm -v $(pwd):/data awesome-cli:latest process /data/input.csv
```

### Building Custom Image

Create a Dockerfile:

```dockerfile
FROM python:3.9-slim

# Install AwesomeCLI
RUN pip install awesome-cli

# Set working directory
WORKDIR /app

# Copy your data
COPY . /app

# Default command
CMD ["awesome-cli", "--help"]
```

Build and run:

```bash
docker build -t my-awesome-cli .
docker run --rm my-awesome-cli
```

## Verification

After installation, verify that AwesomeCLI is working correctly:

```bash
awesome-cli --version
```

Expected output:

```
AwesomeCLI version 1.2.3
```

Run a basic command:

```bash
awesome-cli --help
```

Test with a simple file (create test data first):

```bash
echo "name,value" > test.csv
echo "test,123" >> test.csv
awesome-cli process test.csv
```

## Troubleshooting Installation

### Common Issues

1. **Command not found**: Add Python Scripts directory to PATH

   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

2. **Permission denied**: Use user installation

   ```bash
   pip install --user awesome-cli
   ```

3. **Python version incompatible**: Upgrade Python

   ```bash
   sudo apt install python3.9  # Ubuntu example
   ```

4. **SSL certificate errors**: Upgrade certificates

   ```bash
   pip install --upgrade certifi
   ```

### Uninstalling

To remove AwesomeCLI:

```bash
pip uninstall awesome-cli
```

To remove all dependencies as well:

```bash
pip freeze | grep awesome-cli
pip uninstall awesome-cli
# Remove any related packages manually
```

## Next Steps

After successful installation:

1. Read the [User Guide](user-guide.md)
2. Check out [Examples](../README.md#examples)
3. Configure your [Environment](configuration.md)
