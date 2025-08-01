# Developer Guide: Code Interpreter File Downloads

This guide explains the architecture and implementation of ostruct's Code Interpreter file download system.

## Architecture Overview

The CI file download system uses a multi-tier approach to ensure reliability:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Ostruct CLI Request                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              Template Processor                                 │
│  • Applies model-specific instructions                          │
│  • Enhances system/user prompts                                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                OpenAI API Call                                  │
│  • Uses Responses API with structured output                    │
│  • Code Interpreter tool enabled                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              Response Processing                                 │
│  • Extracts container_file_citation annotations                 │
│  • Tracks container IDs and expiry                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               File Download                                      │
│  • Raw HTTP for cfile_ IDs (SDK limitation bypass)             │
│  • OpenAI SDK for regular file_ IDs                            │
│  • Exponential backoff retry logic                              │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Model-Specific Instructions (`template_processor.py`)

**Location:** `src/ostruct/cli/template_processor.py`

Injects model-specific instructions to improve file annotation reliability:

```python
MODEL_SPECIFIC_INSTRUCTIONS = {
    "gpt-4.1": {
        "system_append": """
### CRITICAL FILE HANDLING REQUIREMENTS
When using the python tool to create files:
1. **ALWAYS provide download links** in this exact format:
   [Download Filename](sandbox:/mnt/data/filename.ext)
2. **Include download links in your response** - this is REQUIRED
3. **Save files to /mnt/data/** directory only
4. **Confirm file creation** with explicit success messages
""",
        "user_append": """
IMPORTANT: Please include download links for any files you create using the format:
[Download Filename](sandbox:/mnt/data/filename.ext)
"""
    },
    # ... other models
}
```

**Integration Point:** `runner.py` calls `inject_model_instructions()` before API calls.

### 2. Container Tracking (`code_interpreter.py`)

**Location:** `src/ostruct/cli/code_interpreter.py`

Tracks container creation and detects expiry:

```python
class ContainerTracker:
    def __init__(self) -> None:
        self.containers: Dict[str, datetime] = {}

    def register_container(self, container_id: str) -> None:
        """Register a new container with current timestamp"""
        self.containers[container_id] = datetime.now()

    def is_container_expired(self, container_id: str) -> bool:
        """Check if container is likely expired (18 minute threshold)"""
        if container_id not in self.containers:
            return False
        age = datetime.now() - self.containers[container_id]
        return age > timedelta(minutes=18)  # 2-minute buffer
```

### 3. Raw HTTP Downloads (`container_downloader.py`)

**Location:** `src/ostruct/cli/container_downloader.py`

Handles container file downloads via raw HTTP (bypasses SDK limitations):

```python
class ContainerFileDownloader:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def download_container_file(self, file_id: str, container_id: str) -> bytes:
        """Download file content with proper fallback strategy"""
        url = f"https://api.openai.com/v1/containers/{container_id}/files/{file_id}/content"

        # Check file size first
        head_response = await self.client.head(url)
        content_length = head_response.headers.get("content-length")
        if content_length and int(content_length) > MAX_DOWNLOAD_SIZE:
            raise DownloadError(f"File too large: {content_length} bytes")

        # Download content
        response = await self.client.get(url)
        if response.status_code == 404:
            raise ContainerExpiredError(f"Container {container_id} expired")
        elif response.status_code != 200:
            raise DownloadError(f"Download failed: {response.status_code}")

        return response.content
```

### 4. Enhanced Error Handling (`download_errors.py`)

**Location:** `src/ostruct/cli/download_errors.py`

Provides classified errors with user-friendly messages:

```python
class DownloadErrorType(Enum):
    CONTAINER_EXPIRED = "container_expired"
    SDK_LIMITATION = "sdk_limitation"
    NETWORK_TIMEOUT = "network_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    FILE_NOT_FOUND = "file_not_found"
    ANNOTATION_MISSING = "annotation_missing"

class EnhancedDownloadError(DownloadError):
    def __init__(self, message: str, error_type: DownloadErrorType, ...):
        super().__init__(message)
        self.error_type = error_type
        self.suggestions = suggestions or []

    def get_user_message(self) -> str:
        """Return user-friendly error message with suggestions"""
        # Implementation provides contextual help
```

### 5. Retry Logic (`retry_handler.py`)

**Location:** `src/ostruct/cli/retry_handler.py`

Implements exponential backoff with jitter:

```python
async def retry_with_backoff(
    func: Callable[..., T],
    config: RetryConfig,
    retryable_exceptions: tuple = (Exception,),
    *args, **kwargs
) -> T:
    """Retry async operations with exponential backoff"""

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            if attempt == config.max_attempts - 1:
                raise

            # Calculate backoff with jitter
            delay = min(
                config.base_delay * (config.backoff_factor ** attempt),
                config.max_delay
            )
            jitter = random.uniform(0, config.jitter_factor * delay)
            await asyncio.sleep(delay + jitter)
```

## Integration Flow

### 1. Request Processing (`runner.py`)

```python
# Apply model-specific instructions
if model:
    from .template_processor import inject_model_instructions
    temp_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    enhanced_messages = inject_model_instructions(temp_messages, model)
    system_prompt = enhanced_messages[0]["content"]
    user_prompt = enhanced_messages[1]["content"]
```

### 2. Response Processing (`code_interpreter.py`)

```python
# Register container for tracking
container_tracker.register_container(container_id)

# Extract file annotations
annotations = collect_file_annotations(response)

# Download files with fallback strategy
for annotation in annotations:
    if annotation.file_id.startswith("cfile_"):
        # Use raw HTTP downloader
        downloader = ContainerFileDownloader(client.api_key)
        content = await downloader.download_container_file(
            annotation.file_id, annotation.container_id
        )
    else:
        # Use OpenAI SDK
        content = await client.files.content(annotation.file_id)
```

## Testing Framework

### Unit Tests

Test individual components in isolation:

```python
# Test model instruction injection
def test_inject_model_instructions():
    messages = [{"role": "system", "content": "You are helpful."}]
    result = inject_model_instructions(messages, "gpt-4.1")
    assert "CRITICAL FILE HANDLING" in result[0]["content"]

# Test container tracking
def test_container_expiry():
    tracker = ContainerTracker()
    tracker.register_container("test_id")
    assert not tracker.is_container_expired("test_id")
```

### Integration Tests

Test complete workflows:

```python
# Test full ostruct CLI with file downloads
def test_ostruct_file_download():
    result = subprocess.run([
        "ostruct", "run", "template.j2", "schema.json",
        "--model", "gpt-4.1", "--enable-tool", "code-interpreter"
    ], capture_output=True, text=True)

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "filename" in output
    assert "sandbox:/mnt/data/" in output.get("message", "")
```

### Performance Tests

Measure reliability and timing:

```python
# Run multiple iterations to test consistency
def test_performance_benchmark():
    results = []
    for i in range(10):
        start_time = time.time()
        result = run_ostruct_test(i)
        end_time = time.time()
        results.append({
            "success": result.returncode == 0,
            "time": end_time - start_time
        })

    success_rate = sum(1 for r in results if r["success"]) / len(results)
    assert success_rate >= 0.9  # 90% success rate minimum
```

## Configuration

### Constants

```python
# File size limits
MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024  # 100MB

# Container expiry
CONTAINER_EXPIRY_MINUTES = 18  # 2-minute buffer before 20min limit

# Retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0,
    max_delay=10.0,
    jitter_factor=0.1
)
```

### Environment Variables

```bash
# API configuration
OPENAI_API_KEY=your_key_here

# Debug settings
OSTRUCT_DEBUG=1              # Enable debug logging
OSTRUCT_VERBOSE=1            # Enable verbose output
```

## Development Workflow

### Adding New Features

1. **Design**: Update architecture diagrams
2. **Implement**: Add core functionality with proper typing
3. **Test**: Create unit and integration tests
4. **Document**: Update this guide and user docs
5. **Validate**: Run full test suite

### Debugging Issues

1. **Enable verbose logging**: `--verbose` flag
2. **Check error classifications**: Look for specific error types
3. **Test with different models**: gpt-4.1 is most reliable
4. **Validate schemas**: Ensure `message` field is included
5. **Monitor container age**: Check for expiry warnings

### Performance Optimization

1. **Profile timing**: Use performance test suite
2. **Monitor success rates**: Track reliability metrics
3. **Optimize retry logic**: Adjust backoff parameters
4. **Cache containers**: Reuse when possible (future enhancement)

## Future Enhancements

### Planned Improvements

1. **WebSocket Streaming**: For large file downloads
2. **Container Persistence**: Extended container lifetimes
3. **Progress Indicators**: Real-time download progress
4. **Parallel Downloads**: Multiple files simultaneously
5. **Caching Layer**: Reduce redundant API calls

### SDK Evolution

Monitor OpenAI SDK updates for native container file support:

```python
# Future: When SDK supports container files
async def download_with_sdk(file_id: str, container_id: str) -> bytes:
    # This will replace raw HTTP when available
    return await client.containers.files.content(file_id, container_id)
```

## Contributing

When contributing to the CI download system:

1. **Follow patterns**: Use existing error handling and logging
2. **Add tests**: Both unit and integration coverage
3. **Update docs**: Keep this guide current
4. **Consider reliability**: Prioritize robustness over performance
5. **Test thoroughly**: Run full test suite including performance benchmarks

The goal is maximum reliability for Code Interpreter file downloads while maintaining reasonable performance and user experience.

## See Also

- **[Troubleshooting Guide](troubleshooting-ci-downloads.md)** - User-facing solutions for common CI download issues
- **[Known Issues](known-issues/2025-06-responses-ci-file-output.md)** - OpenAI API bug details and workarounds
