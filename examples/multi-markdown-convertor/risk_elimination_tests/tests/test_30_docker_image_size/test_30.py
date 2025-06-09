#!/usr/bin/env python3
"""
Test 30: Docker image with all deps stays < 1 GB
Build minimal converter image
"""

import json
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional


def create_dockerfile() -> str:
    """Create a Dockerfile for the markdown converter."""
    return """# Multi-stage build for minimal image size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \\
    pandoc \\
    tesseract-ocr \\
    tesseract-ocr-heb \\
    poppler-utils \\
    && rm -rf /var/lib/apt/lists/* \\
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/
COPY schemas/ ./schemas/

# Create non-root user
RUN useradd -m -u 1000 converter
USER converter

# Set entrypoint
ENTRYPOINT ["python", "-m", "src.converter"]
"""


def create_requirements_txt() -> str:
    """Create requirements.txt for the converter."""
    return """# Core dependencies
PyMuPDF==1.23.8
python-docx==1.1.0
python-pptx==0.6.23
openpyxl==3.1.2
xlwings==0.30.13
pandas==2.1.4
markitdown==0.0.1a2

# PDF processing
pdfminer.six==20231228
camelot-py[cv]==0.11.0
tabula-py==2.9.0

# OCR and image processing
pytesseract==0.3.10
Pillow==10.1.0
opencv-python-headless==4.8.1.78

# LLM and API
openai==1.6.1
requests==2.31.0

# Utilities
pyyaml==6.0.1
jinja2==3.1.2
click==8.1.7
tqdm==4.66.1

# Optional optimizations
lxml==4.9.4
beautifulsoup4==4.12.2
"""


def create_dockerignore() -> str:
    """Create .dockerignore file."""
    return """# Version control
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# Documentation
*.md
docs/

# IDE
.vscode
.idea
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Test files
test-inputs/
tests/
temp_verify/

# Build artifacts
build/
dist/
*.egg-info/
"""


def get_image_size(image_name: str) -> Optional[int]:
    """
    Get Docker image size in bytes.

    Args:
        image_name: Name of the Docker image

    Returns:
        Image size in bytes, or None if failed
    """
    try:
        # Get image size using docker images command
        cmd = ["docker", "images", image_name, "--format", "{{.Size}}"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            size_str = result.stdout.strip()

            # Parse size string (e.g., "1.2GB", "500MB")
            if size_str.endswith("GB"):
                return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
            elif size_str.endswith("MB"):
                return int(float(size_str[:-2]) * 1024 * 1024)
            elif size_str.endswith("KB"):
                return int(float(size_str[:-2]) * 1024)
            elif size_str.endswith("B"):
                return int(size_str[:-1])
            else:
                # Try to parse as bytes
                return int(size_str)

        return None

    except (subprocess.TimeoutExpired, ValueError, subprocess.SubprocessError):
        return None


def test_docker_image_size() -> Dict[str, Any]:
    """
    Test Docker image size for the markdown converter.

    Returns:
        Dict with test results
    """
    results: Dict[str, Any] = {
        "test_id": "30",
        "test_name": "Docker image with all deps stays < 1 GB",
        "target_size_gb": 1.0,
        "docker_available": False,
        "dockerfile_created": False,
        "build_successful": False,
        "image_size_bytes": 0,
        "image_size_mb": 0.0,
        "image_size_gb": 0.0,
        "size_under_limit": False,
        "build_time_seconds": 0.0,
        "build_output": "",
        "success": False,
        "error": None,
    }

    temp_dir = None
    image_name = "markdown-converter-test"

    try:
        # Check if Docker is available
        try:
            subprocess.run(
                ["docker", "--version"], capture_output=True, timeout=10
            )
            results["docker_available"] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            results["error"] = (
                "Docker not available - install Docker to test image size"
            )
            return results

        # Create temporary directory for build context
        temp_dir = Path(tempfile.mkdtemp())

        # Create Dockerfile
        dockerfile_content = create_dockerfile()
        dockerfile_path = temp_dir / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Create requirements.txt
        requirements_content = create_requirements_txt()
        requirements_path = temp_dir / "requirements.txt"
        with open(requirements_path, "w") as f:
            f.write(requirements_content)

        # Create .dockerignore
        dockerignore_content = create_dockerignore()
        dockerignore_path = temp_dir / ".dockerignore"
        with open(dockerignore_path, "w") as f:
            f.write(dockerignore_content)

        # Create minimal source structure
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").touch()
        (src_dir / "converter.py").write_text("""#!/usr/bin/env python3
print("Markdown converter placeholder")
""")

        (temp_dir / "templates").mkdir()
        (temp_dir / "schemas").mkdir()

        results["dockerfile_created"] = True

        print(f"Building Docker image: {image_name}")
        print(f"Build context: {temp_dir}")

        # Build Docker image
        import time

        start_time = time.time()

        build_cmd = ["docker", "build", "-t", image_name, str(temp_dir)]

        build_process = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout for build
        )

        end_time = time.time()
        results["build_time_seconds"] = end_time - start_time
        results["build_output"] = build_process.stdout + build_process.stderr

        if build_process.returncode == 0:
            results["build_successful"] = True
            print(
                f"Build completed in {results['build_time_seconds']:.1f} seconds"
            )

            # Get image size
            image_size = get_image_size(image_name)
            if image_size:
                results["image_size_bytes"] = image_size
                results["image_size_mb"] = image_size / (1024 * 1024)
                results["image_size_gb"] = image_size / (1024 * 1024 * 1024)

                print(
                    f"Image size: {results['image_size_mb']:.1f} MB ({results['image_size_gb']:.2f} GB)"
                )

                # Check if under size limit
                results["size_under_limit"] = (
                    results["image_size_gb"] < results["target_size_gb"]
                )

                if results["size_under_limit"]:
                    print(
                        f"✅ Image size under {results['target_size_gb']} GB limit"
                    )
                else:
                    print(
                        f"❌ Image size exceeds {results['target_size_gb']} GB limit"
                    )
            else:
                results["error"] = "Failed to get image size"
        else:
            results["error"] = f"Docker build failed: {build_process.stderr}"
            print(f"Build failed: {build_process.stderr}")

        # Clean up Docker image
        try:
            subprocess.run(
                ["docker", "rmi", image_name], capture_output=True, timeout=30
            )
        except subprocess.TimeoutExpired:
            pass  # Ignore cleanup timeout

        # Determine success
        results["success"] = (
            results["docker_available"]
            and results["dockerfile_created"]
            and results["build_successful"]
            and results["size_under_limit"]
        )

    except subprocess.TimeoutExpired:
        results["error"] = "Docker build timed out after 10 minutes"
    except Exception as e:
        results["error"] = str(e)
    finally:
        # Clean up temporary directory
        if temp_dir and temp_dir.exists():
            import shutil

            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass  # Ignore cleanup errors

    return results


def main():
    """Run the Docker image size test."""
    print("Test 30: Docker image with all deps stays < 1 GB")
    print("=" * 60)

    results = test_docker_image_size()

    # Save results
    output_file = Path(__file__).parent / "results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\nResults saved to: {output_file}")
    print(f"Docker available: {results['docker_available']}")
    print(f"Build successful: {results['build_successful']}")

    if results["image_size_gb"] > 0:
        print(f"Image size: {results['image_size_gb']:.2f} GB")
        print(f"Under 1 GB limit: {results['size_under_limit']}")

    if results["build_time_seconds"] > 0:
        print(f"Build time: {results['build_time_seconds']:.1f} seconds")

    if results["success"]:
        print("✅ PASS: Docker image size under 1 GB")
    else:
        print("❌ FAIL: Docker image size issues")
        if results["error"]:
            print(f"Error: {results['error']}")

    return results


if __name__ == "__main__":
    main()
